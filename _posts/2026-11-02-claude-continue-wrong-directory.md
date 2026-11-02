---
title: "claude --continue 했는데 이전 대화가 없을 때: 세션은 디렉터리별로 저장된다"
description: "claude -p --continue를 다른 디렉터리에서 돌리면 에러 없이 exit 0으로 빈 새 대화가 시작된다. 대화가 사라진 게 아니라 cwd가 달랐던 것인지, ~/.claude/projects 폴더로 가려내는 법."
date: 2026-11-02 09:00:00 +0900
categories: [AI 에이전트, Claude Code]
tags: [세션, resume, claude-p]
---

> 2026-11 기준, Claude Code 2.1.316에서 확인했다. 명령과 동작은 버전마다 바뀔 수 있다.
{: .prompt-info }

어제 하던 대화를 `claude --continue`로 이어가려는데 맥락이 없다면, 대화가 지워진 게 아니라 **다른 디렉터리에서 실행했을 가능성이 크다.** 세션은 "마지막 대화"가 아니라 "이 디렉터리의 마지막 대화"로 저장된다. 스크립트에서 `claude -p --continue`를 쓰면 이게 에러도 없이 지나가서 더 알아채기 어렵다.

## 공식 문서가 말하는 것

[Manage sessions](https://code.claude.com/docs/en/sessions)에서 읽은 내용이다.

- `claude --continue`는 "Reopens the most recent session **in the current directory**".
- 세션은 `~/.claude/projects/<project>/<session-id>.jsonl`에 저장되고, `<project>`는 작업 디렉터리 경로에서 영숫자가 아닌 문자를 `-`로 바꾼 이름이다.
- 문서의 [common workflows](https://code.claude.com/docs/en/common-workflows#resume-previous-conversations)는 대화가 없으면 `No conversation found to continue`를 출력하고 종료한다고 적는다. (이 메시지는 대화형으로는 재현하지 못했다. 샌드박스에서 TTY를 못 띄웠다.)
- `claude -p`와 Agent SDK로 만든 세션은 대화형 `--continue`와 세션 선택 화면에서 빠지지만, `claude -p --continue`는 이들을 포함한다.

## 직접 돌려 본 결과

`d3`에서 대화를 하나 만들고 `--continue`로 이어간 뒤, 한 번도 쓴 적 없는 `d4`에서 같은 `--continue`를 돌렸다.

```bash
cd /tmp/claude-0/d3
claude -p --output-format json "기억해: 암호는 PINEAPPLE. 'ok'라고만 답해."
claude -p --continue --output-format json "암호가 뭐였지? 모르면 '모름'이라고 답해."
# → "result":"PINEAPPLE","is_error":false

cd /tmp/claude-0/d4
claude -p --continue --output-format json "암호가 뭐였지? 모르면 '모름'이라고 답해."
echo "exit=$?"
# → exit=0
# → "result":"모름. 이 대화에서는 암호가 언급된 적이 없고, ...","is_error":false
```

`d4`에는 이어갈 대화가 없는데도 `-p` 모드에서는 **에러 없이 종료 코드 0**이고 `is_error`도 `false`다. 빈 새 대화가 시작됐을 뿐이다. 이 점은 문서의 `No conversation found to continue` 설명과 다르게 보이지만, 내가 확인한 건 `-p` 쪽뿐이다.

## 판별법: 대화가 사라졌나, 위치가 달랐나

현재 디렉터리가 어느 저장 폴더에 대응하는지 계산해서 열어 본다.

```bash
p=~/.claude/projects/$(pwd | sed 's/[^[:alnum:]]/-/g')
ls "$p"
grep -c PINEAPPLE "$p"/*.jsonl
```

실제 출력:

```text
/root/.claude/projects/-tmp-claude-0-d3   → 517326fc-....jsonl   (PINEAPPLE 7회)
/root/.claude/projects/-tmp-claude-0-d4   → 517326fc-....jsonl   (PINEAPPLE 0회)
```

- 이전 작업 디렉터리 쪽 폴더에 `.jsonl`이 있으면: 대화는 살아 있다. **그 디렉터리로 `cd`해서** 다시 실행하거나 `claude --resume`(선택 화면에서 `Ctrl+A`로 모든 프로젝트 보기)를 쓴다.
- 어느 폴더에도 없으면: 보존 기간이 지났을 수 있다. 문서상 기본 보존은 30일이고 `cleanupPeriodDays`로 바꾼다.

## 같이 알아 둘 것

- **세션 ID를 알면 어느 디렉터리에서든** `claude --resume <session-id>`로 열 수 있다고 문서는 적는다. 다만 ID가 하나도 일치하지 않으면 `No conversation found with session ID: <id>`가 나온다. 존재하지 않는 ID로 `-p --resume`을 돌렸을 때 이 문구와 종료 코드 1을 확인했다.
- 이름을 붙여 두면(`claude -n auth-refactor`, 세션 안에서 `/rename`) `claude --resume auth-refactor`로 이어갈 수 있다.
- 자동화 스크립트에서 `--continue`에 기대려면 매번 같은 디렉터리에서 실행해야 한다. 아니면 결과의 `result`가 이전 맥락을 반영하는지 검사하는 편이 안전하다.

> 이 샌드박스는 환경변수 `CLAUDE_CODE_SESSION_ID`로 세션 ID를 고정해서, 위 실험의 JSON에서는 `session_id`가 두 디렉터리에서 같게 나왔다. 그래서 세션 ID 대신 저장 폴더와 대화 내용으로 판별했다. 일반 환경에서는 이 변수가 없으므로 이 부분을 그대로 적용하지 말 것.
{: .prompt-warning }
