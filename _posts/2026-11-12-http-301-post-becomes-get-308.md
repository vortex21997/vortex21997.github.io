---
title: "curl -L로 POST를 보냈는데 본문이 사라질 때: 301은 GET으로 바뀌고 308은 그대로 간다"
description: "301 응답 뒤에 curl이 POST를 GET으로 바꿔 본문을 버리는 것을 로컬 서버로 재현하고, 308과 비교했다. RFC 9110이 허용하는 동작이다."
date: 2026-11-12 20:00:00 +0900
categories: [전산학, 네트워크]
tags: [curl, http, 리다이렉트]
---

> 2026-11 기준. curl 8.5.0, Linux 6.18, Python 3.11 로컬 서버에서 확인했다.
{: .prompt-info }

**결론부터.** `curl -L -d a=1`로 POST를 보냈는데 서버가 301을 돌려주면, curl은 두 번째 요청을 **GET으로 바꾸고 본문을 버린다.** 308이면 메서드와 본문이 그대로 간다. 둘 다 "영구 이동"이지만 [RFC 9110 §15.4.2](https://www.rfc-editor.org/rfc/rfc9110.html#name-301-moved-permanently)가 301에서 이 변경을 허용하기 때문이다.

> For historical reasons, a user agent MAY change the request method from POST to GET for the subsequent request. If this behavior is undesired, the 308 (Permanent Redirect) status code can be used instead.

## 재현

`/r301`은 301, `/r308`은 308로 `/final`을 가리키는 서버를 파이썬으로 띄우고, `/final`은 받은 메서드와 본문을 되돌려 주게 했다.

```bash
curl -s -L -d a=1 http://127.0.0.1:8765/r301
curl -s -L -d a=1 http://127.0.0.1:8765/r308
```

```
method=GET body=''
method=POST body='a=1'
```

301 쪽만 요청이 GET으로 바뀌고 본문이 비었다. 서버 입장에서는 "필수 파라미터가 없다"는 엉뚱한 에러로 보이기 쉽다.

## 판별법: 메서드가 바뀐 건지, 서버가 본문을 못 받은 건지

증상은 같다(리다이렉트를 따라간 뒤 데이터가 없다). 가르는 기준은 **리다이렉트 응답의 상태 코드**다.

```bash
curl -si -X POST -d a=1 http://127.0.0.1:8765/r301 | head -1
```

```
HTTP/1.0 301 Moved Permanently
```

- 301·302·303이면 클라이언트가 GET으로 바꿨을 수 있다 (303은 처음부터 GET으로 바꾸라는 뜻).
- 307·308이면 바뀌지 않는다. 그런데도 본문이 없다면 리다이렉트가 아니라 서버·프록시 쪽을 본다.

## 이럴 때 `-X POST`는 해결책이 아니다

`-X POST`를 붙이면 메서드 문자열은 POST로 유지되지만 본문은 여전히 사라진 채였다.

```bash
curl -s -L -X POST -d a=1 http://127.0.0.1:8765/r301
```

```
method=POST body=''
```

본문까지 유지하려면 `--post301`을 쓴다(curl 문서: 301 뒤에도 POST를 유지).

```bash
curl -s -L --post301 -d a=1 http://127.0.0.1:8765/r301
```

```
method=POST body='a=1'
```

근본 해결은 서버가 308(또는 307)을 주는 것이다. 이 블로그의 GitHub Pages는 `http://`를 `https://`로 보낼 때 실제로 301을 준다.

```
$ curl -sI http://vortex21997.github.io/about
HTTP/1.1 301 Moved Permanently
location: https://vortex21997.github.io/about
```

그래서 `http://`로 POST하는 스크립트는 https로 넘어가며 GET이 된다. 처음부터 `https://` 주소를 쓰면 이 문제를 피한다.
(같은 주소에 슬래시가 없으면 `https://…/about` → `https://…/about/`로 한 번 더 301이 와서, `-L`로 따라가면 `num_redirects=2`가 나왔다.)

## 정리

| 코드 | 의미 | POST 뒤 후속 요청 (curl 8.5.0, `-L -d`) |
|---|---|---|
| 301 | 영구 이동 | GET, 본문 없음 |
| 308 | 영구 이동 (메서드 유지) | POST, 본문 유지 |

308은 [RFC 9110 §15.4.9](https://www.rfc-editor.org/rfc/rfc9110.html#name-308-permanent-redirect)에 정의돼 있다. 위 결과는 curl 기준이며, 브라우저·라이브러리마다 301 처리가 다를 수 있어 일반화하지 않았다.
