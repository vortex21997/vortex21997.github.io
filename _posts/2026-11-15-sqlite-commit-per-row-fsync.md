---
title: "INSERT 2000건이 1.5초, 한 트랜잭션이면 0.003초: SQLite 커밋마다 디스크를 기다리는 이유"
description: "SQLite에 같은 2000행을 넣는데 행마다 커밋하면 1.5초, 한 트랜잭션으로 묶으면 0.003초가 걸렸다. strace로 커밋 한 번당 fdatasync가 4번 호출되는 것을 세고, synchronous=OFF와 WAL이 이 숫자를 어떻게 바꾸는지 확인했다."
date: 2026-11-15 20:00:00 +0900
categories: [전산학, 데이터베이스]
tags: [sqlite, fsync, 트랜잭션]
---

결론부터: 행마다 커밋하면 느린 건 INSERT가 느려서가 아니라 **커밋마다 디스크에 "정말 썼다"는 확인(`fdatasync`)을 기다리기 때문**이다. 한 트랜잭션으로 묶으면 그 대기가 한 번으로 줄어든다.

> 측정 환경: Linux 6.18, ext4(`/dev/vda`), 4코어 샌드박스 VM, Python 3.11.18, SQLite 3.45.1. 절대 시간은 디스크마다 크게 다르다. 비율과 호출 횟수만 참고할 것.
{: .prompt-info }

## 같은 2000행, 커밋만 다르게

`isolation_level=None`으로 Python이 몰래 `BEGIN`을 넣지 않게 하고, 명령을 직접 제어했다.

```python
import sqlite3, time, os, sys
mode, n = sys.argv[1], int(sys.argv[2])
p = f"t_{mode}.db"
c = sqlite3.connect(p, isolation_level=None)   # 자동 커밋: 문장마다 커밋
c.execute("create table t(id integer primary key, v text)")
t = time.perf_counter()
if mode == "each":
    for i in range(n): c.execute("insert into t(v) values(?)", ("x%d" % i,))
else:
    c.execute("begin")
    for i in range(n): c.execute("insert into t(v) values(?)", ("x%d" % i,))
    c.execute("commit")
print(mode, n, "%.3fs" % (time.perf_counter() - t))
```

```
each 2000 1.532s (2000,)
one 2000 0.003s (2000,)
one 200000 0.240s (200000,)
```

같은 일을 500배 차이로 한다. 20만 행도 한 트랜잭션이면 0.24초다. 행 수가 아니라 **커밋 횟수**가 시간을 정한다.

## strace로 세어 보기

`strace -f -c -e trace=fsync,fdatasync`로 2000건을 다시 돌렸다. (strace가 붙으면 전체가 느려지므로 시간 값은 무시하고 호출 횟수만 본다.)

```
# 행마다 커밋
100.00    0.396410          49      8004           fdatasync
# 한 트랜잭션
100.00    0.000311          38         8           fdatasync
```

행마다 커밋하면 2000번 커밋에 `fdatasync` 8004번, 즉 **커밋 하나당 4번**이다. 한 트랜잭션은 총 8번이다(테이블 생성과 커밋 몫). 기본 모드(`journal_mode`가 `delete`)의 커밋이 여러 번의 플러시를 거치는 구조는 SQLite 공식 문서 [Atomic Commit In SQLite](https://www.sqlite.org/atomiccommit.html)에 설명돼 있다. 4라는 숫자는 이 환경에서 센 값이다.

`fdatasync`는 "운영체제 캐시에 있는 내용을 저장장치에 실제로 내려보내고 끝날 때까지 기다리는" 시스템 콜이다. 행마다 커밋한 실행은 1.532초를 8004번으로 나누면 호출당 약 190µs다(전체 시간을 나눈 값이라 근사치). 어쨌든 INSERT 한 줄의 CPU 시간보다 훨씬 크다.

## 설정을 바꾸면 숫자가 어떻게 변하나

같은 2000건, 행마다 커밋하는 조건에서 PRAGMA만 바꿨다.

```
pragma journal_mode          -> [('delete',)]   1.687s
pragma synchronous=OFF       -> []              0.046s
pragma journal_mode=WAL      -> [('wal',)]      0.349s
```

WAL에서 `fdatasync`를 다시 세면 이렇다.

```
100.00    0.101542          50      2015           fdatasync
```

커밋당 약 1번(2000건에 2015번)이다. 4번에서 1번으로 줄어서 시간이 약 1/5이 됐다. 관련 설명은 [Write-Ahead Logging](https://www.sqlite.org/wal.html).

`synchronous=OFF`는 `fdatasync` 자체를 부르지 않아 가장 빠르다. 대가는 [PRAGMA synchronous 문서](https://www.sqlite.org/pragma.html#pragma_synchronous)에 있다. SQLite가 데이터를 운영체제에 넘기고 바로 진행하므로, **운영체제가 죽거나 전원이 나가면 데이터베이스가 깨질 수 있다**고 한다. 이번 실험에서 정전을 일으켜 본 것은 아니니 이 부분은 문서 내용이다.

## 판별 기준

SQLite 쓰기가 느릴 때 이렇게 가린다.

| 증상 | 원인 | 확인 |
|---|---|---|
| 행 수에 비례해 느리고, 한 번에 묶으면 빨라짐 | 커밋마다 디스크 대기 | `strace -c -e trace=fdatasync`로 호출 수 ≈ 커밋 수 × N |
| 한 트랜잭션인데도 느림 | 디스크 대기가 아니라 쿼리·인덱스 쪽 | `EXPLAIN QUERY PLAN` ([인덱스를 탔는지 보는 글](/posts/sqlite-index-not-used-like/)) |

권장 순서는 (1) 반복 쓰기를 `BEGIN`~`COMMIT`으로 묶고, (2) 동시에 읽고 써야 하면 WAL, (3) 내구성을 포기해도 되는 임시 데이터에만 `synchronous=OFF`다.

> Python `sqlite3`의 기본 `isolation_level`("")은 INSERT 앞에서 자동으로 `BEGIN`을 열고 `commit()`을 부를 때까지 유지한다. 그래서 `commit()`을 반복문 안에 두면 위와 같은 느린 경우가 된다.
{: .prompt-tip }

락 충돌로 `database is locked`가 뜨는 문제는 [별도 글](/posts/sqlite-database-is-locked-busy-timeout/)에서 다뤘다.
