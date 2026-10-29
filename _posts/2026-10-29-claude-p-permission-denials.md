---
title: "claude -p가 성공(exit 0)이라는데 파일이 없을 때"
description: "비대화형 claude -p는 권한이 필요한 도구 호출을 조용히 거절하고도 종료 코드 0, is_error false로 끝난다. 실제로 일을 했는지는 permission_denials로 가린다."
date: 2026-10-29 09:10:00 +0900
categories: [AI 에이전트, Claude Code]
tags: [claude-p, permission-denials, allowedtools]
---

> 2026-10 기준, Claude Code 2.1.312에서 직접 돌린 결과다. 동작 설명의 근거는 공식 문서 [Run Claude Code programmatically](https://code.claude.com/docs/en/headless)다.
{: .prompt-info }

스크립트나 CI에서 `claude -p "..."`를 돌렸는데 종료 코드는 0이고 로그에도 에러가 없다. 그런데 만들라던 파일이 없다.
증상은 같아도 원인은 둘로 갈린다. **Claude가 일을 안 한 것**과 **일을 하려다 권한에 막힌 것**이다. 이 글은 두 번째를 가리는 방법이다.

## 재현

빈 디렉터리에서 아무 옵션 없이 실행했다.

```bash
claude -p "Create a file b.txt containing ok using Bash: echo ok > b.txt" --output-format json
echo "exit=$?"; ls b.txt
```

```text
exit=0
ls: cannot access 'b.txt': No such file or directory
```

JSON에서 추린 필드:

```json
{"is_error":false,"subtype":"success","permission_denials":["Bash"]}
```

`result` 필드에는 이렇게 적혀 있었다.

```text
I couldn't create `b.txt`. The shell command `echo ok > b.txt` was blocked because writing files in `/tmp/claude-0/pt` needs your approval, and none was given.
```

문서에 따르면 `claude -p`에서 승인이 필요한 호출은 승인해 줄 무언가(`PermissionRequest` 훅, `--permission-prompt-tool`)가 없으면 거절된다. 물어볼 사람이 없으니 막힌 채로 끝나고, Claude는 그 사실을 말로 설명한 뒤 **정상 종료**한다. 종료 코드와 `is_error`는 "실행이 에러 없이 끝났는가"만 말해 준다.

## 판별법

| | 일을 안 한 경우 | 권한에 막힌 경우 |
|---|---|---|
| 종료 코드 | 0 | 0 |
| `is_error` | false | false |
| `permission_denials` | 빈 배열 | **막힌 호출이 들어 있음** |

`--output-format json` 응답의 `permission_denials`가 비어 있지 않으면 막힌 것이다. 각 항목에 `tool_name`과 `tool_input.command`가 그대로 들어 있어서, 무엇을 허용해야 하는지도 거기서 읽는다.

```bash
claude -p "..." --output-format json | jq -e '.permission_denials | length == 0'
```

`jq -e`는 결과가 false면 종료 코드 1을 내므로 CI 단계에 그대로 쓸 수 있다.

## 풀기: 허용 규칙은 명령 전체에 맞아야 한다

같은 프롬프트로 네 가지를 비교했다. 결과는 `b.txt`가 생겼는지, `permission_denials`가 몇 건인지다.

| 옵션 | b.txt | denials |
|---|---|---|
| (없음) | 없음 | 1 |
| `--allowedTools "Bash(echo *)"` | **없음** | 1 |
| `--allowedTools "Bash(ls *)"` | 없음 | 1 |
| `--permission-mode acceptEdits` | 생김 | 0 |

두 번째 줄이 함정이다. `Bash(echo *)`를 줬는데도 막혔다. 막힌 호출은 `echo ok > b.txt`였다. 같은 규칙으로 리다이렉션 없는 `echo ok`를 시키면 `permission_denials`가 0건이고 결과도 `ok`로 나온다.
즉 `echo`로 시작한다는 이유로 `>` 파일 쓰기까지 허용되지는 않았다. `Bash(echo * > b.txt)`처럼 리다이렉션까지 적은 규칙도 시험했지만 같은 호출이 그대로 막혔다. 이 환경에서는 이유까지 확인하지 못했고, 막힌 명령 문자열을 `permission_denials`에서 읽어 규칙을 맞추는 쪽이 확실했다.

파일을 쓰는 작업이라면 `--allowedTools`로 명령을 하나씩 열기보다 `--permission-mode acceptEdits`를 기준선으로 두는 편이 덜 헷갈린다. 문서상 `acceptEdits`는 파일 쓰기와 `mkdir`, `touch`, `mv`, `cp` 같은 흔한 파일시스템 명령을 자동 승인하고, 그 밖의 셸 명령과 네트워크 요청에는 여전히 허용 규칙이 필요하다.

> 실험한 것은 위 네 가지뿐이다. `dontAsk`나 `auto` 모드, `--permission-prompts none`은 문서만 읽었고 돌려 보지 않았다.
{: .prompt-warning }
