---
title: "파이프 뒤에 head를 붙였더니 종료 코드가 141: SIGPIPE와 Broken pipe"
description: "yes | head -1 의 앞 명령이 종료 코드 141로 끝나고, 파이썬은 BrokenPipeError를 내는 이유. 읽는 쪽이 먼저 닫힌 파이프에 쓰면 커널이 SIGPIPE(13)를 보내고, 128+13이 141이다. strace로 확인하고 pipefail과의 관계까지 정리."
date: 2026-11-25 20:00:00 +0900
categories: [전산학, 운영체제]
tags: [sigpipe, pipefail, strace]
---

`yes | head -1`처럼 앞 명령이 끝없이 출력하는데 뒤 명령이 한 줄만 읽고 끝나면, 앞 명령은 **시그널 13번(SIGPIPE)에 죽고 종료 코드는 141**이 된다. 141은 `128 + 13`이다. 에러가 아니라 "읽는 쪽이 사라졌으니 그만 써라"는 커널의 통지다. 파이썬은 이 시그널을 기본으로 무시해서 대신 `BrokenPipeError: [Errno 32] Broken pipe`를 낸다.

> 실행 환경: Linux 6.18.44, GNU bash 5.2.21, GNU coreutils 9.4, Python 3.11.18, strace. 다른 환경에서는 다를 수 있다.
{: .prompt-info }

## 1. 종료 코드 141 보기

`PIPESTATUS`는 파이프의 각 명령이 낸 종료 코드를 배열로 준다.

```console
$ bash -c 'yes | head -1; echo "PIPESTATUS=${PIPESTATUS[@]}"'
y
PIPESTATUS=141 0
```

`head`는 한 줄(`y`)을 읽고 정상 종료(0)했다. `yes`는 읽는 쪽이 없어진 파이프에 계속 쓰다가 141로 끝났다. 파이프라인 전체의 `$?`는 마지막 명령 값이라 평소엔 0이다.

```console
$ bash -c 'yes | head -1 >/dev/null; echo "rc=$?"'
rc=0
$ bash -c 'set -o pipefail; yes | head -1 >/dev/null; echo "pipefail rc=$?"'
pipefail rc=141
```

그래서 스크립트에 `set -o pipefail`을 켜면, 멀쩡히 동작한 `... | head -1`이 갑자기 실패(141)로 잡힌다. `set -e`와 같이 쓰면 스크립트가 거기서 멈춘다.

## 2. 커널이 한 일: strace

`write` 시스템 콜만 추적해 봤다.

```console
$ strace -f -e trace=write -o st.txt bash -c 'yes | head -1 >/dev/null'
$ grep -E 'SIGPIPE|EPIPE|exited|killed' st.txt
369   <... write resumed>)              = -1 EPIPE (Broken pipe)
369   --- SIGPIPE {si_signo=SIGPIPE, si_code=SI_USER, si_pid=369, si_uid=0} ---
369   +++ killed by SIGPIPE +++
370   +++ exited with 0 +++
```

순서는 이렇다. 읽는 쪽(`head`, 370)이 종료해 파이프의 읽기 끝이 모두 닫힌다. 쓰는 쪽(`yes`, 369)의 `write`는 `EPIPE`로 실패하고, 동시에 SIGPIPE가 전달된다. 시그널을 따로 처리하지 않았으니 기본 동작인 종료가 일어난다. 쉘은 "SIGPIPE로 죽음"을 `128 + 시그널 번호`로 보고한다. 번호는 `kill -l 13`으로 `PIPE`임을 확인할 수 있다. 시그널과 `EPIPE`는 [signal(7)](https://man7.org/linux/man-pages/man7/signal.7.html)과 [pipe(7)](https://man7.org/linux/man-pages/man7/pipe.7.html) man 페이지에 정의돼 있다.

## 3. 파이썬은 왜 다르게 보이나

```console
$ python3 -c "import signal;print(signal.getsignal(signal.SIGPIPE))"
1
$ python3 -c "
for i in range(10**6): print(i)" | head -1
0
Traceback (most recent call last):
  File "<string>", line 3, in <module>
BrokenPipeError: [Errno 32] Broken pipe
```

`getsignal`이 `1`, 즉 `SIG_IGN`(무시)이다. 파이썬은 시작할 때 SIGPIPE를 무시로 바꾼다([signal 문서](https://docs.python.org/3/library/signal.html#note-on-sigpipe)). 그래서 죽지 않고 `write`의 `EPIPE`가 예외가 된다. 이때 종료 코드는 1이다(`PIPESTATUS=1 0`).

기본 동작으로 되돌리면 `yes`와 같아진다.

```console
$ python3 -c "
import signal
signal.signal(signal.SIGPIPE, signal.SIG_DFL)
for i in range(10**6): print(i)" | head -1
0
$ echo "PIPESTATUS=${PIPESTATUS[@]}"
PIPESTATUS=141 0
```

## 판별법: 141은 고장이 아니다

| 보이는 것 | 뜻 |
|---|---|
| 종료 코드 141, 앞 명령 | 읽는 쪽이 먼저 끝났다. `head`, `grep -m1`, `less`에서 `q` 등 |
| `BrokenPipeError: [Errno 32]` | 파이썬이 같은 상황을 예외로 받았다 |
| 뒤 명령도 비정상 | 그때는 진짜 문제. `PIPESTATUS` 전체를 본다 |

`pipefail` 환경에서 일부러 앞부분만 읽는 파이프라인이라면, `|| true`로 덮기보다 `PIPESTATUS`로 141만 허용하는 편이 다른 실패를 숨기지 않는다.
