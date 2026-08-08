"""Machine-readable validator for the v0.3 golden-case contract."""

from __future__ import annotations

import csv
import re
from pathlib import Path, PurePosixPath

from ipo_risk.domain.risk_codes import V03_ENABLED_RISK_CODES

REQUIRED_COLUMNS = (
    "case_id", "stock_code", "company_name", "document_id", "risk_code",
    "applicable", "gold_page", "exact_text", "expected_status",
    "expected_level", "reviewer", "second_reviewer", "review_status", "notes",
)
STATUSES = {"verified", "needs_review", "rejected"}
LEVELS = {"low", "medium", "high", "critical", "not_applicable"}
REVIEW_STATUSES = {"draft", "first_reviewed", "double_reviewed", "adjudicated"}
# Golden regression may only draw from these splits; the 2025 blind test is barred.
ALLOWED_GOLDEN_SPLITS = {"development", "validation", "development_exception"}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_REAL_CASE_ID_PATTERN = re.compile(r"^ipo_(?P<year>\d{4})_\w+$")


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


def _read_golden_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def _read_prospectus_manifest(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        return {row["case_id"]: row for row in csv.DictReader(source)}


def validate_manifest_integrity(
    path: Path,
    *,
    prospectus_manifest_path: Path | None = None,
    data_root: Path | None = None,
) -> list[str]:
    """Validate the golden manifest as a data catalog, not just per-row fields.

    Runs the per-row annotation contract first, then adds the member #2 data
    checks: case identity consistency, no duplicate judgements, and no 2025
    blind-test leakage. When ``prospectus_manifest_path`` is supplied, every real
    ``ipo_<year>_<code>`` case is cross-checked for a valid SHA-256, an allowed
    dataset split, and (with ``data_root``) an on-disk PDF.
    """
    errors = validate_manifest(path)
    if errors == ["CSV header does not match v03_annotation_v1"]:
        return errors

    rows = _read_golden_rows(path)
    identity: dict[str, tuple[str, str, str]] = {}
    seen_judgements: set[tuple[str, str, str]] = set()
    for line_number, row in enumerate(rows, start=2):
        prefix = f"line {line_number}"
        case_id = row["case_id"].strip()

        # A case_id must always name the same company/security/document.
        current = (row["stock_code"].strip(), row["company_name"].strip(), row["document_id"].strip())
        first = identity.setdefault(case_id, current)
        if current != first:
            errors.append(f"{prefix}: case_id {case_id!r} has inconsistent stock_code/company/document")

        # A (case_id, risk_code, gold_page) judgement must be unique.
        judgement = (case_id, row["risk_code"].strip(), row["gold_page"].strip())
        if judgement in seen_judgements:
            errors.append(
                f"{prefix}: duplicate judgement for {case_id}/{row['risk_code']} on page {row['gold_page']!r}"
            )
        seen_judgements.add(judgement)

        # The 2025 blind test may never enter golden regression.
        match = _REAL_CASE_ID_PATTERN.match(case_id)
        if match and match.group("year") == "2025":
            errors.append(f"{prefix}: 2025 blind-test case {case_id!r} is barred from golden cases")

    if prospectus_manifest_path is not None:
        prospectus = _read_prospectus_manifest(prospectus_manifest_path)
        for case_id in sorted(identity):
            if not _REAL_CASE_ID_PATTERN.match(case_id):
                continue  # synthetic fixtures are not backed by a real prospectus
            record = prospectus.get(case_id)
            if record is None:
                errors.append(f"case {case_id!r}: no prospectus manifest row for cross-check")
                continue
            if record.get("dataset_split") not in ALLOWED_GOLDEN_SPLITS:
                errors.append(
                    f"case {case_id!r}: dataset_split {record.get('dataset_split')!r} not allowed for golden cases"
                )
            if not SHA256_PATTERN.fullmatch(record.get("sha256", "")):
                errors.append(f"case {case_id!r}: prospectus SHA-256 missing or malformed")
            relative_path = record.get("relative_path", "")
            if PurePosixPath(relative_path).is_absolute() or "\\" in relative_path:
                errors.append(f"case {case_id!r}: non-portable prospectus path {relative_path!r}")
            if data_root is not None and relative_path and not (data_root / relative_path).is_file():
                errors.append(f"case {case_id!r}: prospectus PDF missing at {relative_path}")
    return errors
