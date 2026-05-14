# Example: N+1 fixed with batch query
# This is the corrected version of n1_bad.py — 2 queries total regardless of result size.

from sqlalchemy import text
from django.conf import settings

r_session = settings.R_DB_SESSION


def get_applications_with_payments(institute_id: int) -> list:
    applications = r_session.query(Application).filter(
        Application.institute_id == institute_id,
        Application.is_active == 1,
    ).all()

    if not applications:
        return []

    # Step 1: collect IDs
    application_ids = [app.id for app in applications]

    # Step 2: single batch query for all payments
    all_payments = r_session.query(Payment).filter(
        Payment.application_id.in_(application_ids),
        Payment.status == "success",
    ).all()

    # Step 3: group payments by application_id for O(1) lookup
    payments_by_app: dict = {}
    for payment in all_payments:
        payments_by_app.setdefault(payment.application_id, []).append(payment)

    # Step 4: build result without any extra queries
    result = []
    for app in applications:
        payments = payments_by_app.get(app.id, [])
        result.append({
            "application_id": app.id,
            "applicant_name": app.applicant_name,
            "payments": [{"amount": p.amount, "date": p.paid_on} for p in payments],
        })

    return result
    # Total queries: always 2 (regardless of N)