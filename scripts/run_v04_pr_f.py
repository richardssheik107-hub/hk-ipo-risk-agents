"""Run governed PR-F LightGBM models and native SHAP explanations."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from ipo_risk.modeling.lightgbm_modeling import (
    PR_F_MODEL_POLICY_VERSION,
    train_lightgbm_holdout,
)
from ipo_risk.schemas.canonical_modeling import V04CanonicalModelMatrix, canonical_hash


PR_F_VERSION = "v04_pr_f_lightgbm_explainability_v1"
PR_F_COHORT_YEAR_POLICY_VERSION = "v04_official_listing_year_bridge_v1"
PR_F_BOOTSTRAP_ITERATIONS = 2000


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise ValueError(f"missing PR-F input: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid PR-F JSON input: {path}") from exc


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_governed_cohort_years(
    path: Path,
    case_ids: Iterable[str],
    expected_source: dict[str, Any],
) -> tuple[dict[str, int], dict[str, Any]]:
    """Load and bind the official listing-year map already frozen by PR-E."""

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
                    raise ValueError(
                        f"governed cohort year is outside 2020-2024: {case_id}"
                    )
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
        "policy_version": PR_F_COHORT_YEAR_POLICY_VERSION,
        "source_filename": path.name,
        "source_sha256": _sha256_file(path),
        "case_count": len(entries),
        "mapping_hash": canonical_hash(entries),
        "cross_year_case_count": sum(
            source_years[case_id] != resolved[case_id] for case_id in resolved
        ),
        "blind_2025_y_accessed": False,
    }
    for field in (
        "policy_version",
        "source_sha256",
        "case_count",
        "mapping_hash",
        "cross_year_case_count",
        "blind_2025_y_accessed",
    ):
        if provenance.get(field) != expected_source.get(field):
            raise ValueError(f"PR-F cohort-year source drift: {field}")
    return resolved, provenance


def _matrix(path: Path) -> V04CanonicalModelMatrix:
    try:
        return V04CanonicalModelMatrix.model_validate(_read_json(path))
    except ValueError as exc:
        raise ValueError(f"invalid PR-F matrix: {path}") from exc


def _write_text(path: Path, content: str, *, resume: bool) -> None:
    if path.exists():
        if not resume:
            raise ValueError(f"PR-F output exists; use --resume: {path}")
        if path.read_text(encoding="utf-8") != content:
            raise ValueError(f"PR-F output conflict: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: Any, *, resume: bool) -> None:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    _write_text(path, rendered, resume=resume)


def _validate_pr_e_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("pr_e_version") != "v04_pr_e_baseline_diagnostic_v1":
        raise ValueError("PR-F requires the governed PR-E manifest version")
    if manifest.get("status") != "complete_frozen_inputs":
        raise ValueError("PR-F requires PR-E complete_frozen_inputs")
    if manifest.get("formal_gate_passed") is not True:
        raise ValueError("PR-F requires the formal PR-E Gate")
    if manifest.get("blind_2025_y_accessed") is not False:
        raise ValueError("PR-F rejects PR-E that accessed 2025 Blind y")
    if manifest.get("full_production_groups") != ["M", "P", "PM"]:
        raise ValueError("PR-F requires PR-E M/P/PM Production groups")
    if manifest.get("oracle_groups") != ["M", "P", "O", "PM", "OM"]:
        raise ValueError("PR-F requires PR-E M/P/O/PM/OM Oracle groups")
    if not manifest.get("results_hash") or not manifest.get("diagnostic_hash"):
        raise ValueError("PR-F requires PR-E result and diagnostic hashes")
    cohort_year_source = manifest.get("cohort_year_source")
    if not isinstance(cohort_year_source, dict):
        raise ValueError("PR-F requires the frozen PR-E cohort-year source")
    if cohort_year_source.get("policy_version") != PR_F_COHORT_YEAR_POLICY_VERSION:
        raise ValueError("PR-F requires the governed official listing-year policy")


def _validate_pr_e_artifacts(
    manifest: dict[str, Any], manifest_path: Path
) -> None:
    results = _read_json(manifest_path.parent / "baseline_results.json")
    diagnostic = _read_json(manifest_path.parent / "value_diagnostic.json")
    if canonical_hash(results) != manifest["results_hash"]:
        raise ValueError("PR-E baseline-results hash mismatch")
    if canonical_hash(diagnostic) != manifest["diagnostic_hash"]:
        raise ValueError("PR-E value-diagnostic hash mismatch")


def _verify_matrix_hashes(
    matrix_dir: Path,
    cohort: str,
    groups: Iterable[str],
    expected: dict[str, str],
) -> dict[tuple[str, str], V04CanonicalModelMatrix]:
    matrices: dict[tuple[str, str], V04CanonicalModelMatrix] = {}
    for group in groups:
        for split in ("development", "validation"):
            filename = f"{cohort}_{group}_{split}.json"
            path = matrix_dir / filename
            if not path.is_file():
                raise ValueError(f"missing PR-F matrix: {path}")
            if expected.get(filename) != _sha256_file(path):
                raise ValueError(f"PR-F matrix checksum mismatch: {filename}")
            matrices[(group, split)] = _matrix(path)
    return matrices


def _validate_fair_matrices(
    matrices: dict[tuple[str, str], V04CanonicalModelMatrix],
    groups: tuple[str, ...],
) -> None:
    for split in ("development", "validation"):
        reference = matrices[(groups[0], split)]
        for group in groups[1:]:
            current = matrices[(group, split)]
            for field in (
                "cohort",
                "dataset_split",
                "case_ids",
                "raw_return_5d",
                "poor_performer_5d",
                "target_policy_hash",
                "target_threshold_hash",
                "source_dataset_hash",
            ):
                if getattr(reference, field) != getattr(current, field):
                    raise ValueError(
                        f"unfair PR-F {split} {groups[0]}/{group} matrix: {field}"
                    )


def _metric_delta(
    index: dict[tuple[str, str], dict[str, Any]],
    cohort: str,
    left: str,
    right: str,
    metric_family: str,
    metric: str,
) -> float | None:
    left_value = index[(cohort, left)][metric_family][metric]
    right_value = index[(cohort, right)][metric_family][metric]
    if left_value is None or right_value is None:
        return None
    return float(left_value - right_value)


def _classification_comparison(
    index: dict[tuple[str, str], dict[str, Any]],
    cohort: str,
    left: str,
    right: str,
) -> dict[str, float | None]:
    return {
        "roc_auc_gain": _metric_delta(
            index, cohort, left, right, "classification_metrics", "roc_auc"
        ),
        "pr_auc_gain": _metric_delta(
            index, cohort, left, right, "classification_metrics", "pr_auc"
        ),
        "brier_reduction": _metric_delta(
            index, cohort, right, left, "classification_metrics", "brier_score"
        ),
    }


def _regression_comparison(
    index: dict[tuple[str, str], dict[str, Any]],
    cohort: str,
    left: str,
    right: str,
) -> dict[str, float | None]:
    return {
        "mae_reduction": _metric_delta(
            index, cohort, right, left, "regression_metrics", "mae"
        ),
        "rmse_reduction": _metric_delta(
            index, cohort, right, left, "regression_metrics", "rmse"
        ),
        "r2_gain": _metric_delta(
            index, cohort, left, right, "regression_metrics", "r2"
        ),
    }


def _paired_bootstrap_classification(
    index: dict[tuple[str, str], dict[str, Any]],
    cohort: str,
    left: str,
    right: str,
) -> dict[str, Any]:
    """Estimate paired holdout uncertainty without fitting or tuning a model."""

    left_rows = index[(cohort, left)]["case_predictions"]
    right_rows = index[(cohort, right)]["case_predictions"]
    left_ids = [row["case_id"] for row in left_rows]
    right_ids = [row["case_id"] for row in right_rows]
    if left_ids != right_ids:
        raise ValueError(f"unpaired PR-F bootstrap cases: {cohort} {left}/{right}")
    actual = np.asarray([row["poor_performer_5d"] for row in left_rows], dtype=int)
    right_actual = np.asarray(
        [row["poor_performer_5d"] for row in right_rows], dtype=int
    )
    if not np.array_equal(actual, right_actual):
        raise ValueError(f"unpaired PR-F bootstrap targets: {cohort} {left}/{right}")
    left_score = np.asarray(
        [row["poor_performer_score"] for row in left_rows], dtype=float
    )
    right_score = np.asarray(
        [row["poor_performer_score"] for row in right_rows], dtype=float
    )
    seed_material = f"{cohort}:{left}:{right}:{PR_F_BOOTSTRAP_ITERATIONS}"
    seed = int(hashlib.sha256(seed_material.encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    roc_deltas: list[float] = []
    pr_deltas: list[float] = []
    brier_reductions: list[float] = []
    for _ in range(PR_F_BOOTSTRAP_ITERATIONS):
        sample = rng.integers(0, len(actual), size=len(actual))
        sample_y = actual[sample]
        sample_left = left_score[sample]
        sample_right = right_score[sample]
        brier_reductions.append(
            float(
                brier_score_loss(sample_y, sample_right)
                - brier_score_loss(sample_y, sample_left)
            )
        )
        if len(np.unique(sample_y)) != 2:
            continue
        roc_deltas.append(
            float(
                roc_auc_score(sample_y, sample_left)
                - roc_auc_score(sample_y, sample_right)
            )
        )
        pr_deltas.append(
            float(
                average_precision_score(sample_y, sample_left)
                - average_precision_score(sample_y, sample_right)
            )
        )

    def interval(values: list[float]) -> dict[str, Any]:
        array = np.asarray(values, dtype=float)
        return {
            "valid_iterations": len(values),
            "lower_95": float(np.quantile(array, 0.025)),
            "median": float(np.quantile(array, 0.5)),
            "upper_95": float(np.quantile(array, 0.975)),
        }

    return {
        "method": "paired_nonparametric_bootstrap_2024_validation",
        "iterations": PR_F_BOOTSTRAP_ITERATIONS,
        "random_seed": seed,
        "roc_auc_gain": interval(roc_deltas),
        "pr_auc_gain": interval(pr_deltas),
        "brier_reduction": interval(brier_reductions),
    }


def run_pr_f(
    production_matrix_dir: Path,
    oracle_matrix_dir: Path,
    output_dir: Path,
    *,
    pr_e_manifest_path: Path,
    cohort_year_catalog_path: Path = Path(
        "data/catalog/ipo_official_master_bridge.csv"
    ),
    resume: bool = False,
) -> dict[str, Any]:
    """Train fixed-policy LightGBM models after the formal PR-E Gate passes."""

    pr_e_manifest = _read_json(pr_e_manifest_path)
    _validate_pr_e_manifest(pr_e_manifest)
    _validate_pr_e_artifacts(pr_e_manifest, pr_e_manifest_path)
    production_groups = ("M", "P", "PM")
    oracle_groups = ("M", "P", "O", "PM", "OM")
    production = _verify_matrix_hashes(
        production_matrix_dir,
        "full_production",
        production_groups,
        pr_e_manifest["production_matrix_hashes"],
    )
    oracle = _verify_matrix_hashes(
        oracle_matrix_dir,
        "oracle_intersection",
        oracle_groups,
        pr_e_manifest["oracle_matrix_hashes"],
    )
    _validate_fair_matrices(production, production_groups)
    _validate_fair_matrices(oracle, oracle_groups)
    production_case_ids = {
        case_id for matrix in production.values() for case_id in matrix.case_ids
    }
    cohort_year_by_case, cohort_year_source = _load_governed_cohort_years(
        cohort_year_catalog_path,
        production_case_ids,
        pr_e_manifest["cohort_year_source"],
    )

    results: list[dict[str, Any]] = []
    for cohort, groups, matrices in (
        ("full_production", production_groups, production),
        ("oracle_intersection", oracle_groups, oracle),
    ):
        for group in groups:
            run = train_lightgbm_holdout(
                matrices[(group, "development")],
                matrices[(group, "validation")],
                cohort_year_by_case=cohort_year_by_case,
            )
            results.append(run.artifact)
            _write_text(
                output_dir / "models" / f"{cohort}_{group}_classifier.txt",
                run.classifier_model_text,
                resume=resume,
            )
            _write_text(
                output_dir / "models" / f"{cohort}_{group}_regressor.txt",
                run.regressor_model_text,
                resume=resume,
            )

    index = {(row["cohort"], row["feature_group"]): row for row in results}
    comparison = {
        "evaluation_protocol": "development_fit_2024_validation",
        "full_production": {
            "classification_pm_minus_m": _classification_comparison(
                index, "full_production", "PM", "M"
            ),
            "regression_pm_minus_m": _regression_comparison(
                index, "full_production", "PM", "M"
            ),
        },
        "oracle_intersection": {
            "classification_om_minus_m": _classification_comparison(
                index, "oracle_intersection", "OM", "M"
            ),
            "classification_om_minus_pm": _classification_comparison(
                index, "oracle_intersection", "OM", "PM"
            ),
            "regression_om_minus_m": _regression_comparison(
                index, "oracle_intersection", "OM", "M"
            ),
            "regression_om_minus_pm": _regression_comparison(
                index, "oracle_intersection", "OM", "PM"
            ),
        },
    }
    comparison["component_ablation"] = {
        "full_production_document_addition_pm_minus_m": {
            "classification": comparison["full_production"][
                "classification_pm_minus_m"
            ],
            "regression": comparison["full_production"]["regression_pm_minus_m"],
            "classification_uncertainty": _paired_bootstrap_classification(
                index, "full_production", "PM", "M"
            ),
        },
        "oracle_document_addition_om_minus_m": {
            "classification": comparison["oracle_intersection"][
                "classification_om_minus_m"
            ],
            "regression": comparison["oracle_intersection"][
                "regression_om_minus_m"
            ],
            "classification_uncertainty": _paired_bootstrap_classification(
                index, "oracle_intersection", "OM", "M"
            ),
        },
        "oracle_substitution_om_minus_pm": {
            "classification": comparison["oracle_intersection"][
                "classification_om_minus_pm"
            ],
            "regression": comparison["oracle_intersection"][
                "regression_om_minus_pm"
            ],
            "classification_uncertainty": _paired_bootstrap_classification(
                index, "oracle_intersection", "OM", "PM"
            ),
        },
    }
    comparison["calibration_assessment"] = {
        f"{cohort}_{group}": row["calibration_assessment"]
        for (cohort, group), row in sorted(index.items())
    }
    comparison["error_analysis_summary"] = {
        f"{cohort}_{group}": {
            "false_positive_count": row["error_analysis"]["classification"][
                "false_positive_count"
            ],
            "false_negative_count": row["error_analysis"]["classification"][
                "false_negative_count"
            ],
            "mean_signed_return_error": row["error_analysis"]["regression"][
                "mean_signed_error"
            ],
        }
        for (cohort, group), row in sorted(index.items())
    }
    manifest = {
        "pr_f_version": PR_F_VERSION,
        "model_policy_version": PR_F_MODEL_POLICY_VERSION,
        "status": "complete_frozen_inputs",
        "formal_gate_passed": True,
        "pr_e_manifest_sha256": _sha256_file(pr_e_manifest_path),
        "pr_e_results_hash": pr_e_manifest["results_hash"],
        "pr_e_diagnostic_hash": pr_e_manifest["diagnostic_hash"],
        "result_count": len(results),
        "production_groups": list(production_groups),
        "oracle_groups": list(oracle_groups),
        "evaluation_protocol": "development_fit_2024_validation",
        "cohort_year_source": cohort_year_source,
        "explainability_method": "lightgbm_native_pred_contrib_shap",
        "calibration_status": "assessment_only_uncalibrated",
        "ablation_policy": "paired_component_group_comparison_v1",
        "uncertainty_method": "paired_nonparametric_bootstrap_2000",
        "error_analysis": "deterministic_holdout_top_errors_v1",
        "model_result_hash": canonical_hash(results),
        "comparison_hash": canonical_hash(comparison),
        "blind_2025_y_accessed": False,
    }
    _write_json(output_dir / "model_results.json", results, resume=resume)
    _write_json(output_dir / "model_comparison.json", comparison, resume=resume)
    _write_json(output_dir / "run_manifest.json", manifest, resume=resume)
    return {"manifest": manifest, "results": results, "comparison": comparison}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr-d-dir", type=Path, required=True)
    parser.add_argument("--oracle-v2-dir", type=Path, required=True)
    parser.add_argument("--pr-e-manifest", type=Path, required=True)
    parser.add_argument(
        "--cohort-year-catalog",
        type=Path,
        default=Path("data/catalog/ipo_official_master_bridge.csv"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("reports/v04_pr_f"))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    result = run_pr_f(
        args.pr_d_dir / "matrices",
        args.oracle_v2_dir / "matrices",
        args.output_dir,
        pr_e_manifest_path=args.pr_e_manifest,
        cohort_year_catalog_path=args.cohort_year_catalog,
        resume=args.resume,
    )
    print(json.dumps(result["manifest"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
