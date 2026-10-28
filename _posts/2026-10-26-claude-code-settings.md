---
title: "Claude Code를 제대로 쓰려면 알아야 할 네 가지"
description: "매번 같은 설명을 반복하고, 매번 같은 허락을 누르고 있다면 설정을 안 쓰고 있는 것이다. CLAUDE.md, settings.json, 권한 규칙, 훅."
date: 2026-10-26 14:20:00 +0900
categories: [AI 에이전트, Claude Code]
tags: [claude-md, settings-json, 권한, 훅]
---

Claude Code를 설치하고 그냥 쓰면 이렇게 된다.

- 세션을 열 때마다 "이 프로젝트는 이런 구조고, 테스트는 이렇게 돌려"를 다시 설명한다
- `npm test`를 돌릴 때마다 허락 버튼을 누른다
- 커밋 메시지 형식을 매번 말해준다

**전부 설정으로 없앨 수 있는 일이다.** 레버는 네 개다.

## 1. CLAUDE.md — 매번 하는 설명을 한 번만

프로젝트 루트에 `CLAUDE.md`를 두면 세션 시작할 때 자동으로 읽는다.
**매번 타이핑하던 설명을 여기로 옮기는 것**이 가장 먼저 할 일이다.

```markdown
# 프로젝트

Jekyll + Chirpy로 만든 기술 블로그. GitHub Actions로 배포된다.

## 명령어

- 빌드: `JEKYLL_ENV=production bundle exec jekyll build`
- 로컬 확인: `bundle exec jekyll serve`

## 규칙

- 글은 `_posts/YYYY-MM-DD-영문슬러그.md`. 파일명 슬러그가 URL이 된다.
- 테마 파일을 덮어쓸 때는 파일 머리에 이유를 주석으로 남긴다.
- 커밋 메시지는 한국어로, 제목 + 빈 줄 + 본문.
```

요령이 하나 있다. **"하지 마라"보다 "이렇게 해라"가 잘 먹는다.**
"`_site`를 커밋하지 마"보다 "빌드 산출물은 `.gitignore`에 있다"가 낫다.

파일은 한 곳에만 둘 수 있는 게 아니다.

| 위치 | 적용 범위 |
|---|---|
| `~/.claude/CLAUDE.md` | 내 모든 프로젝트 |
| `프로젝트/CLAUDE.md` | 그 프로젝트 (커밋해서 팀과 공유) |
| `하위폴더/CLAUDE.md` | 그 폴더에서 작업할 때 추가로 |

## 2. settings.json — 어디에 쓰느냐가 곧 적용 범위

설정 파일은 네 개이고, **파일을 고르는 것이 곧 "누구에게 적용할지"를 고르는 것**이다.

| 파일 | 적용 대상 | 쓰임 |
|---|---|---|
| `~/.claude/settings.json` | 이 기기의 나, 모든 프로젝트 | 테마, 기본 모델, 내 권한 규칙 |
| `.claude/settings.json` | 이 폴더에서 작업하는 모두 | 팀 권한·훅·플러그인 (커밋한다) |
| `.claude/settings.local.json` | 이 프로젝트의 나만 | 개인 예외 (깃에 안 올라감) |
| 관리형 설정 | 조직이 배포 | 보안 정책 |

같은 키가 여러 곳에 있으면 **위에서부터 이긴다.**

```
관리형  >  --settings 플래그  >  project local  >  shared project  >  user
```

### 리스트는 덮지 않고 합쳐진다

`permissions.allow` 같은 목록형 키는 예외다. **높은 쪽이 낮은 쪽을 지우지 않고 합친다.**
팀 파일의 허용 규칙과 내 개인 규칙이 둘 다 살아 있다는 뜻이다.

### 설정이 안 먹을 때

추측하지 말고 확인하면 된다.

```console
$ /status          # 어떤 설정 파일이 로드됐는지
$ claude doctor    # 거부된 항목과 그 이유
```

`settings.json`은 **엄격한 JSON**이다. `//` 주석이나 끝 쉼표 하나로 파일 전체가 무시된다.
이 경우 시작할 때 "Settings Error"로 알려준다.

## 3. 권한 규칙 — 허락 버튼 없애기

