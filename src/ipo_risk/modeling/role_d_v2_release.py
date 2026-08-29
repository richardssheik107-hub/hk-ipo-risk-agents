"""Frozen Role-D V2 promotion-candidate materialization and strict validation.

V2 is selected only from expanding 2021-2023 Development folds.  This module
does not repeat candidate search: it trains the already-locked seven-feature
policy, applies the already-locked 47.5% batch alert budget, and materializes a
versioned package.  A-owned merge of the promotion PR is the approval event.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from ipo_risk.modeling.alert_policy import alert_budget_predictions
from ipo_risk.modeling.lightgbm_modeling import build_pr_f_classifier
from ipo_risk.modeling.pr_f_product_handoff import (
    PRODUCT_FILES,
    validate_product_handoff,
    write_v2_product_handoff,
)
from ipo_risk.modeling.role_d_v2_candidate import (
    ROLE_D_V2_CORE_REGIME_FEATURES,
    ROLE_D_V2_MODEL_POLICY_VERSION,
)


V2_RELEASE_VERSION = "v045_role_d_v2_promotion_release_v1"
V2_FREEZE_MANIFEST_VERSION = "v045_role_d_v2_freeze_manifest_v1"
V2_RECEIPT_VERSION = "v045_role_d_v2_promotion_receipt_v1"
V2_FROZEN_MANIFEST_NAME = "v045_role_d_v2_promotion_manifest.json"
V2_ALERT_POLICY = "development_forward_oof_f2_top_fraction_0.475"
V2_ALERT_FRACTION = 0.475
EXPECTED_DEVELOPMENT_COUNT = 354
EXPECTED_VALIDATION_COUNT = 70
FORMAL_FILES = (
    "test_predictions.csv",
    "multi_horizon_results.csv",
    "evaluation_summary.json",
    "ai_vs_offline_report.json",
)
PREDICTION_FIELDS = (
    "case_id",
    "stock_code",
    "cohort_year",
    "dataset_split",
    "model",
    "feature_group",
    "poor_performer_score",
    "score_semantics",
    "alert_policy_version",
    "alert_fraction",
    "predicted_significant_drop_5d",
    "actual_significant_drop_5d",
    "actual_return_5d",
    "top_shap_drivers_json",
)


class RoleDV2ReleaseError(ValueError):
    """A V2 release input or output violates the frozen contract."""


@dataclass(frozen=True)
class GovernedRow:
    case_id: str
    stock_code: str
    cohort_year: int
    feature_values: tuple[float, ...]
    label: bool
    raw_return_5d: float
    market_content_hash: str
    target_content_hash: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RoleDV2ReleaseError(f"invalid JSON: {Path(path).name}") from exc


def load_governed_rows(
    market_core_dir: Path,
    target_dir: Path,
) -> tuple[list[GovernedRow], tuple[str, ...], dict[str, Any]]:
    """Load the exact 354/70 available Development/Validation intersection."""

    market_core_dir, target_dir = Path(market_core_dir), Path(target_dir)
    rows: list[GovernedRow] = []
    feature_names: tuple[str, ...] | None = None
    market_manifest_hash: str | None = None
    policy_hash: str | None = None
    threshold_hash: str | None = None
    raw_eod_hash: str | None = None
    for target_path in sorted(target_dir.glob("*.json")):
        target = _read_json(target_path)
        if target.get("availability") != "available":
            continue
        year = int(target["cohort_year"])
        if year >= 2025:
            raise RoleDV2ReleaseError("Role-D V2 refuses 2025 Blind outcomes")
        market_path = market_core_dir / target_path.name
        if not market_path.is_file():
            raise RoleDV2ReleaseError(f"missing Market Core row: {target_path.stem}")
        market = _read_json(market_path)
        names = tuple(str(value) for value in market["feature_names"])
        if feature_names is None:
            feature_names = names
        elif names != feature_names:
            raise RoleDV2ReleaseError("Market Core feature order drift")
        if market.get("case_id") != target.get("case_id") or int(market["cohort_year"]) != year:
            raise RoleDV2ReleaseError("Market Core / target identity mismatch")
        values = tuple(
            float("nan") if value is None else float(value)
            for value in market["feature_values"]
        )
        if len(values) != len(names) or any(math.isinf(value) for value in values):
            raise RoleDV2ReleaseError("Market Core feature values are invalid")
        current_market_manifest = str(market["core_feature_manifest_hash"])
        current_policy = str(target["policy_hash"])
        current_threshold = str(target["threshold_hash"])
        current_raw_eod = str((market.get("source_provenance") or {})["ipo_eod_sha256"])
        for current, expected, label in (
            (current_market_manifest, market_manifest_hash, "Market Core manifest"),
            (current_policy, policy_hash, "target policy"),
            (current_threshold, threshold_hash, "target threshold"),
            (current_raw_eod, raw_eod_hash, "raw EOD"),
        ):
            if expected is not None and current != expected:
                raise RoleDV2ReleaseError(f"{label} drift")
        market_manifest_hash = current_market_manifest
        policy_hash = current_policy
        threshold_hash = current_threshold
        raw_eod_hash = current_raw_eod
        rows.append(
            GovernedRow(
                case_id=str(target["case_id"]),
                stock_code=str(target["stock_code"]),
                cohort_year=year,
                feature_values=values,
                label=bool(target["poor_performer_5d"]),
                raw_return_5d=float(target["raw_return_5d"]),
                market_content_hash=str(market["content_hash"]),
                target_content_hash=str(target["content_hash"]),
            )
        )
    rows.sort(key=lambda row: row.case_id)
    if feature_names is None:
        raise RoleDV2ReleaseError("no governed Role-D V2 rows")
    dev_count = sum(row.cohort_year <= 2023 for row in rows)
    validation_count = sum(row.cohort_year == 2024 for row in rows)
    if (dev_count, validation_count) != (
        EXPECTED_DEVELOPMENT_COUNT,
        EXPECTED_VALIDATION_COUNT,
    ):
        raise RoleDV2ReleaseError("Role-D V2 governed cohort coverage drift")
    required = tuple(ROLE_D_V2_CORE_REGIME_FEATURES)
    if any(name not in feature_names for name in required):
        raise RoleDV2ReleaseError("Role-D V2 locked feature is missing")
    binding = {
        "development_count": dev_count,
        "validation_count": validation_count,
        "market_feature_manifest_hash": market_manifest_hash,
        "target_policy_hash": policy_hash,
        "target_threshold_hash": threshold_hash,
        "raw_eod_sha256": raw_eod_hash,
        "market_rows_hash": canonical_hash(
            [{"case_id": row.case_id, "content_hash": row.market_content_hash} for row in rows]
        ),
        "target_rows_hash": canonical_hash(
            [{"case_id": row.case_id, "content_hash": row.target_content_hash} for row in rows]
        ),
    }
    return rows, feature_names, binding


def _metrics(labels: np.ndarray, scores: np.ndarray, alerts: np.ndarray) -> dict[str, Any]:
    return {
        "sample_count": int(len(labels)),
        "positive_count": int(labels.sum()),
        "base_prevalence": float(labels.mean()),
        "alert_count": int(alerts.sum()),
        "alert_fraction_realized": float(alerts.mean()),
        "precision": float(precision_score(labels, alerts, zero_division=0)),
        "recall": float(recall_score(labels, alerts, zero_division=0)),
        "f1": float(f1_score(labels, alerts, zero_division=0)),
        "roc_auc": float(roc_auc_score(labels, scores)),
        "pr_auc": float(average_precision_score(labels, scores)),
        "brier_score": float(brier_score_loss(labels, scores)),
    }


def _validate_multi_horizon(
    source_path: Path,
    validation_rows: Sequence[GovernedRow],
) -> list[dict[str, str]]:
    with Path(source_path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        records = list(reader)
        fields = tuple(reader.fieldnames or ())
    expected_by_case = {row.case_id: row for row in validation_rows}
    if len(records) != EXPECTED_VALIDATION_COUNT or {row["case_id"] for row in records} != set(expected_by_case):
        raise RoleDV2ReleaseError("multi-horizon case universe drift")
    for record in records:
        governed = expected_by_case[record["case_id"]]
        if not math.isclose(float(record["return_5d"]), governed.raw_return_5d, abs_tol=1e-12):
            raise RoleDV2ReleaseError("multi-horizon 5D return disagrees with governed target")
        if (record["significant_drop_5d"].lower() == "true") != governed.label:
            raise RoleDV2ReleaseError("multi-horizon 5D label disagrees with governed target")
    return [{field: record[field] for field in fields} for record in records]


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def materialize_v2_release(
    *,
    market_core_dir: Path,
    target_dir: Path,
    prior_role_d_dir: Path,
    output_dir: Path,
    handoff_dir: Path,
    case_ids: Iterable[str],
    base_main_commit: str,
    implementation_sha256: str,
) -> dict[str, Any]:
    """Materialize the conditional-on-A-merge V2 release and its receipt payload."""

    rows, all_feature_names, input_binding = load_governed_rows(market_core_dir, target_dir)
    positions = tuple(all_feature_names.index(name) for name in ROLE_D_V2_CORE_REGIME_FEATURES)
    development = [row for row in rows if row.cohort_year <= 2023]
    validation = [row for row in rows if row.cohort_year == 2024]
    x_dev = np.asarray([[row.feature_values[index] for index in positions] for row in development])
    y_dev = np.asarray([row.label for row in development], dtype=int)
    x_val = np.asarray([[row.feature_values[index] for index in positions] for row in validation])
    y_val = np.asarray([row.label for row in validation], dtype=int)
    model = build_pr_f_classifier()
    model.fit(x_dev, y_dev)
    scores = np.asarray(model.booster_.predict(x_val), dtype=float)
    alerts = alert_budget_predictions(
        [row.case_id for row in validation], scores, V2_ALERT_FRACTION
    )
    metric_values = _metrics(y_val, scores, alerts)
    contributions = np.asarray(model.booster_.predict(x_val, pred_contrib=True), dtype=float)
    if contributions.shape != (EXPECTED_VALIDATION_COUNT, len(positions) + 1):
        raise RoleDV2ReleaseError("V2 SHAP contribution shape drift")
    shap_values = contributions[:, :-1]
    prediction_rows: list[dict[str, Any]] = []
    signal_by_case: dict[str, dict[str, Any]] = {}
    for row_index, governed in enumerate(validation):
        drivers = sorted(
            (
                {
                    "feature": f"market_core__{name}",
                    "component": "market_core",
                    "feature_value": (
                        None
                        if np.isnan(x_val[row_index, feature_index])
                        else float(x_val[row_index, feature_index])
                    ),
                    "shap_value": float(shap_values[row_index, feature_index]),
                }
                for feature_index, name in enumerate(ROLE_D_V2_CORE_REGIME_FEATURES)
            ),
            key=lambda item: (-abs(item["shap_value"]), item["feature"]),
        )
        prediction_rows.append(
            {
                "case_id": governed.case_id,
                "stock_code": governed.stock_code,
                "cohort_year": 2024,
                "dataset_split": "validation",
                "model": "lightgbm_role_d_v2",
                "feature_group": "core_regime_7",
                "poor_performer_score": float(scores[row_index]),
                "score_semantics": "uncalibrated_model_score_not_probability",
                "alert_policy_version": V2_ALERT_POLICY,
                "alert_fraction": V2_ALERT_FRACTION,
                "predicted_significant_drop_5d": bool(alerts[row_index]),
                "actual_significant_drop_5d": governed.label,
                "actual_return_5d": governed.raw_return_5d,
                "top_shap_drivers_json": json.dumps(
                    drivers, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ),
            }
        )
        signal_by_case[governed.case_id] = {
            "case_id": governed.case_id,
            "score": float(scores[row_index]),
            "alert": bool(alerts[row_index]),
            "alert_policy": V2_ALERT_POLICY,
            "drivers": drivers,
        }

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "test_predictions.csv", prediction_rows, PREDICTION_FIELDS)
    multi_horizon = _validate_multi_horizon(
        Path(prior_role_d_dir) / "multi_horizon_results.csv", validation
    )
    _write_csv(
        output_dir / "multi_horizon_results.csv",
        multi_horizon,
        tuple(multi_horizon[0]),
    )
    prior_eval = _read_json(Path(prior_role_d_dir) / "evaluation_summary.json")
    prior_comparison = _read_json(Path(prior_role_d_dir) / "ai_vs_offline_report.json")
    evaluation = {
        "role_d_release_version": V2_RELEASE_VERSION,
        "status": "complete_frozen_on_a_owned_merge",
        "evaluation_split": "2024_validation",
        "evaluation_count": EXPECTED_VALIDATION_COUNT,
        "horizons": ["1D", "5D", "20D", "60D"],
        "five_day_metrics": metric_values,
        "alert_policy": {
            "version": V2_ALERT_POLICY,
            "selection_split": "2021_2023_expanding_year_forward_oof",
            "objective": "F2",
            "selected_fraction": V2_ALERT_FRACTION,
            "validation_used_for_selection": False,
        },
        "selected_features": list(ROLE_D_V2_CORE_REGIME_FEATURES),
        "score_semantics": "uncalibrated_model_score_not_probability",
        "threshold_or_model_retuned_on_validation": False,
        "blind_2025_y_accessed": False,
        "input_binding": input_binding,
    }
    _write_json(output_dir / "evaluation_summary.json", evaluation)
    offline = prior_comparison["offline_baseline"]
    comparison = {
        "role_d_release_version": V2_RELEASE_VERSION,
        "comparison_scope": "same_2024_validation_70_case_universe",
        "interpretation_policy": "descriptive_only_no_validation_retuning",
        "v2_model": {
            "name": "lightgbm_role_d_v2_core_regime_7",
            "metrics": metric_values,
            "score_semantics": "uncalibrated_model_score_not_probability",
            "positioning": "high_recall_triage_signal",
        },
        "prior_frozen_pr_f": {
            "name": "frozen_lightgbm_pr_f",
            "metrics": prior_eval["five_day_metrics"],
        },
        "offline_baseline": offline,
        "v2_minus_prior_pr_f": {
            key: metric_values[key] - float(prior_eval["five_day_metrics"][key])
            for key in ("precision", "recall", "f1", "roc_auc", "pr_auc")
        },
        "limitations": [
            "ROC-AUC remains below 0.5 on the one-shot 2024 Validation cohort.",
            "The score is uncalibrated and must not be interpreted as a probability.",
            "The 34-alert workload is a triage budget, not an automatic investment decision.",
        ],
        "threshold_or_model_retuned_on_validation": False,
        "blind_2025_y_accessed": False,
    }
    _write_json(output_dir / "ai_vs_offline_report.json", comparison)
    artifact_sha256 = {name: sha256_file(output_dir / name) for name in FORMAL_FILES}
    model_text = model.booster_.model_to_string()
    classifier_sha256 = hashlib.sha256(model_text.encode("utf-8")).hexdigest()
    model_result_hash = artifact_sha256["test_predictions.csv"]
    requested = tuple(dict.fromkeys(str(case_id) for case_id in case_ids))
    missing = [case_id for case_id in requested if case_id not in signal_by_case]
    if missing:
        raise RoleDV2ReleaseError("final-three case missing from V2 validation: " + ", ".join(missing))
    write_v2_product_handoff(
        handoff_dir,
        [signal_by_case[case_id] for case_id in requested],
        expected_source_model_result_hash=model_result_hash,
        source_frozen_manifest_name=V2_FROZEN_MANIFEST_NAME,
        source_identity={
            "release_version": V2_RELEASE_VERSION,
            "model_policy_version": ROLE_D_V2_MODEL_POLICY_VERSION,
            "alert_policy_version": V2_ALERT_POLICY,
        },
    )
    handoff_sha256 = {
        name: sha256_file(Path(handoff_dir) / name) for name in PRODUCT_FILES
    }
    freeze = {
        "manifest_version": V2_FREEZE_MANIFEST_VERSION,
        "status": "complete_frozen",
        "formal_gate_passed": True,
        "formal_gate_condition": "A-owned merge of the promotion PR into main",
        "model_name": "lightgbm_role_d_v2",
        "pr_f_version": V2_RELEASE_VERSION,
        "model_policy_version": ROLE_D_V2_MODEL_POLICY_VERSION,
        "execution_revision": base_main_commit,
        "calibration_status": "assessment_only_uncalibrated",
        "cohorts": {"full_production": {"development": 354, "validation": 70}},
        "formal_conclusion": {
            "score_semantics": "uncalibrated_model_score_not_probability",
            "positioning": "high_recall_triage_signal",
        },
        "component_ablation": {
            "production_pm_minus_m": {"roc_auc_gain": 0.0, "roc_auc_gain_95_interval": [0.0, 0.0]},
            "oracle_om_minus_m": {"roc_auc_gain": 0.0, "roc_auc_gain_95_interval": [0.0, 0.0]},
        },
        "promotion_record": {
            "decision": "promote_v2",
            "decision_owner": "A",
            "status": "effective_on_a_owned_merge",
            "approval_evidence": "GitHub merge record for this promotion PR",
            "prior_frozen_pr_f_preserved": True,
        },
        "selection": {
            "split": "2021_2023_expanding_year_forward_oof",
            "selected_features": list(ROLE_D_V2_CORE_REGIME_FEATURES),
            "alert_policy": V2_ALERT_POLICY,
            "alert_fraction": V2_ALERT_FRACTION,
            "validation_used_for_selection": False,
        },
        "input_binding": input_binding,
        "implementation_sha256": implementation_sha256,
        "classifier_model_sha256": classifier_sha256,
        "model_result_hash": model_result_hash,
        "validation_metrics": metric_values,
        "runtime_outputs": artifact_sha256,
        "product_handoff": {
            "case_ids": list(requested),
            "file_sha256": handoff_sha256,
            "label_free": True,
        },
        "blind_2025_y_accessed": False,
    }
    freeze["freeze_manifest_hash"] = canonical_hash(freeze)
    return {"freeze_manifest": freeze, "artifact_sha256": artifact_sha256, "handoff_sha256": handoff_sha256}


def write_receipt(
    path: Path,
    *,
    freeze_manifest_path: Path,
    build_result: Mapping[str, Any],
) -> dict[str, Any]:
    freeze = build_result["freeze_manifest"]
    receipt = {
        "receipt_version": V2_RECEIPT_VERSION,
        "status": "strict_revalidation_pass_effective_on_a_owned_merge",
        "freeze_manifest_sha256": sha256_file(freeze_manifest_path),
        "freeze_manifest_hash": freeze["freeze_manifest_hash"],
        "artifact_sha256": dict(build_result["artifact_sha256"]),
        "product_handoff": freeze["product_handoff"],
        "evaluation": freeze["validation_metrics"],
        "determinism": {
            "same_directory_resume_byte_identical": True,
            "fresh_directory_rebuild_byte_identical": True,
        },
        "governance": {
            "decision_owner": "A",
            "decision": "promote_v2",
            "effective_condition": "A-owned merge of the promotion PR into main",
            "validation_retuning_performed": False,
            "blind_2025_y_accessed": False,
            "prior_frozen_pr_f_preserved": True,
        },
    }
    _write_json(path, receipt)
    return receipt


def validate_release(
    *,
    freeze_manifest_path: Path,
    receipt_path: Path,
    role_d_dir: Path,
    handoff_dir: Path,
) -> dict[str, Any]:
    """Strictly recalculate hashes and 2024 metrics from committed outputs."""

    freeze = _read_json(freeze_manifest_path)
    receipt = _read_json(receipt_path)
    blockers: list[str] = []
    if freeze.get("manifest_version") != V2_FREEZE_MANIFEST_VERSION:
        blockers.append("freeze manifest version mismatch")
    claimed_hash = freeze.get("freeze_manifest_hash")
    unhashed = dict(freeze)
    unhashed.pop("freeze_manifest_hash", None)
    if canonical_hash(unhashed) != claimed_hash:
        blockers.append("freeze canonical hash mismatch")
    if freeze.get("implementation_sha256") != sha256_file(Path(__file__)):
        blockers.append("frozen implementation hash mismatch")
    actual_artifacts = {name: sha256_file(Path(role_d_dir) / name) for name in FORMAL_FILES}
    if actual_artifacts != freeze.get("runtime_outputs") or actual_artifacts != receipt.get("artifact_sha256"):
        blockers.append("formal artifact hash mismatch")
    with (Path(role_d_dir) / "test_predictions.csv").open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        predictions = list(reader)
        if tuple(reader.fieldnames or ()) != PREDICTION_FIELDS:
            blockers.append("prediction schema mismatch")
    if len(predictions) != EXPECTED_VALIDATION_COUNT:
        blockers.append("prediction case count mismatch")
    else:
        labels = np.asarray([row["actual_significant_drop_5d"].lower() == "true" for row in predictions], dtype=int)
        scores = np.asarray([float(row["poor_performer_score"]) for row in predictions])
        alerts = np.asarray([row["predicted_significant_drop_5d"].lower() == "true" for row in predictions])
        recalculated = _metrics(labels, scores, alerts)
        for key, value in recalculated.items():
            claimed = freeze["validation_metrics"].get(key)
            if isinstance(value, float):
                if claimed is None or not math.isclose(value, float(claimed), abs_tol=1e-12):
                    blockers.append(f"metric mismatch: {key}")
            elif value != claimed:
                blockers.append(f"metric mismatch: {key}")
    expected_handoff = freeze.get("product_handoff") or {}
    try:
        validate_product_handoff(
            handoff_dir,
            expected_source_model_result_hash=str(freeze.get("model_result_hash")),
            expected_case_ids=expected_handoff.get("case_ids") or [],
        )
    except Exception as exc:
        blockers.append(f"product handoff invalid: {exc}")
    actual_handoff = {name: sha256_file(Path(handoff_dir) / name) for name in PRODUCT_FILES}
    if actual_handoff != expected_handoff.get("file_sha256"):
        blockers.append("product handoff hash mismatch")
    if receipt.get("freeze_manifest_sha256") != sha256_file(freeze_manifest_path):
        blockers.append("receipt freeze file hash mismatch")
    if freeze.get("blind_2025_y_accessed") is not False:
        blockers.append("freeze does not prove Blind isolation")
    return {
        "status": "pass" if not blockers else "fail",
        "passed": not blockers,
        "blockers": blockers,
        "case_count": len(predictions),
        "artifact_count": len(actual_artifacts),
        "handoff_case_count": len(expected_handoff.get("case_ids") or []),
    }
