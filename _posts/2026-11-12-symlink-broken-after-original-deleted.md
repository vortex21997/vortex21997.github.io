---
title: "원본을 지웠더니 바로가기가 안 열리는 이유: 심볼릭 링크와 하드 링크 비교"
description: "원본 파일을 지우면 바로가기(심볼릭 링크)는 'No such file or directory'로 깨지는데 하드 링크는 멀쩡하다. ln, ls -li, stat 출력으로 둘의 차이를 확인했다."
date: 2026-11-12 13:00:00 +0900
categories: [컴퓨터 기초, 파일·운영체제]
tags: [심볼릭 링크, 하드 링크, ln]
---

**바로가기(심볼릭 링크)는 파일이 아니라 '파일 이름이 적힌 쪽지'라서, 원본을 지우면 쪽지가 가리키는 곳이 사라져 열리지 않는다.** 반대로 하드 링크는 같은 파일에 이름을 하나 더 붙인 것이라, 이름 하나를 지워도 다른 이름으로 열린다. 복사본은 처음부터 별개의 파일이다.

> 아래 출력은 Linux 6.18, ext4, GNU coreutils 9.4(`ln`)에서 직접 돌린 결과다. Windows의 `.lnk` 바로가기와 NTFS 링크는 이 글에서 확인하지 않았다.
{: .prompt-info }

## 세 가지를 만들어 비교하기

용어부터. **inode**는 파일시스템이 파일 내용을 가리키려고 붙이는 번호이고, 우리가 보는 파일 이름은 그 번호로 가는 안내표다.

```bash
echo hello > original.txt
ln original.txt hard.txt        # 하드 링크
ln -s original.txt soft.txt     # 심볼릭 링크
cp original.txt copy.txt        # 복사
ls -li
stat -c '%n inode=%i links=%h size=%s' original.txt hard.txt soft.txt copy.txt
```

```
679983 -rw-r--r-- 1 root root  6 Nov 12 04:14 copy.txt
679981 -rw-r--r-- 2 root root  6 Nov 12 04:14 hard.txt
679981 -rw-r--r-- 2 root root  6 Nov 12 04:14 original.txt
679982 lrwxrwxrwx 1 root root 12 Nov 12 04:14 soft.txt -> original.txt
original.txt inode=679981 links=2 size=6
hard.txt inode=679981 links=2 size=6
soft.txt inode=679982 links=1 size=12
copy.txt inode=679983 links=1 size=6
```

- `original.txt`와 `hard.txt`는 inode가 같다(679981). 이름 둘이 같은 파일을 가리키고, 링크 수가 2다.
- `soft.txt`는 inode가 따로 있고 크기가 12다. 안에 든 것은 내용이 아니라 `original.txt`라는 글자 12개다.
- `copy.txt`도 inode가 따로지만, 내용 자체를 한 벌 더 가진 별개 파일이다.

## 원본을 고치면, 그리고 지우면

```bash
echo changed > original.txt
cat hard.txt copy.txt soft.txt
```

```
changed
hello
changed
```

하드 링크와 바로가기는 바뀐 내용을 보여주고, 복사본만 `hello` 그대로다. 이제 원본 이름을 지운다.

```bash
unlink original.txt
cat hard.txt
cat soft.txt
```

```
changed
cat: soft.txt: No such file or directory
```

하드 링크는 열리고, 심볼릭 링크는 **`No such file or directory`** 로 실패한다. 메시지가 `soft.txt`를 가리키고 있어 "soft.txt가 없다"로 읽히지만, 실제로 없는 것은 쪽지가 가리키는 `original.txt`다.

## 깨진 링크 판별법

링크 자체는 아직 있다. `ls`에는 그대로 보인다.

```bash
ls -li soft.txt; readlink soft.txt
test -e soft.txt; echo "test -e exit=$?"
test -L soft.txt; echo "test -L exit=$?"
```

```
679982 lrwxrwxrwx 1 root root 12 Nov 12 04:14 soft.txt -> original.txt
original.txt
test -e exit=1
test -L exit=0
```

- `test -L`은 "이 이름이 링크인가"를 보고 성공(0)이다.
- `test -e`는 링크를 따라가서 "대상이 있는가"를 보고 실패(1)다.

두 결과가 갈리면 **링크는 있는데 가리키는 곳이 없는 깨진 링크**다. `readlink`로 쪽지에 적힌 이름을 확인하면 어디를 다시 만들어야 하는지 알 수 있다.

같은 이름으로 원본을 다시 만들면 링크가 살아난다. 링크는 inode가 아니라 이름을 기억하기 때문이다.

```bash
echo new > original.txt
cat soft.txt
```

```
new
```

## 정리

| | 하드 링크 | 심볼릭 링크 | 복사 |
|---|---|---|---|
| inode | 원본과 같음 | 따로 | 따로 |
| 안에 든 것 | 원본과 같은 내용 | 대상 이름 | 내용 한 벌 |
| 원본 이름을 지우면 | 그대로 열림 | 깨짐 | 영향 없음 |
| 원본을 수정하면 | 같이 바뀜 | 같이 바뀜 | 안 바뀜 |

하드 링크는 마지막 이름이 지워질 때(링크 수 0, 그리고 열고 있는 프로세스도 없을 때) 비로소 내용이 사라진다. 이 "열고 있는 프로세스" 부분은 [파일을 지웠는데 df 용량이 그대로인 이유]({% post_url 2026-11-11-deleted-file-space-not-freed-open-fd %})에서 다뤘다.

## 근거

- [ln(1)](https://man7.org/linux/man-pages/man1/ln.1.html) — 하드 링크가 기본이고 `-s`가 심볼릭 링크
- [symlink(7)](https://man7.org/linux/man-pages/man7/symlink.7.html) — 심볼릭 링크는 경로 문자열을 담고, 대상이 없으면 dangling 상태
- [link(2)](https://man7.org/linux/man-pages/man2/link.2.html) — 하드 링크는 같은 파일에 이름을 더하는 것
