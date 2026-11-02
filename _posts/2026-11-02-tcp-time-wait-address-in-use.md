---
title: "서버를 껐다 켜면 'Address already in use'가 뜨는 이유: TIME_WAIT를 직접 보기"
description: "연결을 먼저 닫은 쪽에 TIME_WAIT가 남고 리눅스에서는 60초간 유지된다. /proc/net/tcp로 상태 변화를 관찰하고, SO_REUSEADDR 유무에 따라 bind가 갈리는 것을 확인했다."
date: 2026-11-02 20:00:00 +0900
categories: [전산학, 네트워크]
tags: [tcp, time-wait, so-reuseaddr]
---

서버를 종료한 직후 같은 포트로 다시 띄우면 `OSError: [Errno 98] Address already in use`가 날 수 있다. 원인은 **연결을 먼저 닫은 쪽에 TCP 연결 기록이 TIME_WAIT 상태로 남아 있기 때문**이고, 리눅스에서는 이 상태가 약 60초 유지된다. 소켓에 `SO_REUSEADDR`를 켜면 이 상태가 남아 있어도 `bind`된다.

> 환경: Linux 6.18.44, Python 3.11.18, 4코어 샌드박스. 모든 출력은 이 환경에서 직접 돌린 결과다. 다른 OS에서는 시간과 동작이 다를 수 있다.
{: .prompt-info }

## 상태 변화 관찰하기

`ss`가 없는 환경이어서 `/proc/net/tcp`의 상태 코드(06 = TIME_WAIT 등)를 직접 읽었다. 로컬호스트에서 서버(9100)와 클라이언트를 만들고, **서버가 먼저 `close()`** 하게 했다.

```text
1. connected
  local_port=9100 remote_port=0 LISTEN
  local_port=9100 remote_port=54566 ESTABLISHED
  local_port=54566 remote_port=9100 ESTABLISHED
2. server called close(), client has not yet
  local_port=9100 remote_port=0 LISTEN
  local_port=9100 remote_port=54566 FIN_WAIT2
  local_port=54566 remote_port=9100 CLOSE_WAIT
3. both closed
  local_port=9100 remote_port=0 LISTEN
  local_port=9100 remote_port=54566 TIME_WAIT
```

- 2단계: 먼저 닫은 서버 쪽은 `FIN_WAIT2`, 아직 안 닫은 클라이언트 쪽은 `CLOSE_WAIT`.
- 3단계: 클라이언트까지 닫자 클라이언트 기록은 사라지고, **먼저 닫은 서버 쪽만 `TIME_WAIT`로 남았다.**

[RFC 9293 §3.6.1](https://www.rfc-editor.org/rfc/rfc9293.html#name-half-closed-connections)에 해당 규정이 있다. 원문: "When a connection is closed actively, it MUST linger in the TIME-WAIT state for a time 2xMSL". MSL은 같은 문서의 용어집에서 "Arbitrarily defined to be 2 minutes"로 정의돼 있다. 즉 문서 기준 대기 시간은 4분이지만, 아래 측정에서 보듯 리눅스는 다른 값을 쓴다.

## 얼마나 남나, 그리고 bind는 되나

서버 소켓을 닫은 뒤 같은 주소에 다시 `bind`를 시도하고, TIME_WAIT가 사라질 때까지 시간을 쟀다.

```text
states ['06']
no SO_REUSEADDR: [Errno 98] Address already in use
SO_REUSEADDR: bind ok
TIME_WAIT lasted 60.7s
```

- `SO_REUSEADDR` 없이는 `Errno 98`, 있으면 성공.
- TIME_WAIT는 **60.7초**였다. RFC의 4분이 아니라 리눅스 커널의 고정값에 가깝다. 이 값은 `tcp_fin_timeout`(이 환경에서 60)과는 별개로 보이지만, 커널 소스는 이번에 확인하지 않았다.

## 판별법

같은 `Address already in use`라도 원인이 둘이다.

| 구분 | 확인 | 해결 |
|---|---|---|
| 다른 프로세스가 아직 LISTEN 중 | `/proc/net/tcp`에서 해당 포트가 `0A`(LISTEN) | 그 프로세스를 종료 |
| 닫힌 연결의 TIME_WAIT만 남음 | 해당 포트가 `06`뿐이고 LISTEN은 없음 | 60초 대기 또는 `SO_REUSEADDR` |

Python 표준 `socketserver`의 `allow_reuse_address = True`가 바로 이 옵션이다.

## 한계

로컬호스트 한 대에서만 확인했다. 실제 네트워크에서 TIME_WAIT가 쌓이는 규모나 `tcp_tw_reuse`의 효과는 측정하지 않았다.
