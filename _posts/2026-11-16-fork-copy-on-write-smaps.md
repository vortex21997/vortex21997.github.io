---
title: "fork()하면 200MB 메모리가 정말 복사될까: Copy-on-Write를 smaps로 보기"
description: "fork 직후 자식의 Rss는 부모와 같은 205MB지만 Pss는 절반이고, 쓰기를 하는 만큼만 Private_Dirty로 바뀐다. /proc/PID/smaps_rollup으로 Copy-on-Write를 직접 확인했다."
date: 2026-11-16 20:00:00 +0900
categories: [전산학, 운영체제]
tags: [fork, copy-on-write, smaps]
---

결론부터: `fork()`는 메모리를 복사하지 않는다. 부모와 자식이 **같은 물리 페이지를 읽기 전용으로 공유**하다가, 누군가 **쓰는 페이지만** 그때 복사한다(Copy-on-Write). 그런데 `ps`나 `top`의 RSS는 이 공유를 구분하지 못해서 자식이 부모만큼 메모리를 먹는 것처럼 보인다. 구분하려면 `/proc/PID/smaps_rollup`의 `Pss`와 `Private_Dirty`를 봐야 한다.

> 측정 환경: Linux 6.18.44, Python 3.11.18, 4코어, RAM 16GB 샌드박스. 시간 값은 이 환경의 것이며 일반화하지 않는다.
{: .prompt-info }

## 근거

