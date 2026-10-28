---
title: "html-proofer가 'Checking 0 internal links'로 통과할 때"
description: "로컬에서 html-proofer가 링크를 0개 검사하고 성공으로 끝난다. 로케일이 US-ASCII라서 한글 페이지를 못 읽고 건너뛴 것이다. 깨진 링크를 심어 두 상태를 비교했다."
date: 2026-10-28 10:55:00 +0900
categories: [자동화, 워크플로]
tags: [github-actions, html-proofer, jekyll, 로케일]
---

이 블로그의 배포 워크플로(`.github/workflows/pages-deploy.yml`)에는 빌드 뒤에 html-proofer로 내부 링크를 검사하는 단계가 있다.
이걸 로컬에서 똑같이 돌려 봤더니 **성공으로 끝났는데 링크를 하나도 검사하지 않았다.**

> 2026-10 기준. 환경: Ruby 3.3.6, Jekyll 4.4.1, html-proofer 5.2.3, jekyll-theme-chirpy 7.6.0. 아래 출력은 모두 이 환경에서 직접 돌린 것이다.
{: .prompt-info }

## 증상

워크플로의 Test site 단계와 같은 인자로 실행했다.

```bash
JEKYLL_ENV=production bundle exec jekyll build
bundle exec htmlproofer _site \
  --disable-external \
  --ignore-urls "/^http:\/\/127.0.0.1/,/^http:\/\/0.0.0.0/,/^http:\/\/localhost/"
```

끝부분은 이랬다.

```text
Checking 0 internal links
Checking internal link hashes in 0 files
Ran on 52 files!


HTML-Proofer finished successfully.
Finished in 0.02 seconds
```

종료 코드는 0이다. 52개 파일을 훑었다면서 내부 링크가 0개일 수는 없다.

## 원인: 로케일이 US-ASCII

출력 위쪽에는 JSON 한 줄짜리 경고가 파일 수만큼 쏟아졌다. 핵심 부분만 옮기면 이렇다.

```text
"message":"Task may have ended with unhandled exception."
"class":"Encoding::InvalidByteSequenceError","message":"\"\\xED\" on US-ASCII"
```

이 환경은 `LANG`과 `LC_ALL`이 비어 있었고, Ruby는 이때 파일을 US-ASCII로 읽는다.
한글이 든 HTML(`\xED`는 한글 UTF-8 바이트의 첫 글자)을 읽다가 예외가 나고, html-proofer는 **그 파일을 실패로 치지 않고 조용히 건너뛴다.**
경고가 52줄 중 51줄이었다. 한글이 없는 파일 하나만 정상적으로 읽혔다.

`LC_ALL=C.UTF-8`을 주고 같은 명령을 다시 돌리면 달라진다.

```text
Checking 152 internal links
Checking internal link hashes in 15 files
Ran on 52 files!
...
HTML-Proofer finished successfully.
```

0개가 152개가 됐다.

## 판별법: 통과가 진짜인지 보는 기준

"성공"이라는 문구만으로는 둘을 구분할 수 없다. 이 숫자로 가른다.

| | 정상 | 로케일 문제 |
|---|---|---|
| `Checking N internal links` | 100개 이상 (이 블로그는 152) | **0** |
| `Checking internal link hashes in N files` | 15 | **0** |
| 출력 위쪽의 `Encoding::InvalidByteSequenceError` | 없음 | 파일 수만큼 |
| 종료 코드 | 0 | **0 (똑같다)** |

종료 코드가 같으니 CI에 그대로 넣었을 때 알아챌 방법이 숫자뿐이다.

## 깨진 링크를 심어 확인

"0개 검사"가 진짜로 검사를 놓치는 건지 확인하려고, 빌드된 사본의 글 하나에 없는 글로 가는 링크를 넣었다.

```html
<a href="/posts/no-such-post/">broken</a>
```

UTF-8 로케일에서는 잡는다.

```text
Checking 153 internal links
...
For the Links > Internal check, the following failures were found:

* At site/posts/claude-code-context/index.html:33:

  internally linking to /posts/no-such-post/, which does not exist

HTML-Proofer found 1 failure!
```

종료 코드는 1이다. 로케일을 비운 채 같은 사본을 돌리면 이렇게 나온다.

```text
Checking internal link hashes in 0 files
Ran on 52 files!
...
HTML-Proofer finished successfully.
```

종료 코드는 0이다. **깨진 링크가 있는데 통과한다.**

## 해결

로컬에서는 로케일을 지정한다.

```bash
LC_ALL=C.UTF-8 bundle exec htmlproofer _site --disable-external
```

셸 프로필에 `export LC_ALL=C.UTF-8`을 넣어 두는 쪽이 편하다. 시스템에 `C.UTF-8`이 없으면 `en_US.UTF-8` 같은 UTF-8 로케일을 쓴다.

## GitHub Actions에서는

위 워크플로는 `ubuntu-latest` 러너에서 돈다. 이 글에서 US-ASCII로 읽힌 건 내가 쓴 샌드박스 환경이고, **러너의 로케일은 따로 확인하지 못했다.** 그래서 CI에서도 같은 문제가 있다고는 쓰지 않는다.

CI 로그에서 확인할 수 있다. Test site 단계 끝에 `Checking N internal links`가 0이 아닌지만 보면 된다.
0이면 위 표의 로케일 문제이고, 단계에 `env: LC_ALL: C.UTF-8`을 추가하면 된다.

## 참고

- html-proofer: <https://github.com/gjtorikian/html-proofer>
- 이 블로그의 워크플로: `.github/workflows/pages-deploy.yml`의 `Test site` 단계
