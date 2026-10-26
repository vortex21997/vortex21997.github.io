---
title: "giscus 댓글, 카테고리 ID가 안 나올 때"
description: "giscus.app이 [ENTER CATEGORY ID HERE]를 그대로 뱉는다면 순서가 틀린 것이다. Discussions를 먼저 켜야 하는 이유와, 깃허브 회색 댓글창을 블로그 색에 맞추는 법."
date: 2026-10-26 11:00:00 +0900
categories: [블로그, 구축]
tags: [giscus, chirpy, 댓글, github-pages]
media_subpath: /assets/img/posts/giscus-category-id/
---

정적 블로그에 댓글을 붙이는 가장 흔한 선택이 **giscus**다.
깃허브 Discussions를 댓글 저장소로 쓰기 때문에 서버도, DB도, 광고도 없다.

그런데 [giscus.app](https://giscus.app)에서 설정 코드를 받으려 하면 이런 게 나올 때가 있다.

```html
data-repo-id="R_kgDOVUO-Lg"
data-category="[ENTER CATEGORY NAME HERE]"
data-category-id="[ENTER CATEGORY ID HERE]"
```

`repo-id`는 채워졌는데 **카테고리만 플레이스홀더로 남는다.**

## 원인은 순서

레포에 **Discussions가 꺼져 있기 때문**이다.
Discussions를 켜야 카테고리(Announcements, General, Q&A…)가 생기고,
그제서야 giscus.app의 드롭다운에 선택지가 뜬다.

레포 ID는 레포만 있으면 나오니까 먼저 채워지고, 카테고리만 비는 것이다.

올바른 순서는 이렇다.

1. **Discussions 켜기** — 레포 `Settings → General → Features → Discussions` 체크
2. **giscus 앱 설치** — [github.com/apps/giscus](https://github.com/apps/giscus)에서 해당 레포에 설치
3. **giscus.app에서 ID 받기** — 이제 드롭다운이 채워져 있다

이미 giscus.app을 열어둔 채로 Discussions를 켰다면 **새로고침**해야 한다.

> 카테고리는 **Announcements**를 고르는 걸 권한다. 이 카테고리는 레포 관리자만
> 새 글을 만들 수 있어서, 아무나 빈 스레드를 양산하는 걸 막아준다.
> 댓글은 누구나 달 수 있으니 기능상 손해가 없다.
{: .prompt-tip }

### API로는 못 가져온다

카테고리 ID를 코드로 받아오려 했다면 접는 게 낫다.
REST API에는 그 엔드포인트가 없다.

```console
$ gh api repos/OWNER/REPO/discussions/categories
{"message":"Not Found","status":"404"}
```

GraphQL의 `discussionCategories`로만 조회된다.
giscus.app을 한 번 거치는 게 제일 빠르다.

## Chirpy에 넣기

`_config.yml`의 `comments` 블록을 채운다.

```yaml
comments:
  provider: giscus
  giscus:
    repo: OWNER/REPO
    repo_id: R_kgDOxxxxxx
    category: Announcements
    category_id: DIC_kwDOxxxxxx
    mapping: pathname
    strict: '0'
    input_position: bottom
    lang: ko
    reactions_enabled: '1'
```

`mapping: pathname`이면 글 주소마다 Discussion이 하나씩 자동으로 생긴다.
누군가 첫 댓글을 달기 전까지는 스레드가 만들어지지 않으니, 빈 글이 쌓이지 않는다.

## 회색 댓글창 문제

여기까지 하면 댓글은 뜨는데, **깃허브 기본 테마라 블로그와 따로 논다.**
특히 다크 모드에서 giscus는 `dark_dimmed`(깃허브 회색)를 쓰는데,
블로그 배경이 회색 계열이 아니면 네모난 회색 박스가 본문 아래 얹힌 꼴이 된다.

giscus는 `data-theme`에 **CSS 파일 URL을 직접 넘길 수 있다.**
giscus 공식 테마를 베이스로 깔고 그 위에 내 색을 덮으면 된다.

```css
/* assets/css/giscus-dark.css */

/* ① giscus 공식 dark_dimmed.css 내용을 여기에 붙여넣고 */

/* ② 아래에서 덮어쓴다 */
main {
  --color-canvas-default: transparent; /* 블로그 배경이 비치게 */
  --color-border-default: #272c54;
  --color-fg-default: #c3c8de;
  --color-accent-fg: #4fd6f0;

  /* 댓글 작성 버튼이 기본 초록이라 눈에 띈다 */
  --color-btn-primary-bg: #6b4fd8;
  --color-btn-primary-hover-bg: #7c62e0;

  background: transparent;
  font-family: 'Pretendard Variable', Pretendard, sans-serif;
}
```

`--color-canvas-default: transparent`가 핵심이다.
배경을 비워야 블로그 바탕이 그대로 올라와서 박스 느낌이 사라진다.

### CORS를 확인할 것

giscus는 이 CSS를 **iframe 안에서 가져간다.** 그래서 CORS 헤더가 필요하다.
GitHub Pages는 열어 준다.

```console
$ curl -sI https://OWNER.github.io/assets/css/giscus-dark.css | grep -i access-control
access-control-allow-origin: *
```

다른 데 호스팅한다면 이게 나오는지 먼저 확인해야 한다.

### Chirpy에 테마 URL 넘기기

Chirpy는 테마 이름을 include 안에 하드코딩해 둬서,
`_config.yml`로는 못 바꾸고 `_includes/comments/giscus.html`을 덮어써야 한다.

```js
// 원본
const themeMap = Theme.newThemeMap('light', 'dark_dimmed');

// 바꾼 뒤
const themeMap = Theme.newThemeMap(
  '{% raw %}{{ "/assets/css/giscus-light.css" | absolute_url }}{% endraw %}',
  '{% raw %}{{ "/assets/css/giscus-dark.css" | absolute_url }}{% endraw %}'
);
```

나머지 줄은 원본 그대로 두면 된다.
라이트/다크 토글을 누르면 Chirpy가 iframe에 `postMessage`로 새 테마를 넘기는 코드가
이미 들어 있어서, **댓글창도 같이 따라온다.**

> 이 파일만은 테마 원본을 통째로 덮어쓰는 것이라, 버전을 올릴 때 한 번 대조해야 한다.
> 파일 머리에 메모를 남겨두면 나중에 덜 헤맨다.
{: .prompt-warning }

적용하면 이렇게 된다. 회색 박스가 사라지고 배경이 그대로 비친다.

![다크 모드 댓글창](giscus-themed-dark.webp)
_다크 모드 — 배경이 투명해져 본문과 이어진다_

![라이트 모드 댓글창](giscus-themed-light.webp)
_라이트 모드 — 같은 CSS 한 벌을 색만 바꿔 쓴다_

## 확인하는 법

적용했는지는 iframe **안쪽**을 읽어야 안다. 개발자 도구 콘솔에서:

```js
const f = document.querySelector('.giscus-frame');
// 같은 출처가 아니라 콘솔에선 안 보인다 → 프레임 선택을 giscus로 바꾼 뒤
getComputedStyle(document.querySelector('main'))
  .getPropertyValue('--color-accent-fg');
```

내가 지정한 색이 돌아오면 적용된 것이다.
`#539bf5`(깃허브 기본 파랑)가 나오면 CSS를 못 가져간 것이니 CORS부터 보면 된다.
