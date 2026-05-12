---
description: Check specifically for SQL injection vulnerabilities in a file or directory. For every unsafe query found, provide a parameterized replacement with confidence level.
---

Check for SQL injection vulnerabilities in: $ARGUMENTS

## What counts as SQL injection risk

Any query where user-controlled or externally-sourced data is interpolated directly into a SQL string — instead of being passed as a bound parameter.

## Step 1 — Find all query construction patterns

Scan for these patterns in every language:

**Python — UNSAFE:**
```python
f"SELECT * FROM users WHERE id = {user_id}"           # f-string
"SELECT * FROM users WHERE id = " + user_id            # concat
"SELECT * FROM users WHERE id = %s" % user_id          # % format (positional ok, but flag named %)
cursor.execute(f"...")                                  # f-string in execute
session.execute(text(f"..."))                           # f-string in text()
db.execute("... WHERE name = '{}'".format(name))        # .format()
```

**Python — SAFE:**
```python
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
session.execute(text("SELECT * FROM users WHERE id = :id"), {"id": user_id})
db.query(User).filter(User.id == user_id)              # ORM parameterizes automatically
```

**JavaScript / TypeScript — UNSAFE:**
```js
db.query(`SELECT * FROM users WHERE id = ${userId}`)   # template literal
db.raw(`SELECT * FROM users WHERE name = '${name}'`)   # raw with template
prisma.$queryRaw(`SELECT * FROM users WHERE id = ${id}`) # $queryRaw with template
```

**JavaScript / TypeScript — SAFE:**
```js
db.query("SELECT * FROM users WHERE id = $1", [userId])
prisma.$queryRaw`SELECT * FROM users WHERE id = ${userId}`  # tagged template (safe)
```

**Go — UNSAFE:**
```go
db.Raw(fmt.Sprintf("SELECT * FROM users WHERE id = %d", userID))
db.Exec("DELETE FROM users WHERE id = " + id)
```

**Go — SAFE:**
```go
db.Raw("SELECT * FROM users WHERE id = ?", userID)
db.Where("id = ?", userID).Find(&user)
```

**Java — UNSAFE:**
```java
em.createQuery("SELECT u FROM User u WHERE u.id = " + id)
stmt.executeQuery("SELECT * FROM users WHERE name = '" + name + "'")
```

**Java — SAFE:**
```java
em.createQuery("SELECT u FROM User u WHERE u.id = :id").setParameter("id", id)
PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?");
```

## Step 2 — Assess each finding

For each unsafe pattern found:
1. Identify the source of the interpolated value — is it user input, internal value, or config?
2. Risk level:
   - User input directly → CRITICAL
   - API request param → CRITICAL
   - Internal value from another DB query → HIGH (second-order injection)
   - Config or env var → MEDIUM (still bad practice)

## Step 3 — Output

### Summary
```
## SQL Injection Check — {target}

Unsafe query patterns found: {N}

| # | Confidence | Risk | Pattern | Source | File | Line |
|---|-----------|------|---------|--------|------|------|
```

### Per-finding block (required for every unsafe query)

```
---
### Injection #N — {RISK} · Confidence: {HIGH | MEDIUM | LOW}
**{Pattern type} in {function/method name}**
`{file}:{line}`

**Confidence explanation**
{What was confirmed — is the value definitely user-controlled, or just possibly?}

**Problem**
{Exact interpolation pattern and where the value comes from}

**Attack scenario**
{One concrete example: what an attacker would send and what SQL it produces}
e.g. Input: `' OR '1'='1` → Query becomes: `SELECT * FROM users WHERE name = '' OR '1'='1'`

**Current code** _(exact lines)_
```{language}
{copy the unsafe query from the file}
```

**Solution — parameterized query**
```{language}
{complete parameterized replacement using the same library already in the file}
{include import if a new function like text() is needed}
```

**Why this works**
The database driver separates SQL structure from data — the value can never alter query logic.

**Verify**
```bash
grep -n "f\"" {file}       # find remaining f-strings in queries
grep -n "text(f" {file}    # find text() with f-string
# After fix: re-run this check — should return 0 hits
```
```

## Confidence levels for injection

**HIGH** — confirmed injection path:
- f-string, `.format()`, or concat directly in `execute()` / `text()` / `db.Raw()`
- Value traced to `request.query_params`, `request.data`, or function argument from API view
- No escaping or validation layer between input and query

**MEDIUM** — unsafe pattern but risk uncertain:
- Value comes from an internal function — source not fully traced
- Pattern is unsafe but value is an integer cast (still bad practice, lower exploit risk)
- Query is in a function only callable by authenticated admin users

**LOW** — suspicious but likely safe:
- Value comes from settings or env var (not user input)
- Value is a hardcoded constant being assembled dynamically for readability
- Pattern flagged but ORM wraps it in parameterized execution under the hood