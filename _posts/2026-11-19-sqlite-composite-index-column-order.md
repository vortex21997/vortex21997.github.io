---
title: "(user_id, status) 복합 인덱스가 status만 찾을 땐 SCAN이 되는 이유: 컬럼 순서"
description: "SQLite에서 (user_id, status) 인덱스는 user_id 조건이 있을 때만 SEARCH가 되고 status 단독 조건은 SCAN orders로 떨어집니다. EXPLAIN QUERY PLAN 출력으로 앞 컬럼부터만 쓰이는 규칙과 순서를 바꿨을 때의 차이를 확인했습니다."
date: 2026-11-19 20:00:00 +0900
categories: [전산학, 데이터베이스]
tags: [sqlite, explain-query-plan, 복합-인덱스]
---

`(user_id, status)` 복합 인덱스는 **앞 컬럼 `user_id`부터 차례로** 쓰인다. `status` 조건만 있는 쿼리는 이 인덱스를 못 써서 `SCAN orders`가 나온다. 컬럼 순서가 곧 인덱스의 정렬 순서이기 때문이다. 직접 돌려 확인했다.

> 환경: Python 3 `sqlite3` 모듈, SQLite 3.45.1, 샌드박스(메모리 DB). `orders` 20만 행(user_id 0~999, status 4종류 무작위). 계획 문구는 버전마다 다를 수 있다.
{: .prompt-info }

```python
c.execute('create table orders(id integer primary key, user_id int, status text, amount int)')
c.execute('create index idx_us on orders(user_id,status)')
```

## 실행 결과

```
select * from orders where user_id=7 and status='paid'
   SEARCH orders USING INDEX idx_us (user_id=? AND status=?)
select * from orders where user_id=7
   SEARCH orders USING INDEX idx_us (user_id=?)
select * from orders where status='paid'
   SCAN orders
select * from orders where status='paid' and amount>990
   SCAN orders
```

- 두 컬럼 조건 → 인덱스 두 컬럼 모두 사용.
- 앞 컬럼만 → 사용. 괄호 안에 `user_id=?`만 찍힌다.
- **뒤 컬럼만 → `SCAN`.** 인덱스는 user_id로 먼저 정렬돼 있어서 status가 같은 항목이 인덱스 곳곳에 흩어져 있다.

판별법은 계획 끝의 괄호다. `(user_id=? AND status=?)`처럼 인덱스 컬럼이 몇 개 찍혔는지가 실제로 쓰인 앞부분이다. `SEARCH`가 떠도 괄호에 첫 컬럼만 있으면 나머지 조건은 행을 읽은 뒤 걸러진다.

## 순서를 바꾸면

`status`가 앞인 인덱스를 추가하고 범위 조건을 줬다.

```
create index idx_su on orders(status,user_id)
select * from orders where status='paid' and user_id>990
   SEARCH orders USING INDEX idx_su (status=? AND user_id>?)
```

등호 조건 컬럼이 앞, 범위 조건(`>`) 컬럼이 뒤면 둘 다 쓰인다. 반대로 범위 컬럼이 앞이면 그 뒤 컬럼은 좁히는 데 못 쓰인다(이 글에서는 실행하지 않았다).

## 인덱스만으로 답이 나올 때

선택 컬럼이 모두 인덱스에 있으면 테이블을 읽지 않는다.

```
select user_id,status from orders where user_id=7
   SEARCH orders USING COVERING INDEX idx_us (user_id=?)
```

`COVERING INDEX`가 그 표시다.

## 정리

- 복합 인덱스는 앞 컬럼부터만 쓰인다. 자주 쓰는 단독 조건 컬럼을 앞에 둔다.
- 뒤 컬럼 단독 조건이 필요하면 그 컬럼이 앞인 인덱스를 따로 만든다.
- 확인은 `EXPLAIN QUERY PLAN`의 괄호 안 컬럼 수.

같은 `SCAN`이 다른 이유로 나오는 경우(`LIKE`, 함수 적용)는 [인덱스를 만들었는데 EXPLAIN QUERY PLAN에 SCAN users가 뜰 때]({% post_url 2026-10-31-sqlite-index-not-used-like %})에 있다.

근거: [SQLite Query Planner](https://www.sqlite.org/queryplanner.html), [EXPLAIN QUERY PLAN](https://www.sqlite.org/eqp.html).
