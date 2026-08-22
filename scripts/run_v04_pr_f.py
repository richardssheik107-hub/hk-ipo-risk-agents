"""Run fixed-policy PR-F LightGBM models and native SHAP explanations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.modeling.lightgbm_modeling import (
    PR_F_MODEL_POLICY_VERSION,
    train_lightgbm_development_cv,
    train_lightgbm_holdout,
)
from ipo_risk.schemas.canonical_modeling import V04CanonicalModelMatrix, canonical_hash


PR_F_VERSION = "v04_pr_f_lightgbm_explainability_v1"


def _matrix(path: Path) -> V04CanonicalModelMatrix:
    if not path.is_file():
        raise ValueError(f"missing PR-F matrix: {path}")
    return V04CanonicalModelMatrix.model_validate_json(path.read_text(encoding="utf-8"))


def _write(path: Path, content: str, *, resume: bool) -> None:
    if path.exists():
        if not resume:
            raise ValueError(f"PR-F output exists; use --resume: {path}")
        if path.read_text(encoding="utf-8") != content:
            raise ValueError(f"PR-F output conflict: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run_pr_f(matrix_dir: Path, output_dir: Path, *, resume: bool = False):
    results = []
    models = []
    for group in ("M", "P", "PM"):
        run = train_lightgbm_holdout(
            _matrix(matrix_dir / f"full_production_{group}_development.json"),
            _matrix(matrix_dir / f"full_production_{group}_validation.json"),
        )
        results.append(run.artifact)
        models.append(("full_production", group, run))
    oracle_paths = {
        group: matrix_dir / f"oracle_intersection_{group}_development.json"
        for group in ("M", "P", "O", "PM", "OM")
    }
    oracle_status = "unavailable_no_reviewed_gold"
    if all(path.is_file() for path in oracle_paths.values()):
        oracle_status = "development_cv_only"
        for group, path in oracle_paths.items():
            run = train_lightgbm_development_cv(_matrix(path))
            results.append(run.artifact)
            models.append(("oracle_intersection", group, run))
    for cohort, group, run in models:
        _write(
            output_dir / "models" / f"{cohort}_{group}_classifier.txt",
            run.classifier_model_text,
            resume=resume,
        )
        _write(
            output_dir / "models" / f"{cohort}_{group}_regressor.txt",
            run.regressor_model_text,
            resume=resume,
        )
    rendered = json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    _write(output_dir / "model_results.json", rendered, resume=resume)
    index = {(row["cohort"], row["feature_group"]): row for row in results}
    full_m = index[("full_production", "M")]["classification_metrics"]
    full_pm = index[("full_production", "PM")]["classification_metrics"]
    comparison = {
        "full_production_validation": {
            "pm_minus_m_roc_auc": (
                full_pm["roc_auc"] - full_m["roc_auc"]
                if full_pm["roc_auc"] is not None and full_m["roc_auc"] is not None
                else None
            ),
            "pm_minus_m_pr_auc": (
                full_pm["pr_auc"] - full_m["pr_auc"]
                if full_pm["pr_auc"] is not None and full_m["pr_auc"] is not None
                else None
            ),
        },
        "oracle_development_cv": None,
        "oracle_validation_status": "unavailable_no_reviewed_gold",
    }
    if oracle_status == "development_cv_only":
        oracle_m = index[("oracle_intersection", "M")]["classification_metrics"]
        oracle_pm = index[("oracle_intersection", "PM")]["classification_metrics"]
        oracle_om = index[("oracle_intersection", "OM")]["classification_metrics"]
        comparison["oracle_development_cv"] = {
            "om_minus_m_roc_auc": oracle_om["roc_auc"] - oracle_m["roc_auc"],
            "pm_minus_m_roc_auc": oracle_pm["roc_auc"] - oracle_m["roc_auc"],
            "om_minus_pm_roc_auc": oracle_om["roc_auc"] - oracle_pm["roc_auc"],
            "not_2024_validation": True,
        }
    _write(
        output_dir / "model_comparison.json",
        json.dumps(comparison, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        resume=resume,
    )
    manifest = {
        "pr_f_version": PR_F_VERSION,
        "model_policy_version": PR_F_MODEL_POLICY_VERSION,
        "result_count": len(results),
        "oracle_status": oracle_status,
        "explainability_method": "lightgbm_native_pred_contrib_shap",
        "model_result_hash": canonical_hash(results),
        "blind_2025_y_accessed": False,
    }
    _write(
        output_dir / "run_manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        resume=resume,
    )
    return {"manifest": manifest, "results": results, "comparison": comparison}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr-d-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/v04_pr_f"))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    result = run_pr_f(args.pr_d_dir / "matrices", args.output_dir, resume=args.resume)
    print(json.dumps(result["manifest"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
