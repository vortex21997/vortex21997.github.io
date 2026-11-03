---
title: "압축했는데 용량이 안 줄어드는 이유: 텍스트와 이미지를 gzip으로 비교하기"
description: "텍스트는 398KB가 94KB로 줄지만 난수 데이터와 이미 압축된 WebP는 거의 그대로이고, 한 번 더 압축하면 오히려 커진다. 직접 gzip을 돌려 확인했다."
date: 2026-11-03 13:00:00 +0900
categories: [컴퓨터 기초, 파일·운영체제]
tags: [압축, gzip, 파일 크기]
---

사진이나 동영상 폴더를 ZIP으로 묶었는데 용량이 거의 그대로이거나 오히려 조금 커지는 건 고장이 아니다. **압축은 "반복되는 패턴"을 짧게 줄여 쓰는 방식이라, 반복이 없는 데이터는 줄일 게 없다.** JPG·PNG·WebP·MP4 같은 파일은 이미 한 번 압축된 결과물이라 반복이 거의 남아 있지 않다.

> 아래 수치는 Linux 6.18, gzip 1.12, Python 3.11 샌드박스에서 직접 잰 값이다. 파일마다 달라진다.
{: .prompt-info }

## 실험: 같은 도구로 세 종류의 파일 압축하기

`gzip`은 ZIP과 같은 DEFLATE 방식(반복된 문자열을 앞에서 가리키는 방식과 자주 나오는 글자를 짧은 부호로 바꾸는 방식의 조합)을 쓴다. 파이썬 표준 라이브러리 소스를 이어 붙인 텍스트, 난수 1MB, 이 블로그에 올린 WebP 스크린샷 하나를 각각 압축했다.

```bash
cat $P/os.py $P/argparse.py $P/typing.py $P/subprocess.py $P/pathlib.py > src.txt
gzip -c src.txt > src.gz
head -c 1000000 /dev/urandom > random.bin; gzip -c random.bin > random.gz
gzip -c img.webp > img.webp.gz
wc -c src.txt src.gz random.bin random.gz img.webp img.webp.gz
```

```
 398351 src.txt
  94515 src.gz
1000000 random.bin
1000184 random.gz
  36880 img.webp
  35741 img.webp.gz
```

| 파일 | 원본 | 압축 후 | 변화 |
|---|---|---|---|
| 소스 코드 텍스트 | 398,351 B | 94,515 B | 약 76% 감소 |
| 난수 1MB | 1,000,000 B | 1,000,184 B | **184 B 증가** |
| WebP 이미지 | 36,880 B | 35,741 B | 약 3% 감소 |

텍스트는 `import`, `def`, 들여쓰기처럼 같은 문자열이 계속 나와서 크게 줄었다. 난수에는 반복이 없어서 줄지 않았고, 압축 형식의 머리말(헤더)만큼 오히려 커졌다. WebP는 이미 압축된 파일이라 3%만 줄었다.

## 두 번 압축하면 더 작아질까

한 번 압축한 `src.gz`를 다시 압축해 봤다.

```bash
gzip -c src.gz > src.gz.gz
wc -c src.gz src.gz.gz
```

```
 94515 src.gz
 94555 src.gz.gz
```

94,515 B가 94,555 B로 **40 B 늘었다.** 첫 압축이 반복을 거의 다 걷어내서 두 번째에는 줄일 게 없다. 어떤 압축이든 모든 입력을 줄일 수는 없다. 줄어드는 입력이 있으면 반드시 안 줄어드는(또는 커지는) 입력도 있어야 하기 때문이다.

## ZIP 안에서도 같다

파이썬 `zipfile`에 DEFLATE로 두 파일을 넣어 봤다.

```python
z = zipfile.ZipFile('t.zip', 'w', zipfile.ZIP_DEFLATED)
z.write('src.txt'); z.write('random.bin')
```

```
src.txt 398351 94566
random.bin 1000000 1000310
```

앞이 원본, 뒤가 ZIP 안에 저장된 크기다. 난수 파일은 310 B 커졌다. 압축 도구에 따라 이럴 때 압축을 포기하고 원본을 그대로 담는 경우도 있다. DEFLATE 규격([RFC 1951](https://www.rfc-editor.org/rfc/rfc1951))에도 압축하지 않은 블록 형식이 따로 있다. 이 샌드박스의 파이썬 `zipfile`은 그렇게 하지 않고 그대로 압축해서 조금 커졌다.

## 확인하는 방법

- **종류로 판단한다:** 문서·텍스트·로그·소스 코드는 잘 줄고, JPG·PNG·WebP·MP3·MP4·이미 만든 ZIP은 거의 안 줄어든다.
- **직접 재 본다:** `gzip -c 파일 | wc -c`로 압축 후 크기를 바로 볼 수 있다. 원본과 비슷하면 압축할 이유가 없다.
- **ZIP을 쓰는 이유는 따로 있다:** 용량이 안 줄어도 여러 파일을 하나로 묶어 보내기에는 여전히 편하다.
