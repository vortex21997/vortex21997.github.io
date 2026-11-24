---
title: "배포했는데 내 브라우저에서만 옛날 화면일 때: Chirpy PWA 서비스 워커와 '새 콘텐츠가 있습니다'"
description: "푸시와 배포는 성공했는데 새로고침해도 홈과 검색이 옛 상태일 때. Chirpy의 서비스 워커가 캐시를 먼저 내주기 때문이다. 배포를 흉내 내 새로고침이 소용없다가 '업데이트' 버튼에서 바뀌는 과정을 직접 확인했다."
date: 2026-11-24 09:00:00 +0900
categories: [블로그, 운영]
tags: [chirpy, pwa, service-worker]
---

배포 워크플로는 초록색인데 내 브라우저에서만 새 글이 안 보이고 새로고침해도 그대로라면, **서버가 아니라 브라우저 안의 서비스 워커 캐시가 옛 페이지를 내주고 있을 가능성이 크다.**
Chirpy는 `_config.yml`의 `pwa.cache.enabled: true`가 기본이고, 이 설정에서는 같은 주소 요청을 네트워크보다 캐시가 먼저 받는다.
화면 아래에 뜨는 **"새 콘텐츠가 있습니다 / 업데이트"** 알림의 버튼을 눌러야 바뀐다.

> 서비스 워커(service worker): 사이트가 브라우저에 등록해 두는 스크립트로, 페이지 요청을 가로채 저장해 둔 응답을 대신 줄 수 있다. 동작 방식은 [MDN: Service Worker API 사용하기](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers)에 있다.
{: .prompt-info }

`Chirpy v7.6.0 기준`, 아래 실험은 Chromium(Playwright 1.63.0)과 Node v22.23.5, 로컬 정적 서버(`python3 -m http.server`)에서 했다. 실제 GitHub Pages가 아니라 **배포를 파일 수정으로 흉내 낸 것**이다.

## 판별: 서버 문제인가, 캐시 문제인가

| 확인 | 서버(배포) 문제 | 브라우저 캐시 문제 |
|---|---|---|
| 시크릿 창이나 다른 브라우저로 열었을 때 | 거기서도 옛 화면 | 거기서는 새 화면 |
| `curl -s https://vortex21997.github.io/ \| grep 찾는문장` | 안 나온다 | 나온다 |

시크릿 창에서는 등록된 서비스 워커가 없어 처음부터 네트워크로 받는다. `curl`에서 새 내용이 나오는데 내 브라우저만 옛 화면이면 이 글의 상황이다.
둘 다 옛 화면이면 이 글이 아니라 배포 쪽(Actions 실패, [미래 날짜로 빌드 제외](/posts/jekyll-future-date-skipped/) 등)을 본다.

## 서비스 워커가 하는 일

빌드한 `_site/sw.min.js`의 요청 처리 부분이다(출력 그대로, 줄바꿈만 넣었다).

```js
self.addEventListener("fetch", s => {
  s.request.headers.has("range") || s.respondWith(
    caches.match(s.request).then(n => n || fetch(s.request).then(n => { ... caches.open(swconf.cacheName).then(e => e.put(s.request, a)) ... }))
  )
})
```

`caches.match(...)`가 먼저고 네트워크(`fetch`)는 캐시에 없을 때만 탄다. 그리고 받은 응답은 `swconf.cacheName` 캐시에 넣는다.
캐시 이름은 `_site/assets/js/data/swconf.js`에서 정해진다.

```
cacheName: 'chirpy-1795479269'
```

테마의 `swconf.js` 템플릿을 보면 이 숫자는 `"now" | date: "%s"`, 즉 **빌드한 시각의 초 단위 타임스탬프**다. 배포할 때마다 이름이 바뀐다.
방문 후 캐시에 실제로 들어 있던 주소를 `caches.open(...).keys()`로 뽑아 보니 홈(`/`), `/categories/`, `/tags/`, `/archives/`, `/about/` 뿐 아니라 `/assets/js/data/search.json`도 있었다.
홈 목록과 검색 색인이 캐시에서 나오니, 새 글이 목록에도 검색에도 안 보이는 것이다.

## 직접 재현

1. 빌드한 `_site`를 로컬 서버로 띄우고 열었다가 한 번 새로고침한다(서비스 워커가 페이지를 제어하기 시작한다).
2. 서버 쪽 `index.html`의 부제목 문장을 `DEPLOYED-NEW`로 바꾼다(배포 흉내).
3. 새로고침한다.
4. `swconf.js`의 `cacheName`을 다른 값으로 바꾸고(새 빌드 흉내) 서비스 워커 갱신을 요청한다.
5. 다시 새로고침한다.
6. 알림의 "업데이트" 버튼을 누른다.

각 단계에서 부제목을 읽은 실제 출력이다.

```
1b after deploy, plain reload: AI로 진행합니다 — AI 에이전트와 함께 만드는 기록
2 reg state: { waiting: true, installing: false, active: true }
2 keys: [ 'chirpy-1795479269', 'chirpy-9999999999' ]
2 toast visible: toast w-auto rounded-5 text-nowrap fade show | 새 콘텐츠가 있습니다 업데이트
3 reload while waiting: AI로 진행합니다 — AI 에이전트와 함께 만드는 기록
4 after clicking update: DEPLOYED-NEW
```

- 서버 파일이 바뀐 뒤에도 일반 새로고침은 **옛 문장**을 보여 준다(1b).
- 새 서비스 워커는 내려받아졌지만 `waiting: true`, 즉 **대기** 상태다. 옛 것이 아직 페이지를 제어하고 있어서 캐시 이름이 둘 공존한다(2).
- 이때 알림이 뜬다. 알림을 무시하고 새로고침해도 옛 문장이다(3).
- "업데이트"를 누르면 대기 중이던 워커가 즉시 넘겨받고 페이지가 다시 로드되어 새 문장이 나온다(4). `app.min.js`가 버튼 클릭 시 `SKIP_WAITING` 메시지를 보내고 `controllerchange`에서 `location.reload()`를 하는 구조다.

## 풀기

- **알림이 보이면** "업데이트"를 누른다. 가장 빠르다.
- 알림을 놓쳤다면 이 사이트의 탭을 **전부** 닫았다가 다시 연다. 제어하는 탭이 없어져야 대기 중이던 워커가 활성화된다는 것이 서비스 워커 생명주기의 일반 규칙이다(MDN 문서 기준이며 이번에는 따로 재현하지 않았다).
- 캐시를 아예 쓰지 않으려면 `_config.yml`에서 `pwa.cache.enabled: false`로 둔다. `swconf.js` 템플릿 소스상 이 경우 `purge: true`가 되어 서비스 워커가 캐시를 비우고 쓰지 않게 되어 있다. 이 분기는 소스를 읽어 확인했고 빌드해 돌려 보지는 않았다.

> 새 글이 올라간 걸 방문자에게도 바로 보여 주고 싶다면 이 동작이 걸림돌이다. 다만 한 번 방문한 독자는 알림 버튼을 누르거나 탭을 닫기 전까지 옛 목록을 볼 수 있다는 점을 알고 쓰면 된다.
{: .prompt-tip }
