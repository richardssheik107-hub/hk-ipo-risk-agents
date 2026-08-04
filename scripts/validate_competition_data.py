"""Validate the generated v0.2 competition-data catalogs."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_competition_manifest import EXPECTED_TOTAL, EXPECTED_YEAR_COUNTS


SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


def read_rows(path: Path) -> list[dict[str, str]]:
    """Read one generated UTF-8 CSV catalog."""
    if not path.is_file():
        raise ValueError(f"missing generated catalog: {path.as_posix()}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def validate(catalog_dir: Path, data_root: Path | None = None) -> list[str]:
    """Return all B1 acceptance failures instead of stopping at the first."""
    errors: list[str] = []
    manifest = read_rows(catalog_dir / "ipo_prospectus_manifest.csv")
    coverage = read_rows(catalog_dir / "eod_coverage_report.csv")
    splits = read_rows(catalog_dir / "dataset_split.csv")
    issues = read_rows(catalog_dir / "data_quality_issues.csv")

    if len(manifest) != EXPECTED_TOTAL:
        errors.append(f"manifest rows: expected {EXPECTED_TOTAL}, got {len(manifest)}")
    year_counts = Counter(int(row["source_year"]) for row in manifest)
    if dict(sorted(year_counts.items())) != EXPECTED_YEAR_COUNTS:
        errors.append(f"year counts: expected {EXPECTED_YEAR_COUNTS}, got {dict(year_counts)}")
    case_ids = [row["case_id"] for row in manifest]
    if len(case_ids) != len(set(case_ids)):
        errors.append("manifest case_id values are not unique")
    raw_codes = [row["stock_code_raw"] for row in manifest]
    if len(raw_codes) != len(set(raw_codes)):
        errors.append("manifest stock_code_raw values are not unique")

    for row in manifest:
        relative_path = row["relative_path"]
        pure_path = PurePosixPath(relative_path)
        if pure_path.is_absolute() or ":" in relative_path or "\\" in relative_path:
            errors.append(f"non-portable relative_path: {relative_path}")
        if not SHA256_PATTERN.fullmatch(row["sha256"]):
            errors.append(f"invalid SHA-256 for {row['case_id']}")
        if row["source_year"] == "2025" and row["dataset_split"] != "blind_test":
            errors.append(f"2025 case escaped blind test: {row['case_id']}")
        if row["parser_status"] not in {"not_run", "pdf_metadata_failed"}:
            errors.append(f"unexpected B1 parser status for {row['case_id']}: {row['parser_status']}")
        if data_root is not None and not (data_root / relative_path).is_file():
            errors.append(f"manifest source file missing: {relative_path}")

    if len(coverage) != EXPECTED_TOTAL:
        errors.append(f"coverage rows: expected {EXPECTED_TOTAL}, got {len(coverage)}")
    available = sum(row["eod_available"] == "true" for row in coverage)
    missing = sum(row["eod_available"] == "false" for row in coverage)
    if (available, missing) != (555, 10):
        errors.append(f"EOD coverage: expected 555/10, got {available}/{missing}")

    if len(splits) != EXPECTED_TOTAL:
        errors.append(f"split rows: expected {EXPECTED_TOTAL}, got {len(splits)}")
    split_counts = Counter(row["dataset_split"] for row in splits)
    expected_splits = {
        "development": 376,
        "validation": 72,
        "development_exception": 1,
        "blind_test": 116,
    }
    if dict(split_counts) != expected_splits:
        errors.append(f"split counts: expected {expected_splits}, got {dict(split_counts)}")
    real_case = [row for row in splits if row["stock_code_raw"] == "02410"]
    if len(real_case) != 1 or real_case[0]["dataset_split"] != "development_exception":
        errors.append("2410.HK is not the single development_exception")
    if any(row["source_year"] == "2025" and row["is_blind_test"] != "true" for row in splits):
        errors.append("one or more 2025 split rows are not marked blind")

    security_issues = [row for row in issues if row["issue_code"] == "SECURITY_MASTER_TRUNCATED"]
    if len(security_issues) != 1 or security_issues[0]["status"] != "quarantined":
        errors.append("truncated security master is not explicitly quarantined")
    eod_missing_issues = [row for row in issues if row["issue_code"] == "EOD_NOT_AVAILABLE"]
    if len(eod_missing_issues) != 10:
        errors.append(f"expected 10 EOD_NOT_AVAILABLE issues, got {len(eod_missing_issues)}")
    if not any(row["issue_code"] == "EOD_AMOUNT_UNIT_UNCONFIRMED" for row in issues):
        errors.append("missing EOD_AMOUNT_UNIT_UNCONFIRMED issue")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-dir", type=Path, default=Path("data/catalog"))
    parser.add_argument("--data-root", type=Path)
    args = parser.parse_args()
    errors = validate(args.catalog_dir, args.data_root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("competition_data_validation=passed")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
