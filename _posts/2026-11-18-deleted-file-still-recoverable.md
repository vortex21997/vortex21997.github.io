---
title: "파일을 삭제했는데 복구 프로그램은 왜 되살릴 수 있나: 지워진 건 '목록'이지 내용이 아니다"
description: "삭제한 파일의 내용이 저장장치에 그대로 남아 있는 것을 ext4 이미지로 확인했다. 삭제는 디렉터리 항목과 사용 중 표시만 바꾸고, 내용이 사라지는 건 그 칸을 덮어쓸 때다."
date: 2026-11-18 13:00:00 +0900
categories: [컴퓨터 기초, 파일·운영체제]
tags: [파일 삭제, 복구, ext4]
---

**삭제는 파일 내용을 지우는 게 아니라, "이 칸은 이제 써도 된다"고 표시를 바꾸는 일이다.** 그래서 새 파일이 그 칸에 쓰이기 전까지는 내용이 저장장치에 그대로 있고, 복구 프로그램은 그걸 다시 찾아 주는 것뿐이다.

> 아래 출력은 Linux 6.18, e2fsprogs 1.47.0(`debugfs`), 8MB짜리 ext4 이미지 파일에서 직접 돌린 결과다. 윈도우의 NTFS나 맥의 APFS는 구조가 달라서 같은 출력이 나온다고 말할 수 없다. 이 글은 ext4에서 본 것만 말한다.
{: .prompt-info }

## 실험 준비: 29바이트짜리 파일 하나

실제 디스크 대신 8MB짜리 파일을 ext4로 포맷해서 쓴다. 지워도 되는 연습장이다. 안에 `memo.txt`를 넣고, 용어를 먼저 풀면 이렇다.

- **inode(아이노드)**: 파일의 이름을 뺀 정보(크기, 권한, 내용이 있는 칸의 위치)를 적어 둔 카드. 이름은 폴더 쪽 목록에 따로 있다.
- **블록**: 저장장치를 나눈 칸. 이 이미지에서는 4096바이트다.

```bash
echo "SECRET-MEMO-2026 meet at 3pm" > src/memo.txt
truncate -s 8M d.img && mkfs.ext4 -q -d src d.img
debugfs -R "blocks /memo.txt" d.img
```

```text
1162
```

`memo.txt`의 내용은 1162번 칸에 있다. 이미지 전체에서 내용 문자열을 찾으면 한 번 나온다.

```bash
grep -a -c SECRET d.img
```

```text
1
```

## 삭제하고 나서 본 것

`debugfs`의 `rm`으로 지운다. 파일 관리자에서 휴지통을 비우는 것과 같은 단계(이름과 inode를 해제)를 한다. 지운 뒤 inode 카드를 다시 본다.

```bash
debugfs -w -R "rm /memo.txt" d.img
debugfs -R "stat <12>" d.img
```

```text
Inode: 12   Type: regular    Mode:  0644   Flags: 0x80000
User:     0   Group:     0   Project:     0   Size: 29
Links: 0   Blockcount: 8
 dtime: 0x6afd2616:(00000000) -- Wed Nov 18 04:14:14 2026
EXTENTS:
(0):1162
```

바뀐 것은 둘이다. `Links`가 1에서 **0**이 됐고(이 파일을 가리키는 이름이 없다), `dtime`(삭제 시각)이 찍혔다. 반면 `Size: 29`와 내용 위치 `(0):1162`는 **그대로**다.

1162번 칸의 상태를 물어보면 이렇게 나온다.

```bash
debugfs -R "testb 1162" d.img
```

```text
Block 1162 not in use
```

"쓰는 중이 아님"이다. 비어 있다는 뜻이지, 0으로 채워졌다는 뜻이 아니다. 실제로 이미지를 다시 검색하면 내용이 나온다.

```bash
grep -a -c SECRET d.img
```

```text
1
```

폴더 쪽에도 흔적이 있다. 루트 폴더 목록을 지운 항목까지 보면 `memo.txt`가 `<12>`(inode 12번)로 남아 있다.

```bash
debugfs -R "ls -d /" d.img
```

```text
 2  (12) .    2  (12) ..    11  (4060) lost+found   <12> (4040) memo.txt
```

## 복구 프로그램이 하는 일, 그리고 못 하는 때

위 세 가지(inode 카드의 위치 정보, 폴더의 지워진 항목, 칸에 남은 내용)가 복구의 재료다. 복구 도구는 이걸 읽어서 "이 칸들이 한때 이 파일이었다"고 맞춰 본다. ext4 inode의 구조는 [커널 문서](https://www.kernel.org/doc/html/latest/filesystems/ext4/inodes.html)에 정리돼 있고, 위 명령의 옵션은 [debugfs man 페이지](https://man7.org/linux/man-pages/man8/debugfs.8.html)에 있다.

내용이 정말 사라지는 때는 **그 칸에 다른 것이 쓰일 때**다. 같은 이미지에서 1162번 칸만 0으로 덮어써 보면 이렇다.

```bash
dd if=/dev/zero of=d.img bs=4096 seek=1162 count=1 conv=notrunc
grep -a -c SECRET d.img
```

```text
4096 bytes (4.1 kB, 4.0 KiB) copied, 7.743e-05 s, 52.9 MB/s
0
```

검색 결과가 0이 됐다. 이 상태에서는 inode 카드가 위치를 가리켜도(`Size: 29`는 그대로다) 읽을 내용이 없다.

그래서 현실에서는 이렇게 이해하면 된다.

- 지운 직후 **아무것도 설치·저장하지 않고** 복구를 시도할수록 되살릴 가능성이 높다. 새로 쓰는 파일이 그 칸을 가져갈 수 있기 때문이다.
- 오래 쓴 컴퓨터일수록, 디스크가 꽉 찰수록 빈 칸이 다시 쓰일 가능성이 크다.
- 정말 지워야 하는 파일이면 "삭제"만으로는 부족하다. 그 칸을 덮어쓰는 단계가 따로 필요하다.

## 확인하지 못한 것

- **SSD에서의 동작**: SSD는 운영체제가 "이 칸은 안 쓴다"고 알려 주는 TRIM 명령이 있어서 지운 내용이 더 빨리 사라질 수 있다고 알려져 있다([fstrim man 페이지](https://man7.org/linux/man-pages/man8/fstrim.8.html)). 이 샌드박스는 파일 이미지라서 TRIM이 도는 실제 SSD로는 확인하지 못했다. 위 실험은 "ext4의 삭제 자체가 내용을 지우지 않는다"까지만 보여 준다.
- **윈도우·맥의 휴지통**: 휴지통은 파일을 다른 폴더로 옮겨 두는 기능이라 이 글의 "휴지통을 비운 뒤" 단계와는 별개다. NTFS·APFS에서의 복구 가능성도 이 글에서 다루지 않았다.

한 줄로 줄이면, 삭제는 **이름과 사용 표시를 바꾸는 일**이고, 내용은 그 칸이 재사용될 때 사라진다.
