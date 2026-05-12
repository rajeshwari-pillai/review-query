---
description: Review all database queries in a specific file for N+1s, unbounded fetches, SQL injection, missing indexes, and ORM anti-patterns. Provides solutions with confidence levels.
---

Review all database queries in the file: $ARGUMENTS

Follow these steps precisely:

## Step 1 — Read the file
Read the full file at the given path. Never review from memory or assumptions.

## Step 2 — Detect stack
Scan imports to identify ORM and database:
- `from sqlalchemy` → SQLAlchemy
- `from django.db` → Django ORM
- `@prisma/client` / `typeorm` / `sequelize` → Node ORM
- `gorm.io` → GORM (Go)
- `mongoose` → Mongoose
- `pymongo` / `MongoClient` → MongoDB
- `redis` / `ioredis` → Redis
- Raw `SELECT`/`INSERT` strings → raw SQL

Note the exact session variable used (`r_session`, `session`, `db`, etc.) — all solutions must use this exact variable.

## Step 3 — Scan for issues
Check every query in the file against:
- N+1: query inside a `for` / `while` / `map` loop
- Unbounded: `.all()` / `findMany()` / `.find({})` with no `.limit()`
- SELECT *: fetching all columns when only some are needed
- SQL injection: f-string / string concat / template literal in query
- No timeout: no `execution_options`, `statement_timeout`, or `.timeout()`
- Missing index hint on heavy filter columns
- Lazy load in loop (SQLAlchemy / Django ORM)
- Count + fetch separately instead of one query
- Fetching full object to read one field
- ORM-specific issues for the detected stack

## Step 4 — Output findings

### Summary table
```
## Query Review — {filename}

Stack: {detected ORM + database}
Queries found: {N}
Issues found: {N}

| # | Confidence | Severity | Issue | Line |
|---|-----------|----------|-------|------|
| 1 | HIGH       | CRITICAL | SQL injection via f-string | 42 |
| 2 | HIGH       | HIGH     | N+1: fetch in loop | 88 |
| 3 | MEDIUM     | HIGH     | Unbounded .all() | 31 |
| 4 | LOW        | MEDIUM   | No query timeout | 55 |
```

### Per-finding block

For EVERY finding, output this full block — no exceptions:

```
---
### Finding #N — {SEVERITY} · Confidence: {HIGH | MEDIUM | LOW}
**{Issue title}**
`{file}:{line}`

**Confidence: HIGH** — I read the code at this line. The issue is present and unambiguous.
**Confidence: MEDIUM** — The pattern matches but context may change the assessment. Verify before applying.
**Confidence: LOW** — Possible issue depending on call sites or runtime data. Investigate first.

---

**Problem**
{One sentence: what exactly the code does wrong}

**Impact**
{One sentence: what breaks — be concrete, e.g. "1000 students = 1000 queries per export request"}

**Current code** _(from file, exact lines)_
```{language}
{copy the actual problematic lines from the file}
```

**Solution**
```{language}
{complete drop-in replacement — use the exact session var and ORM from the file}
{include every line needed: imports, helper function, updated caller}
{no pseudocode, no ... placeholders}
```

**Why this works**
{One sentence}

**Verify**
```bash
{exact command to confirm fix — EXPLAIN query, grep, test to run}
```
```

## Confidence level rules

Assign confidence before writing the solution:

**HIGH** — apply when:
- You read the exact lines and confirmed the issue
- The problematic pattern is unambiguous (e.g. query inside a for loop, f-string in execute())
- No edge case could make this safe

**MEDIUM** — apply when:
- The pattern matches but a decorator, base class, or framework behaviour might handle it
- The query may be intentionally unbounded (e.g. admin-only export with known small dataset)
- The issue is real but the suggested fix might need adjustment for this codebase

**LOW** — apply when:
- The issue depends on runtime data (e.g. "this table might be large")
- The function is only called in one place and that caller has a guard
- The pattern is suspicious but you cannot confirm it causes harm without more context

## Solution rules

1. Read the actual file — never write generic code
2. Use the exact session variable declared at the top of the file
3. Use the exact ORM/library already imported
4. For N+1 fixes: provide both the new batch query AND the updated caller
5. For unbounded queries: use the actual model and column names from the file
6. Include new imports if needed — check what is already imported first
7. The solution must be the complete replacement, not a partial diff