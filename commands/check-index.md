---
description: Find missing indexes on filtered, joined, sorted, and grouped columns. Provides CREATE INDEX statements with confidence levels.
---

Audit the file or directory for missing database indexes: $ARGUMENTS

Follow these steps precisely.

## Step 1 — Read the file(s)

Read every file in scope. Never work from memory.

## Step 2 — Detect stack and dialect

Scan imports to identify ORM and database dialect:
- `from sqlalchemy` + `mysql` / `pymysql` / `mysqlclient` → SQLAlchemy + MySQL
- `from sqlalchemy` + `psycopg2` / `asyncpg` → SQLAlchemy + PostgreSQL
- `from django.db` → Django ORM (check `DATABASES` for dialect)
- `gorm.io/driver/mysql` → GORM + MySQL
- `gorm.io/driver/postgres` → GORM + PostgreSQL
- Raw `SELECT` strings → infer dialect from syntax (`LIMIT ?` = MySQL, `$1` = Postgres)

Record the dialect — index syntax differs between MySQL and PostgreSQL.

## Step 3 — Extract all query patterns

For each query found, identify:

### Filtered columns (WHERE clause)
```python
# SQLAlchemy
session.query(Application).filter(Application.institute_id == institute_id)
# → candidate: index on applications(institute_id)

session.query(Payment).filter(
    Payment.status == "success",
    Payment.created_at >= start_date
)
# → candidate: composite index on payments(status, created_at)
```

### Joined columns (JOIN / relationship)
```python
session.query(Application).join(Payment, Payment.application_id == Application.id)
# → candidate: index on payments(application_id)  ← FK columns often missed
```

### Sorted columns (ORDER BY)
```python
session.query(Application).order_by(Application.created_at.desc())
# → candidate: index on applications(created_at)
# if combined with filter: composite index (filter_col, created_at)
```

### Grouped columns (GROUP BY)
```python
session.query(Payment.status, func.count()).group_by(Payment.status)
# → candidate: index on payments(status)
```

### Unique constraint candidates
```python
session.query(User).filter(User.email == email).first()
# → if used for lookups: UNIQUE INDEX on users(email) is better than plain index
```

## Step 4 — Assess index need by confidence

**HIGH** — index is missing and query pattern is clearly harmful:
- FK column with no index (JOIN on unindexed FK = full table scan)
- High-cardinality column in WHERE with `.all()` or unbounded result
- `ORDER BY` on unindexed column with large result set
- Composite filter where leading column has low selectivity alone

**MEDIUM** — index would help but context is unclear:
- Column filtered but table may be small (< 10K rows)
- Composite index where partial index might suffice
- Column in WHERE but also appears in a UNIQUE constraint (may already be indexed)

**LOW** — index might help, but benefit depends on data distribution:
- Low-cardinality column (e.g., `status` with 3 values on large table — depends on selectivity)
- Column only used in admin/export queries (infrequent execution)
- Covering index optimization (already indexed, but could add columns to avoid table lookup)

## Step 5 — Generate CREATE INDEX statements

Match syntax to detected dialect.

### MySQL
```sql
-- Single column
CREATE INDEX idx_payments_application_id ON payments(application_id);

-- Composite (filter + sort)
CREATE INDEX idx_applications_institute_status ON applications(institute_id, status);

-- Unique
CREATE UNIQUE INDEX idx_users_email ON users(email);

-- Covering index (avoids table lookup)
CREATE INDEX idx_payments_status_amount ON payments(status, amount);
```

### PostgreSQL
```sql
-- Single column
CREATE INDEX CONCURRENTLY idx_payments_application_id ON payments(application_id);

-- Composite
CREATE INDEX CONCURRENTLY idx_applications_institute_status ON applications(institute_id, status);

-- Partial index (high selectivity on a subset)
CREATE INDEX CONCURRENTLY idx_payments_pending ON payments(created_at)
WHERE status = 'pending';

-- Unique
CREATE UNIQUE INDEX CONCURRENTLY idx_users_email ON users(email);
```

**PostgreSQL rule**: always use `CONCURRENTLY` in production to avoid table lock.
**MySQL rule**: `CREATE INDEX` on InnoDB acquires a metadata lock — run during low-traffic window.

## Step 6 — Check for composite index ordering

Column order in composite indexes matters. Lead with the most selective filter:

```
-- Good: institute_id is high-cardinality (many distinct values)
CREATE INDEX idx_applications ON applications(institute_id, status, created_at);

-- Bad: status is low-cardinality (only 3 values) — wastes the index
CREATE INDEX idx_applications ON applications(status, institute_id, created_at);
```

Rule: equality filters first, range filters last, sort columns at the end.

## Step 7 — Output findings

### Summary Table
| # | Severity | Confidence | Table | Column(s) | Query Pattern | Action |
|---|----------|-----------|-------|-----------|---------------|--------|
| 1 | HIGH | HIGH | payments | application_id | JOIN (FK) | CREATE INDEX |
| 2 | HIGH | HIGH | applications | institute_id, status | WHERE composite | CREATE INDEX |
| 3 | MEDIUM | MEDIUM | users | status | WHERE low-cardinality | Review first |
| 4 | LOW | LOW | audit_logs | created_at | ORDER BY on infrequent query | Consider |

### Detailed Finding Block (for each HIGH/MEDIUM)

```
Finding #N — SEVERITY · CONFIDENCE confidence
File: path/to/file.py, Line: NN

Query pattern:
{exact query code}

Missing index on: {table}({column(s)})
Impact: {what happens without the index — e.g., "full scan of payments table (est. 2M rows) on every request"}

Recommended index:
{CREATE INDEX statement}

Notes:
- {any caveats — existing constraints, partial index option, composite ordering advice}
```

## Step 8 — Migration snippet

For every HIGH-confidence finding, also output a ready-to-use Alembic migration:

```python
# Alembic migration snippet
def upgrade():
    op.create_index('idx_payments_application_id', 'payments', ['application_id'])

def downgrade():
    op.drop_index('idx_payments_application_id', table_name='payments')
```

## Rules

1. Never invent table or column names — only use names visible in the code
2. If the model definition isn't in scope, note it: "Verify column `institute_id` exists in `applications` table"
3. Don't flag primary key columns — they're always indexed
4. Don't flag columns that appear in UNIQUE constraints — unique constraints imply an index
5. Always provide both the `CREATE INDEX` and the Alembic snippet for HIGH findings