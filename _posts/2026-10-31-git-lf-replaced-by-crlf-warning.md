---
title: "git add 때 'LF will be replaced by CRLF the next time Git touches it'가 뜰 때"
description: "이 경고는 오류가 아니라 '지금 파일은 그대로 두고 다음에 변환하겠다'는 알림이다. 방향(LF→CRLF / CRLF→LF)별 뜻과, 내 설정이 원인인지 저장소가 원인인지 git ls-files --eol로 가리는 법."
date: 2026-10-31 09:00:00 +0900
categories: [개발 환경, Windows]
tags: [autocrlf, gitattributes, crlf]
---

`git add`를 하면 이런 경고가 나온다.

```text
warning: in the working copy of 'f.txt', LF will be replaced by CRLF the next time Git touches it
```

**결론부터: 오류가 아니고, 커밋도 된다.** Git이 "이 파일의 줄바꿈이 내 설정과 다르니, 다음에 이 파일을 건드릴 때 바꾸겠다"고 알려 주는 것이다. 바뀌는 건 *작업 폴더의 파일*이고, 저장소(인덱스)에는 항상 LF로 들어간다. 아래는 Git 2.43.0, Linux 샌드박스에서 `core.autocrlf`를 직접 켜서 재현한 결과다. (Windows 기본 설치가 `autocrlf=true`로 시작하는 경우가 많아서 이 경고는 주로 Windows에서 보이지만, 설정만 같으면 어디서든 똑같이 난다.)

## 방향부터 읽는다

경고 문구는 두 가지다. 어느 쪽이냐에 따라 "내 설정 탓"인지 "파일 탓"인지가 갈린다.

| 경고 | 지금 파일 | Git이 하려는 일 | 흔한 원인 |
|---|---|---|---|
| `LF will be replaced by CRLF` | LF | 다음에 CRLF로 바꿈 | `core.autocrlf=true` |
| `CRLF will be replaced by LF` | CRLF | 다음에 LF로 바꿈 | `autocrlf=input`, 또는 `.gitattributes`의 `eol=lf` |

## 재현: LF 파일 + autocrlf=true

```bash
git init -q t && cd t
git config core.autocrlf true
printf 'a\nb\n' > f.txt
git add f.txt
```

```text
warning: in the working copy of 'f.txt', LF will be replaced by CRLF the next time Git touches it
```

`git ls-files --eol`로 인덱스(`i/`)와 작업 폴더(`w/`)를 따로 본다.

```text
i/lf    w/lf    attr/                 	f.txt
```

경고가 났는데도 작업 폴더(`w/lf`)는 아직 LF다. 인덱스도 `i/lf`다. 저장소에 들어간 바이트도 확인했다.

```bash
git commit -qm x
git cat-file -p HEAD:f.txt | od -c
```

```text
0000000   a  \n   b  \n
```

**CRLF가 저장소로 들어가지 않았다.** 경고는 "체크아웃 때 CRLF로 바꾸겠다"는 예고일 뿐이라, 이 경고 때문에 커밋이 깨지는 일은 없다.

## 반대 방향: CRLF 파일 + autocrlf=input

```bash
git config core.autocrlf input
printf 'p\r\n' > m.txt
git add m.txt
```

```text
warning: in the working copy of 'm.txt', CRLF will be replaced by LF the next time Git touches it
```

```text
i/lf    w/crlf  attr/text=auto eol=lf 	m.txt
```

인덱스는 `i/lf`, 작업 폴더는 `w/crlf`. 이 출력의 `attr/` 칸에 `text=auto eol=lf`가 찍힌 건 같은 폴더에 `.gitattributes`를 만들어 뒀기 때문이다. 열을 읽는 법은 아래 판별법에서 설명한다.

## 판별: 내 설정 탓인가, 저장소 탓인가

`git ls-files --eol`의 `attr/` 칸이 비어 있으면 `.gitattributes`가 이 파일에 아무것도 지정하지 않은 것이고, 줄바꿈 동작은 `core.autocrlf` 같은 *내 설정*이 정한다. 값이 채워져 있으면(`text=auto eol=lf` 등) *저장소가 정한 규칙*이다.

```bash
git ls-files --eol                           # i/ w/ attr/ 확인
git config --show-origin --get-all core.autocrlf   # 내 설정이 어느 파일에서 왔는지
```

두 번째 명령은 설정이 `file:.git/config`(이 저장소)인지, 전역 설정 파일인지 알려 준다. `--show-origin` 없이는 값만 보여서 출처를 모른다.

[gitattributes 문서](https://git-scm.com/docs/gitattributes)는 `text=auto`를 "Git이 텍스트인지 바이너리인지 스스로 판단하고, 텍스트면 체크인·체크아웃 때 변환한다"고, `eol=lf`를 "작업 폴더에서도 인덱스와 같은 줄바꿈으로 체크아웃한다"고 설명한다(2026-10 기준). 저장소에 이 속성이 있으면 팀원의 `autocrlf` 값과 무관하게 같은 규칙이 적용된다.

## 경고를 끄지 말고 정할 것

경고가 거슬려서 `core.safecrlf`를 올리면 이번에는 *실패*한다. 같은 설정 조합에서 CRLF와 LF가 섞인 파일을 추가해 봤다.

```bash
git config core.safecrlf true
git config core.autocrlf true
printf 'p\r\nq\n' > n.txt
git add n.txt
```

```text
fatal: CRLF would be replaced by LF in n.txt
```

종료 코드는 128이었다. 경고(warn)는 알림, `true`는 변환이 되돌릴 수 없을 때 중단이다. 이 실행에서 확인한 건 여기까지이고, `safecrlf`의 정확한 정의는 [git-config 문서](https://git-scm.com/docs/git-config)에서 `core.safecrlf`를 찾아 읽는 편이 낫다.

팀 저장소라면 개인 설정에 맡기지 말고 루트에 `.gitattributes`를 두는 것이 경고를 줄이는 방법이다.

```text
* text=auto eol=lf
```

## CRLF를 방치하면 생기는 진짜 문제

경고보다 무서운 건 CRLF 파일이 *그대로 실행될 때*다. 셸 스크립트를 CRLF로 저장하고 돌려 봤다.

```bash
printf '#!/bin/bash\r\necho hi\r\n' > r.sh && chmod +x r.sh && ./r.sh
```

```text
/bin/bash: line 1: ./r.sh: cannot execute: required file not found
```

종료 코드 127. 셔뱅 줄이 `/bin/bash\r`로 읽혀서 그런 인터프리터가 없는 것이다. (배포판이나 셸에 따라 `bad interpreter` 같은 다른 문구가 나올 수 있다.) 리눅스·Docker·WSL에서 도는 `.sh`는 `eol=lf`로 고정해 두는 이유다.
