---
title: "푸시했는데 Actions 실행이 아예 안 생길 때: paths-ignore와 [skip ci] 가려내기"
description: "푸시 뒤 Actions 목록에 실행이 하나도 없으면 실패가 아니라 '트리거 조건 불일치'다. paths-ignore, branches 필터, 커밋 메시지의 skip 문구 중 무엇이 막았는지 가리는 기준을 공식 문서와 이 저장소의 실행 이력으로 정리했다."
date: 2026-11-11 09:00:00 +0900
categories: [자동화, 워크플로]
tags: [paths-ignore, skip-ci, github-actions]
---

푸시했는데 Actions 탭에 새 실행이 **아예 없다**. 빨간 X도, `cancelled`도 아니고 목록 자체가 그대로다. 결론부터: 이건 워크플로가 실패한 게 아니라 **트리거 조건이 맞지 않아 실행이 만들어지지 않은 것**이다. 원인 후보는 셋이고, 푸시한 커밋의 변경 파일·브랜치·메시지 세 가지만 보면 가려진다.

> 2026-11 기준. 규칙은 GitHub Docs의 [Workflow syntax](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions)와 [Skipping workflow runs](https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-workflow-runs/skipping-workflow-runs)에서 읽었다. 이 글에서 직접 실행해 본 것은 이 저장소의 실행 이력 조회뿐이고, 필터 동작 자체를 일부러 재현해 보지는 않았다.
{: .prompt-info }

## 이 블로그의 트리거 설정

`.github/workflows/pages-deploy.yml`의 `on:` 부분이다.

```yaml
on:
  push:
    branches:
      - main
      - master
    paths-ignore:
      - .gitignore
      - README.md
      - LICENSE
  workflow_dispatch:
```

`main`/`master`에 푸시하면 실행되지만, 바뀐 파일이 `.gitignore`, `README.md`, `LICENSE`뿐이면 실행되지 않는다.

## 판별: 세 가지 중 무엇이 막았나

| 확인할 것 | 막았다면 | 문서의 근거 |
|---|---|---|
| 푸시에 포함된 **모든** 변경 파일이 `paths-ignore` 목록에 해당하나 | 실행 안 생김 | "When all the path names match patterns in `paths-ignore`, the workflow will not run." |
| 푸시한 브랜치가 `branches` 목록에 있나 | 실행 안 생김 | "the workflow will only run when both filters are satisfied." (branches와 paths를 같이 쓰면 둘 다 만족해야 한다) |
| 커밋 메시지에 skip 문구가 있나 | 실행 안 생김 | `[skip ci]`, `[ci skip]`, `[no ci]`, `[skip actions]`, `[actions skip]` |

확인 명령은 이렇다.

```bash
git diff --name-only HEAD~1 HEAD      # 마지막 커밋이 바꾼 파일 (여러 커밋을 한 번에 푸시했다면 그 범위 전체)
git branch --show-current             # 푸시한 브랜치
git log -1 --format=%B | grep -iE '\[(skip ci|ci skip|no ci|skip actions|actions skip)\]'
```

세 줄 다 해당 없는데도 실행이 없다면, 그때 워크플로 파일의 문법이나 Actions 사용 설정을 의심한다.

### 놓치기 쉬운 두 가지

- **"모든" 파일이 일치해야 건너뛴다.** `README.md`와 `_posts/새글.md`를 같이 푸시하면 `_posts/새글.md`는 목록에 없으므로 실행된다. 반대로 한 푸시에 커밋이 여러 개면 커밋별이 아니라 푸시 전체의 변경 파일로 판단된다는 점을 염두에 둔다.
- **skip 문구는 `push`와 `pull_request`에만 적용된다.** 문서: "Skip instructions only apply to the `push` and `pull_request` events." 그래서 `workflow_dispatch`로 수동 실행하는 것은 막지 못한다. 필터에 걸려 배포가 빠졌다면 Actions 탭의 `Run workflow`로 직접 돌리면 된다(이 워크플로는 `workflow_dispatch`가 켜져 있다).

## 반대로 필터가 안 먹는 경우

문서는 두 경우에 필터와 상관없이 **항상 실행**된다고 적는다.

- "If a push contains more than 1,000 commits, the workflow will always run."
- "If generating the diff times out, the workflow will always run."

그래서 "README만 고쳤는데 실행됐다"면 위 두 경우나, 같은 푸시에 다른 파일이 섞였는지를 먼저 본다.

## PR에서는 더 아프다

같은 문서에 이런 경고가 있다. 필터로 건너뛴 워크플로의 체크는 "Pending" 상태로 남고, 그 체크를 필수로 걸어 둔 PR은 머지가 막힌다. 이 블로그는 `main`에 직접 푸시하는 구조라 겪지 않았지만, 브랜치 보호 규칙에 이 워크플로의 체크를 필수로 걸면 README만 고친 PR이 영원히 대기할 수 있다.

## 이 저장소에서 확인한 것: 글 커밋마다 실행이 하나씩 있다

GitHub Actions API로 `Build and Deploy` 실행을 조회해, 최근 5건의 `head_sha`가 글 커밋과 1:1로 대응하는지 봤다(2026-11-11 조회, 총 52건).

```text
run #50  d68fe6e  success   (2026-11-10 11:17 UTC)
run #49  17690fd  success   (2026-11-10 04:15 UTC)
run #48  c3ecef5  success   (2026-11-10 00:16 UTC)
run #47  ad41e7f  success   (2026-11-09 11:21 UTC)
run #46  0cf633e  success   (2026-11-09 04:15 UTC)
```

글 커밋은 `_posts/`에 파일을 추가하므로 `paths-ignore`에 걸리지 않고, 푸시 대상이 `main`이며, 커밋 메시지에 skip 문구도 없다. 세 조건이 모두 "통과"라서 실행이 생긴 것이다. 저장소 전체 커밋 메시지에서 skip 문구를 검색하면 0건이었다.

비슷하지만 다른 글: 실행이 **생겼는데** `cancelled`로 끝난 경우는 [concurrency 글]({% post_url 2026-11-04-actions-run-cancelled-concurrency %})에서 다뤘다. 이 글은 실행 자체가 **생기지 않은** 경우다.
