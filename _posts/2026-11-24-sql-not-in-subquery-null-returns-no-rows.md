---
title: "NOT IN 서브쿼리가 결과를 0건으로 돌려줄 때: 목록에 NULL 한 개가 섞여 있다"
description: "WHERE id NOT IN (SELECT ...)가 빈 결과를 내면 서브쿼리 결과에 NULL이 하나 들어 있는 경우가 많다. SQLite에서 직접 돌려 NOT IN이 NULL이 되는 이유와 NOT EXISTS·IS NOT NULL로 푸는 방법을 확인했다."
date: 2026-11-24 20:00:00 +0900
categories: [전산학, 데이터베이스]
tags: [sqlite, null, not-in]
---

**`NOT IN (서브쿼리)`가 0건을 돌려주면, 서브쿼리 결과에 `NULL`이 한 개 섞여 있는지 먼저 본다.** 오른쪽 목록에 `NULL`이 있고 왼쪽 값이 목록에 없으면 `NOT IN`의 결과는 참이 아니라 `NULL`이고, `WHERE`는 `NULL`인 행을 버린다. 에러도 경고도 없이 빈 결과만 나온다.

> 환경: Python 3.12 `sqlite3` 모듈, SQLite 3.45.1 (샌드박스, 인메모리 DB). 2026-11 기준.
{: .prompt-info }

## 재현

사용자 3명과 차단 목록. 차단 목록의 `user_id`에 `NULL` 행이 하나 있다.

```python
import sqlite3
c = sqlite3.connect(":memory:")
c.executescript("""
create table users(id integer primary key, name text);
create table blocked(user_id integer);
insert into users values (1,'a'),(2,'b'),(3,'c');
insert into blocked values (1),(NULL);
""")
q = lambda s: print(s, '->', c.execute(s).fetchall())
q("select id from users where id not in (select user_id from blocked)")
```

실제 출력:

```text
select id from users where id not in (select user_id from blocked) -> []
```

차단되지 않은 2, 3이 나와야 할 것 같지만 빈 목록이다. 같은 데이터에서 `IN`은 정상으로 보인다.

```text
select id from users where id in (select user_id from blocked) -> [(1,)]
```

그래서 "서브쿼리는 맞는데 `NOT`만 붙이면 사라진다"는 모양이 된다.

## 왜 그런가

SQL의 `NULL`은 "값 없음"이 아니라 "알 수 없음"이다. `2 NOT IN (1, NULL)`은 `2 <> 1 AND 2 <> NULL`로 풀리고, `2 <> NULL`은 거짓이 아니라 알 수 없음이므로 전체가 알 수 없음이 된다. `WHERE`는 참인 행만 남긴다.

```text
select 2 not in (1,NULL), 1 not in (1,NULL), 2 in (1,NULL), NULL = NULL, NULL is NULL
-> [(None, 0, None, None, 1)]
```

- `2 NOT IN (1, NULL)` → `NULL` (파이썬에서는 `None`). 행이 사라진다.
- `1 NOT IN (1, NULL)` → `0` (거짓). 찾았으니 확실히 거짓이다.
- `NULL = NULL`도 `NULL`이다. `NULL`끼리 비교하려면 `IS NULL`을 쓴다.

[SQLite 공식 문서의 IN/NOT IN 표](https://www.sqlite.org/lang_expr.html#the_in_and_not_in_operators)도 같다. 왼쪽이 `NULL`이 아니고, 오른쪽에 `NULL`이 있고, 왼쪽 값을 못 찾으면 `IN`과 `NOT IN` 둘 다 `NULL`이다. 오른쪽이 빈 집합일 때만 `NOT IN`이 항상 참이다.

## 판별법

증상이 같아 보이는 두 경우를 이렇게 가른다.

1. **서브쿼리에 NULL이 있나**: `select count(*) from blocked where user_id is null`이 1 이상이면 이 글의 원인이다.
2. **서브쿼리가 비었나**: 비어 있으면 `NOT IN`은 모든 행을 돌려준다. 0건이 아니라 전부 나온다.

```text
select id from users where id not in (select user_id from blocked where 0) -> [(1,), (2,), (3,)]
```

즉 "0건"이면 비어서가 아니라 `NULL`이 섞여서다. 서브쿼리를 단독으로 실행해 값 목록을 눈으로 보는 것이 가장 빠르다.

## 해결

**① 서브쿼리에서 NULL을 걸러낸다.**

```text
select id from users where id not in (select user_id from blocked where user_id is not null)
-> [(2,), (3,)]
```

**② `NOT EXISTS`로 바꾼다.** 비교 결과가 `NULL`이어도 `EXISTS`는 행이 있는지만 보므로 `NULL`에 흔들리지 않는다.

```text
select id from users u where not exists (select 1 from blocked b where b.user_id = u.id)
-> [(2,), (3,)]
```

①은 지금 데이터에서만 안전하고, 나중에 다른 컬럼이 `NULL`을 낼 수 있는 쿼리로 바뀌면 다시 깨진다. 컬럼이 `NULL`을 허용하는 한 `NOT EXISTS`가 의도를 더 직접 표현한다. 두 방식의 실행 속도 차이는 이 글에서 재지 않았다.

> 왼쪽 값이 `NULL`인 행도 `NOT IN`에서 사라진다(위 문서 표의 마지막 줄). `users.id`가 `NULL`을 가질 수 있다면 그 행은 결과에서 빠진다는 뜻이다.
{: .prompt-warning }
