"""Read-only consumer of the frozen PR-F model result for the PR-G Final Supervisor.

PR-F is COMPLETE / FROZEN but its runtime artifacts are deliberately not
committed (``runtime_artifacts_committed: false``).  Only the freeze manifest is
in the repository.  This module therefore reads on two tiers:

``Tier 1`` — cohort evidence, always available, from the committed freeze
manifest: model identity, calibration status, the two ablation gains and their
bootstrap intervals.  It describes the frozen *cohort*, never the case in hand.

``Tier 2`` — per-case score and SHAP drivers, only when a local PR-F run
directory is configured.  Both the local run manifest and the actual
``model_results.json`` content are bound to the frozen ``model_result_hash``
before any per-case number is consumed.

Nothing here trains, scores or re-runs anything.  A number that is not already
inside the frozen artifacts is not produced.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ipo_risk.modeling.statistical_power import assess_comparison
from ipo_risk.modeling.pr_f_product_handoff import (
    PRODUCT_MANIFEST_NAME,
    ProductCaseNotPresentError,
    ProductRuntimeHandoffError,
    read_product_case_signal_details,
)
from ipo_risk.schemas.canonical_modeling import canonical_hash
from ipo_risk.schemas.final_supervision import ChannelStatus, ModelDriver, ModelPredictionView

FROZEN_MANIFEST_NAME = "v04_pr_f_lightgbm_manifest.json"
MODEL_NAME = "lightgbm"
# The product model is fixed here rather than in Settings: which frozen model the
# product speaks for is a governance decision, not a runtime switch.
PRODUCTION_COHORT = "full_production"
PRODUCTION_FEATURE_GROUP = "PM"

# The one reason that means "the package is intact, this case is simply outside
# its three rows".  The generalized runtime keys off exactly this string, so it
# is a constant rather than a literal repeated in two lanes.
PRODUCT_HANDOFF_SCOPE_REASON = "case_is_not_in_the_sanitized_product_handoff"

EXPECTED_STATUS = "complete_frozen"
EXPECTED_CALIBRATION = "assessment_only_uncalibrated"
EXPECTED_SCORE_SEMANTICS = "uncalibrated_model_score_not_probability"

UNCALIBRATED_DISCLAIMER = "model score is uncalibrated and must not be read as a probability"
# The only supportable phrasing for a gap the cohort cannot resolve; see
# docs/V04_ORACLE_GOLD_COVERAGE_AUDIT.md.  Rendering these as "no signal" or
# "document features are useless" is explicitly forbidden there.
NOT_VALIDATED_PHRASE = "not validated at this sample size"
PRODUCTION_EQUIVALENCE_STATEMENT = (
    "the frozen LightGBM policy gave the production document features no split and no gain, "
    "so the document-plus-market and market-only arms are prediction-equivalent "
    f"({NOT_VALIDATED_PHRASE})"
)
ORACLE_CEILING_STATEMENT = (
    "the expert-gold ceiling arm differs from market-only by less than its own bootstrap "
    f"interval spans, on a 19-case validation intersection ({NOT_VALIDATED_PHRASE})"
)


class FrozenModelEvidenceError(ValueError):
    """The frozen PR-F manifest cannot be trusted as a model-channel source."""


class AblationGain(BaseModel):
    """One arm-to-arm gain with the interval PR-F measured for it."""

    model_config = ConfigDict(frozen=True)

    comparison: str = Field(min_length=1)
    roc_auc_gain: float
    interval_low: float
    interval_high: float

    @property
    def spans_zero(self) -> bool:
        return self.interval_low <= 0.0 <= self.interval_high

    @property
    def sign_is_informative(self) -> bool:
        """A degenerate interval still spans zero, so check width as well."""
        return not self.spans_zero


class FrozenModelCohortEvidence(BaseModel):
    """Tier 1: what the frozen PR-F run established about the cohort."""

    model_config = ConfigDict(frozen=True)

    model_name: str
    model_version: str
    model_policy_version: str
    freeze_manifest_hash: str
    execution_revision: str
    calibration_status: str
    score_semantics: str
    validation_cohort_size: int
    production_gain: AblationGain
    oracle_gain: AblationGain

    def statements(self) -> tuple[str, ...]:
        """Cohort-level sentences safe to place in a report."""
        lines = [PRODUCTION_EQUIVALENCE_STATEMENT] if self.production_gain.spans_zero else []
        if self.oracle_gain.spans_zero:
            lines.append(ORACLE_CEILING_STATEMENT)
        return tuple(lines)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise FrozenModelEvidenceError(message)


def load_frozen_cohort_evidence(
    frozen_dir: Path,
    *,
    manifest_name: str = FROZEN_MANIFEST_NAME,
) -> FrozenModelCohortEvidence:
    """Load and fail-closed validate the committed PR-F freeze manifest."""
    _require(Path(manifest_name).name == manifest_name, "frozen manifest name must be a basename")
    path = Path(frozen_dir) / manifest_name
    _require(path.is_file(), f"frozen model manifest not found at {manifest_name}")
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))

    _require(payload.get("status") == EXPECTED_STATUS, "frozen PR-F manifest is not complete_frozen")
    _require(payload.get("formal_gate_passed") is True, "frozen PR-F manifest did not pass its gate")
    # The 2025 guard belongs at every consumption boundary, not only at production.
    _require(payload.get("blind_2025_y_accessed") is False, "frozen PR-F manifest reports blind 2025 access")
    _require(payload.get("calibration_status") == EXPECTED_CALIBRATION,
             "frozen PR-F calibration status is not the assessment-only value PR-G expects")
    conclusion = payload.get("formal_conclusion") or {}
    _require(conclusion.get("score_semantics") == EXPECTED_SCORE_SEMANTICS,
             "frozen PR-F score semantics are not the uncalibrated value PR-G expects")

    ablation = payload.get("component_ablation") or {}
    return FrozenModelCohortEvidence(
        model_name=str(payload.get("model_name") or MODEL_NAME),
        model_version=str(payload["pr_f_version"]),
        model_policy_version=str(payload["model_policy_version"]),
        freeze_manifest_hash=str(payload["freeze_manifest_hash"]),
        execution_revision=str(payload["execution_revision"]),
        calibration_status=str(payload["calibration_status"]),
        score_semantics=str(conclusion["score_semantics"]),
        validation_cohort_size=int(payload["cohorts"][PRODUCTION_COHORT]["validation"]),
        production_gain=_gain("production_pm_minus_m", ablation),
        oracle_gain=_gain("oracle_om_minus_m", ablation),
    )


def _gain(key: str, ablation: dict[str, Any]) -> AblationGain:
    block = ablation.get(key) or {}
    interval = block.get("roc_auc_gain_95_interval") or [0.0, 0.0]
    return AblationGain(
        comparison=key,
        roc_auc_gain=float(block.get("roc_auc_gain", 0.0)),
        interval_low=float(interval[0]),
        interval_high=float(interval[1]),
    )


def frozen_manifest_result_hash(
    frozen_dir: Path,
    *,
    manifest_name: str = FROZEN_MANIFEST_NAME,
) -> str:
    _require(Path(manifest_name).name == manifest_name, "frozen manifest name must be a basename")
    path = Path(frozen_dir) / manifest_name
    return str(json.loads(path.read_text(encoding="utf-8"))["model_result_hash"])


def runtime_frozen_manifest_name(run_dir: Path) -> str:
    """Resolve a versioned manifest only from the checksum-verified handoff directory."""

    payload = _read_json_if_valid(Path(run_dir) / PRODUCT_MANIFEST_NAME)
    if not isinstance(payload, dict):
        return FROZEN_MANIFEST_NAME
    name = payload.get("source_frozen_manifest_name")
    if name is None:
        return FROZEN_MANIFEST_NAME
    if not isinstance(name, str) or Path(name).name != name or not name.endswith(".json"):
        raise FrozenModelEvidenceError("product handoff names an invalid frozen manifest")
    return name


class LocalRunBindingError(ValueError):
    """A local PR-F run directory does not correspond to the frozen result."""


class FrozenModelPredictionProvider:
    """Read one governed per-case score from a sanitized or verified PR-F run."""

    name = "frozen_pr_f"

    def __init__(self, *, run_dir: str | Path, frozen_dir: str | Path) -> None:
        self.run_dir = Path(run_dir)
        self.frozen_dir = Path(frozen_dir)

    def prediction(self, profile) -> ModelPredictionView:
        case_id = profile.metadata.get("case_id") if profile is not None else None
        return load_case_prediction(self.run_dir, self.frozen_dir, case_id)


def _unavailable(reason: str, base: dict[str, Any]) -> ModelPredictionView:
    return ModelPredictionView(status=ChannelStatus.UNAVAILABLE_ERROR, reason=reason, **base)


def _read_json_if_valid(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def load_case_prediction(
    run_dir: Path,
    frozen_dir: Path,
    case_id: str | None,
) -> ModelPredictionView:
    """Tier 2: the per-case score, or an explicit reason it is unavailable.

    Binding is two-step and fail-closed:

    1. the local ``run_manifest.json`` must claim the exact frozen
       ``model_result_hash``;
    2. the canonical hash of the *actual* ``model_results.json`` payload must
       equal the same frozen hash.

    This prevents a stale/tampered results file from being accepted merely
    because somebody copied a trusted hash into the local run manifest.
    """
    try:
        manifest_name = runtime_frozen_manifest_name(run_dir)
    except FrozenModelEvidenceError:
        return _unavailable("product_handoff_frozen_manifest_binding_is_invalid", {
            "model_name": MODEL_NAME,
            "model_version": None,
            "score_semantics": "uncalibrated_model_score",
            "calibration_status": "uncalibrated",
        })
    evidence = load_frozen_cohort_evidence(frozen_dir, manifest_name=manifest_name)
    base = {
        "model_name": evidence.model_name,
        "model_version": evidence.model_version,
        "score_semantics": "uncalibrated_model_score",
        "calibration_status": "uncalibrated",
    }
    if not case_id:
        return _unavailable("ipo_identity_not_bound_to_the_governed_case_catalog", base)

    run_path = Path(run_dir)
    expected_hash = frozen_manifest_result_hash(
        frozen_dir, manifest_name=manifest_name
    )
    try:
        product_signal = read_product_case_signal_details(
            run_path,
            expected_source_model_result_hash=expected_hash,
            case_id=case_id,
        )
    except ProductCaseNotPresentError:
        # The package is intact; this case is out of its scope. Every dynamic
        # new-IPO case lands here, and must not be told the artifact is broken.
        return _unavailable(PRODUCT_HANDOFF_SCOPE_REASON, base)
    except ProductRuntimeHandoffError:
        return _unavailable("sanitized_pr_f_product_handoff_failed_validation", base)
    if product_signal is not None:
        score, drivers, alert, alert_policy = product_signal
        return ModelPredictionView(
            status=ChannelStatus.AVAILABLE,
            reason="per-case score read from the content-verified sanitized Role-D handoff",
            score=score,
            alert=alert,
            alert_policy=alert_policy,
            drivers=drivers,
            **base,
        )

    manifest_path, results_path = run_path / "run_manifest.json", run_path / "model_results.json"
    if not manifest_path.is_file() or not results_path.is_file():
        return _unavailable("frozen_pr_f_runtime_artifacts_are_not_present_locally", base)

    local_manifest = _read_json_if_valid(manifest_path)
    results_payload = _read_json_if_valid(results_path)
    if not isinstance(local_manifest, dict) or not isinstance(results_payload, list):
        return _unavailable("frozen_pr_f_runtime_artifacts_are_invalid_json", base)

    if local_manifest.get("model_result_hash") != expected_hash:
        return _unavailable("local_pr_f_artifacts_do_not_match_the_frozen_hash", base)
    if canonical_hash(results_payload) != expected_hash:
        return _unavailable("local_pr_f_model_results_do_not_match_the_frozen_hash", base)
    if local_manifest.get("blind_2025_y_accessed") not in (False, None):
        return _unavailable("local_pr_f_runtime_manifest_reports_blind_2025_access", base)

    artifact = _production_artifact(results_payload)
    if artifact is None:
        return _unavailable("frozen_pr_f_results_carry_no_production_artifact", base)

    row = next((item for item in artifact.get("case_predictions", []) if item.get("case_id") == case_id), None)
    if row is None:
        return _unavailable("case_is_not_in_the_frozen_2024_validation_cohort", base)

    return ModelPredictionView(
        status=ChannelStatus.AVAILABLE,
        reason="per-case score read from the content-verified frozen PR-F result",
        score=float(row["poor_performer_score"]),
        drivers=_drivers(artifact, case_id),
        **base,
    )


def _production_artifact(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next(
        (item for item in results
         if item.get("cohort") == PRODUCTION_COHORT and item.get("feature_group") == PRODUCTION_FEATURE_GROUP),
        None,
    )


def _drivers(artifact: dict[str, Any], case_id: str) -> tuple[ModelDriver, ...]:
    explainability = artifact.get("explainability") or {}
    entry = next((item for item in explainability.get("single_ipo_drivers", [])
                  if item.get("case_id") == case_id), None)
    if entry is None:
        return ()
    return tuple(
        ModelDriver(
            feature=str(driver["feature"]),
            component=str(driver.get("component") or "unclassified"),
            feature_value=None if driver.get("feature_value") is None else float(driver["feature_value"]),
            shap_value=float(driver["shap_value"]),
            direction="increases" if float(driver["shap_value"]) >= 0 else "decreases",
        )
        for driver in entry.get("top_drivers", [])
    )


def power_statement(artifact: dict[str, Any], gain: AblationGain) -> str | None:
    """Place an observed gain against the exact class counts of the frozen cohort.

    Counts come from ``case_predictions``; they are never inferred from PR-AUC.
    Returns ``None`` when the cohort is degenerate, so no infinity reaches a report.
    """
    labels = [bool(row["poor_performer_5d"]) for row in artifact.get("case_predictions", [])]
    positive, negative = sum(labels), len(labels) - sum(labels)
    assumed = (artifact.get("classification_metrics") or {}).get("roc_auc")
    result = assess_comparison(
        gain.roc_auc_gain, positive, negative,
        **({"assumed_auc": float(assumed)} if assumed is not None else {}),
    )
    if not math.isfinite(result.minimum_detectable_difference):
        return None
    return result.statement()
