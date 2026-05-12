---
description: Review all database queries in a file and automatically apply all HIGH-confidence fixes directly to the code. MEDIUM/LOW findings are listed but not auto-applied — user is prompted to confirm each one.
---

Review AND fix all database query issues in the file: $ARGUMENTS

Follow these steps precisely. This command WRITES to the file — read carefully before editing.

## Step 1 — Read the file

Read the full file. Never work from memory.

## Step 2 — Detect stack

Scan imports to identify ORM, database, and the exact session variable:
- `from sqlalchemy` → SQLAlchemy
- `from django.db` → Django ORM
- `gorm.io` → GORM (Go)
- `mongoose` → Mongoose
- `pymongo` / `MongoClient` → MongoDB
- `redis` / `ioredis` → Redis
- Raw `SELECT`/`INSERT` strings → raw SQL

Record the exact session variable (`r_session`, `session`, `db`, etc.) — every edit must use this variable.

## Step 3 — Find all issues

Check every query against:
- N+1: query inside a `for` / `while` / `map` loop
- Unbounded: `.all()` / `findMany()` / `.find({})` with no `.limit()`
- SELECT *: fetching all columns when only some are needed
- SQL injection: f-string / string concat / template literal in query
- No timeout: no `execution_options`, `statement_timeout`, or `.timeout()`
- Lazy load in loop
- Count then fetch anti-pattern
- Fetching full object to read one field
- Result of `.all()` / `.execute()` not assigned to a variable (result thrown away)
- Duplicate filter blocks or `.group_by()` calls on the same query
- Unused imports
- Manual `session.close()` when `@with_session` decorator is present or should be added

## Step 4 — Assign confidence to every finding

**HIGH** — confirmed issue, unambiguous fix, safe to auto-apply:
- Result of `.all()` not assigned
- Duplicate filter / group_by block
- Wrong alias used in filter (aliased model used in SELECT but base model used in WHERE)
- Unused import (symbol never referenced outside the import line)
- Manual `session.close()` inside a `@with_session`-decorated function
- f-string / string concat in `execute()` — SQL injection

**MEDIUM** — real issue but fix needs context, prompt user before applying:
- Unbounded `.all()` on a table that could be large — may be intentional for admin/export
- Duplicate `payment_status` column in SELECT
- Missing `@with_session` on a function that manually calls `session.close()`

**LOW** — do not auto-apply, flag only:
- No query timeout — connection-level setting may already cover it
- `r_session.commit()` that could be `expire_all()` — depends on session config

## Step 5 — Output the plan (before editing anything)

Print this table, then ask the user to confirm before making any edits:

```
## Query Fix Plan — {filename}

Stack: {detected ORM + database}
Issues found: {N}

| # | Confidence | Severity | Issue | Line | Action |
|---|-----------|----------|-------|------|--------|
| 1 | HIGH       | CRITICAL | Result of .all() not assigned | 90 | AUTO-FIX |
| 2 | HIGH       | HIGH     | Wrong alias in mobile_no filter | 316 | AUTO-FIX |
| 3 | HIGH       | HIGH     | Duplicate payment_status filter block | 396-405 | AUTO-FIX |
| 4 | HIGH       | HIGH     | Unused import: json | 3 | AUTO-FIX |
| 5 | MEDIUM     | MEDIUM   | Unbounded .all() — no limit fallback | 534 | PROMPT |
| 6 | LOW        | LOW      | Manual r_session.close() calls | 543 | SKIP |

AUTO-FIX: will be applied immediately
PROMPT: will ask you before applying
SKIP: flagged only, not touched
```

Then ask:
```
Proceed with AUTO-FIX items? [Y/n] — or type `S <N>` to skip specific findings (e.g. S 2,3):
```

- If user says Y or Enter: apply all HIGH-confidence fixes
- If user says `S 2,3`: skip findings 2 and 3, apply the rest
- If user says N: abort, make no edits

## Step 6 — Apply HIGH-confidence fixes

For each AUTO-FIX item (after user confirms):

1. Read the exact lines from the file
2. Apply the fix using the Edit tool — **use old_string/new_string with the exact current code**
3. After each edit, print:
   ```
   ✓ Fixed #N — {title} ({file}:{line})
   ```
4. If an edit fails (old_string not found): print the error, skip that finding, continue with the rest

## Step 7 — Prompt for MEDIUM-confidence fixes

For each MEDIUM-confidence finding, show:

```
Finding #N — {SEVERITY} · MEDIUM confidence
{file}:{line}

Problem: {one sentence}
Impact: {one sentence}

Current code:
{exact lines from file}

Proposed fix:
{complete replacement}

Apply this fix? [Y/n/s(kip all remaining)]
```

- Y: apply the edit
- N: skip this one
- s: skip all remaining MEDIUM findings

## Step 8 — Print final summary

```
## Fix Summary — {filename}

| # | Confidence | Issue | Line | Result |
|---|-----------|-------|------|--------|
| 1 | HIGH       | Result of .all() not assigned | 90 | ✓ Fixed |
| 2 | HIGH       | Wrong alias in mobile_no filter | 316 | ✓ Fixed |
| 3 | HIGH       | Duplicate payment_status filter block | 396 | ✓ Fixed |
| 4 | HIGH       | Unused import: json | 3 | ✓ Fixed |
| 5 | MEDIUM     | Unbounded .all() | 534 | ✗ Skipped |
| 6 | LOW        | Manual r_session.close() | 543 | — Flagged only |

Applied: 4 fixes | Skipped: 1 | Flagged: 1
```

## Fix rules — CRITICAL, follow exactly

1. **Read before every edit** — always read the current file state before each Edit call; a previous fix may have shifted line numbers
2. **Use exact code** — `old_string` must be the exact text from the file, including indentation
3. **Use the exact session variable** — match whatever is declared at the top of the file (`r_session`, `rr_session`, `session`, etc.)
4. **Use the exact ORM** — match the library already imported, never introduce new dependencies
5. **One edit per finding** — do not batch multiple fixes into one Edit call
6. **Never edit LOW-confidence findings** — flag them in the summary only
7. **Include new imports** if the fix needs them — check what's already imported first
8. **Do not reformat surrounding code** — only change the lines required by the fix