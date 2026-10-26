---
title: "github.io는 '도메인' 속성으로 등록할 수 없다"
description: "서치콘솔에서 도메인 속성을 고르면 DNS 인증만 나오는데, github.io는 내 도메인이 아니라 거기서 막힌다. URL 접두어로 가는 법과, 사이트맵 '가져올 수 없음'이 실패가 아닌지 판별하는 법."
date: 2026-10-26 13:35:00 +0900
categories: [Blog, 블로그 구축]
tags: [search-console, seo, github-pages, 사이트맵]
---

Google Search Console에 블로그를 등록하려고 하면 처음에 속성 유형을 고르라고 한다.
**도메인**과 **URL 접두어** 두 가지다.

도메인 쪽이 더 포괄적으로 보여서 그걸 고르기 쉬운데,
`사용자이름.github.io` 라면 **거기서 막힌다.**

## 왜 막히나

도메인 속성은 소유 확인 방법이 **DNS TXT 레코드 하나뿐이다.**
`google-site-verification=...` 형태의 값을 도메인 DNS 설정에 추가해야 한다.

그런데 `github.io`는 깃허브 도메인이다.
내가 가진 건 그 아래 서브도메인 하나뿐이고, **DNS 레코드를 추가할 권한이 없다.**

> 값을 복사해 왔는데 넣을 데가 없다면 속성 유형이 잘못된 것이다.
> `google-site-verification=` 처럼 **등호가 붙은 형태**는 DNS용 표기다.
{: .prompt-warning }

커스텀 도메인(`example.com`)을 연결했다면 도메인 속성을 쓸 수 있다.
기본 `github.io` 주소라면 **URL 접두어**로 가야 한다.

## URL 접두어로 등록하기

속성 추가 → **URL 접두어** → `https://사용자이름.github.io` 입력.
소유 확인 방법이 여러 개 나오는데, 정적 블로그에 쓸 만한 건 둘이다.

### 방법 1 — HTML 태그

Jekyll에 `jekyll-seo-tag` 플러그인이 있으면 `_config.yml` 한 줄이면 끝난다.
Chirpy에는 기본으로 들어 있다.

```yaml
webmaster_verifications:
  google: k7DQGCvKMdL1LW4bhuCB9MwvJbBoYrDF-cqJWGTtJ4g
```

여기 넣는 건 **토큰만**이다. `google-site-verification=` 접두사는 떼야 한다.
플러그인이 알아서 메타 태그로 만들어 모든 페이지 `<head>`에 넣는다.

```html
<meta name="google-site-verification" content="k7DQGCvKMdL1LW4bhuCB9MwvJbBoYrDF-cqJWGTtJ4g" />
```

### 방법 2 — HTML 파일

구글이 `google28d194753ee9824a.html` 같은 파일을 받으라고 하는 방식이다.
이 파일의 내용은 **한 줄이 전부**다.

```
google-site-verification: google28d194753ee9824a.html
```

파일 이름을 그대로 적은 것뿐이다. 받은 파일을 꼭 써야 하는 건 아니고,
같은 이름·같은 내용으로 만들어 **레포 루트에 두면 된다.**

Jekyll은 **front matter(`---`)가 없는 파일을 건드리지 않고 그대로 복사**하므로,
`_site` 최상단에 그대로 나오고 `https://사이트/google28d19....html`로 열린다.

```console
$ curl https://내사이트.github.io/google28d194753ee9824a.html
google-site-verification: google28d194753ee9824a.html
```

둘 다 해둬도 상관없다. 하나만 통과해도 확인은 끝난다.

## 사이트맵 — "가져올 수 없음"은 실패가 아닐 수 있다

확인이 끝나면 **Sitemaps** 메뉴에서 사이트맵을 제출한다.
여기서 두 가지로 헷갈린다.

### 입력란에는 경로만 쓴다

입력란 앞에 이미 `https://내사이트.github.io/`가 붙어 있다.
거기에 전체 주소를 붙여넣으면 이렇게 된다.

```
https://내사이트.github.io/https://내사이트.github.io/sitemap.xml  → 404
```

**`sitemap.xml`** 만 쳐야 한다. 앞의 `/`도 필요 없다.

### "가져올 수 없음" = 아직 안 가져갔다

제대로 넣었는데도 상태가 빨간 글씨로 **"가져올 수 없음"** 이라고 뜬다.
여기서 설정을 다시 뒤지기 쉬운데, **옆 칸을 먼저 봐야 한다.**

| 열 | 값 | 해석 |
|---|---|---|
| 마지막으로 읽은 날짜 | **비어 있음** | 구글이 아직 한 번도 안 가져감 |
| | 날짜가 있음 | 가져갔는데 실패함 — 이때부터 진짜 문제 |

비어 있다면 **실패가 아니라 대기**다. 막 제출한 속성은 몇 시간에서 이틀쯤 걸린다.
유형이 "알 수 없음"으로 나오는 것도 같은 이유다. 내용을 본 적이 없으니 형식을 모른다.

## 서버 쪽은 내가 직접 확인할 수 있다

기다리기 전에 내 쪽 문제가 아닌 건 확인해두면 마음이 편하다.

```console
$ curl -sI https://내사이트.github.io/sitemap.xml | head -3
HTTP/2 200
content-type: application/xml

$ curl -s https://내사이트.github.io/robots.txt
User-agent: *
Disallow: /norobots/
Sitemap: https://내사이트.github.io/sitemap.xml
```

`robots.txt`에 사이트맵이 선언돼 있으면, 제출하지 않아도 구글이 알아서 찾아간다.
`jekyll-sitemap`과 Chirpy를 쓰면 둘 다 자동으로 만들어진다.

Googlebot 입장에서 막히는 게 없는지도 볼 수 있다.

```console
$ curl -s -o /dev/null -w '%{http_code}\n' \
    -A 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)' \
    https://내사이트.github.io/sitemap.xml
200
```

여기까지 전부 통과하면 **내가 할 수 있는 건 끝났다.** 나머지는 구글이 가져가기를 기다리는 일이다.

> 더 빨리 보고 싶으면 **URL 검사** 메뉴에 주소를 넣고 "실시간 테스트"를 돌려보면 된다.
> "URL을 사용할 수 있음"이 나오면 지금 이 순간 크롤링이 가능하다는 뜻이다.
> 홈 주소로 **색인 생성 요청**을 누르면 사이트맵을 기다리지 않고 대기열에 올라간다.
{: .prompt-tip }

## 덤 — 등록은 노출의 조건이 아니다

Search Console에 등록해야 구글에 뜨는 건 아니다.
구글은 등록 여부와 무관하게 크롤링하고 색인한다.

Search Console은 **노출을 시키는 도구가 아니라 보고 관리하는 도구**다.

- 사이트맵 제출·색인 요청 → 색인 **속도**를 당김
- 어떤 검색어로 들어왔는지 성과 데이터
- 색인이 안 된 페이지와 그 이유

그래서 네이버 블로그처럼 **메타태그도 파일도 넣을 수 없는 플랫폼**은
Search Console 등록 자체가 불가능하지만, 구글 검색에는 멀쩡히 나온다.
