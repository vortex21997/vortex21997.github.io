---
title: "복사가 끝났다고 떴는데 USB를 '안전하게 제거'해야 하는 이유: 파일은 먼저 메모리에 써진다"
description: "1GiB를 쓰는 데 0.46초(2.3GB/s)가 걸렸지만 그 순간 디스크에 간 건 없었고, Dirty 메모리가 약 1GB 쌓여 있었다. sync로 실제로 내리는 데 0.9초가 더 걸렸다. 복사 완료 표시와 저장 완료가 다른 이유를 dd와 /proc/meminfo로 확인한다."
date: 2026-11-22 13:00:00 +0900
categories: [컴퓨터 기초, 하드웨어]
tags: [쓰기 캐시, fsync, 저장장치]
---

**결론부터.** 파일을 저장하거나 복사하면 운영체제는 내용을 먼저 **메모리**에 적고 "다 썼다"고 답한다. 저장장치에 실제로 내려쓰는 건 그 뒤에 따로 일어난다. 그래서 복사 창이 닫힌 직후에 USB를 뽑으면, 아직 메모리에만 있던 내용이 사라질 수 있다. '안전하게 제거'는 그 남은 내용을 전부 내려쓰게 만드는 버튼이다.

## 직접 확인: 쓰는 속도가 디스크 속도보다 빠르다

1GiB짜리 파일을 `dd`로 쓰고, 그 직후 메모리 상태를 봤다. (`Dirty`는 "메모리에는 있지만 아직 저장장치에 안 쓴 데이터" 양이다.)

환경: Linux 6.18, ext4, 4코어 가상 머신(클라우드 샌드박스). 디스크 종류는 모른다. 아래 수치는 이 환경의 값이고 일반화하지 않는다.

```console
$ grep -E 'Dirty|Writeback:' /proc/meminfo
Dirty:              5840 kB
Writeback:             0 kB
$ dd if=/dev/zero of=a bs=1M count=1024
1073741824 bytes (1.1 GB, 1.0 GiB) copied, 0.462113 s, 2.3 GB/s
$ grep -E 'Dirty|Writeback:' /proc/meminfo
Dirty:           1054468 kB
Writeback:             0 kB
```

`dd`는 0.46초 만에 "끝났다"고 돌아왔는데, 그 시점에 `Dirty`가 약 1GB(1054468 kB)다. 방금 쓴 1GiB가 거의 그대로 메모리에만 있다는 뜻이다. 이어서 `sync`(메모리에 있는 걸 저장장치로 내리라는 명령)를 잰 결과:

```console
$ time sync
real	0m0.925s
$ grep -E 'Dirty|Writeback:' /proc/meminfo
Dirty:                 8 kB
Writeback:             0 kB
```

`sync`가 0.9초를 더 쓰고 나서야 `Dirty`가 8kB로 내려갔다. "쓰기 완료"와 "저장 완료" 사이에 이만큼의 틈이 있었다는 것이다.

## 메모리를 거치지 않으면 느려진다

같은 1GiB를, 내려쓰기가 끝날 때까지 기다리게 해서 다시 쟀다.

```console
$ dd if=/dev/zero of=b bs=1M count=1024 conv=fdatasync
1073741824 bytes (1.1 GB, 1.0 GiB) copied, 1.52674 s, 703 MB/s
$ dd if=/dev/zero of=c bs=1M count=1024 oflag=direct
1073741824 bytes (1.1 GB, 1.0 GiB) copied, 1.10434 s, 972 MB/s
```

`conv=fdatasync`는 끝나기 전에 저장장치로 내려쓰기를 마치게 하는 옵션이고, `oflag=direct`는 메모리 캐시를 거치지 않고 쓰는 옵션이다. 같은 양인데 2.3GB/s가 아니라 703~972MB/s로 나왔다. 앞의 2.3GB/s는 저장장치의 속도가 아니라 **메모리에 복사한 속도**였다. (이 측정은 한 번씩만 돌렸다. 정확한 비율이 아니라 "차이가 있다"는 확인이다.)

## 윈도우도 같은 방식이다

Microsoft 문서는 윈도우가 기본적으로 쓰기 내용을 디스크가 아니라 시스템 파일 캐시에 쓰고(write-back cache), 나중에 운영체제가 정한 간격으로 디스크에 쓴다고 설명한다. 문서에는 갑작스러운 정전 같은 일이 flush 전에 생기면 캐시된 데이터를 잃는다고도 적혀 있다.
[File Caching - Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/fileio/file-caching) (문서 갱신일 2025-03-12, 내가 읽은 시점 2026-11). 윈도우 쪽은 직접 돌려보지 않았고 문서에서 읽은 내용이다.

## 그래서 어떻게 하면 되나

- 외장 저장장치는 뽑기 전에 운영체제의 '안전하게 제거'(리눅스에서는 `sync` 후 `umount`)를 누른다. 이 동작이 남은 내용을 내려쓰고 끝날 때까지 기다려 준다.
- 위 측정에서 밀린 양은 1GiB에 약 1초였다. 느린 USB 메모리나 큰 파일이면 이 틈이 훨씬 길 수 있다. 그 수치는 이 글에서 재지 않았다.
- 장치가 '빠른 제거'로 설정돼 있으면 쓰기 캐시를 쓰지 않도록 운영체제가 조절하기도 한다. 이 설정은 이 글에서 확인하지 않았다.

> 복사 진행 창이 닫힌 것은 "운영체제가 받아 적었다"는 신호이지, "저장장치에 도착했다"는 신호가 아닐 수 있다.
{: .prompt-tip }
