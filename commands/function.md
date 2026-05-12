---
description: Review a specific function or method for database query issues. Provide solutions with confidence levels. Input format: "function_name in path/to/file.py"
---

Review the database queries in this function: $ARGUMENTS

Follow these steps precisely:

## Step 1 — Locate and read
Parse the input to extract the function name and file path.
Read the full file — do not rely on memory.
Find the exact function definition — note its start and end line numbers.
Also read 20 lines before the function to capture session variables, imports, and context.

## Step 2 — Detect stack
From the file's imports identify the ORM and session variable:
- Session var: look for `r_session = settings.R_DB_SESSION`, `session = settings.DB_SESSION`, `db = ...`
- ORM: `from sqlalchemy` / `from django.db` / `import prisma` / `gorm.io` / `mongoose`
- Database: `.with_hint(dialect_name="mysql")` → MySQL, `asyncpg` → PostgreSQL, etc.

All solutions MUST use the exact variable names found in the file.

## Step 3 — Deep review of the function

Read every line of the function. For each query check:

**Query-level checks:**
- Is there a `.limit()` / `LIMIT` / `take()` on list queries?
- Is the query inside a loop?
- Does the SELECT fetch columns that are immediately discarded?
- Is there a `GROUP BY` that doesn't include all non-aggregated SELECT columns?
- Is there a bare column reference inside `and_()` instead of a comparison?
- Is `session.commit()` called before a read (unnecessary) or missing after a write?
- Is the session closed explicitly when `@with_session` already handles it?

**Security checks:**
- Is user input interpolated directly into a query string?
- Is `text()` used with f-strings or `%` formatting?

**ORM-specific:**
- SQLAlchemy: lazy access on relationship inside loop, duplicate imports, `func` imported twice
- Django: `.all()` without filter, missing `select_related`, queryset evaluated multiple times
- Mongoose: `.find({})` without `.limit()`, missing `.lean()`
- GORM: `.Find()` without `.Limit()`, missing `db.Error` check

## Step 4 — Output

### Function summary
```
## Query Review — {function_name}()
File: {path}:{start_line}–{end_line}
Stack: {ORM + database}
Queries in function: {N}
Issues found: {N}

| # | Confidence | Severity | Issue | Line |
|---|-----------|----------|-------|------|
```

### Per-finding block (required for every issue)

```
---
### Finding #N — {SEVERITY} · Confidence: {HIGH | MEDIUM | LOW}
**{Issue title}**
`{file}:{line}`

**Confidence explanation**
{One sentence: why this confidence level — what you verified or could not verify}

**Problem**
{What the code does wrong at this exact line}

**Impact**
{Concrete production scenario — numbers where possible}

**Current code** _(exact lines from the function)_
```python
{actual code copied from file}
```

**Solution**
```python
{complete replacement — exact ORM, exact session var, exact model names}
{if N+1: include both new batch helper AND updated caller}
{if import needed: include the import line}
```

**Why this works**
{One sentence}

**Verify**
```bash
{command to confirm — EXPLAIN, grep, or test}
```
```

## Confidence levels

**HIGH** — confirmed by reading the code:
- Query is visibly inside a loop
- f-string in execute() call
- Bare column reference in and_()
- Duplicate import confirmed by reading both lines
- `data` column selected and immediately popped in the same function

**MEDIUM** — pattern matches, context needed:
- Unbounded `.all()` — table may be intentionally small
- `commit()` before read — may be intentional for read-committed isolation
- Missing timeout — may be set at connection level not shown in this file

**LOW** — depends on caller or runtime:
- Function takes `limit` parameter — caller might always pass one
- GROUP BY mismatch — MySQL mode may allow it on this server
- Session close — `@with_session` behaviour depends on decorator implementation