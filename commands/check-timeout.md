---
description: Check for queries missing timeout configuration that could cause connection pool exhaustion. Provides timeout solutions with confidence levels.
---

Check for missing query timeouts in: $ARGUMENTS

## Why timeouts matter

A query with no timeout runs until the DB finishes or the connection is dropped.
One slow query holds a DB connection. At peak load, all connections are held = connection pool exhausted = 500 errors for every user.

## Step 1 — Detect timeout configuration

Check where timeouts might be set:
1. **Connection level** — in `db_config.py` / `settings.py` / connection pool setup
2. **Query level** — `execution_options(timeout=N)`, `statement_timeout`, `MAX_EXECUTION_TIME`
3. **ORM level** — SQLAlchemy `execution_options`, Django `QuerySet.using()`, GORM `WithContext`

If connection-level timeout is set globally → flag individual queries as LOW only.
If no timeout found anywhere → flag every complex query as HIGH.

## Step 2 — Find queries that need timeouts

Flag queries that are candidates for slow execution:
- Multi-table JOINs (3+ tables)
- Aggregations (`COUNT`, `SUM`, `GROUP BY`) on large tables
- Full-text search or `LIKE '%...%'` patterns
- Queries with no index hint and multiple filter conditions
- Any `.all()` without limit (already flagged by check-unbounded, note it here too)
- Export / report queries (always long-running by nature)

## Step 3 — Output

### Summary
```
## Timeout Check — {target}

Global timeout configured: {YES at connection level | NO | UNKNOWN}
Queries missing timeout: {N}

| # | Confidence | Query type | Tables | Timeout risk | File | Line |
|---|-----------|-----------|--------|-------------|------|------|
```

### Per-finding block

```
---
### Finding #N — {SEVERITY} · Confidence: {HIGH | MEDIUM | LOW}
**No timeout on {query description}**
`{file}:{line}`

**Confidence explanation**
{Was global timeout checked? Is this query definitely slow or possibly slow?}

**Problem**
{Why this query can run long — joins, aggregation, no index, large table}

**Impact**
{What happens when it's slow: "holds DB connection for duration, at 20 concurrent users = pool exhausted"}

**Current code** _(exact lines)_
```python
{copy the query from the file}
```

**Solution A — query-level timeout (SQLAlchemy)**
```python
{same query with .execution_options(timeout=30) added before .all()/.one_or_none()}
```

**Solution B — statement timeout (MySQL / raw SQL)**
```python
# Set before the query, clear after
r_session.execute(text("SET SESSION MAX_EXECUTION_TIME=30000"))  # 30s in ms
{original query}
r_session.execute(text("SET SESSION MAX_EXECUTION_TIME=0"))      # reset
```

**Solution C — global timeout in db_config (recommended if no global timeout exists)**
```python
# In gqinstitute_backend/utils/db_config.py — add to engine creation:
engine = create_engine(
    DATABASE_URL,
    connect_args={"connect_timeout": 10},   # connection timeout
    pool_timeout=30,                          # pool checkout timeout
    execution_options={"timeout": 60},        # query execution timeout
)
```

**Recommend**: {Solution A | B | C} — {one sentence why}

**Verify**
```bash
# Test with an intentionally slow query and confirm it times out
# Check global config: grep -r "execution_options" gqinstitute_backend/utils/
# Check MySQL global: SHOW VARIABLES LIKE 'MAX_EXECUTION_TIME';
```
```

## Confidence levels for missing timeouts

**HIGH** — query is definitely slow and no timeout found anywhere:
- Multi-table JOIN (4+ tables) with aggregation
- No index hint and no filter on high-cardinality column
- Export query fetching all rows
- No global timeout found in db_config or settings

**MEDIUM** — query may be slow, global timeout uncertain:
- 2–3 table JOIN with filters
- Aggregation on indexed columns
- Global timeout may exist but was not confirmed in this review

**LOW** — query is likely fast or global timeout protects it:
- Single-table query on indexed primary key
- Query on a small master/lookup table
- Global timeout confirmed in db_config