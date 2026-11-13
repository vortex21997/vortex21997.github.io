---
title: "리스트의 in은 데이터가 늘수록 느려지는데 set의 in은 왜 안 느려질까: 해시로 직접 재기"
description: "원소 100만 개에서 x in list는 4.4ms, x in set은 0.027us. 해시 값이 같은 객체를 일부러 만들어 set의 in도 느려지는 모습까지 직접 재서 O(1)의 조건을 확인했다."
date: 2026-11-13 20:00:00 +0900
categories: [전산학, 자료구조·알고리즘]
tags: [python, set, 해시테이블]
---

`if x in items:`가 반복문 안에 있으면 데이터가 늘수록 코드가 눈에 띄게 느려진다. 결론부터: **리스트의 `in`은 앞에서부터 하나씩 비교하므로 길이에 비례하고, set의 `in`은 값을 해시해 곧바로 칸을 찾아가므로 길이와 거의 무관하다.** 단, 이 "거의"는 해시 값이 잘 흩어진다는 조건 위에서만 성립한다.

## 직접 재기

없는 값(`-1`)을 찾는 경우로 쟀다. 리스트는 끝까지 다 봐야 하는 최악의 경우다.

```python
import timeit
for n in (1_000, 10_000, 100_000, 1_000_000):
    L = list(range(n)); S = set(L); x = -1
    tl = min(timeit.repeat(lambda: x in L, number=20, repeat=5)) / 20
    ts = min(timeit.repeat(lambda: x in S, number=20000, repeat=5)) / 20000
    print(f"{n:>9,} list {tl*1e6:10.2f} us   set {ts*1e6:7.3f} us")
```

```text
    1,000 list       4.79 us   set   0.043 us
   10,000 list      48.12 us   set   0.036 us
  100,000 list     465.83 us   set   0.031 us
1,000,000 list    4425.67 us   set   0.027 us
```

환경: Python 3.11.18, Linux 6.18 x86_64, Xeon 2.10GHz 4코어 샌드박스. 절대값은 기계마다 다르다. 볼 것은 모양이다.

- 리스트: n이 10배가 될 때마다 시간도 약 10배. 길이에 비례(O(n))한다.
- set: 1천 개든 100만 개든 0.03~0.04us 안팎으로 일정하다.

대가도 있다. 같은 정수 100만 개를 담은 컨테이너의 크기는 다음과 같다.

```python
import sys
print(sys.getsizeof(list(range(10**6))), sys.getsizeof(set(range(10**6))))
```

```text
8000056 33554648
```

리스트 약 8MB, set 약 33.5MB다. (리스트는 정수 객체 자체를 빼고 포인터 배열만 센 값이고, set은 해시 테이블 칸이 더 많이 필요하다.) 속도를 메모리와 바꾼 셈이다.

## 왜 일정한가: 해시로 칸을 바로 찾는다

set은 원소의 `hash()` 값으로 "어느 칸에 있을지"를 계산한다. 그 칸만 보면 되므로 다른 원소는 볼 필요가 없다.

```python
print(hash(1), hash(2), hash("a") == hash("a"))
```

```text
1 2 True
```

[공식 문서](https://docs.python.org/3/library/stdtypes.html#set-types-set-frozenset)(2026-11 확인)는 set을 *an unordered collection of distinct hashable objects*라 정의하고, 대표 용도로 *membership testing*을 든다. 이 구조가 동작하려면 [데이터 모델 문서](https://docs.python.org/3/reference/datamodel.html#object.__hash__)의 규칙이 필요하다: *objects which compare equal have the same hash value*. 같다고 판정되는 객체는 해시가 같아야 같은 칸을 찾아간다.

## 조건이 깨지면: 해시가 전부 같을 때

"해시가 잘 흩어진다"가 전제라는 걸 확인하려고, `__hash__`가 항상 1을 돌려주는 클래스를 만들었다. 문법상 규칙(같으면 해시도 같다)은 지키지만 모든 원소가 같은 칸으로 몰린다.

```python
class K:
    def __init__(s, v): s.v = v
    def __hash__(s): return 1
    def __eq__(s, o): return s.v == o.v

for n in (100, 200, 400, 800):
    S = {K(i) for i in range(n)}; k = K(-1)
    t = min(timeit.repeat(lambda: k in S, number=200, repeat=5)) / 200
    print(n, f"{t*1e6:.2f} us  (all hash=1)")
```

```text
100 3.77 us  (all hash=1)
200 8.22 us  (all hash=1)
400 16.07 us  (all hash=1)
800 35.78 us  (all hash=1)
```

n이 2배가 될 때마다 시간도 2배다. set인데도 리스트처럼 길이에 비례한다. 같은 칸에 몰린 원소를 하나씩 `__eq__`로 비교해야 하기 때문이다. 정수나 문자열 같은 내장 타입은 해시가 잘 흩어지게 만들어져 있어 보통 겪지 않는다. 직접 `__hash__`를 정의한 클래스에서 상수나 한두 필드만 쓰면 이 꼴이 된다.

## 판별법: 내 코드가 이 문제인가

1. 반복문 안의 `x in some_list`를 찾는다. 같은 리스트에 `in`을 여러 번 하면 후보다.
2. 입력을 10배로 키웠을 때 시간이 10배 이상이면 리스트 탐색이 원인일 수 있다.
3. 그 리스트를 한 번만 `set(...)`으로 바꾸고 `in`을 set에 하면 된다. 변환 비용은 한 번이므로, 검사를 여러 번 할 때만 이득이다.
4. set으로 바꿨는데도 느리면, 원소가 직접 만든 클래스인지 보고 `__hash__`가 값을 잘 흩는지 본다.

주의: 원소를 set에 넣으려면 해시 가능해야 한다. 리스트나 딕셔너리는 담을 수 없고, 순서가 필요하거나 중복을 허용해야 하면 set이 맞지 않다. 원소가 몇십 개 이하면 차이는 마이크로초 단위라 굳이 바꿀 이유가 없다.

이 글의 측정은 CPython 3.11 한 환경의 값이며, 다른 버전과 구현에서 비율은 달라질 수 있다.
