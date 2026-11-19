---
title: "메모리 16GB인데 왜 사진을 더 못 넣나: RAM과 저장공간은 다른 부품이다"
description: "'메모리 16GB'는 작업 책상 넓이(RAM)이고 사진이 쌓이는 곳은 서랍(저장장치)이다. 같은 200MB 파일을 RAM과 디스크에 각각 써서 free와 df 숫자가 어디서 변하는지 확인했다."
date: 2026-11-19 13:00:00 +0900
categories: [컴퓨터 기초, 하드웨어]
tags: [RAM, 저장장치, tmpfs]
---

**사진이 들어가는 곳은 "메모리"가 아니라 "저장공간"이고, 둘은 따로 있는 부품이다.** 스펙표의 "메모리 16GB"는 **RAM**(프로그램이 지금 쓰는 데이터를 잠깐 올려 두는 빠른 작업 공간)의 크기다. 사진·문서·앱을 보관하는 곳은 **저장장치**(SSD, 하드디스크, 스마트폰의 "저장공간")이고, 사진을 더 넣을 수 있는지는 이쪽 남은 용량이 정한다. 비유하면 RAM은 책상 넓이, 저장장치는 서랍이다. 책상이 넓어도 서랍이 가득 차면 물건을 더 못 넣는다.

> 이 글은 `memory`(RAM)와 `storage`(저장장치)를 구분하는 이야기다. RAM 사용량 표시가 90%여도 괜찮은 이유는 [메모리 사용량이 90%로 뜨는데 정말 부족한 걸까](/posts/memory-free-low-but-fine/)에서 다뤘다.
{: .prompt-info }

## 직접 확인: 같은 200MB를 두 곳에 써 보기

리눅스 샌드박스에서 확인했다 (커널 6.18, RAM 16GB, 디스크 252GB). 먼저 두 곳의 크기부터 본다.

```console
$ free -m | head -2
               total        used        free      shared  buff/cache   available
Mem:           16087         457       15612          12         230       15630

$ df -h / /dev/shm
Filesystem      Size  Used Avail Use% Mounted on
/dev/vda        252G  8.9G   31G  23% /
tmpfs            16G     0   16G   0% /dev/shm
```

`free`의 `Mem`이 RAM(16GB)이고, `df`의 `/dev/vda`가 저장장치(252GB)다. 숫자도, 이름도 다른 두 개다. `/dev/shm`은 **RAM 안에 만든 폴더**(tmpfs)라서 크기가 RAM과 같은 16GB로 나온다.

이제 200MB 파일을 RAM 쪽 폴더에 쓴다.

```console
$ dd if=/dev/zero of=/dev/shm/t.bin bs=1M count=200 status=none
$ free -m | awk 'NR==2{print "shared:",$5,"used:",$3,"avail:",$7}'
shared: 212 used: 665 avail: 15421
$ df -h /dev/shm
tmpfs            16G  200M   16G   2% /dev/shm
```

`shared`가 12 → 212MB로 정확히 200MB 늘었다. 파일이 RAM을 차지한 것이다. 이어서 같은 크기의 파일을 디스크에 쓴다.

```console
$ dd if=/dev/zero of=/root/d.bin bs=1M count=200 status=none; sync
$ df -h /root
/dev/vda        252G  9.0G   30G  24% /
```

디스크 `Used`가 8.9G → 9.0G로 늘었다(`df -h`는 소수 첫째 자리까지만 보여 줘서 200MB가 0.1G로 보인다). 이 쪽은 사진을 넣는 쪽이고, RAM 숫자와는 따로 움직인다. 두 파일을 지우면 `shared`는 12MB로 돌아갔다.

> 디스크에 쓴 직후 `free`의 `available`이 15421 → 15411MB로 조금 줄었는데, 이는 방금 쓴 파일을 운영체제가 읽기 속도를 위해 메모리에 잠시 복사해 둔 **캐시**다. 필요하면 바로 비워지는 양이라 "사진이 RAM을 차지한다"는 뜻이 아니다.
{: .prompt-tip }

## 둘의 결정적 차이: 전원을 끄면

리눅스 커널 문서는 tmpfs를 이렇게 설명한다. "Tmpfs is a file system which keeps all of its files in virtual memory.", "If you unmount a tmpfs instance, everything stored therein is lost." ([kernel.org: tmpfs](https://www.kernel.org/doc/html/latest/filesystems/tmpfs.html)) 그 문서는 "no files will be created on your hard drive"라고도 쓴다. 즉 RAM에 둔 파일은 디스크에 남지 않는 임시 파일이다.

이 문서가 직접 말하는 것은 "unmount하면 사라진다"까지다. 전원이 꺼질 때 RAM이 비는 것은 RAM이 전기가 있어야 내용을 유지하는 메모리라는 일반적인 성질에서 나오는 설명이고, 이번 샌드박스에서 재부팅해 확인하지는 않았다.

## 정리: 어느 숫자를 봐야 하나

| 궁금한 것 | 볼 숫자 | 윈도우에서 보는 곳 |
|---|---|---|
| 사진·앱을 더 넣을 수 있나 | 저장장치 남은 용량 | 파일 탐색기 > 내 PC의 드라이브 |
| 여러 프로그램을 동시에 돌려도 버티나 | RAM 크기와 사용량 | 작업 관리자 > 성능 > 메모리 |

저장공간이 가득 찼는데 메모리를 늘려도 해결되지 않는 이유가 이것이다. 사진을 더 넣으려면 파일을 지우거나 외장 저장장치·클라우드를 쓰는 쪽이다.

## 측정 환경

- Linux 6.18.44, RAM 16GB, 디스크 252GB (클라우드 샌드박스 가상 머신), Python 3.11, `dd`·`free`·`df`는 배포판 기본 버전
- 값은 이 환경에서 한 번 잰 것이고, 기기마다 크기는 다르다.
