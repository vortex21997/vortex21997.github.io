---
title: "GoatCounter 조회수가 0에서 안 변할 때"
description: "403은 설정 하나로 풀리고, 그 뒤에도 0인 건 캐시 때문이다. 설치가 잘못된 게 아니라는 걸 확인하는 순서."
date: 2026-10-26 12:00:00 +0900
categories: [블로그, 구축]
tags: [goatcounter, 통계, chirpy, github-pages]
---

**GoatCounter**는 구글 애널리틱스 대신 쓸 만한 가벼운 방문자 통계다.
추적 스크립트가 3KB 남짓이고 쿠키를 안 써서 동의 배너도 필요 없다.
Chirpy 테마는 **글마다 조회수 표시**까지 기본으로 지원한다 — GA로는 안 되는 기능이다.

설정은 두 줄이다.

```yaml
# _config.yml
analytics:
  goatcounter:
    id: 내코드 # <코드>.goatcounter.com 의 그 코드

pageviews:
  provider: goatcounter
```

그런데 배포하고 글을 열어 보면 **조회수가 0에서 안 움직인다.**
원인이 두 단계로 나뉘어 있어서, 순서대로 걷어내야 한다.

## 1단계 — 403

먼저 카운터 API를 직접 찔러 본다. 경로는 URL 인코딩해야 한다.

```console
$ curl "https://내코드.goatcounter.com/counter/%2Fposts%2F글주소.json"
error 403: Need to enable the 'allow using the visitor counter' setting
```

에러 메시지가 친절하게 알려준다. **공개 카운터 기능이 기본으로 꺼져 있다.**

추적(방문자 집계)과 공개 카운터(그 숫자를 외부에 알려주기)는 별개 설정이다.
방문은 이미 쌓이고 있지만, 내 블로그가 그 숫자를 읽어갈 권한이 없는 상태다.

`Settings → "Allow adding visitor counts to your website"` 를 켜면 풀린다.

```console
$ curl "https://내코드.goatcounter.com/counter/TOTAL.json"
{"count_unique":"0", "count":"0"}
```

403이 사라지고 JSON이 돌아오면 1단계 통과다.

## 2단계 — 그래도 0이다

여기서 "역시 설치가 잘못됐나" 싶어서 설정을 다시 뒤지기 쉬운데,
**응답 헤더를 보면 답이 나온다.**

```console
$ curl -sI "https://내코드.goatcounter.com/counter/TOTAL.json" | grep -iE 'cache|expires|age'
cache-control: public
expires: Mon, 26 Oct 2026 07:26:25 +0000
age: 42
```

`expires`가 **네 시간쯤 뒤**다. 이 엔드포인트는 응답을 길게 캐시한다.
방금 들어온 방문은 캐시가 만료되기 전까지 이 숫자에 반영되지 않는다.

즉 **0은 "집계가 안 된다"가 아니라 "아직 묵은 값을 보고 있다"**는 뜻이다.

실제 집계 여부는 대시보드(`https://내코드.goatcounter.com`)에서 바로 확인된다.
대시보드에 방문이 찍혀 있는데 카운터만 0이면, 그냥 기다리면 된다.

> 설치가 제대로 됐는지 당장 확인하고 싶다면 네트워크 탭을 열고 글을 새로고침해 보자.
> `gc.zgo.at/count.js`와 `goatcounter.com/count` 요청이 보이면 추적은 동작하는 것이다.
{: .prompt-tip }

## 내 방문은 빼기

통계를 보기 시작하면 바로 걸리는 문제다. 내가 들어간 것도 다 잡힌다.
방법이 두 가지인데, 공식 문서가 권하는 쪽은 첫 번째다.

### 브라우저 단위

주소 끝에 `#toggle-goatcounter`를 붙여서 한 번 들어간다.

```
https://내블로그.github.io#toggle-goatcounter
```

그 브라우저에 플래그가 저장돼서 이후 방문이 전부 무시된다.
다시 들어가면 토글돼서 풀린다.

대신 **브라우저마다, 기기마다 한 번씩** 해줘야 한다. 집·회사·폰 각각.

### IP 단위

`Settings → Tracking`의 **Ignore IPs**에 IP를 넣으면 그 주소에서 오는 요청이 전부 빠진다.
고정 IP면 이쪽이 확실하고, 유동 IP면 소용이 없다.

## 정리

조회수가 0일 때 볼 순서는 이거다.

| 확인 | 결과 | 의미 |
|---|---|---|
| 카운터 API `curl` | `403` | 공개 카운터 설정이 꺼짐 |
| | `{"count":"0"}` | 설정은 켜짐 |
| 응답 헤더 `expires` | 몇 시간 뒤 | 캐시된 값 — 기다리면 됨 |
| 대시보드 | 방문 기록 있음 | 추적은 정상 |

네 칸 중 어디서 걸리는지만 알면 설정을 처음부터 다시 볼 일은 없다.
