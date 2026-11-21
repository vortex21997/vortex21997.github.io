---
title: "report.txt와 Report.txt가 리눅스에서는 두 파일인데 윈도우에서는 한 파일인 이유"
description: "윈도우는 파일 이름의 대소문자를 같은 글자로 보고, 리눅스는 다른 글자로 봅니다. 리눅스에서 두 파일을 실제로 만들어 확인하고, 윈도우로 옮길 때 생기는 문제와 미리 찾는 명령을 정리했습니다."
date: 2026-11-21 13:00:00 +0900
categories: [컴퓨터 기초, 파일·운영체제]
tags: [대소문자, 파일이름, ntfs]
---

**윈도우의 파일 시스템(NTFS 등)은 기본적으로 파일 이름의 대문자와 소문자를 같은 글자로 취급하고, 리눅스는 다른 글자로 취급합니다.** 그래서 `report.txt`와 `Report.txt`는 리눅스에서는 서로 다른 파일 두 개이고, 윈도우에서는 같은 이름 하나입니다. 이 차이는 둘이 파일을 주고받을 때(압축 파일, 깃 저장소, 공유 폴더) 가끔 "파일이 하나 사라졌다"는 증상으로 나타납니다.

> *파일 시스템*은 저장장치에 파일을 어떤 이름과 구조로 보관할지 정한 규칙입니다. 대소문자를 구분하는지도 이 규칙에 들어 있습니다.
{: .prompt-info }

## 리눅스에서 직접 만들어 보기

아래는 리눅스 샌드박스(커널 6.18, ext4)에서 실행한 결과입니다.

```console
$ echo "소문자 report" > report.txt
$ echo "대문자 Report" > Report.txt
$ ls -l
-rw-r--r-- 1 root root 17 Nov 21 04:13 Report.txt
-rw-r--r-- 1 root root 17 Nov 21 04:13 report.txt
$ cat report.txt Report.txt
소문자 report
대문자 Report
$ stat -c '%i %n' report.txt Report.txt
614442 report.txt
614443 Report.txt
```

두 파일의 내용이 각각 살아 있고, 파일의 고유 번호(inode, 저장장치 안에서 파일을 가리키는 번호)도 다릅니다. 진짜로 별개의 파일입니다.

세 번째 철자 `REPORT.TXT`는 어느 쪽과도 일치하지 않습니다.

```console
$ cat REPORT.TXT
cat: REPORT.TXT: No such file or directory
```

리눅스는 이름을 글자 그대로 비교하므로 대소문자가 한 글자라도 다르면 "없는 파일"입니다. 윈도우에서는 `REPORT.TXT`로 열어도 열립니다.

## 윈도우는 어떻게 다른가

Microsoft 문서는 기본 동작을 이렇게 설명합니다. ([Case Sensitivity - Microsoft Learn](https://learn.microsoft.com/en-us/windows/wsl/case-sensitivity), 문서 갱신 2026-06 기준)

- Windows 파일 시스템은 파일·디렉터리 이름을 대소문자 구분 없이 다룬다. `FOO.txt`와 `foo.txt`는 같은 파일로 취급된다.
- Linux 파일 시스템은 대소문자를 구분한다. 둘은 다른 파일이다.

같은 문서에 이런 주의도 있습니다. 대소문자만 다른 파일이 윈도우 쪽으로 넘어오면, 파일 탐색기에는 둘 다 보여도 **어느 쪽을 선택해도 하나만 열린다**고 합니다. 이 글에서는 윈도우 환경을 직접 돌려 보지 못했으므로, 윈도우 쪽 동작은 이 문서에 쓰인 내용 그대로만 옮겼습니다.

> 폴더마다 대소문자 구분을 켜는 기능도 있습니다(Windows 10 빌드 17107부터). 관리자 권한 PowerShell에서 `fsutil.exe file setCaseSensitiveInfo <경로> enable`을 실행하고, 폴더가 비어 있어야 합니다. 다만 문서는 대소문자가 다른 파일을 가정하지 않는 윈도우 프로그램이 그 폴더에서 파일을 못 찾을 수 있다고 경고합니다. 일반 사용자는 기본값을 그대로 두는 편이 안전합니다.
{: .prompt-warning }

## 실제로 문제가 되는 때

- **리눅스에서 만든 압축 파일을 윈도우에서 풀 때**: 이름이 대소문자만 다른 파일이 들어 있으면 하나가 다른 하나를 덮어쓰거나 건너뛸 수 있습니다.
- **깃 저장소**: 깃은 이름을 구분해서 저장하는데 윈도우 폴더는 구분하지 못하므로, 한쪽에서 만든 두 파일이 다른 쪽에서는 충돌합니다. 깃에는 이 상황을 위한 `core.ignorecase` 설정이 있습니다. ([git-config 문서](https://git-scm.com/docs/git-config#Documentation/git-config.txt-coreignoreCase)) Microsoft 문서는 대소문자를 구분하지 않는 파일 시스템에서 `false`로 두면 혼란스러운 오류와 중복 파일이 생길 수 있다고 경고합니다.
- **웹 서버와 코드의 파일 경로**: 윈도우에서 개발할 때는 `Logo.png`를 `logo.png`로 적어도 열리는데, 리눅스 서버에 올리면 같은 코드가 "파일 없음"이 됩니다. 이 블로그가 도는 GitHub Pages 같은 리눅스 서버도 같은 규칙을 따를 가능성이 큽니다(직접 확인하지는 않았습니다).

## 옮기기 전에 겹치는 이름 찾기

소문자로 바꿨을 때 같아지는 이름이 있는지 보면 됩니다. 리눅스에서 실행한 결과입니다.

```console
$ ls | tr A-Z a-z | sort | uniq -d
report.txt
```

`uniq -d`는 두 번 이상 나온 줄만 보여 줍니다. 출력이 있으면 윈도우로 옮길 때 충돌하는 이름이 있다는 뜻입니다. 깃 저장소는 `git ls-files | tr A-Z a-z | sort | uniq -d`로 같은 검사를 할 수 있고, 이 블로그 저장소에서 돌리니 겹치는 이름은 0개였습니다.

## 정리

| | 윈도우(기본) | 리눅스 |
|---|---|---|
| `report.txt`와 `Report.txt` | 같은 이름 | 다른 파일 |
| `REPORT.TXT`로 열기 | 열림 | `No such file or directory` |

- 환경: 리눅스 샌드박스(커널 6.18.44, ext4), Python 3.11, git 2.43. 윈도우 쪽은 위 Microsoft 문서를 근거로 했고 직접 실행하지 않았습니다.
