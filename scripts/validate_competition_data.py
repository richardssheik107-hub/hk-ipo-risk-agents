"""Validate the generated v0.2 competition-data catalogs."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_competition_manifest import (
    EXPECTED_TOTAL,
    EXPECTED_YEAR_COUNTS,
    OFFICIAL_IPO_WORKBOOK_FILENAME,
)


SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
EXPECTED_SHADOW_YEAR_COUNTS = {2020: 5, 2021: 5, 2022: 5, 2023: 4, 2024: 5}


def read_rows(path: Path) -> list[dict[str, str]]:
    """Read one generated UTF-8 CSV catalog."""
    if not path.is_file():
        raise ValueError(f"missing generated catalog: {path.as_posix()}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_shadow_manifest_alignment(
    manifest: list[dict[str, str]],
    shadow_selection: list[dict[str, str]],
) -> list[str]:
    """Validate that every frozen shadow case is traceable to the B1 manifest."""
    errors: list[str] = []
    manifest_by_key = {
        (row["source_year"], row["stock_code_raw"]): row
        for row in manifest
    }

    if len(shadow_selection) != 24:
        errors.append(f"shadow selection rows: expected 24, got {len(shadow_selection)}")
    shadow_year_counts = Counter(int(row["source_year"]) for row in shadow_selection)
    if dict(sorted(shadow_year_counts.items())) != EXPECTED_SHADOW_YEAR_COUNTS:
        errors.append(
            "shadow year counts: "
            f"expected {EXPECTED_SHADOW_YEAR_COUNTS}, got {dict(shadow_year_counts)}"
        )
    if sum(row["manual_review"] == "true" for row in shadow_selection) != 12:
        errors.append("shadow selection must contain exactly 12 manual-review cases")

    seen_keys: set[tuple[str, str]] = set()
    for shadow in shadow_selection:
        key = (shadow["source_year"], shadow["stock_code_raw"])
        if key in seen_keys:
            errors.append(f"duplicate shadow manifest key: {key[0]}/{key[1]}")
            continue
        seen_keys.add(key)
        manifest_row = manifest_by_key.get(key)
        if manifest_row is None:
            errors.append(f"shadow case missing from manifest: {shadow['case_id']}")
            continue
        if shadow["source_filename"] != manifest_row["source_filename"]:
            errors.append(f"shadow filename differs from manifest: {shadow['case_id']}")
        if shadow["stock_code_wind"] != manifest_row["stock_code_wind"]:
            errors.append(f"shadow Wind code differs from manifest: {shadow['case_id']}")
        if PurePosixPath(manifest_row["relative_path"]).name != shadow["source_filename"]:
            errors.append(f"shadow relative path differs from manifest: {shadow['case_id']}")
        if not SHA256_PATTERN.fullmatch(manifest_row["sha256"]):
            errors.append(f"shadow case lacks a valid manifest SHA-256: {shadow['case_id']}")
        if manifest_row["dataset_split"] not in {"development", "validation"}:
            errors.append(
                f"shadow case uses disallowed split {manifest_row['dataset_split']}: "
                f"{shadow['case_id']}"
            )
        if shadow["source_year"] == "2025" or shadow["stock_code_raw"] == "02410":
            errors.append(f"shadow selection contains a frozen exclusion: {shadow['case_id']}")
    return errors


def validate(catalog_dir: Path, data_root: Path | None = None) -> list[str]:
    """Return all B1 acceptance failures instead of stopping at the first."""
    errors: list[str] = []
    manifest = read_rows(catalog_dir / "ipo_prospectus_manifest.csv")
    coverage = read_rows(catalog_dir / "eod_coverage_report.csv")
    splits = read_rows(catalog_dir / "dataset_split.csv")
    official_bridge = read_rows(catalog_dir / "ipo_official_master_bridge.csv")
    issues = read_rows(catalog_dir / "data_quality_issues.csv")
    shadow_selection = read_rows(catalog_dir / "shadow_sample_24.csv")

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

    errors.extend(validate_shadow_manifest_alignment(manifest, shadow_selection))

    if len(coverage) != EXPECTED_TOTAL:
        errors.append(f"coverage rows: expected {EXPECTED_TOTAL}, got {len(coverage)}")
    coverage_by_case = {row["case_id"]: row for row in coverage}
    if len(coverage_by_case) != len(coverage) or set(coverage_by_case) != set(case_ids):
        errors.append("coverage case IDs do not match the manifest")
    for row in manifest:
        coverage_row = coverage_by_case.get(row["case_id"])
        if coverage_row is not None and coverage_row["eod_available"] != row["eod_available"]:
            errors.append(f"coverage availability differs from manifest: {row['case_id']}")
    available = sum(row["eod_available"] == "true" for row in coverage)
    missing = sum(row["eod_available"] == "false" for row in coverage)
    if (available, missing) != (555, 10):
        errors.append(f"EOD coverage: expected 555/10, got {available}/{missing}")

    if len(splits) != EXPECTED_TOTAL:
        errors.append(f"split rows: expected {EXPECTED_TOTAL}, got {len(splits)}")
    splits_by_case = {row["case_id"]: row for row in splits}
    if len(splits_by_case) != len(splits) or set(splits_by_case) != set(case_ids):
        errors.append("split case IDs do not match the manifest")
    for row in manifest:
        split_row = splits_by_case.get(row["case_id"])
        if split_row is not None and split_row["dataset_split"] != row["dataset_split"]:
            errors.append(f"dataset split differs from manifest: {row['case_id']}")
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

    if len(official_bridge) != EXPECTED_TOTAL:
        errors.append(f"official bridge rows: expected {EXPECTED_TOTAL}, got {len(official_bridge)}")
    official_case_ids = [row["case_id"] for row in official_bridge]
    if set(official_case_ids) != set(case_ids) or len(official_case_ids) != len(set(official_case_ids)):
        errors.append("official bridge case IDs do not match the manifest")
    official_status_counts = Counter(row["official_match_status"] for row in official_bridge)
    if dict(official_status_counts) != {"matched": 562, "manifest_only_placeholder": 3}:
        errors.append(f"official bridge status counts unexpected: {dict(official_status_counts)}")
    valid_relations = {
        "not_applicable_unmatched", "not_comparable_missing_listed_date", "no_eod_coverage",
        "eod_starts_on_listed_date", "eod_starts_after_listed_date", "eod_starts_before_listed_date",
    }
    for row in official_bridge:
        if row["source_workbook"] != OFFICIAL_IPO_WORKBOOK_FILENAME:
            errors.append(f"unexpected official source workbook: {row['case_id']}")
        if not SHA256_PATTERN.fullmatch(row["source_workbook_sha256"]):
            errors.append(f"invalid official workbook SHA-256: {row['case_id']}")
        if row["listed_date_eod_relation"] not in valid_relations:
            errors.append(f"invalid listed-date/EOD relation: {row['case_id']}")
        if row["official_match_status"] == "matched" and not row["official_listed_date"]:
            errors.append(f"matched official bridge row lacks listed date: {row['case_id']}")

    security_issues = [row for row in issues if row["issue_code"] == "SECURITY_MASTER_TRUNCATED"]
    if len(security_issues) != 1 or security_issues[0]["status"] != "quarantined":
        errors.append("truncated security master is not explicitly quarantined")
    eod_missing_issues = [row for row in issues if row["issue_code"] == "EOD_NOT_AVAILABLE"]
    if len(eod_missing_issues) != 10:
        errors.append(f"expected 10 EOD_NOT_AVAILABLE issues, got {len(eod_missing_issues)}")
    if not any(row["issue_code"] == "EOD_AMOUNT_UNIT_UNCONFIRMED" for row in issues):
        errors.append("missing EOD_AMOUNT_UNIT_UNCONFIRMED issue")
    official_missing_issues = [row for row in issues if row["issue_code"] == "OFFICIAL_IPO_MASTER_MATCH_MISSING"]
    if len(official_missing_issues) != 3:
        errors.append(f"expected 3 OFFICIAL_IPO_MASTER_MATCH_MISSING issues, got {len(official_missing_issues)}")
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
