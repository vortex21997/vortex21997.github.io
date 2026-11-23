---
title: "Claude Code에서 '다시 묻지 않기'를 눌렀는데 또 물을 때: deny → ask → allow 순서"
description: "allow 규칙을 저장했는데도 같은 명령에 허락 프롬프트가 뜨거나 deny에 막힐 때, 규칙이 어떤 순서로 평가되고 여러 설정 파일이 어떻게 합쳐지는지 공식 문서 기준으로 정리했다."
date: 2026-11-23 09:00:00 +0900
categories: [AI 에이전트, Claude Code]
tags: [permissions, settings-json, allow-deny]
---

> 2026-11 기준. 이 글은 **공식 문서를 읽고 정리한 것**이다. 샌드박스에서 직접 재현한 동작은 없다.
> 근거: [Configure permissions](https://code.claude.com/docs/en/permissions) · [Settings files and precedence](https://code.claude.com/docs/en/settings)
{: .prompt-info }

## 결론

허락 프롬프트에서 **"Yes, and don't ask again"** 을 눌러 `allow` 규칙이 저장됐는데도 같은 명령을 또 물어본다면, 대개 **다른 파일에 같은 명령과 맞는 `ask`나 `deny` 규칙이 있어서**다.
`allow`는 평가 순서에서 가장 마지막이라 `ask`와 `deny`를 이기지 못한다.

## 평가 순서

공식 문서의 문장은 이렇다.

> Rules are evaluated in order: deny, then ask, then allow. The first match in that order determines the outcome, and rule specificity doesn't change the order.

그리고 이어서 이런 예를 든다.

- `Bash(aws *)` 같은 넓은 `deny`는 `Bash(aws s3 ls)` 같은 좁은 `allow`가 있어도 그 호출을 막는다. **`allow`로 `deny`에 예외를 낼 수 없다.**
- `ask`와 `allow`도 같다. 더 구체적인 `allow`가 맞아도 `ask`가 맞으면 프롬프트가 뜬다.

"구체적인 규칙이 넓은 규칙을 이긴다"는 직관이 여기서는 통하지 않는다. 순서만 본다.

## 판별법: 어느 파일 때문인가

같은 증상(허락을 또 묻는다)에 원인이 둘이다.

| 상황 | 원인 | 확인 |
|---|---|---|
| 규칙이 **저장되지 않았다** | 저장 위치가 다르거나 파일이 로드되지 않았다 | `/status`의 `Setting sources` 줄에 그 파일이 있는지 |
| 규칙은 저장됐는데 **다른 규칙이 먼저 맞는다** | 다른 스코프의 `ask`/`deny`가 같은 명령에 맞는다 | 각 설정 파일에서 `ask`·`deny` 항목 검색 |

`/status`는 어떤 파일을 읽었는지만 보여 주고, **키마다 어느 파일에서 왔는지는 보여 주지 않는다**(문서 설명). 그래서 두 번째 경우는 파일을 직접 열어 찾아야 한다.
깨진 항목은 `claude doctor`로 본다. 규칙 문법이 틀리면 그 항목만 건너뛰고 "Settings Warning"이 뜬다.

## 스코프 사이에서는 합쳐진다

`permissions.allow` 같은 목록은 파일끼리 **덮어쓰지 않고 합쳐진다.** 그래서 한 파일의 `deny`는 다른 파일의 `allow`로 지워지지 않는다.
문서는 이렇게 못 박는다. 사용자 설정이 허용하고 프로젝트 설정이 거부하면 막히고, 반대로 사용자 설정의 `deny`는 프로젝트 설정의 `allow`를 막는다.

설정 파일의 우선순위(스칼라 값 기준, 높은 쪽부터)는 이렇다.

1. 관리형(managed) 설정 — 조직이 배포
2. 명령줄 `--settings`
3. `.claude/settings.local.json` — 나만, 이 프로젝트만
4. `.claude/settings.json` — 팀 공유
5. `~/.claude/settings.json` — 나만, 모든 프로젝트

하지만 **권한 규칙은 이 순위로 덮어쓰는 게 아니라 합쳐진 뒤 deny → ask → allow로 평가**된다는 점이 핵심이다.
문서의 문제 해결 항목도 같은 사례를 든다. 프롬프트에서 "다시 묻지 않기"를 고르면 `allow`가 로컬 파일에 저장되는데, 로컬 파일의 `allow`는 프로젝트나 관리형 파일의 `ask`보다 세지 않다.

## 같은 파일 안에서도 헷갈리는 두 가지

- **프로젝트 `.claude/settings.json`의 `allow`는 작업 폴더를 신뢰해야 적용된다.** `deny`와 `ask`는 신뢰 전에도 바로 적용된다. 팀원이 "내 쪽에선 또 묻는다"고 하면 신뢰 대화상자를 넘겼는지부터 본다.
- **훅이 먼저다.** PreToolUse 훅이 exit 2로 끝나면 권한 규칙을 평가하기도 전에 호출이 막힌다. `allow`가 있어도 소용없다. (훅 종료 코드는 [exit 1은 막지 못한다](/posts/claude-hook-exit-1-does-not-block/) 글 참고.)

## 막지 않고 예외를 두고 싶다면

"`aws`는 다 막되 `aws s3 ls`만 허용" 같은 구성은 `deny`+`allow`로 안 된다. 문서가 제시하는 방법은 `Bash` 전체를 `allow`에 넣고, 막을 명령만 **PreToolUse 훅**으로 거절하는 것이다.

## 확인 못 한 것

- 위 동작을 `claude` 실행으로 재현하지는 않았다. 버전별로 달라졌을 수 있으니 문서의 해당 절을 직접 확인하자.
- 관리형 설정이 있는 환경의 실제 화면은 확인하지 못했다.
