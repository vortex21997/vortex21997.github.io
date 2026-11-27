---
title: "curl (60) 에러가 두 가지 메시지로 나올 때: 발급자를 모르는 것과 호스트 이름이 안 맞는 것"
description: "curl 종료 코드 60은 'unable to get local issuer certificate'와 'no alternative certificate subject name matches' 두 원인을 모두 덮는다. 로컬 TLS 서버에서 둘을 재현하고, 메시지 한 줄로 가려내는 기준을 정리했다."
date: 2026-11-27 20:00:00 +0900
categories: [전산학, 네트워크]
tags: [curl, openssl, 인증서, san]
---

> 2026-11 기준. curl 8.5.0, OpenSSL 3.0.13, Ubuntu 샌드박스에서 확인했다.
{: .prompt-info }

`curl: (60)`은 한 가지 에러가 아니다. **종료 코드 60은 "서버 인증서 검증 실패" 전체**를 가리키고, 실제 원인은 메시지 첫 줄에 있다. 인증서를 **발급한 곳(CA)을 믿을 수 없는 것**과 **인증서가 접속한 이름과 안 맞는 것**은 해법이 전혀 다르다. 전자는 CA 파일을 알려 주면 되고, 후자는 `--cacert`를 아무리 넣어도 안 풀린다.

## 재현: 같은 서버, 다른 메시지

로컬에 CA를 하나 만들고, 그 CA로 서버 인증서 두 개를 서명했다. 둘의 차이는 SAN(Subject Alternative Name, 인증서가 유효하다고 선언한 이름 목록)뿐이다.

```bash
openssl req -x509 -newkey rsa:2048 -nodes -keyout ca.key -out ca.crt -subj "/CN=Test CA" -days 2
openssl req -newkey rsa:2048 -nodes -keyout s.key -out s.csr -subj "/CN=localhost"
printf "subjectAltName=DNS:other.test\n" > san1.ext
printf "subjectAltName=DNS:localhost\n"  > san2.ext
openssl x509 -req -in s.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out bad.crt  -days 2 -extfile san1.ext
openssl x509 -req -in s.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out good.crt -days 2 -extfile san2.ext
openssl s_server -accept 8443 -cert bad.crt -key s.key -www -quiet &
```

`bad.crt`는 `CN = localhost`지만 SAN이 `DNS:other.test`다. 이 서버에 접속하면:

```console
$ curl -sS https://localhost:8443/ -o /dev/null; echo "exit=$?"
curl: (60) SSL certificate problem: unable to get local issuer certificate
exit=60

$ curl -sS --cacert ca.crt https://localhost:8443/ -o /dev/null; echo "exit=$?"
curl: (60) SSL: no alternative certificate subject name matches target host name 'localhost'
exit=60
```

종료 코드는 둘 다 60이다. CA를 알려 주자 **첫 번째 문제가 사라지고 두 번째 문제가 드러났다.** 검증은 순서대로 진행되고 먼저 걸린 것만 보고하기 때문에, 발급자 문제에 가려 있던 이름 문제는 한 단계 풀어야 보인다.

## 판별법: 메시지 첫 줄을 본다

| 메시지(원문) | 무엇이 틀렸나 | 방향 |
|---|---|---|
| `SSL certificate problem: unable to get local issuer certificate` | 발급 CA를 신뢰 목록에서 못 찾음 | CA 인증서를 `--cacert`로 주거나 시스템에 등록. 서버가 중간 인증서를 빠뜨렸을 수도 있음 |
| `SSL: no alternative certificate subject name matches target host name '...'` | 접속한 이름이 인증서 SAN에 없음 | 인증서를 그 이름으로 다시 발급하거나, 인증서에 있는 이름으로 접속 |

`openssl s_client`는 같은 상황을 번호로 보여 준다. `-verify_hostname`을 주면 이름 검사도 같이 한다.

```console
$ openssl s_client -connect localhost:8443 -verify_hostname localhost </dev/null 2>&1 | grep -E 'verify error|Verification'
verify error:num=20:unable to get local issuer certificate
verify error:num=62:hostname mismatch
verify error:num=21:unable to verify the first certificate
Verification error: unable to verify the first certificate

$ openssl s_client -connect localhost:8443 -CAfile ca.crt -verify_hostname localhost </dev/null 2>&1 | grep -E 'verify error|Verification'
verify error:num=62:hostname mismatch
Verification error: hostname mismatch
```

`s_client`는 curl과 달리 **두 문제를 한꺼번에** 보여 준다(20번과 62번). curl 메시지가 하나만 나와서 원인이 헷갈릴 때 쓸 만하다.

## SAN이 있으면 CN은 안 본다

`bad.crt`의 CN은 `localhost`인데도 이름이 안 맞는다고 나왔다. 호스트 이름 검증은 SAN에 DNS 이름이 있으면 그것만 보고 CN은 무시한다. 규칙은 [RFC 6125 §6.4.4](https://www.rfc-editor.org/rfc/rfc6125#section-6.4.4)에 있다. "CN은 맞는데 왜 안 되나"의 답이 이것이다.

## 고친 뒤 확인

SAN을 `DNS:localhost`로 바꾼 `good.crt` 서버로 바꿔 돌렸다.

```console
$ curl -sS https://localhost:8443/ -o /dev/null
curl: (60) SSL certificate problem: unable to get local issuer certificate   # CA를 안 줬으니 당연

$ curl -sS --cacert ca.crt https://localhost:8443/ -o /dev/null -w "http=%{http_code}\n"
http=200

$ curl -sS --cacert ca.crt https://127.0.0.1:8443/ -o /dev/null
curl: (60) SSL: no alternative certificate subject name matches target host name '127.0.0.1'
```

마지막 줄도 흔한 함정이다. SAN에 `DNS:localhost`만 있으면 **IP로 접속할 때는 이름이 안 맞는다.** IP로 접속하려면 SAN에 `IP:127.0.0.1`이 따로 있어야 한다.

> `curl -k`(`--insecure`)는 두 검증을 모두 끄므로 `http=200`이 나온다. 하지만 위조된 서버도 통과시키는 방법이라, 원인을 가려내는 용도로만 쓰고 고정 설정으로 두지 않는다.
{: .prompt-warning }

## 근거

- curl의 인증서 검증 설명: <https://curl.se/docs/sslcerts.html> (에러 메시지 본문이 이 페이지를 가리킨다)
- 호스트 이름 검증 규칙: [RFC 6125 §6.4.4](https://www.rfc-editor.org/rfc/rfc6125#section-6.4.4)
- 직접 돌린 것: 위 명령 전부. 환경은 curl 8.5.0 / OpenSSL 3.0.13 / Python 3.11 샌드박스. 메시지 문구는 curl·OpenSSL 버전에 따라 조금 다를 수 있다.

HTTPS 자물쇠가 무엇을 보증하는지는 [주소창 자물쇠가 있으면 안전한 사이트일까]({% post_url 2026-11-11-https-lock-does-not-mean-safe-site %})에서 다룬 적이 있다.
