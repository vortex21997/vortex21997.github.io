---
title: "Chirpy를 업그레이드 가능한 상태로 고치기"
description: "gem 테마는 파일을 같은 경로에 두면 덮인다. 그래서 아무 데나 덮으면 다음 버전에서 깨진다. 테마가 열어둔 확장 지점 세 곳과 각각의 비용."
date: 2026-10-26 13:50:00 +0900
categories: [블로그, 구축]
tags: [chirpy, jekyll, 테마, github-pages]
---

Chirpy는 **gem 테마**다. `Gemfile`에 이렇게만 적혀 있고, 실제 파일은 레포에 없다.

```ruby
gem "jekyll-theme-chirpy", "~> 7.6"
```

Jekyll의 규칙은 간단하다. **레포에 gem과 같은 경로의 파일이 있으면 그게 이긴다.**
`_includes/footer.html`을 만들면 테마의 footer 대신 내 것이 쓰인다.

편해 보이지만 함정이 있다. 덮어쓴 파일은 **그 시점의 사본으로 굳는다.**
테마가 7.7, 7.8로 올라가면서 그 파일이 바뀌어도 내 사본은 그대로다.
운이 좋으면 기능 하나를 못 받고, 나쁘면 다른 파일과 안 맞아서 깨진다.

그래서 **어디를 고치느냐가 중요하다.** 비용이 다르다.

## 1단계 — 스타일: `assets/css/jekyll-theme-chirpy.scss`

가장 안전하다. 테마가 **덮으라고 만들어 둔 파일**이다.
gem 안의 원본은 이게 전부다.

```scss
---
---

@use 'abstracts/variables' with (
  $theme: '{% raw %}{{ site.theme_mode }}{% endraw %}'
);

/* prettier-ignore */
@use 'main
{% raw %}{%- if jekyll.environment == 'production' -%}{% endraw %}
  .bundle
{% raw %}{%- endif -%}{% endraw %}
';

/* append your custom style below */
```

마지막 줄이 "여기 아래에 네 스타일을 붙여라"라고 대놓고 말한다.
색, 글꼴, 간격은 전부 여기서 끝난다.

### 색은 변수로 덮는다

Chirpy는 라이트/다크를 CSS 커스텀 속성으로 관리한다.
컴포넌트 CSS를 고치는 게 아니라 **변수만 덮어쓰면** 전체가 따라온다.

문제는 선택자 구조다. 테마는 세 갈래로 적용한다.

```scss
:root[data-bs-theme='light'] { /* 라이트 고정 */ }
:root[data-bs-theme='dark']  { /* 다크 고정 */ }
:root:not([data-bs-theme])   { /* 시스템 설정 따라감 */ }
```

세 번째가 핵심이다. 방문자 대부분은 테마를 직접 고르지 않아서
`data-bs-theme` 속성이 **아예 없는 상태**로 본다.
`[data-bs-theme='dark']`에만 색을 적으면 그 사람들에게는 적용되지 않는다.

그래서 믹스인으로 묶고 세 곳에 모두 적용한다.

```scss
@mixin brand-dark {
  --main-bg: #11132a;
  --link-color: #4fd6f0;
  /* ... */
}

:root[data-bs-theme='dark'] { @include brand-dark; }
:root:not([data-bs-theme]) {
  @media (prefers-color-scheme: dark) { @include brand-dark; }
}
```

### 변수는 `@use ... with` 안에서만 바뀐다

글꼴처럼 **SCSS 변수**인 것은 파일 아래쪽에 다시 적어도 안 먹는다.

```scss
/* ❌ 안 됨 — main이 이미 값을 읽은 뒤다 */
@use 'main';
$font-family-base: Pretendard, sans-serif;

/* ✅ 됨 */
@use 'abstracts/variables' with (
  $font-family-base: (Pretendard, sans-serif)
);
@use 'main';
```

테마 변수에 `!default`가 붙어 있어서 `with`로 넘긴 값이 이긴다.

## 2단계 — head 추가: `_includes/metadata-hook.html`

