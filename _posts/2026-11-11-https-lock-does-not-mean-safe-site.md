---
title: "주소창 자물쇠가 있으면 안전한 사이트일까: 인증서가 보증하는 것과 안 하는 것"
description: "자물쇠는 '연결이 암호화됐고 주소의 이름과 인증서가 맞는다'까지만 말한다. 로컬 인증서로 curl 오류 세 가지를 재현하고, 이름이 수상해도 자물쇠가 뜨는 경우를 직접 확인했다."
date: 2026-11-11 13:00:00 +0900
categories: [컴퓨터 기초, 인터넷·보안]
tags: [https, 인증서, curl]
---

**자물쇠는 "안전한 사이트"라는 표시가 아니다.** 지금 내 컴퓨터와 이 주소의 서버 사이의 통신이 **암호화**돼 있고, 서버가 내민 **인증서**가 주소창의 이름과 맞으며 브라우저가 믿는 발급 기관이 서명했다는 뜻까지만이다. 그 사이트의 주인이 정직한지는 자물쇠가 말해 주지 않는다.

> 인증서: "이 이름의 서버는 이 공개 키를 쓴다"고 발급 기관(CA, Certificate Authority)이 서명해 준 증명서.
{: .prompt-info }

실제로 확인해 봤다. 아래는 샌드박스(Linux, curl 8.5.0, OpenSSL 3.0.13)에서 가짜 발급 기관을 만들고 로컬 서버를 띄워 돌린 결과다. 실제 인터넷 사이트가 아니라 내가 만든 인증서로 한 실험이다.

## 준비: 발급 기관과 서버 세 대

```bash
# 내가 만든 발급 기관(Demo Root CA)
openssl req -x509 -newkey rsa:2048 -nodes -keyout ca.key -out ca.crt -subj "/CN=Demo Root CA" -days 30
# bank.test 이름으로 CA가 서명한 인증서 (bank-login-secure.test도 같은 방식)
# 같은 이름 bank.test로 CA 없이 스스로 서명한 인증서(self.crt)
openssl s_server -accept 8441 -cert bank.test.crt -key bank.test.key -www
```

## 1. 정상: 자물쇠가 뜨는 경우

```
$ curl --cacert ca.crt --resolve bank.test:8441:127.0.0.1 https://bank.test:8441/
http=200 verify=0
```

`verify=0`이 "인증서 검사 통과"다. 브라우저의 자물쇠는 이 검사를 통과했다는 표시다.

## 2. 이름이 안 맞을 때

같은 서버에 `other.test`라는 이름으로 접속했다.

```
curl: (60) SSL: no alternative certificate subject name matches target host name 'other.test'
```

인증서는 "bank.test용"인데 내가 찾아간 주소는 `other.test`다. 브라우저에서는 "연결이 비공개로 설정되어 있지 않습니다" 같은 경고 화면으로 보인다.

## 3. 스스로 서명했을 때

```
curl: (60) SSL certificate problem: self-signed certificate
```

## 4. 정상 인증서인데 발급 기관을 모를 때

2번과 달리 `--cacert ca.crt`를 빼고 접속했다.

```
curl: (60) SSL certificate problem: unable to get local issuer certificate
```

3번과 4번은 모두 "이 인증서를 서명한 쪽을 내가 믿는 목록에서 찾지 못했다"는 뜻이다. 컴퓨터와 브라우저에는 믿는 발급 기관 목록이 미리 들어 있고, 서명이 그 목록으로 이어져야 통과한다. 두 경우를 가르는 건 오류 문구다. 인증서가 **자기 자신이 서명**한 것이면 `self-signed certificate`, 서명한 **상위 발급 기관을 못 찾으면** `unable to get local issuer certificate`가 뜬다.

## 5. 이름이 수상해도 통과한다

```
$ curl --cacert ca.crt --resolve bank-login-secure.test:8442:127.0.0.1 https://bank-login-secure.test:8442/
http=200 verify=0
```

`bank-login-secure.test`는 은행인 척하는 이름이다. 그런데 이 이름으로 발급받은 인증서는 이름이 맞으니 **통과**한다. 인증서는 "이 주소가 이 서버 것"임을 증명할 뿐, 그 주소가 내가 찾던 은행인지는 보증하지 않는다. 그래서 피싱 사이트에도 자물쇠가 뜬다. 주소창에서 직접 읽어야 하는 건 자물쇠가 아니라 **도메인 이름**이다.

## 정리

| 자물쇠가 말해 주는 것 | 말해 주지 않는 것 |
|---|---|
| 중간에서 내용을 엿보거나 바꾸기 어렵다 | 사이트 운영자가 믿을 만한가 |
| 주소의 이름과 인증서가 맞는다 | 주소가 내가 가려던 곳이 맞는가 |
| 믿는 발급 기관의 서명이 이어진다 | 사이트에 악성 코드가 없는가 |

인증서 검사 규칙은 [RFC 9110 §4.3.3](https://www.rfc-editor.org/rfc/rfc9110#section-4.3.3)(https 주소의 서버 인증서 확인)과 curl의 [SSL 인증서 문서](https://curl.se/docs/sslcerts.html)에 있다. 이 글의 실행 결과는 내가 로컬에서 돌린 것이고, 브라우저 경고 화면의 문구는 브라우저와 버전마다 달라 직접 확인하지 않았다.

비밀번호를 사이트가 어떻게 저장하는지는 [해시와 솔트로 보기](/posts/passwords-stored-as-hash/)에서 다룬다.
