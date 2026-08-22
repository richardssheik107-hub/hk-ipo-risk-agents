"""Build the PR-D Core-first canonical modeling datasets and fair matrices."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from ipo_risk.modeling.canonical_dataset import (
    V04CanonicalDatasetBuilder,
    hash_source_manifests,
    load_target_artifact,
    project_model_matrix,
)
from ipo_risk.schemas.canonical_modeling import (
    V04CanonicalCohort,
    V04ModelFeatureGroup,
    canonical_hash,
)
from ipo_risk.schemas.market import MarketDatasetSplit, MarketLabelAvailability


PR_D_VERSION = "v04_pr_d_canonical_dataset_v1"
PR_C_OFFICIAL_CASE_COUNT = 438
PR_C_AVAILABLE_COUNT = 424
PR_C_UNAVAILABLE_COUNT = 14
PR_C_DEVELOPMENT_AVAILABLE_COUNT = 354
PR_C_VALIDATION_AVAILABLE_COUNT = 70
PR_C_UNAVAILABLE_REASON_COUNTS = {
    "missing_base_price": 12,
    "no_eligible_session": 2,
}


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise ValueError(f"missing PR-D input: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid PR-D JSON input: {path}") from exc


def _write_json(path: Path, payload: Any, *, resume: bool) -> None:
    normalized = json.loads(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    if path.exists():
        if not resume:
            raise ValueError(f"PR-D output exists; use --resume: {path}")
        if _read_json(path) != normalized:
            raise ValueError(f"PR-D output provenance/content conflict: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _validate_upstream_freezes(
    pr_a: dict[str, Any],
    pr_b: dict[str, Any],
    pr_c: dict[str, Any],
) -> None:
    if not (
        pr_a.get("official_case_count") == 438
        and pr_a.get("production_materialized_count") == 438
        and pr_a.get("determinism_passed") is True
        and pr_a.get("blind_2025_accessed") is False
    ):
        raise ValueError("PR-A freeze manifest is not eligible for PR-D")
    if not (
        pr_b.get("status") == "complete_frozen"
        and pr_b.get("official_case_count") == 438
        and pr_b.get("materialized_count") == 438
        and pr_b.get("determinism", {}).get("passed") is True
        and pr_b.get("blind_2025_y_accessed") is False
    ):
        raise ValueError("PR-B freeze manifest is not eligible for PR-D")
    if not (
        pr_c.get("gate_passed") is True
        and pr_c.get("official_case_count") == PR_C_OFFICIAL_CASE_COUNT
        and pr_c.get("available_count") == PR_C_AVAILABLE_COUNT
        and pr_c.get("unavailable_count") == PR_C_UNAVAILABLE_COUNT
        and pr_c.get("failure_count") == 0
        and pr_c.get("determinism_mismatch_count") == 0
        and pr_c.get("validation_used_for_threshold") is False
        and pr_c.get("blind_2025_y_accessed") is False
    ):
        raise ValueError("PR-C formal Gate has not passed")


def materialize_pr_d(
    *,
    production_dir: Path,
    market_core_dir: Path,
    target_dir: Path,
    oracle_dir: Path | None,
    pr_a_manifest_path: Path,
    pr_b_manifest_path: Path,
    pr_c_manifest_path: Path,
    output_dir: Path,
    resume: bool = False,
) -> dict[str, Any]:
    """Materialize canonical datasets after all three upstream freezes pass."""

    pr_a = _read_json(pr_a_manifest_path)
    pr_b = _read_json(pr_b_manifest_path)
    pr_c = _read_json(pr_c_manifest_path)
    _validate_upstream_freezes(pr_a, pr_b, pr_c)
    source_manifest_hash = hash_source_manifests(
        (pr_a_manifest_path, pr_b_manifest_path, pr_c_manifest_path)
    )

    target_paths = sorted(target_dir.glob("*.json"))
    if len(target_paths) != PR_C_OFFICIAL_CASE_COUNT:
        raise ValueError(
            f"PR-D expected {PR_C_OFFICIAL_CASE_COUNT} PR-C targets, "
            f"found {len(target_paths)}"
        )
    builder = V04CanonicalDatasetBuilder()
    records = []
    coverage: list[dict[str, Any]] = []
    policy_hashes: set[str] = set()
    threshold_hashes: set[str] = set()
    for target_path in target_paths:
        target_payload = _read_json(target_path)
        target = load_target_artifact(target_payload)
        policy_hashes.add(target.policy_hash)
        threshold_hashes.add(target.threshold_hash)
        production_path = production_dir / f"{target.case_id}.json"
        market_core_path = market_core_dir / f"{target.case_id}.json"
        if not production_path.is_file() or not market_core_path.is_file():
            raise ValueError(f"PR-D missing frozen X for {target.case_id}")
        oracle_path = oracle_dir / f"{target.case_id}.json" if oracle_dir else None
        oracle = _read_json(oracle_path) if oracle_path and oracle_path.is_file() else None
        if target.availability is MarketLabelAvailability.AVAILABLE:
            record = builder.join_artifacts(
                production=_read_json(production_path),
                market_core=_read_json(market_core_path),
                target_payload=target_payload,
                oracle=oracle,
                source_manifest_hash=source_manifest_hash,
            )
            records.append(record)
            status = "model_ready"
            exclusion_reason = ""
        else:
            status = "excluded"
            exclusion_reason = f"target_unavailable:{target.missing_reason.value}"
        coverage.append(
            {
                "case_id": target.case_id,
                "stock_code": target.stock_code,
                "cohort_year": target.cohort_year,
                "dataset_split": target.dataset_split.value,
                "modeling_status": status,
                "exclusion_reason": exclusion_reason,
                "production_document_available": True,
                "market_core_available": True,
                "market_extended_status": "not_supplied_governed_optional",
                "oracle_document_available": oracle is not None,
                "target_available": (
                    target.availability is MarketLabelAvailability.AVAILABLE
                ),
            }
        )
    if len(policy_hashes) != 1 or len(threshold_hashes) != 1:
        raise ValueError("PR-D target policy/threshold drift across cases")
    if next(iter(policy_hashes)) != pr_c.get("policy_hash"):
        raise ValueError("PR-D targets disagree with PR-C policy manifest")
    if next(iter(threshold_hashes)) != pr_c.get("threshold_hash"):
        raise ValueError("PR-D targets disagree with PR-C threshold manifest")

    available_count = len(records)
    development_available_count = sum(
        row.dataset_split is MarketDatasetSplit.DEVELOPMENT for row in records
    )
    validation_available_count = sum(
        row.dataset_split is MarketDatasetSplit.VALIDATION for row in records
    )
    unavailable_reason_counts = Counter(
        row["exclusion_reason"].removeprefix("target_unavailable:")
        for row in coverage
        if row["target_available"] is False
    )
    if available_count != PR_C_AVAILABLE_COUNT:
        raise ValueError(
            "PR-D target coverage disagrees with frozen PR-C: "
            f"expected {PR_C_AVAILABLE_COUNT} available, found {available_count}"
        )
    if development_available_count != PR_C_DEVELOPMENT_AVAILABLE_COUNT:
        raise ValueError(
            "PR-D Development target coverage disagrees with frozen PR-C: "
            f"expected {PR_C_DEVELOPMENT_AVAILABLE_COUNT}, "
            f"found {development_available_count}"
        )
    if validation_available_count != PR_C_VALIDATION_AVAILABLE_COUNT:
        raise ValueError(
            "PR-D Validation target coverage disagrees with frozen PR-C: "
            f"expected {PR_C_VALIDATION_AVAILABLE_COUNT}, "
            f"found {validation_available_count}"
        )
    if dict(unavailable_reason_counts) != PR_C_UNAVAILABLE_REASON_COUNTS:
        raise ValueError(
            "PR-D unavailable-reason coverage disagrees with frozen PR-C: "
            f"expected {PR_C_UNAVAILABLE_REASON_COUNTS}, "
            f"found {dict(unavailable_reason_counts)}"
        )

    datasets = {}
    matrices = {}
    oracle_split_status: dict[str, str] = {}
    for split in (MarketDatasetSplit.DEVELOPMENT, MarketDatasetSplit.VALIDATION):
        split_records = [row for row in records if row.dataset_split is split]
        full = builder.build(
            split_records,
            cohort=V04CanonicalCohort.FULL_PRODUCTION,
            dataset_split=split,
        )
        datasets[(split.value, "full_production")] = full
        for group in (V04ModelFeatureGroup.M, V04ModelFeatureGroup.P, V04ModelFeatureGroup.PM):
            matrices[(split.value, "full_production", group.value)] = (
                project_model_matrix(full, group)
            )
        oracle_rows = [row for row in split_records if row.oracle_document is not None]
        if oracle_rows:
            oracle = builder.build(
                oracle_rows,
                cohort=V04CanonicalCohort.ORACLE_INTERSECTION,
                dataset_split=split,
            )
            datasets[(split.value, "oracle_intersection")] = oracle
            oracle_split_status[split.value] = "available"
            for group in V04ModelFeatureGroup:
                matrices[(split.value, "oracle_intersection", group.value)] = (
                    project_model_matrix(oracle, group)
                )
        else:
            oracle_split_status[split.value] = "unavailable_no_reviewed_gold"

    for (split, cohort), dataset in datasets.items():
        _write_json(
            output_dir / "datasets" / f"{cohort}_{split}.json",
            dataset.model_dump(mode="json")
            | {"content_hash": dataset.content_hash()},
            resume=resume,
        )
    for (split, cohort, group), matrix in matrices.items():
        _write_json(
            output_dir / "matrices" / f"{cohort}_{group}_{split}.json",
            matrix.model_dump(mode="json"),
            resume=resume,
        )

    coverage.sort(key=lambda row: row["case_id"])
    output_dir.mkdir(parents=True, exist_ok=True)
    coverage_path = output_dir / "coverage.csv"
    if coverage_path.exists() and not resume:
        raise ValueError(f"PR-D output exists; use --resume: {coverage_path}")
    rendered_rows = [
        {key: str(value).lower() if isinstance(value, bool) else value for key, value in row.items()}
        for row in coverage
    ]
    if coverage_path.exists():
        with coverage_path.open("r", encoding="utf-8", newline="") as handle:
            if list(csv.DictReader(handle)) != [
                {key: str(value) for key, value in row.items()} for row in rendered_rows
            ]:
                raise ValueError("PR-D coverage conflict on resume")
    else:
        with coverage_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rendered_rows[0]))
            writer.writeheader()
            writer.writerows(rendered_rows)

    summary = {
        "pr_d_version": PR_D_VERSION,
        "source_manifest_hash": source_manifest_hash,
        "official_case_count": len(coverage),
        "full_production_model_ready_count": len(records),
        "target_unavailable_count": sum(
            row["target_available"] is False for row in coverage
        ),
        "target_unavailable_reason_counts": dict(sorted(unavailable_reason_counts.items())),
        "oracle_intersection_model_ready_count": sum(
            row.oracle_document is not None for row in records
        ),
        "oracle_split_status": oracle_split_status,
        "oracle_development_model_ready_count": sum(
            row.oracle_document is not None
            and row.dataset_split is MarketDatasetSplit.DEVELOPMENT
            for row in records
        ),
        "oracle_validation_model_ready_count": sum(
            row.oracle_document is not None
            and row.dataset_split is MarketDatasetSplit.VALIDATION
            for row in records
        ),
        "development_model_ready_count": development_available_count,
        "validation_model_ready_count": validation_available_count,
        "market_core_feature_count": len(records[0].market_core.feature_names),
        "production_document_feature_count": len(
            records[0].production_document.feature_names
        ),
        "market_extended_status": "not_supplied_governed_optional",
        "feature_groups": [group.value for group in V04ModelFeatureGroup],
        "coverage_hash": canonical_hash(coverage),
        "target_policy_hash": next(iter(policy_hashes)),
        "target_threshold_hash": next(iter(threshold_hashes)),
        "blind_2025_y_accessed": False,
    }
    _write_json(output_dir / "run_manifest.json", summary, resume=resume)
    return {"summary": summary, "coverage": coverage, "datasets": datasets, "matrices": matrices}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr-a-dir", type=Path, required=True)
    parser.add_argument("--pr-b-dir", type=Path, required=True)
    parser.add_argument("--pr-c-dir", type=Path, required=True)
    parser.add_argument("--pr-a-freeze-manifest", type=Path, required=True)
    parser.add_argument("--pr-b-freeze-manifest", type=Path, required=True)
    parser.add_argument("--pr-c-freeze-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/v04_pr_d"))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    result = materialize_pr_d(
        production_dir=args.pr_a_dir / "production_features",
        market_core_dir=args.pr_b_dir / "core_features",
        target_dir=args.pr_c_dir / "targets",
        oracle_dir=args.pr_a_dir / "oracle_features",
        pr_a_manifest_path=args.pr_a_freeze_manifest,
        pr_b_manifest_path=args.pr_b_freeze_manifest,
        pr_c_manifest_path=args.pr_c_freeze_manifest,
        output_dir=args.output_dir,
        resume=args.resume,
    )
    print(json.dumps(result["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
