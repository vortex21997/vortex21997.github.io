---
title: "GEMINI.md의 @import가 'Path traversal attempt'로 실패할 때: .git 밖 파일은 못 가져온다"
description: "Gemini CLI의 GEMINI.md에서 @../shared/style.md 같은 import가 <!-- Import failed: ... - Path traversal attempt --> 주석으로 바뀌고 내용이 안 들어올 때. 프로젝트 루트(.git 기준) 밖 경로는 거부되고, 없는 파일·순환·깊이 한도는 다른 주석으로 나온다. 소스 기준 판별법."
date: 2026-11-26 09:00:00 +0900
categories: [AI 에이전트, 다른 도구]
tags: [gemini-cli, gemini-md, memory-import]
---

**결론:** GEMINI.md 안의 `@경로` import는 **프로젝트 루트 안의 파일만** 가져온다. 루트는 GEMINI.md가 있는 디렉터리에서 위로 올라가며 처음 만나는 `.git`이 있는 폴더다. 저장소 밖(`@../shared/style.md`처럼 루트를 벗어나는 경로)이나 URL은 내용 대신 아래 주석으로 바뀐다.

```
<!-- Import failed: ../shared/style.md - Path traversal attempt -->
```

> 2026-11 기준. **이 글은 소스를 읽은 내용이다. 직접 돌려서 확인한 출력은 없다.** `@google/gemini-cli-core` 0.71.1을 설치해 `dist/src/utils/memoryImportProcessor.js`의 문자열이 `main` 브랜치 소스와 같은 것까지만 `grep`으로 확인했고, 처리기를 실행하는 단계는 샌드박스 권한 때문에 못 했다.
{: .prompt-warning }

## 근거

- 공식 문서: [GEMINI.md](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/gemini-md.md)는 `@./components/instructions.md`, `@../shared/style-guide.md` 같은 상대·절대 경로를 지원한다고 쓴다. 이 예시에 `../`가 있어서 "저장소 밖도 되겠지"로 읽기 쉽다.
- [Memory Import Processor](https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/memport.md): "imports are only allowed from specified directories"(`validateImportPath`), 최대 깊이 기본 5단계, 순환 import 감지, 코드 블록·인라인 코드 안의 `@`는 무시한다고 쓴다. **허용 디렉터리가 어디인지, 실패하면 무엇이 보이는지는 문서에 없다.**
- 소스: [`memoryImportProcessor.ts`](https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/utils/memoryImportProcessor.ts). 아래 내용은 모두 여기서 읽었다.

## 소스에서 읽은 규칙

- 허용 디렉터리는 `projectRoot` 하나다. 넘겨받지 않으면 `findProjectRoot`가 `.git`(기본 경계 표식)을 찾을 때까지 위로 올라가고, 못 찾으면 시작 디렉터리를 쓴다. 심볼릭 링크는 실제 경로로 바꾼 뒤 비교하므로, 루트 안의 링크가 밖을 가리켜도 거부된다.
- `file://`, `http://`, `https://`로 시작하는 경로는 무조건 거부된다.
- import로 인식되는 `@`는 **앞이 공백이거나 줄 처음**이고, 바로 뒤가 `.`, `/`, 영문자인 경우다. `me@example.com`은 `@` 앞이 글자라 import가 아니다. 반면 문장 속 ` @bob`은 형식이 맞아 import 후보가 되고, 파일이 없으면 실패 주석이 된다.
- 백틱(`` ` ``)으로 감싼 구간 안의 `@`는 그대로 둔다.

## 주석으로 가르는 원인

증상은 "import한 내용이 안 보인다"로 같지만 `/memory show`에서 보이는 주석이 다르다. 이 주석 문자열(`memoryImportProcessor.js` 0.71.1에서도 확인)이 판별 기준이다.

| 보이는 주석 | 원인 | 조치 |
|---|---|---|
| `<!-- Import failed: ../shared/style.md - Path traversal attempt -->` | 프로젝트 루트(`.git` 기준) 밖이거나 URL | 파일을 저장소 안으로 옮기거나 링크가 아닌 복사본을 둔다 |
| `<!-- Import failed: ./docs/missing.md - ENOENT: no such file or directory, ... -->` | 경로는 허용 범위 안인데 파일이 없다 (메시지는 Node의 오류 메시지가 그대로 붙는다) | 경로·대소문자 확인 |
| `<!-- File already processed: ./a.md -->` | 같은 import 체인에서 이미 가져온 파일 (순환 또는 중복) | 의도한 중복인지 확인 |
| 주석 없이 `@./deep.md` 글자가 그대로 남음 | 깊이 한도(기본 5단계)에서 처리를 멈췄다. 이때는 경고 로그만 남고 본문 주석은 없다 | import 체인을 줄인다 |
| 가져오기 성공 | `<!-- Imported from: ./docs/rules.md -->` … `<!-- End of import from: ./docs/rules.md -->`로 감싸 들어온다 | — |

주의: `.git`이 없는 폴더(압축만 푼 소스, 임시 디렉터리)에서는 루트가 GEMINI.md가 있는 폴더 자신이 된다. 이때는 `@./docs/rules.md`처럼 같은 폴더 아래 파일만 허용되고, 형제 폴더를 가리키는 `../`는 전부 거부된다. 저장소 안인데도 `Path traversal attempt`가 나오면 루트 판정부터 의심한다.

## 어떻게 확인하나

1. 대화형 세션에서 `/memory show`를 실행하면 [공식 문서](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/gemini-md.md)상 "현재 계층 메모리의 전체 합쳐진 내용"이 나온다. 위 주석이 거기에 들어 있는지 찾는다.
2. 파일을 고친 뒤에는 `/memory reload`로 다시 읽힌다(문서: "모든 위치의 GEMINI.md를 다시 스캔").

내가 확인하지 못한 것: `/memory show` 화면에 주석이 실제로 그대로 노출되는지(처리기의 반환 문자열에 들어간다는 것까지만 소스로 읽었다), 그리고 0.71.1 이후 버전의 동작이다. 버전이 올라가면 `memoryImportProcessor.ts`를 다시 확인한다.

같은 설정 계열로, 파일 이름 문제는 [Gemini CLI가 AGENTS.md를 안 읽을 때](/posts/gemini-cli-agents-md-context-filename/)에서 다뤘다. 이 글은 파일은 찾았는데 그 안의 import가 막히는 경우다.
