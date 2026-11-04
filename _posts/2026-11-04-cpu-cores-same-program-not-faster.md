---
title: "CPU 코어가 4개인데 프로그램은 왜 4배 빨라지지 않나"
description: "코어 수는 동시에 돌릴 수 있는 일의 수일 뿐입니다. 같은 계산 8개를 프로세스 1·2·4·8개로 나눠 돌려 코어 4개에서 속도가 어디까지 오르는지 쟀습니다."
date: 2026-11-04 13:00:00 +0900
categories: [컴퓨터 기초, 하드웨어]
tags: [cpu, 코어, 병렬 처리]
---

**코어는 "한 번에 할 수 있는 일의 개수"이지 "일 하나의 속도"가 아닙니다.** 프로그램이 일을 여러 조각으로 나눠 놓지 않았다면 코어가 4개든 16개든 그중 하나만 일합니다. 나눠 놓았더라도 코어 수를 넘는 조각은 빨라지지 않습니다. 아래는 같은 계산을 나눠 돌려 직접 잰 결과입니다.

(용어: **코어**는 CPU 안에서 실제로 계산을 하는 단위입니다. 코어가 4개면 서로 다른 계산 4개를 동시에 진행할 수 있습니다.)

## 측정 환경

이 글의 수치는 클라우드 샌드박스(가상 머신) 한 대에서 잰 값입니다. 다른 컴퓨터에서는 달라집니다.

```
$ lscpu | grep -E 'Model name|^CPU\(s\)|Thread|Core'
CPU(s):                                  4
Model name:                              Intel(R) Xeon(R) Processor @ 2.10GHz
Thread(s) per core:                      1
Core(s) per socket:                      4
```

CPU 사양은 `lscpu`로 봅니다([man 페이지](https://man7.org/linux/man-pages/man1/lscpu.1.html)). 코어 4개, 파이썬 3.11.18, 메모리 약 16GB입니다.

## 실험: 같은 계산 8개를 나눠 돌리기

"1부터 500만까지 제곱을 더하는" 계산 8개를 만들고, 한꺼번에 일하는 프로세스(실행 중인 프로그램의 단위) 수를 1·2·4·8개로 바꿔 전체가 끝나는 시간을 쟀습니다. 파이썬 표준 라이브러리 [`multiprocessing`](https://docs.python.org/3/library/multiprocessing.html)의 `Pool`을 썼습니다.

```python
import sys, time, multiprocessing as mp

def work(n):
    s = 0
    for i in range(n):
        s += i * i
    return s

if __name__ == "__main__":
    N = 5_000_000
    TOTAL = 8
    print("python", sys.version.split()[0], "cpus", mp.cpu_count())
    base = None
    for p in (1, 2, 4, 8):
        t = time.perf_counter()
        with mp.Pool(p) as pool:
            pool.map(work, [N] * TOTAL, chunksize=1)
        dt = time.perf_counter() - t
        base = base or dt
        print(f"processes={p} jobs={TOTAL} time={dt:.2f}s speedup={base/dt:.2f}x", flush=True)
```

두 번 실행한 실제 출력입니다.

```
python 3.11.18 cpus 4
processes=1 jobs=8 time=1.44s speedup=1.00x
processes=2 jobs=8 time=0.79s speedup=1.82x
processes=4 jobs=8 time=0.44s speedup=3.24x
processes=8 jobs=8 time=0.49s speedup=2.97x

python 3.11.18 cpus 4
processes=1 jobs=8 time=1.40s speedup=1.00x
processes=2 jobs=8 time=0.69s speedup=2.04x
processes=4 jobs=8 time=0.37s speedup=3.78x
processes=8 jobs=8 time=0.40s speedup=3.54x
```

## 읽는 법

- **프로세스 1개 → 4개: 약 3.2~3.8배.** 코어 수만큼 거의 비례해 빨라졌습니다. 이 계산은 조각끼리 서로 기다릴 일이 없어서 가장 잘 나오는 경우입니다.
- **4배가 아니라 4배에 못 미칩니다.** 프로세스를 띄우고 결과를 모으는 데 시간이 들고, 같은 기계에서 다른 프로그램도 돌기 때문입니다.
- **프로세스 8개는 4개보다 빨라지지 않았습니다.** 코어가 4개라 동시에 진행되는 건 최대 4개이고, 나머지는 차례를 기다립니다. 두 번 모두 4개와 비슷하거나 약간 느렸습니다.
- **프로세스 1개일 때는 코어 4개 중 1개만 일했습니다.** 위 코드를 `Pool(1)`로 돌린 것이 "나누지 않은 프로그램"에 해당하고, 나머지 3개는 놀았습니다.

## 그래서 일상에서는

- 작업 관리자나 활동 모니터에서 CPU 사용률이 25% 근처에서 멈춘 채 프로그램이 느리다면, 4코어 컴퓨터에서 프로그램이 코어 하나만 쓰고 있을 가능성이 있습니다. (4코어 기준이고, 확정이 아니라 단서입니다.)
- 코어가 많은 컴퓨터가 항상 빠른 것은 아닙니다. 여러 프로그램을 동시에 돌리거나, 일을 나눌 줄 아는 프로그램(영상 인코딩, 빌드 등)을 쓸 때 차이가 납니다.
- 일을 나눌 수 있는지는 프로그램이 정합니다. 앞 단계 결과가 있어야 다음 단계를 할 수 있는 계산은 코어를 더해도 그대로입니다.

> 이 실험은 서로 독립적인 계산이라 가장 유리한 경우입니다. 실제 프로그램의 속도 향상은 이보다 작게 나오는 것이 보통이지만, 이 글에서는 그 비율을 잰 적이 없으므로 수치를 일반화하지 않습니다.
{: .prompt-info }
