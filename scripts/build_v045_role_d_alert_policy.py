"""Build a Development-only high-recall policy for frozen PR-F Market scores.

This is a governed operating-policy study, not a rewrite of the frozen PR-F
model.  It reconstructs the existing 30-position Market Core matrix from PR-B
and PR-C artifacts, reproduces the frozen 2024 PR-F scores, selects an alert
budget from 2021-2023 forward-OOF predictions only, and then evaluates that
already-selected policy on 2024 Validation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from ipo_risk.modeling.alert_policy import (
    ROLE_D_ALERT_BETA,
    ROLE_D_ALERT_FRACTIONS,
    ROLE_D_ALERT_POLICY_VERSION,
    evaluate_alert_budget,
    select_development_alert_budget,
)
from ipo_risk.modeling.lightgbm_modeling import build_pr_f_classifier
from ipo_risk.modeling.role_d_v2_candidate import run_role_d_v2_candidate


EXPECTED_DEVELOPMENT_COUNT = 354
EXPECTED_VALIDATION_COUNT = 70
EXPECTED_MARKET_FEATURE_COUNT = 30
SCORE_REPRODUCTION_TOLERANCE = 1e-12


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise ValueError(f"missing Role-D alert-policy input: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid Role-D alert-policy JSON: {path}") from exc


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_market_rows(
    market_core_dir: Path,
    target_dir: Path,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    feature_names: tuple[str, ...] | None = None
    feature_manifest_hash: str | None = None
    for target_path in sorted(target_dir.glob("*.json")):
        target = _read_json(target_path)
        if target.get("availability") != "available":
            continue
        case_id = str(target.get("case_id") or "")
        market = _read_json(market_core_dir / f"{case_id}.json")
        pairs = {
            "case_id": (case_id, market.get("case_id")),
            "cohort_year": (target.get("cohort_year"), market.get("cohort_year")),
            "dataset_split": (
                target.get("dataset_split"),
                market.get("dataset_split"),
            ),
            "listing_date": (target.get("listing_date"), market.get("listing_date")),
        }
        mismatches = [name for name, pair in pairs.items() if pair[0] != pair[1]]
        if mismatches:
            raise ValueError(
                f"Role-D alert-policy identity mismatch for {case_id}: "
                + ", ".join(mismatches)
            )
        names = tuple(market.get("feature_names") or ())
        values = tuple(market.get("feature_values") or ())
        if len(names) != EXPECTED_MARKET_FEATURE_COUNT or len(values) != len(names):
            raise ValueError(f"invalid Market Core vector for {case_id}")
        manifest_hash = str(market.get("core_feature_manifest_hash") or "")
        if feature_names is None:
            feature_names = names
            feature_manifest_hash = manifest_hash
        elif names != feature_names or manifest_hash != feature_manifest_hash:
            raise ValueError("Role-D alert-policy Market Core manifest drift")
        rows.append(
            {
                "case_id": case_id,
                "cohort_year": int(target["cohort_year"]),
                "feature_values": [
                    np.nan if value is None else float(value) for value in values
                ],
                "label": bool(target["poor_performer_5d"]),
                "raw_return_5d": float(target["raw_return_5d"]),
            }
        )
    rows.sort(key=lambda row: row["case_id"])
    if len({row["case_id"] for row in rows}) != len(rows):
        raise ValueError("Role-D alert-policy case IDs must be unique")
    if any(row["cohort_year"] >= 2025 for row in rows):
        raise ValueError("Role-D alert-policy refuses 2025 Blind y")
    development = [row for row in rows if row["cohort_year"] <= 2023]
    validation = [row for row in rows if row["cohort_year"] == 2024]
    if len(development) != EXPECTED_DEVELOPMENT_COUNT:
        raise ValueError("Role-D alert-policy Development coverage drift")
    if len(validation) != EXPECTED_VALIDATION_COUNT:
        raise ValueError("Role-D alert-policy Validation coverage drift")
    return {
        "rows": rows,
        "development": development,
        "validation": validation,
        "feature_names": feature_names,
        "feature_manifest_hash": feature_manifest_hash,
    }


def _arrays(rows: list[dict[str, Any]]) -> tuple[list[str], np.ndarray, np.ndarray]:
    return (
        [row["case_id"] for row in rows],
        np.asarray([row["feature_values"] for row in rows], dtype=float),
        np.asarray([row["label"] for row in rows], dtype=int),
    )


def _development_forward_oof(
    development: list[dict[str, Any]],
) -> tuple[list[str], np.ndarray, np.ndarray, list[dict[str, Any]]]:
    case_ids, x, y = _arrays(development)
    years = np.asarray([row["cohort_year"] for row in development], dtype=int)
    scores = np.full(len(development), np.nan, dtype=float)
    fold_audit: list[dict[str, Any]] = []
    for evaluation_year in (2021, 2022, 2023):
        train = years < evaluation_year
        evaluate = years == evaluation_year
        model = build_pr_f_classifier()
        model.fit(x[train], y[train])
        scores[evaluate] = np.asarray(
            model.booster_.predict(x[evaluate]), dtype=float
        )
        fold_audit.append(
            {
                "train_years": sorted(set(int(value) for value in years[train])),
                "evaluation_years": [evaluation_year],
                "train_count": int(train.sum()),
                "evaluation_count": int(evaluate.sum()),
            }
        )
    available = np.isfinite(scores)
    if int(available.sum()) != 237:
        raise ValueError("Role-D alert-policy forward-OOF coverage drift")
    return (
        [case_ids[index] for index in np.flatnonzero(available)],
        y[available],
        scores[available],
        fold_audit,
    )


def _frozen_market_result(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    matches = [
        row
        for row in payload
        if row.get("cohort") == "full_production"
        and row.get("feature_group") == "M"
        and row.get("evaluation_protocol") == "development_fit_2024_validation"
    ]
    if len(matches) != 1:
        raise ValueError("Role-D alert-policy requires one frozen PR-F M result")
    result = matches[0]
    if result.get("blind_2025_y_accessed") is not False:
        raise ValueError("Role-D alert-policy rejects PR-F Blind access")
    return result


def build_alert_policy(
    *,
    market_core_dir: Path,
    target_dir: Path,
    pr_f_results_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    data = _load_market_rows(market_core_dir, target_dir)
    development = data["development"]
    validation = data["validation"]
    oof_ids, oof_y, oof_scores, fold_audit = _development_forward_oof(development)
    selected = select_development_alert_budget(oof_ids, oof_y, oof_scores)

    dev_ids, dev_x, dev_y = _arrays(development)
    valid_ids, valid_x, valid_y = _arrays(validation)
    model = build_pr_f_classifier()
    model.fit(dev_x, dev_y)
    reproduced_scores = np.asarray(model.booster_.predict(valid_x), dtype=float)

    frozen = _frozen_market_result(pr_f_results_path)
    frozen_by_case = {
        row["case_id"]: row for row in frozen.get("case_predictions") or []
    }
    if set(frozen_by_case) != set(valid_ids):
        raise ValueError("Role-D alert-policy frozen PR-F case coverage drift")
    frozen_scores = np.asarray(
        [frozen_by_case[case_id]["poor_performer_score"] for case_id in valid_ids],
        dtype=float,
    )
    max_score_difference = float(np.max(np.abs(reproduced_scores - frozen_scores)))
    if max_score_difference > SCORE_REPRODUCTION_TOLERANCE:
        raise ValueError("Role-D alert-policy could not reproduce frozen PR-F scores")
    frozen_labels = np.asarray(
        [frozen_by_case[case_id]["poor_performer_5d"] for case_id in valid_ids],
        dtype=int,
    )
    if not np.array_equal(valid_y, frozen_labels):
        raise ValueError("Role-D alert-policy target labels disagree with frozen PR-F")

    predicted, policy_metrics = evaluate_alert_budget(
        valid_ids, valid_y, frozen_scores, selected.fraction
    )
    fixed_metrics = dict(frozen["classification_metrics"])
    fixed_predicted = frozen_scores >= float(fixed_metrics["classification_threshold"])
    rows = []
    for index, case_id in enumerate(valid_ids):
        rows.append(
            {
                "case_id": case_id,
                "cohort_year": 2024,
                "actual_significant_drop_5d": bool(valid_y[index]),
                "actual_return_5d": validation[index]["raw_return_5d"],
                "frozen_pr_f_score": float(frozen_scores[index]),
                "frozen_threshold_prediction": bool(fixed_predicted[index]),
                "development_alert_budget_prediction": bool(predicted[index]),
            }
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "test_predictions_alert_policy.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    all_rows = data["rows"]
    v2_study = run_role_d_v2_candidate(
        case_ids=[row["case_id"] for row in all_rows],
        years=[row["cohort_year"] for row in all_rows],
        feature_names=data["feature_names"],
        feature_values=[row["feature_values"] for row in all_rows],
        labels=[row["label"] for row in all_rows],
        raw_returns=[row["raw_return_5d"] for row in all_rows],
        frozen_pr_f_metrics=frozen["classification_metrics"],
    )
    with (output_dir / "test_predictions_v2.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(v2_study.prediction_rows[0])
        )
        writer.writeheader()
        writer.writerows(v2_study.prediction_rows)
    _write_json(output_dir / "v2_model_summary.json", v2_study.summary)
    (output_dir / "role_d_v2_classifier.txt").write_text(
        v2_study.model_text, encoding="utf-8"
    )
    comparison_rows = []
    selected_group = v2_study.summary["selection_protocol"][
        "selected_feature_group"
    ]
    for candidate in v2_study.summary["selection_protocol"][
        "candidate_results"
    ]:
        comparison_rows.append(
            {
                "feature_group": candidate["feature_group"],
                "feature_count": candidate["feature_count"],
                "pooled_pr_auc": candidate["pooled_pr_auc"],
                "macro_forward_year_pr_auc": candidate[
                    "macro_forward_year_pr_auc"
                ],
                "pooled_roc_auc": candidate["pooled_roc_auc"],
                "macro_forward_year_roc_auc": candidate[
                    "macro_forward_year_roc_auc"
                ],
                "pooled_brier_score": candidate["pooled_brier_score"],
                "selected": candidate["feature_group"] == selected_group,
            }
        )
    with (output_dir / "development_feature_comparison.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(comparison_rows[0]))
        writer.writeheader()
        writer.writerows(comparison_rows)

    summary = {
        "policy_version": ROLE_D_ALERT_POLICY_VERSION,
        "status": "complete_development_only_policy_selection",
        "purpose": "supplement_frozen_uncalibrated_score_with_high_recall_alert_budget",
        "frozen_pr_f_unchanged": True,
        "score_semantics": "uncalibrated_model_score",
        "model_channel": "full_production_M_lightgbm",
        "policy_selection": {
            "split": "2021_2023_development_forward_oof",
            "objective": f"F{ROLE_D_ALERT_BETA:g}",
            "candidate_fractions": list(ROLE_D_ALERT_FRACTIONS),
            "selected_fraction": selected.fraction,
            "selected_alert_count": selected.alert_count,
            "oof_precision": selected.precision,
            "oof_recall": selected.recall,
            "oof_f1": selected.f1,
            "oof_f2": selected.f2,
            "fold_audit": fold_audit,
            "validation_labels_used_for_selection": False,
        },
        "frozen_score_reproduction": {
            "development_count": len(dev_ids),
            "validation_count": len(valid_ids),
            "feature_count": len(data["feature_names"]),
            "feature_manifest_hash": data["feature_manifest_hash"],
            "maximum_absolute_score_difference": max_score_difference,
            "tolerance": SCORE_REPRODUCTION_TOLERANCE,
            "passed": True,
        },
        "2024_validation_comparison": {
            "fixed_threshold_0_5": {
                "alert_count": int(fixed_predicted.sum()),
                "precision": fixed_metrics["precision"],
                "recall": fixed_metrics["recall"],
                "f1": fixed_metrics["f1"],
            },
            "development_selected_alert_budget": policy_metrics,
            "ranking_metrics_unchanged": {
                "roc_auc": float(roc_auc_score(valid_y, frozen_scores)),
                "pr_auc": float(average_precision_score(valid_y, frozen_scores)),
            },
        },
        "root_cause": [
            (
                "5D labels and frozen PR-F scores reproduce exactly; no "
                "label-direction or metric bug was found."
            ),
            (
                "The frozen score is explicitly uncalibrated, so a universal "
                "0.5 cutoff is not a governed probability decision rule."
            ),
            (
                "The fixed cutoff emitted only three alerts among 70 Validation "
                "cases, creating 22 false negatives."
            ),
            (
                "The 2024 ROC-AUC remains weak; this policy improves the "
                "operating-point recall but does not manufacture better ranking quality."
            ),
        ],
        "optimized_v2_candidate": {
            "policy_version": v2_study.summary["policy_version"],
            "selected_feature_group": v2_study.summary["selection_protocol"][
                "selected_feature_group"
            ],
            "selected_feature_count": v2_study.summary["selection_protocol"][
                "selected_feature_count"
            ],
            "validation": v2_study.summary["validation"],
            "ranking_metric_deltas": v2_study.summary["ranking_metric_deltas"],
            "validation_labels_used_for_selection": False,
        },
        "pr_f_results_sha256": _sha256_file(pr_f_results_path),
        "blind_2025_y_accessed": False,
    }
    _write_json(output_dir / "alert_policy_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market-core-dir", type=Path, required=True)
    parser.add_argument("--target-dir", type=Path, required=True)
    parser.add_argument("--pr-f-results", type=Path, required=True)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("reports/v045_role_d_reaudit")
    )
    args = parser.parse_args()
    summary = build_alert_policy(
        market_core_dir=args.market_core_dir,
        target_dir=args.target_dir,
        pr_f_results_path=args.pr_f_results,
        output_dir=args.output_dir,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
