---
title: "파일을 지웠는데 df 용량이 그대로인 이유: 열려 있는 파일은 unlink로 안 사라진다"
description: "rm으로 200MB 파일을 지웠는데 df 사용량이 그대로였다. 프로세스가 파일을 열고 있으면 inode가 살아 있고, /proc/PID/fd와 lsof +L1로 찾아 fd를 비우면 공간이 돌아온다."
date: 2026-11-11 20:00:00 +0900
categories: [전산학, 운영체제]
tags: [unlink, lsof, proc, 파일-디스크립터]
---

**결론:** `rm`은 파일 *이름*(디렉터리 항목)을 지울 뿐이다. 파일 내용이 차지한 공간은 그 파일을 가리키는 이름이 하나도 없고 **열고 있는 프로세스도 없을 때** 비로소 돌려받는다. 프로세스가 열어 둔 채라면 `ls`에서는 사라져도 `df`는 그대로다. 공식 문서의 표현은 이렇다.

> If that name was the last link to a file, but any processes still have the file open, the file will remain in existence until the last file descriptor referring to it is closed.
>
> — [unlink(2)](https://man7.org/linux/man-pages/man2/unlink.2.html)

> 환경: Linux 6.18.44 (샌드박스), ext4, Python 3.11, 2026-11 기준. 아래 출력은 모두 이 환경에서 직접 돌린 것이다.

## 재현: 지웠는데 df가 안 변한다

200MB 파일을 만들고, 파이썬 프로세스가 읽기용으로 열어 둔 채 `rm`했다.

```console
$ dd if=/dev/zero of=big.bin bs=1M count=200 status=none
$ df -m . | tail -1        # rm 전
/dev/vda          258020  8845     30527  23% /
$ rm big.bin
$ df -m . | tail -1        # rm 후
/dev/vda          258020  8845     30527  23% /
$ du -sm /tmp/t            # 디렉터리 합계는 줄었다
1	/tmp/t
```

`du`는 디렉터리 항목을 따라 걸으며 합산하므로 1MB로 줄었지만, `df`는 파일시스템이 기록한 사용 블록 수를 그대로 읽으므로 안 변했다. **`du`와 `df`가 어긋나는 것이 이 증상의 신호**다.

## 판별법: 열린 채 지워진 파일 찾기

프로세스가 열고 있는 파일은 `/proc/<PID>/fd/`에 심볼릭 링크로 보이고, 지워진 파일은 링크 대상 끝에 `(deleted)`가 붙는다. ([proc(5)](https://man7.org/linux/man-pages/man5/proc.5.html))

```console
$ ls -l /proc/298/fd | grep big
lr-x------ 1 root root 64 Nov 11 11:20 3 -> /tmp/t/big.bin (deleted)
$ stat -L -c 'size=%s links=%h inode=%i' /proc/298/fd/3
size=209715200 links=0 inode=679975
```

`links=0`인데 크기는 200MB(209715200바이트) 그대로다. 이름은 없고 inode와 데이터 블록만 남은 상태다. 시스템 전체에서는 `lsof +L1`(링크 수가 1 미만인 열린 파일)이 한 번에 찾아 준다.

```console
$ lsof +L1 -p 325
COMMAND PID USER   FD   TYPE DEVICE  SIZE/OFF NLINK   NODE NAME
python3 325 root   3w   REG  254,0 209715200     0 679980 /tmp/t/log.bin (deleted)
```

흔한 실제 사례는 로그 파일이다. 실행 중인 서버의 로그를 `rm`하면 서버는 계속 그 fd에 쓰고, 공간은 서버가 재시작될 때까지 안 돌아온다.

## 공간 돌려받기

프로세스를 종료하면 fd가 닫히며 공간이 반환된다. 첫 번째 실험에서 프로세스를 `kill`한 뒤 사용량이 `8845 → 8645`(MB)로 200MB 줄었다.

종료할 수 없다면 쓰기용으로 열린 fd의 내용을 비울 수 있다. 같은 파일을 쓰기로 열어 둔 프로세스(`3w`)에 대해 `/proc`의 fd 경로를 잘랐다.

```console
$ : > /proc/325/fd/3
$ df -m /tmp/t | tail -1
/dev/vda          258020  8645     30727  23% /
```

사용량이 8845 → 8645MB로 줄었다.

> 이 방법은 프로세스가 아직 그 파일에 쓰고 있을 수 있다는 점을 감수해야 한다. 잘린 뒤에도 프로세스는 자기 오프셋부터 계속 쓰므로, 로그 용도가 아니면 데이터가 어긋난다. 읽기용 fd(`3r`)는 잘라도 의미가 없다. 쓰기 권한이 없어 실패할 수도 있다.
{: .prompt-warning }

## 정리

| 증상 | 확인 | 의미 |
|---|---|---|
| `du`는 줄었는데 `df`는 그대로 | `lsof +L1` 또는 `ls -l /proc/*/fd \| grep deleted` | 지워진 파일을 누가 열고 있다 |
| 위 결과가 비어 있다 | `df -i`로 inode 확인, 다른 마운트인지 확인 | 열린 파일 문제가 아니다 |

두 번째 행은 이번에 재현하지 않았으므로 확인 방향만 적었다.
