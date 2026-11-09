---
title: "파일 크기는 1바이트인데 '디스크 할당 크기'는 4KB로 나오는 이유"
description: "1바이트 파일이 디스크에서는 4KB를 차지하고, 1GB짜리 파일이 0KB를 차지하기도 한다. 크기와 디스크 사용량이 다른 이유를 ls, du, stat 출력으로 확인했다."
date: 2026-11-09 13:00:00 +0900
categories: [컴퓨터 기초, 파일·운영체제]
tags: [디스크 할당 크기, 클러스터, 파일 크기]
---

**파일 속성의 '크기'는 안에 든 내용의 길이이고, '디스크 할당 크기'는 저장장치가 그 파일에 내준 칸(블록)의 총량이다.** 저장장치는 파일을 바이트 단위가 아니라 일정한 크기의 칸 단위로 나눠 주기 때문에, 1바이트짜리 파일도 칸 하나를 통째로 받는다. 반대로 내용 대부분이 빈 파일은 크기보다 훨씬 적게 차지하기도 한다.

> 아래 출력은 Linux 6.18, ext4 파일시스템(칸 크기 4096바이트)에서 직접 돌린 결과다. Windows 속성창의 '크기'와 '디스크 할당 크기'도 같은 구분이지만, 이 글에서 직접 확인한 것은 Linux뿐이다.
{: .prompt-info }

## 1바이트 파일을 만들어 보기

용어를 먼저 풀면, **블록**(Windows에서는 클러스터)은 파일시스템이 저장 공간을 나눠 주는 최소 단위다. 여기서는 4096바이트다.

```bash
printf 'a' > one.txt                                  # 1바이트
head -c 5000 /dev/zero | tr '\0' 'x' > f5000.txt      # 5000바이트
: > empty.txt                                         # 0바이트
ls -l one.txt f5000.txt empty.txt
du -k one.txt f5000.txt empty.txt
```

```
-rw-r--r-- 1 root root    0 Nov  9 04:13 empty.txt
-rw-r--r-- 1 root root 5000 Nov  9 04:13 f5000.txt
-rw-r--r-- 1 root root    1 Nov  9 04:13 one.txt
4	one.txt
8	f5000.txt
0	empty.txt
```

`ls -l`은 내용의 길이(바이트)를, `du -k`는 실제로 할당된 양(KB)을 보여준다.
1바이트는 4KB, 5000바이트는 4096바이트 칸 두 개(8KB), 빈 파일은 0이다.
`stat`으로 보면 이유가 보인다.

```
one.txt size=1 blocks=8 blocksize=512 ioblock=4096
f5000.txt size=5000 blocks=16 blocksize=512 ioblock=4096
empty.txt size=0 blocks=0 blocksize=512 ioblock=4096
```

`blocks`는 512바이트 단위의 개수라서 8 × 512 = 4096바이트다. 리눅스 매뉴얼은 `st_size`를 "the size of the file ... in bytes", `st_blocks`를 "the number of blocks allocated to the file, 512-byte units"로 정의한다([inode(7)](https://man7.org/linux/man-pages/man7/inode.7.html)). 두 값은 처음부터 다른 것을 센다.

## 작은 파일이 많으면 차이가 커진다

1바이트 파일 1000개를 만들어 합쳤다.

```bash
# (내용 길이는 아래 cat으로 확인)
cat small_* | wc -c
du -sk .
```

```
1000
4048
```

내용은 합쳐서 1000바이트인데 할당은 4048KB(약 4MB)다. 같은 폴더에 있던 다른 파일 몇 개가 더해진 값이지만, 1000개 × 4KB = 4000KB가 대부분이다. 작은 파일을 수만 개 가진 폴더가 '크기'보다 '디스크 할당 크기'가 훨씬 큰 이유다.

## 반대로: 1GB인데 0KB

```bash
truncate -s 1G sparse.img
ls -l sparse.img ; du -k sparse.img ; du -k --apparent-size sparse.img
stat -c '%n size=%s blocks=%b' sparse.img
```

```
-rw-r--r-- 1 root root 1073741824 Nov  9 04:13 sparse.img
0	sparse.img
1048576	sparse.img
sparse.img size=1073741824 blocks=0
```

크기는 1GiB인데 할당은 0이다. `truncate`는 길이만 늘리고 데이터를 쓰지 않아서, 파일시스템이 그 구간을 **구멍(hole)**으로 두고 칸을 내주지 않았다. 매뉴얼도 `st_blocks`가 "may be smaller than st_size/512 when the file has holes"라고 적는다. 구멍은 읽으면 0으로 채워져 보인다. 이런 파일을 **희소 파일(sparse file)**이라 부른다.

`du`는 기본이 할당량이고, `--apparent-size`를 주면 크기(내용 길이)를 보여준다. GNU 문서는 이 옵션을 "print apparent sizes rather than device usage"라고 설명하며, 보통은 크기가 더 작지만 구멍·내부 낭비 등으로 반대일 수도 있다고 한다([du(1)](https://man7.org/linux/man-pages/man1/du.1.html)).

## 판별법

| 보고 싶은 것 | 보는 값 | 명령 |
|---|---|---|
| 파일을 복사·전송할 때 옮겨지는 양 | 크기 | `ls -l`, `du --apparent-size` |
| 디스크에서 실제로 차지하는 양 | 할당 크기 | `du`, `stat`의 `blocks` |

- 할당 > 크기: 마지막 칸의 남는 부분이 낭비되는 것(작은 파일일수록 비율이 큼).
- 할당 < 크기: 구멍이 있는 희소 파일일 가능성이 높다.

## 한계

- 칸 크기는 파일시스템과 포맷 설정마다 다르다. 이 글의 4096은 이 샌드박스 ext4의 값이다.
- Windows(NTFS)의 클러스터 크기와 압축 파일 처리는 직접 확인하지 않았다.
