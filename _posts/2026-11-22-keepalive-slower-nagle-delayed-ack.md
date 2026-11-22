---
title: "keep-alive로 연결을 재사용했더니 요청당 44ms로 느려질 때: Nagle 알고리즘과 지연 ACK"
description: "연결을 매번 새로 맺는 쪽이 1.35초, 재사용하는 쪽이 88초였다. 서버가 헤더와 본문을 따로 write하면 Nagle과 지연 ACK가 맞물려 요청마다 약 44ms를 기다린다. strace와 TCP_NODELAY로 확인했다."
date: 2026-11-22 20:00:00 +0900
categories: [전산학, 네트워크]
tags: [tcp, nagle, keep-alive, strace]
---

HTTP/1.1 keep-alive로 연결을 재사용하면 빨라져야 하는데, 직접 재 보니 **재사용 쪽이 오히려 65배 느렸다.** 원인은 서버가 응답의 헤더와 본문을 `write`로 두 번 나눠 보낸 것이다. 작은 조각 하나가 아직 ACK되지 않았으면 다음 작은 조각을 붙잡아 두는 **Nagle 알고리즘**과, ACK를 일부러 늦추는 **지연 ACK**가 서로를 기다려 요청마다 약 44ms가 사라진다. 두 번째 조각을 같은 `write`로 합치거나 `TCP_NODELAY`를 켜면 0.1ms로 내려온다.

> 환경: Linux 6.18.44 x86_64, Python 3.11.18, curl 8.5.0, 4코어 샌드박스. 모두 루프백(127.0.0.1)에서 직접 돌린 결과다. 절대 시간은 환경마다 다르다.
{: .prompt-info }

## 1. keep-alive가 켜진 건 확인했다

서버가 `HTTP/1.0`이면 curl은 요청마다 연결을 새로 맺고, `HTTP/1.1`이면 한 연결을 재사용한다. 서버 로그의 클라이언트 포트로 가려낸다.

```console
== server HTTP/1.0
* Connected to 127.0.0.1 (127.0.0.1) port 8101
* Closing connection
* Connected to 127.0.0.1 (127.0.0.1) port 8101
* Closing connection
req from client port 54288: GET /a HTTP/1.1
req from client port 54290: GET /b HTTP/1.1

== server HTTP/1.1
* Connected to 127.0.0.1 (127.0.0.1) port 8102
* Connection #0 to host 127.0.0.1 left intact
* Re-using existing connection with host 127.0.0.1
req from client port 55652: GET /a HTTP/1.1
req from client port 55652: GET /b HTTP/1.1
```

포트가 같으면 같은 TCP 연결이다. 여기까지는 기대대로다.

## 2. 그런데 재사용이 더 느리다

같은 서버에 2000번 요청해 연결을 매번 새로 맺는 경우와 재사용하는 경우를 쟀다.

```console
new   1.354s for 2000
reuse 88.156s for 2000
new   1.361s for 2000
```

(재사용 쪽은 두 번째 시도가 120초 제한에 걸려 끝까지 재지 못했다. 첫 측정의 88초가 전부다.) 요청당 88.156/2000 ≈ 44ms다. 루프백에서 44ms는 네트워크 지연일 수 없다.

## 3. 원인: write가 두 번이다

`strace`로 서버가 소켓에 쓰는 것을 보면 응답 하나에 `sendto`가 두 번 나온다.

```console
$ strace -f -e trace=sendto -p <서버 PID>
sendto(4, "HTTP/1.1 200 OK\r\nContent-Length:"..., 38, 0, NULL, 0) = 38
sendto(4, "hello\n", 6, 0, NULL, 0) = 6
sendto(4, "HTTP/1.1 200 OK\r\nContent-Length:"..., 38, 0, NULL, 0) = 38
sendto(4, "hello\n", 6, 0, NULL, 0) = 6
```

- **Nagle 알고리즘**([RFC 896](https://www.rfc-editor.org/rfc/rfc896.txt)): 보낸 데이터 중 ACK를 못 받은 것이 있으면, 작은 데이터는 ACK가 올 때까지 모아 둔다. 첫 조각(헤더 38바이트)은 바로 나가지만, 이 조각의 ACK가 오기 전에는 두 번째 조각(`hello`)이 나가지 못한다.
- **지연 ACK**([RFC 1122 §4.2.3.2](https://www.rfc-editor.org/rfc/rfc1122.txt)): 수신 쪽은 ACK를 바로 보내지 않고 조금 기다려도 된다(지연은 0.5초 미만이어야 한다고 규정). 클라이언트는 헤더만 받았고 응답이 덜 끝나 보낼 데이터도 없으니 ACK를 미룬다.

서버는 ACK를 기다리고, 클라이언트는 ACK를 미루니 한쪽이 타이머로 풀릴 때까지 멈춘다. 그 시간이 요청마다 44ms 안팎이다. 매번 새 연결을 맺을 때는 이 정체가 없었는데, 연결의 첫 조각은 미확인 데이터가 없어 Nagle에 걸리지 않기 때문이다. 이 설명 중 "44ms가 이 커널의 지연 ACK 타이머 값"이라는 부분은 문서로 확인하지 못했고, 측정값(중앙값 43.99ms)만 확인한 것이다.

## 4. 판별: 두 가지 수리법으로 같이 사라지는지

서버 코드만 바꿔서 세 가지를 비교했다(요청 100번, 한 연결).

```console
== split     (헤더·본문 write 2번)  100 reqs 4.355s  median 43.99ms  max 46.48ms
== oneshot   (한 번에 write)        100 reqs 0.015s  median 0.10ms   max 2.22ms
== nodelay   (write 2번 + TCP_NODELAY) 100 reqs 0.014s  median 0.11ms   max 2.30ms
```

`TCP_NODELAY`는 Nagle을 끄는 소켓 옵션이다([tcp(7)](https://man7.org/linux/man-pages/man7/tcp.7.html): "disable the Nagle algorithm … segments are always sent as soon as possible"). 코드 변경은 이 한 줄이다.

```python
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
```

| 관찰 | 의미 |
|---|---|
| 요청 지연이 일정하게 약 40ms대로 고정 | 네트워크 거리가 아니라 타이머를 기다리는 것 |
| 첫 요청만 빠르거나 연결을 새로 맺으면 빠름 | 연결 재사용 시 미확인 데이터가 남는 Nagle 패턴 |
| 한 번에 write하거나 `TCP_NODELAY`로 사라짐 | Nagle과 지연 ACK의 맞물림이 원인 |

서버가 응답을 만들어 한 번에 쓰거나(`wfile.write(헤더+본문)`), 쪼개 써야 한다면 `TCP_NODELAY`를 켜면 된다. 이 실험은 Python 표준 라이브러리 서버 기준이며, 다른 서버·프록시 환경에서 같은 값이 나온다는 보장은 없다.
