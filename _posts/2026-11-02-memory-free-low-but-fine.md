---
title: "메모리 사용량이 90%로 뜨는데 정말 부족한 걸까: 캐시와 '사용 가능' 메모리"
description: "사용 중 메모리가 거의 가득 찬 것처럼 보여도 대부분은 파일 캐시라서, 프로그램이 필요하면 바로 돌려준다. 1.5GB 파일을 읽기 전후의 free 출력으로 free와 available의 차이를 확인했다."
date: 2026-11-02 13:00:00 +0900
categories: [컴퓨터 기초, 하드웨어]
tags: [메모리, 캐시, free]
---

**메모리가 "거의 다 찼다"고 나와도 부족하다는 뜻이 아닌 경우가 많다.** 운영체제는 남는 메모리를 놀리지 않고, 읽은 파일의 내용을 보관하는 **파일 캐시**(자주 읽는 파일을 메모리에 남겨 두어 다음에 빠르게 쓰는 공간)로 채워 둔다. 이 캐시는 프로그램이 메모리를 요구하면 곧바로 비워서 내준다. 그래서 봐야 할 숫자는 "비어 있는(free)" 양이 아니라 "쓸 수 있는(available)" 양이다.

## 직접 확인: 1.5GB 파일을 쓰고 읽기

램 16GB짜리 리눅스 샌드박스에서 `free -m`(MB 단위 출력)을 세 번 찍었다. 사이에 1.5GB 파일을 만들고 읽었다.

```console
$ free -m                       # 시작
               total        used        free      shared  buff/cache   available
Mem:           16091         418       15653          15         235       15672

$ dd if=/dev/urandom of=/tmp/big.bin bs=1M count=1500 status=none; sync
$ free -m                       # 파일을 쓴 직후
               total        used        free      shared  buff/cache   available
Mem:           16091         454       14105          15        1773       15636

$ rm /tmp/big.bin
$ free -m                       # 파일을 지운 뒤
               total        used        free      shared  buff/cache   available
Mem:           16091         427       15650          15         235       15663
```

- `free`는 15653 → 14105MB로 **약 1.5GB 줄었다.** 작업 관리자식 "사용량" 그래프를 free 기준으로 그리면 이때 사용량이 늘어난 것으로 보인다.
- 늘어난 만큼은 `buff/cache`(235 → 1773MB)로 갔다. 방금 쓴 파일 내용이 캐시에 남은 것이다.
- `available`은 15672 → 15636MB로 **거의 그대로**다. 캐시는 필요하면 비울 수 있어서 "쓸 수 있는 메모리"에 포함되기 때문이다.
- 파일을 지우자 캐시도 같이 사라져 `free`가 원래대로 돌아왔다.

## 두 숫자의 정의

[`free`의 man 페이지](https://man7.org/linux/man-pages/man1/free.1.html)는 두 열을 이렇게 설명한다.

- `free`: "Unused memory" — 말 그대로 아무것도 안 쓰는 메모리.
- `available`: "Estimation of how much memory is available for starting new applications, without swapping" — 스왑(메모리가 모자랄 때 디스크로 내보내는 것) 없이 새 프로그램을 띄울 때 쓸 수 있는 양의 추정치.

커널 문서도 `MemAvailable`을 같은 뜻으로 설명하고, 계산에 `MemFree`, 회수 가능한 슬랩, 파일 목록의 크기 등이 들어간다고 적는다([kernel.org `/proc` 문서](https://www.kernel.org/doc/html/latest/filesystems/proc.html)). `free`는 이 값을 `/proc/meminfo`에서 읽는다.

> 위 출력은 이 글을 쓸 때 돌린 것이다. 확인 환경: Linux 6.18, procps-ng 4.0.4(`free --version`), 램 약 16GB의 샌드박스. 캐시가 얼마나 쌓이는지는 기기와 사용 방식에 따라 다르다.
{: .prompt-info }

## 그러면 언제 진짜 부족한가

- **`available` 자체가 작을 때.** 총량 대비 `available`이 바닥이면 캐시를 다 비워도 모자란 것이다.
- **스왑을 쓰기 시작할 때.** 메모리가 모자라면 디스크로 내보내기 때문에 눈에 띄게 느려진다.

이 글에서는 이 두 상황을 재현하지 않았다. 윈도우 작업 관리자의 "사용 가능"·"캐시됨" 항목이나 macOS 활동 모니터의 "메모리 압력"도 같은 문제를 다루는 화면이지만, 직접 확인하지 못해 수치는 싣지 않는다. 같은 증상으로 보이면 총 사용률 대신 **사용 가능 메모리와 느려짐 여부**를 보는 것이 첫걸음이다.
