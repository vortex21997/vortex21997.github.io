---
title: "GitHub Actions 배포가 cancelled로 뜰 때: concurrency 때문인지 진짜 실패인지 가리기"
description: "푸시했는데 Actions 실행이 빨간 X 없이 cancelled로 끝나면 대개 concurrency의 cancel-in-progress 때문이다. 이 블로그의 실제 실행 기록 두 건으로, 괜찮은 취소와 배포가 빠진 취소를 가르는 기준을 정리했다."
date: 2026-11-04 09:00:00 +0900
categories: [자동화, 워크플로]
tags: [concurrency, cancel-in-progress, github-actions]
---

푸시 직후 Actions 목록에서 한 실행이 `cancelled`(회색 취소 표시)로 끝나 있었다. 에러 로그는 없는데 배포가 됐는지 알 수 없다. 결론부터: **그 실행 뒤에 같은 워크플로의 더 새로운 실행이 `success`로 끝났다면 정상**이다. 새 푸시가 이전 실행을 밀어낸 것이고, 새 실행이 이전 커밋까지 포함해서 배포한다. 취소된 실행이 **가장 최근** 것이라면 그때만 배포가 빠진 것이다.

> 2026-11-04 기준. 아래 기록은 이 저장소의 `Build and Deploy` 워크플로 실행 이력(GitHub Actions API)에서 읽은 값이다.
{: .prompt-info }

## 원인: 워크플로에 적어 둔 두 줄

이 블로그의 `.github/workflows/pages-deploy.yml`에는 이렇게 적혀 있다.

```yaml
concurrency:
  group: "pages"
  cancel-in-progress: true
```

[GitHub 문서](https://docs.github.com/en/actions/using-jobs/using-concurrency)는 이렇게 말한다.

- 같은 concurrency 그룹에서는 "at most one running job or workflow in a concurrency group at any time"(동시에 실행되는 것은 최대 하나).
- `cancel-in-progress: true`를 주면 "any currently running job or workflow in the same concurrency group"도 취소된다. 즉 새 실행이 시작되면 돌고 있던 실행이 중단된다.

이 줄은 Pages 배포 템플릿에 기본으로 들어 있어서, 직접 쓴 기억이 없어도 있을 수 있다.

## 실제 기록: run 35와 run 36

이 블로그에서 2026-11-02에 18초 간격으로 푸시가 두 번 있었다. 목록에서 읽은 값이다.

| run | 커밋 | 푸시 시각(UTC) | conclusion |
|---|---|---|---|
| 35 | `수정: 제목에 '<'가 있으면 RSS 피드가 깨지는 문제` | 00:19:25 | `cancelled` |
| 36 | `글: claude --continue 했는데 …` | 00:19:43 | `success` |

run 35의 잡을 열어 보면 취소 위치가 보인다.

```
build   conclusion: cancelled   (단계 Checkout ~ Upload site artifact 전부 success)
deploy  conclusion: cancelled   (created_at 00:19:48)
```

`build` 안의 단계는 모두 성공인데 잡 conclusion만 `cancelled`다. 단계 실패가 아니라 **바깥에서 실행이 통째로 취소**됐다는 표시다. 그리고 `deploy`는 시작도 못 했다.

그러면 이 수정 커밋은 사이트에 안 나갔을까? 아니다. run 36의 커밋(`6a1af0f`)은 run 35의 커밋(`5fd077c`) 위에 쌓여 있다.

```
$ git merge-base --is-ancestor 5fd077c 6a1af0f && echo ancestor
ancestor
```

run 36은 `5fd077c`까지 포함한 트리를 빌드해 배포했다. 그래서 취소된 run 35의 변경은 run 36을 통해 나갔다.

## 판별 순서

1. 취소된 실행의 `head_sha`를 적는다.
2. **그 뒤에** 같은 워크플로의 실행이 있고 `success`인가? 그렇다면 그 실행이 `head_sha`의 자손 커밋을 배포한 것이므로 끝이다(`git merge-base --is-ancestor <취소된 sha> <성공한 sha>`로 확인).
3. 취소된 것이 목록의 맨 위(가장 최근)라면 배포가 빠진 것이다. 누가 직접 취소했거나 다른 사유다. **Re-run all jobs**를 누르거나 `workflow_dispatch`로 다시 돌린다.

> 이 판단은 푸시가 같은 브랜치에 순서대로 쌓일 때 성립한다. 다른 브랜치에서 온 실행이 같은 그룹을 쓰면 취소된 쪽 변경이 배포에 안 들어갈 수 있으니, 2번의 조상 확인을 건너뛰지 않는다.
{: .prompt-warning }

## 이 설정을 바꿔야 하나

배포 워크플로에서는 보통 그대로 둔다. 최신 커밋만 배포하면 되는데, 앞선 실행을 끝까지 기다리면 시간만 쓴다. 매번 모든 실행이 끝까지 돌아야 하는 작업(예: 릴리스 번호 발급)이라면 `cancel-in-progress`를 빼야 한다. 그때는 문서대로 대기 중인 실행이 최대 하나만 남고 나머지는 밀려 취소된다는 점은 같다.

직접 확인한 것은 run 35·36의 기록과 조상 관계이고, `cancel-in-progress`와 대기 실행의 동작은 위 문서에서 읽었다. 대기 중 실행이 교체되는 경우는 이 저장소에서 재현해 보지 않았다.
