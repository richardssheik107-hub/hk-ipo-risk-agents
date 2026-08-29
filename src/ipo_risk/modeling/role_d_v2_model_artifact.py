"""Hash-verified materialization of the frozen Role-D V2 model artifact.

The V2 promotion froze a model *identity* -- ``classifier_model_sha256`` -- but
kept no booster file in the repository, so the product could only replay the
three per-case handoff rows and every other IPO was told the case is not in the
sanitized handoff.

This module rebuilds that exact booster from committed artifacts and refuses to
write anything unless the rebuilt model text hashes to the identity already
frozen in ``v045_role_d_v2_promotion_manifest.json``.  That equality is the
whole point: it proves the reconstructed training input is the frozen training
input, so the file written here *is* the promoted model rather than a lookalike
retrained on whatever happened to be on disk.

This is build-time materialization, not training.  The recipe, the feature
policy, the cohort boundary and the alert budget were all frozen by the
promotion; nothing here selects anything.  Labels are read only to reproduce
the frozen fit.  The runtime loads ``model.txt`` and never sees an outcome.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

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
from ipo_risk.modeling.role_d_v2_candidate import (
    ROLE_D_V2_CORE_REGIME_FEATURES,
    ROLE_D_V2_MODEL_POLICY_VERSION,
)

# The forward-OOF fold construction is reused rather than reimplemented: a
# second copy of the recipe could drift from the one that selected the 47.5%
# budget, and a drifted derivation is exactly what a frozen policy forbids.
from ipo_risk.modeling.role_d_v2_candidate import _forward_oof
from ipo_risk.modeling.role_d_v2_release import (
    EXPECTED_DEVELOPMENT_COUNT,
    EXPECTED_VALIDATION_COUNT,
    V2_ALERT_FRACTION,
    V2_ALERT_POLICY,
    V2_RELEASE_VERSION,
    canonical_hash,
)

# The package identity lives in a dependency-free module so the product import
# graph never needs LightGBM just to name the model. Re-exported here because
# this module is the builder that writes it.
from ipo_risk.modeling.role_d_v2_model_package import (  # noqa: F401
    ALERT_POLICY_ARTIFACT_VERSION,
    ALERT_POLICY_FILE,
    ARTIFACT_FILES,
    CALIBRATION_STATUS,
    CHECKSUM_FILE,
    DEFAULT_FROZEN_DIR,
    DEFAULT_MARKET_CORE_DIR,
    DEFAULT_MODEL_DIR,
    DEFAULT_OUTCOME_PACK,
    FEATURE_MANIFEST_FILE,
    FEATURE_MANIFEST_VERSION,
    LABEL_RULE,
    METRIC_TOLERANCE,
    MISSINGNESS_POLICY,
    MODEL_ARTIFACT_VERSION,
    MODEL_FILE,
    MODEL_MANIFEST_FILE,
    MODEL_NAME,
    PR_C_MANIFEST_NAME,
    SCORE_SEMANTICS,
    SINGLE_CASE_ALERT_POLICY_VERSION,
    V2_PROMOTION_MANIFEST_NAME,
    sha256_file,
)


class RoleDV2ModelArtifactError(ValueError):
    """The frozen model artifact cannot be materialized under its frozen identity."""


@dataclass(frozen=True)
class ArtifactRow:
    case_id: str
    cohort_year: int
    feature_values: tuple[float, ...]
    label: bool


def _read_json(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RoleDV2ModelArtifactError(f"invalid JSON: {Path(path).name}") from exc


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def reconstruct_governed_rows(
    *,
    market_core_dir: Path,
    outcome_pack_path: Path,
    pr_c_manifest_path: Path,
) -> tuple[list[ArtifactRow], tuple[str, ...], dict[str, Any]]:
    """Rebuild the frozen 354/70 training matrix from committed artifacts only.

    PR-C keeps its per-case target rows out of Git, but the frozen PR-C manifest
    publishes everything needed to recreate the binary label: the threshold, the
    comparison operator and the exact list of outcome-unavailable cases.  The
    governed outcome pack supplies the 5D returns under the same EOD extract.
    """

    pack = _read_json(outcome_pack_path)
    pr_c = _read_json(pr_c_manifest_path)

    if pack.get("blind_outcomes_included") is not False:
        raise RoleDV2ModelArtifactError("outcome pack does not prove Blind isolation")
    cohort_years = [int(year) for year in pack.get("outcome_cohort_years") or ()]
    if any(year >= 2025 for year in cohort_years):
        raise RoleDV2ModelArtifactError("outcome pack carries 2025 Blind outcomes")
    if pack.get("ipo_eod_sha256") != pr_c.get("raw_eod_sha256"):
        raise RoleDV2ModelArtifactError(
            "outcome pack and PR-C were built from different EOD extracts"
        )

    threshold = float(pr_c["poor_performer_threshold"])
    unavailable = set(pr_c.get("unavailable_case_ids") or ())
    records = {
        str(record["case_id"]): record for record in pack.get("records") or ()
    }

    rows: list[ArtifactRow] = []
    feature_names: tuple[str, ...] | None = None
    feature_manifest_hash: str | None = None
    for path in sorted(Path(market_core_dir).glob("*.json")):
        market = _read_json(path)
        case_id = str(market["case_id"])
        year = int(market["cohort_year"])
        if year >= 2025:
            raise RoleDV2ModelArtifactError(
                "the Role-D V2 training matrix refuses 2025 Blind cases"
            )
        if case_id in unavailable:
            continue
        record = records.get(case_id)
        if record is None or record.get("return_5d") is None:
            raise RoleDV2ModelArtifactError(
                f"governed outcome coverage drift: {case_id} has no 5D return"
            )
        names = tuple(str(value) for value in market["feature_names"])
        current_manifest_hash = str(market["core_feature_manifest_hash"])
        if feature_names is None:
            feature_names, feature_manifest_hash = names, current_manifest_hash
        elif names != feature_names or current_manifest_hash != feature_manifest_hash:
            raise RoleDV2ModelArtifactError("Market Core feature identity drift")
        values = tuple(
            float("nan") if value is None else float(value)
            for value in market["feature_values"]
        )
        if len(values) != len(names) or any(math.isinf(value) for value in values):
            raise RoleDV2ModelArtifactError(
                f"invalid Market Core feature vector: {case_id}"
            )
        rows.append(
            ArtifactRow(
                case_id=case_id,
                cohort_year=year,
                feature_values=values,
                label=float(record["return_5d"]) <= threshold,
            )
        )

    rows.sort(key=lambda row: row.case_id)
    if feature_names is None:
        raise RoleDV2ModelArtifactError("no governed Market Core rows")
    development = sum(row.cohort_year <= 2023 for row in rows)
    validation = sum(row.cohort_year == 2024 for row in rows)
    if (development, validation) != (
        EXPECTED_DEVELOPMENT_COUNT,
        EXPECTED_VALIDATION_COUNT,
    ):
        raise RoleDV2ModelArtifactError(
            f"governed cohort coverage drift: {development}/{validation}"
        )
    binding = {
        "development_count": development,
        "validation_count": validation,
        "market_feature_manifest_hash": feature_manifest_hash,
        "raw_eod_sha256": pack.get("ipo_eod_sha256"),
        "outcome_pack_content_hash": pack.get("content_hash"),
        "outcome_pack_sha256": sha256_file(Path(outcome_pack_path)),
        "pr_c_freeze_manifest_hash": pr_c.get("freeze_manifest_hash"),
        "pr_c_threshold": pr_c.get("poor_performer_threshold"),
        "pr_c_threshold_hash": pr_c.get("threshold_hash"),
        "pr_c_policy_hash": pr_c.get("policy_hash"),
        "label_rule": LABEL_RULE,
        "case_rows_hash": canonical_hash(
            [{"case_id": row.case_id, "label": row.label} for row in rows]
        ),
    }
    return rows, feature_names, binding


def _matrix(rows: Sequence[ArtifactRow], positions: Sequence[int]) -> np.ndarray:
    return np.asarray(
        [[row.feature_values[index] for index in positions] for row in rows],
        dtype=float,
    )


def _validation_metrics(
    labels: np.ndarray, scores: np.ndarray, alerts: np.ndarray
) -> dict[str, Any]:
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


def derive_single_case_cutoff(
    x_development: np.ndarray,
    y_development: np.ndarray,
    years: np.ndarray,
) -> dict[str, Any]:
    """Turn the frozen batch alert budget into a single-case score cutoff.

    The promoted policy alerts on the top 47.5% of a governed *batch*, which one
    fresh IPO does not have.  The cutoff is therefore read off the same evidence
    the budget was selected on -- 2021-2023 forward-OOF Development scores, by
    nearest rank -- so no Validation or Blind row participates in the
    derivation.
    """

    oof, folds = _forward_oof(x_development, y_development, years)
    available = np.isfinite(oof)
    scores = np.sort(oof[available])[::-1]
    if scores.size == 0:
        raise RoleDV2ModelArtifactError("no Development forward-OOF scores")
    nearest_rank = max(1, int(np.ceil(scores.size * V2_ALERT_FRACTION)))
    return {
        "cutoff": float(scores[nearest_rank - 1]),
        "development_oof_count": int(scores.size),
        "nearest_rank": nearest_rank,
        "forward_oof_folds": [
            {
                "evaluation_year": fold["evaluation_year"],
                "train_years": fold["train_years"],
                "train_count": fold["train_count"],
                "evaluation_count": fold["evaluation_count"],
            }
            for fold in folds
        ],
    }


def _verify_frozen_identity(
    frozen: dict[str, Any],
    *,
    classifier_sha256: str,
    binding: dict[str, Any],
    metrics: dict[str, Any],
) -> dict[str, Any]:
    """Refuse to write unless every frozen claim is independently reproduced."""

    blockers: list[str] = []
    if frozen.get("classifier_model_sha256") != classifier_sha256:
        blockers.append(
            "rebuilt classifier hash does not match the frozen model identity"
        )
    if frozen.get("model_name") != MODEL_NAME:
        blockers.append("frozen model name drift")
    if frozen.get("status") != "complete_frozen" or frozen.get("formal_gate_passed") is not True:
        blockers.append("V2 promotion is not frozen and gate-passed")
    if (frozen.get("promotion_record") or {}).get("decision") != "promote_v2":
        blockers.append("frozen manifest does not record the promote_v2 decision")
    if frozen.get("blind_2025_y_accessed") is not False:
        blockers.append("frozen manifest does not prove Blind isolation")

    selection = frozen.get("selection") or {}
    if tuple(selection.get("selected_features") or ()) != ROLE_D_V2_CORE_REGIME_FEATURES:
        blockers.append("frozen selected-feature set drift")
    if selection.get("alert_policy") != V2_ALERT_POLICY:
        blockers.append("frozen alert policy drift")
    if selection.get("alert_fraction") != V2_ALERT_FRACTION:
        blockers.append("frozen alert fraction drift")

    frozen_binding = frozen.get("input_binding") or {}
    for key in ("development_count", "validation_count", "market_feature_manifest_hash", "raw_eod_sha256"):
        if frozen_binding.get(key) != binding.get(key):
            blockers.append(f"input binding drift: {key}")

    frozen_metrics = frozen.get("validation_metrics") or {}
    for key, value in metrics.items():
        claimed = frozen_metrics.get(key)
        if isinstance(value, float):
            if claimed is None or not math.isclose(value, float(claimed), abs_tol=METRIC_TOLERANCE):
                blockers.append(f"recomputed metric mismatch: {key}")
        elif value != claimed:
            blockers.append(f"recomputed metric mismatch: {key}")

    if blockers:
        raise RoleDV2ModelArtifactError(
            "frozen model identity verification failed: " + "; ".join(blockers)
        )
    return {
        "classifier_model_sha256": "match",
        "input_binding": "match",
        "validation_metrics": "recomputed_and_matched",
        "selected_features": "match",
        "alert_policy": "match",
    }


def materialize_model_artifact(
    *,
    model_dir: Path = DEFAULT_MODEL_DIR,
    market_core_dir: Path = DEFAULT_MARKET_CORE_DIR,
    outcome_pack_path: Path = DEFAULT_OUTCOME_PACK,
    frozen_dir: Path = DEFAULT_FROZEN_DIR,
) -> dict[str, Any]:
    """Rebuild, verify and write the runtime model package. Fail closed."""

    frozen_root = Path(frozen_dir)
    frozen = _read_json(frozen_root / V2_PROMOTION_MANIFEST_NAME)
    rows, feature_names, binding = reconstruct_governed_rows(
        market_core_dir=Path(market_core_dir),
        outcome_pack_path=Path(outcome_pack_path),
        pr_c_manifest_path=frozen_root / PR_C_MANIFEST_NAME,
    )
    missing = [name for name in ROLE_D_V2_CORE_REGIME_FEATURES if name not in feature_names]
    if missing:
        raise RoleDV2ModelArtifactError(
            "Market Core omits locked model features: " + ", ".join(missing)
        )
    positions = tuple(feature_names.index(name) for name in ROLE_D_V2_CORE_REGIME_FEATURES)

    development = [row for row in rows if row.cohort_year <= 2023]
    validation = [row for row in rows if row.cohort_year == 2024]
    x_dev, x_val = _matrix(development, positions), _matrix(validation, positions)
    y_dev = np.asarray([row.label for row in development], dtype=int)
    y_val = np.asarray([row.label for row in validation], dtype=int)

    model = build_pr_f_classifier()
    model.fit(x_dev, y_dev)
    model_text = model.booster_.model_to_string()
    classifier_sha256 = hashlib.sha256(model_text.encode("utf-8")).hexdigest()

    scores = np.asarray(model.booster_.predict(x_val), dtype=float)
    alerts = alert_budget_predictions(
        [row.case_id for row in validation], scores, V2_ALERT_FRACTION
    )
    metrics = _validation_metrics(y_val, scores, alerts)
    verification = _verify_frozen_identity(
        frozen,
        classifier_sha256=classifier_sha256,
        binding=binding,
        metrics=metrics,
    )

    cutoff = derive_single_case_cutoff(
        x_dev, y_dev, np.asarray([row.cohort_year for row in development], dtype=int)
    )
    # Label-free agreement report: it compares two alert *rules* on the already
    # published 2024 scores.  No outcome takes part, and nothing here selects
    # the cutoff, which was fixed by Development forward-OOF alone.
    cutoff_alerts = scores >= cutoff["cutoff"]
    agreement = {
        "cohort": "2024_validation_scores_already_published_by_the_promotion",
        "labels_used": False,
        "used_for_derivation": False,
        "batch_policy_alert_count": int(alerts.sum()),
        "single_case_policy_alert_count": int(cutoff_alerts.sum()),
        "per_case_agreement": float((cutoff_alerts == alerts).mean()),
    }

    model_directory = Path(model_dir)
    model_directory.mkdir(parents=True, exist_ok=True)
    model_path = model_directory / MODEL_FILE
    model_path.write_text(model_text, encoding="utf-8")

    feature_manifest = {
        "manifest_version": FEATURE_MANIFEST_VERSION,
        "core_feature_manifest_hash": binding["market_feature_manifest_hash"],
        "handoff_feature_position_count": len(feature_names),
        "handoff_feature_names": list(feature_names),
        "model_input_feature_names": list(ROLE_D_V2_CORE_REGIME_FEATURES),
        "model_input_positions": list(positions),
        "model_expected_dimension": len(positions),
        "feature_component": "market_core",
        "dtype": "float64",
        "missingness_policy": MISSINGNESS_POLICY,
        "zero_fill_forbidden": True,
        "document_features_used": False,
        "gold_derived_features_used": False,
    }
    feature_manifest["content_hash"] = canonical_hash(feature_manifest)

    alert_policy = {
        "manifest_version": ALERT_POLICY_ARTIFACT_VERSION,
        "batch_policy": {
            "version": V2_ALERT_POLICY,
            "fraction": V2_ALERT_FRACTION,
            "operator": "top_fraction_of_a_governed_batch_with_case_id_tie_break",
            "applies_to": "a governed batch scored in one run",
        },
        "single_case_policy": {
            "version": SINGLE_CASE_ALERT_POLICY_VERSION,
            "operator": "score >= cutoff",
            "cutoff": cutoff["cutoff"],
            "derivation": "development_2021_2023_forward_oof_nearest_rank_top_fraction_0.475",
            "development_oof_count": cutoff["development_oof_count"],
            "nearest_rank": cutoff["nearest_rank"],
            "forward_oof_folds": cutoff["forward_oof_folds"],
            "validation_used_for_derivation": False,
            "blind_used_for_derivation": False,
            "applies_to": "one case scored without a governed batch",
            "consistency_report": agreement,
        },
        "score_semantics": SCORE_SEMANTICS,
    }
    alert_policy["content_hash"] = canonical_hash(alert_policy)

    model_manifest = {
        "manifest_version": MODEL_ARTIFACT_VERSION,
        "model_name": MODEL_NAME,
        "model_version": V2_RELEASE_VERSION,
        "model_policy_version": ROLE_D_V2_MODEL_POLICY_VERSION,
        "model_file": MODEL_FILE,
        "model_file_sha256": sha256_file(model_path),
        "classifier_model_sha256": classifier_sha256,
        "feature_manifest_file": FEATURE_MANIFEST_FILE,
        "feature_manifest_hash": feature_manifest["content_hash"],
        "alert_policy_file": ALERT_POLICY_FILE,
        "alert_policy_hash": alert_policy["content_hash"],
        "score_semantics": SCORE_SEMANTICS,
        "calibration_status": CALIBRATION_STATUS,
        "source_freeze_manifest": V2_PROMOTION_MANIFEST_NAME,
        "source_freeze_manifest_sha256": sha256_file(
            frozen_root / V2_PROMOTION_MANIFEST_NAME
        ),
        "source_freeze_manifest_hash": frozen.get("freeze_manifest_hash"),
        "source_model_result_hash": frozen.get("model_result_hash"),
        "materialization": {
            "method": "hash_verified_reproduction_of_the_frozen_training_recipe",
            "runtime_retraining": False,
            "overwrites_prior_frozen_identity": False,
            "training_input_binding": binding,
            "verification": verification,
            "recomputed_validation_metrics": metrics,
        },
        "blind_2025_y_accessed": False,
    }
    model_manifest["content_hash"] = canonical_hash(model_manifest)

    _write_json(model_directory / FEATURE_MANIFEST_FILE, feature_manifest)
    _write_json(model_directory / ALERT_POLICY_FILE, alert_policy)
    _write_json(model_directory / MODEL_MANIFEST_FILE, model_manifest)
    checksums = {name: sha256_file(model_directory / name) for name in ARTIFACT_FILES}
    (model_directory / CHECKSUM_FILE).write_text(
        "".join(f"{checksums[name]}  {name}\n" for name in ARTIFACT_FILES),
        encoding="utf-8",
    )
    return {
        "status": "pass",
        "model_dir": str(model_directory),
        "classifier_model_sha256": classifier_sha256,
        "frozen_identity_verified": True,
        "single_case_cutoff": cutoff["cutoff"],
        "artifact_sha256": checksums,
    }
