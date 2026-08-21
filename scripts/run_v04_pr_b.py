"""Canonical PR-B orchestration for Market-X Core + governed IPO EOD store.

PR-B Core intentionally uses the currently governed, high-coverage inputs that
exist today: authoritative IPO metadata, prior-IPO offer facts, and governed IPO
EOD outcomes that were already historical facts before each target listing.
Missing HSI / industry-index / total-market-turnover sources remain explicit
Market-X Extended gaps; this command never fabricates proxies for them.

The CLI is an orchestration layer. Core feature formulas live in
``ipo_risk.market.ipo_market_context_features`` and outcome formulas live in
``MarketLabelGenerator``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import re
import subprocess
from collections import Counter
from decimal import Decimal, InvalidOperation
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Iterable

from ipo_risk.market.ipo_market_context_features import (
    IPO_MARKET_CONTEXT_FEATURE_MANIFEST,
    IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
    IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
    IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,
    IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER,
    build_ipo_market_context,
    content_hash,
    vectorize_ipo_market_context,
)
from ipo_risk.market.labels import MarketLabelGenerator
from ipo_risk.providers.competition_market import CompetitionCSVMarketDataProvider
from ipo_risk.schemas.data_readiness import V04SourceManifest
from ipo_risk.schemas.market import (
    IPOMarketMetadata,
    MarketLabelAvailability,
    MarketLabelHorizon,
)
from scripts.build_v04_ipo_eod_store import (
    EXPECTED_OFFICIAL_CASE_COUNT,
    FILTER_SCHEMA_VERSION,
    build_store,
    sha256_file,
)

PR_B_VERSION = "v04_pr_b_core_v1"
_HEX_REVISION = re.compile(r"^[0-9a-f]{7,64}$")
EXTENDED_SOURCE_IDS = (
    "hsi",
    "industry_mapping",
    "industry_index",
    "market_turnover",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _package_versions() -> dict[str, str]:
    result: dict[str, str] = {}
    for package in ("pydantic",):
        try:
            result[package] = version(package)
        except PackageNotFoundError:
            result[package] = "not-installed"
    return result


def _git_revision(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    revision = result.stdout.strip().lower()
    if result.returncode != 0 or not _HEX_REVISION.fullmatch(revision):
        raise RuntimeError(
            "PR-B requires a git checkout with an auditable committed revision"
        )
    return revision


def require_clean_worktree(repo_root: Path) -> None:
    """Refuse full materialization from uncommitted source code."""

    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("PR-B could not verify the git working tree")
    if result.stdout.strip():
        raise RuntimeError(
            "PR-B requires a clean git working tree for reproducible materialization"
        )


def _parse_decimal(raw: str | None) -> Decimal | None:
    value = (raw or "").replace(",", "").strip()
    if not value:
        return None
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return None
    if not parsed.is_finite():
        return None
    return parsed


def _read_bridge_rows(catalog_dir: Path) -> dict[str, dict[str, str]]:
    path = catalog_dir / "ipo_official_master_bridge.csv"
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_case: dict[str, dict[str, str]] = {}
    for row in rows:
        case_id = (row.get("case_id") or "").strip()
        if not case_id:
            continue
        if case_id in by_case:
            raise ValueError(f"duplicate bridge case_id: {case_id}")
        by_case[case_id] = row
    return by_case


def _load_source_manifest(catalog_dir: Path) -> tuple[V04SourceManifest, Path]:
    path = catalog_dir / "v04_source_manifest.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    manifest = V04SourceManifest.model_validate_json(path.read_text(encoding="utf-8"))
    return manifest, path


def _extended_source_status(manifest: V04SourceManifest) -> dict[str, str]:
    by_id = {entry.logical_id: entry for entry in manifest.entries}
    return {
        logical_id: (
            by_id[logical_id].availability.value
            if logical_id in by_id
            else "missing_manifest_entry"
        )
        for logical_id in EXTENDED_SOURCE_IDS
    }


def load_official_metadata(catalog_dir: Path) -> tuple[IPOMarketMetadata, ...]:
    """Load only authoritative 2020-2024 listing-year metadata."""

    provider = CompetitionCSVMarketDataProvider(Path("."), catalog_dir=catalog_dir)
    metadata = provider.iter_listing_metadata()
    if len(metadata) != EXPECTED_OFFICIAL_CASE_COUNT:
        raise ValueError(
            "official cohort drift: "
            f"expected {EXPECTED_OFFICIAL_CASE_COUNT}, found {len(metadata)}"
        )
    if any(item.cohort_year >= 2025 for item in metadata):
        raise ValueError("2025 blind cohort is forbidden in PR-B")
    return metadata


def select_metadata(
    metadata: Iterable[IPOMarketMetadata],
    *,
    case_ids: list[str] | None = None,
    limit: int | None = None,
) -> tuple[IPOMarketMetadata, ...]:
    ordered = tuple(sorted(metadata, key=lambda item: item.case_id))
    if case_ids:
        requested = list(dict.fromkeys(case_ids))
        by_case = {item.case_id: item for item in ordered}
        unknown = [case_id for case_id in requested if case_id not in by_case]
        if unknown:
            raise ValueError(
                "case ids outside official 2020-2024 cohort: " + ", ".join(unknown)
            )
        ordered = tuple(by_case[case_id] for case_id in requested)
    if limit is not None:
        if limit <= 0:
            raise ValueError("--limit must be positive")
        ordered = ordered[:limit]
    if any(item.cohort_year >= 2025 for item in ordered):
        raise ValueError("2025 blind cohort is forbidden in PR-B")
    return ordered


def _write_json_conflict_safe(
    path: Path,
    payload: Any,
    *,
    resume: bool,
) -> str:
    normalized = json.loads(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    if path.exists():
        if not resume:
            raise ValueError(
                f"artifact already exists; use --resume or a new output root: {path}"
            )
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != normalized:
            raise ValueError(
                f"artifact provenance/content conflict; use a new output root: {path}"
            )
        return "reused"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return "created"


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def build_prior_ipo_records(
    *,
    all_metadata: tuple[IPOMarketMetadata, ...],
    market_provider: CompetitionCSVMarketDataProvider,
    bridge_rows: dict[str, dict[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Build reusable prior-IPO facts and 1D/5D outcomes for PIT context X."""

    generator = MarketLabelGenerator()
    records: list[dict[str, Any]] = []
    label_audit: dict[str, dict[str, Any]] = {}

    for metadata in sorted(
        all_metadata,
        key=lambda item: (item.listing_date, item.case_id),
    ):
        bridge = bridge_rows.get(metadata.case_id, {})
        bars = market_provider.get_daily_bars(metadata.stock_code)
        labels = generator.generate(metadata, bars)
        by_horizon = {label.horizon: label for label in labels}
        one = by_horizon[MarketLabelHorizon.ONE_DAY]
        five = by_horizon[MarketLabelHorizon.FIVE_DAYS]

        records.append(
            {
                "case_id": metadata.case_id,
                "stock_code": metadata.stock_code,
                "listing_date": metadata.listing_date,
                "industry": (bridge.get("official_industry_name") or "").strip()
                or None,
                "funds_raised": _parse_decimal(bridge.get("official_funds_raised")),
                "target_1d": one.target_trading_date,
                "return_1d": one.raw_return,
                "target_5d": five.target_trading_date,
                "return_5d": five.raw_return,
            }
        )
        label_audit[metadata.case_id] = {
            "one_day_available": one.availability is MarketLabelAvailability.AVAILABLE,
            "one_day_missing_reason": (
                one.missing_reason.value if one.missing_reason else ""
            ),
            "five_day_available": five.availability is MarketLabelAvailability.AVAILABLE,
            "five_day_missing_reason": (
                five.missing_reason.value if five.missing_reason else ""
            ),
        }
    return records, label_audit


