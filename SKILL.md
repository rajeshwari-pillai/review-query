---
name: query-review
description: This skill should be used when the user asks to "review queries", "audit queries", "check my queries", "find query issues", "optimize queries", "check for N+1", "review my database code", "check ORM queries", or mentions slow queries, query performance, or database bottlenecks. Works with all databases and ORMs.
version: 1.0.0
---

# Query Review — Universal DB Query Auditor

Audits database queries across all ORMs, raw SQL dialects, and NoSQL drivers. Detects correctness, performance, and safety issues.

## Step 1 — Detect Stack

Before reviewing, scan the target file(s) for imports and usage to identify:

**ORM detection (check imports):**
- `sqlalchemy` / `from sqlalchemy` → SQLAlchemy (Python)
- `from django.db` / `models.Model` → Django ORM
- `import prisma` / `@prisma/client` → Prisma
- `typeorm` / `@Entity` / `getRepository` → TypeORM
- `sequelize` / `DataTypes` → Sequelize
- `mongoose` / `Schema` / `model(` → Mongoose
- `gorm.io` / `db.Find` / `db.Where` → GORM (Go)
- `ActiveRecord` / `has_many` / `belongs_to` → ActiveRecord (Rails)
- `Hibernate` / `@Entity` / `EntityManager` → Hibernate (Java)

