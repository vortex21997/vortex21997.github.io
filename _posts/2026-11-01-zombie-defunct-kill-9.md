---
title: "ps에 <defunct>로 뜨는 좀비 프로세스는 kill -9로도 안 죽는다"
description: "좀비(Z) 프로세스는 이미 죽은 상태라 SIGKILL이 소용없다. fork한 자식을 wait하지 않고 /proc와 ps로 관찰해, 부모가 waitpid를 불러야 사라진다는 것을 확인했다."
date: 2026-11-01 20:00:00 +0900
categories: [전산학, 운영체제]
tags: [zombie, defunct, waitpid, proc]
---

> 2026-11 기준. Linux 6.18, Python 3.11.18, 4 vCPU 샌드박스에서 실행했다.
{: .prompt-info }

`ps`에 `[python3] <defunct>`가 보이고 `kill -9`를 해도 안 사라진다면, 그 프로세스는 **이미 죽어 있다.** 죽은 프로세스는 다시 죽일 수 없다. 남아 있는 건 종료 상태를 부모가 읽어 가길 기다리는 커널의 기록 한 줄이고, 부모가 `wait` 계열 호출을 해야 사라진다. 부모가 그럴 생각이 없다면 부모를 끝내야 한다.

## 직접 만들어 보기

자식을 `fork`하고 종료 코드 3으로 바로 끝나게 한 뒤, 부모는 `wait`하지 않고 상태를 본다.

```python
import os,time,signal
pid=os.fork()
if pid==0: os._exit(3)
time.sleep(0.5)
print("child",pid)
print(open(f"/proc/{pid}/status").read().split("\n")[0:3])
os.system(f"ps -o pid,ppid,stat,comm -p {pid}")
print("cmdline:",repr(open(f"/proc/{pid}/cmdline").read()))
os.kill(pid,signal.SIGKILL)
time.sleep(0.3)
print("after SIGKILL:"); os.system(f"ps -o pid,stat,comm -p {pid}")
print("waitpid:",os.waitpid(pid,0))
print("after wait, exists:",os.path.exists(f"/proc/{pid}"))
```

실제 출력:

```
child 287
['Name:\tpython3', 'State:\tZ (zombie)', 'Tgid:\t287']
  PID  PPID STAT COMMAND
  287   286 Z    python3
cmdline: ''
after SIGKILL:
  PID STAT COMMAND
  287 Z    python3
waitpid: (287, 768)
after wait, exists: False
```

읽을 점은 네 가지다.

- `/proc/287/status`의 `State: Z (zombie)`, `ps`의 `STAT`이 `Z`다. 자식은 코드를 더 실행하지 않는다.
- `/proc/287/cmdline`이 빈 문자열이다. 메모리는 이미 회수됐고 PID와 종료 상태 같은 최소 정보만 남았다.
- `SIGKILL`을 보낸 뒤에도 `Z`가 그대로다. 시그널을 받아 처리할 프로세스 자체가 없다.
- `waitpid`가 `(287, 768)`을 돌려준 뒤에야 `/proc/287`이 사라졌다. `768`은 종료 코드 3이 상위 바이트(`3 << 8`)에 들어간 값이다.

`ps -o args`로 보면 이름 뒤에 `<defunct>`가 붙는다.

```
  PID STAT COMMAND
  303 Z    [python3] <defunct>
```

## 왜 이렇게 설계됐나

[wait(2) man 페이지](https://man7.org/linux/man-pages/man2/wait.2.html)는 이렇게 설명한다. 종료했지만 wait되지 않은 자식은 "zombie"가 되고, 커널은 부모가 나중에 wait로 얻을 수 있도록 PID·종료 상태·자원 사용 정보를 최소한으로 보관한다. 좀비가 쌓이면 프로세스 테이블의 슬롯을 계속 차지한다. 부모가 자식의 종료 코드를 놓치지 않게 하려는 장치라서, 읽어 가기 전에는 지울 수 없다.

## 판별법

`Z`가 보일 때 할 일은 하나다. `ps -o pid,ppid,stat,args -p <PID>`로 `PPID`를 보고 **그 부모**를 본다.

- 부모가 살아 있고 일을 하는 중이면: 부모가 `wait`/`waitpid`를 부르지 않는 버그다. 자식 수만큼 좀비가 쌓인다. 부모 코드를 고치거나 부모를 재시작한다.
- 부모가 종료되면: 좀비는 init 계열 프로세스에 입양되어 정리된다. 이 글에서는 이 경로를 실행해 확인하지 않았다.
- 상태가 `D`(디스크 대기)나 `S`면 좀비가 아니다. 그건 다른 문제다.

이 글에서 확인한 것은 `Z` 상태의 관찰과 `waitpid`로 사라지는 것까지다. 좀비 수가 많을 때의 실제 한계(PID 고갈 시점)는 재 보지 않았다.
