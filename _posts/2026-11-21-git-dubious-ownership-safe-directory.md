---
title: "git이 'detected dubious ownership in repository'로 멈출 때: safe.directory는 저장소 안에 못 적는다"
description: "저장소 소유자와 지금 사용자가 다르면 git status까지 fatal로 막힌다. 안내대로 safe.directory를 적는 방법과, 저장소 설정에 적으면 안 먹는 이유, SUDO_UID 예외를 직접 재현해 확인했다."
date: 2026-11-21 09:00:00 +0900
categories: [개발 환경, Git·GitHub]
tags: [safe.directory, git, 권한]
---

`git status`, `git log`, `git pull` 가릴 것 없이 전부 이 한 줄로 막힐 때가 있다.

```
fatal: detected dubious ownership in repository at '/work/repo'
To add an exception for this directory, call:

	git config --global --add safe.directory /work/repo
```

**결론부터.** 저장소 폴더의 소유자(uid)와 git을 실행한 사용자가 다르기 때문이다. 안내된 `git config --global --add safe.directory <경로>`를 그대로 실행하면 풀린다. 단, 이 설정은 **저장소 안의 `.git/config`에 적으면 무시된다.** 전역(global)·시스템(system) 설정이나 `-c` 옵션에서만 읽힌다.

> 아래 출력은 git 2.43.0, Linux(root로 실행)에서 직접 돌린 것이다. 원래 경로가 길어서 `/work/repo`로 줄여 적었다.
{: .prompt-info }

## 재현

일반 사용자(uid 1234) 소유의 저장소를 root로 열어 본다. 도커 볼륨, 마운트한 외장 디스크, `sudo`로 만든 폴더, 다른 계정이 쓰던 폴더가 같은 상황이다.

```bash
git init -q repo && cd repo && git commit -q --allow-empty -m init
cd .. && chown -R 1234:1234 repo && cd repo
ls -ld .
```

```
drwxr-xr-x 3 1234 1234 4096 Nov 21 00:13 .
```

```bash
git status; echo "exit=$?"
```

```
fatal: detected dubious ownership in repository at '/work/repo'
To add an exception for this directory, call:

	git config --global --add safe.directory /work/repo
exit=128
```

`git log`, `git rev-parse --is-inside-work-tree`도 같은 메시지와 종료 코드 128이었다. 명령 하나가 아니라 **저장소를 여는 모든 명령**이 막힌다.

## 풀기: 안 되는 것부터

가장 먼저 떠오르는 건 "저장소 설정에 적자"다. 두 가지로 해 봤고 둘 다 안 됐다.

```bash
git config --local safe.directory "$PWD"
```

```
fatal: --local can only be used inside a git repository
```

저장소로 인정을 못 받는 상태라 `--local`이 아예 안 된다. 그럼 `.git/config`에 직접 적으면?

```bash
printf '[safe]\n\tdirectory = %s\n' "$PWD" >> .git/config
git status
```

```
fatal: detected dubious ownership in repository at '/work/repo'
```

여전히 막힌다. 이유는 git 공식 문서에 있다. `safe.directory`는 [protected configuration에서만 읽는다](https://git-scm.com/docs/git-config). 저장소 안의 설정은 그 저장소를 내려받은 쪽이 마음대로 쓸 수 있으니, 거기에 "나는 안전함"이라고 적게 두면 검사가 의미가 없어서다.

## 풀기: 되는 것

설정 위치별로 같은 저장소에 돌려 본 결과다. 사용자별 전역 설정 파일은 매번 빈 파일에서 시작했다.

| 방법 | 결과 |
|---|---|
| 전역에 경로 하나: `git config --global --add safe.directory /work/repo` | **통과** (`On branch master`) |
| 전역에 `*`: `git config --global safe.directory '*'` | **통과**. 모든 저장소의 검사를 끈다 |
| 명령줄: `git -c safe.directory=/work/repo -C /work/repo status` | **통과**. 이번 한 번만 |
| 저장소 `.git/config` | 막힘 |
| 전역에 `/work/parent/*` (하위 저장소 두 개에 시도) | 막힘 (git 2.43.0에서) |

마지막 줄은 주의가 필요하다. 상위 폴더에 `/*`를 붙여 한꺼번에 풀 수 있다는 글을 볼 수 있는데, 내가 쓴 2.43.0에서는 동작하지 않았다. 더 새 버전에서 되는지는 직접 확인하지 못했으니, 쓰기 전에 `git --version`부터 보고 시험해 보는 편이 낫다.

쓰기 안전한 순서는 이렇다.

1. 한 번만 필요하면 `git -c safe.directory=<경로> ...`
2. 계속 쓸 저장소라면 경로를 하나씩 `--global --add`
3. `'*'`는 내가 만든 샌드박스·컨테이너처럼 어차피 신뢰하는 환경에서만. 남의 저장소가 섞이는 PC에서는 검사를 통째로 끄는 셈이다.

## sudo에서만 되는 예외: SUDO_UID

root로 `sudo git ...`을 쓰는 경우에는 사정이 다르다. 문서에 따르면 root가 `sudo`로 실행하면 환경변수 `SUDO_UID`의 uid도 소유자로 인정한다(`make && sudo make install`이 되게 하려는 장치). 같은 저장소(소유자 1234)로 확인했다.

```bash
SUDO_UID=1234 git status
```

```
On branch master
```

```bash
SUDO_UID=999 git status
```

```
fatal: detected dubious ownership in repository at '/work/repo'
```

소유자와 같은 uid일 때만 통과한다. 그래서 "일반 계정으로는 되는데 `sudo git`이나 root 셸에서는 막힌다", 또는 그 반대는 `SUDO_UID`가 있느냐 없느냐로 갈린다. `sudo -i`나 `su`처럼 이 변수가 없는 경로로 root가 되면 막힌다.

## 소유자를 바꾸는 쪽은 어떤가

설정을 건드리는 대신 소유자를 맞춰도 된다. 위 저장소에서 `chown -R 0:0 .`로 root 소유로 돌리자 설정 없이 `git status`가 바로 통과했다. 진짜 원인이 "소유자가 다름"이라는 확인이기도 하다. 다만 같은 폴더를 다른 계정도 쓴다면 이번엔 그쪽이 막히니, 누가 쓰는 폴더인지부터 정하고 고른다.

## 정리

- 메시지의 `detected dubious ownership` 문자열 = 폴더 소유자 uid ≠ 실행한 사용자 uid.
- 안내대로 `--global --add safe.directory <경로>`, 일회성이면 `-c`.
- `.git/config`에 적는 것은 소용없다. 일부러 막아 둔 것이다.
- sudo 환경이면 `SUDO_UID`가 소유자와 같은지 본다.

근거: [git-config 문서](https://git-scm.com/docs/git-config)의 safe.directory 항목(2.43.0 소스 트리의 `Documentation/config/safe.txt`로 확인). 위 동작은 모두 git 2.43.0 / Linux 샌드박스에서 직접 실행한 결과이며, Windows·macOS에서의 동작은 확인하지 않았다.
