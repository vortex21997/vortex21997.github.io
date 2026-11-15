---
title: "같은 드라이브 안에서 파일을 옮기면 순식간인데 다른 드라이브로는 오래 걸리는 이유"
description: "500MB 파일을 같은 폴더 트리 안에서 mv하면 0.002초, 다른 파일시스템으로 mv하면 0.3초가 걸렸다. strace로 보니 앞쪽은 이름만 바꾸는 renameat2 한 번이고, 뒤쪽은 renameat2가 EXDEV로 실패한 뒤 복사하고 원본을 지운다."
date: 2026-11-15 13:00:00 +0900
categories: [컴퓨터 기초, 파일·운영체제]
tags: [mv, rename, inode, strace]
---

**결론:** 같은 드라이브(같은 파일시스템) 안에서 파일을 옮기면 내용은 건드리지 않고 **"이 파일은 이제 저 폴더에 있다"는 목록의 기록만 고친다.** 그래서 파일이 1GB든 1TB든 거의 즉시 끝난다. 다른 드라이브로 옮기면 기록만 고칠 수 없어서 **내용을 통째로 복사한 뒤 원본을 지운다.** 그래서 크기에 비례해 시간이 든다.

> 용어: **파일시스템**은 드라이브 위에 파일과 폴더를 정리해 두는 방식(과 그 결과물)이다. 보통 파티션 하나가 파일시스템 하나다. **inode**는 파일시스템이 파일마다 붙이는 번호표로, 파일의 내용 위치와 크기 같은 정보를 담고 있다.
{: .prompt-info }

## 직접 재 보기

환경: Linux 6.18.44, GNU coreutils 9.4(`mv`), 루트(`/`)는 `/dev/vda`의 ext 계열 파일시스템, `/dev/shm`은 메모리 기반 `tmpfs`. 두 곳은 서로 다른 파일시스템이다. 결과는 환경마다 다르다.

500MB짜리 파일을 만들고, 같은 파일시스템 안의 폴더로 옮겨 본다.

```console
$ dd if=/dev/zero of=big bs=1M count=500
524288000 bytes (524 MB, 500 MiB) copied, 0.270818 s, 1.9 GB/s
$ ls -i big
679975 big
$ time mv big d/big
real	0m0.002s
$ ls -i d/big
679975 d/big
```

옮겼는데 inode 번호가 `679975`로 **그대로**다. 같은 파일이 이름만 바뀐 위치에 놓인 것이다. 시간은 0.002초다.

같은 파일을 이번에는 다른 파일시스템(`/dev/shm`, tmpfs)으로 옮긴다.

```console
$ time mv d/big /dev/shm/big
real	0m0.325s
$ ls -i /dev/shm/big
3 /dev/shm/big
```

inode 번호가 `3`으로 바뀌었다. **새 파일이 만들어진 것**이다. 시간은 0.325초로 약 160배다. 이 샌드박스에서는 디스크가 빨라 0.3초지만, 느린 USB 메모리나 네트워크 드라이브라면 파일 크기 ÷ 쓰기 속도만큼 걸린다.

## 시스템이 실제로 한 일

`strace`(프로그램이 운영체제에 보내는 요청, 즉 시스템 콜을 보여 주는 도구)로 보면 차이가 그대로 나온다. 같은 파일시스템 안:

```console
$ strace -f -e trace=rename,renameat,renameat2 mv big d/big
renameat2(AT_FDCWD, "big", AT_FDCWD, "d/big", RENAME_NOREPLACE) = 0
```

요청 한 번에 성공이다. 다른 파일시스템으로:

```console
$ strace -f -e trace=rename,renameat,renameat2,openat,copy_file_range,sendfile mv /dev/shm/big ./big2
renameat2(AT_FDCWD, "/dev/shm/big", AT_FDCWD, "./big2", RENAME_NOREPLACE) = -1 EXDEV (Invalid cross-device link)
openat(AT_FDCWD, "/dev/shm/big", O_RDONLY|O_NOFOLLOW) = 3
openat(AT_FDCWD, "./big2", O_WRONLY|O_CREAT|O_EXCL, 0600) = 4
copy_file_range(3, NULL, 4, NULL, 9223372035781033984, 0) = -1 EXDEV (Invalid cross-device link)
```

`mv`는 먼저 이름 바꾸기(`renameat2`)를 시도한다. 파일시스템이 다르면 커널이 `EXDEV (Invalid cross-device link)`로 거절한다. 그러면 `mv`는 원본을 열고(`openat`) 새 파일을 만들어(`O_CREAT`) 내용을 복사하는 쪽으로 넘어간다. 위 출력은 `head`로 잘라 낸 것이라 그 뒤 과정(복사가 끝난 뒤 원본 삭제)은 직접 확인하지 못했다. 다만 앞의 시간 측정에서 `/dev/shm`으로 옮긴 뒤 원본 `d/big`이 사라져 있었다는 점은 `mv`의 문서 설명과 맞는다.

이 샌드박스에서는 `copy_file_range`도 `EXDEV`로 실패했는데, 그 뒤에 어떤 방식으로 복사했는지는 이 출력만으로는 알 수 없다. 에러 문자열은 이 둘이 같은 말이지만 **원인 위치가 다르다**는 점만 기억하면 된다. 이름 바꾸기의 `EXDEV`는 "같은 드라이브가 아니니 복사로 가라"는 정상 신호다.

## 이게 일상에서 보이는 모습

- 같은 드라이브의 폴더끼리 드래그하면 용량이 커도 바로 끝나고, 다른 드라이브(C:에서 D:, 내장에서 USB)로 끌면 진행 막대가 뜬다. 같은 "이동"이지만 하는 일이 다르다.
- 이동 도중 전원이 나가면 결과도 다르다. 같은 드라이브 안의 이동은 기록 하나를 고치는 작업이라 대개 "옮겨졌다" 아니면 "그대로"다. 드라이브 간 이동은 복사 중간에 끊기면 **새 쪽에 반쪽짜리 파일이 남을 수 있다.** 이건 `strace` 출력에서 읽은 구조로 한 추론이고, 실제로 전원을 끊어 확인하지는 않았다.
- 폴더 하나에 같은 드라이브처럼 보여도 **그 안에 다른 드라이브가 연결(마운트)된 경우**가 있다. 이름 바꾸기가 `EXDEV`로 실패하면 이 경우다.

## 근거

- `mv` 설명(GNU coreutils): <https://www.gnu.org/software/coreutils/manual/html_node/mv-invocation.html> — 같은 파일시스템이면 이름을 바꾸고, 아니면 복사 후 삭제한다고 서술한다.
- `rename(2)` man 페이지: <https://man7.org/linux/man-pages/man2/rename.2.html> — `EXDEV`는 두 경로가 같은 마운트된 파일시스템에 있지 않을 때 돌려준다.

Windows와 macOS의 탐색기·Finder도 비슷한 원리로 동작한다고 알려져 있지만, 이 글에서는 Linux에서만 직접 확인했다.
