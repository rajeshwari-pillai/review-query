# Example: SQL injection vulnerabilities
# This file demonstrates what query-review-check-injection detects.
#
# Run: /query-review-check-injection examples/injection_bad.py

from sqlalchemy import text
from django.conf import settings

r_session = settings.R_DB_SESSION


# CRITICAL — user input directly in f-string
def search_applications(applicant_name: str) -> list:
    query = text(f"SELECT * FROM applications WHERE applicant_name = '{applicant_name}'")
    # Attack: applicant_name = "' OR '1'='1" → returns all rows
    # Attack: applicant_name = "'; DROP TABLE applications; --" → destroys table
    return r_session.execute(query).fetchall()


# CRITICAL — string concatenation with request param
def get_by_status(status: str) -> list:
    sql = "SELECT * FROM applications WHERE status = '" + status + "'"
    return r_session.execute(text(sql)).fetchall()


# HIGH — second-order injection: value from DB re-used unsafely
def reprocess_application(application_id: int) -> dict:
    # Fetch stored data (was parameterized on insert — looks safe)
    row = r_session.execute(
        text("SELECT applicant_name FROM applications WHERE id = :id"),
        {"id": application_id}
    ).fetchone()

    # But now the stored value is injected back into a new query — second-order injection
    audit_query = f"SELECT * FROM audit_log WHERE actor = '{row['applicant_name']}'"
    return r_session.execute(text(audit_query)).fetchone()