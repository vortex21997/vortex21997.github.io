---
title: ".gitignore에 넣었는데 git status에 계속 뜰 때: 이미 추적 중인 파일은 무시되지 않는다"
description: ".env를 .gitignore에 적었는데도 수정 표시(M)가 계속 뜨는 이유와, git check-ignore가 아무것도 안 보여주는 함정, git rm --cached로 푸는 방법. 히스토리에 남은 값은 그대로라는 점까지."
date: 2026-11-28 09:00:00 +0900
categories: [개발 환경, Git·GitHub]
tags: [gitignore, git-rm-cached, git-check-ignore]
---

`.gitignore`에 `.env`를 적었는데 `git status`에는 여전히 ` M .env`가 뜬다. 원인은 그 파일이 **이미 커밋된 적이 있어서**다.
`.gitignore`는 "아직 추적하지 않는 파일을 계속 추적하지 않게" 하는 규칙이라, 이미 추적 중인 파일에는 효과가 없다.
`git rm --cached <파일>`로 추적만 끊으면 풀린다. (Git 2.43.0, Linux에서 확인)

## 재현

```bash
git init -q -b main .
echo "KEY=1" > .env; echo hi > app.txt
git add .; git commit -qm init       # .env가 이미 커밋됨

echo ".env" > .gitignore             # 뒤늦게 무시 규칙 추가
echo "KEY=2" > .env                  # 값 수정
git status -s
```

```
 M .env
?? .gitignore
```

`.gitignore`가 있는데도 `.env`가 수정됨(` M`)으로 뜬다. 무시되고 있었다면 아예 목록에 안 나와야 한다.

## 판별: git check-ignore는 이 경우 빈 결과를 낸다

"규칙이 틀렸나?" 싶어서 `git check-ignore`를 돌리면 더 헷갈린다.

```bash
git check-ignore -v .env; echo "exit=$?"
```

```
exit=1
```

출력이 없고 종료 코드 1이다. 규칙이 틀려서가 아니라, 기본적으로 **추적 중인 파일은 검사에서 빼기** 때문이다. `--no-index`를 붙이면 규칙 자체는 맞게 읽힌다.

```bash
git check-ignore -v --no-index .env; echo "exit=$?"
```

```
.gitignore:1:.env	.env
exit=0
```

그래서 기준은 이렇다.

| 확인 | 결과 | 뜻 |
|---|---|---|
| `git check-ignore -v --no-index <파일>`이 규칙을 보여준다 | 규칙은 맞다 | 문제는 패턴이 아니라 **추적 여부** |
| `git ls-files <파일>`에 이름이 나온다 | 추적 중 | `git rm --cached` 대상 |
| `--no-index`로도 안 나온다 | 패턴이 안 맞는다 | 경로·슬래시·오타를 고친다 |

```bash
git ls-files
```

```
.env
app.txt
```

## 해결: 추적만 끊는다

```bash
git rm --cached .env
git status -s
```

```
D  .env
?? .gitignore
```

`--cached`가 있어서 **작업 폴더의 파일은 남고** 인덱스에서만 빠진다. 이 삭제를 커밋하면 끝이다.

```bash
git commit -qam "untrack"
echo "KEY=3" > .env
git status -s
```

```
?? .gitignore
```

이제 `.env`를 고쳐도 목록에 안 뜬다. 새로 `git add .env`를 해도 막힌다.

```
The following paths are ignored by one of your .gitignore files:
.env
hint: Use -f if you really want to add them.
```

## 주의: 히스토리에는 그대로 남아 있다

`git rm --cached`는 **다음 커밋부터** 추적을 끊을 뿐이다. 앞서 커밋한 값은 그대로다.

```bash
git show HEAD~1:.env
```

```
KEY=1
```

비밀번호나 토큰이 들어 있던 파일이라면 이미 올라간 값은 유출된 것으로 보고 **키를 새로 발급**해야 한다.
이 명령은 "앞으로 안 올라가게" 하는 것이지 "올라간 걸 지우는" 것이 아니다.

## 근거

- 공식 문서: [gitignore](https://git-scm.com/docs/gitignore) — "Files already tracked by Git are not affected" (NOTES 항목에서 `git rm --cached`를 안내)
- [git-check-ignore](https://git-scm.com/docs/git-check-ignore) — `--no-index` 옵션 설명

위 출력은 모두 이번에 샌드박스(Linux, Git 2.43.0)에서 직접 돌린 결과다.
