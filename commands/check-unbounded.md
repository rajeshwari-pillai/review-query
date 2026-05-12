---
description: Check for unbounded queries (missing LIMIT / .limit() / take()) that could return entire tables and cause OOM or extreme latency. Provides paginated replacements with confidence levels.
---

Check for unbounded queries in: $ARGUMENTS

## What counts as unbounded

A query that can return an arbitrary number of rows with no upper bound set in code.

**Unbounded — always flag:**
```python
session.query(Model).all()                    # no limit
session.query(Model).filter(...).all()        # filtered but still no limit
Model.objects.all()                           # Django — full table
Model.objects.filter(status="active")         # filtered but no limit
collection.find({})                           # MongoDB — full collection
db.Find(&results)                             # GORM — no Limit()
prisma.model.findMany()                       # Prisma — no take
```

**Bounded — do not flag:**
```python
session.query(Model).filter(...).limit(100).all()
session.query(Model).filter(...).one_or_none()   # single row
session.query(Model).filter(...).first()          # single row
Model.objects.filter(...).count()                 # count only
collection.find({}).limit(100)
db.Find(&results).Limit(100)
```

## Step 1 — Find all list queries

Scan for `.all()`, `findMany()`, `find({})`, `db.Find(&`, `Model.objects.filter(` with no chained `.limit()`, `[:n]`, `.first()`, `.one_or_none()`.

## Step 2 — Assess each unbounded query

For each find:
1. What table/collection does it query?
2. What filters are applied? (fewer filters = higher risk)
3. Is a `limit` parameter accepted by the function but not applied? (caller might pass limit=None)
4. Is this called from an export / report endpoint? (higher risk — no user-facing pagination)
5. Is this called from a background task? (medium risk — can cause timeout)

## Step 3 — Output

### Summary
```
## Unbounded Query Check — {target}

Unbounded queries found: {N}

| # | Confidence | Severity | Table | Filters | Called from | File | Line |
|---|-----------|----------|-------|---------|-------------|------|------|
```

### Per-finding block (required for every unbounded query)

```
---
### Finding #N — {SEVERITY} · Confidence: {HIGH | MEDIUM | LOW}
**Unbounded query on {table/model}**
`{file}:{line}`

**Confidence explanation**
{What was read — confirmed no limit in function? Checked all call sites?}

**Problem**
{Table queried, filters applied, estimated risk if table grows}

**Impact**
{Concrete scenario: "forms table at 50K rows, no filter — full table scan, all rows loaded to memory"}

**Current code** _(exact lines)_
```python
{copy the unbounded query from the file}
```

**Solution A — add limit (for paginated endpoints)**
```python
{same query with .limit(limit).offset(offset) added}
{update the function signature to accept limit and offset if not already present}
```

**Solution B — add hard cap (for internal/export use)**
```python
{same query with .limit(MAX_ROWS) where MAX_ROWS is a reasonable constant for this use case}
{e.g. .limit(10_000) for exports, .limit(100) for API list endpoints}
```

**Solution C — stream in batches (for large exports)**
```python
{batch processing pattern using .limit(batch_size).offset(i * batch_size)}
{or keyset pagination using .filter(Model.id > last_id).limit(batch_size)}
```

**Recommend**: {Solution A | B | C} — {one sentence why}

**Why this works**
{One sentence}

**Verify**
```bash
# After fix: confirm limit is always applied
grep -n "\.all()" {file}   # should return 0 unbounded .all() calls
```
```

## Confidence levels for unbounded queries

**HIGH** — confirmed unbounded in this function AND no caller applies a limit:
- `.all()` with no `.limit()` in the function body
- Function signature has no `limit` parameter
- Called from an export or report endpoint that fetches all records

**MEDIUM** — unbounded in function but caller context uncertain:
- `.all()` with no limit in function
- Function accepts `limit` and `offset` parameters but the check shows `limit=None` path can call `.all()`
- Table is likely small now but has no structural cap

**LOW** — pattern flagged but likely intentional or safe:
- Query is for a lookup/master table with a known small number of rows (e.g., education types, class masters)
- `.all()` is on a table filtered to a single parent entity (result is inherently small)
- Admin-only endpoint where full data load is the explicit requirement