제일 체감이 큰 부분이다. 자주 쓰는 안전한 명령을 미리 허용해두면 프롬프트가 사라진다.

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "allow": [
      "Bash(bundle exec jekyll build)",
      "Bash(git status)",
      "Bash(git diff *)",
      "Bash(npm run lint)"
    ],
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)"
    ]
  }
}
```

`allow`는 "묻지 말고 실행", `deny`는 "아예 금지"다.
`.env` 같은 비밀 파일은 **읽기 자체를 막아두는 게 맞다.**

`$schema` 줄을 넣어두면 VS Code 같은 편집기에서 자동완성과 검증이 붙는다. 오타로 날리는 시간이 준다.

> 허락 프롬프트에서 **"Yes, and don't ask again"** 을 누르면
> 그 규칙이 `.claude/settings.local.json`에 자동으로 저장된다.
> 한동안 쓰다가 그 파일을 열어보면 내가 자주 쓰는 명령 목록이 이미 만들어져 있다.
> 거기서 팀과 공유할 것만 골라 `.claude/settings.json`으로 옮기면 된다.
{: .prompt-tip }

## 4. 훅 — "매번 ~해줘"를 자동으로

"커밋 전에 린트 돌려줘" 같은 걸 매번 말하고 있다면, 그건 훅이 할 일이다.
설정에 적어두면 **Claude가 아니라 도구 자체가** 실행한다.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "npm run lint --silent" }
        ]
      }
    ]
  }
}
```

구조가 세 겹이다. **이벤트 → 매처 → 핸들러.**

주요 이벤트는 이 정도를 알면 충분하다.

| 이벤트 | 시점 |
|---|---|
| `SessionStart` | 세션 시작·재개 |
| `UserPromptSubmit` | 내가 프롬프트를 보낸 직후, 처리 전 |
| `PreToolUse` | 도구 실행 전 — **막을 수 있는 지점** |
| `PostToolUse` | 도구 실행 성공 후 |
| `Stop` | 응답이 끝났을 때 |

### 막는 방법은 종료 코드

훅은 이벤트 JSON을 stdin으로 받고, **종료 코드로 판단을 돌려준다.**

| 종료 코드 | 결과 |
|---|---|
| `0` | 통과 |
| `2` | **차단.** stderr가 Claude에게 이유로 전달된다 |
| 그 외 | 통과하되 기록만 남음 (`1`도 **차단하지 않는다**) |

`exit 1`이 차단일 거라고 생각하기 쉬운데 아니다. **차단은 `2`다.**

더 세밀하게 하려면 `0`으로 끝내면서 JSON으로 판단을 내보낸다.

```bash
#!/bin/bash
CMD=$(jq -r '.tool_input.command')
if echo "$CMD" | grep -q 'rm -rf'; then
  jq -n '{hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: "위험한 명령이라 훅이 막았습니다"
  }}'
else
  exit 0
fi
```

주의할 점 두 가지.

- 훅은 **현재 작업 디렉터리**에서 돌아간다. 경로는 `${CLAUDE_PROJECT_DIR}`를 쓰거나 절대 경로로.
- 출력이 전부 컨텍스트로 들어간다. `--silent`, `-q` 같은 걸 붙여 조용하게 만드는 게 좋다.

## 클라우드 세션은 다르다

브라우저에서 돌리는 [클라우드 세션](https://code.claude.com/docs/en/claude-code-on-the-web)은
**내 기기가 아니라 저장소를 새로 클론한 컨테이너**에서 돈다. 읽는 설정이 다르다.

| 설정 | 클라우드 세션 |
|---|---|
| `프로젝트/CLAUDE.md` | ✅ 클론에 포함되므로 읽힘 |
| `.claude/settings.json` | ✅ 저장소 하나짜리 세션이면 읽힘 |
| `~/.claude/settings.json` | ❌ 내 기기에 있음 |
| `.claude/settings.local.json` | ❌ 깃에 없음 |

즉 **커밋한 것만 따라간다.** 클라우드에서도 쓰고 싶은 설정은 `.claude/settings.json`에 넣고 커밋해야 한다.

참고로 이 블로그는 클라우드 세션에서 만들었다.
테마 수정부터 커밋·푸시·배포 확인까지 전부 거기서 돌았고,
그래서 `~/.claude`에 있던 내 개인 설정은 하나도 안 따라왔다.

## 정리

| 증상 | 고칠 곳 |
|---|---|
| 매번 같은 설명을 한다 | `CLAUDE.md` |
| 매번 허락을 누른다 | `permissions.allow` |
| 매번 "~도 해줘"라고 한다 | `hooks` |
| 설정이 안 먹는다 | `/status`, `claude doctor` |

네 개 중 **`CLAUDE.md`와 `permissions.allow` 두 개만 해도** 체감이 크게 달라진다.
훅은 반복이 확실히 보일 때 추가하면 된다.
