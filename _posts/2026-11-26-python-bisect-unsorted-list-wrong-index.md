---
title: "bisect_left가 리스트에 있는 값을 못 찾을 때: 정렬 안 된 리스트에는 에러 없이 틀린 인덱스를 돌려준다"
description: "bisect는 정렬되지 않은 리스트에도 예외 없이 인덱스를 돌려준다. 10개짜리 무작위 리스트에서 값 10개 중 8개를 못 찾았고, 같은 값을 정렬 후에는 찾았다. 비교 횟수 20번(100만 개)과 함께 확인했다."
date: 2026-11-26 20:00:00 +0900
categories: [전산학, 자료구조·알고리즘]
tags: [bisect, 이진 탐색, python]
---

**`bisect.bisect_left(a, x)`는 `a`가 정렬돼 있다고 믿고 움직인다.** 정렬이 안 된 리스트를 넘겨도 예외는 없고, 그럴듯한 인덱스를 돌려준다. 그래서 `a[i] == x`를 확인하지 않으면 "리스트에 분명히 있는 값이 없다고 나오는" 버그가 조용히 생긴다. 판별법은 하나다. **같은 값을 `sorted()` 한 사본에서 찾아 보고, 거기서는 찾아지면 원인은 정렬이다.**

> 환경: Linux x86_64 샌드박스, Python 3.11.18. 아래 출력은 모두 이 환경에서 직접 돌린 결과다. 시간은 환경마다 다르다.
{: .prompt-info }

## 정렬 안 된 리스트에서 생기는 일

```python
import bisect, random
random.seed(1)
u = random.sample(range(100), 10)
print(u)            # [17, 72, 97, 8, 32, 15, 63, 57, 60, 83]
x = u[7]            # 57. 리스트에 있는 값이다
i = bisect.bisect_left(u, x)
print(i, u[i])      # 6 63   ← 57이 아니다
print(x in u)       # True
```

`bisect_left`는 6을 돌려줬지만 `u[6]`은 63이다. 에러는 없다. 같은 값을 정렬한 사본에서 찾으면 맞는다.

```python
s = sorted(u)
i = bisect.bisect_left(s, x)
print(i, s[i] == x)   # 4 True
```

리스트에 있는 값 10개를 전부 `bisect_left`로 찾아 인덱스의 값이 같은지 세어 보니 **8개를 못 찾았다.** 가운데 원소와 비교해 왼쪽/오른쪽을 버리는 알고리즘이라, 순서가 어긋나 있으면 엉뚱한 쪽을 버린다.

공식 문서는 반환값을 "정렬 순서를 유지하며 삽입할 위치"로 설명하고, 이 값이 `list.insert()`에 쓸 만한 것은 "assuming that *a* is already sorted"일 때라고 쓴다. 정렬이 안 된 입력에서 무슨 일이 생기는지는 문서에 적혀 있지 않다. 위 출력은 이 환경에서 관찰한 동작이다.
([bisect — Array bisection algorithm](https://docs.python.org/3/library/bisect.html))

## 찾았는지는 항상 되짚어 확인한다

`bisect_left`가 돌려주는 건 "찾은 위치"가 아니라 **삽입 위치**다. 값이 없어도 인덱스가 나오고, 끝을 넘을 수도 있다. 그래서 다음 두 줄이 한 세트다.

```python
i = bisect.bisect_left(s, x)
found = i < len(s) and s[i] == x
```

문서는 `ip`가 배열을 `all(elem < x for elem in a[lo:ip])`와 `all(elem >= x for elem in a[ip:hi])`로 나눈다고 보장한다. 같은 값이 여럿이면 `bisect_left`는 그중 가장 왼쪽을 가리킨다.

## 정렬을 지켜 주면 얼마나 이득인가

비교 연산(`__lt__`, `__eq__`)이 불릴 때마다 센 횟수다. 원소가 `i*2`인 정렬된 리스트에서 뒤쪽 값을 찾았다.

```text
bisect N= 1000     비교 10
선형   N= 1000     비교 500
bisect N= 1000000  비교 20
선형   N= 1000000  비교 500000
```

100만 개에서 20번이다. 원소가 두 배가 될 때마다 비교가 한 번 늘 뿐이다. 100만 개에서 마지막 부근 값을 찾는 시간은 다음과 같았다.

```text
선형 in 8.64 ms
bisect  0.25 us
```

단, 이건 이미 정렬된 리스트가 있을 때의 비교다. 한 번 찾으려고 매번 정렬하면 `sorted()`가 O(n log n)이라 오히려 손해다. 여러 번 찾을 때, 또는 `insort`로 정렬을 유지하며 넣을 때 쓴다. 문서도 `insort`는 삽입 단계가 O(n)이라 전체가 O(n)이라고 쓴다.

## 정리

- `bisect`는 정렬 여부를 검사하지 않는다. 틀린 인덱스가 에러 없이 나온다.
- 찾았는지는 `i < len(a) and a[i] == x`로 확인한다.
- 의심되면 `sorted()` 사본에서 같은 값을 찾아 비교한다.
- 값 하나 찾으려고 매번 정렬하지 않는다. 같은 데이터에서 여러 번 찾을 때만 이득이다.

리스트의 `in`이 왜 느리고 `set`은 왜 안 느린지는 [리스트의 in과 set의 in](/posts/python-in-list-vs-set-hash/)에서 다뤘다.
