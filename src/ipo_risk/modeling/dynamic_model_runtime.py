"""Generalized frozen-model inference: score any case with a governed feature vector.

The product used to answer "is this case one of the three rows in the sanitized
handoff?".  This module answers the question the model identity actually
supports: "does this case satisfy the frozen feature contract?".  If it does,
the promoted booster is loaded from disk, run once, and asked for its own native
``pred_contrib`` SHAP values.  If it does not, the case is UNAVAILABLE with a
reason -- never a borrowed score and never a copied driver set.

Three rules hold everywhere here:

* nothing trains.  The booster is loaded from ``models/role_d_v2/model.txt`` and
  its hash is checked against the frozen promotion manifest before use;
* a missing feature stays missing.  It reaches LightGBM as ``NaN``, which is how
  the frozen training matrix carried it; zero-filling is a contract violation;
* every number is stamped with the identity that produced it -- model hash,
  feature manifest hash, input feature hash and a deterministic run id.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ipo_risk.market.handoff import (
    MarketFeatureHandoffError,
    MarketHandoffBindingError,
    build_market_feature_handoff,
    verify_market_handoff_binding,
)
from ipo_risk.modeling.frozen_model_evidence import PRODUCT_HANDOFF_SCOPE_REASON
from ipo_risk.modeling.role_d_v2_model_package import (
    ALERT_POLICY_FILE,
    DEFAULT_FROZEN_DIR,
    DEFAULT_MODEL_DIR,
    FEATURE_MANIFEST_FILE,
    MODEL_FILE,
    MODEL_MANIFEST_FILE,
    V2_PROMOTION_MANIFEST_NAME,
    sha256_file,
)
from ipo_risk.schemas.canonical_modeling import canonical_hash
from ipo_risk.schemas.final_supervision import (
    ChannelStatus,
    ModelDriver,
    ModelPredictionView,
)

# LightGBM, scikit-learn and NumPy are optional extras. They are imported where
# inference actually happens, so merely wiring this channel into the container
# never forces a deployment to carry the modelling stack; a deployment without
# it gets an explicit UNAVAILABLE instead of an import crash.


DYNAMIC_MODEL_RUNTIME_VERSION = "v046_dynamic_model_runtime_v1"
FEATURE_COMPONENT = "market_core"
UNCALIBRATED_SCORE_SEMANTICS = "uncalibrated_model_score_not_probability"


class DynamicModelRuntimeError(ValueError):
    """The frozen model package or its input cannot be trusted for inference."""


@dataclass(frozen=True)
class FrozenModelBundle:
    """A loaded, hash-verified frozen model and its governing manifests."""

    booster: Any
    model_manifest: Mapping[str, Any]
    feature_manifest: Mapping[str, Any]
    alert_policy: Mapping[str, Any]
    model_dir: Path

    @property
    def identity(self) -> dict[str, Any]:
        return {
            "model_name": self.model_manifest["model_name"],
            "model_version": self.model_manifest["model_version"],
            "model_policy_version": self.model_manifest["model_policy_version"],
            "model_file_sha256": self.model_manifest["model_file_sha256"],
            "classifier_model_sha256": self.model_manifest["classifier_model_sha256"],
            "feature_manifest_hash": self.model_manifest["feature_manifest_hash"],
            "alert_policy_hash": self.model_manifest["alert_policy_hash"],
            "core_feature_manifest_hash": self.feature_manifest[
                "core_feature_manifest_hash"
            ],
        }

    @property
    def model_feature_names(self) -> tuple[str, ...]:
        return tuple(self.feature_manifest["model_input_feature_names"])


@dataclass(frozen=True)
class ModelInput:
    """One frozen-contract feature vector, with missingness kept explicit."""

    case_id: str
    values: tuple[float | None, ...]
    missing_features: tuple[str, ...]
    input_feature_hash: str
    market_binding: Mapping[str, Any]
    handoff_content_hash: str | None
    market_runtime_path: str | None
    pit_cutoff_date: str | None

    @property
    def available_count(self) -> int:
        return len(self.values) - len(self.missing_features)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DynamicModelRuntimeError(
            f"frozen model package file is unreadable: {Path(path).name}"
        ) from exc


def load_frozen_model_bundle(
    *,
    model_dir: Path = DEFAULT_MODEL_DIR,
    frozen_dir: Path = DEFAULT_FROZEN_DIR,
) -> FrozenModelBundle:
    """Load the frozen booster only if every hash in its chain still agrees.

    The chain is: model file bytes -> model manifest -> the V2 promotion
    manifest that A merged.  A model that cannot prove it is the promoted model
    is not used at reduced confidence; it is refused.
    """

    directory = Path(model_dir)
    model_path = directory / MODEL_FILE
    if not model_path.is_file():
        raise DynamicModelRuntimeError(
            f"frozen model artifact is not present: {model_path}"
        )
    model_manifest = _read_json(directory / MODEL_MANIFEST_FILE)
    feature_manifest = _read_json(directory / FEATURE_MANIFEST_FILE)
    alert_policy = _read_json(directory / ALERT_POLICY_FILE)

    for manifest, label in (
        (model_manifest, "model manifest"),
        (feature_manifest, "feature manifest"),
        (alert_policy, "alert policy"),
    ):
        claimed = dict(manifest)
        declared_hash = claimed.pop("content_hash", None)
        if canonical_hash(claimed) != declared_hash:
            raise DynamicModelRuntimeError(f"{label} content hash mismatch")

    model_text = model_path.read_text(encoding="utf-8")
    if hashlib.sha256(model_text.encode("utf-8")).hexdigest() != model_manifest.get(
        "classifier_model_sha256"
    ):
        raise DynamicModelRuntimeError(
            "model text does not match the classifier hash in its own manifest"
        )
    if sha256_file(model_path) != model_manifest.get("model_file_sha256"):
        raise DynamicModelRuntimeError("model file hash mismatch")
    if feature_manifest.get("content_hash") != model_manifest.get("feature_manifest_hash"):
        raise DynamicModelRuntimeError("feature manifest is not the one the model declares")
    if alert_policy.get("content_hash") != model_manifest.get("alert_policy_hash"):
        raise DynamicModelRuntimeError("alert policy is not the one the model declares")

    frozen = _read_json(Path(frozen_dir) / V2_PROMOTION_MANIFEST_NAME)
    if frozen.get("classifier_model_sha256") != model_manifest.get(
        "classifier_model_sha256"
    ):
        raise DynamicModelRuntimeError(
            "the local model artifact is not the promoted frozen model"
        )
    if model_manifest.get("blind_2025_y_accessed") is not False:
        raise DynamicModelRuntimeError("model manifest does not prove Blind isolation")

    try:
        import lightgbm as lgb
    except ImportError as exc:  # pragma: no cover - exercised by extras-free installs
        raise DynamicModelRuntimeError(
            "LightGBM is not installed, so the frozen model cannot be loaded"
        ) from exc

    booster = lgb.Booster(model_str=model_text)
    expected = int(feature_manifest["model_expected_dimension"])
    if booster.num_feature() != expected:
        raise DynamicModelRuntimeError(
            f"frozen booster expects {booster.num_feature()} features, "
            f"the feature manifest declares {expected}"
        )
    return FrozenModelBundle(
        booster=booster,
        model_manifest=model_manifest,
        feature_manifest=feature_manifest,
        alert_policy=alert_policy,
        model_dir=directory,
    )


def build_model_input(
    handoff: Mapping[str, Any],
    *,
    bundle: FrozenModelBundle,
    frozen_dir: Path = DEFAULT_FROZEN_DIR,
) -> ModelInput:
    """Project a verified market handoff onto the frozen feature contract.

    Features are taken by name, never by assumed position, and the handoff's own
    missing mask decides what is unknown.  Any disagreement between the handoff
    and the frozen feature manifest raises rather than being repaired.
    """

    binding = verify_market_handoff_binding(handoff, frozen_dir=Path(frozen_dir))

    declared_names = tuple(bundle.feature_manifest["handoff_feature_names"])
    handoff_names = tuple(str(name) for name in handoff.get("feature_names") or ())
    if handoff_names != declared_names:
        raise DynamicModelRuntimeError(
            "market handoff feature order does not match the frozen feature manifest"
        )
    handoff_values = tuple(handoff.get("feature_values") or ())
    if len(handoff_values) != len(declared_names):
        raise DynamicModelRuntimeError("market handoff vector width mismatch")

    mask = handoff.get("missing_mask") or {}
    positions = tuple(int(index) for index in bundle.feature_manifest["model_input_positions"])
    names = bundle.model_feature_names
    if len(positions) != len(names):
        raise DynamicModelRuntimeError("feature manifest positions and names disagree")

    values: list[float | None] = []
    missing: list[str] = []
    for name, position in zip(names, positions):
        if declared_names[position] != name:
            raise DynamicModelRuntimeError(
                f"frozen feature position {position} is not {name}"
            )
        raw = handoff_values[position]
        declared_missing = bool(int(mask.get(name, 0)))
        if (raw is None) != declared_missing:
            raise DynamicModelRuntimeError(
                f"market handoff missing mask disagrees with its value for {name}"
            )
        if raw is None:
            values.append(None)
            missing.append(name)
        else:
            values.append(float(raw))

    case_id = str(handoff.get("case_id") or "")
    return ModelInput(
        case_id=case_id,
        values=tuple(values),
        missing_features=tuple(missing),
        input_feature_hash=canonical_hash(
            {
                "case_id": case_id,
                "feature_names": list(names),
                "feature_values": list(values),
            }
        ),
        market_binding=binding,
        handoff_content_hash=handoff.get("content_hash"),
        market_runtime_path=handoff.get("market_runtime_path"),
        pit_cutoff_date=handoff.get("pit_cutoff_date"),
    )


def _drivers(
    names: Sequence[str],
    values: Sequence[float | None],
    contributions: np.ndarray,
) -> list[dict[str, Any]]:
    return sorted(
        (
            {
                "feature": f"{FEATURE_COMPONENT}__{name}",
                "component": FEATURE_COMPONENT,
                "feature_value": None if values[index] is None else float(values[index]),
                "shap_value": float(contributions[index]),
            }
            for index, name in enumerate(names)
        ),
        key=lambda item: (-abs(item["shap_value"]), item["feature"]),
    )


def _unavailable_signal(case_id: str | None, reason: str, bundle: FrozenModelBundle | None) -> dict[str, Any]:
    signal: dict[str, Any] = {
        "runtime_version": DYNAMIC_MODEL_RUNTIME_VERSION,
        "case_id": case_id,
        "status": ChannelStatus.UNAVAILABLE.value,
        "reason": reason,
        "score": None,
        "score_semantics": UNCALIBRATED_SCORE_SEMANTICS,
        "alert": None,
        "alert_policy": None,
        "drivers": [],
        "blind_2025_y_accessed": False,
    }
    if bundle is not None:
        signal.update(bundle.identity)
    return signal


def infer_batch(
    handoffs: Sequence[Mapping[str, Any]],
    *,
    bundle: FrozenModelBundle,
    frozen_dir: Path = DEFAULT_FROZEN_DIR,
    use_batch_alert_policy: bool = False,
) -> list[dict[str, Any]]:
    """Score every governed handoff once, with native SHAP from that same call.

    ``use_batch_alert_policy`` applies the promoted top-47.5% batch budget, which
    is only meaningful when the sequence really is a governed cohort scored in
    one run.  A single fresh IPO instead gets the Development-derived single-case
    cutoff, because a batch rank over one case is not the frozen policy.
    """

    inputs: list[ModelInput | None] = []
    failures: list[dict[str, Any] | None] = []
    for handoff in handoffs:
        try:
            inputs.append(build_model_input(handoff, bundle=bundle, frozen_dir=frozen_dir))
            failures.append(None)
        except (DynamicModelRuntimeError, MarketHandoffBindingError) as exc:
            inputs.append(None)
            failures.append(
                _unavailable_signal(
                    str(handoff.get("case_id") or "") or None,
                    f"frozen_feature_contract_not_satisfied: {exc}",
                    bundle,
                )
            )

    import numpy as np

    scored = [
        (index, model_input)
        for index, model_input in enumerate(inputs)
        if model_input is not None and model_input.available_count > 0
    ]
    for index, model_input in enumerate(inputs):
        if model_input is not None and model_input.available_count == 0:
            failures[index] = _unavailable_signal(
                model_input.case_id,
                "every frozen model feature is missing for this case",
                bundle,
            )

    signals: list[dict[str, Any] | None] = list(failures)
    if scored:
        matrix = np.asarray(
            [
                [np.nan if value is None else value for value in model_input.values]
                for _, model_input in scored
            ],
            dtype=float,
        )
        scores = np.asarray(bundle.booster.predict(matrix), dtype=float)
        contributions = np.asarray(
            bundle.booster.predict(matrix, pred_contrib=True), dtype=float
        )
        if contributions.shape != (len(scored), matrix.shape[1] + 1):
            raise DynamicModelRuntimeError("native SHAP contribution shape drift")
        single_case = bundle.alert_policy["single_case_policy"]
        batch_policy = bundle.alert_policy["batch_policy"]
        if use_batch_alert_policy:
            from ipo_risk.modeling.alert_policy import alert_budget_predictions

            alerts = alert_budget_predictions(
                [model_input.case_id for _, model_input in scored],
                scores,
                float(batch_policy["fraction"]),
            )
            alert_policy_version = batch_policy["version"]
            alert_scope = "governed_batch"
        else:
            alerts = scores >= float(single_case["cutoff"])
            alert_policy_version = single_case["version"]
            alert_scope = "single_case"
        for row, (index, model_input) in enumerate(scored):
            drivers = _drivers(
                bundle.model_feature_names, model_input.values, contributions[row, :-1]
            )
            signal = {
                "runtime_version": DYNAMIC_MODEL_RUNTIME_VERSION,
                "case_id": model_input.case_id,
                "status": ChannelStatus.AVAILABLE.value,
                "reason": (
                    "frozen model inference over the governed market feature vector"
                ),
                "score": float(scores[row]),
                "score_semantics": UNCALIBRATED_SCORE_SEMANTICS,
                "calibration_status": bundle.model_manifest["calibration_status"],
                "alert": bool(alerts[row]),
                "alert_policy": alert_policy_version,
                "alert_policy_scope": alert_scope,
                "shap_source": "lightgbm_native_pred_contrib",
                "shap_base_value": float(contributions[row, -1]),
                "drivers": drivers,
                "model_input_feature_names": list(bundle.model_feature_names),
                "available_model_feature_count": model_input.available_count,
                "missing_model_features": list(model_input.missing_features),
                "input_feature_hash": model_input.input_feature_hash,
                "market_handoff_content_hash": model_input.handoff_content_hash,
                "market_runtime_path": model_input.market_runtime_path,
                "pit_cutoff_date": model_input.pit_cutoff_date,
                "market_binding_checks": dict(model_input.market_binding.get("checks") or {}),
                "blind_2025_y_accessed": False,
            }
            signal.update(bundle.identity)
            # A deterministic run id: the same model over the same input is the
            # same inference, so replaying an audit does not invent a new one.
            signal["inference_run_id"] = canonical_hash(
                {
                    "classifier_model_sha256": signal["classifier_model_sha256"],
                    "feature_manifest_hash": signal["feature_manifest_hash"],
                    "input_feature_hash": signal["input_feature_hash"],
                    "alert_policy": alert_policy_version,
                }
            )
            signals[index] = signal

    resolved = [signal for signal in signals if signal is not None]
    if len(resolved) != len(handoffs):
        raise DynamicModelRuntimeError("dynamic inference lost a case")
    return resolved


def infer_case(
    handoff: Mapping[str, Any],
    *,
    bundle: FrozenModelBundle,
    frozen_dir: Path = DEFAULT_FROZEN_DIR,
) -> dict[str, Any]:
    """Score exactly one case under the single-case alert cutoff."""

    return infer_batch([handoff], bundle=bundle, frozen_dir=frozen_dir)[0]


def signal_to_prediction_view(signal: Mapping[str, Any]) -> ModelPredictionView:
    """Render a governed ModelSignal as the Final Supervisor's channel view."""

    base = {
        "model_name": signal.get("model_name"),
        "model_version": signal.get("model_version"),
        "score_semantics": "uncalibrated_model_score",
        "calibration_status": "uncalibrated",
    }
    if signal.get("status") != ChannelStatus.AVAILABLE.value:
        return ModelPredictionView(
            status=ChannelStatus.UNAVAILABLE,
            reason=str(signal.get("reason") or "dynamic model inference unavailable"),
            **base,
        )
    drivers = tuple(
        ModelDriver(
            feature=driver["feature"],
            component=driver["component"],
            feature_value=driver.get("feature_value"),
            shap_value=driver["shap_value"],
            direction="increases" if driver["shap_value"] >= 0 else "decreases",
        )
        for driver in signal.get("drivers") or ()
    )
    return ModelPredictionView(
        status=ChannelStatus.AVAILABLE,
        reason=(
            "score and native SHAP drivers produced by this run of the frozen model"
        ),
        score=signal.get("score"),
        alert=signal.get("alert"),
        alert_policy=signal.get("alert_policy"),
        drivers=drivers,
        **base,
    )


