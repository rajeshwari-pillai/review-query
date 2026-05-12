<div align="center">

![Query Review Banner](https://img.shields.io/badge/🔍_Query_Review-Universal_DB_Query_Auditor-blue?style=for-the-badge)

# query-review

### Universal DB Query Auditor for All ORMs and Databases

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](../LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/rajeshwari-p/claude-skills/releases)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Compatible-purple.svg)](https://claude.ai/code)
[![Commands](https://img.shields.io/badge/commands-8-orange.svg)](#commands)

**Auto-detects your ORM and database. Finds N+1s, unbounded queries, SQL injection, and missing indexes — before they hit production. Every finding includes a complete solution rated with 3 confidence levels. One command to review, one command to auto-fix.**

[Quick Start](#quick-start) |
[Commands](#commands) |
[Confidence Levels](#confidence-levels) |
[Stack Support](#stack-support) |
[What It Checks](#what-it-checks)

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
cp -r query-review ~/.claude/skills/
```

Or install from repo root:

```bash
curl -sSL https://raw.githubusercontent.com/rajeshwari-p/claude-skills/main/install.sh | bash
```

---

## Commands

8 commands covering all common review scenarios.

| Command | What it does |
|---------|-------------|
| [`file`](#file) | Review all queries in a file |
| [`fix`](#fix) | Review + auto-apply HIGH-confidence fixes, prompt for MEDIUM |
| [`function`](#function) | Deep review of a single function |
| [`scan`](#scan) | Scan an entire app or project |
| [`check-n1`](#check-n1) | Find all N+1 patterns with batch solutions |
| [`check-injection`](#check-injection) | Find SQL injection risks with parameterized fixes |
| [`check-unbounded`](#check-unbounded) | Find missing LIMITs with pagination solutions |
| [`check-timeout`](#check-timeout) | Find queries missing timeout configuration |

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
/query-review-fix direct_payments/helpers/query_helpers/stats_data_helper.py
```

**How it works:**
1. Finds all issues (same as `file` command)
2. Shows a fix plan — `AUTO-FIX` / `PROMPT` / `SKIP` per finding
3. Asks `Proceed? [Y/n]` before touching anything
4. **HIGH confidence** → applied automatically (e.g. `.all()` result not assigned, wrong alias, unused imports)
5. **MEDIUM confidence** → prompts you one-by-one with current code + proposed fix
6. **LOW confidence** → flagged only, never touched
7. Prints a final summary of what was fixed, skipped, or flagged

**Output**: Fix plan → confirmation prompt → edits applied inline → summary table.

---

### `function`

Deep review of a single function — reads the function body, session variables, and imports.

```bash
/query-review-function fetch_custom_form_details in forms/helpers/query_helpers/custom_form_export_helper.py
/query-review-function export_custom_form in forms/helpers/function_helpers/custom_form_export_helper.py
```

**Output**: Function-scoped findings with exact line numbers, confidence-rated solutions, and verify commands.

---

### `scan`

Scan an entire app directory or the full project. Ranks findings by severity + confidence and gives a prioritised fix list.

```bash
/query-review-scan forms/
/query-review-scan payments/
/query-review-scan                    # scan entire project
```

**Output**: Cross-file findings table → per-finding blocks → recommended fix order (CRITICAL+HIGH first).

---

### `check-n1`

Focused N+1 detection. Traces function calls inside loops to confirm indirect N+1s. Provides batch-query solutions.

```bash
/query-review-check-n1 forms/helpers/function_helpers/custom_form_export_helper.py
/query-review-check-n1 payments/
```

**Output**: For each N+1 — impact calculation (e.g. "500 students = 501 queries"), current loop code, batch helper to add, and updated caller loop.

---

### `check-injection`

SQL injection scan. Detects f-strings, string concat, `.format()`, and template literals inside `execute()`, `text()`, `db.Raw()`. Traces value sources to assess exploitability.

```bash
/query-review-check-injection forms/
/query-review-check-injection gqinstitute_backend/utils/
```

**Output**: For each unsafe query — attack scenario example, parameterized replacement, and confidence level based on whether value is user-controlled.

---

### `check-unbounded`

Finds `.all()`, `findMany()`, `find({})` with no `.limit()`. Offers 3 fix options per finding: paginated, hard-capped, or batch-streamed.

```bash
/query-review-check-unbounded forms/helpers/query_helpers/
/query-review-check-unbounded reports/
```

**Output**: For each unbounded query — risk assessment, Solution A (pagination), Solution B (hard cap), Solution C (batch streaming), with a recommendation.

---

### `check-timeout`

Finds complex queries missing timeout configuration. Checks global config first — if found, downgrades individual findings to LOW.

```bash
/query-review-check-timeout forms/helpers/query_helpers/
/query-review-check-timeout gqinstitute_backend/utils/db_config.py
```

**Output**: For each missing timeout — query complexity analysis, Solution A (query-level), Solution B (statement-level), Solution C (global config).

---

## Confidence Levels

Every finding is rated HIGH, MEDIUM, or LOW before a solution is written.

| Level | Meaning | What to do |
|-------|---------|-----------|
| **HIGH** | Issue confirmed by reading the code. Unambiguous. | Apply solution directly |
| **MEDIUM** | Pattern matches but context (caller, config, table size) may change the assessment | Review solution before applying |
| **LOW** | Suspicious pattern but depends on runtime data or call sites | Investigate first, then apply if confirmed |

### How confidence is assigned

**HIGH** when:
- Query is visibly inside a loop (N+1)
- f-string or concat confirmed in `execute()` / `text()` / `db.Raw()` (injection)
- `.all()` with no `.limit()` and function has no limit parameter (unbounded)
- No global timeout found in db_config AND query has 4+ table JOINs (timeout)

**MEDIUM** when:
- Pattern matches but a decorator or framework behaviour might handle it
- Table may be intentionally small (master/lookup tables)
- Global timeout may exist but was not confirmed in this scan

**LOW** when:
- Value source not fully traced (injection)
- Caller always passes a limit even though function doesn't enforce one (unbounded)
- Query is on a known small table (timeout)

---

## Stack Support

### ORMs (auto-detected from imports)

| ORM | Language | Detection |
|-----|----------|-----------|
| SQLAlchemy | Python | `from sqlalchemy` |
| Django ORM | Python | `from django.db` |
| Prisma | TypeScript/JS | `@prisma/client` |
| TypeORM | TypeScript/JS | `@Entity`, `getRepository` |
| Sequelize | TypeScript/JS | `DataTypes` |
| GORM | Go | `gorm.io` |
| Mongoose | Node.js | `mongoose`, `Schema` |
| ActiveRecord | Ruby | `has_many`, `belongs_to` |
| Hibernate | Java | `@Entity`, `EntityManager` |

**Raw SQL:** MySQL · PostgreSQL · SQLite · MSSQL · Oracle

**NoSQL:** MongoDB aggregation pipelines · Redis commands · Elasticsearch DSL

---

## What It Checks

### Universal (all stacks)

| Check | Command |
|-------|---------|
| N+1 query pattern | `check-n1`, `review-file`, `scan` |
| Unbounded query — no LIMIT | `check-unbounded`, `review-file`, `scan` |
| SELECT * / all columns | `review-file`, `scan` |
| SQL injection | `check-injection`, `review-file`, `scan` |
| No query timeout | `check-timeout`, `review-file` |
| Count + fetch anti-pattern | `review-file`, `scan` |
| Fetch full object for one field | `review-file`, `scan` |
| Query inside serializer/property | `review-file`, `scan` |

### ORM-Specific

| ORM | Additional checks |
|-----|-------------------|
| SQLAlchemy | Lazy load in loop, session across threads, duplicate imports, bare column in `and_()`, incomplete `GROUP BY` |
| Django ORM | Missing `select_related`/`prefetch_related`, `.all()` without filter |
| Prisma/TypeORM | `findMany()` without `take`, `await` inside loop |
| GORM | `.Find()` without `.Limit()`, missing `db.Error` check |
| Mongoose | `.find({})` without `.limit()`, `$where` JS eval, missing `.lean()` |
| Redis | `KEYS *` in prod, `SMEMBERS` on large set, `SETNX` without `EXPIRE` |

---

## File Structure

```
query-review/
  SKILL.md          # Core skill — detection rules + solution format
  README.md         # This file
  install.sh        # Install to ~/.claude/skills/query-review/ + commands
  uninstall.sh      # Remove from ~/.claude/skills/
  commands/
    file.md              # /query-review-file   — review all queries in a file
    fix.md               # /query-review-fix    — review + auto-apply fixes
    function.md          # /query-review-function — deep review of one function
    scan.md              # /query-review-scan   — scan entire app or project
    check-n1.md          # /query-review-check-n1
    check-injection.md   # /query-review-check-injection
    check-unbounded.md   # /query-review-check-unbounded
    check-timeout.md     # /query-review-check-timeout
```

---

## License

MIT License — see [LICENSE](../LICENSE) for details.
