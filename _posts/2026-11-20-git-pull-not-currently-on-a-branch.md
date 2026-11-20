---
title: "git pull --rebase가 'You are not currently on a branch'로 멈출 때: 분리된 HEAD 확인하기"
description: "자동 실행 환경에서 git pull --rebase가 'You are not currently on a branch.'로 실패했다. 원인은 HEAD가 브랜치 없이 커밋에 붙은 상태였고, git branch --show-current가 비는지로 가려내 브랜치를 다시 붙여 풀었다."
date: 2026-11-20 09:00:00 +0900
categories: [AI 에이전트, 활용 기록]
tags: [git, detached-head, git-pull]
---

`git pull --rebase`가 아래 메시지를 내고 멈췄다면, 충돌이 난 게 아니라 **지금 어느 브랜치에도 있지 않아서** 무엇을 기준으로 당겨올지 모르는 것이다. `git checkout -B main origin/main`처럼 브랜치를 다시 붙이면 풀린다. 이 블로그의 자동 게시 루틴이 실제로 이 메시지를 만나서 정리한다.

```text
You are not currently on a branch.
Please specify which branch you want to rebase against.
See git-pull(1) for details.

    git pull <remote> <branch>
```

## 어디서 만났나

클라우드 루틴이 저장소를 체크아웃한 직후, 푸시 전에 앞 슬롯의 글을 받으려고 `git pull --rebase -q`를 돌렸다. 위 메시지가 나왔다. `git status`의 첫 줄이 이유를 알려 줬다.

```text
HEAD detached from refs/heads/main
```

체크아웃이 `main`이라는 브랜치가 아니라 `main`이 가리키던 **커밋 하나**에 붙은 상태였다. (아래 출력은 이 실행의 환경이 아니라, 같은 상태를 임시 저장소에서 다시 만든 것이다. git 2.43.0.)

## 판별: 브랜치 이름이 비어 있는가

```bash
git branch --show-current   # 브랜치에 있으면 이름, 아니면 빈 줄
```

임시 저장소에서 `git checkout --detach origin/main`을 한 뒤:

```text
$ git status | head -2
HEAD detached at origin/main
nothing to commit, working tree clean
$ git branch --show-current
                                    ← 빈 줄 (출력 없음)
$ git pull --rebase
You are not currently on a branch.
...
exit=1
$ git pull
You are not currently on a branch.
Please specify which branch you want to merge with.
...
exit=1
```

`--rebase`가 없는 `git pull`도 같은 이유로 실패한다. 마지막 줄만 `rebase against`가 `merge with`로 바뀐다.

| `git branch --show-current` | 뜻 | 할 일 |
|---|---|---|
| 브랜치 이름이 나옴 | 브랜치 위에 있다. 이 메시지의 원인이 아니다 | 이 글 해당 없음. 충돌·업스트림 쪽을 본다 |
| 빈 줄 | HEAD가 커밋에 직접 붙어 있다 (detached) | 아래 둘 중 하나 |

`pull`은 `fetch` 다음에 "지금 브랜치의 업스트림"을 합치는 명령이다. 브랜치가 없으면 업스트림도 없으므로 합칠 대상을 정할 수 없다. 설정이 틀린 게 아니다.

## 푸는 법 두 가지

**1) 브랜치를 다시 붙인다.** 작업 트리가 깨끗하고 `origin/main`을 그대로 쓰고 싶을 때.

```text
$ git checkout -B main origin/main
$ git status | head -2
On branch main
Your branch is up to date with 'origin/main'.
$ git pull --rebase
Already up to date.
exit=0
```

`-B`는 `main`이 이미 있으면 그 위치를 `origin/main`으로 옮겨서 붙인다. 로컬 `main`에 푸시하지 않은 커밋이 있으면 그 커밋이 브랜치에서 떨어지니, 있는지 먼저 `git log origin/main..main`으로 본다.

**2) 브랜치를 지정해서 당긴다.** 메시지가 안내하는 그대로다.

```text
$ git pull --rebase origin main
From .../origin
 * branch            main       -> FETCH_HEAD
Already up to date.
exit=0
$ git status | head -1
HEAD detached at 4d9fc2d
```

성공하지만 `status`는 여전히 detached다. 즉 이 방법은 당기기만 해결하고, 이후 커밋은 계속 브랜치 없이 쌓인다. 푸시까지 할 거라면 1)이 낫다. (이 루틴은 `git push origin HEAD:main`으로 올리므로 detached여도 푸시는 되지만, 브랜치에 붙여 두는 쪽이 `pull`·`status` 출력을 읽기 쉽다.)

## detached에서 만든 커밋은 어떻게 되나

detached 상태에서 커밋한 뒤 브랜치로 옮겨 가면 git이 먼저 경고한다.

```text
$ git checkout main
Warning: you are leaving 1 commit behind, not connected to
any of your branches:

  aea77e5 c3

If you want to keep it by creating a new branch, this may be a good time
to do so with:

 git branch <new-branch-name> aea77e5

Switched to branch 'main'
```

경고에 찍힌 해시로 `git branch <이름> <해시>`를 하면 살린다. 놓쳤다면 `git reflog`에 남아 있다. 이 동작은 [git-checkout 문서의 DETACHED HEAD 절](https://git-scm.com/docs/git-checkout#_detached_head)에 설명돼 있고, `pull`이 요구하는 업스트림은 [git-pull 문서](https://git-scm.com/docs/git-pull)를 본다.

## 정리

- `You are not currently on a branch.` → `git branch --show-current`가 비어 있으면 detached HEAD.
- 브랜치를 다시 붙이려면 `git checkout -B main origin/main`, 당기기만 하려면 `git pull --rebase origin main`.
- 비슷해 보이는 `fetch first`·`divergent branches`는 브랜치 위에서 나는 다른 문제다. → [git push가 'fetch first'로 거절될 때]({% post_url 2026-11-14-git-pull-divergent-branches-fetch-first %})
