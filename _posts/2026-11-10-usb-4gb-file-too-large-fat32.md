---
title: "USB에 4GB 넘는 파일이 안 들어가는 이유: 빈 공간은 충분한데 'too big'"
description: "USB 메모리 여유 공간이 2GB나 남았는데 4GB 파일이 복사되지 않는 건 용량이 아니라 FAT32 파일 시스템의 파일 크기 한계 때문이다. FAT32 이미지를 만들어 4GiB-1바이트는 들어가고 4GiB는 거부되는 걸 직접 확인했다."
date: 2026-11-10 13:00:00 +0900
categories: [컴퓨터 기초, 하드웨어]
tags: [fat32, exfat, usb]
---

**결론부터:** 빈 공간이 충분한데도 큰 파일이 안 들어가면, 저장장치가 아니라 그 장치에 깔린 **파일 시스템**(저장장치에 파일을 어떤 규칙으로 적어 둘지 정한 방식)의 한계다. 많은 USB 메모리는 FAT32로 포맷되어 나오고, FAT32는 파일 하나가 **4GiB(4,294,967,296바이트)보다 1바이트라도 작아야** 한다. 이 한계는 용량과 무관하다.

## 직접 확인

리눅스 샌드박스에서 6GiB짜리 빈 디스크 이미지를 FAT32로 포맷하고, 크기가 다른 파일 두 개를 넣어 봤다. (`dosfstools 4.2`, `mtools 4.0.43`. 파일은 내용이 비어 있는 희소 파일이고, 이 환경에서만 잰 결과다.)

```bash
truncate -s 6G f.img && mkfs.vfat -F 32 f.img
truncate -s $((4*1024**3-1)) a.bin   # 4GiB - 1바이트
truncate -s $((4*1024**3))   b.bin   # 정확히 4GiB
mcopy -i f.img a.bin ::a.bin
mcopy -i f.img b.bin ::b.bin
```

두 번째 복사의 출력은 이렇다.

```text
File "b.bin" too big
```

그 뒤 `mdir -i f.img ::`로 보면 `a.bin`만 들어가 있고, 이미지에는 **2,134,880,256바이트(약 2GB)가 비어 있었다.** 공간이 모자라서가 아니다. 바이트 하나 차이로 갈렸다.

## 왜 하필 4GiB인가

FAT32는 디렉터리 항목(파일 이름·크기 등을 적어 두는 32바이트짜리 칸)에 파일 크기를 **32비트**로 적는다. 32비트로 표현할 수 있는 최댓값은 2³²−1 = 4,294,967,295다. 위 이미지의 `a.bin` 항목에서 크기 칸을 직접 읽어 보면 정확히 그 값이 나온다.

```text
b'A       BIN' size field bytes ffffffff 4294967295
```

`ffffffff`가 32비트가 꽉 찬 값이다. 1을 더하면 칸에 들어가지 않는다. 같은 원리는 [8비트 정수에서 127 + 1이 -128이 되는 이유](/posts/int8-127-plus-1-minus-128/)에서 비트로 본 적이 있다.

## 해결: 파일 시스템을 바꾼다

반대로 exFAT은 이름처럼 FAT을 확장한 것으로, 파일 크기를 64비트로 적는다. Microsoft 명세는 "The exFAT file system uses 64 bits to describe file size, thereby enabling applications which depend on very large files."라고 설명한다([exFAT specification](https://learn.microsoft.com/en-us/windows/win32/fileio/exfat-specification), 2026-11 확인). 이 샌드박스에는 exFAT 도구가 없어 직접 돌려 보지는 못했고, 문서에서 읽은 내용이다.

> 포맷하면 USB 안의 파일이 전부 지워진다. 먼저 다른 곳에 백업한다.
{: .prompt-warning }

- 윈도우·맥 모두에서 쓴다면 exFAT, 윈도우만 쓴다면 NTFS가 보통 선택지다.
- 오래된 TV·차량 오디오·게임기는 FAT32만 읽는 경우가 있으니, 그 기기에서 쓸 USB라면 설명서를 확인한다.
- 포맷하지 않고 풀려면 파일을 4GiB 미만 조각으로 나눠 옮긴 뒤 합치는 방법이 있다.
