---
title: "'한글'은 2글자인데 파일은 7바이트인 이유: UTF-8에서 한글 한 글자가 3바이트가 되는 과정"
description: "wc -m은 3, wc -c는 7이 나오는 이유를 바이트로 확인한다. 0xD55C(한)가 ed 95 9c가 되는 비트 배치와, 깨진 글자(�)가 생기는 두 가지 경우를 가르는 기준."
date: 2026-11-18 20:00:00 +0900
categories: [전산학, 컴퓨터 구조]
tags: [utf-8, 문자인코딩, wc]
---

`한글`과 줄바꿈 하나만 적은 파일에 `wc -m -c`를 돌리면 글자 수 3, 바이트 수 7이 나온다. 한글 한 글자가 UTF-8에서 **3바이트**이고, 줄바꿈이 1바이트이기 때문이다(3 + 3 + 1 = 7). 3바이트가 되는 규칙은 RFC에 표로 적혀 있고, 아래에서 직접 비트로 풀어 본다.

> 환경: Python 3.11.18, GNU coreutils 9.4 (`wc`), Linux, `LC_ALL=C.UTF-8`.
{: .prompt-info }

## 글자 수와 바이트 수는 다른 숫자다

```console
$ printf '한글\n' > h.txt
$ wc -m -c h.txt
 3 7 h.txt
$ od -An -tx1 h.txt
 ed 95 9c ea b8 80 0a
```

`ed 95 9c`가 `한`, `ea b8 80`이 `글`, `0a`가 줄바꿈이다. **`wc -m`은 로케일이 UTF-8일 때만 글자를 센다.** 같은 파일을 `LC_ALL=C wc -m -c`로 세면 `7 7`이 나온다. C 로케일에서는 바이트 하나를 글자 하나로 보기 때문이다.

## 한 글자가 3바이트가 되는 규칙

UTF-8은 글자 번호(코드 포인트)가 클수록 바이트를 더 쓴다. [RFC 3629](https://www.rfc-editor.org/rfc/rfc3629) 3절의 표다.

```text
0000 0000-0000 007F | 0xxxxxxx
0000 0080-0000 07FF | 110xxxxx 10xxxxxx
0000 0800-0000 FFFF | 1110xxxx 10xxxxxx 10xxxxxx
0001 0000-0010 FFFF | 11110xxx 10xxxxxx 10xxxxxx 10xxxxxx
```

`한`의 코드 포인트는 `U+D55C`이고 `0800-FFFF` 구간이라 3바이트 칸에 들어간다. 이진수 16비트를 `x` 자리에 채우면 된다.

```python
>>> s = "한"
>>> hex(ord(s)), format(ord(s), '016b')
('0xd55c', '1101010101011100')
>>> [format(x, '08b') for x in s.encode()]
['11101101', '10010101', '10011100']
```

```text
1101 010101 011100        ← 코드 포인트를 4 + 6 + 6비트로 자름
1110 1101 | 10 010101 | 10 011100
 ed          95           9c
```

맨 앞 `1110`은 "이 글자는 3바이트다", 뒤의 `10`은 "나는 글자의 중간 바이트다"라는 표시다. 그래서 코드 포인트 16비트가 아니라 표시 8비트가 더해진 24비트(3바이트)가 된다.

글자별로 보면 이렇다.

```python
for t in ["A", "é", "한", "😀"]:
    print(repr(t), hex(ord(t)), len(t.encode('utf-8')), t.encode('utf-8').hex(' '))
```

```text
'A'  0x41     1  41
'é'  0xe9     2  c3 a9
'한' 0xd55c   3  ed 95 9c
'😀' 0x1f600  4  f0 9f 98 80
```

UTF-16은 `한`이 2바이트(`5c d5`, 리틀 엔디언), UTF-32는 모두 4바이트였다. `"한글 abc"`를 인코딩 길이로 비교하면 다음과 같다.

| 인코딩 | 바이트 |
|---|---|
| UTF-8 | 10 |
| UTF-16 (BOM 없음) | 12 |
| EUC-KR / CP949 | 8 |

EUC-KR에서 `한`은 `c7 d1`, 2바이트다. 한글 위주 텍스트는 EUC-KR이 UTF-8보다 작지만, 이 표는 이 문자열 하나의 결과일 뿐 일반화할 수 없다.

## 깨진 글자(�)를 가르는 기준

"깨졌다"는 증상은 같아도 원인은 둘로 갈린다. **바이트가 잘렸는지, 인코딩을 잘못 짐작했는지**다.

**① 바이트가 중간에서 잘린 경우.** `한`의 3바이트 중 앞 2개만 디코딩한다.

```python
>>> b = "한".encode()
>>> b[:2].decode('utf-8')
UnicodeDecodeError: 'utf-8' codec can't decode bytes in position 0-1: unexpected end of data
>>> b[:2].decode('utf-8', errors='replace')
'�'
```

메시지가 `unexpected end of data`이면 데이터가 끝나기 전에 잘렸다는 뜻이다. 고정 길이로 파일을 읽다가 글자 중간에서 끊었을 때 이 오류가 난다.

**② 다른 인코딩의 바이트를 UTF-8로 읽은 경우.** EUC-KR로 저장된 `한`(`c7 d1`)을 UTF-8로 읽는다.

```python
>>> "한".encode('euc-kr').decode('utf-8')
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xc7 in position 0: invalid continuation byte
```

여기서는 `invalid continuation byte`다. `c7`은 2바이트 글자의 시작 표시(`110xxxxx`)인데 뒤따르는 `d1`이 `10xxxxxx` 꼴이 아니라는 뜻이다. 반대로 UTF-8 바이트를 다른 인코딩으로 읽으면 예외 없이 이상한 글자가 나온다.

```python
>>> "한글".encode('utf-8').decode('latin-1')
'íê¸'          # 중간에 제어 문자가 섞여 안 보이는 글자도 있다
>>> "한글".encode('utf-8').decode('cp949', errors='replace')
'�븳湲�'
```

이 경우 오류가 안 나서 더 늦게 발견된다. 판별은 간단하다. **`unexpected end of data`면 잘림, `invalid continuation byte`나 `invalid start byte`면 인코딩 불일치**를 먼저 의심한다.

## 정리

- UTF-8은 코드 포인트 크기에 따라 1~4바이트를 쓰고, 한글(`U+AC00`~`U+D7A3`)은 3바이트 구간이다.
- `wc -c`와 `wc -m`이 다르게 나오면 파일에 ASCII가 아닌 글자가 있다는 뜻이고, `wc -m`은 로케일이 UTF-8이어야 글자를 센다.
- 글자 수 제한이 있는 곳(DB 컬럼 길이, 바이트로 자르는 API)에서는 어느 단위인지부터 확인한다.

로케일이 비어 있을 때 생기는 비슷한 문제는 [html-proofer가 링크 0개를 검사하고 통과한 일]({% post_url 2026-10-28-htmlproofer-zero-links-locale %})에서 다뤘다. 바이트 순서 쪽은 [엔디언 글]({% post_url 2026-11-14-endianness-0x12345678-bytes %})을 본다.