def build_core_feature_artifact(
    *,
    metadata: IPOMarketMetadata,
    bridge_row: dict[str, str],
    prior_records: list[dict[str, Any]],
    bridge_sha256: str,
    eod_sha256: str,
) -> dict[str, Any]:
    """Build one deterministic, strictly pre-listing Market-X Core artifact."""

    if metadata.listing_date is None:
        raise ValueError("official listing date is required for PR-B core")
    industry = (bridge_row.get("official_industry_name") or "").strip() or None
    values = build_ipo_market_context(
        listing_date=metadata.listing_date,
        industry=industry,
        prior_ipos=prior_records,
    )
    names, vector = vectorize_ipo_market_context(values)
    body: dict[str, Any] = {
        "case_id": metadata.case_id,
        "stock_code": metadata.stock_code,
        "cohort_year": metadata.cohort_year,
        "dataset_split": "development"
        if metadata.cohort_year <= 2023
        else "validation",
        "listing_date": metadata.listing_date.isoformat(),
        "cutoff_semantics": "strictly_before_target_listing_date",
        "core_feature_schema_version": IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,
        "core_feature_policy_version": IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
        "core_feature_manifest_hash": IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
        "feature_names": list(names),
        "feature_values": [
            float(value) if isinstance(value, Decimal) else value for value in vector
        ],
        "raw_values": {
            name: float(value) if isinstance(value, Decimal) else value
            for name, value in values.items()
        },
        "source_provenance": {
            "official_bridge_sha256": bridge_sha256,
            "ipo_eod_sha256": eod_sha256,
        },
    }
    body["content_hash"] = content_hash(body)
    return body


