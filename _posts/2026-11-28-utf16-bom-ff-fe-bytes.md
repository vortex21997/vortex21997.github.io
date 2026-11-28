---
title: "파일 맨 앞의 FF FE는 무엇인가: UTF-16과 BOM을 바이트로 보기"
description: "UTF-16 파일은 ff fe로 시작하고 글자마다 00이 끼어 있다. BOM이 바이트 순서를 알리는 표식이라는 것, UTF-8에 붙은 ef bb bf가 일으키는 문제, 이모지가 4바이트가 되는 서로게이트 계산을 Python과 iconv로 확인한다."
date: 2026-11-28 20:00:00 +0900
categories: [전산학, 컴퓨터 구조]
tags: [utf-16, bom, 문자인코딩]
---

UTF-16 파일은 맨 앞 두 바이트가 `ff fe`(또는 `fe ff`)이고, ASCII 글자 뒤에 `00`이 하나씩 붙는다. 앞의 두 바이트는 **BOM(Byte Order Mark)**, 즉 "이 파일의 2바이트 단위는 어느 쪽 바이트가 먼저인가"를 알리는 표식이다. 글자 `U+FEFF`를 파일 맨 앞에 적어 두고, 읽는 쪽이 그것이 `ff fe`로 보이는지 `fe ff`로 보이는지로 순서를 판별한다. 바이트 순서 자체는 [엔디언 글](/posts/endianness-0x12345678-bytes/)에서 다뤘고, UTF-8의 바이트 배치는 [UTF-8 글](/posts/utf8-hangul-3-bytes-len/)에서 다뤘다.

> 환경: Python 3.11.18, GNU bash 5.2.21, iconv (GNU libc 2.39), Linux x86_64, `LC_ALL=C.UTF-8`.
{: .prompt-info }

## 같은 문자열, 인코딩별 바이트

`한`, `A`, 이모지 `😀`(U+1F600) 세 글자를 인코딩별로 찍었다.

```python
s = "한A😀"
for enc in ["utf-16-le", "utf-16-be", "utf-16", "utf-8-sig", "utf-8"]:
    print(enc, s.encode(enc).hex(' '))
```

```
utf-16-le 5c d5 41 00 3d d8 00 de
utf-16-be d5 5c 00 41 d8 3d de 00
utf-16 ff fe 5c d5 41 00 3d d8 00 de
utf-8-sig ef bb bf ed 95 9c 41 f0 9f 98 80
utf-8 ed 95 9c 41 f0 9f 98 80
```

- `한`은 U+D55C이다. little-endian은 낮은 바이트부터 `5c d5`, big-endian은 `d5 5c`로 적는다.
- `utf-16`(순서를 지정하지 않은 것)은 앞에 `ff fe`를 붙이고 little-endian으로 썼다. 이 출력은 x86_64 환경에서 나온 것이다.
- `A`는 U+0041이라 `41 00`이 된다. ASCII 텍스트에 `00`이 끼어 보이는 이유가 이것이다.
- `utf-8-sig`는 UTF-8 앞에 `ef bb bf`를 붙인 것이다. 같은 U+FEFF를 UTF-8로 적으면 이 세 바이트가 된다.

BOM 상수는 `codecs`에 있다.

```python
import codecs
print(codecs.BOM_UTF16_LE.hex(' '), codecs.BOM_UTF16_BE.hex(' '), codecs.BOM_UTF8.hex(' '))
```

```
ff fe fe ff ef bb bf
```

