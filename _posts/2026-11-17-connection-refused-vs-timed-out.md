---
title: "curl이 'Connection refused'와 'Timeout was reached'로 갈리는 기준: RST가 오는가, 아무 응답이 없는가"
description: "같은 '연결 실패'인데 닫힌 포트는 즉시 curl (7), 패킷이 버려지면 curl (28)까지 기다린다. iptables DROP과 REJECT로 두 경우를 재현해 시간·종료 코드·소켓 상태로 판별했다."
date: 2026-11-17 20:00:00 +0900
categories: [전산학, 네트워크]
tags: [tcp, curl, iptables]
---

서버에 연결이 안 될 때 메시지는 크게 둘로 갈린다. **`Connection refused`는 상대 쪽 TCP가 "그 포트에는 아무도 없다"고 RST로 곧바로 답한 것**이고, **`Timeout was reached`(`ETIMEDOUT`)는 SYN에 아무 답도 오지 않은 것**이다. 앞은 몇 ms 안에 끝나고, 뒤는 타임아웃까지 기다린다. 그래서 "얼마나 걸려서 실패했나"가 가장 빠른 판별 기준이다.

> 환경: Linux 6.18.44 x86_64, curl 8.5.0, Python 3.11.18, 4코어 샌드박스. 모든 출력은 이 환경에서 직접 돌린 결과다. 루프백(127.0.0.1)에서 잰 것이라 실제 네트워크에서는 시간이 다르다.
{: .prompt-info }

## 1. 닫힌 포트: 즉시 거절

아무도 듣지 않는 포트(18099)로 접속한다.

```console
$ curl -sv --noproxy '*' http://127.0.0.1:18099/
*   Trying 127.0.0.1:18099...
* connect to 127.0.0.1 port 18099 from 127.0.0.1 port 54150 failed: Connection refused
* Failed to connect to 127.0.0.1 port 18099 after 0 ms: Couldn't connect to server
$ echo $?
7
```

`after 0 ms`에 `curl: (7)`로 끝났다. Python에서도 같다.

```text
18099 ConnectionRefusedError [Errno 111] Connection refused 0.0
```

RFC 9293 [3.5.2 Reset Generation](https://www.rfc-editor.org/rfc/rfc9293.html)은 "If the connection does not exist (CLOSED), then a reset is sent in response to any incoming segment except another reset."라고 적는다. 듣는 소켓이 없는 포트로 온 SYN에는 커널이 RST로 답하고, 클라이언트는 이를 `ECONNREFUSED`로 받는다.

## 2. 패킷이 버려질 때: 기다리다 타임아웃

방화벽이 SYN을 조용히 버리는 상황은 `iptables`로 만든다. 서버(18081)는 실제로 떠 있고 규칙만 다르다.

```console
$ iptables -A INPUT -p tcp --dport 18081 -j DROP
$ curl -sv --noproxy '*' --connect-timeout 3 http://127.0.0.1:18081/
*   Trying 127.0.0.1:18081...
* Failed to connect to 127.0.0.1 port 18081 after 3002 ms: Timeout was reached
$ echo $?
28
```

```text
18081 TimeoutError timed out 3.003
```

3초를 꽉 채우고 `curl: (28)`로 끝났다. 서버가 떠 있는지, 포트가 틀렸는지 이 메시지만으로는 알 수 없다. 응답이 아예 없었기 때문이다.

대기 중의 소켓 상태는 `/proc/net/tcp`에서 보인다(`state 02`가 SYN_SENT).

```console
$ awk 'NR>1 && $4=="02"{print "local",$2,"remote",$3,"state",$4,"retrnsmt_timer",$6}' /proc/net/tcp
local 0100007F:8EA6 remote 0100007F:46A1 state 02 retrnsmt_timer 01:00000000
```

`0100007F:46A1`은 127.0.0.1:18081(0x46A1)이고, 재전송 타이머(`01`)가 걸려 SYN을 다시 보내려고 대기 중이다. `--connect-timeout`이 없으면 이 재전송이 계속된다. [tcp(7)](https://man7.org/linux/man-pages/man7/tcp.7.html)에 따르면 `tcp_syn_retries` 기본값은 6이고 "약 127초" 재시도한다. 이 값 6은 이 샌드박스에서 `/proc/sys/net/ipv4/tcp_syn_retries`로 확인했고, 127초 자체를 끝까지 재 보지는 않았다.

## 3. 방화벽이 있어도 "거절"로 보이는 경우

방화벽이라고 모두 타임아웃이 되는 건 아니다. 규칙을 `DROP` 대신 `REJECT --reject-with tcp-reset`으로 바꾸면 같은 포트가 닫힌 포트와 똑같이 보인다.

```console
$ iptables -A INPUT -p tcp --dport 18081 -j REJECT --reject-with tcp-reset
$ curl -sS --noproxy '*' http://127.0.0.1:18081/
curl: (7) Failed to connect to 127.0.0.1 port 18081 after 0 ms: Couldn't connect to server
```

서버가 떠 있는데도 `refused`다. 따라서 `refused`는 "서버 프로세스가 없다"가 아니라 **"RST를 보낸 누군가(서버 커널이나 방화벽)가 있다"**까지만 말해 준다.

## 판별 정리

| 관찰 | 의미 | 먼저 볼 것 |
|---|---|---|
| 즉시 `Connection refused` (curl 7) | RST가 돌아옴 | 서버 프로세스가 떠 있나, 포트·바인드 주소(127.0.0.1만 듣는지) |
| 한참 뒤 `Timeout was reached` (curl 28) | SYN에 응답 없음 | 방화벽·보안 그룹 DROP, 경로 단절, 잘못된 IP |

원인이 다른 두 상황을 같은 "연결이 안 돼요"로 부르기 쉬운데, 위 기준은 소요 시간만 봐도 갈린다. 단, 방화벽이 REJECT로 설정돼 있으면 앞 줄이 서버 문제가 아닐 수도 있다.
