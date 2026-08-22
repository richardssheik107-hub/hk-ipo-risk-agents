"""Materialize the governed PR-C five-session outcome target.

The command reads only the official 2020-2024 cohort. It fits the binary
``poor_performer_5d`` threshold on available 2020-2023 Development labels,
then applies the frozen threshold to Development and 2024 Validation. There is
deliberately no option that can request or expose 2025 Blind outcomes.
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
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Iterable

from ipo_risk.market.eod_store import EXPECTED_OFFICIAL_CASE_COUNT, sha256_file
from ipo_risk.market.labels import MarketLabelGenerator
from ipo_risk.market.outcomes import FiveDayOutcomeBuilder
from ipo_risk.providers.competition_market import CompetitionCSVMarketDataProvider
from ipo_risk.schemas.market import (
    IPOMarketMetadata,
    MarketDatasetSplit,
    MarketLabelAvailability,
    MarketLabelHorizon,
    MarketOutcomeLabel,
)
from ipo_risk.schemas.outcomes import FiveDayOutcomePolicy, FiveDayOutcomeTarget


PR_C_VERSION = "v04_pr_c_5d_outcome_v1"
_HEX_REVISION = re.compile(r"^[0-9a-f]{7,64}$")


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
        raise RuntimeError("PR-C requires an auditable committed git revision")
    return revision


def require_clean_worktree(repo_root: Path) -> None:
    """Refuse formal materialization from uncommitted implementation code."""

    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("PR-C could not verify the git working tree")
    if result.stdout.strip():
        raise RuntimeError(
            "PR-C requires a clean git working tree for reproducible materialization"
        )


def _write_json_conflict_safe(path: Path, payload: Any, *, resume: bool) -> str:
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


def load_official_metadata(
    provider: CompetitionCSVMarketDataProvider,
) -> tuple[IPOMarketMetadata, ...]:
    """Return the full official 2020-2024 target universe and reject Blind."""

    metadata = provider.iter_listing_metadata()
    if len(metadata) != EXPECTED_OFFICIAL_CASE_COUNT:
        raise ValueError(
            "official cohort drift: "
            f"expected {EXPECTED_OFFICIAL_CASE_COUNT}, found {len(metadata)}"
        )
    if any(item.cohort_year >= 2025 for item in metadata):
        raise ValueError("2025 Blind cohort is forbidden in PR-C")
    return metadata


def generate_five_day_labels(
    metadata: Iterable[IPOMarketMetadata],
    provider: CompetitionCSVMarketDataProvider,
) -> tuple[dict[str, MarketOutcomeLabel], list[dict[str, str]]]:
    """Generate one 5D raw label or one visible generation failure per case."""

    generator = MarketLabelGenerator()
    labels: dict[str, MarketOutcomeLabel] = {}
    failures: list[dict[str, str]] = []
    for item in sorted(metadata, key=lambda value: value.case_id):
        if item.cohort_year >= 2025:
            raise ValueError("2025 Blind cohort is forbidden in PR-C")
        try:
            bars = provider.get_daily_bars(item.stock_code)
            generated = generator.generate(item, bars)
            label = next(
                value
                for value in generated
                if value.horizon is MarketLabelHorizon.FIVE_DAYS
            )
            if item.case_id in labels:
                raise ValueError(f"duplicate 5D label: {item.case_id}")
            labels[item.case_id] = label
        except Exception as exc:
            failures.append(
                {
                    "case_id": item.case_id,
                    "stage": "five_day_label_generation",
                    "reason": f"{type(exc).__name__}: {exc}",
                }
            )
    return labels, failures


def _coverage_row(
    *,
    metadata: IPOMarketMetadata,
    target: FiveDayOutcomeTarget | None,
    failure: dict[str, str] | None,
) -> dict[str, Any]:
    return {
        "case_id": metadata.case_id,
        "stock_code": metadata.stock_code,
        "cohort_year": metadata.cohort_year,
        "dataset_split": (
            MarketDatasetSplit.DEVELOPMENT.value
            if metadata.cohort_year <= 2023
            else MarketDatasetSplit.VALIDATION.value
        ),
        "listing_date": metadata.listing_date.isoformat()
        if metadata.listing_date
        else "",
        "target_status": (
            target.availability.value if target is not None else "failed"
        ),
        "target_available": (
            target is not None
            and target.availability is MarketLabelAvailability.AVAILABLE
        ),
        "missing_reason": (
            target.missing_reason.value
            if target is not None and target.missing_reason is not None
            else ""
        ),
        "target_trading_date": (
            target.target_trading_date if target is not None else ""
        ),
        "poor_performer_5d": (
            target.poor_performer_5d
            if target is not None and target.poor_performer_5d is not None
            else ""
        ),
        "target_hash": target.content_hash() if target is not None else "",
        "policy_hash": target.policy_hash if target is not None else "",
        "threshold_hash": target.threshold_hash if target is not None else "",
        "abnormal_return_status": "unavailable_without_governed_benchmark",
        "failure_stage": failure["stage"] if failure else "",
        "failure_reason": failure["reason"] if failure else "",
    }


def _validate_label_identity(
    metadata: IPOMarketMetadata,
    label: MarketOutcomeLabel,
) -> None:
    expected_split = (
        MarketDatasetSplit.DEVELOPMENT
        if metadata.cohort_year <= 2023
        else MarketDatasetSplit.VALIDATION
    )
    pairs = {
        "case_id": (metadata.case_id, label.case_id),
        "stock_code": (metadata.stock_code, label.stock_code),
        "cohort_year": (metadata.cohort_year, label.cohort_year),
        "listing_date": (metadata.listing_date, label.listing_date),
        "dataset_split": (expected_split, label.dataset_split),
        "label_horizon": (MarketLabelHorizon.FIVE_DAYS, label.horizon),
    }
    mismatches = [name for name, (left, right) in pairs.items() if left != right]
    if mismatches:
        raise ValueError(
            f"PR-C metadata/label identity mismatch for {metadata.case_id}: "
            + ", ".join(mismatches)
        )


def materialize_from_labels(
    *,
    metadata: tuple[IPOMarketMetadata, ...],
    labels_by_case: dict[str, MarketOutcomeLabel],
    generation_failures: list[dict[str, str]],
    output_dir: Path,
    source_context: dict[str, Any],
    resume: bool = False,
    verify_determinism: bool = False,
    expected_case_count: int | None = EXPECTED_OFFICIAL_CASE_COUNT,
) -> dict[str, Any]:
    """Pure PR-C materialization boundary used by the real CLI and tests."""

    if expected_case_count is not None and len(metadata) != expected_case_count:
        raise ValueError(
            f"PR-C expected {expected_case_count} metadata rows, found {len(metadata)}"
        )
    case_ids = [item.case_id for item in metadata]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("duplicate official case_id in PR-C metadata")
    if any(item.cohort_year >= 2025 for item in metadata):
        raise ValueError("2025 Blind metadata is forbidden in PR-C")
    metadata_by_case = {item.case_id: item for item in metadata}
    unknown_labels = sorted(set(labels_by_case) - set(case_ids))
    if unknown_labels:
        raise ValueError("labels outside official cohort: " + ", ".join(unknown_labels))
    for key, label in labels_by_case.items():
        if key != label.case_id:
            raise ValueError(f"PR-C label key/case_id mismatch: {key}")
        _validate_label_identity(metadata_by_case[key], label)

    failure_case_ids = [row.get("case_id", "") for row in generation_failures]
    if len(failure_case_ids) != len(set(failure_case_ids)):
        raise ValueError("duplicate PR-C generation failure case_id")
    unknown_failures = sorted(set(failure_case_ids) - set(case_ids))
    if unknown_failures:
        raise ValueError(
            "generation failures outside official cohort: "
            + ", ".join(unknown_failures)
        )
    label_failure_overlap = sorted(set(labels_by_case) & set(failure_case_ids))
    if label_failure_overlap:
        raise ValueError(
            "case cannot have both a label and generation failure: "
            + ", ".join(label_failure_overlap)
        )

    policy = FiveDayOutcomePolicy()
    builder = FiveDayOutcomeBuilder(policy)
    development_labels = [
        label
        for label in labels_by_case.values()
        if label.dataset_split is MarketDatasetSplit.DEVELOPMENT
    ]
    threshold = builder.freeze_threshold(development_labels)
    output_dir.mkdir(parents=True, exist_ok=True)

    policy_payload = {
        "policy": policy.model_dump(mode="json"),
        "policy_hash": policy.content_hash(),
        "threshold": threshold.model_dump(mode="json"),
        "threshold_hash": threshold.content_hash(),
        "threshold_fit_split": "development",
        "validation_used_for_threshold": False,
        "blind_used_for_threshold": False,
    }
    _write_json_conflict_safe(
        output_dir / "frozen_threshold_policy.json",
        policy_payload,
        resume=resume,
    )

    failures_by_case = {
        row["case_id"]: row for row in generation_failures
    }
    targets: dict[str, FiveDayOutcomeTarget] = {}
    coverage: list[dict[str, Any]] = []
    determinism_mismatches: list[str] = []

    for item in sorted(metadata, key=lambda value: value.case_id):
        label = labels_by_case.get(item.case_id)
        target: FiveDayOutcomeTarget | None = None
        failure = failures_by_case.get(item.case_id)
        if label is not None and failure is None:
            try:
                target = builder.build_target(label, threshold)
                targets[item.case_id] = target
                payload = target.model_dump(mode="json") | {
                    "content_hash": target.content_hash()
                }
                _write_json_conflict_safe(
                    output_dir / "targets" / f"{item.case_id}.json",
                    payload,
                    resume=resume,
                )
                if verify_determinism:
                    rebuilt = builder.build_target(label, threshold)
                    if rebuilt != target or rebuilt.content_hash() != target.content_hash():
                        determinism_mismatches.append(item.case_id)
            except Exception as exc:
                failure = {
                    "case_id": item.case_id,
                    "stage": "five_day_target_build",
                    "reason": f"{type(exc).__name__}: {exc}",
                }
                failures_by_case[item.case_id] = failure
        elif label is None and failure is None:
            failure = {
                "case_id": item.case_id,
                "stage": "five_day_label_generation",
                "reason": "MissingLabel: no label or explicit generation failure",
            }
            failures_by_case[item.case_id] = failure
        coverage.append(_coverage_row(metadata=item, target=target, failure=failure))

    coverage.sort(key=lambda row: row["case_id"])
    failures = sorted(failures_by_case.values(), key=lambda row: row["case_id"])
    coverage_hash = _hash(coverage)
    available_by_split = Counter(
        row["dataset_split"]
        for row in coverage
        if row["target_available"] is True
    )
    unavailable_by_split = Counter(
        row["dataset_split"]
        for row in coverage
        if row["target_status"] == MarketLabelAvailability.UNAVAILABLE.value
    )
    poor_by_split = Counter(
        row["dataset_split"]
        for row in coverage
        if row["poor_performer_5d"] is True
    )
    summary = {
        "pr_c_version": PR_C_VERSION,
        "policy_version": policy.version,
        "policy_hash": policy.content_hash(),
        "threshold_method": threshold.method.value,
        "threshold_quantile": str(threshold.quantile),
        "poor_performer_threshold": str(threshold.threshold),
        "threshold_hash": threshold.content_hash(),
        "threshold_fit_split": "development",
        "development_threshold_sample_count": threshold.development_sample_count,
        "official_case_count": len(metadata),
        "coverage_row_count": len(coverage),
        "target_row_count": len(targets),
        "available_count": sum(available_by_split.values()),
        "unavailable_count": sum(unavailable_by_split.values()),
        "failure_count": len(failures),
        "available_by_split": dict(sorted(available_by_split.items())),
        "unavailable_by_split": dict(sorted(unavailable_by_split.items())),
        "poor_performer_by_split": dict(sorted(poor_by_split.items())),
        "coverage_content_hash": coverage_hash,
        "abnormal_return_status": "unavailable_without_governed_benchmark",
        "validation_used_for_threshold": False,
        "blind_2025_y_accessed": False,
        "source_context": source_context,
    }
    _write_json_conflict_safe(
        output_dir / "coverage.json",
        {"summary": summary, "records": coverage},
        resume=resume,
    )
    _write_csv(
        output_dir / "coverage.csv",
        coverage,
        list(coverage[0]) if coverage else [],
    )
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
        "checked_case_count": len(targets) if verify_determinism else 0,
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
                "PR-C deterministic rebuild mismatch: "
                + ", ".join(sorted(determinism_mismatches))
            )

    return {
        "summary": summary,
        "coverage": coverage,
        "failures": failures,
        "targets": targets,
        "reproducibility": reproducibility,
    }


def materialize_pr_c(
    *,
    repo_root: Path,
    catalog_dir: Path,
    data_root: Path,
    output_dir: Path,
    resume: bool = False,
    verify_determinism: bool = False,
    require_clean: bool = True,
) -> dict[str, Any]:
    """Load governed sources and run the formal full-cohort PR-C materialization."""

    if require_clean:
        require_clean_worktree(repo_root)
    revision = _git_revision(repo_root)
    provider = CompetitionCSVMarketDataProvider(data_root, catalog_dir=catalog_dir)
    metadata = load_official_metadata(provider)
    readiness = provider.readiness_report()
    labels_by_case, failures = generate_five_day_labels(metadata, provider)
    bridge_path = catalog_dir / "ipo_official_master_bridge.csv"
    source_context = {
        "git_revision": revision,
        "python_version": platform.python_version(),
        "implementation": platform.python_implementation(),
        "package_versions": _package_versions(),
        "official_bridge_sha256": sha256_file(bridge_path),
        "raw_eod_sha256": readiness.source_sha256,
        "provider_ohlcv_matched": readiness.ohlcv_matched,
        "provider_ohlcv_missing": readiness.ohlcv_missing,
        "provider_5d_horizon_coverage": readiness.horizon_coverage.get("5D", 0),
        "blind_outcomes_included": False,
    }
    return materialize_from_labels(
        metadata=metadata,
        labels_by_case=labels_by_case,
        generation_failures=failures,
        output_dir=output_dir,
        source_context=source_context,
        resume=resume,
        verify_determinism=verify_determinism,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-dir", type=Path, default=Path("data/catalog"))
    parser.add_argument("--data-root", type=Path, default=Path("data/competition"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/v04_pr_c"))
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--verify-determinism", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    result = materialize_pr_c(
        repo_root=repo_root,
        catalog_dir=args.catalog_dir,
        data_root=args.data_root,
        output_dir=args.output_dir,
        resume=args.resume,
        verify_determinism=args.verify_determinism,
    )
    summary = result["summary"]
    print(
        "pr_c_complete=true "
        f"coverage={summary['coverage_row_count']} "
        f"available={summary['available_count']} "
        f"unavailable={summary['unavailable_count']} "
        f"failed={summary['failure_count']} "
        f"threshold={summary['poor_performer_threshold']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
