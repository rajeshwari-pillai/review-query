---
description: Check specifically for N+1 query patterns in a file, function, or app directory. For each N+1 found, provide a complete batch-query solution with confidence level.
---

Check for N+1 query patterns in: $ARGUMENTS

## What is an N+1

A query executed inside a loop: 1 query to get a list, then 1 query per item = N+1 total.
At 10 items: 11 queries. At 500 items: 501 queries. At 10,000 items: 10,001 queries.

## Step 1 — Find all loops with DB calls inside

Scan the target for any of these patterns:

**Python:**
```python
for x in results:
    session.query(...)           # ← N+1
    r_session.query(...)         # ← N+1
    SomeModel.objects.filter(...) # ← N+1
    fetch_something(x.id)        # ← N+1 if fetch_something runs a query
```

**JavaScript / TypeScript:**
```js
for (const x of results) {
    await db.findOne(...)         // ← N+1
    await prisma.model.findUnique(...) // ← N+1
}
results.map(async x => await repo.find(x.id))  // ← N+1
```

**Go:**
```go
for _, x := range results {
    db.Where("id = ?", x.ID).First(&item)  // ← N+1
}
```

**Indirect N+1** — function called in loop that internally queries:
- Read the called function to confirm it runs a query
- If confirmed: N+1 at calling site, not inside the function

## Step 2 — For each N+1 found

Calculate real impact:
- Identify what the outer query returns (e.g., "all students in a form")
- State the N+1 multiplier (e.g., "1 query per student")
- Give a concrete number: "100 students = 101 queries; 1000 students = 1001 queries"

## Step 3 — Output

### Summary
```
## N+1 Check Results — {target}

N+1 patterns found: {N}

| # | Confidence | Outer query returns | Inner query | Multiplier | File | Line |
|---|-----------|---------------------|-------------|------------|------|------|
```

### Per-finding block (required for every N+1)

```
---
### N+1 #N — Confidence: {HIGH | MEDIUM | LOW}
**{Outer model} → {Inner model} in loop**
`{file}:{line}`

**Confidence explanation**
{What was confirmed — did you read the inner function? Is the loop definitely unbounded?}

**Problem**
{What the loop does and how many queries it causes}

**Impact**
{Real numbers: "export with 500 students fires 500 extra queries = ~2.5s added latency at 5ms/query"}

**Current code** _(exact lines)_
```python
{the loop and the query inside it, copied from the file}
```

**Solution — batch with .in_()**
```python
# Step 1: collect IDs before the loop
{id_list} = [{item}.{id_field} for {item} in {outer_results}]

# Step 2: single batch query
{results_map} = {batch_query_using_in_(id_list)}
# returns: {id: data} dict for O(1) lookup

# Step 3: replace the loop body
for {item} in {outer_results}:
    {data} = {results_map}.get({item}.{id_field}, {default})
    # ... rest of loop body unchanged
```

**Full batch helper** _(if the query is in a separate helper file)_
```python
@with_session
def {new_batch_function}({id_list}: list):
    if not {id_list}:
        return {}
    rows = (
        r_session.query(
            {Model}.{id_field},
            {Model}.{needed_columns},
        )
        .filter(
            {Model}.{id_field}.in_({id_list}),
            {Model}.is_active == 1,
            {Model}.deleted_on.is_(None),
        )
        .all()
    )
    return {row["{id_field}"]: row for row in result_list_to_dict(rows)}
```

**Why this works**
Single IN() query replaces N queries — DB executes one index range scan.

**Verify**
```bash
# Before: add logging to count queries
# After: should log exactly 1 query for this operation
# Or: run EXPLAIN on the new batch query — should show index range scan
```
```

## Confidence levels for N+1

**HIGH** — loop is visible in the file AND inner query confirmed:
- Query directly inside the loop (not a function call)
- Function called in loop was read and confirmed to run a query
- No lazy-load decorator or caching that would prevent repeated queries

**MEDIUM** — loop found but inner call not fully traced:
- Function called in loop but its body was not read
- Loop may be over a small fixed-size list (e.g., a list of 3 status codes)
- Caching decorator on the inner function may deduplicate

**LOW** — pattern suspicious but unconfirmed:
- Async function called in loop but `await` missing (may not execute)
- Loop variable shadowed — actual iteration target unclear
- Inner function name suggests it might be cached