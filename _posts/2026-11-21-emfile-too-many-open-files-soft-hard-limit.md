---
title: "'Too many open files'(EMFILE)는 파일 개수 문제가 아니라 프로세스당 fd 한도다: soft/hard 제한을 직접 보기"
description: "[Errno 24] Too many open files가 뜰 때, 프로세스당 파일 디스크립터 한도(RLIMIT_NOFILE)를 /proc/self/limits로 확인하고 soft는 hard까지 올릴 수 있지만 hard는 못 올리는 것을 직접 돌려 확인했다."
date: 2026-11-21 20:00:00 +0900
categories: [전산학, 운영체제]
tags: [emfile, ulimit, rlimit, 파일 디스크립터]
---

`[Errno 24] Too many open files`는 디스크에 파일이 너무 많다는 뜻이 아니다. **한 프로세스가 동시에 열어 둘 수 있는 파일 디스크립터(fd) 수가 `RLIMIT_NOFILE`에 닿았다**는 뜻이다. 한도는 soft와 hard 두 값이고, 실제로 막는 쪽은 soft다. soft는 hard까지 스스로 올릴 수 있지만, hard는 권한이 없으면 못 올린다.

> 파일 디스크립터(fd)는 열린 파일·소켓·파이프를 가리키는 프로세스 안의 번호표다. 0·1·2는 표준 입력·출력·에러가 이미 차지한다.
{: .prompt-info }

_2026-11 기준. 실행 환경: Linux 6.18.44, Python 3.11.18, bash. 근거: [getrlimit(2)](https://man7.org/linux/man-pages/man2/getrlimit.2.html), [open(2)](https://man7.org/linux/man-pages/man2/open.2.html)의 EMFILE 항목._

## 에러 메시지 원문

```text
OSError: [Errno 24] Too many open files: '/dev/null'
```

시스템 콜 수준에서는 `openat`이 `EMFILE`을 돌려준다.

```text
openat(AT_FDCWD, "/dev/null", O_RDONLY|O_CLOEXEC) = -1 EMFILE (Too many open files)
```

## 재현: soft를 64로 낮추고 계속 열기

```python
import os, resource
soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
print("soft,hard =", soft, hard)
fds=[]
try:
    while True:
        fds.append(os.open("/dev/null", os.O_RDONLY))
except OSError as e:
    print("opened", len(fds), "->", e)
```

```console
$ (ulimit -Sn 64; python3 openmany.py)
soft,hard = 64 20000
opened 61 -> [Errno 24] Too many open files: '/dev/null'
```

64개가 아니라 **61개**에서 멈췄다. 0·1·2번 fd가 이미 3개를 쓰고 있기 때문이다. 한도는 "열린 fd 개수"가 아니라 "fd 번호의 상한"이라, 번호 0~63을 다 쓰면 끝이다.

## 판별법: 지금 이 프로세스의 한도는 얼마인가

한도는 프로세스마다 `/proc/<pid>/limits`에 있다. 서버 프로세스가 문제라면 셸의 `ulimit -n`이 아니라 **그 프로세스의 PID**로 본다.

```console
$ (ulimit -Sn 64; grep 'open files' /proc/self/limits)
Max open files            64                   20000                files
```

열 순서는 Soft Limit, Hard Limit, 단위다. 지금 몇 개를 쓰는지는 `ls /proc/<pid>/fd | wc -l`로 센다. 이 수가 soft에 가깝다면 한도 문제이고, 한참 낮은데도 EMFILE이 나면 다른 프로세스의 한도를 보고 있는 것이다.

## soft는 hard까지, hard는 못 올린다

```console
$ (ulimit -Sn 64; ulimit -Sn 128; echo rc=$?; python3 openmany.py)
rc=0
soft,hard = 128 20000
opened 125 -> [Errno 24] Too many open files: '/dev/null'

$ (ulimit -Sn 64; ulimit -Sn 100000)
/bin/bash: ulimit: open files: cannot modify limit: Invalid argument
```

soft를 hard(20000) 이하로 올리는 것은 되고, hard를 넘기려 하면 `Invalid argument`다. 프로그램 안에서는 시작할 때 soft를 hard까지 올리면 된다.

```python
resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))
```

```console
(20000, 20000)
```

한 번 낮춘 hard를 다시 올리는 것도 막혀 있었다.

```console
$ (ulimit -Hn 128; ulimit -Sn 64; ulimit -Hn 256)
/bin/bash: ulimit: open files: cannot modify limit: Operation not permitted
```

getrlimit(2)에 따르면 hard를 올리려면 `CAP_SYS_RESOURCE` 권한이 필요하다. 이 샌드박스는 root인데도 거부됐으니, 이 환경에는 그 권한이 없는 것으로 보인다(권한 목록까지는 확인하지 않았다). 그리고 자식 프로세스는 부모의 한도를 그대로 물려받는다. 셸에서 낮춘 `ulimit`은 그 셸이 띄우는 프로그램에 모두 적용된다.

## 정리

- 메시지는 `EMFILE`, 원인은 프로세스별 `RLIMIT_NOFILE`(soft)에 닿은 것이다. 디스크 파일 수와 무관하다.
- 진단은 `/proc/<pid>/limits`로 한도를, `/proc/<pid>/fd`로 사용량을 본다.
- soft < hard면 코드나 `ulimit -Sn`으로 올릴 수 있다. hard가 낮으면 서비스 설정이나 관리자 권한이 필요하다. 이 글에서는 설정 파일 방식은 돌려 보지 않았다.
- fd가 계속 늘기만 한다면 한도를 올리는 것은 미룰 뿐이고, 닫지 않는 누수를 찾아야 한다.
