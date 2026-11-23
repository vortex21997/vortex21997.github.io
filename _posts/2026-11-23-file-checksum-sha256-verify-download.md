---
title: "다운로드 페이지에 적힌 긴 SHA-256 값은 뭘 확인하라는 걸까: 1비트만 달라져도 값이 통째로 바뀐다"
description: "10MiB 파일에서 비트 하나만 뒤집어도 SHA-256이 완전히 달라졌고, 이름만 .exe로 바꾼 복사본은 같았다. 체크섬이 잡아내는 것(전송 중 손상)과 못 잡는 것(같은 페이지에서 가져온 값)을 sha256sum으로 확인한다."
date: 2026-11-23 13:00:00 +0900
categories: [컴퓨터 기초, 인터넷·보안]
tags: [체크섬, sha256, 파일 무결성]
---

**결론부터.** 다운로드 페이지에 적힌 64자리 16진수는 **"내가 받은 파일이 올린 파일과 한 비트도 다르지 않은가"**를 확인하는 값이다. 파일 내용에서 계산한 지문(해시)이라서, 내용이 1비트만 달라져도 값이 통째로 바뀐다. 반대로 이름이나 확장자를 바꿔도 값은 그대로다. 다만 이 값이 **파일과 같은 페이지에서** 왔다면, 그 사이트가 뚫렸을 때의 안전까지 보증하지는 않는다.

> 실험 환경: Linux 6.18, GNU coreutils 9.4 `sha256sum`. 파일은 `/dev/urandom`으로 만든 10MiB(10,485,760바이트)입니다.
{: .prompt-info }

## 용어 한 줄

- **해시(hash)**: 파일 내용 전체를 넣으면 정해진 길이의 값이 나오는 계산. SHA-256은 항상 256비트, 16진수로 64자리다.
- **체크섬**: 이런 값으로 파일이 온전한지 확인하는 용도를 부르는 말.

## 1비트만 바꿔 보기

원본 `setup.bin`을 만들고, 5,000,000번째 바이트의 맨 아래 비트 하나만 뒤집은 `flipped.bin`, 이름만 바꾼 `copy-renamed.exe`, 끝 1바이트가 잘린 `trunc2.bin`을 만들어 해시를 앞 16자리만 비교했다.

```console
$ sha256sum *.bin *.exe | awk '{print substr($1,1,16)"…", $2}'
330486ca0aec00c4… flipped.bin
0acf7684b3fe258c… setup.bin
6c53c629b178b193… trunc2.bin
0acf7684b3fe258c… copy-renamed.exe

$ cmp setup.bin flipped.bin
setup.bin flipped.bin differ: char 5000001, line 19466
```

| 파일 | 원본과 차이 | 크기 | 해시 |
|---|---|---|---|
| `copy-renamed.exe` | 이름만 다름 | 같음 | **같다** |
| `flipped.bin` | 1비트 | 같음(10,485,760) | 완전히 다르다 |
| `trunc2.bin` | 끝 1바이트 없음 | 1바이트 작음 | 완전히 다르다 |

`flipped.bin`은 크기가 같아서 폴더에서 보면 구별되지 않는다. 해시를 보지 않으면 파일 크기만으로는 깨진 걸 알 수 없다는 뜻이다. 이름·확장자는 해시에 영향이 없다는 점은 [확장자를 바꾸면 파일이 바뀌나]({% post_url 2026-10-31-rename-extension-changes-file %})에서 본 것과 같다.

## 페이지의 값과 비교하기

게시된 값을 파일로 두고 `-c`(check)로 비교한다. 형식은 `해시  파일이름`(공백 두 칸)이다.

```console
$ echo "$(cat setup.sha256)  copy-renamed.exe" | sha256sum -c
copy-renamed.exe: OK
$ echo "$(cat setup.sha256)  flipped.bin" | sha256sum -c
flipped.bin: FAILED
sha256sum: WARNING: 1 computed checksum did NOT match
$ echo $?
1
```

`FAILED`가 나오면 그 파일을 쓰지 말고 다시 받는다. Windows에서는 PowerShell의 `Get-FileHash 파일경로 -Algorithm SHA256`이 같은 일을 한다. [공식 문서](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/get-filehash)에 따르면 알고리즘을 생략하면 기본값이 SHA256이다. 출력의 `Hash`가 페이지의 값과 같은지 눈으로 비교하거나 `-eq`로 비교하면 된다.

## 이 값이 잡는 것과 못 잡는 것

- **잡는다:** 전송 중 끊김, 저장 중 손상, 불완전한 이어받기처럼 **우연한 변형**. 위 실험의 `flipped.bin`, `trunc2.bin`이 그런 경우다.
- **못 잡을 수 있다:** 파일을 바꾼 사람이 **같은 페이지의 해시값도 함께** 바꿔 두었다면 비교는 `OK`가 나온다. 이건 위 실험으로 확인한 게 아니라 구조에서 나오는 한계다. 해시는 "두 파일이 같은가"만 알려 줄 뿐 "누가 올렸는가"는 알려 주지 않는다.
  그래서 값은 파일과 **다른 경로**(공식 릴리스 노트, 별도 도메인)에서 가져오는 편이 의미가 있다.
- Microsoft 문서도 MD5와 SHA1은 안전하지 않다고 보고 "단순한 변경 확인"에만 쓰라고 한다. 게시된 값이 SHA-256이면 SHA-256으로 비교한다.

> 확인 범위: 위 표와 출력은 이 샌드박스에서 직접 돌린 결과다. Windows의 `Get-FileHash` 동작은 직접 실행하지 않고 공식 문서(PowerShell 7.6 문서, 2026-11 확인)에서 읽은 내용이다.
{: .prompt-warning }
