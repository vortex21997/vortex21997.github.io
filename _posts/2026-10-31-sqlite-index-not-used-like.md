---
title: "인덱스를 만들었는데 EXPLAIN QUERY PLAN에 SCAN users가 뜰 때"
description: "SQLite에서 email에 인덱스를 걸어도 LIKE 'user500%'와 lower(email) = ... 는 전체 SCAN이 됩니다. 계획 출력으로 SCAN과 SEARCH를 가르고, 인덱스를 타게 만드는 세 가지 방법을 실행 결과로 확인했습니다."
date: 2026-10-31 20:00:00 +0900
categories: [전산학, 데이터베이스]
tags: [sqlite, explain-query-plan, 인덱스]
---

인덱스를 만들었는데도 `EXPLAIN QUERY PLAN`에 `SCAN users`가 나온다면, 쿼리 모양이 인덱스의 **정렬 기준과 맞지 않는 것**이다. `SEARCH ... USING INDEX`가 나와야 인덱스를 쓴 것이고, `SCAN`은 테이블 전체를 훑는다는 뜻이다. 아래는 SQLite로 직접 돌려 본 결과다.

> 환경: Python 3 `sqlite3` 모듈, SQLite 3.45.1, 샌드박스(메모리 DB). 행 10만 개. 계획 문구는 SQLite 버전마다 조금 다를 수 있다.
{: .prompt-info }

## 준비

```python
import sqlite3
c = sqlite3.connect(":memory:")
c.execute("create table users(id integer primary key, email text, name text)")
c.executemany("insert into users(email,name) values(?,?)",
              [(f"user{i}@example.com", f"n{i}") for i in range(100000)])
c.execute("create index idx_email on users(email)")

def p(q):
    print("SQL>", q)
    for r in c.execute("explain query plan " + q): print("   ", r[3])
```

## 판별: 어느 쿼리가 인덱스를 타나

```text
SQL> select * from users where email = 'user500@example.com'
    SEARCH users USING INDEX idx_email (email=?)
SQL> select * from users where email like 'user500%'
    SCAN users
SQL> select * from users where email like '%500@example.com'
    SCAN users
SQL> select * from users where lower(email) = 'user500@example.com'
    SCAN users
```

- 같다(`=`) 비교만 `SEARCH`가 나왔다.
- **접두사 `LIKE 'user500%'`도 `SCAN`**이다. 앞이 고정된 패턴이라 인덱스를 탈 것 같지만 안 탔다.
- 앞이 `%`인 패턴은 어떤 인덱스로도 못 탄다. 정렬된 목록에서 "끝이 같은 것"은 찾을 수 없다.
- 컬럼에 함수를 씌우면(`lower(email)`) 인덱스는 `email` 값 기준으로 정렬돼 있지 `lower(email)` 기준이 아니라서 못 쓴다.

## 접두사 LIKE가 SCAN인 이유

SQLite 문서의 [LIKE 최적화 조건](https://www.sqlite.org/optoverview.html#the_like_optimization)에 따르면, 좌변 컬럼이 **LIKE는 NOCASE 정렬 규칙으로 인덱싱**돼 있어야 한다(기본 모드인 `case_sensitive_like` 꺼짐 기준). LIKE는 기본이 대소문자를 구분하지 않는데, 위 인덱스는 기본 BINARY 정렬이라 순서가 맞지 않는다. 같은 문서에서 GLOB은 BINARY 인덱스여야 한다고 한다.

NOCASE 인덱스를 만들어 확인했다.

```python
c.execute("create index idx_nocase on users(email collate nocase)")
p("select * from users where email like 'user500%'")
```

```text
    SEARCH users USING INDEX idx_nocase (email>? AND email<?)
```

`email>? AND email<?`는 문서에서 말하는, LIKE를 범위 조건으로 바꾼 가상 항이다.

## 인덱스를 타게 만드는 방법 세 가지

**1. 컬럼 식 그대로 인덱스를 건다.** 함수 쓰는 쿼리는 같은 식으로 인덱스를 만든다.

```python
c.execute("create index idx_lower on users(lower(email))")
p("select * from users where lower(email) = 'user500@example.com'")
```
```text
    SEARCH users USING INDEX idx_lower (<expr>=?)
```

**2. 대소문자 구분이 필요 없는 접두사 검색이면 NOCASE 인덱스를 둔다.** 위 `idx_nocase` 예.

**3. 대소문자를 구분해도 되면 `GLOB`이나 범위 조건을 쓴다.** 기본 BINARY 인덱스(`idx_email`만 있는 상태)에서:

```text
select * from users where email glob 'user500*'
   SEARCH users USING COVERING INDEX idx_email (email>? AND email<?)
select * from users where email >= 'user500' and email < 'user501'
   SEARCH users USING COVERING INDEX idx_email (email>? AND email<?)
```

(`COVERING`은 이 확인용 표에 컬럼이 `id`와 `email`뿐이라 인덱스만으로 답이 나온다는 표시다. 위 표와 컬럼 구성이 달라 문구가 다르다.)

## 정리

계획 출력에서 `SCAN`이 나오면 먼저 두 가지를 본다. 컬럼에 함수가 씌워졌는가, LIKE라면 인덱스의 정렬 규칙(BINARY/NOCASE)이 맞는가. 수치(시간)는 재지 않았고, 이 글이 확인한 것은 **계획이 SCAN이냐 SEARCH냐**까지다.