def _coverage_row(
    *,
    metadata: IPOMarketMetadata,
    artifact: dict[str, Any] | None,
    label_audit: dict[str, Any],
    extended_status: dict[str, str],
    failure_stage: str = "",
    failure_reason: str = "",
) -> dict[str, Any]:
    values = artifact.get("raw_values", {}) if artifact else {}
    available = sum(value is not None for value in values.values())
    return {
        "case_id": metadata.case_id,
        "stock_code": metadata.stock_code,
        "cohort_year": metadata.cohort_year,
        "dataset_split": "development"
        if metadata.cohort_year <= 2023
        else "validation",
        "listing_date": metadata.listing_date.isoformat()
        if metadata.listing_date
        else "",
        # Lifecycle details such as created/reused are intentionally excluded so
        # the semantic coverage artifact is stable across a resume rerun.
        "core_market_x_status": "available" if artifact is not None else "failed",
        "core_market_x_available": artifact is not None,
        "available_raw_feature_count": available,
        "missing_raw_feature_count": len(IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER)
        - available,
        "core_feature_hash": artifact.get("content_hash", "") if artifact else "",
        "core_feature_manifest_hash": IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
        "core_feature_policy_version": IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
        "pit_status": "pass" if artifact is not None else "not_run",
        "one_day_outcome_history_available": label_audit.get(
            "one_day_available", False
        ),
        "five_day_outcome_history_available": label_audit.get(
            "five_day_available", False
        ),
        "hsi_extended_source_status": extended_status["hsi"],
        "industry_mapping_extended_source_status": extended_status[
            "industry_mapping"
        ],
        "industry_index_extended_source_status": extended_status["industry_index"],
        "market_turnover_extended_source_status": extended_status[
            "market_turnover"
        ],
        "failure_stage": failure_stage,
        "failure_reason": failure_reason,
    }


