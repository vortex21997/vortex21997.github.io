---
title: "Codex에서 '--ask-for-approval untrusted'와 '--full-auto'가 invalid value로 막힐 때"
description: "예전 글에 나온 Codex CLI 승인 옵션 untrusted와 --full-auto가 최신 버전에서 에러를 낸다. 지금 쓸 수 있는 sandbox·approval 조합과 직접 확인한 출력을 정리했다."
date: 2026-11-05 09:00:00 +0900
categories: [AI 에이전트, 다른 도구]
tags: [codex, sandbox, approval-policy]
---

**결론:** Codex CLI `0.166.0`에서는 `--ask-for-approval untrusted`와 `--full-auto`가 받아들여지지 않는다. 승인 정책은 `on-request`와 `never`만 남았고, `--full-auto` 자리는 `--sandbox workspace-write --ask-for-approval on-request` 조합이 대신한다.

> 2026-11 기준, `codex-cli 0.166.0`에서 직접 실행한 결과다. 옵션은 버전마다 바뀌므로 `codex --help`로 먼저 확인한다.
{: .prompt-info }

## 나온 에러 (원문)

```console
$ codex -a untrusted exec --skip-git-repo-check "hi"
error: invalid value 'untrusted' for '--ask-for-approval <APPROVAL_POLICY>'
  [possible values: on-request, never]

$ codex exec --full-auto "x"
error: unexpected argument '--full-auto' found

  tip: to pass '--full-auto' as a value, use '-- --full-auto'
```

옛 블로그 글이나 README의 예시를 그대로 붙여넣으면 이렇게 된다.

## 지금 쓸 수 있는 값

`codex --help`에서 확인한 값이다.

```console
-s, --sandbox <SANDBOX_MODE>
    [possible values: read-only, workspace-write, danger-full-access]
-a, --ask-for-approval <APPROVAL_POLICY>
    - on-request: The model decides when to ask the user for approval
    - never:      Never ask for user approval Execution failures are immediately returned to the model
```

공식 문서([Agent approvals & security](https://learn.chatgpt.com/docs/agent-approvals-security))는 같은 내용을 이렇게 설명한다. 이 부분은 문서에서 읽은 것이고 직접 돌려보지는 않았다.

- `untrusted`는 **retired**다. 더 엄격하게 하려면 `approval_policy`를 생략하고 `[projects."/path/to/project"]` 아래에 `trust_level = "untrusted"`를 둔다.
- "Auto" 프리셋은 `--sandbox workspace-write --ask-for-approval on-request`다.
- `--dangerously-bypass-approvals-and-sandbox`(별칭 `--yolo`)는 샌드박스도 승인도 없다.
- 설정 파일 키는 `sandbox_mode`, `approval_policy`다.

## 판별법: 승인 문제인가, 샌드박스 문제인가

두 설정은 서로 다른 것을 막는다. 증상이 비슷해서 헷갈린다.

| 보이는 것 | 원인 | 조정할 것 |
|---|---|---|
| CLI가 `invalid value`/`unexpected argument`로 바로 종료 | 없어진 옵션 | 위 값으로 교체 |
| 실행은 되는데 명령이 `Read-only file system`으로 실패 | **샌드박스**가 쓰기를 막음 | `--sandbox` |
| 매번 승인을 묻는다 | **승인 정책** | `--ask-for-approval` |

샌드박스가 쓰기를 막는 모습은 `codex sandbox`로 직접 봤다. 기본 정책에서 파일을 쓰려고 하면 이렇게 된다.

```console
$ codex sandbox -- sh -c 'echo hi > a.txt; echo rc=$?'
sh: 1: cannot create a.txt: Read-only file system
rc=2
```

이때 `--ask-for-approval never`를 줘도 소용없다. 승인을 안 묻는 것일 뿐, 샌드박스가 허용하는 범위는 그대로이기 때문이다(문서: `never`는 "still works within the chosen sandbox mode"). 쓰기가 필요하면 `--sandbox workspace-write`를 준다.

## 네트워크는 따로 꺼져 있다

문서에 따르면 기본값은 네트워크 꺼짐이고, `workspace-write`에서도 아래를 켜야 한다.

```toml
[sandbox_workspace_write]
network_access = true
```

`npm install`이 샌드박스 안에서 실패하면 승인이 아니라 이쪽을 본다. 이 항목은 문서에서만 확인했다.
