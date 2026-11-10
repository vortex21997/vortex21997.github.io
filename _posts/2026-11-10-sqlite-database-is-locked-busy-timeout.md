---
title: "SQLite 'database is locked'가 뜰 때: 기다리다 실패한 건지, 기다리지도 않고 실패한 건지"
description: "sqlite3.OperationalError: database is locked를 두 연결로 재현하고, 타임아웃만큼 기다린 뒤 실패하는 경우와 즉시 실패하는 경우를 시간으로 가른다. WAL 모드와 BEGIN IMMEDIATE가 각각 무엇을 바꾸는지 실행 출력으로 확인했다."
date: 2026-11-10 20:00:00 +0900
categories: [전산학, 데이터베이스]
tags: [sqlite, 트랜잭션, wal]
---

> 2026-11 기준. Python 3.11.18, SQLite 3.45.1, Linux 샌드박스에서 실행했다. 시간은 이 환경에서 잰 값이다.

같은 DB 파일에 연결 두 개가 쓰면 `sqlite3.OperationalError: database is locked`가 난다. 이 에러는 **원인이 둘**이고, 에러 문구는 같다. 가르는 기준은 **실패까지 걸린 시간**이다. `timeout`만큼 기다렸다 실패하면 단순한 쓰기 경합이고, 기다리지 않고 바로 실패하면 트랜잭션을 읽기로 시작했다가 쓰기로 올리려다 막힌 것이다.

## 1. 기다렸다 실패: 다른 연결이 쓰기 중

연결 a가 트랜잭션 안에서 INSERT하고 아직 커밋하지 않은 채, 연결 b(`timeout=1`)가 쓰려는 상황이다.

```python
a = sqlite3.connect("t.db", isolation_level=None, timeout=1)
b = sqlite3.connect("t.db", isolation_level=None, timeout=1)
a.execute("begin"); a.execute("insert into t values(1)")
b.execute("insert into t values(2)")   # 여기서 실패
```

```
== delete journal_mode= delete
 read : (0,)
 write: OperationalError: database is locked 1.0 s
== wal journal_mode= wal
 read : (0,)
 write: OperationalError: database is locked 1.0 s
```

`timeout=1`이라 정확히 1.0초 뒤에 실패했다. 읽기는 두 모드 모두 막히지 않았고 커밋 전 값(0)을 읽었다. 쓰기는 모드와 상관없이 한 번에 하나다. WAL 문서도 "there can only be one writer at a time"이라고 적는다([WAL 문서](https://www.sqlite.org/wal.html)). 이 경우의 해법은 `timeout`을 늘리거나 a의 트랜잭션을 짧게 끝내는 것이다.

## 2. 기다리지 않고 실패: 읽기 트랜잭션을 쓰기로 올리려다

두 연결이 모두 `BEGIN`(기본값 DEFERRED) 뒤에 SELECT를 하고, a가 먼저 쓰고, b가 쓰려는 경우다.

```
upgrade b: database is locked 0.0
```

`timeout=1`인데 **0.0초**에 실패했다. b가 기다려 봐야 소용없다. b는 이미 읽기 스냅샷을 잡고 있어서, 기다려서 락을 얻더라도 그 사이 바뀐 DB 위에 쓰게 되기 때문으로 보인다(이 부분은 문서 인용이 아니라 관찰에서 추정한 것이다). 공식 문서는 이렇게만 적는다. ([트랜잭션 문서](https://www.sqlite.org/lang_transaction.html))

> If some other database connection has already modified the database or is already in the process of modifying the database, then upgrading to a write transaction is not possible and the write statement will fail with SQLITE_BUSY.

타임아웃을 아무리 늘려도 이 경우는 안 풀린다. 시작을 `BEGIN IMMEDIATE`로 바꿔 처음부터 쓰기 락을 잡아야 한다.

## 3. BEGIN IMMEDIATE로 바꾸면: 모드에 따라 결과가 다르다

스레드 두 개가 각각 `begin`(또는 `begin immediate`) → SELECT → 0.3초 대기 → INSERT → commit을 하고, `timeout=5`다.

| journal_mode | 시작 | w0 | w1 |
|---|---|---|---|
| WAL | `BEGIN` | ok 0.3s | database is locked 0.3s |
| WAL | `BEGIN IMMEDIATE` | ok 0.3s | **ok 0.63s** |
| delete(기본) | `BEGIN` | database is locked 5.32s | database is locked 0.3s |
| delete(기본) | `BEGIN IMMEDIATE` | database is locked 5.02s | database is locked 5.02s |

- WAL + `BEGIN IMMEDIATE`: w1이 w0의 커밋을 기다렸다가 성공했다. 이게 원하는 동작이다.
- 기본 모드(delete)에서는 `BEGIN IMMEDIATE`로도 **둘 다 5초를 기다린 뒤 실패**했다. 원인은 확인하지 못했다. 읽기를 하는 연결이 서로 기다리는 상황일 것으로 짐작할 뿐이다.

## 정리: 에러를 만나면

1. 실패까지 걸린 시간을 본다. `timeout`만큼이면 쓰기 경합, 즉시면 읽기→쓰기 승격이다.
2. 승격이면 `BEGIN IMMEDIATE`로 시작한다.
3. 여러 연결이 쓴다면 `PRAGMA journal_mode=WAL`을 함께 쓴다. 이 환경에서 `BEGIN IMMEDIATE`가 기다렸다 성공한 것은 WAL뿐이었다.
