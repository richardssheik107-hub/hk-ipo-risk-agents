"""Run governed PR-F LightGBM models and native SHAP explanations."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from ipo_risk.modeling.lightgbm_modeling import (
    PR_F_MODEL_POLICY_VERSION,
    train_lightgbm_holdout,
)
from ipo_risk.schemas.canonical_modeling import V04CanonicalModelMatrix, canonical_hash


PR_F_VERSION = "v04_pr_f_lightgbm_explainability_v1"


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


def run_pr_f(
    production_matrix_dir: Path,
    oracle_matrix_dir: Path,
    output_dir: Path,
    *,
    pr_e_manifest_path: Path,
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

    results: list[dict[str, Any]] = []
    for cohort, groups, matrices in (
        ("full_production", production_groups, production),
        ("oracle_intersection", oracle_groups, oracle),
    ):
        for group in groups:
            run = train_lightgbm_holdout(
                matrices[(group, "development")],
                matrices[(group, "validation")],
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
        "explainability_method": "lightgbm_native_pred_contrib_shap",
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
    parser.add_argument("--output-dir", type=Path, default=Path("reports/v04_pr_f"))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    result = run_pr_f(
        args.pr_d_dir / "matrices",
        args.oracle_v2_dir / "matrices",
        args.output_dir,
        pr_e_manifest_path=args.pr_e_manifest,
        resume=args.resume,
    )
    print(json.dumps(result["manifest"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
