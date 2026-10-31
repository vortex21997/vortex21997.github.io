---
title: "파일 확장자를 .png에서 .txt로 바꾸면 파일이 바뀌나"
description: "확장자는 파일 이름의 일부일 뿐이라 내용은 그대로입니다. 이름만 바꾼 파일을 해시와 첫 바이트로 비교하고, 프로그램이 확장자 대신 무엇을 보는지 확인했습니다."
date: 2026-10-31 13:00:00 +0900
categories: [컴퓨터 기초, 파일·운영체제]
tags: [확장자, file-명령어, 매직-넘버]
---

**바뀌지 않습니다.** 확장자(`.png`, `.txt` 같은 파일 이름 끝부분)를 고치면 이름만 달라지고 안에 든 바이트는 한 개도 변하지 않습니다. 사진을 `.txt`로 바꾼다고 글자 파일이 되지 않고, 메모장으로 열면 깨진 글자만 보입니다. 파일 형식을 실제로 바꾸려면 그 형식으로 다시 저장(변환)해야 합니다.

## 직접 확인

1×1 픽셀짜리 PNG 파일을 만들고, 복사해서 이름만 `.txt`, `.jpg`로 붙였습니다. (Linux 6.18, `file` 5.45에서 실행)

```console
$ ls -l
-rw-r--r-- 1 root root 69 Oct 31 04:13 photo.jpg
-rw-r--r-- 1 root root 69 Oct 31 04:13 photo.png
-rw-r--r-- 1 root root 69 Oct 31 04:13 photo.txt

$ cmp photo.png photo.txt && echo same
same

$ sha256sum photo.png photo.txt | cut -c1-16
b1ff9c8ea3a780ba
b1ff9c8ea3a780ba
```

크기도 69바이트로 같고, 내용을 비교하는 `cmp`도 "같다"고 답하며, 해시(내용의 지문 같은 값)도 같습니다. 이름만 다른 같은 파일입니다.

## 그럼 프로그램은 무엇을 보고 형식을 아나

`file` 명령은 확장자를 보지 않고 **파일 맨 앞 몇 바이트**를 봅니다.

```console
$ file photo.*
photo.jpg: PNG image data, 1 x 1, 8-bit/color RGB, non-interlaced
photo.png: PNG image data, 1 x 1, 8-bit/color RGB, non-interlaced
photo.txt: PNG image data, 1 x 1, 8-bit/color RGB, non-interlaced

$ head -c 8 photo.txt | od -An -tx1c
  89  50  4e  47  0d  0a  1a  0a
 211   P   N   G  \r  \n 032  \n
```

`.jpg`, `.txt`라고 이름을 붙였는데도 셋 다 PNG로 나옵니다. 앞 8바이트 `89 50 4e 47 0d 0a 1a 0a`가 PNG의 서명이기 때문입니다([PNG 규격 — File signature](https://www.w3.org/TR/png-3/#5PNG-file-signature)). 이런 앞부분 표식을 흔히 매직 넘버라고 부릅니다. `file`이 이 표식을 규칙 목록과 맞춰 본다는 설명은 [file(1) man 페이지](https://man7.org/linux/man-pages/man1/file.1.html)에 있습니다.

다른 형식도 같았습니다.

```console
$ cp /usr/bin/ls fake.pdf
$ file fake.pdf | cut -c1-80
fake.pdf: ELF 64-bit LSB pie executable, x86-64, version 1 (SYSV), dynamically l
```

실행 파일(`ls`)에 `.pdf`를 붙여도 `file`은 ELF 실행 파일(앞 4바이트 `7f 45 4c 46`)이라고 답합니다.

## 왜 확장자가 있는데도 바꾸면 안 되나

확장자는 운영체제가 "더블클릭하면 어떤 프로그램으로 열까"를 고르는 **힌트**입니다. 힌트를 바꾸면 엉뚱한 프로그램이 열리거나, 열었다가 "손상된 파일"이라는 오류가 납니다. 파일 내용이 그 프로그램이 기대하는 형식이 아니기 때문입니다.

반대로 이름 바꾸기가 **실제로 통하는** 경우도 있습니다. `.docx`는 내부가 ZIP 묶음이라 앞 4바이트가 ZIP 서명(`50 4b 03 04`, 글자로 `PK`)입니다.

```console
$ file d.docx d.zip
d.docx: Zip archive data, at least v2.0 to extract, compression method=store
d.zip: Zip archive data, at least v2.0 to extract, compression method=store

$ unzip -l d.zip | tail -3
        1  2026-10-31 04:13   a.txt
---------                     -------
        1                     1 file
```

여기서는 `.docx`를 `.zip`으로 바꿔 안을 열 수 있습니다. 형식이 변한 게 아니라 원래 ZIP이었기 때문입니다. (위 `d.docx`는 ZIP 구조만 흉내 낸 시험용 파일이라 Word에서 열리는 진짜 문서는 아닙니다.)

> 윈도우·맥은 기본 설정에서 확장자를 숨깁니다. 그래서 `보고서.pdf.exe` 같은 이름이 `보고서.pdf`로만 보일 수 있습니다. 파일 형식이 이름이 아니라 내용으로 정해진다는 점과 함께 기억해 둘 만합니다.
{: .prompt-info }

## 정리

- 이름 바꾸기 = 이름표만 교체. 내용(해시)은 그대로.
- 형식은 파일 앞부분 바이트로 알 수 있고, `file 파일명`으로 확인한다.
- 형식을 바꾸려면 해당 프로그램의 "다른 이름으로 저장/내보내기"로 변환한다.

측정 환경: Linux 6.18.44, file-5.45, Python 3 표준 라이브러리로 시험 파일을 생성.
