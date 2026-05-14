# Sample Tool Output

This shows what query-review produces when run on `n1_bad.py`.

```
/query-review-check-n1 examples/n1_bad.py
```

---

## N+1 Check Results — examples/n1_bad.py

N+1 patterns found: 1

| # | Confidence | Outer query returns | Inner query | Multiplier | File | Line |
|---|-----------|---------------------|-------------|------------|------|------|
| 1 | HIGH | applications (unbounded) | payments per application | 1 per app | n1_bad.py | 21 |

---

### N+1 #1 — Confidence: HIGH
**Application → Payment in loop**
`examples/n1_bad.py:21`

**Confidence explanation**
Query directly visible inside the `for app in applications` loop on line 17. Outer query is unbounded — no LIMIT. Inner query confirmed to hit DB (not cached).

**Problem**
`r_session.query(Payment).filter(Payment.application_id == app.id)` is called once per application inside the loop. With 500 applications this fires 501 DB queries instead of 2.

**Impact**
At 500 applications: 501 queries × ~5ms each = ~2.5s added latency per request. At peak load (50 concurrent users) = 25,050 DB round trips per second.

**Current code** _(exact lines)_
```python
for app in applications:                                          # 1 outer query
    payments = r_session.query(Payment).filter(                  # N queries (1 per app)
        Payment.application_id == app.id,
        Payment.status == "success",
    ).all()
```

**Solution — batch with .in_()**
```python
# Step 1: collect IDs before the loop
application_ids = [app.id for app in applications]

# Step 2: single batch query
all_payments = r_session.query(Payment).filter(
    Payment.application_id.in_(application_ids),
    Payment.status == "success",
).all()

# Step 3: group for O(1) lookup
payments_by_app: dict = {}
for payment in all_payments:
    payments_by_app.setdefault(payment.application_id, []).append(payment)

# Step 4: replace loop body
for app in applications:
    payments = payments_by_app.get(app.id, [])
    result.append({...})
```

**Why this works**
Single `IN()` query replaces N queries — the DB executes one index range scan on `payments(application_id)`.

**Verify**
```bash
# Before fix: enable SQLAlchemy query logging and count queries in one call
# After fix: should log exactly 2 queries (1 for applications, 1 for payments)
EXPLAIN SELECT * FROM payments WHERE application_id IN (1,2,3,...);
# Should show: type=range, key=idx_payments_application_id
```

---

## Recommended Fix Order

Fix these first (HIGH confidence):
1. N+1 #1 — Application → Payment in loop (n1_bad.py:21)

---

> See `n1_fixed.py` for the corrected implementation.