`<head>`에 뭔가 넣어야 할 때가 있다. 웹폰트, 검증 메타태그, `theme-color` 같은 것.

이때 `_includes/head.html`을 통째로 복사해서 고치는 사람이 많은데,
**그럴 필요가 없다.** 테마에 이런 파일이 있다.

```html
<!-- A placeholder to allow defining custom metadata -->
```

주석 한 줄짜리 빈 파일이고, `head.html` 끝에서 불러간다.

```liquid
{% raw %}{% include metadata-hook.html %}{% endraw %}
</head>
```

**비워둔 자리**다. 같은 경로에 파일을 만들어 넣으면 된다.

```html
<!-- _includes/metadata-hook.html -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<meta name="theme-color" content="#19153d">
```

내용이 없는 파일을 덮는 것이라 **테마가 올라가도 충돌할 게 없다.**

## 3단계 — 동작 바꾸기: 원본 덮어쓰기 (최후 수단)

여기부터는 비용이 생긴다. 그래도 **달리 방법이 없을 때**가 있다.

giscus 댓글창을 블로그 색에 맞추려 했을 때가 그랬다.
giscus는 `data-theme`에 CSS 파일 URL을 받는데, Chirpy는 테마 이름을 include 안에 박아뒀다.

```js
// _includes/comments/giscus.html
const themeMap = Theme.newThemeMap('light', 'dark_dimmed');
```

`_config.yml`에는 이걸 바꾸는 키가 없다. 파일을 덮는 수밖에 없었다.

이럴 때 최소한 두 가지는 지키는 게 좋다.

**① 바꾼 곳을 최소로.** 원본을 그대로 복사하고 필요한 줄만 건드린다.

```js
const themeMap = Theme.newThemeMap(
  '{% raw %}{{ "/assets/css/giscus-light.css" | absolute_url }}{% endraw %}',
  '{% raw %}{{ "/assets/css/giscus-dark.css" | absolute_url }}{% endraw %}'
);
```

**② 파일 머리에 메모를 남긴다.** 몇 달 뒤의 나는 이 파일이 왜 레포에 있는지 모른다.

```liquid
{% raw %}{%- comment -%}
  Chirpy 기본 include를 덮어쓴 것. 바뀐 곳은 themeMap 한 줄뿐.
  → 테마 버전을 올릴 때는 원본과 이 파일을 한 번 비교할 것.
{%- endcomment -%}{% endraw %}
```

## 정리

| 고치는 것 | 어디에 | 업그레이드 비용 |
|---|---|---|
| 색·글꼴·간격 | `assets/css/jekyll-theme-chirpy.scss` | 없음 — 덮으라고 있는 파일 |
| `<head>` 추가 | `_includes/metadata-hook.html` | 없음 — 원래 비어 있음 |
| 동작·구조 | `_includes/<원본>.html` | **있음** — 버전 올릴 때 대조 필요 |

이번에 이 블로그를 고치면서 1·2단계로 끝난 게 글꼴과 색 전부였고,
3단계가 필요했던 건 giscus 테마 하나였다. 대부분은 1·2단계로 해결된다.

## 테마를 올릴 때

`bundle update jekyll-theme-chirpy` 전에 할 일은 한 가지다.
**레포의 `_includes`, `_layouts`, `_sass`에 뭐가 있는지 본다.**

```console
$ ls _includes _layouts _sass 2>/dev/null
_includes:
comments/  metadata-hook.html
```

여기 있는 파일이 3단계로 덮은 것들이다.
`metadata-hook.html`은 무시해도 되고, `comments/giscus.html`은 gem의 새 원본과 대조한다.

```console
$ GEM=$(ruby -e 'puts Gem::Specification.find_by_name("jekyll-theme-chirpy").gem_dir')
$ diff $GEM/_includes/comments/giscus.html _includes/comments/giscus.html
```

내가 바꾼 줄만 차이로 나오면 안전하다. 다른 줄까지 바뀌어 있으면 그건 테마가 고친 것이니 가져와야 한다.
