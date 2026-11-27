---
title: "하루 3편을 올리는데 feed.xml에는 5편만 있을 때: Chirpy 피드의 limit: 5"
description: "글이 86편인데 빌드한 feed.xml의 <entry>는 5개뿐이었다. Chirpy 7.6.0 원본 feed.xml이 최근 5편만 내보내기 때문이고, 하루 3편 페이스에서는 피드가 이틀도 못 덮는다."
date: 2026-11-27 09:00:00 +0900
categories: [블로그, 구축]
tags: [atom-feed, chirpy]
---

글이 86편인데 `/feed.xml`을 열면 `<entry>`가 **5개**뿐이다. 고장이 아니라 Chirpy 테마 기본값이다. 피드 템플릿이 `limit: 5`로 최근 5편만 내보낸다. 이 블로그처럼 하루 3편을 올리면 피드 하나가 덮는 기간은 이틀이 안 된다.

> 확인 환경: 2026-11-27, jekyll-theme-chirpy 7.6.0 (`Gemfile.lock`), Jekyll 빌드는 `JEKYLL_ENV=production`.
{: .prompt-info }

## 증상: 글은 많은데 피드는 5개

빌드하고 `_site/feed.xml`의 항목 수를 센다. 이 파일은 Chirpy의 `compress` 레이아웃을 거쳐 한 줄로 압축되어 있어서, `grep -c '<entry>'`는 **줄 수**를 세어 `1`이 나온다. 개수를 세려면 `-o`로 매치를 한 줄씩 뽑아야 한다.

```bash
$ ls _posts | wc -l
86
$ grep -c '<entry>' _site/feed.xml        # 줄 수라서 틀린 숫자
1
$ grep -o '<entry>' _site/feed.xml | wc -l
5
$ grep -o '<published>[^<]*' _site/feed.xml
<published>2026-11-26T20:00:00+09:00
<published>2026-11-26T13:00:00+09:00
<published>2026-11-26T09:00:00+09:00
<published>2026-11-25T20:00:00+09:00
<published>2026-11-25T13:00:00+09:00
```

배포된 사이트도 같다.

```bash
$ curl -s https://vortex21997.github.io/feed.xml | grep -o '<entry>' | wc -l
5
```

가장 오래된 항목이 11월 25일 13:00이다. 그보다 앞선 글은 피드에서 이미 빠졌다.

## 원인: 템플릿의 `limit: 5`

gem 안의 원본 `assets/feed.xml`을 찾아 `limit`을 검색한다.

{% raw %}
```bash
$ bundle exec gem contents jekyll-theme-chirpy | grep assets/feed.xml
.../gems/jekyll-theme-chirpy-7.6.0/assets/feed.xml
$ grep -n limit .../gems/jekyll-theme-chirpy-7.6.0/assets/feed.xml
25:{% for post in site.posts limit: 5 %}
```
{% endraw %}

`_config.yml`에는 피드 개수를 정하는 설정이 없다. 이 블로그는 `assets/feed.xml`을 덮어쓴 파일을 쓰는데(제목의 `<`를 이스케이프하려고), 그 파일에도 같은 줄이 그대로 있다.

{% raw %}
```bash
$ grep -n limit assets/feed.xml
33:{% for post in site.posts limit: 5 %}
```
{% endraw %}

## 이게 문제가 되는 경우, 아닌 경우

피드는 구독자가 **자주 가져가면** 5개로 충분하다. 문제는 가져가는 간격이 길 때다.

| 상황 | 영향 |
|---|---|
| 리더 앱이 몇 시간마다 가져옴 | 없음. 새 글이 5편 넘게 쌓이기 전에 다 받는다 |
| 이틀 이상 안 가져오다 한 번에 가져옴 | 그 사이 올라온 글이 6편 이상이면 앞부분이 **조용히 빠진다** (에러 없음) |
| 프로필 README의 "최근 글" 워크플로 | 최근 N편만 필요하면 상관없다 |

하루 3편이면 5편은 약 1.7일치다. 이틀 쉬었다 읽는 구독자는 글을 놓친다. 이 판단은 위 계산에서 나온 것이고, 실제로 어떤 리더가 얼마 간격으로 가져가는지는 확인하지 못했다.

## 판별법: 내 피드가 얼마나 덮고 있나

피드에 있는 가장 오래된 `published`와 `_posts`의 날짜를 비교하면 된다.

```bash
# 피드가 덮는 가장 오래된 시각
grep -o '<published>[^<]*' _site/feed.xml | tail -1
# 그 시각 이후 올라온 글 수 (= 한 번에 놓치지 않고 받을 수 있는 양)
ls _posts | wc -l
```

피드의 가장 오래된 날짜가 "구독자가 마지막으로 가져온 시점"보다 **늦으면** 그 사이 글이 빠진 것이다.

## 늘리려면

`assets/feed.xml`의 해당 줄에서 숫자만 바꾸면 된다.

{% raw %}
```liquid
{% for post in site.posts limit: 20 %}
```
{% endraw %}

이 파일은 테마를 덮어쓴 3단계 파일이라 버전을 올릴 때 원본과 대조해야 한다. 숫자를 바꾼다고 달라지는 구조는 없다. 다만 피드가 길수록 `/feed.xml` 용량이 늘고, 프로필 저장소 워크플로가 읽는 양도 같이 늘어난다. 이 글을 쓴 실행에서는 파일을 바꾸지 않았고, 현재 값(5)을 측정만 했다.
