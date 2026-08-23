"""Run governed PR-E baselines and Production/Oracle value diagnostics."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from ipo_risk.modeling.baselines import (
    PR_E_BASELINE_POLICY_VERSION,
    evaluate_development_forward_chaining_baselines,
    evaluate_holdout_baselines,
)
from ipo_risk.modeling.oracle_v2_matrices import (
    ORACLE_V2_MATRIX_MANIFEST_VERSION,
    validate_oracle_v2_freeze,
)
from ipo_risk.schemas.canonical_modeling import V04CanonicalModelMatrix, canonical_hash


PR_E_VERSION = "v04_pr_e_baseline_diagnostic_v1"
PR_D_FREEZE_VERSION = "v04_pr_d_freeze_manifest_v1"
PR_E_COHORT_YEAR_POLICY_VERSION = "v04_official_listing_year_bridge_v1"


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise ValueError(f"missing PR-E input: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid PR-E JSON input: {path}") from exc


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_governed_cohort_years(
    path: Path,
    case_ids: Iterable[str],
) -> tuple[dict[str, int], dict[str, Any]]:
    """Load official listing years for the exact frozen modeling case set."""

    if not path.is_file():
        raise ValueError(f"missing governed cohort-year catalog: {path}")
    expected = set(case_ids)
    resolved: dict[str, int] = {}
    source_years: dict[str, int] = {}
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = csv.DictReader(handle)
            required = {"case_id", "source_year", "official_listed_date"}
            if rows.fieldnames is None or not required.issubset(rows.fieldnames):
                raise ValueError("governed cohort-year catalog has incompatible columns")
            for row in rows:
                case_id = str(row.get("case_id") or "").strip()
                if case_id not in expected:
                    continue
                if case_id in resolved:
                    raise ValueError(f"duplicate governed cohort year for {case_id}")
                listed_date = date.fromisoformat(
                    str(row.get("official_listed_date") or "").strip()
                )
                source_year = int(str(row.get("source_year") or "").strip())
                if listed_date.year not in range(2020, 2025):
                    raise ValueError(f"governed cohort year is outside 2020-2024: {case_id}")
                resolved[case_id] = listed_date.year
                source_years[case_id] = source_year
    except (OSError, csv.Error, TypeError, ValueError) as exc:
        if isinstance(exc, ValueError) and str(exc).startswith(
            ("governed ", "duplicate ")
        ):
            raise
        raise ValueError(f"invalid governed cohort-year catalog: {path}") from exc
    missing = sorted(expected - resolved.keys())
    if missing:
        preview = ", ".join(missing[:5])
        raise ValueError(
            f"governed cohort-year catalog is missing {len(missing)} cases: {preview}"
        )
    entries = [
        {"case_id": case_id, "cohort_year": resolved[case_id]}
        for case_id in sorted(resolved)
    ]
    provenance = {
        "policy_version": PR_E_COHORT_YEAR_POLICY_VERSION,
        "source_filename": path.name,
        "source_sha256": _sha256_file(path),
        "case_count": len(entries),
        "mapping_hash": canonical_hash(entries),
        "cross_year_case_count": sum(
            source_years[case_id] != resolved[case_id] for case_id in resolved
        ),
        "blind_2025_y_accessed": False,
    }
    return resolved, provenance


def _read_matrix(path: Path) -> V04CanonicalModelMatrix:
    try:
        return V04CanonicalModelMatrix.model_validate(_read_json(path))
    except ValueError as exc:
        raise ValueError(f"invalid PR-E matrix: {path}") from exc


def _write(path: Path, payload: Any, *, resume: bool) -> None:
    normalized = json.loads(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    if path.exists():
        if not resume:
            raise ValueError(f"PR-E output exists; use --resume: {path}")
        if json.loads(path.read_text(encoding="utf-8")) != normalized:
            raise ValueError(f"PR-E output conflict: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _matrix_filenames(cohort: str, groups: Iterable[str]) -> tuple[str, ...]:
    return tuple(
        f"{cohort}_{group}_{split}.json"
        for group in groups
        for split in ("development", "validation")
    )


def _verify_runtime_files(
    matrix_dir: Path,
    freeze_manifest: dict[str, Any],
    filenames: Iterable[str],
    *,
    label: str,
) -> dict[str, str]:
    runtime_files = freeze_manifest.get("runtime_files")
    if not isinstance(runtime_files, dict):
        raise ValueError(f"{label} freeze manifest is missing runtime_files")
    verified: dict[str, str] = {}
    for filename in filenames:
        path = matrix_dir / filename
        if not path.is_file():
            raise ValueError(f"missing {label} matrix: {path}")
        expected = runtime_files.get(f"matrices/{filename}")
        if not isinstance(expected, dict) or not expected.get("sha256"):
            raise ValueError(f"{label} freeze manifest does not bind matrices/{filename}")
        actual = _sha256_file(path)
        if actual != expected["sha256"]:
            raise ValueError(f"{label} matrix checksum mismatch: {filename}")
        verified[filename] = actual
    return verified


def _validate_pr_d_freeze(manifest: dict[str, Any]) -> None:
    if manifest.get("manifest_version") != PR_D_FREEZE_VERSION:
        raise ValueError("PR-E requires the frozen PR-D manifest version")
    if manifest.get("status") != "complete_frozen":
        raise ValueError("PR-E requires PR-D status complete_frozen")
    if manifest.get("blind_2025_y_accessed") is not False:
        raise ValueError("PR-E rejects a PR-D input that accessed 2025 Blind y")
    if manifest.get("model_ready_count") != 424:
        raise ValueError("PR-E requires the frozen 424-row PR-D cohort")
    if manifest.get("development_model_ready_count") != 354:
        raise ValueError("PR-E requires the frozen 354-row Development cohort")
    if manifest.get("validation_model_ready_count") != 70:
        raise ValueError("PR-E requires the frozen 70-row Validation cohort")


def _validate_oracle_v2_freeze(manifest: dict[str, Any]) -> None:
    validate_oracle_v2_freeze(manifest)


def _validate_oracle_v2_matrix_manifest(
    manifest: dict[str, Any],
    oracle_freeze: dict[str, Any],
) -> None:
    if manifest.get("manifest_version") != ORACLE_V2_MATRIX_MANIFEST_VERSION:
        raise ValueError("formal PR-E requires the governed Oracle-v2 matrix manifest")
    if manifest.get("status") != "complete_frozen_inputs":
        raise ValueError("formal PR-E requires completed Oracle-v2 matrices")
    if manifest.get("evaluation_only") is not True:
        raise ValueError("Oracle-v2 matrices must remain evaluation_only")
    if manifest.get("production_consumable") is not False:
        raise ValueError("Oracle-v2 matrices cannot become production-consumable")
    if manifest.get("blind_2025_y_accessed") is not False:
        raise ValueError("PR-E rejects Oracle-v2 matrices that accessed 2025 Blind y")
    if manifest.get("oracle_v2_freeze_manifest_hash") != oracle_freeze.get(
        "freeze_manifest_hash"
    ):
        raise ValueError("Oracle-v2 matrices are not bound to the supplied freeze")
    if manifest.get("oracle_v2_artifact_set_hash") != oracle_freeze.get(
        "artifact_set_hash"
    ):
        raise ValueError("Oracle-v2 matrix artifact-set binding drift")
    if manifest.get("development_model_ready_count") != oracle_freeze.get(
        "development_usable_count"
    ):
        raise ValueError("Oracle-v2 matrix Development count drift")
    if manifest.get("validation_model_ready_count") != oracle_freeze.get(
        "validation_usable_count"
    ):
        raise ValueError("Oracle-v2 matrix Validation count drift")
    declared_hash = manifest.get("manifest_hash")
    body = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if declared_hash != canonical_hash(body):
        raise ValueError("Oracle-v2 matrix manifest self-hash mismatch")


def _load_matrix_pairs(
    matrix_dir: Path,
    cohort: str,
    groups: Iterable[str],
) -> dict[str, tuple[V04CanonicalModelMatrix, V04CanonicalModelMatrix]]:
    return {
        group: (
            _read_matrix(matrix_dir / f"{cohort}_{group}_development.json"),
            _read_matrix(matrix_dir / f"{cohort}_{group}_validation.json"),
        )
        for group in groups
    }


def _validate_fair_comparison(
    pairs: dict[str, tuple[V04CanonicalModelMatrix, V04CanonicalModelMatrix]],
) -> None:
    reference_group = next(iter(pairs))
    reference = pairs[reference_group]
    for group, matrices in pairs.items():
        for split_index, split in enumerate(("Development", "Validation")):
            left = reference[split_index]
            right = matrices[split_index]
            fields = {
                "cohort": (left.cohort, right.cohort),
                "dataset_split": (left.dataset_split, right.dataset_split),
                "case_ids": (left.case_ids, right.case_ids),
                "raw_return_5d": (left.raw_return_5d, right.raw_return_5d),
                "poor_performer_5d": (
                    left.poor_performer_5d,
                    right.poor_performer_5d,
                ),
                "target_policy_hash": (
                    left.target_policy_hash,
                    right.target_policy_hash,
                ),
                "target_threshold_hash": (
                    left.target_threshold_hash,
                    right.target_threshold_hash,
                ),
                "source_dataset_hash": (
                    left.source_dataset_hash,
                    right.source_dataset_hash,
                ),
            }
            drift = [name for name, values in fields.items() if values[0] != values[1]]
            if drift:
                raise ValueError(
                    f"unfair {split} comparison for {reference_group}/{group}: "
                    + ", ".join(drift)
                )


def _validate_row_counts(
    pairs: dict[str, tuple[V04CanonicalModelMatrix, V04CanonicalModelMatrix]],
    *,
    expected_development: int,
    expected_validation: int,
    label: str,
) -> None:
    for group, (development, validation) in pairs.items():
        if len(development.case_ids) != expected_development:
            raise ValueError(
                f"{label} {group} Development row count does not match its freeze"
            )
        if len(validation.case_ids) != expected_validation:
            raise ValueError(
                f"{label} {group} Validation row count does not match its freeze"
            )


def _evaluate_pairs(
    pairs: dict[str, tuple[V04CanonicalModelMatrix, V04CanonicalModelMatrix]],
    *,
    cohort_year_by_case: dict[str, int],
) -> list[dict[str, Any]]:
    _validate_fair_comparison(pairs)
    results: list[dict[str, Any]] = []
    for development, validation in pairs.values():
        results.extend(
            item.as_dict()
            for item in evaluate_development_forward_chaining_baselines(
                development, cohort_year_by_case=cohort_year_by_case
            )
        )
        results.extend(
            item.as_dict()
            for item in evaluate_holdout_baselines(
                development,
                validation,
                cohort_year_by_case=cohort_year_by_case,
            )
        )
    return results


def _metric_index(results: list[dict[str, Any]], *, protocol: str):
    return {
        (row["cohort"], row["feature_group"], row["model_family"]): row["metrics"]
        for row in results
        if row["evaluation_protocol"] == protocol
    }


def _delta(
    index: dict[tuple[str, str, str], dict[str, Any]],
    cohort: str,
    left: str,
    right: str,
    metric: str,
) -> float | None:
    left_value = index[(cohort, left, "logistic_regression")][metric]
    right_value = index[(cohort, right, "logistic_regression")][metric]
    if left_value is None or right_value is None:
        return None
    return float(left_value - right_value)


def _metric_delta(
    index: dict[tuple[str, str, str], dict[str, Any]],
    cohort: str,
    left: str,
    right: str,
    model_family: str,
    metric: str,
) -> float | None:
    left_value = index[(cohort, left, model_family)][metric]
    right_value = index[(cohort, right, model_family)][metric]
    if left_value is None or right_value is None:
        return None
    return float(left_value - right_value)


def _regression_increment(
    index: dict[tuple[str, str, str], dict[str, Any]],
    cohort: str,
    left: str,
    right: str,
    model_family: str,
) -> dict[str, float | None]:
    return {
        "mae_reduction": _metric_delta(
            index, cohort, right, left, model_family, "mae"
        ),
        "rmse_reduction": _metric_delta(
            index, cohort, right, left, model_family, "rmse"
        ),
        "r2_gain": _metric_delta(
            index, cohort, left, right, model_family, "r2"
        ),
    }


def _value_diagnostic(
    index: dict[tuple[str, str, str], dict[str, Any]],
    cohort: str,
    *,
    oracle: bool,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "classification": {
            "production_increment_pm_minus_m_roc_auc": _delta(
                index, cohort, "PM", "M", "roc_auc"
            ),
            "production_increment_pm_minus_m_pr_auc": _delta(
                index, cohort, "PM", "M", "pr_auc"
            ),
            "production_increment_m_minus_pm_brier": _delta(
                index, cohort, "M", "PM", "brier_score"
            ),
        },
        "regression": {
            family: {
                "production_increment_pm_vs_m": _regression_increment(
                    index, cohort, "PM", "M", family
                )
            }
            for family in ("linear_regression", "ridge_regression")
        },
    }
    if oracle:
        result["classification"].update(
            {
                "document_signal_ceiling_om_minus_m_roc_auc": _delta(
                    index, cohort, "OM", "M", "roc_auc"
                ),
                "document_signal_ceiling_om_minus_m_pr_auc": _delta(
                    index, cohort, "OM", "M", "pr_auc"
                ),
                "pipeline_gap_om_minus_pm_roc_auc": _delta(
                    index, cohort, "OM", "PM", "roc_auc"
                ),
                "pipeline_gap_om_minus_pm_pr_auc": _delta(
                    index, cohort, "OM", "PM", "pr_auc"
                ),
                "pipeline_gap_pm_minus_om_brier": _delta(
                    index, cohort, "PM", "OM", "brier_score"
                ),
            }
        )
        for family in ("linear_regression", "ridge_regression"):
            result["regression"][family].update(
                {
                    "document_signal_ceiling_om_vs_m": _regression_increment(
                        index, cohort, "OM", "M", family
                    ),
                    "pipeline_gap_om_vs_pm": _regression_increment(
                        index, cohort, "OM", "PM", family
                    ),
                }
            )
    return result


def run_pr_e(
    matrix_dir: Path,
    output_dir: Path,
    *,
    pr_d_freeze_manifest_path: Path,
    oracle_v2_matrix_dir: Path | None = None,
    oracle_v2_freeze_manifest_path: Path | None = None,
    oracle_v2_matrix_manifest_path: Path | None = None,
    cohort_year_catalog_path: Path = Path(
        "data/catalog/ipo_official_master_bridge.csv"
    ),
    allow_production_only: bool = False,
    resume: bool = False,
):
    """Run frozen Production baselines and, when frozen, Oracle v2 diagnostics."""

    pr_d_manifest = _read_json(pr_d_freeze_manifest_path)
    _validate_pr_d_freeze(pr_d_manifest)
    production_groups = ("M", "P", "PM")
    production_files = _matrix_filenames("full_production", production_groups)
    production_hashes = _verify_runtime_files(
        matrix_dir, pr_d_manifest, production_files, label="PR-D"
    )
    production_pairs = _load_matrix_pairs(
        matrix_dir, "full_production", production_groups
    )
    _validate_row_counts(
        production_pairs,
        expected_development=pr_d_manifest["development_model_ready_count"],
        expected_validation=pr_d_manifest["validation_model_ready_count"],
        label="PR-D",
    )
    production_case_ids = {
        case_id
        for pair in production_pairs.values()
        for matrix in pair
        for case_id in matrix.case_ids
    }
    cohort_year_by_case, cohort_year_provenance = _load_governed_cohort_years(
        cohort_year_catalog_path,
        production_case_ids,
    )
    results = _evaluate_pairs(
        production_pairs,
        cohort_year_by_case=cohort_year_by_case,
    )

    oracle_ready = (
        oracle_v2_matrix_dir is not None
        and oracle_v2_freeze_manifest_path is not None
        and oracle_v2_matrix_manifest_path is not None
    )
    oracle_hashes: dict[str, str] = {}
    if oracle_ready:
        oracle_manifest = _read_json(oracle_v2_freeze_manifest_path)
        _validate_oracle_v2_freeze(oracle_manifest)
        oracle_matrix_manifest = _read_json(oracle_v2_matrix_manifest_path)
        _validate_oracle_v2_matrix_manifest(oracle_matrix_manifest, oracle_manifest)
        oracle_groups = ("M", "P", "O", "PM", "OM")
        oracle_files = _matrix_filenames("oracle_intersection", oracle_groups)
        oracle_hashes = _verify_runtime_files(
            oracle_v2_matrix_dir,
            oracle_matrix_manifest,
            oracle_files,
            label="Oracle-v2 matrix",
        )
        oracle_pairs = _load_matrix_pairs(
            oracle_v2_matrix_dir, "oracle_intersection", oracle_groups
        )
        _validate_row_counts(
            oracle_pairs,
            expected_development=oracle_matrix_manifest[
                "development_model_ready_count"
            ],
            expected_validation=oracle_matrix_manifest[
                "validation_model_ready_count"
            ],
            label="Oracle v2",
        )
        results.extend(
            _evaluate_pairs(
                oracle_pairs,
                cohort_year_by_case=cohort_year_by_case,
            )
        )
    elif not allow_production_only:
        raise ValueError(
            "formal PR-E requires frozen Oracle v2 matrices and manifest; "
            "use --allow-production-only only for an explicitly incomplete readiness run"
        )

    holdout = _metric_index(
        results, protocol="development_fit_2024_validation"
    )
    forward = _metric_index(
        results, protocol="development_expanding_year_forward_oof"
    )
    diagnostic: dict[str, Any] = {
        "full_production_validation": _value_diagnostic(
            holdout, "full_production", oracle=False
        ),
        "full_production_development_forward": _value_diagnostic(
            forward, "full_production", oracle=False
        ),
        "oracle_validation": None,
        "oracle_development_forward": None,
        "oracle_status": (
            "frozen_v2_validation" if oracle_ready else "blocked_oracle_v2_not_supplied"
        ),
    }
    if oracle_ready:
        diagnostic["oracle_validation"] = _value_diagnostic(
            holdout, "oracle_intersection", oracle=True
        )
        diagnostic["oracle_development_forward"] = _value_diagnostic(
            forward, "oracle_intersection", oracle=True
        )

    manifest = {
        "pr_e_version": PR_E_VERSION,
        "baseline_policy_version": PR_E_BASELINE_POLICY_VERSION,
        "status": "complete_frozen_inputs" if oracle_ready else "production_readiness_only",
        "formal_gate_passed": oracle_ready,
        "full_production_groups": list(production_groups),
        "oracle_groups": ["M", "P", "O", "PM", "OM"] if oracle_ready else [],
        "oracle_status": diagnostic["oracle_status"],
        "cohort_year_source": cohort_year_provenance,
        "pr_d_freeze_manifest_sha256": _sha256_file(pr_d_freeze_manifest_path),
        "oracle_v2_freeze_manifest_sha256": (
            _sha256_file(oracle_v2_freeze_manifest_path)
            if oracle_v2_freeze_manifest_path is not None
            else None
        ),
        "oracle_v2_matrix_manifest_sha256": (
            _sha256_file(oracle_v2_matrix_manifest_path)
            if oracle_v2_matrix_manifest_path is not None
            else None
        ),
        "production_matrix_hashes": production_hashes,
        "oracle_matrix_hashes": oracle_hashes,
        "result_count": len(results),
        "blind_2025_y_accessed": False,
        "results_hash": canonical_hash(results),
        "diagnostic_hash": canonical_hash(diagnostic),
    }
    _write(output_dir / "baseline_results.json", results, resume=resume)
    _write(output_dir / "value_diagnostic.json", diagnostic, resume=resume)
    _write(output_dir / "run_manifest.json", manifest, resume=resume)
    return {"manifest": manifest, "results": results, "diagnostic": diagnostic}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr-d-dir", type=Path, required=True)
    parser.add_argument(
        "--pr-d-freeze-manifest",
        type=Path,
        default=Path("reports/frozen/v04_pr_d_canonical_dataset_manifest.json"),
    )
    parser.add_argument("--oracle-v2-dir", type=Path)
    parser.add_argument("--oracle-v2-freeze-manifest", type=Path)
    parser.add_argument("--oracle-v2-matrix-manifest", type=Path)
    parser.add_argument(
        "--cohort-year-catalog",
        type=Path,
        default=Path("data/catalog/ipo_official_master_bridge.csv"),
    )
    parser.add_argument("--allow-production-only", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("reports/v04_pr_e"))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    result = run_pr_e(
        args.pr_d_dir / "matrices",
        args.output_dir,
        pr_d_freeze_manifest_path=args.pr_d_freeze_manifest,
        oracle_v2_matrix_dir=(
            args.oracle_v2_dir / "matrices" if args.oracle_v2_dir is not None else None
        ),
        oracle_v2_freeze_manifest_path=args.oracle_v2_freeze_manifest,
        oracle_v2_matrix_manifest_path=(
            args.oracle_v2_matrix_manifest
            if args.oracle_v2_matrix_manifest is not None
            else (
                args.oracle_v2_dir / "run_manifest.json"
                if args.oracle_v2_dir is not None
                else None
            )
        ),
        cohort_year_catalog_path=args.cohort_year_catalog,
        allow_production_only=args.allow_production_only,
        resume=args.resume,
    )
    print(json.dumps(result["manifest"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
