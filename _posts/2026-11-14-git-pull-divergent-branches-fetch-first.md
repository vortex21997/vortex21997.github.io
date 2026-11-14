---
title: "git push가 'fetch first'로 거절되고 git pull은 'divergent branches'로 막힐 때"
description: "푸시는 '! [rejected] (fetch first)', 이어서 한 pull은 'Need to specify how to reconcile divergent branches'. 로컬에서 실제로 재현해 두 메시지의 관계와 merge·rebase·ff-only 결과를 비교했다."
date: 2026-11-14 09:00:00 +0900
categories: [개발 환경, Git·GitHub]
tags: [git, divergent-branches, git-pull]
---

두 메시지는 같은 상황의 앞뒤다. **원격에 내가 모르는 커밋이 있고, 내 로컬에도 원격에 없는 커밋이 있어서** 히스토리가 갈라졌다. `push`는 그래서 거절되고, `pull`은 "합칠 방법을 정해 달라"며 멈춘다. 방법을 정하면(`merge` / `rebase`) 풀린다.

> 2026-11 기준, git 2.43.0에서 직접 재현했다. 아래 출력은 모두 로컬 bare 저장소 두 개를 clone해서 얻은 원문이다.
{: .prompt-info }

## 재현

저장소 `a`, `b`가 같은 원격을 바라본다. `a`가 커밋 `A`를 먼저 푸시하고, `b`는 그걸 모른 채 자기 커밋 `B`를 만들어 푸시한다.

```console
$ git push origin main
 ! [rejected]        main -> main (fetch first)
error: failed to push some refs to '...remote.git'
hint: Updates were rejected because the remote contains work that you do not
hint: have locally. This is usually caused by another repository pushing to
hint: the same ref. If you want to integrate the remote changes, use
hint: 'git pull' before pushing again.
hint: See the 'Note about fast-forwards' in 'git push --help' for details.
```

힌트대로 `git pull`을 하면 이번엔 이렇게 막힌다.

```console
$ git pull
hint: You have divergent branches and need to specify how to reconcile them.
hint: You can do so by running one of the following commands sometime before
hint: your next pull:
hint: 
hint:   git config pull.rebase false  # merge
hint:   git config pull.rebase true   # rebase
hint:   git config pull.ff only       # fast-forward only
hint: 
hint: You can replace "git config" with "git config --global" to set a default
hint: preference for all repositories. You can also pass --rebase, --no-rebase,
hint: or --ff-only on the command line to override the configured default per
hint: invocation.
fatal: Need to specify how to reconcile divergent branches.
```

`git status -sb`는 갈라진 상태를 한 줄로 보여 준다.

```console
$ git status -sb
## main...origin/main [ahead 1, behind 1]
```

`ahead 1, behind 1`이 핵심이다. 내가 1개 앞서고 원격이 1개 앞서 있다. 한쪽만 앞서면(`ahead`만 또는 `behind`만) 이 오류는 나지 않는다.

```console
$ git log --oneline --graph --all
* fc088cb B
| * f3d386d A
|/  
* 70ea129 base
```

## 판별: 푸시 거절 메시지가 둘이다

같은 거절인데 괄호 안이 다르고, 원인도 한 단계 다르다.

| 괄호 안 | 의미 | 내가 한 일 |
|---|---|---|
| `(fetch first)` | 원격에 내가 **아직 받지 않은** 커밋이 있다 | 마지막 fetch 이후 누군가 푸시함 |
| `(non-fast-forward)` | 받아서 알고는 있는데, 내 브랜치가 **그 뒤에 있다** | `git fetch`는 했지만 합치지 않음 |

둘째 경우는 `git fetch` 직후 푸시해서 재현했다.

```console
$ git fetch && git push origin main
 ! [rejected]        main -> main (non-fast-forward)
error: failed to push some refs to '...remote.git'
hint: Updates were rejected because the tip of your current branch is behind
hint: its remote counterpart. If you want to integrate the remote changes,
hint: use 'git pull' before pushing again.
```

어느 쪽이든 해결은 같다. 원격 커밋을 내 브랜치에 합친 뒤 푸시한다. 괄호 안은 "fetch를 이미 했는가"만 알려 준다.

## 세 가지 선택 결과

같은 상태에서 설정만 바꿔 `git pull`을 돌렸다.

**merge** (`pull.rebase false`) — 병합 커밋이 생긴다.

```console
$ git config pull.rebase false && git pull
Merge made by the 'ort' strategy.
 a.txt | 1 +
$ git log --oneline --graph
*   3d87d40 Merge branch 'main' of ...
|\  
| * f3d386d A
* | fc088cb B
|/  
* 70ea129 base
```

**rebase** (`pull.rebase true`) — 내 커밋 `B`를 원격 뒤로 옮겨 다시 만든다. 직선이 되지만 커밋 해시가 바뀐다(`fc088cb` → `63d2159`).

```console
$ git config pull.rebase true && git pull
Successfully rebased and updated refs/heads/main.
$ git log --oneline --graph
* 63d2159 B
* f3d386d A
* 70ea129 base
```

**ff-only** (`pull.ff only`) — 갈라진 상태에서는 합치지 않고 실패한다.

```console
$ git config pull.ff only && git pull
hint: Diverging branches can't be fast-forwarded, you need to either:
hint: 
hint: 	git merge --no-ff
hint: 
hint: or:
hint: 
hint: 	git rebase
fatal: Not possible to fast-forward, aborting.
```

`ff-only`는 "자동으로 합치지 말고 항상 알려 달라"는 설정이라, 이 오류를 없애 주지 않고 오히려 이 상황에서는 늘 실패한다.

## 정리

- 한 번만 풀 때는 명령줄 옵션이 가장 짧다: `git pull --rebase` 또는 `git pull --no-rebase`.
- 계속 같은 방식으로 쓸 거면 `git config --global pull.rebase true`(또는 `false`)로 고정하면 이 힌트는 다시 안 나온다.
- 이미 푸시한 커밋을 rebase하면 해시가 바뀌므로, 혼자 쓰는 브랜치가 아니라면 merge가 안전하다. 이건 위 해시 변화에서 확인한 사실까지만 말한다.

근거: [git-pull 문서](https://git-scm.com/docs/git-pull)의 `--rebase`·`--ff-only` 항목, [git-config의 pull.rebase](https://git-scm.com/docs/git-config#Documentation/git-config.txt-pullrebase).
