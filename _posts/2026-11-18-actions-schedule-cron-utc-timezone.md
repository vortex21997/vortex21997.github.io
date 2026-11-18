---
title: "Actions schedule이 9시간 어긋나 돌 때: cron은 UTC, 그리고 늦게 도는 것과 구분하기"
description: "on.schedule의 cron은 기본이 UTC라 KST 09:00으로 쓴 '0 9 * * *'는 18:00에 돈다. 9시간 어긋남과 몇 분 지연, 기본 브랜치 문제를 가려내는 기준과 timezone 옵션 정리."
date: 2026-11-18 09:00:00 +0900
categories: [자동화, 워크플로]
tags: [cron, schedule, github-actions, timezone]
---

> 2026-11 기준. 아래 동작은 GitHub 공식 문서를 읽고 정리한 것이다. 시각 환산(`date` 출력)만 이 글을 쓰며 직접 돌렸고, 실제 스케줄 실행은 이 글에서 새로 돌려 보지 않았다.
{: .prompt-info }

**결론부터.** `on.schedule`의 `cron`은 따로 지정하지 않으면 **UTC**로 해석된다. 한국 시각 09:00에 돌리려고 `0 9 * * *`이라고 쓰면 UTC 09:00, 곧 KST 18:00에 돈다. 9시간 어긋나서 도는 건 고장이 아니라 설정 그대로 도는 것이다.

공식 문서의 문장은 이렇다 ([Events that trigger workflows – schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)).

> By default, scheduled workflows run in UTC.

## 환산은 직접 확인한다

KST는 UTC보다 9시간 빠르다. 샌드박스에서 `date`로 확인했다.

```bash
$ TZ=Asia/Seoul date -d '2026-11-17 00:00 UTC' '+%F %T %Z'
2026-11-17 09:00:00 KST
$ TZ=UTC date -d 'TZ="Asia/Seoul" 2026-11-18 09:00' '+%F %T %Z'
2026-11-18 00:00:00 UTC
```

그러니 KST 09:00에 돌리려면 cron에는 UTC 00:00, 즉 `0 0 * * *`을 쓴다. 하루 세 번(KST 09·13·20시)이면 UTC로 00·04·11시다.

```yaml
on:
  schedule:
    - cron: '0 0 * * *'    # KST 09:00
    - cron: '0 4 * * *'    # KST 13:00
    - cron: '0 11 * * *'   # KST 20:00
```

## timezone 옵션

환산하기 싫으면 `timezone`에 IANA 시간대 문자열을 줄 수 있다. 문서(Workflow syntax의 `on.schedule`)의 예시다.

```yaml
on:
  schedule:
    - cron: '30 5 * * 1-5'
      timezone: "America/New_York"
```

한국 시각이면 `timezone: "Asia/Seoul"`이다. 이 옵션은 비교적 최근에 생긴 것이라, 오래된 글이나 답변에는 없다. 쓰기 전에 [Workflow syntax 문서](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)에 지금도 있는지 확인한다. 서머타임이 있는 시간대는 건너뛴 시각의 실행이 다음 유효 시각으로 밀린다고 문서에 적혀 있다. 한국은 서머타임이 없어 해당하지 않는다.

## 증상별 판별법

"예상한 시각에 안 돈다"는 증상은 같아도 원인이 넷으로 갈린다. Actions 탭에서 실행 목록의 **시작 시각**을 보면 가려진다.

| 실행 목록에서 보이는 것 | 원인 | 근거(공식 문서) |
|---|---|---|
| 매일 같은 시각에, 설정과 **정확히 9시간(또는 시간대 차이만큼)** 어긋난다 | cron이 UTC | "By default, scheduled workflows run in UTC." |
| 시각은 맞는데 **몇 분~수십 분** 늦게 시작한다 | 부하로 인한 지연 | "The `schedule` event can be delayed during periods of high loads … High load times include the start of every hour." |
| 실행 기록이 **아예 없다** (수정 후 새 cron이 안 먹는다) | 기본 브랜치가 아닌 곳에 있는 워크플로 | "Scheduled workflows will only run on the default branch." |
| 한동안 돌다가 **어느 날부터 멈췄다** (공개 저장소) | 60일간 저장소 활동이 없어 자동 비활성화 | "scheduled workflows are automatically disabled when no repository activity has occurred in 60 days" |

핵심은 첫 두 줄의 구분이다. **어긋남이 일정하고 시간대 차이와 같으면 UTC 문제**, 날마다 들쭉날쭉하고 몇 분 단위면 지연이다. 지연은 고칠 수 없지만 줄일 수는 있다. 문서가 정시(매시 0분)를 부하가 몰리는 때로 꼽으므로, 꼭 정시일 필요가 없다면 `7 0 * * *`처럼 분을 비껴 두는 편이 낫다. 다만 지연이 얼마나 줄어드는지는 이 글에서 재 보지 않았다.

세 번째 줄과 관련해, 스케줄은 "latest commit on the default branch"의 워크플로를 쓴다. 다른 브랜치에서 cron을 고치고 병합하기 전에 기다려 봐야 소용없다.

## 그 밖에 알아둘 것

- 가장 짧은 간격은 5분이다: "The shortest interval you can run scheduled workflows is once every 5 minutes."
- 부하가 아주 높으면 대기 중인 작업이 버려질 수 있다고 문서에 있다("some queued jobs may be dropped"). 꼭 한 번은 돌아야 하는 작업이라면 스케줄만 믿지 않는 편이 낫다.