**Raw SQL detection:**
- String literals containing `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `JOIN`, `WHERE`
- `cursor.execute(`, `db.query(`, `conn.execute(`, `session.execute(`

**NoSQL detection:**
- `pymongo` / `MongoClient` / `.aggregate(` / `.find(` → MongoDB
- `redis` / `ioredis` / `SETNX` / `KEYS` / `MGET` → Redis
- `elasticsearch` / `_search` / `bool` query → Elasticsearch

---

## Step 1b — Dialect Detection

After detecting the ORM, identify the database dialect for dialect-specific rules:

**MySQL indicators**: `pymysql`, `mysqlclient`, `mysql+pymysql`, `SHOW TABLES`, `LIMIT ? OFFSET ?`, `AUTO_INCREMENT`, backtick identifiers
**PostgreSQL indicators**: `psycopg2`, `asyncpg`, `postgresql+psycopg2`, `$1` placeholders, `RETURNING`, `JSONB`, `CONCURRENTLY`, `ON CONFLICT`
**SQLite indicators**: `sqlite3`, `pysqlite`, `///path/to/db.sqlite`

**MySQL-specific checks:**
- `LIMIT` without `ORDER BY` — results are non-deterministic in MySQL (no guaranteed sort without explicit ORDER BY)
- `EXPLAIN FORMAT=JSON` available in MySQL 5.6+ — use for detailed plan
- `SELECT ... FOR UPDATE` requires `innodb_lock_wait_timeout` to be set, or it blocks indefinitely
- `GROUP BY` in MySQL 5.7 (ONLY_FULL_GROUP_BY mode off by default) may hide bugs that fail in strict mode

**PostgreSQL-specific checks:**
- `JSONB` queries without a GIN index (`@>`, `?`, `?|`) — full table scan on JSONB column
- `INSERT ... RETURNING` preferred over INSERT then SELECT — avoids a second round trip
- `SELECT FOR UPDATE` without `NOWAIT` or `SKIP LOCKED` — blocks silently in production
- `CREATE INDEX` without `CONCURRENTLY` — locks table during index build in Postgres
- Stale statistics: if `rows` estimate in EXPLAIN is far off actual, run `ANALYZE table_name`

## Step 2 — Universal Checks (apply to ALL stacks)

These checks apply regardless of database or ORM:

### U1 — N+1 Query Pattern
**Trigger**: A query or ORM call inside a loop (`for`, `while`, `map`, `forEach`, list comprehension).
**Risk**: 1 outer query + N inner queries = exponential DB load.
**Fix pattern**: Replace with a single query using JOIN, `IN (...)`, eager loading, or batch fetch.

```
# Bad
for user in users:
    orders = db.query(Order).filter_by(user_id=user.id).all()

# Good
user_ids = [u.id for u in users]
orders = db.query(Order).filter(Order.user_id.in_(user_ids)).all()
```

### U2 — Unbounded Query (No LIMIT)
**Trigger**: A SELECT / `.all()` / `.find()` with no `.limit()`, `.first()`, or `LIMIT` clause on a table that could grow.
**Risk**: Full table scan returned to memory — OOM or extreme latency at scale.
**Fix**: Always apply `.limit(n)` or paginate. Never trust that a table will stay small.

### U3 — SELECT * / Fetching All Columns
**Trigger**: `SELECT *`, `.all()` on a model with many columns, `.find({})` with no projection.
**Risk**: Transfers unused data over the wire, prevents index-only scans, breaks if schema changes.
**Fix**: Select only needed columns — `SELECT id, name`, `.only('id', 'name')`, `values('id', 'name')`.

### U4 — Query Inside a Serializer / Property / `__str__`
**Trigger**: DB call inside a model property, `__str__`, `to_dict`, or serializer field method.
**Risk**: Each access triggers a new query — invisible N+1, hard to trace.
**Fix**: Preload the data before serialization, pass it explicitly.

### U5 — Missing Index on Filtered / Joined Column
**Trigger**: `WHERE col = ?` or `JOIN ON col` where `col` has no index hint, no `db_index=True`, no `@Index`.
**Risk**: Full table scan on every query — acceptable at 1K rows, catastrophic at 1M+.
**Fix**: Add index. For composite filters, add a composite index in the right column order.

### U6 — Count Then Fetch Anti-Pattern
**Trigger**: `COUNT(*)` query immediately followed by a `SELECT` for the same rows.
**Risk**: Two round trips to DB when one suffices.
**Fix**: Use `SELECT SQL_CALC_FOUND_ROWS` (MySQL), `RETURNING`, or paginate with a single query.

### U9 — INSERT Then SELECT (Missing RETURNING)
**Trigger**: `INSERT` immediately followed by `SELECT` to retrieve the inserted row or its generated ID.
**Risk**: Two DB round trips; race condition if another process modifies the row between insert and select.
**Fix** (PostgreSQL): Use `RETURNING id` or `RETURNING *` in the INSERT.
**Fix** (MySQL): Use `cursor.lastrowid` or `session.execute(...).inserted_primary_key` — no second SELECT.

### U10 — Queries Inside Serializers / Properties
**Trigger**: DB call inside `to_dict()`, `__str__`, `@property`, a DRF serializer field, or a SQLAlchemy `@hybrid_property`.
**Risk**: Every access triggers a hidden query — creates invisible N+1 that doesn't appear in loop analysis.
**Fix**: Preload the data before serialization. Pass it as a parameter or use eager loading.

### U7 — No Query Timeout
**Trigger**: Long-running or potentially slow query with no timeout set at query or connection level.
**Risk**: One slow query blocks a DB connection until completion — cascading connection pool exhaustion.
**Fix**: Set `statement_timeout` (Postgres), `MAX_EXECUTION_TIME` (MySQL), or `.timeout()` in ORM.

### U8 — Fetching Full Object to Read One Field
**Trigger**: Load full model instance, then access only `obj.id` or `obj.name`.
**Risk**: Loads all columns, triggers lazy loads, wastes memory.
**Fix**: Use `.values('field')`, `scalar()`, or `SELECT specific_col`.

---

## Step 3 — ORM-Specific Checks

Load only the section matching the detected stack.

### SQLAlchemy
- `session.query(Model).all()` with no limit on potentially large tables
- Lazy relationship access inside a loop (`for order in user.orders:` — triggers N+1)
- Using `session` across threads without `scoped_session`
- `session.execute(text("raw sql"))` with f-string or % formatting — SQL injection risk
- Missing `session.close()` / not using `@with_session` decorator or context manager
- `.filter()` on unindexed column

### Django ORM
- `.all()` without `.filter()` — loads entire table
- Missing `select_related()` on ForeignKey access in loops
- Missing `prefetch_related()` on ManyToMany / reverse FK in loops
- `.values()` vs `.only()` — use `.only()` when you need model instances
- `.annotate()` with `Count` that could be cached
- `QuerySet` evaluated multiple times — cache in a variable if reused

### Prisma / TypeORM / Sequelize (Node/TypeScript)
- `findMany()` with no `take` / `limit`
- `include` on nested relations without limiting depth
- Raw query with template literal string interpolation — SQL injection
- `await` inside a loop over DB results
- Transaction not rolled back on error

### GORM (Go)
- `db.Find(&results)` without `.Limit()`
- `db.Raw()` with `fmt.Sprintf` formatting — SQL injection
- Missing `db.Error` check after query
- `AutoMigrate` called in production code path

### ActiveRecord (Rails)
- `Model.all` without scope
- `n.times { Model.find(...) }` — N+1
- Missing `.includes()` for associations used in views
- Calling `.count` + `.all` separately — use `.size` or paginate

### Mongoose (MongoDB)
- `.find({})` with no `.limit()` — full collection scan
- `$where` clause — executes JavaScript on server, security risk
- Missing `.lean()` when result is read-only — unnecessary hydration overhead
- No index on fields used in `.find()` conditions
- Aggregation `$lookup` without `$limit` downstream

### Redis
- `KEYS *` in production — O(N) blocks the server
- `SMEMBERS` on a large set — loads entire set into memory
- `SETNX` without `EXPIRE` — potential memory leak / stale lock
- `GET`/`SET` in a loop instead of `MGET`/`MSET` — use pipeline
- No TTL on cached keys

---

## Step 4 — Security Checks

### SQL Injection Vectors
Flag any query built with string concatenation or interpolation:
```python
# CRITICAL — SQL injection
query = f"SELECT * FROM users WHERE name = '{name}'"
cursor.execute("SELECT * FROM users WHERE id = " + user_id)

# Safe
cursor.execute("SELECT * FROM users WHERE name = %s", (name,))
```

Flag in all languages:
- Python: f-string or `%` in `execute()`, `text()`, `db.query()`
- JS/TS: template literal in `query()`, `raw()`, `$queryRaw`
- Go: `fmt.Sprintf` in `db.Raw()` or `db.Exec()`
- Java: string concat in `createQuery()`, `createNativeQuery()`

---

## Step 5 — Output Format

Always output a summary table first, then a full finding block for every issue. Every finding MUST include a complete, copy-pasteable solution using the exact ORM and library already present in the file.

### Summary table

```
## Query Review Results

| # | Severity | Complexity | Issue | Location | Solution |
|---|----------|-----------|-------|----------|----------|
| 1 | CRITICAL  | 6/10 | SQL injection via f-string | auth.py:42 | Parameterized query |
| 2 | HIGH      | 8/10 | N+1: orders fetched in loop | orders.py:18 | Batch with .in_() |
| 3 | HIGH      | 4/10 | Unbounded SELECT * | users.py:31 | .limit() + named columns |
| 4 | MEDIUM    | 7/10 | No query timeout | db.py:55 | execution_options(timeout=) |
| 5 | LOW       | 3/10 | Count + fetch anti-pattern | reports.py:12 | Single paginated query |

Stack detected: SQLAlchemy + MySQL
Total: 5 findings (1 critical, 2 high, 1 medium, 1 low)
```

**Complexity score (1–10)** — computed per query, shown in the summary table:
- +1 per JOIN
- +1 per subquery
- +2 for GROUP BY or aggregation (COUNT, SUM, AVG)
- +1 for ORDER BY on unindexed column
- +2 if no LIMIT on a potentially large table
- +1 per filter condition beyond the first
- +1 if no timeout is set
- -1 if result is cached (Redis, memcached)

Score 1–3: low complexity (simple indexed lookup)
Score 4–6: moderate (review recommended)
Score 7–10: high complexity (flag, explain plan suggested)

### Per-finding block (required for every finding)

For each finding output this exact structure:

```
---
### Finding #N — [SEVERITY] Title
**Location**: `file.py:line`

**Problem**
[One sentence: what the code does wrong right now]

**Impact**
[One sentence: what breaks at scale or in production — be specific, e.g. "500 students = 500 DB round trips"]

**Current code**
```python
# current problematic code (copy from the actual file)
```

**Solution**
```python
# complete drop-in replacement — must use the same ORM/library as the file
# include all lines needed to make the fix work, not just the changed line
```

**Why this works**
[One sentence explaining the fix]

**Verify**
[Exact command or query to confirm the fix — e.g. EXPLAIN output, grep, test to run]
```

### Solution rules

1. **Always read the actual file** before writing a solution — never write generic pseudocode
2. **Match the ORM exactly** — if the file uses `r_session.query(Model)`, the solution must use `r_session.query(Model)`, not `db.query()` or `session.query()`
3. **Match the session variable** — use `r_session`, `session`, `db`, or whatever is declared at the top of the file
4. **Include imports** if the solution needs a new import that isn't already in the file
5. **Batch solutions** — for N+1, always provide both the new query helper AND the updated caller loop
6. **Complete, not partial** — the solution must be the full replacement block, not just the changed line with `...` placeholders

---

## Invocation

**Review a specific file:**
> `/query-review path/to/file.py`

**Review a specific function:**
> `/query-review review the get_orders function in orders/helpers/query_helpers.py`

**Review all query helpers in the project:**
> `/query-review scan all query_helpers directories`

**Check for a specific issue:**
> `/query-review check for N+1 in the forms app`