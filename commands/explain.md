---
description: Generate EXPLAIN / EXPLAIN ANALYZE for a query and interpret the execution plan — identifies seq scans, missing indexes, bad joins, and cost estimates.
---

Generate and interpret an EXPLAIN plan for the query or function: $ARGUMENTS

Input can be:
- A function name + file: `get_applications in app/query_helpers/application_helper.py`
- A raw SQL query pasted inline
- A file path (explains every query in the file)

Follow these steps precisely.

## Step 1 — Extract the SQL

### From a function/file
Read the file. Locate the function. Extract the raw SQL or ORM query. Convert ORM to approximate SQL:

```python
# SQLAlchemy ORM input
session.query(Application).filter(
    Application.institute_id == institute_id,
    Application.status == "active"
).order_by(Application.created_at.desc()).limit(50).all()

# Approximate SQL output
SELECT * FROM applications
WHERE institute_id = :institute_id
  AND status = 'active'
ORDER BY created_at DESC
LIMIT 50;
```

### From raw SQL input
Use the query as-is. Sanitize any f-string variables to named parameters (`:param` for MySQL/SQLAlchemy, `$1` for PostgreSQL).

## Step 2 — Generate the EXPLAIN command

Output the exact command the user should run, matched to their dialect.

### MySQL / MariaDB
```sql
-- Basic plan (fast, no execution)
EXPLAIN
SELECT * FROM applications
WHERE institute_id = 123 AND status = 'active'
ORDER BY created_at DESC
LIMIT 50;

-- JSON format (more detail)
EXPLAIN FORMAT=JSON
SELECT * FROM applications
WHERE institute_id = 123 AND status = 'active'
ORDER BY created_at DESC
LIMIT 50;
```

### PostgreSQL
```sql
-- Full analysis (executes the query — use on non-prod or with ROLLBACK)
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM applications
WHERE institute_id = 123 AND status = 'active'
ORDER BY created_at DESC
LIMIT 50;
```

**Warning for PostgreSQL ANALYZE**: This actually runs the query. Wrap in a transaction and roll back if testing on prod:
```sql
BEGIN;
EXPLAIN (ANALYZE, BUFFERS) SELECT ...;
ROLLBACK;
```

### SQLAlchemy (Python — generate plan inline)
```python
from sqlalchemy import text

# MySQL
result = session.execute(text("EXPLAIN FORMAT=JSON " + str(query.statement.compile(
    dialect=session.bind.dialect,
    compile_kwargs={"literal_binds": True}
))))

# PostgreSQL
result = session.execute(text("EXPLAIN (ANALYZE, BUFFERS) " + str(query.statement.compile(
    dialect=session.bind.dialect,
    compile_kwargs={"literal_binds": True}
))))

for row in result:
    print(row[0])
```

## Step 3 — Interpret the plan (if output is provided)

If the user provides EXPLAIN output, parse and interpret it. If not, provide expected plan based on query structure.

### MySQL EXPLAIN columns

| Column | What it means |
|--------|--------------|
| `type` | Access method — see ranking below |
| `key` | Index used (NULL = no index) |
| `rows` | Estimated rows examined |
| `Extra` | Important flags (see below) |
| `filtered` | % of rows passing WHERE after index |

**`type` ranking** (best → worst):
```
system → const → eq_ref → ref → range → index → ALL
```
- `ALL` = full table scan → almost always bad on large tables
- `index` = full index scan → better than ALL but still slow on large indexes
- `range` = index range scan → acceptable
- `ref` / `eq_ref` = index lookup → good
- `const` / `system` = single row → best possible

**`Extra` flags to flag as problems**:
- `Using filesort` → ORDER BY cannot use an index → add index on sort column
- `Using temporary` → GROUP BY or ORDER BY requires temp table → often fixable with index
- `Using where; Using index` → covering index in use → good
- `Full scan on NULL key` → LEFT JOIN with OR NULL condition → restructure query

### PostgreSQL EXPLAIN nodes

| Node type | Meaning |
|-----------|---------|
| `Seq Scan` | Full table scan — bad on large tables |
| `Index Scan` | Index lookup — good |
| `Index Only Scan` | Covering index — best |
| `Bitmap Heap Scan` | Range scan via bitmap — acceptable |
| `Hash Join` | Join via hash table — good for large joins |
| `Nested Loop` | Loop join — good for small outer sets, bad for large |
| `Sort` | In-memory sort — check `work_mem` if large |

**Key cost fields**:
```
Seq Scan on applications  (cost=0.00..4821.00 rows=50000 width=256)
                                    ↑ startup    ↑ total    ↑ row count
```
- High `rows` on a Seq Scan = missing index
- `actual rows` >> `rows` estimate = stale statistics → run `ANALYZE table_name`

## Step 4 — Identify problems and fixes

For each problem found in the plan, output a finding block:

```
Problem: Full table scan (type=ALL / Seq Scan)
Table: applications
Estimated rows examined: 250,000
Actual rows returned: 47

Root cause: No index on (institute_id, status)

Fix — add index:
CREATE INDEX CONCURRENTLY idx_applications_institute_status
ON applications(institute_id, status);

Expected improvement: type=ALL → type=ref, rows examined: 250,000 → ~200
```

```
Problem: Using filesort
Column: created_at (ORDER BY)
Root cause: Existing index on (institute_id) doesn't include created_at

Fix — extend index to cover sort:
DROP INDEX idx_applications_institute;
CREATE INDEX CONCURRENTLY idx_applications_institute_status_date
ON applications(institute_id, status, created_at DESC);

Expected improvement: filesort eliminated, ORDER BY uses index
```

```
Problem: Using temporary (GROUP BY)
Root cause: GROUP BY on unindexed column or expression

Fix options:
1. Add index on GROUP BY column
2. Rewrite as subquery with pre-aggregation
3. Add result caching (Redis) if grouping result is reused
```

## Step 5 — Output format

### Section 1: Generated EXPLAIN command
Exact SQL to run — copy-paste ready.

### Section 2: Expected plan (if no output provided)
Based on query structure, predict likely plan issues before running.

### Section 3: Plan interpretation (if output provided)
Table of each node/row with flag (OK / WARNING / CRITICAL).

### Section 4: Findings and fixes
One block per problem, with root cause + fix + expected improvement.

### Section 5: Verification
```
After applying the fix, re-run:
EXPLAIN ...same query...

Confirm:
✓ type changed from ALL → ref (MySQL)
✓ Seq Scan replaced by Index Scan (PostgreSQL)
✓ "Using filesort" removed from Extra column
✓ rows examined dropped from 250,000 → ~200
```

## Rules

1. Never invent EXPLAIN output — only interpret what the user provides, or predict based on query structure
2. Always output the exact EXPLAIN command first — the user must run it; don't skip this
3. For PostgreSQL ANALYZE, always warn about execution side effects and suggest wrapping in BEGIN/ROLLBACK
4. Match fix syntax to the detected dialect
5. If the query has parameters (`:institute_id`), substitute a realistic example value in the EXPLAIN command