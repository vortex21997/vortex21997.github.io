---
title: "주소창에 IP 주소를 직접 넣으면 사이트가 안 열리는 이유: 한 IP에 사이트가 여러 개 산다"
description: "도메인이 가리키는 IP를 알아내 그대로 입력해도 사이트가 안 나올 때가 많다. 서버는 IP가 아니라 요청에 실린 Host 헤더로 어느 사이트인지 가르기 때문이며, 로컬 서버와 curl로 직접 확인했다."
date: 2026-11-20 13:00:00 +0900
categories: [컴퓨터 기초, 인터넷·보안]
tags: [host-헤더, dns, curl]
---

**결론부터: 도메인을 IP로 바꿔 입력하면 서버가 "어느 사이트를 원하는지" 알 수 없게 되기 때문이다.** IP 주소는 서버 컴퓨터(정확히는 그 서버의 접속 지점)를 가리킬 뿐이고, 그 한 대 안에 사이트가 수십~수천 개 있을 수 있다. 브라우저는 요청을 보낼 때 "나는 이 이름의 사이트를 원한다"를 `Host`라는 한 줄에 적어 보내고, 서버는 그 줄을 보고 보여 줄 사이트를 고른다. IP를 직접 넣으면 그 줄에 이름 대신 숫자가 들어간다.

> 이 글의 실험은 전부 이 샌드박스(Linux 6.18, curl 8.5.0, Python 3.11)에서 돌린 것이다. 로컬에 만든 가짜 서버로 동작을 보이고, 실제 서비스에 IP로 접속해 보는 시도는 하지 않았다. 그래서 "특정 사이트에 IP로 접속하면 어떤 화면이 나온다"는 주장은 하지 않는다.
{: .prompt-info }

## 한 IP에 여러 도메인이 연결된 모습

DNS(도메인 이름을 IP 주소로 바꿔 주는 전화번호부 같은 체계)에 물어 보면, 서로 다른 도메인이 같은 IP 목록을 돌려주는 경우를 쉽게 볼 수 있다. 샌드박스에서 `getent ahostsv4`로 확인한 결과다.

```console
$ getent ahostsv4 vortex21997.github.io | awk '$2=="STREAM"{print $1}'
185.199.109.153
185.199.110.153
185.199.111.153
185.199.108.153
$ getent ahostsv4 pages.github.com | awk '$2=="STREAM"{print $1}'
185.199.111.153
185.199.110.153
185.199.109.153
185.199.108.153
```

두 도메인이 가진 IP 4개가 같다(나열 순서만 다르다). 즉 이 IP로 들어온 연결만 봐서는 어느 도메인을 찾아온 것인지 알 수 없다. 같은 IP 하나에 사이트 여러 개를 얹는 이런 방식을 흔히 "이름 기반 가상 호스트"라고 부른다. 이 IP들이 구체적으로 어떻게 운영되는지는 확인하지 않았다. 여기서 보인 것은 "두 도메인의 DNS 응답이 같다"까지다.

## 서버가 보는 것: Host 헤더

HTTP 요청(브라우저가 서버에 보내는 글)의 첫머리는 이렇게 생겼다. `curl -v`로 본 실제 요청이다.

```console
$ curl -sv -H 'Host: a.example' http://127.0.0.1:8099/ 2>&1 | grep -E '^> '
> GET / HTTP/1.1
> Host: a.example
> User-Agent: curl/8.5.0
> Accept: */*
```

`Host` 줄이 그 역할이다. [RFC 9110 7.2절](https://www.rfc-editor.org/rfc/rfc9110.html#name-host-and-authority)은 이렇게 정의한다.

```text
The "Host" header field in a request provides the host and port
information from the target URI, enabling the origin server to
distinguish among resources while servicing requests for multiple
host names.
```

"여러 호스트 이름을 서비스하는 서버가 리소스를 구분할 수 있게 한다"가 이 헤더의 목적이라고 표준에 적혀 있다. (HTTP/2와 HTTP/3에서는 같은 역할을 `:authority`가 맡는 경우가 있다고 같은 절에 나온다.)

## 직접 확인: 같은 IP·같은 포트, Host만 바꿨다

`Host` 값에 따라 다른 내용을 내주는 서버를 파이썬 표준 라이브러리로 만들었다. 핵심은 이 부분뿐이다.

```python
SITES = {'a.example': 'A 사이트', 'b.example': 'B 사이트'}
# 요청의 Host 헤더에서 포트를 떼고, SITES에 있으면 200, 없으면 404
```

`127.0.0.1:8099` 하나에 접속하되 `Host`만 바꿔 네 번 요청했다.

```console
$ curl -s -w ' [%{http_code}]' http://127.0.0.1:8099/
모르는 Host: 127.0.0.1
 [404]
$ curl -s -w ' [%{http_code}]' -H Host:a.example http://127.0.0.1:8099/
A 사이트
 [200]
$ curl -s -w ' [%{http_code}]' -H Host:b.example http://127.0.0.1:8099/
B 사이트
 [200]
$ curl -s -w ' [%{http_code}]' -H Host:c.example http://127.0.0.1:8099/
모르는 Host: c.example
 [404]
```

- 접속한 곳(IP와 포트)은 네 번 모두 같다.
- 첫 번째처럼 `Host`가 IP(`127.0.0.1`)로 채워지면 이 서버는 "등록된 사이트가 아니다"라며 404를 준다. 주소창에 IP를 넣을 때 벌어지는 일의 축소판이다.
- `Host`만 `a.example`, `b.example`로 바꿔도 다른 사이트가 나온다.

이 서버는 모르는 이름에 404를 주도록 내가 짰다. 실제 서버가 모르는 이름에 어떻게 반응할지(기본 사이트를 보여 줄지, 오류를 낼지, 연결을 끊을지)는 서버 설정마다 다르다. 이 실험이 보이는 것은 "서버가 IP가 아니라 `Host`로 가른다"는 구조다.

## 정리: 증상별로 가려내기

| 상황 | 의미 |
|---|---|
| 도메인으로는 열리고 IP로는 안 열린다 | 서버가 `Host`로 사이트를 고르는 구조일 가능성이 크다. 서버가 죽은 게 아니다 |
| 도메인으로도 IP로도 안 열린다 | 서버·네트워크 쪽 문제를 의심한다. 연결 자체가 안 되는 증상은 [connection refused와 timed out을 가르는 글](/posts/connection-refused-vs-timed-out/)을 참고한다 |
| 내 컴퓨터 IP와 공인 IP가 달라 헷갈린다 | 별개의 질문이다. [사설 IP와 공인 IP](/posts/private-vs-public-ip/) 글에서 다뤘다 |

참고로 HTTPS 사이트에 IP로 접속하면 인증서 검사 단계에서 따로 걸리는 경우도 있다. 이 글은 그 부분을 직접 확인하지 않아 다루지 않는다.
