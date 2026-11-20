---
title: "점수가 같은 사람의 순서가 안 바뀌는 이유: 파이썬 sorted는 안정 정렬이다"
description: "sorted(key=...)로 정렬하면 키가 같은 항목은 입력 순서가 유지된다. reverse=True에서도 같은 이유와, 이 성질로 정렬을 두 번 해서 다중 키 정렬을 만드는 법을 직접 돌려 확인했다."
date: 2026-11-20 20:00:00 +0900
categories: [전산학, 자료구조·알고리즘]
tags: [안정 정렬, sorted, timsort]
---

**점수가 같은 항목끼리는 정렬 전의 순서가 그대로 남는다.** 파이썬의 `sorted()`와 `list.sort()`는 안정 정렬(stable sort)이 보장되기 때문이다. 안정 정렬이란 키가 같은 레코드의 원래 순서를 바꾸지 않는 정렬을 말한다. [공식 Sorting HOWTO](https://docs.python.org/3/howto/sorting.html)는 이렇게 적는다: "Sorts are guaranteed to be stable. That means that when multiple records have the same key, their original order is preserved."

> 실행 환경: Python 3.11.18, Linux. 문서는 2026-11에 읽었다.
{: .prompt-info }

## 같은 점수끼리 순서가 유지된다

```python
rows=[("민수",90),("지연",85),("철수",90),("영희",85),("보라",90)]
print(sorted(rows,key=lambda r:r[1]))
print(sorted(rows,key=lambda r:r[1],reverse=True))
print(list(reversed(sorted(rows,key=lambda r:r[1]))))
```

```
[('지연', 85), ('영희', 85), ('민수', 90), ('철수', 90), ('보라', 90)]
[('민수', 90), ('철수', 90), ('보라', 90), ('지연', 85), ('영희', 85)]
[('보라', 90), ('철수', 90), ('민수', 90), ('영희', 85), ('지연', 85)]
```

- 오름차순에서 85점은 입력 순서대로 `지연, 영희`, 90점은 `민수, 철수, 보라`다.
- `reverse=True`에서도 90점이 `민수, 철수, 보라`로 **입력 순서 그대로**다. 문서도 "The reverse parameter still maintains sort stability"라고 적는다.
- 결과를 `reversed()`로 뒤집으면 동점끼리도 뒤집힌다(`보라, 철수, 민수`). 내림차순이 필요하면 뒤집지 말고 `reverse=True`를 쓴다.

## 정렬을 두 번 하면 다중 키 정렬이 된다

"점수 내림차순, 같으면 이름 오름차순"을 두 단계로 만들 수 있다. **덜 중요한 키로 먼저, 중요한 키로 나중에** 정렬한다.

```python
step1=sorted(rows,key=lambda r:r[0])
step2=sorted(step1,key=lambda r:r[1],reverse=True)
print(step1)
print(step2)
print(sorted(rows,key=lambda r:(-r[1],r[0]))==step2)
```

```
[('민수', 90), ('보라', 90), ('영희', 85), ('지연', 85), ('철수', 90)]
[('민수', 90), ('보라', 90), ('철수', 90), ('영희', 85), ('지연', 85)]
True
```

두 번째 정렬이 동점의 순서를 건드리지 않으니 첫 번째 정렬의 이름순이 살아남는다. 튜플 키 `(-r[1], r[0])` 한 번과 결과가 같다(`True`). 문서도 이 방식을 "complex sorts in multiple passes"로 소개한다. 숫자가 아니라 문자열 키를 내림차순으로 섞어야 할 때는 부호를 뒤집을 수 없으므로 이 방법이 쓸모 있다.

## 정리

- 동점의 순서는 입력 순서다. 정렬 전에 이미 원하는 순서였다면 그대로 유지된다.
- 안정성은 언어 사양이 아니라 [파이썬 문서가 보장](https://docs.python.org/3/howto/sorting.html)하는 동작이다. 다른 언어의 정렬 함수는 안정적이지 않을 수 있으니 해당 문서를 확인한다.