def freeze_execution_context(
    *,
    repo_root: Path,
    catalog_dir: Path,
    output_dir: Path,
    selected: tuple[IPOMarketMetadata, ...],
    revision: str,
    eod_manifest: dict[str, Any],
    source_manifest_path: Path,
    extended_status: dict[str, str],
    resume: bool,
) -> dict[str, Any]:
    bridge = catalog_dir / "ipo_official_master_bridge.csv"
    payload = {
        "pr_b_version": PR_B_VERSION,
        "git_revision": revision,
        "python_version": platform.python_version(),
        "implementation": platform.python_implementation(),
        "package_versions": _package_versions(),
        "core_feature_schema_version": IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,
        "core_feature_policy_version": IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
        "core_feature_manifest_hash": IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
        "core_feature_manifest": IPO_MARKET_CONTEXT_FEATURE_MANIFEST,
        "governed_eod_filter_schema_version": FILTER_SCHEMA_VERSION,
        "governed_eod_manifest": eod_manifest,
        "official_bridge_sha256": sha256_file(bridge),
        "source_manifest_sha256": sha256_file(source_manifest_path),
        "extended_source_status": extended_status,
        "selected_case_count": len(selected),
        "selected_case_ids": [item.case_id for item in selected],
        "selected_case_ids_hash": _hash([item.case_id for item in selected]),
        "blind_outcomes_included": False,
        "post_listing_target_data_used_as_target_x": False,
    }
    _write_json_conflict_safe(
        output_dir / "execution_context.json",
        payload,
        resume=resume,
    )
    return payload


