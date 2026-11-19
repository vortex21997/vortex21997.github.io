---
title: "Codex가 AGENTS.md 뒷부분을 무시할 때: project_doc_max_bytes 32KiB 한도"
description: "Codex는 AGENTS.md를 합쳐 32KiB(32768바이트)까지만 읽는다. 한글 문서는 글자 수가 아니라 바이트로 세므로 약 1만 8천 자에서 잘릴 수 있다. 공식 문서 기준 한도와 확인법, 늘리는 설정을 정리했다."
date: 2026-11-19 09:00:00 +0900
categories: [AI 에이전트, 다른 도구]
tags: [codex, agents-md, project_doc_max_bytes]
---

AGENTS.md 아래쪽에 적은 규칙만 Codex가 따르지 않는다면, 파일이 **합쳐서 32KiB(32768바이트)** 한도에서 잘렸을 가능성이 있다. 한도는 `config.toml`의 `project_doc_max_bytes`로 올린다. 한글 문서는 글자 수가 아니라 **바이트**로 세기 때문에 생각보다 빨리 닿는다.

> 2026-11 기준. 아래 동작은 공식 문서를 읽고 정리한 것이고, 이 샌드박스에는 Codex CLI가 없어 `codex` 명령은 직접 돌려보지 못했다. 바이트 계산만 직접 실행했다.
{: .prompt-info }

## 문서에 적힌 동작

[Codex 공식 AGENTS.md 가이드](https://learn.chatgpt.com/docs/agent-configuration/agents-md)(옛 주소 `developers.openai.com/codex/guides/agents-md`가 여기로 리다이렉트된다)에서 읽은 내용이다.

- 프로젝트 루트부터 현재 디렉터리까지 내려오며 **디렉터리마다 `AGENTS.override.md` → `AGENTS.md` → 폴백 이름** 순으로 찾고, 디렉터리당 최대 한 파일만 쓴다.
- 파일은 루트부터 아래로 이어 붙인다. 현재 디렉터리에 가까운 파일이 뒤에 오므로 앞의 지침을 덮는다.
- 기본 `project_doc_max_bytes`는 32 KiB. 문서 표현으로는 합친 크기가 한도에 닿으면 파일 추가를 멈춘다("stops adding files once the combined size reaches the limit").
- 잘림 대처로 문서가 권하는 방법: "Raise `project_doc_max_bytes` or split large files across nested directories".

## 한글은 바이트로 센다

한도 단위가 바이트라서 같은 글자 수라도 한글이 훨씬 빨리 찬다. 이 저장소의 `CLAUDE.md`로 확인했다.

```bash
export LC_ALL=C.UTF-8
python3 -c "
s=open('CLAUDE.md',encoding='utf-8').read()
print(len(s), len(s.encode()), round(32768/(len(s.encode())/len(s))))"
```

```text
10740 19666 17895
```

글자 10,740자가 19,666바이트다. 이 비율(글자당 약 1.83바이트)이 계속된다면 약 17,900자에서 32KiB에 닿는다. 영문만 쓴 파일이면 3만 자 넘게 들어간다. 글자당 3바이트 원리는 [UTF-8 한글 3바이트 글](/posts/utf8-hangul-3-bytes-len/)에서 다뤘다.

## 잘렸는지 판별하는 기준

증상이 같아도 원인이 다른 경우가 있다.

| 확인 | 결과 | 의미 |
|---|---|---|
| `wc -c AGENTS.md`(루트부터 현재 디렉터리까지 모두 합산) | 32768 미만 | 한도 문제가 아님. 다른 디렉터리의 `AGENTS.override.md`가 가리는지 본다 |
| 같은 합계가 32768 이상 | | 뒷부분이 잘렸을 수 있음 |
| `codex --cd <하위디렉터리> --ask-for-approval never "Show which instruction files are active."` | 기대한 파일이 목록에 없음 | 이름이 다르거나(폴백 이름 미등록) override가 대신 읽힘 |

`wc -c`는 로케일과 무관하게 바이트를 센다. 위 `wc -m`(글자 수)은 로케일이 UTF-8이어야 제대로 나오니 헷갈리지 말 것.

문서가 소개하는 로그 확인법도 있다. `codex -c log_dir=./.codex-log`로 실행한 뒤 `./.codex-log/codex-tui.log`를 보면 된다.

## 한도를 올리기

`~/.codex/config.toml`(문서의 예시 그대로):

```toml
project_doc_fallback_filenames = ["TEAM_GUIDE.md", ".agents.md"]
project_doc_max_bytes = 65536
```

`65536`은 64KiB다. 다만 지침이 길어질수록 매 요청의 컨텍스트를 더 쓰므로, 올리기 전에 꼭 필요한 규칙만 남기고 하위 디렉터리의 AGENTS.md로 나누는 쪽을 문서도 먼저 권한다.
