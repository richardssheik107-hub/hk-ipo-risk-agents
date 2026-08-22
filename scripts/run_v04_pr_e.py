"""Run PR-E baselines and the governed Production/Oracle value diagnostic."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ipo_risk.modeling.baselines import (
    PR_E_BASELINE_POLICY_VERSION,
    evaluate_development_cv_baselines,
    evaluate_holdout_baselines,
)
from ipo_risk.schemas.canonical_modeling import V04CanonicalModelMatrix, canonical_hash


PR_E_VERSION = "v04_pr_e_baseline_diagnostic_v1"


def _read_matrix(path: Path) -> V04CanonicalModelMatrix:
    if not path.is_file():
        raise ValueError(f"missing PR-E matrix: {path}")
    return V04CanonicalModelMatrix.model_validate_json(path.read_text(encoding="utf-8"))


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


def _metric_index(results: list[dict[str, Any]], *, protocol: str):
    return {
        (row["feature_group"], row["model_family"]): row["metrics"]
        for row in results
        if row["evaluation_protocol"].startswith(protocol)
    }


def run_pr_e(matrix_dir: Path, output_dir: Path, *, resume: bool = False):
    """Run full Production holdout and Development-only Oracle diagnostics."""

    results: list[dict[str, Any]] = []
    for group in ("M", "P", "PM"):
        development = _read_matrix(
            matrix_dir / f"full_production_{group}_development.json"
        )
        validation = _read_matrix(
            matrix_dir / f"full_production_{group}_validation.json"
        )
        results.extend(
            item.as_dict()
            for item in evaluate_holdout_baselines(development, validation)
        )

    oracle_paths = {
        group: matrix_dir / f"oracle_intersection_{group}_development.json"
        for group in ("M", "P", "O", "PM", "OM")
    }
    oracle_status = "unavailable_no_reviewed_gold"
    if all(path.is_file() for path in oracle_paths.values()):
        oracle_status = "development_cv_only"
        for group, path in oracle_paths.items():
            results.extend(
                item.as_dict()
                for item in evaluate_development_cv_baselines(_read_matrix(path))
            )

    holdout = _metric_index(results, protocol="development_fit_2024_validation")
    oracle_cv = _metric_index(results, protocol="development_stratified_")
    diagnostic = {
        "full_production_validation": {
            "pm_minus_m_roc_auc": (
                holdout[("PM", "logistic_regression")]["roc_auc"]
                - holdout[("M", "logistic_regression")]["roc_auc"]
                if holdout[("PM", "logistic_regression")]["roc_auc"] is not None
                and holdout[("M", "logistic_regression")]["roc_auc"] is not None
                else None
            ),
            "pm_minus_m_pr_auc": (
                holdout[("PM", "logistic_regression")]["pr_auc"]
                - holdout[("M", "logistic_regression")]["pr_auc"]
                if holdout[("PM", "logistic_regression")]["pr_auc"] is not None
                and holdout[("M", "logistic_regression")]["pr_auc"] is not None
                else None
            ),
            "interpretation": "Production Increment = PM - M on untouched 2024 Validation",
        },
        "oracle_development_cv": None,
        "oracle_validation_status": "unavailable_no_reviewed_gold",
    }
    if oracle_cv:
        diagnostic["oracle_development_cv"] = {
            "om_minus_m_roc_auc": (
                oracle_cv[("OM", "logistic_regression")]["roc_auc"]
                - oracle_cv[("M", "logistic_regression")]["roc_auc"]
            ),
            "pm_minus_m_roc_auc": (
                oracle_cv[("PM", "logistic_regression")]["roc_auc"]
                - oracle_cv[("M", "logistic_regression")]["roc_auc"]
            ),
            "om_minus_pm_roc_auc": (
                oracle_cv[("OM", "logistic_regression")]["roc_auc"]
                - oracle_cv[("PM", "logistic_regression")]["roc_auc"]
            ),
            "interpretation": (
                "Development-only OOF diagnostic; not a substitute for 2024 "
                "Oracle Validation"
            ),
        }
    manifest = {
        "pr_e_version": PR_E_VERSION,
        "baseline_policy_version": PR_E_BASELINE_POLICY_VERSION,
        "full_production_groups": ["M", "P", "PM"],
        "oracle_groups": ["M", "P", "O", "PM", "OM"],
        "oracle_status": oracle_status,
        "result_count": len(results),
        "blind_2025_y_accessed": False,
        "results_hash": canonical_hash(results),
    }
    _write(output_dir / "baseline_results.json", results, resume=resume)
    _write(output_dir / "value_diagnostic.json", diagnostic, resume=resume)
    _write(output_dir / "run_manifest.json", manifest, resume=resume)
    return {"manifest": manifest, "results": results, "diagnostic": diagnostic}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr-d-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/v04_pr_e"))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    result = run_pr_e(
        args.pr_d_dir / "matrices", args.output_dir, resume=args.resume
    )
    print(json.dumps(result["manifest"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
