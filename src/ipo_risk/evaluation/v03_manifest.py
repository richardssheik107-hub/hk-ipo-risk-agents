"""Machine-readable validator for the v0.3 golden-case contract."""

from __future__ import annotations

import csv
from pathlib import Path

from ipo_risk.domain.risk_codes import V03_ENABLED_RISK_CODES

REQUIRED_COLUMNS = (
    "case_id", "stock_code", "company_name", "document_id", "risk_code",
    "applicable", "gold_page", "exact_text", "expected_status",
    "expected_level", "reviewer", "second_reviewer", "review_status", "notes",
)
STATUSES = {"verified", "needs_review", "rejected"}
LEVELS = {"low", "medium", "high", "critical", "not_applicable"}
REVIEW_STATUSES = {"draft", "first_reviewed", "double_reviewed", "adjudicated"}


def validate_manifest(path: Path) -> list[str]:
    errors: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if tuple(reader.fieldnames or ()) != REQUIRED_COLUMNS:
            return ["CSV header does not match v03_annotation_v1"]
        for line_number, row in enumerate(reader, start=2):
            prefix = f"line {line_number}"
            for field in ("case_id", "stock_code", "company_name", "document_id", "reviewer"):
                if not row[field].strip():
                    errors.append(f"{prefix}: {field} is required")
            if row["risk_code"] not in V03_ENABLED_RISK_CODES:
                errors.append(f"{prefix}: unsupported v0.3 risk_code {row['risk_code']!r}")
            if row["applicable"] not in {"true", "false"}:
                errors.append(f"{prefix}: applicable must be true or false")
            if row["expected_status"] not in STATUSES:
                errors.append(f"{prefix}: invalid expected_status")
            if row["expected_level"] not in LEVELS:
                errors.append(f"{prefix}: invalid expected_level")
            if row["review_status"] not in REVIEW_STATUSES:
                errors.append(f"{prefix}: invalid review_status")
            if row["applicable"] == "true":
                try:
                    page = int(row["gold_page"])
                    if page < 1:
                        raise ValueError
                except ValueError:
                    errors.append(f"{prefix}: applicable row requires a positive gold_page")
                if not row["exact_text"].strip():
                    errors.append(f"{prefix}: applicable row requires exact_text")
            elif row["expected_level"] != "not_applicable":
                errors.append(f"{prefix}: non-applicable row must use not_applicable level")
    return errors
