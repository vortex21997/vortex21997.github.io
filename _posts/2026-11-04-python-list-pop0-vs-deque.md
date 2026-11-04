---
title: "큐를 list.pop(0)으로 만들면 왜 갑자기 느려질까: deque와 직접 재기"
description: "list.pop(0)으로 20만 개를 비우는 데 3.7초, deque.popleft()는 15ms. 맨 앞 원소를 빼는 비용이 길이에 비례하는 모습을 직접 측정하고 공식 문서로 확인했다."
date: 2026-11-04 20:00:00 +0900
categories: [전산학, 자료구조·알고리즘]
tags: [python, deque, 시간복잡도]
---

BFS나 작업 큐를 만들 때 `queue = [...]`에 `queue.pop(0)`을 쓰면 데이터가 작을 땐 멀쩡하다가 어느 순간 급격히 느려진다. 결론부터: **리스트는 맨 앞 원소를 빼면 나머지를 전부 한 칸씩 당기므로 한 번에 O(n)이고, 끝까지 비우면 O(n²)이다.** `collections.deque`의 `popleft()`는 양 끝 모두 O(1)이다.

## 공식 문서의 설명

[`collections.deque` 문서](https://docs.python.org/3/library/collections.html#collections.deque)(2026-11 확인)는 이렇게 말한다.

> Deques support thread-safe, memory efficient appends and pops from either side of the deque with approximately the same O(1) performance in either direction.
>
> Though list objects support similar operations, they are optimized for fast fixed-length operations and incur O(n) memory movement costs for `pop(0)` and `insert(0, v)` operations which change both the size and position of the underlying data representation.

## 직접 재기

원소 n개짜리 리스트와 deque를 맨 앞에서 하나씩 끝까지 뺀다.

```python
import time, collections
for n in (10_000, 100_000, 200_000):
    l = list(range(n)); t = time.perf_counter()
    while l: l.pop(0)
    a = time.perf_counter() - t
    d = collections.deque(range(n)); t = time.perf_counter()
    while d: d.popleft()
    b = time.perf_counter() - t
    print(f"n={n:>7}  list.pop(0)={a*1000:8.1f}ms  deque.popleft={b*1000:6.1f}ms")
```

```text
3.11.18 x86_64
n=  10000  list.pop(0)=     7.3ms  deque.popleft=   0.9ms
n= 100000  list.pop(0)=   936.7ms  deque.popleft=   4.6ms
n= 200000  list.pop(0)=  3711.5ms  deque.popleft=  15.5ms
```

환경: Python 3.11.18, x86_64 Xeon 2.10GHz 4코어, 메모리 16GB 샌드박스. 절대 시간은 기계마다 다르고, 봐야 할 것은 증가하는 모양이다.

- n이 10배(1만→10만)일 때 `list.pop(0)`은 약 128배, 2배(10만→20만)일 때 약 4배 늘었다. 길이의 제곱에 가깝게 늘어나는 O(n²) 모양이다.
- `deque.popleft()`는 n에 거의 비례한다(20만 개에 15ms). 한 번 뺄 때의 비용이 길이에 상관없다는 뜻이다.

## 판별법: 내 코드가 이 문제인가

증상은 "데이터가 늘수록 **갑자기** 느려진다"이다. 입력이 10배가 됐는데 시간이 10배가 아니라 100배쯤 늘었다면 의심한다.

1. 코드에서 `pop(0)` 또는 `insert(0, x)`가 반복문 안에 있는지 찾는다.
2. 입력 크기를 2배씩 키우며 시간을 잰다. 4배씩 늘면 O(n²) 꼴이다.

고치는 법은 한 줄이다.

```python
from collections import deque
queue = deque(items)
queue.popleft()
```

## 반대로 deque가 항상 낫지는 않다

같은 문서가 적었듯 deque는 가운데 접근이 O(n)이다(`Indexed access is O(1) at both ends but slows to O(n) in the middle`). 인덱스로 임의 접근을 많이 한다면 리스트가 맞다. 뒤에서만 넣고 빼는 스택은 `list.append()`/`pop()`으로 충분하다.

이 글의 측정은 CPython 3.11 한 환경의 값이며, 다른 구현이나 버전에서 비율은 달라질 수 있다.
