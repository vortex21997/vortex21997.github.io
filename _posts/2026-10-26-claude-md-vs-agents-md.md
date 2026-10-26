---
title: "CLAUDE.md와 AGENTS.md, 둘 다 둬야 하나"
description: "Claude Code는 AGENTS.md도 읽는다. 다만 둘이 같이 있으면 AGENTS.md를 무시한다. 그 규칙을 모르면 적어둔 지시가 조용히 안 먹는다."
date: 2026-10-26 13:10:00 +0900
categories: [AI 에이전트, Claude Code]
tags: [claude-code, agents-md, ai, 개발도구]
---

> **2026-10 기준.** [agents.md](https://agents.md/)와
> [Claude Code 메모리 문서](https://code.claude.com/docs/en/memory)를 근거로 정리했다.
> 도구별 지원 현황은 자주 바뀌니 각 도구의 공식 문서를 확인하는 편이 정확하다.
{: .prompt-info }

AI 코딩 도구마다 "이 프로젝트는 이렇게 생겼다"를 적어두는 파일이 있다.
Claude Code는 `CLAUDE.md`, 다른 도구들은 `AGENTS.md`를 쓴다.

도구를 두 개 이상 쓰면 당연히 이런 생각이 든다. **둘 다 둬야 하나?**

결론부터. **Claude Code는 `AGENTS.md`도 읽는다.** 다만 **조건이 붙는다.**

## AGENTS.md란

`README.md`가 사람을 위한 것이라면, `AGENTS.md`는 **에이전트를 위한 README**다.
빌드 절차, 테스트 돌리는 법, 코드 관례처럼 사람 기여자에게는 군더더기인 내용을 담는다.

```markdown
# AGENTS.md

## Setup commands
- Install deps: `pnpm install`
- Run tests: `pnpm test`

## Code style
- TypeScript strict mode
- Single quotes, no semicolons
```

**필수 항목은 없다.** 그냥 마크다운이고, 제목도 마음대로 쓰면 된다.
에이전트가 그 텍스트를 읽을 뿐이다.

Codex, Cursor, Jules, Aider, Zed, GitHub Copilot, Windsurf, Gemini CLI 등
[여러 도구가 이 파일을 읽는다](https://agents.md/). 6만 개 넘는 오픈소스 저장소가 쓰고 있다고 한다.

> 지시가 충돌하면 **고친 파일에서 가장 가까운 `AGENTS.md`가 이긴다.**
> 그리고 채팅으로 직접 준 지시가 파일보다 우선한다. 하위 폴더에 따로 두는 게 의미가 있는 이유다.
{: .prompt-tip }

## Claude Code는 언제 읽나

여기가 핵심이다. **둘 다 있으면 `AGENTS.md`를 안 읽는다.**

| 저장소 상태 | Claude가 읽는 것 |
|---|---|
| `AGENTS.md`만 있음 | **`AGENTS.md`** |
| `AGENTS.md` + `CLAUDE.md` 둘 다 | **`CLAUDE.md`만** |
| `CLAUDE.md`가 `AGENTS.md`를 import | `CLAUDE.md` (import를 통해 둘 다) |

"둘 다 적어두면 둘 다 읽겠지"가 아니다. **`CLAUDE.md`가 있으면 `AGENTS.md`는 조용히 빠진다.**

판정에 쓰이는 파일도 정해져 있다.

- **판정에 포함** (있으면 `AGENTS.md`를 밀어냄): 작업 디렉터리나 그 위의 `CLAUDE.md`, `.claude/CLAUDE.md`, `CLAUDE.local.md`
- **판정에서 제외** (있어도 `AGENTS.md`가 같이 로드됨): `~/.claude/CLAUDE.md`, 조직 관리형 `CLAUDE.md`, `.claude/rules/`

> **흔한 함정.** `AGENTS.md`로 돌아가는 프로젝트에 내 개인 메모를 `CLAUDE.local.md`로 추가하면,
> 그 순간부터 **Claude가 `AGENTS.md`를 안 읽는다.** 팀 지시가 통째로 빠지는데 에러는 안 난다.
{: .prompt-warning }

읽었는지는 세션 시작 메시지로 확인할 수 있다.

```text
no CLAUDE.md found; AGENTS.md loaded: /home/you/repo/AGENTS.md
```

이 줄이 없는데 `AGENTS.md`가 있다면, 어딘가에 `CLAUDE.md`가 있다는 뜻이다.

## 둘 다 읽게 하기

기본 동작이 마음에 안 들면 바꿀 수 있다. `/config` → **Project instructions**.

| 값 | 읽는 것 |
|---|---|
| `claude-md-or-agents-md` | `CLAUDE.md`, 없으면 `AGENTS.md` **(기본값)** |
| `claude-md-and-agents-md` | **둘 다.** 디렉터리마다 `CLAUDE.md` 먼저, `AGENTS.md` 나중 |
| `claude-md` | `CLAUDE.md`만 |
| `managed-only` | 조직 관리형 지시와 자동 메모리만 |

설정 파일로도 된다. 단 **사용자 설정이나 관리형 설정에서만 읽히고, 프로젝트·로컬 설정에서는 무시된다.**

```json
{
  "pluginConfigs": {
    "cc-plugin-agents-md@builtin": {
      "options": { "instructionFiles": "claude-md-and-agents-md" }
    }
  }
}
```

## 그래서 어떻게 두면 되나

**① Claude Code만 쓴다** → `CLAUDE.md` 하나. 끝.

**② 여러 도구를 쓰는데 지시가 같다** → `AGENTS.md` 하나만 두고 `CLAUDE.md`를 만들지 않는다.
Claude Code가 알아서 읽는다. 추가 설정도, import도 필요 없다.

**③ 여러 도구를 쓰는데 Claude 전용 지시가 따로 있다** → 공통은 `AGENTS.md`,
Claude 전용은 `CLAUDE.md`에 두고 **import로 묶는다.**

```markdown
<!-- CLAUDE.md -->
@AGENTS.md

## Claude Code 전용

- 테마 파일을 덮어쓸 때는 파일 머리에 이유를 주석으로 남긴다
- 커밋 메시지는 한국어로
```

②가 제일 깔끔하다. **파일을 하나만 유지하면 두 개가 어긋날 일이 없다.**

## 내용은 어느 쪽이든 같다

파일 이름이 뭐든 안에 쓸 것은 같다. **매번 다시 설명하게 되는 것**을 적는다.

- Claude가 같은 실수를 두 번째로 했을 때
- 지난 세션에 쳤던 교정을 또 치고 있을 때
- 새 팀원이라면 똑같이 알아야 할 맥락일 때

반대로 **길어지면 안 된다.** 이 파일은 세션 시작할 때 통째로 컨텍스트에 들어가고,
**관련 없는 작업을 할 때도 계속 들어 있다.** 공식 권장은 200줄 이하다.

특정 작업에만 쓰는 긴 절차(PR 리뷰 체크리스트, 마이그레이션 순서)는
**스킬로 빼면 호출할 때만 로드된다.**

## 정리

| 상황 | 둘 것 |
|---|---|
| Claude Code만 | `CLAUDE.md` |
| 여러 도구, 같은 지시 | `AGENTS.md` 하나 (Claude가 알아서 읽음) |
| 여러 도구, Claude 전용 지시 있음 | `CLAUDE.md`에서 `@AGENTS.md` import |
| 둘 다 그대로 읽히게 | `/config` → Project instructions → `claude-md-and-agents-md` |

기억할 건 하나다. **`CLAUDE.md`가 있으면 `AGENTS.md`는 조용히 무시된다.**
에러가 안 나기 때문에, 적어둔 지시가 안 먹는데 이유를 모르는 상황이 여기서 나온다.
