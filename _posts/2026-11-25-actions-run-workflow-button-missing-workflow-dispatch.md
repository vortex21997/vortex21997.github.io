---
title: "Actions 탭에 'Run workflow' 버튼이 없을 때: workflow_dispatch와 기본 브랜치 확인"
description: "수동 실행 버튼이 안 보이면 워크플로에 workflow_dispatch가 없거나, 그 파일이 기본 브랜치에 없는 것이다. 이 블로그의 배포 워크플로로 확인하는 방법을 정리했다."
date: 2026-11-25 09:00:00 +0900
categories: [자동화, 워크플로]
tags: [workflow-dispatch, github-actions, 수동 실행]
---

> 2026-11 기준. 아래 조건은 [GitHub 공식 문서(Manually running a workflow)](https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-workflow-runs/manually-running-a-workflow)에서 읽은 것이고, 이 저장소의 워크플로와 실행 기록은 직접 확인했다.
{: .prompt-info }

## 결론

Actions 탭에서 워크플로를 골랐는데 **Run workflow** 버튼이 없으면 원인은 둘 중 하나다.

1. 워크플로의 `on:`에 `workflow_dispatch`가 없다.
2. `workflow_dispatch`가 있는 파일이 **기본 브랜치에 아직 없다.**

공식 문서는 이렇게 적는다.

> To run a workflow manually, the workflow must be configured to run on the `workflow_dispatch` event.
>
> To trigger the `workflow_dispatch` event, your workflow must be in the default branch.

그리고 "Only workflow files that use the `workflow_dispatch` event trigger will have the option to run the workflow manually using the **Run workflow** button." 라고도 한다. 저장소 쓰기 권한도 필요하다.

## 판별법

| 확인할 것 | 방법 | 결과 |
|---|---|---|
| 파일에 트리거가 있나 | `.github/workflows/*.yml`의 `on:` 아래를 본다 | `workflow_dispatch`가 없으면 ①. 추가하고 푸시한다 |
| 그 파일이 기본 브랜치에 있나 | GitHub에서 기본 브랜치로 바꿔 같은 파일을 연다 | 트리거가 없거나 파일이 없으면 ②. 기본 브랜치에 병합한다 |

기능 브랜치에서 `workflow_dispatch`를 추가하고 Actions 탭을 열어도 버튼은 안 생긴다. 병합 전에는 기본 브랜치의 파일만 보기 때문이다.

## 이 블로그의 경우

배포 워크플로(`.github/workflows/pages-deploy.yml`)의 `on:`은 이렇다.

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

  # Allows you to run this workflow manually from the Actions tab
  workflow_dispatch:
```

`workflow_dispatch:` 뒤에 아무 값이 없어도 된다. 입력(`inputs`)이 필요 없으면 빈 채로 둔다. PyYAML로 읽어 보면 값이 `None`으로 나온다.

```console
$ python3 -c "import yaml;d=yaml.safe_load(open('.github/workflows/pages-deploy.yml'));print(d[True])"
{'push': {'branches': ['main', 'master'], 'paths-ignore': ['.gitignore', 'README.md', 'LICENSE']}, 'workflow_dispatch': None}
```

`d[True]`로 읽은 건 PyYAML가 YAML 1.1 규칙에 따라 `on` 키를 불리언 `True`로 해석하기 때문이다. 이 출력에서 확인하려는 건 `workflow_dispatch` 키가 있다는 점뿐이다.

참고로 이 저장소의 실행 기록을 `event=workflow_dispatch`로 걸러 보면 `total_count`가 0이다. 트리거는 있지만 지금까지 수동 실행을 한 번도 안 썼다는 뜻이다. 모든 배포가 `push`로 돌았다.

## 같이 보면 좋은 글

- 푸시했는데 실행이 아예 안 생길 때: [paths-ignore와 [skip ci]](/posts/actions-no-run-paths-ignore-skip-ci/)
- 실행이 `cancelled`로 뜰 때: [concurrency](/posts/actions-run-cancelled-concurrency/)
