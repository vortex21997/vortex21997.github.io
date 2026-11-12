---
title: "Gemini CLI가 AGENTS.md를 안 읽을 때: context.fileName 설정"
description: "Gemini CLI는 기본으로 GEMINI.md만 찾는다. AGENTS.md를 쓰는 저장소에서 지침이 안 먹으면 settings.json의 context.fileName에 이름을 추가한다. 공식 문서 기준 로드 순서와 확인 명령 정리."
date: 2026-11-12 09:00:00 +0900
categories: [AI 에이전트, 다른 도구]
tags: [gemini-cli, agents-md, settings-json]
---

**결론:** Gemini CLI가 읽는 기본 컨텍스트 파일 이름은 `GEMINI.md`다. 저장소에 `AGENTS.md`만 있으면 지침이 적용되지 않는다. `settings.json`의 `context.fileName`에 이름을 추가하면 읽는다.

> 2026-11 기준. 아래 동작은 [Gemini CLI 공식 문서(GEMINI.md)](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/gemini-md.md)에서 읽은 내용이다. `@google/gemini-cli` 0.68.0을 샌드박스에 설치해 실행했지만 **인증 키가 없어 모델 응답까지는 확인하지 못했다.** 그래서 "실제로 읽혔다"는 출력은 싣지 않는다.
{: .prompt-info }

## 직접 확인한 것

npm으로 설치하고 버전과 인증 없이 실행했을 때의 출력이다.

```console
$ gemini --version
0.68.0
$ gemini -p "/memory show"
Please set an Auth method in your /tmp/g/home/.gemini/settings.json or specify one of the following environment variables before running: GEMINI_API_KEY, GOOGLE_GENAI_USE_VERTEXAI, GOOGLE_GENAI_USE_GCA
```

`/memory show`도 인증 뒤에야 돌아간다. 아래 로드 규칙은 문서에서 읽은 것이다.

## 문서에서 읽은 것

**1. 어디서 읽나.** 일치하는 파일을 모두 이어 붙여 매 프롬프트에 보낸다.

1. 전역: `~/.gemini/GEMINI.md`
2. 작업 디렉터리와 그 상위 디렉터리
3. JIT: 도구가 파일·디렉터리에 접근할 때 그 위치와 상위(신뢰하는 루트까지)를 확인

**2. 파일 이름 바꾸기.** 문서의 예시 그대로다.

```json
{
  "context": {
    "fileName": ["AGENTS.md", "CONTEXT.md", "GEMINI.md"]
  }
}
```

프로젝트의 `.gemini/settings.json`이나 `~/.gemini/settings.json`에 넣는다. 목록으로 쓰면 이름 하나가 아니라 여러 개를 찾는다.

**3. 확인 명령.**

- `/memory show` — 지금 합쳐진 컨텍스트 전체를 보여 준다.
- `/memory reload` — 모든 위치를 다시 훑는다. 파일을 고친 뒤 쓴다.
- 화면 아래 표시줄에 읽힌 컨텍스트 파일 수가 나온다.

## 판별법

"지침이 안 먹는다"에는 원인이 둘이다.

| 증상 | 확인 | 원인 |
|---|---|---|
| `/memory show`에 AGENTS.md 내용이 없다 | 파일 이름이 `fileName` 목록에 있나 | 이름 설정 문제 → 위 설정 추가 |
| `/memory show`에는 있는데 따르지 않는다 | 내용이 다른 파일과 충돌하나 | 읽힌 것이므로 파일 이름 문제가 아니다 |

`fileName`을 바꾼 뒤에는 `/memory reload`를 한 번 실행한다.

같은 문제를 Claude Code 쪽에서 본 글은 [CLAUDE.md와 AGENTS.md](/posts/claude-md-vs-agents-md/)에 있다.
