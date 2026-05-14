# Example: N+1 query pattern
# This file demonstrates what query-review-check-n1 detects.
#
# Problem: fetching 500 applications fires 500 extra queries for payments.
# Run: /query-review-check-n1 examples/n1_bad.py

from sqlalchemy import text
from django.conf import settings

r_session = settings.R_DB_SESSION


def get_applications_with_payments(institute_id: int) -> list:
    applications = r_session.query(Application).filter(
        Application.institute_id == institute_id,
        Application.is_active == 1,
    ).all()

    result = []
    for app in applications:                                          # 1 outer query
        payments = r_session.query(Payment).filter(                  # N queries (1 per app)
            Payment.application_id == app.id,
            Payment.status == "success",
        ).all()
        result.append({
            "application_id": app.id,
            "applicant_name": app.applicant_name,
            "payments": [{"amount": p.amount, "date": p.paid_on} for p in payments],
        })

    return result
    # Total queries: 1 + N (where N = number of applications)
    # At 500 applications → 501 queries