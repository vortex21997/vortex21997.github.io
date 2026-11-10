---
title: "코드 블록에 쓴 ${{ secrets.TOKEN }}이 글에서 $만 남을 때: Jekyll의 Liquid와 raw"
description: "Jekyll은 마크다운 코드 블록 안의 {{ }}와 {% %}도 Liquid로 실행한다. 에러 없이 빈 문자열로 사라지는 경우와 'Unknown tag' 에러로 빌드가 죽는 경우를 직접 재현하고, raw로 감싸는 법을 확인했다."
date: 2026-11-10 09:00:00 +0900
categories: [블로그, 운영]
tags: [liquid, jekyll, github-actions]
---
{% assign o = '{' %}{% assign c = '}' %}
{% raw %}
GitHub Actions 워크플로를 글에 옮기면서 ` ```yaml ` 코드 블록에 `run: echo ${{ secrets.TOKEN }}`를 썼는데, 사이트에는 `run: echo $`만 나온다면 코드 블록이라서 안전할 거라는 가정이 틀린 것이다. Jekyll은 마크다운을 변환하기 **전에** 파일 전체를 Liquid 템플릿으로 한 번 실행한다. 코드 블록도 인라인 코드도 예외가 아니다. 해결은 해당 부분을 `{% endraw %}{{ o }}% raw %{{ c }}{% raw %}` … `{% endraw %}{{ o }}% endraw %{{ c }}{% raw %}`로 감싸는 것이다.

> 확인 환경: Jekyll 4.4.1, Liquid 4.0.4, jekyll-theme-chirpy 7.6.0, Ruby 3.3.6 (2026-11 기준). 아래 출력은 이 블로그를 복사한 임시 디렉터리에서 `jekyll build`로 직접 얻은 것이다.
{: .prompt-info }

## 증상은 두 갈래다

같은 원인인데 내용에 따라 결과가 전혀 다르다. 이 차이가 판별 기준이다.

| 코드 블록에 쓴 내용 | 빌드 | 사이트에 보이는 것 |
|---|---|---|
| `{{ 변수 }}` (정의된 변수/없는 변수) | 성공, 경고 없음 | 값으로 바뀌거나 **빈 문자열** |
| `{% 알 수 없는 태그 %}` | **실패** | — |
| `{% if x %}`만 쓰고 안 닫음 | **실패** | — |
| `{{ "a" \| 없는필터 }}` | 성공, 경고 없음 | 필터가 무시되고 `a`만 |

빌드가 죽으면 눈에 띄지만, `{{ }}`는 조용히 사라지기 때문에 글을 올리고 한참 뒤에야 알게 된다.

## 재현 1: 조용히 사라지는 경우

글 본문에 아래 내용을 넣고 빌드했다.

````markdown
```yaml
run: echo ${{ secrets.TOKEN }}
```
````

생성된 HTML에서 코드 부분의 텍스트만 뽑으면 이렇다.

```text
1 run: echo $
```

`secrets.TOKEN`은 Liquid 입장에서 정의되지 않은 변수라 빈 문자열이 되고, 남은 건 앞의 `$`뿐이다. 에러도 경고도 없다.

정의된 변수면 값으로 바뀐다. 인라인 코드 `` `{{ page.title }}` ``은 글 제목(`liquid test`)으로, 코드 블록의 `title: "{{ site.title }}"`도 사이트 제목으로 바뀌었다. 코드 블록 안이라고 막아 주지 않는다.

## 재현 2: 빌드가 죽는 경우

` ```text ` 블록에 `{% foo %}`를 쓰면 이렇게 실패한다.

```text
Liquid Exception: Liquid syntax error (line 2): Unknown tag 'foo' in .../_posts/2026-11-10-liquid-test.md
```

`{% if x %}`를 닫지 않은 채 쓰면 이렇다.

```text
Liquid Exception: Liquid syntax error (line 4): 'if' tag was never closed in .../_posts/2026-11-10-liquid-test.md
```

에러 메시지에 파일 경로가 나오므로 어느 글인지는 바로 찾을 수 있다. 줄 번호는 위 재현에서 본문(front matter 제외) 기준과 일치했다.

## 해결: raw로 감싼다

````markdown
{% endraw %}{{ o }}% raw %{{ c }}{% raw %}
```yaml
run: echo ${{ secrets.TOKEN }}
```
{% endraw %}{{ o }}% endraw %{{ c }}{% raw %}
````

이렇게 빌드하면 코드 블록 텍스트가 `run: echo ${{ secrets.TOKEN }}` 그대로 나온다. `raw`는 그 구간을 Liquid가 해석하지 않고 원문 그대로 통과시키는 태그다([Liquid 문서의 raw](https://shopify.github.io/liquid/tags/raw/), [Jekyll의 Liquid 설명](https://jekyllrb.com/docs/liquid/)).

인라인 코드도 마찬가지로 줄 안에서 감싸면 된다. 이 글의 본문이 그 예라서, 소스에는 `{% endraw %}{{ o }}% raw %{{ c }}{% raw %}`를 쓴 곳이 여러 군데 있다.

## 정리

- 코드 블록에 `{{`나 `{%`가 들어가면 일단 `raw`로 감싼다. GitHub Actions의 `${{ }}`, Helm·Ansible·Jinja 템플릿, Vue·Handlebars 문법이 모두 해당한다.
- 글을 올린 뒤에는 사이트에서 코드 블록을 한 번 본다. 빌드가 성공해도 `{{ }}`는 사라져 있을 수 있다.
- 빌드 로그에 `Liquid Exception`이 보이면 그 글의 `{%`부터 찾는다.
{% endraw %}
