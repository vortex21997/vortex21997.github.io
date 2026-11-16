---
title: "PreToolUse 훅이 exit 1로 끝났는데 명령이 그냥 실행될 때: 막는 건 exit 2뿐이다"
description: "정책 위반이면 exit 1로 끝내는 훅을 짰더니 Bash 명령이 그대로 실행됐다. PreToolUse에서 도구 호출을 막는 종료 코드는 2이고, 1은 비차단 오류라는 것을 claude -p로 두 경우를 나란히 돌려 확인했다."
date: 2026-11-16 09:00:00 +0900
categories: [AI 에이전트, Claude Code]
tags: [훅, pretooluse, exit-code]
---

> 2026-11 기준. Claude Code 2.1.325에서 확인했다.
{: .prompt-info }

**결론부터: `PreToolUse` 훅에서 도구 호출을 막는 종료 코드는 `2`다.** 유닉스 관례대로 실패를 `exit 1`로 알리면 훅은 "오류"로 기록될 뿐 명령은 그대로 실행된다. 정책을 강제하려는 훅이라면 이게 조용히 뚫린다.

## 공식 문서가 말하는 것

[Hooks 레퍼런스](https://code.claude.com/docs/en/hooks)의 종료 코드 설명(문서에서 읽은 것):

- exit 0: 성공. 출력이 없으면 "the hook has no decision to report" — 결정을 내리지 않은 것이고 일반 권한 흐름으로 넘어간다.
- exit 2: "**Blocking error**". `PreToolUse`는 "Blocks the tool call"로 표에 올라 있다. Claude는 훅의 stderr를 도구 오류로 받는다.
- 그 외 코드(예: 1): "**Non-blocking error**". 동작은 진행되고, 트랜스크립트에 `<hook name> hook error` 알림만 뜬다.

문서는 이 함정을 직접 경고한다: "Exit code 1 without valid JSON output is a non-blocking error ... even though 1 is the conventional Unix failure code. If your hook is meant to enforce a policy, use `exit 2`."

## 직접 돌려 본 것

빈 디렉터리에 `Bash` 호출에 걸리는 훅을 두고, 종료 코드만 1과 2로 바꿔서 같은 프롬프트를 `claude -p`로 실행했다.

`.claude/settings.json`:

```json
{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"type":"command","command":"sh $CLAUDE_PROJECT_DIR/h.sh"}]}]}}
```

`h.sh` (끝의 숫자만 바꿈):

```sh
echo "blocked by policy" >&2
exit 1   # 또는 exit 2
```

```bash
claude -p "Run this exact bash command: echo hi > out.txt . Then say done." --allowedTools Bash --output-format json
```

| 훅 종료 코드 | `out.txt` | `permission_denials` | Claude의 응답 |
|---|---|---|---|
| 1 | **생성됨** | `[]` | `Done. I ran the command, and it wrote hi to out.txt ...` |
| 2 | 없음 | Bash 호출 1건 | `A PreToolUse hook blocked the command with "blocked by policy", so out.txt wasn't created.` |

exit 2에서는 훅이 stderr에 쓴 `blocked by policy`가 Claude의 응답에 그대로 인용됐다. 문서의 "Claude receives the hook's stderr as the tool's error"와 맞는 동작이다. exit 1에서는 같은 stderr를 썼는데도 명령이 실행됐다.

## 판별법

"훅이 있는데 막지 못한다"일 때 원인이 둘로 갈린다.

1. **훅이 실행되지 않았다** — 매처가 안 맞거나 설정 파일 위치가 틀린 경우. 트랜스크립트에 훅 관련 표시가 아예 없다.
2. **훅은 실행됐지만 차단이 아니다** — 종료 코드가 0 또는 1 등이다. 트랜스크립트에 `hook error` 알림이 보이는데 명령은 실행된다.

2번이면 스크립트의 종료 코드를 먼저 본다. `set -e`나 `grep` 실패 같은 부수 효과로 의도치 않게 1이 나오는 경우도 같다.

## 같이 알아 둘 것 (문서에서 읽은 것, 직접 실행은 안 함)

- 타임아웃이 난 `PreToolUse` 훅도 차단하지 않는다. 호출은 일반 권한 흐름으로 계속되므로, 멈춘 훅을 관문으로 기대하면 안 된다.
- exit 0으로 아무것도 출력하지 않는 것은 승인이 아니다. 훅은 거부할 수는 있어도 조용히 있는 것으로 허용하지는 못한다.
- 종료 코드 대신 JSON으로도 막을 수 있다: `hookSpecificOutput.permissionDecision`에 `"deny"`를 주고 `permissionDecisionReason`을 적는다. 이 방식은 문서의 예시만 확인했고 직접 돌려 보지는 않았다.

관련: 같은 `claude -p`가 권한 때문에 일을 못 하고도 exit 0으로 끝나는 경우는 [claude -p가 성공(exit 0)이라는데 파일이 없을 때](/posts/claude-p-permission-denials/)에서 다뤘다. 이번 실험에서도 exit 2로 막힌 쪽의 `is_error`는 `false`였다.
