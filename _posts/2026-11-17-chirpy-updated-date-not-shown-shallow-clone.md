---
title: "글을 고쳤는데 Chirpy에 '업데이트' 날짜가 안 뜰 때: 커밋 수와 fetch-depth"
description: "글을 수정해 푸시했는데 '게시' 날짜만 보이고 '업데이트'가 없을 때. 이 블로그의 lastmod 훅은 그 글의 커밋이 2개 이상이어야 날짜를 달고, 얕은 클론에서는 커밋이 1개로 보인다. 직접 빌드해 가려냈다."
date: 2026-11-17 09:00:00 +0900
categories: [블로그, 운영]
tags: [chirpy, lastmod, fetch-depth]
---

글을 고쳐 푸시했는데 페이지에는 `게시 2026/01/01`만 보이고 `업데이트`가 없다면, 원인은 둘 중 하나다.
**① 그 글의 커밋이 아직 1개뿐이거나, ② 빌드하는 곳의 git 히스토리가 잘려 있어서 1개로 보이거나.**
Chirpy 자체가 아니라 이 블로그의 `_plugins/posts-lastmod-hook.rb`가 정하는 동작이다.

> 2026-11 기준. Chirpy 7.6.0, Jekyll 4.4.1, git 2.43.0, Ruby 3.3.6, 4코어 샌드박스에서 확인했다.
{: .prompt-info }

## 날짜는 어디서 오나

Chirpy의 글 레이아웃(`_layouts/post.html`)은 `last_modified_at`이 있고 `date`와 다를 때만 `업데이트`를 그린다.

{% raw %}
```liquid
{% if page.last_modified_at and page.last_modified_at != page.date %}
  <span>
    {{ site.data.locales[lang].post.updated }}
    {% include datetime.html date=page.last_modified_at tooltip=true lang=lang %}
  </span>
{% endif %}
```
{% endraw %}

`last_modified_at`은 front matter에 직접 적지 않아도 된다. 이 저장소의 `_plugins/posts-lastmod-hook.rb`가 빌드할 때 git 기록에서 채운다.

```ruby
commit_num = `git rev-list --count HEAD "#{ post.path }"`

if commit_num.to_i > 1
  lastmod_date = `git log -1 --pretty="%ad" --date=iso "#{ post.path }"`
  post.data['last_modified_at'] = lastmod_date
end
```

조건이 `> 1`이다. 글을 처음 커밋한 것이 1번이므로, **수정 커밋이 하나라도 있어야** 날짜가 붙는다.
그리고 `git rev-list --count HEAD <파일>`은 **지금 있는 히스토리 안에서만** 센다.

## 직접 돌려 본 결과

글 한 편짜리 임시 사이트를 만들어 같은 훅으로 빌드하고, 페이지의 `<time data-ts>` 개수를 셌다.
(`업데이트`라는 글자는 사이드바에도 있어서 문구 검색으로는 가려지지 않는다. `<time>`이 2개면 게시+업데이트다.)

| 상태 | `git rev-list --count HEAD _posts/…` | 글 머리의 `<time>` |
|---|---|---|
| 글 커밋 1번 | `1` | 1개 (게시만) |
| 글 수정 후 커밋 2번 | `2` | 2개 (게시, 업데이트) |
| 위 저장소를 `git clone --depth=1` | `1` (`--is-shallow-repository`가 `true`) | 1개 |
| 위 클론을 `git fetch --unshallow` | `2` | 2개 |

2번 줄의 업데이트 부분은 이렇게 나왔다.

```html
<span> 게시 <time data-ts="1767225600" data-df="YYYY/MM/DD" ...> 2026/01/01 </time> </span>
<span> 업데이트 <time data-ts="1794874480" data-df="YYYY/MM/DD" ...> 2026/11/17 </time> </span>
```

같은 저장소·같은 커밋인데 **히스토리를 얼마나 가져왔느냐만으로** 결과가 갈렸다.

## 판별법

```bash
git rev-parse --is-shallow-repository      # true면 히스토리가 잘려 있다
git rev-list --count HEAD _posts/<파일>.md  # 2 이상이어야 '업데이트'가 뜬다
```

- `false`이고 개수가 `1` → **정말 수정 커밋이 없는 것**이다. 고친 내용을 커밋해 푸시하면 된다. 새 글을 쓰고 같은 커밋에서 고친 경우도 여기에 해당한다.
- `true`이고 개수가 `1` → **히스토리가 잘려서 그렇다.** 로컬이면 `git fetch --unshallow`, CI면 체크아웃 설정을 본다.
- 개수가 `2` 이상인데도 안 뜬다 → 훅 파일이 사라졌거나, 오래된 `_site`를 보고 있는지 확인한다.

## 배포 쪽은 어떻게 되어 있나

`actions/checkout`은 가져오는 커밋 수의 기본값이 1이다. [공식 README](https://github.com/actions/checkout)는 `fetch-depth`를 이렇게 설명한다.

> Number of commits to fetch. 0 indicates all history for all branches and tags. Default: 1

그래서 이 훅을 쓰는 사이트의 워크플로는 `fetch-depth: 0`이 필요하다. 이 저장소의 `.github/workflows/pages-deploy.yml`에는 이미 들어 있다.

```yaml
      - name: Checkout
        uses: actions/checkout@v7
        with:
          fetch-depth: 0
```

이 줄을 지우거나 워크플로를 새로 짜면서 빠뜨리면, **배포된 사이트에서만** 모든 글의 `업데이트`가 한꺼번에 사라진다. 에러는 나지 않는다. 히스토리가 온전한 로컬 클론에서 보면 정상이라 알아채기 어렵다.

> 이 글을 쓴 세션의 클론도 `--is-shallow-repository`가 `true`였다. 로컬 빌드로 날짜를 확인할 때는 먼저 이 값을 본다.
{: .prompt-warning }