class DynamicFrozenModelPredictionProvider:
    """Model channel that scores whatever satisfies the frozen feature contract."""

    # The workflow hands the market view to providers that declare this; older
    # providers keep their single-argument call.
    consumes_market_context = True

    def __init__(
        self,
        *,
        model_dir: Path = DEFAULT_MODEL_DIR,
        frozen_dir: Path = DEFAULT_FROZEN_DIR,
    ) -> None:
        self.model_dir = Path(model_dir)
        self.frozen_dir = Path(frozen_dir)
        self._bundle: FrozenModelBundle | None = None
        self._load_error: str | None = None

    def bundle(self) -> FrozenModelBundle | None:
        """Load once; a package that fails verification stays refused."""

        if self._bundle is None and self._load_error is None:
            try:
                self._bundle = load_frozen_model_bundle(
                    model_dir=self.model_dir, frozen_dir=self.frozen_dir
                )
            except DynamicModelRuntimeError as exc:
                self._load_error = str(exc)
        return self._bundle

    def prediction(self, profile, market_context=None) -> ModelPredictionView:
        bundle = self.bundle()
        if bundle is None:
            return ModelPredictionView(
                status=ChannelStatus.UNAVAILABLE_ERROR,
                reason=f"frozen_model_artifact_is_not_loadable: {self._load_error}",
            )
        base = {
            "model_name": bundle.model_manifest["model_name"],
            "model_version": bundle.model_manifest["model_version"],
        }
        if market_context is None:
            return ModelPredictionView(
                status=ChannelStatus.UNAVAILABLE,
                reason="the market channel produced no context for this case",
                **base,
            )
        if market_context.status is not ChannelStatus.AVAILABLE:
            return ModelPredictionView(
                status=ChannelStatus.UNAVAILABLE,
                reason=(
                    f"market channel is {market_context.status.value}, "
                    "so the frozen model has no governed feature vector"
                ),
                **base,
            )
        try:
            handoff = build_market_feature_handoff(market_context)
            signal = infer_case(handoff, bundle=bundle, frozen_dir=self.frozen_dir)
        except (
            MarketFeatureHandoffError,
            MarketHandoffBindingError,
            DynamicModelRuntimeError,
        ) as exc:
            return ModelPredictionView(
                status=ChannelStatus.UNAVAILABLE,
                reason=f"governed model input could not be built: {exc}",
                **base,
            )
        return signal_to_prediction_view(signal)


class CompositeModelPredictionProvider:
    """Frozen per-case handoff first, generalized inference for everything else.

    The handoff rows stay authoritative where they exist, so the canonical
    replay cases keep their byte-identical published numbers.  Only the
    out-of-scope answer -- "this case is not in the sanitized handoff" -- is
    replaced by a real inference.  Any other handoff failure is an integrity
    signal and is passed through untouched rather than papered over.
    """

    consumes_market_context = True

    def __init__(self, primary, dynamic: DynamicFrozenModelPredictionProvider) -> None:
        self.primary = primary
        self.dynamic = dynamic

    def prediction(self, profile, market_context=None) -> ModelPredictionView:
        view = self.primary.prediction(profile)
        if view.status is ChannelStatus.AVAILABLE:
            return view
        if view.reason != PRODUCT_HANDOFF_SCOPE_REASON:
            return view
        return self.dynamic.prediction(profile, market_context=market_context)
