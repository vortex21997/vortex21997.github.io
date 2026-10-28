---
title: "Chirpy 테마에는 한글 글꼴이 없다"
description: "한글 블로그인데 글꼴 설정을 안 건드렸다면, 지금 보이는 글꼴은 테마가 고른 게 아니라 방문자 OS가 떠넘긴 것이다. Pretendard로 바꾸는 방법."
date: 2026-10-26 10:00:00 +0900
categories: [블로그, 구축]
tags: [chirpy, jekyll, 글꼴]
---

Jekyll **Chirpy** 테마로 한글 블로그를 만들고 글꼴을 따로 건드리지 않았다면,
지금 화면에 보이는 글꼴은 **테마가 고른 게 아니다.**

테마의 기본값을 열어 보면 이렇다. (`_sass/abstracts/_variables.scss`, v7.6.0)

```scss
$font-family-base: 'Source Sans Pro', 'Microsoft Yahei', sans-serif !default;
$font-family-heading: Lato, 'Microsoft Yahei', sans-serif !default;
```

Source Sans Pro와 Lato에는 **한글 글리프가 없다.** Microsoft Yahei는 중국어 글꼴이다.
그래서 한글은 목록 끝의 `sans-serif`까지 떨어지고, 결국 방문자 OS의 기본 고딕으로 그려진다.

- 맥: Apple SD Gothic Neo
- 윈도우: 맑은 고딕
- 안드로이드: Noto Sans KR

**같은 글이 기기마다 다른 글꼴로 보인다.** 디자인을 아무리 맞춰도 본문이 따로 노는 이유다.

## 고치기 — 두 파일

### 1. 글꼴 파일 불러오기

Chirpy에는 `_includes/metadata-hook.html`이라는 빈 파일이 있다.
테마 원본은 주석 한 줄이 전부다.

```html
<!-- A placeholder to allow defining custom metadata -->
```

`<head>` 끝에서 `{% raw %}{% include metadata-hook.html %}{% endraw %}`로 불러가므로,
**테마가 공식으로 열어둔 확장 지점**이다. 같은 경로에 파일을 만들면 원본을 덮어쓴다.

```html
<!-- _includes/metadata-hook.html -->
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link
  rel="stylesheet"
  href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
>
```

`dynamic-subset`은 한글을 유니코드 범위별로 쪼개 둔 버전이라, 페이지에 실제로 쓰인 글자만 받아온다.
한글 폰트는 통짜로 받으면 1MB를 넘기 때문에 이쪽을 쓰는 게 맞다.

> `head.html`을 통째로 덮어쓰는 방법도 돌아가긴 한다. 다만 테마 버전을 올릴 때마다
> 원본과 대조해야 해서, 확장 지점이 따로 있는데 굳이 그럴 이유가 없다.
{: .prompt-tip }

### 2. 글꼴 지정하기

`assets/css/jekyll-theme-chirpy.scss`를 만들어 덮어쓴다.
여기서 중요한 건 **`@use ... with` 안에서 바꿔야 한다**는 점이다.

```scss
---
---

@use 'abstracts/variables' with (
  $theme: '{% raw %}{{ site.theme_mode }}{% endraw %}',
  $font-family-base: (
    'Pretendard Variable', Pretendard, -apple-system,
    'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif
  ),
  $font-family-heading: (
    'Pretendard Variable', Pretendard, -apple-system,
    'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif
  )
);

/* prettier-ignore */
@use 'main
{% raw %}{%- if jekyll.environment == 'production' -%}{% endraw %}
  .bundle
{% raw %}{%- endif -%}{% endraw %}
';
```

변수에 `!default`가 붙어 있어서 `with`로 넘긴 값이 이긴다.
파일 아래쪽에 `$font-family-base: ...`라고 다시 적는 방식은 통하지 않는다.
이미 `main`이 그 값을 읽은 뒤이기 때문이다.

Pretendard를 못 받아왔을 때를 대비해 **목록 뒤쪽에 OS 기본 한글 글꼴을 깔아둔다.**
비어 있는 `sans-serif`보다는 낫다.

## 덤 — 한글이라서 더 해야 하는 것

글꼴만 바꿔도 체감이 크지만, 두 줄 더 넣으면 확실히 달라진다.

```scss
body {
  word-break: keep-all; /* 한글을 어절 단위로 끊는다 */
  overflow-wrap: break-word;
}

.content {
  line-height: 1.78; /* 영문 기준 기본값은 한글에 빡빡하다 */
}
```

`word-break: keep-all`이 없으면 브라우저가 한글을 **글자 단위로 자른다.**
"블로그를 시작합니다"가 "블로그를 시작합니" / "다"로 끊기는 그 현상이다.
`overflow-wrap: break-word`를 같이 두는 이유는, 줄바꿈할 데가 없는 긴 URL이
레이아웃을 밀어내지 않게 하기 위해서다.

## 정리

| 항목 | 기본값 | 바꾼 값 |
|---|---|---|
| 본문 글꼴 | Source Sans Pro → OS 기본 | Pretendard |
| 줄바꿈 | 글자 단위 | 어절 단위 |
| 본문 줄간 | 영문 기준 | 1.78 |

파일 두 개가 전부고, 둘 다 테마가 공식으로 열어둔 자리라 버전을 올려도 깨지지 않는다.
