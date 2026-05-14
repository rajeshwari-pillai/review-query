<div align="center">

![Query Review Banner](https://img.shields.io/badge/🔍_Query_Review-Universal_DB_Query_Auditor-blue?style=for-the-badge)

# query-review

### Universal DB Query Auditor for All ORMs and Databases

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](https://github.com/rajeshwari-pillai/review-query/releases)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Compatible-purple.svg)](https://claude.ai/code)
[![Commands](https://img.shields.io/badge/commands-10-orange.svg)](#commands)

**Auto-detects your ORM and database. Finds N+1s, unbounded queries, SQL injection, missing indexes, and transaction issues — before they hit production. Every finding includes a complete solution rated with 3 confidence levels. One command to review, one command to auto-fix.**

[Quick Start](#quick-start) |
[Commands](#commands) |
[Confidence Levels](#confidence-levels) |
[Stack Support](#stack-support) |
[What It Checks](#what-it-checks) |
[Examples](#examples)

</div>

---

## Overview

`query-review` audits database queries in any file or function. It detects your stack automatically from imports — no configuration needed. Every finding includes:
- The exact problematic lines from your file
- A complete drop-in solution using your exact ORM and session variables
- A confidence rating so you know whether to apply immediately or investigate first

---

## Quick Start

### Install

```bash
git clone https://github.com/rajeshwari-pillai/review-query.git
cp -r review-query ~/.claude/skills/query-review
```

---

## Commands

10 commands covering all common review scenarios.

| Command | What it does |
|---------|-------------|
| [`file`](#file) | Review all queries in a file |
| [`fix`](#fix) | Review + auto-apply HIGH-confidence fixes, prompt for MEDIUM |
| [`function`](#function) | Deep review of a single function or raw pasted query |
| [`scan`](#scan) | Scan an entire app or project, export report |
| [`check-n1`](#check-n1) | Find all N+1 patterns with batch solutions |
| [`check-injection`](#check-injection) | Find SQL injection risks including second-order injection |
| [`check-unbounded`](#check-unbounded) | Find missing LIMITs with pagination solutions |
| [`check-timeout`](#check-timeout) | Find queries missing timeout configuration |
| [`check-index`](#check-index) | Find missing indexes on filtered, joined, and sorted columns |
| [`explain`](#explain) | Generate and interpret EXPLAIN / EXPLAIN ANALYZE plans |

---

### `file`

Review all database queries in a specific file.

```bash
/query-review-file forms/helpers/query_helpers/custom_form_export_helper.py
/query-review-file payments/helpers/query_helpers/payment_helper.py
```

**Output**: Summary table + per-finding block with current code, solution, and confidence level for every issue found.

---

### `fix`

Review all queries in a file AND automatically apply the fixes — no copy-paste needed.

```bash
/query-review-fix payments/helpers/query_helpers/payment_helper.py
```

**How it works:**
1. Finds all issues (same as `file` command)
2. Shows a fix plan — `AUTO-FIX` / `PROMPT` / `SKIP` per finding
3. Asks `Proceed? [Y/n]` before touching anything
4. **HIGH confidence** → applied automatically
5. **MEDIUM confidence** → prompts you one-by-one with current code + proposed fix
6. **LOW confidence** → flagged only, never touched
7. Prints a final summary of what was fixed, skipped, or flagged

---

### `function`

Deep review of a single function. Also accepts raw SQL or ORM code pasted directly — no file needed. Traces cross-function calls to detect indirect N+1s.

```bash
# File-based
/query-review-function fetch_custom_form_details in forms/helpers/query_helpers/custom_form_export_helper.py

# Raw paste — no file needed
/query-review-function
SELECT u.*, p.* FROM users u
JOIN payments p ON p.user_id = u.id
WHERE u.institute_id = 123
```

---

### `scan`

Scan an entire app directory or the full project. Supports output and threshold flags.

```bash
/query-review-scan forms/
/query-review-scan payments/ --severity-threshold HIGH
/query-review-scan --output audit.md
/query-review-scan
```

**Output**: Cross-file findings ranked by file impact (most issues first) → per-finding blocks → recommended fix order.

---

### `check-n1`

Focused N+1 detection. Covers Django `select_related`/`prefetch_related`, Mongoose `.populate()`, and Celery async N+1 patterns.

```bash
/query-review-check-n1 forms/helpers/function_helpers/custom_form_export_helper.py
/query-review-check-n1 payments/
```

**Output**: For each N+1 — impact calculation (e.g. "500 students = 501 queries"), current loop code, batch helper, and updated caller.

---

### `check-injection`

SQL injection scan. Detects f-strings, string concat, `.format()`, and template literals. Also detects **second-order injection** — where a value stored safely in the DB is later re-used unsafely in a query.

```bash
/query-review-check-injection forms/
/query-review-check-injection gqinstitute_backend/utils/
```

---

### `check-unbounded`

Finds `.all()`, `findMany()`, `find({})` with no `.limit()`. Offers pagination, hard-cap, or batch-streaming fixes.

```bash
/query-review-check-unbounded forms/helpers/query_helpers/
/query-review-check-unbounded reports/
```

---

### `check-timeout`

Finds complex queries missing timeout configuration. Checks global config first — if found, downgrades individual findings to LOW.

```bash
/query-review-check-timeout forms/helpers/query_helpers/
/query-review-check-timeout gqinstitute_backend/utils/db_config.py
```

---

### `check-index`

Detects missing indexes on filtered, joined, sorted, and grouped columns. Generates `CREATE INDEX` statements and Alembic migration snippets. Handles composite index ordering and MySQL vs PostgreSQL syntax.

```bash
/query-review-check-index payments/helpers/query_helpers/payment_helper.py
/query-review-check-index applications/
```

**Output**: For each missing index — the query pattern, `CREATE INDEX` statement, and Alembic `upgrade`/`downgrade` snippet.

---

### `explain`

Generates the exact `EXPLAIN` / `EXPLAIN ANALYZE` SQL to run, then interprets the plan — identifies seq scans, missing indexes, filesort, and bad joins.

```bash
# From a function
/query-review-explain get_applications in payments/helpers/query_helpers/payment_helper.py

# From raw SQL
/query-review-explain
SELECT * FROM applications WHERE institute_id = 123 ORDER BY created_at DESC
```

**Output**: Copy-paste EXPLAIN command → plan interpretation → root cause + fix for each problem node.

---

## Confidence Levels

| Level | Meaning | What to do |
|-------|---------|-----------|
| **HIGH** | Issue confirmed by reading the code. Unambiguous. | Apply solution directly |
| **MEDIUM** | Pattern matches but context may change the assessment | Review before applying |
| **LOW** | Suspicious pattern — depends on runtime data or call sites | Investigate first |

---

## Stack Support

| ORM | Language |
|-----|----------|
| SQLAlchemy | Python |
| Django ORM | Python |
| Prisma | TypeScript/JS |
| TypeORM | TypeScript/JS |
| Sequelize | TypeScript/JS |
| GORM | Go |
| Mongoose | Node.js |
| ActiveRecord | Ruby |
| Hibernate | Java |

**Raw SQL:** MySQL · PostgreSQL · SQLite · MSSQL · Oracle

**NoSQL:** MongoDB · Redis · Elasticsearch

---

## What It Checks

| Check | Command |
|-------|---------|
| N+1 query pattern | `check-n1`, `file`, `scan` |
| Unbounded query — no LIMIT | `check-unbounded`, `file`, `scan` |
| SELECT * / all columns | `file`, `scan` |
| SQL injection (direct + second-order) | `check-injection`, `file`, `scan` |
| No query timeout | `check-timeout`, `file` |
| Missing indexes | `check-index` |
| Execution plan analysis | `explain` |
| Count + fetch anti-pattern | `file`, `scan` |
| INSERT then SELECT (use RETURNING) | `file`, `scan` |
| Query inside serializer/property | `file`, `scan` |

---

## Examples

The `examples/` directory contains annotated before/after code and sample tool output:

| File | What it shows |
|------|--------------|
| `examples/n1_bad.py` | N+1 pattern — 501 queries for 500 rows |
| `examples/n1_fixed.py` | Fixed with batch query — always 2 queries |
| `examples/injection_bad.py` | Direct + second-order SQL injection |
| `examples/unbounded_bad.py` | Unbounded queries + missing index patterns |
| `examples/sample_output.md` | Full example of tool output for `check-n1` |

---

## File Structure

```
query-review/
  SKILL.md              # Core skill — detection rules + solution format
  README.md             # This file
  install.sh            # Install to ~/.claude/skills/query-review/
  uninstall.sh          # Remove from ~/.claude/skills/
  commands/
    file.md             # /query-review-file
    fix.md              # /query-review-fix
    function.md         # /query-review-function
    scan.md             # /query-review-scan
    check-n1.md         # /query-review-check-n1
    check-injection.md  # /query-review-check-injection
    check-unbounded.md  # /query-review-check-unbounded
    check-timeout.md    # /query-review-check-timeout
    check-index.md      # /query-review-check-index
    explain.md          # /query-review-explain
  examples/
    n1_bad.py
    n1_fixed.py
    injection_bad.py
    unbounded_bad.py
    sample_output.md
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.