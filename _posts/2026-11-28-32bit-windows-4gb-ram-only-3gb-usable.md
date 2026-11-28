---
title: "램을 4GB 꽂았는데 3GB대만 보이는 이유: 32비트가 셀 수 있는 주소는 4GiB까지다"
description: "32비트 운영체제에서 램이 3GB대로 보이는 까닭을 주소 계산과 리눅스 /proc/iomem 출력으로 확인한다. 장치가 4GiB 아래 주소를 차지해 램이 그 위로 밀려난다."
date: 2026-11-28 13:00:00 +0900
categories: [컴퓨터 기초, 하드웨어]
tags: [32비트, 주소공간, proc]
---

오래된 PC에 램을 4GB 꽂았는데 "설치된 메모리 4GB (사용 가능 3.xGB)"로 뜨는 경우가 있다. **32비트 운영체제는 번호를 32비트로만 적을 수 있어서, 메모리 칸을 4GiB(약 4.29GB)까지만 가리킬 수 있다.** 그런데 그 4GiB 안에는 그래픽 카드 같은 장치의 몫도 같이 들어 있어서, 램이 쓸 수 있는 자리는 그만큼 줄어든다.

## 주소는 메모리 칸의 번호다

램의 1바이트마다 번호(주소)가 붙어 있고, 프로세서는 그 번호로 위치를 찾는다. 번호를 32비트로 적으면 만들 수 있는 번호는 2³²개다.

```console
$ python3 -c 'print(2**32, 2**32/2**30)'
4294967296 4.0
```

2³² = 4,294,967,296개, 칸 하나가 1바이트이므로 4.0GiB다. 64비트 쪽은 계산이 다르다. 실제 CPU는 64비트 전부를 쓰지 않고 일부만 쓴다.

```console
$ grep -m1 address /proc/cpuinfo
address sizes	: 52 bits physical, 57 bits virtual
```

(이 샌드박스: Intel Xeon 2.30GHz, x86_64, 리눅스 6.18, 램 약 16GiB. 다른 CPU는 값이 다르다.) 물리 주소 52비트면 2⁵² 바이트, 4,096TiB까지 가리킬 수 있어서 4GiB 한계와는 거리가 멀다.

## 4GiB 안에는 장치도 산다

주소 공간은 램만의 것이 아니다. 그래픽 카드·PCI 장치도 자기 메모리나 제어 레지스터를 같은 번호표 위에 올린다. 이 리눅스 머신의 주소 배치를 직접 봤다. (`/proc/iomem`은 커널이 주소 범위별 용도를 적어 둔 파일이고, 읽으려면 보통 root 권한이 필요하다.)

```console
$ grep -E '^[0-9a-f]+-[0-9a-f]+ : (System RAM|PCI|Reserved)' /proc/iomem
00000000-00000fff : Reserved
00001000-0009fbff : System RAM
0009fc00-000fffff : Reserved
00100000-bfffffff : System RAM
c0001000-eebfffff : PCI Bus 0000:00
eec00000-febfffff : Reserved
100000000-43fffffff : System RAM
4000000000-7fffffffff : PCI Bus 0000:00
```

읽는 법은 이렇다.

- `00100000-bfffffff : System RAM` — 램은 0번지부터 `0xc0000000`(= 3.0GiB) 직전까지.
- `c0001000-eebfffff : PCI Bus`, `eec00000-febfffff : Reserved` — 3GiB부터 4GiB 직전까지는 장치가 차지한 구간이다.
- `100000000-43fffffff : System RAM` — 4GiB(`0x100000000`) 이상에서 램이 다시 시작한다. 가려진 구간만큼의 램이 위쪽으로 옮겨 놓인 것이다.

이 머신은 64비트라서 4GiB 위의 램도 다 쓴다. 32비트 운영체제는 그 위쪽 주소를 적을 수 없다. 그래서 4GiB 아래에서 장치 몫을 뺀 나머지(여기서는 0~3GiB 구간)만 보이게 된다. 장치 구간 크기는 장치 구성에 따라 다르므로 "항상 3GB"가 되는 것은 아니다. 그래서 화면에 3.2GB, 3.5GB처럼 제각각 뜬다.

## 같은 말이 공식 문서에도 있다

Microsoft의 [메모리 한도 문서](https://learn.microsoft.com/en-us/windows/win32/memory/memory-limits-for-windows-releases) (문서 갱신 2025-06 기준)는 Windows 10 32비트(x86) 모든 에디션의 물리 메모리 한도를 4GB로 적는다. 같은 문서의 "How graphics cards and other devices affect memory limits" 절에는 다음 취지의 설명이 있다.

> Devices have to map their memory below 4 GB for compatibility with non-PAE-aware Windows releases. Therefore, if the system has 4GB of RAM, some of it is either disabled or is remapped above 4GB by the BIOS. If the memory is remapped, X64 Windows can use this memory. X86 client versions of Windows don't support physical memory above the 4GB mark, so they can't access these remapped regions.

위 `/proc/iomem`에서 본 "4GiB 위로 다시 시작하는 램"이 바로 문서가 말하는 remapped 구간이다. 이 문서에서 읽은 내용이고, Windows에서 직접 돌려 확인한 것은 아니다.

> 64비트 Windows 11 Home은 같은 문서 기준 한도가 128GB라서, 일반 가정용 PC에서는 이 한계를 만날 일이 거의 없다.
{: .prompt-info }

## 판별법: 내 PC가 이 경우인지

| 보이는 것 | 의미 |
|---|---|
| 운영체제가 32비트, 설치 4GB 이상, 사용 가능 3.xGB | 이 글의 경우. 64비트 운영체제로 바꿔야 4GB 위를 쓴다 |
| 운영체제가 64비트인데 설치 용량보다 조금 적게 보임 | 내장 그래픽 등이 램 일부를 예약한 것이다. 다른 이유다 |

운영체제 비트 수는 Windows 설정의 시스템 정보에서 "시스템 종류"로 볼 수 있다. 램을 더 사도 소용이 없고, 운영체제가 64비트여야 한다.
