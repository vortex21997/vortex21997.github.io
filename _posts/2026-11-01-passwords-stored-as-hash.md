---
title: "사이트는 내 비밀번호를 그대로 저장할까: 해시와 솔트로 보기"
description: "제대로 만든 사이트는 비밀번호 원문이 아니라 해시를 저장한다. 같은 비밀번호도 솔트가 다르면 해시가 다르다는 것과, 빠른 해시가 비밀번호에 부적합한 이유를 직접 돌려 확인했다."
date: 2026-11-01 13:00:00 +0900
categories: [컴퓨터 기초, 인터넷·보안]
tags: [해시, 솔트, pbkdf2]
---

**제대로 만든 사이트는 비밀번호 원문을 저장하지 않는다.** 원문 대신 **해시**(입력을 일정 길이의 값으로 바꾸는 한 방향 계산의 결과)를 저장하고, 로그인할 때 입력한 비밀번호를 같은 방식으로 계산해 값이 같은지만 본다. 그래서 "비밀번호 찾기"에서 원래 비밀번호를 알려 주지 않고 재설정하게 하는 사이트가 정상이다. 원문을 메일로 보내 주는 사이트는 원문을 갖고 있다는 뜻이다.

> 2026-11 기준. 아래 수치는 Python 3.11.18, 리눅스 샌드박스(4코어, 단일 스레드로 측정)에서 직접 잰 값이다. 기기마다 다르다.
{: .prompt-info }

## 해시는 이렇게 생겼다

Python 표준 라이브러리 [`hashlib`](https://docs.python.org/3/library/hashlib.html)로 `hunter2`의 SHA-256 해시를 구했다.

```python
import hashlib
pw = b"hunter2"
print(hashlib.sha256(pw).hexdigest())
print(hashlib.sha256(pw).hexdigest())
print(hashlib.sha256(b"hunter3").hexdigest())
```

```text
f52fbd32b2b3b86ff88ef6c490628285f482af15ddcb29541f94bcf526a3f6c7
f52fbd32b2b3b86ff88ef6c490628285f482af15ddcb29541f94bcf526a3f6c7
fb8c2e2b85ca81eb4350199faddd983cb26af3064614e737ea9f479621cfa57a
```

- 같은 입력은 언제나 같은 결과다. 그래서 로그인 때 비교할 수 있다.
- 글자 하나만 달라도 결과가 전혀 다르다.
- 결과에서 원문을 거꾸로 계산해 낼 수 없게 설계돼 있다.

## 같은 비밀번호인데 해시가 같으면 생기는 문제

위처럼 해시만 저장하면, 같은 비밀번호를 쓰는 사용자는 저장된 값도 같다. 데이터베이스가 유출되면 값이 같은 사람끼리 묶이고, 흔한 비밀번호의 해시를 미리 계산해 둔 표(레인보 테이블 등)와 대조하면 한꺼번에 풀린다.

그래서 사용자마다 무작위 값인 **솔트**를 붙여서 계산하고, 솔트는 해시와 함께 저장한다. [OWASP 비밀번호 저장 치트 시트](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)도 "A unique salt must be added to each password"라고 적는다. 같은 `hunter2`에 솔트만 바꿔 PBKDF2로 계산해 봤다.

```python
import os
s = os.urandom(16)
print(s.hex(), hashlib.pbkdf2_hmac("sha256", pw, s, 600_000).hex())
```

```text
salt b1b57fbeeff79813832323fdb009523e -> 0edc7b61ce20d6821ae3b528b912408dc769e0b9409a36aeb3026eccec0a7aab
salt 34d061f8a6998989ce89623a3e565cd7 -> 21a1ba3f6a5c3d5625364b5c0bd993e0af3122dcd076f77a3da707d13b352038
```

비밀번호는 같은데 결과가 완전히 다르다. 솔트는 비밀이 아니다. 목적은 값을 숨기는 게 아니라, 미리 계산해 둔 표를 못 쓰게 하고 사용자마다 따로 계산하게 만드는 것이다.

## 왜 SHA-256 한 번으로는 부족한가

SHA-256 같은 해시는 **빠르도록** 설계됐다. 비밀번호에서는 이 속도가 약점이다. 공격자가 유출된 해시를 놓고 비밀번호를 하나씩 대입해 보는 속도도 같이 빨라지기 때문이다. OWASP도 "Fast hashing algorithms such as SHA‑256 are not suitable for password storage"라고 적는다.

같은 기기에서 SHA-256과 PBKDF2(반복 600,000회)를 비교했다.

```text
sha256 x1000000: 0.37s -> 2,732,245/s
pbkdf2 600000 iters: 144 ms each -> 6.9/s
```

| 방식 | 코어 하나로 1초에 계산하는 횟수 |
|---|---|
| SHA-256 한 번 | 약 270만 |
| PBKDF2-HMAC-SHA256, 60만 회 반복 | 약 7 |

로그인하는 사람에게 0.14초는 느껴지지 않는다. 하지만 대입하는 공격자에게는 속도가 40만 분의 1 수준으로 떨어진다. 일부러 느리게 만든 해시를 쓰는 이유다. OWASP는 PBKDF2-HMAC-SHA256에 60만 회 이상, 가능하면 Argon2id(메모리 19 MiB, 반복 2회, 병렬 1 이상)를 권장한다.

## 내가 할 수 있는 것

사이트가 어떻게 저장하는지는 밖에서 알 수 없다. 사용자가 할 수 있는 일은 이쪽이다.

- 비밀번호를 **길고 사이트마다 다르게** 쓴다. 느린 해시도 `hunter2` 같은 짧고 흔한 비밀번호는 오래 못 버틴다.
- 같은 비밀번호를 여러 곳에 쓰면 한 곳이 뚫릴 때 나머지도 같이 뚫린다.
- "비밀번호를 메일로 보내 드립니다"가 오면 그 사이트는 원문을 저장하고 있다는 신호이므로, 그 비밀번호를 다른 곳에서 쓰고 있다면 바꾼다.