BOM을 UTF-16에 쓰는 규칙은 [RFC 2781](https://www.rfc-editor.org/rfc/rfc2781)(UTF-16)에, UTF-8의 바이트 배치는 [RFC 3629](https://www.rfc-editor.org/rfc/rfc3629)에 있다.

## 이모지가 4바이트인 이유: 서로게이트

16비트 하나로는 U+FFFF까지만 적을 수 있다. 그 위의 문자는 16비트 두 개(서로게이트 쌍)로 나눠 적는다. U+1F600으로 계산하면:

```python
cp = 0x1F600 - 0x10000
print(hex(0xD800 + (cp >> 10)), hex(0xDC00 + (cp & 0x3FF)))
```

```
0xd83d 0xde00
```

위 little-endian 출력의 `3d d8 00 de`가 정확히 이 `d83d`, `de00`을 낮은 바이트부터 적은 것이다.

## 판별: BOM이 있는데 도구가 못 읽는 두 경우

UTF-16으로 `echo hi`를 저장해 `od`로 봤다.

```
 ff fe 65 00 63 00 68 00 6f 00 20 00 68 00 69 00
 0a 00
```

**경우 1: UTF-8 도구가 UTF-16 파일을 읽는 경우.** 이 파일을 bash로 실행하면 이렇게 된다.

```
$ bash u16.txt
/bin/bash: line 29: /tmp/u16.txt: cannot execute binary file
```

UTF-8로 디코딩하면 첫 바이트부터 실패한다.

```
'utf-8' codec can't decode byte 0xff in position 0: invalid start byte
```

`ff`는 UTF-8에서 어떤 문자의 첫 바이트로도 쓰이지 않는 값이다. 그래서 첫 바이트가 `ff`/`fe`면 UTF-16일 가능성을 먼저 의심하면 된다. 읽는 쪽이 `00` 사이사이 문자를 `e\0c\0h\0o`로 받아 깨져 보이는 것도 같은 원인이다. 변환은 `iconv`로 한다.

```
$ iconv -f UTF-16 -t UTF-8 u16.txt
echo hi
```

**경우 2: UTF-8인데 BOM이 붙은 경우.** 첫 바이트가 `ef bb bf`이다. 셸 스크립트 앞에 이것이 붙은 파일을 실행해 봤다.

```
$ od -An -tx1 -N8 bom8.sh
 ef bb bf 23 21 2f 62 69
$ ./bom8.sh
./bom8.sh: line 1: ﻿#!/bin/bash: No such file or directory
hi
```

커널은 파일이 정확히 `#!`로 시작할 때만 인터프리터를 찾는다. BOM 때문에 첫 줄이 `#!/bin/bash`로 인식되지 않아 실행이 실패했고, bash가 대신 파일을 스크립트로 읽으면서 첫 줄을 존재하지 않는 명령 이름으로 보았다. 이 실행에서는 둘째 줄의 `echo hi`는 돌아서 종료 코드가 0이었다. **오류 메시지가 나왔는데 결과는 정상**이라 놓치기 쉽다. 이 동작은 위 환경에서 확인한 것이며, 셸이나 호출 방식이 다르면 달라질 수 있다.

## 같은 U+FEFF가 남는 경우

`iconv`에 방향을 지정해 버리면 BOM이 글자로 남는다.

```
$ iconv -f UTF-16LE -t UTF-8 u16.txt | od -An -tx1
 ef bb bf 65 63 68 6f 20 68 69 0a
```

`UTF-16`은 BOM을 순서 표식으로 소비하고, `UTF-16LE`는 순서가 이미 정해졌다고 보아 BOM을 **글자 U+FEFF**로 그대로 내보낸다. Python도 같다.

```python
open('u16.txt','rb').read().decode('utf-16le')[:3].encode('unicode_escape')
# b'\\ufeffec'
```

앞에서 본 `ef bb bf`가 UTF-8 파일에 들어가는 한 가지 경로가 이것이다.

## 정리

| 파일 앞 바이트 | 의미 |
|---|---|
| `ff fe` | UTF-16 little-endian (BOM) |
| `fe ff` | UTF-16 big-endian (BOM) |
| `ef bb bf` | UTF-8 BOM (U+FEFF를 UTF-8로 적은 것) |

이 표는 위에서 직접 만든 샘플과 RFC 2781, 3629를 근거로 한 것이며, UTF-32 등 다른 BOM은 확인하지 않았다.
