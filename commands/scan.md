---
description: Scan an entire app, directory, or the full project for database query issues across all query helper files. Provides a ranked findings report with solutions and confidence levels.
---

Scan for database query issues in: $ARGUMENTS

If no argument given, scan the entire project.

Follow these steps:

## Step 1 — Find all query files

Search for files that contain database queries:
- Files named `*query_helper*`, `*query*`, `*repository*`, `*dao*`, `*store*`
- Files containing: `session.query(`, `db.query(`, `.find(`, `.findMany(`, `SELECT`, `cursor.execute(`
- Exclude: test files, migration files, `__pycache__`

List every file found before reviewing.

## Step 2 — Detect stack per file

For each file note:
- ORM in use
- Session variable name
- Database dialect

## Step 3 — Review each file

For each file run the same checks as `review-file`:
- N+1, unbounded queries, SELECT *, SQL injection, no timeout, ORM-specific issues

Track all findings with: file, line, issue type, severity, confidence.

## Step 4 — Output

### Project-wide summary
```
## Query Scan Results — {app or project name}

Files scanned: {N}
Total queries found: {N}
Total issues: {N}

### By severity
| Severity | Count |
|----------|-------|
| CRITICAL | {N}   |
| HIGH     | {N}   |
| MEDIUM   | {N}   |
| LOW      | {N}   |

### By confidence
| Confidence | Count |
|-----------|-------|
| HIGH      | {N}   |
| MEDIUM    | {N}   |
| LOW       | {N}   |

### All findings (ranked: CRITICAL HIGH first, then by confidence)
| # | Confidence | Severity | Issue | File | Line |
|---|-----------|----------|-------|------|------|
```

### Per-finding block (required for every issue — same format as review-file)

```
---
### Finding #N — {SEVERITY} · Confidence: {HIGH | MEDIUM | LOW}
**{Issue title}**
`{file}:{line}`

**Confidence explanation**
{Why this confidence — what was confirmed vs assumed}

**Problem**
{What the code does wrong}

**Impact**
{Production failure scenario with numbers}

**Current code**
```{language}
{exact lines from the file}
```

**Solution**
```{language}
{complete drop-in fix — exact ORM, session var, model names from this file}
```

**Why this works**
{One sentence}

**Verify**
```bash
{EXPLAIN / grep / test command}
```
```

### Fix priority order

After all findings, output a prioritised fix list:

```
## Recommended Fix Order

Fix these first (CRITICAL + HIGH confidence):
1. Finding #N — {title} ({file}:{line})
2. ...

Fix these next (HIGH severity, MEDIUM confidence):
3. Finding #N — {title} ({file}:{line})
4. ...

Investigate these (LOW confidence — verify before fixing):
5. Finding #N — {title} ({file}:{line})
6. ...
```

## Confidence levels

**HIGH** — read the code, confirmed the issue exists and is unambiguous.
**MEDIUM** — pattern matches; context (caller, config, table size) may change assessment.
**LOW** — suspicious pattern; requires investigation before applying fix.