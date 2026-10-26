# AI · vortex21997 블로그

Jekyll + [Chirpy](https://github.com/cotes2020/jekyll-theme-chirpy) 테마. GitHub Actions로 `main`에 푸시하면 자동 배포된다.
사이트: <https://vortex21997.github.io>

## 명령어

```bash
bundle install
JEKYLL_ENV=production bundle exec jekyll build   # 배포와 같은 조건으로 빌드
bundle exec jekyll serve                         # 로컬 확인
```

빌드가 글을 건너뛰면 대개 **미래 날짜** 때문이다. Jekyll은 `date`가 현재보다 뒤인 글을 빼고 빌드한다.

## 글 쓰기

파일은 `_posts/YYYY-MM-DD-영문슬러그.md`. **파일명의 영문 슬러그가 그대로 URL**이 된다(`/posts/<슬러그>/`).
제목이 한글이어도 슬러그는 영문으로 짓는다.

```yaml
---
title: "글 제목"
description: "목록과 검색 결과에 나오는 한 줄 요약"
date: 2026-10-26 14:00:00 +0900
categories: [상위, 하위]
tags: [태그1, 태그2]
---
```

- `description`을 빼면 본문 앞부분이 잘려서 들어간다. 직접 쓰는 편이 낫다.
- 태그는 소문자 영문을 기본으로 하되, 한글이 자연스러운 것(`글꼴`, `댓글`)은 한글로.
- 안내 블록은 Chirpy 문법을 쓴다. `> 내용` 다음 줄에 `{: .prompt-tip }` (`info` / `warning` / `danger`).
- 본문에 Liquid 문법(`{{ }}`, `{% %}`)을 코드로 보여줄 때는 `{% raw %}` / `{% endraw %}`로 감싼다. 안 그러면 Jekyll이 실행해 버린다.

## 카테고리

**`[상위, 하위]` 두 단계로만 쓴다.** 아래 표에 없는 조합은 새로 만들지 말고, 필요하면 표를 먼저 고친다.

| 상위 | 하위 | 담는 글 |
|---|---|---|
| **AI 에이전트** | Claude Code | 설정·훅·스킬·슬래시 명령어 등 도구 자체 |
| | 활용 기록 | 실제 작업에 AI를 붙여 돌린 기록 |
| **자동화** | 워크플로 | GitHub Actions, 스케줄, CI |
| | 콘텐츠 | 제작·업로드처럼 반복되는 일의 자동화 |
| **블로그** | 구축 | 테마·댓글·통계·SEO 등 세팅 |
| | 운영 | 발행 한도, 글쓰기 방식, 유지보수 |
| | 시작 | 공지성 글 |
| **회고** | 프로젝트 | 만들면서 겪은 시행착오와 배운 점 |

경계가 애매할 때의 기준:

- **도구 얘기인가, 그 도구로 한 일 얘기인가** → 전자는 `AI 에이전트 > Claude Code`, 후자는 `활용 기록`
- **이 블로그를 만든 얘기인가, 일반적인 자동화인가** → 전자는 `블로그`, 후자는 `자동화`
- 상위를 새로 만들기 전에 기존 네 개 중 하나에 들어가는지 먼저 본다

## 테마를 고칠 때

Chirpy는 gem 테마라 레포에 같은 경로의 파일을 두면 덮인다. **덮는 위치에 따라 업그레이드 비용이 다르다.**

| 고치는 것 | 어디에 | 비용 |
|---|---|---|
| 색·글꼴·간격 | `assets/css/jekyll-theme-chirpy.scss` | 없음 (덮으라고 있는 파일) |
| `<head>` 추가 | `_includes/metadata-hook.html` | 없음 (원래 비어 있음) |
| 동작·구조 | `_includes/<원본>.html` | **있음 — 버전 올릴 때 원본과 대조** |

- SCSS 변수(`$font-family-base` 등)는 **`@use 'abstracts/variables' with (...)` 안에서만** 바뀐다. 파일 아래에 다시 적으면 안 먹는다.
- 색은 CSS 변수를 덮는다. 선택자는 `[data-bs-theme='dark']`와 `:not([data-bs-theme])` **둘 다** 필요하다. 방문자 대부분은 테마를 직접 고르지 않아 속성이 없는 상태로 본다.
- 3단계로 덮은 파일에는 **파일 머리에 왜 덮었는지 주석을 남긴다.** 현재 덮은 파일은 `_includes/comments/giscus.html` 하나뿐이고, `themeMap` 한 줄만 바꿨다.

## 연동된 것

| | 설정 위치 | 비고 |
|---|---|---|
| 댓글 | `_config.yml` `comments.giscus` | 깃허브 Discussions(Announcements)에 저장 |
| 통계 | `_config.yml` `analytics.goatcounter` | 대시보드: `vortex21997.goatcounter.com` |
| 조회수 | `_config.yml` `pageviews.provider` | 공개 카운터 API를 읽으며 **몇 시간 캐시된다** |
| 검색 노출 | `_config.yml` `webmaster_verifications.google` + 루트의 `google*.html` | 둘 다 유효 |

`assets/css/giscus-light.css` / `giscus-dark.css`는 giscus 댓글창을 블로그 색에 맞추는 커스텀 테마다.
giscus가 iframe에서 가져가므로 CORS가 필요하고, GitHub Pages는 `access-control-allow-origin: *`를 준다.