def materialize_pr_b(
    *,
    repo_root: Path,
    catalog_dir: Path,
    data_root: Path,
    output_dir: Path,
    case_ids: list[str] | None = None,
    limit: int | None = None,
    resume: bool = False,
    verify_determinism: bool = False,
    require_clean: bool = True,
) -> dict[str, Any]:
    """Materialize governed EOD + one explicit PR-B Core row per target case."""

    if require_clean:
        require_clean_worktree(repo_root)
    revision = _git_revision(repo_root)
    all_metadata = load_official_metadata(catalog_dir)
    selected = select_metadata(all_metadata, case_ids=case_ids, limit=limit)
    bridge_rows = _read_bridge_rows(catalog_dir)
    source_manifest, source_manifest_path = _load_source_manifest(catalog_dir)
    extended_status = _extended_source_status(source_manifest)

    output_dir.mkdir(parents=True, exist_ok=True)
    eod_manifest = build_store(
        data_root=data_root,
        catalog_dir=catalog_dir,
        cache_dir=output_dir / "governed_eod",
        rebuild=False,
    )
    freeze_execution_context(
        repo_root=repo_root,
        catalog_dir=catalog_dir,
        output_dir=output_dir,
        selected=selected,
        revision=revision,
        eod_manifest=eod_manifest,
        source_manifest_path=source_manifest_path,
        extended_status=extended_status,
        resume=resume,
    )

    market_provider = CompetitionCSVMarketDataProvider(
        data_root,
        catalog_dir=catalog_dir,
    )
    readiness = market_provider.readiness_report()
    raw_eod_hash = readiness.source_sha256
    if raw_eod_hash != eod_manifest.get("raw_eod_sha256"):
        raise RuntimeError("governed EOD store hash disagrees with market provider")

    prior_records, labels_by_case = build_prior_ipo_records(
        all_metadata=all_metadata,
        market_provider=market_provider,
        bridge_rows=bridge_rows,
    )

    feature_dir = output_dir / "core_features"
    coverage: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    determinism_mismatches: list[str] = []

    for metadata in selected:
        artifact: dict[str, Any] | None = None
        failure_stage = ""
        failure_reason = ""
        try:
            bridge_row = bridge_rows.get(metadata.case_id)
            if bridge_row is None:
                raise ValueError("official bridge row missing")
            artifact = build_core_feature_artifact(
                metadata=metadata,
                bridge_row=bridge_row,
                prior_records=prior_records,
                bridge_sha256=eod_manifest["bridge_sha256"],
                eod_sha256=raw_eod_hash,
            )
            artifact_path = feature_dir / f"{metadata.case_id}.json"
            _write_json_conflict_safe(
                artifact_path,
                artifact,
                resume=resume,
            )
            if verify_determinism:
                rebuilt = build_core_feature_artifact(
                    metadata=metadata,
                    bridge_row=bridge_row,
                    prior_records=prior_records,
                    bridge_sha256=eod_manifest["bridge_sha256"],
                    eod_sha256=raw_eod_hash,
                )
                if rebuilt != artifact:
                    determinism_mismatches.append(metadata.case_id)
        except Exception as exc:
            failure_stage = "core_feature_build"
            failure_reason = f"{type(exc).__name__}: {exc}"
            failures.append(
                {
                    "case_id": metadata.case_id,
                    "stage": failure_stage,
                    "reason": failure_reason,
                }
            )

        coverage.append(
            _coverage_row(
                metadata=metadata,
                artifact=artifact if not failure_reason else None,
                label_audit=labels_by_case.get(metadata.case_id, {}),
                extended_status=extended_status,
                failure_stage=failure_stage,
                failure_reason=failure_reason,
            )
        )

    coverage.sort(key=lambda row: row["case_id"])
    failures.sort(key=lambda row: row["case_id"])
    coverage_hash = _hash(coverage)
    full_core_count = sum(bool(row["core_market_x_available"]) for row in coverage)
    summary = {
        "pr_b_version": PR_B_VERSION,
        "selected_case_count": len(selected),
        "core_market_x_materialized_count": full_core_count,
        "failed_count": len(failures),
        "failure_count_by_stage": dict(
            sorted(Counter(row["stage"] for row in failures).items())
        ),
        "core_feature_manifest_hash": IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
        "coverage_content_hash": coverage_hash,
        "governed_eod": {
            "target_case_count": eod_manifest.get("target_case_count"),
            "row_count": eod_manifest.get("row_count"),
            "distinct_target_securities": eod_manifest.get(
                "distinct_target_securities"
            ),
            "raw_eod_sha256": raw_eod_hash,
            "provider_ohlcv_matched": readiness.ohlcv_matched,
            "provider_ohlcv_missing": readiness.ohlcv_missing,
        },
        "extended_source_status": extended_status,
        "extended_missing_is_not_core_failure": True,
        "blind_outcomes_included": False,
    }

    coverage_payload = {
        "summary": summary,
        "records": coverage,
    }
    _write_json_conflict_safe(
        output_dir / "coverage.json",
        coverage_payload,
        resume=resume,
    )
    coverage_fields = list(coverage[0]) if coverage else []
    _write_csv(output_dir / "coverage.csv", coverage, coverage_fields)
    _write_csv(
        output_dir / "failure_report.csv",
        failures,
        ["case_id", "stage", "reason"],
    )
    _write_json_conflict_safe(
        output_dir / "run_manifest.json",
        summary,
        resume=resume,
    )

    reproducibility = {
        "verify_determinism_requested": verify_determinism,
        "checked_case_count": len(selected) if verify_determinism else 0,
        "mismatch_count": len(determinism_mismatches),
        "mismatch_case_ids": sorted(determinism_mismatches),
        "passed": verify_determinism and not determinism_mismatches,
        "coverage_content_hash": coverage_hash,
    }
    if verify_determinism:
        _write_json_conflict_safe(
            output_dir / "reproducibility_report.json",
            reproducibility,
            resume=resume,
        )
        if determinism_mismatches:
            raise RuntimeError(
                "PR-B deterministic rebuild mismatch: "
                + ", ".join(sorted(determinism_mismatches))
            )

    return {
        "summary": summary,
        "coverage": coverage,
        "failures": failures,
        "reproducibility": reproducibility,
    }


def _parse_case_ids(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    values = [value.strip() for value in raw.split(",") if value.strip()]
    return values or None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-dir", type=Path, default=Path("data/catalog"))
    parser.add_argument("--data-root", type=Path, default=Path("data/competition"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/v04_pr_b"))
    parser.add_argument("--case-ids", type=str, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--verify-determinism", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    result = materialize_pr_b(
        repo_root=repo_root,
        catalog_dir=args.catalog_dir,
        data_root=args.data_root,
        output_dir=args.output_dir,
        case_ids=_parse_case_ids(args.case_ids),
        limit=args.limit,
        resume=args.resume,
        verify_determinism=args.verify_determinism,
    )
    summary = result["summary"]
    print(
        "pr_b_core_complete=true "
        f"selected={summary['selected_case_count']} "
        f"materialized={summary['core_market_x_materialized_count']} "
        f"failed={summary['failed_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