[fork(2) man 페이지](https://man7.org/linux/man-pages/man2/fork.2.html)에서 읽은 문장이다.

- DESCRIPTION: "The child process and the parent process run in separate memory spaces." / "At the time of fork() both memory spaces have the same content."
- NOTES: "Under Linux, fork() is implemented using copy-on-write pages, so the only penalty that it incurs is the time and memory required to duplicate the parent's page tables, and to create a unique task structure for the child."

즉 복사되는 것은 데이터가 아니라 **페이지 테이블**(가상 주소가 어느 물리 페이지인지 적은 표)이다. 각 항목의 정의는 [proc_pid_smaps(5)](https://man7.org/linux/man-pages/man5/proc_pid_smaps.5.html)에 있다. `Pss`는 "the process's proportional share of this mapping"이다. 공유 페이지의 크기를 공유하는 프로세스 수로 나눠 각자에게 배분한 값이다.

## 실험

200MB짜리 익명 메모리를 만들고 모든 페이지를 한 번씩 써서 실제로 할당한 뒤 `fork()`한다. 자식이 그중 절반(100MB)에 쓰기를 한다. 각 단계에서 `/proc/<pid>/smaps_rollup`을 읽는다.

```python
import os, mmap
N = 200 * 1024 * 1024
buf = mmap.mmap(-1, N, flags=mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS)
for i in range(0, N, 4096): buf[i] = 1       # 모든 페이지를 부모가 미리 씀

def mem(pid, label):
    keys = ('Rss', 'Pss', 'Private_Dirty', 'Shared_Dirty')
    with open(f"/proc/{pid}/smaps_rollup") as f:
        d = {l.split(':')[0]: int(l.split()[1]) for l in f if l.split(':')[0] in keys}
    print(label, {k: d[k] // 1024 for k in keys}, "(MB)")
```

(`pipe`로 부모·자식 순서를 맞추는 부분은 생략했다. 단계는 아래 출력의 줄과 같다.)

```
parent before fork           Rss= 207MB Pss= 206MB Private_Dirty= 202MB Shared_Dirty=   0MB
child after fork (no write)  Rss= 205MB Pss= 102MB Private_Dirty=   0MB Shared_Dirty= 202MB
parent while child exists    Rss= 208MB Pss= 104MB Private_Dirty=   0MB Shared_Dirty= 202MB
child after writing 100MB    Rss= 206MB Pss= 153MB Private_Dirty= 100MB Shared_Dirty= 102MB
parent after child wrote     Rss= 208MB Pss= 154MB Private_Dirty= 100MB Shared_Dirty= 102MB
```

읽는 법:

1. **fork 직후**: 자식의 `Rss`가 205MB로 부모와 같다. 하지만 `Private_Dirty`는 0이고 `Shared_Dirty`가 202MB다. 내 페이지가 하나도 없다. 부모도 `Private_Dirty`가 202MB에서 0으로 바뀐다. 같은 페이지가 이제 둘의 공유가 됐기 때문이다. `Pss`는 둘 다 약 100MB로, 202MB를 둘이 반씩 나눠 가진다.
2. **자식이 100MB를 쓴 뒤**: 자식의 `Private_Dirty`가 100MB로 늘고 `Shared_Dirty`는 102MB로 줄었다. 쓴 페이지만 자식 몫으로 복사됐다. `Rss`는 그대로 206MB라서 **RSS만 보면 아무 일도 없었던 것처럼** 보인다.
3. **부모도 같이 바뀐다**: 부모의 `Private_Dirty`도 100MB가 됐다. 자식이 복사해 간 자리의 원본 페이지는 이제 부모만 쓰기 때문이다. 아직 공유 중인 102MB만 `Shared_Dirty`로 남는다.

## 같은 코드가 다르게 나올 때: `MAP_PRIVATE`

처음에 `mmap.mmap(-1, N)`만 썼다가 전혀 다른 값을 얻었다.

```
child after fork (no write)  Rss=   6MB Pss=   2MB Private_Dirty=   0MB Shared_Dirty=   2MB
child after writing 100MB    Rss= 106MB Pss=  53MB Private_Dirty=   0MB Shared_Dirty= 102MB
```

자식의 `Rss`가 6MB에서 시작하고, 100MB를 써도 `Private_Dirty`가 0이다. 직접 확인한 바로는 Python의 `mmap.mmap(-1, N)`이 만든 익명 매핑은 `MAP_SHARED`로 동작했다. 공유 매핑은 Copy-on-Write 대상이 아니라서 자식이 쓴 내용이 부모에게도 그대로 보이고 페이지가 복사되지 않는다. 위 실험은 `flags=MAP_PRIVATE | MAP_ANONYMOUS`를 명시해서 얻은 값이다. "fork하면 메모리가 격리된다"는 말은 **프라이빗 매핑일 때** 성립한다.

## fork가 빠른 이유

복사하는 것이 페이지 테이블뿐이라면 200MB를 다 쓴 프로세스의 `fork()`도 짧아야 한다. `fork()` 호출 시간만 재 보았다(자식은 즉시 `_exit`).

```
fork() 200MB: 2.57 ms
fork() 200MB: 2.71 ms
fork() 200MB: 1.69 ms
```

200MB를 실제로 복사했다면 이 시간에 끝날 수 없다. 다만 이 값은 이 샌드박스에서 세 번 잰 것이다. 메모리가 클수록 페이지 테이블도 커지므로 시간이 어떻게 늘어나는지는 재 보지 않았다.

## 정리

- `fork()` 직후 자식의 RSS가 부모와 같아도 메모리가 두 배가 된 것이 아니다. `Pss`와 `Private_Dirty`가 실제 몫을 보여 준다.
- 복사는 **쓰는 순간, 쓰는 페이지만** 일어난다. 자식이 쓰는 양에 비례해 메모리가 늘어난다.
- 공유 매핑(`MAP_SHARED`)은 이 규칙의 밖이다.

이 글은 "그래서 이론상 이렇다"가 아니라 이 환경에서 위 출력이 나왔다는 기록이다. 다른 커널이나 `fork` 이후 `exec`을 하는 경우는 확인하지 않았다. 좀비 프로세스가 `fork` 뒤에 어떻게 남는지는 [ps에 \<defunct\>로 뜨는 좀비 프로세스](/posts/zombie-defunct-kill-9/)에서 다뤘다.
