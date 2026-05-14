# Example: Unbounded queries and missing indexes
# This file demonstrates what query-review-check-unbounded and check-index detect.
#
# Run: /query-review-check-unbounded examples/unbounded_bad.py
# Run: /query-review-check-index examples/unbounded_bad.py

from sqlalchemy import text, func
from django.conf import settings

r_session = settings.R_DB_SESSION


# UNBOUNDED — .all() with no limit on a large table
def get_all_applications(institute_id: int) -> list:
    return r_session.query(Application).filter(
        Application.institute_id == institute_id,
    ).all()
    # If institute has 50,000 applications → 50,000 rows loaded into memory


# UNBOUNDED + MISSING INDEX — ORDER BY on unindexed column, no LIMIT
def get_recent_payments() -> list:
    return r_session.query(Payment).order_by(
        Payment.created_at.desc()   # no index on created_at → filesort on full table
    ).all()                         # no LIMIT → entire table returned


# MISSING INDEX — JOIN on FK column with no index
def get_applications_with_fees(institute_id: int) -> list:
    return (
        r_session.query(Application, FeeHeader)
        .join(FeeHeader, FeeHeader.application_id == Application.id)
        # payments.application_id has no index → full scan of fee_headers per application
        .filter(Application.institute_id == institute_id)
        .all()
    )


# FIXED versions below ↓

def get_all_applications_paginated(institute_id: int, page: int = 0, page_size: int = 50) -> list:
    return r_session.query(Application).filter(
        Application.institute_id == institute_id,
    ).limit(page_size).offset(page * page_size).all()


def get_recent_payments_paginated(limit: int = 100) -> list:
    # Requires: CREATE INDEX idx_payments_created_at ON payments(created_at DESC)
    return r_session.query(Payment).order_by(
        Payment.created_at.desc()
    ).limit(limit).all()