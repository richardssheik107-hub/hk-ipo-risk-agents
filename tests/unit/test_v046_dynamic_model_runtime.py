"""The frozen model must behave as a runtime: load, infer, explain, or refuse."""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

import numpy as np
import pytest

from ipo_risk.agents.market_context import GovernedPRBMarketContextProvider
from ipo_risk.market.handoff import build_market_feature_handoff
from ipo_risk.modeling.dynamic_model_runtime import (
    CompositeModelPredictionProvider,
    DynamicFrozenModelPredictionProvider,
    DynamicModelRuntimeError,
    build_model_input,
    infer_batch,
    infer_case,
    load_frozen_model_bundle,
    signal_to_prediction_view,
)
from ipo_risk.modeling.frozen_model_evidence import PRODUCT_HANDOFF_SCOPE_REASON
from ipo_risk.modeling.role_d_v2_model_artifact import (
    ALERT_POLICY_FILE,
    MODEL_FILE,
    MODEL_MANIFEST_FILE,
    V2_PROMOTION_MANIFEST_NAME,
)
from ipo_risk.schemas import IPOProfile
from ipo_risk.schemas.final_supervision import ChannelStatus, ModelPredictionView


REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = REPO_ROOT / "models/role_d_v2"
FROZEN_DIR = REPO_ROOT / "reports/frozen"
FEATURE_DIR = REPO_ROOT / "reports/v04_pr_b/core_features"
BRIDGE = REPO_ROOT / "data/catalog/ipo_official_master_bridge.csv"
PUBLISHED = REPO_ROOT / "reports/v045_role_d_v2/test_predictions.csv"

IN_HANDOFF_CASE = "ipo_2024_02410"
OUTSIDE_HANDOFF_CASE = "ipo_2023_02453"

pytestmark = pytest.mark.skipif(
    not (MODEL_DIR / MODEL_FILE).is_file(),
    reason="the frozen model package is not materialized in this checkout",
)


@pytest.fixture(scope="module")
def bundle():
    return load_frozen_model_bundle(model_dir=MODEL_DIR, frozen_dir=FROZEN_DIR)


@pytest.fixture(scope="module")
def market_provider():
    return GovernedPRBMarketContextProvider(
        feature_dir=FEATURE_DIR, official_bridge_path=BRIDGE
    )


def _profile(case_id: str) -> IPOProfile:
    with BRIDGE.open(encoding="utf-8-sig", newline="") as handle:
        row = next(row for row in csv.DictReader(handle) if row["case_id"] == case_id)
    return IPOProfile(
        company_name=(row.get("selected_name") or "").strip(),
        stock_code=(row.get("stock_code_wind") or "").strip(),
        listing_date=date.fromisoformat(row["official_listed_date"].strip()),
        industry=(row.get("official_industry_name") or "").strip(),
        metadata={"case_id": case_id},
    )


def _handoff(market_provider, case_id: str) -> dict:
    view = market_provider.context(_profile(case_id))
    assert view.status is ChannelStatus.AVAILABLE
    return build_market_feature_handoff(view)


def _copied_package(tmp_path: Path) -> Path:
    target = tmp_path / "role_d_v2"
    target.mkdir()
    for path in MODEL_DIR.iterdir():
        if path.is_file():
            target.joinpath(path.name).write_bytes(path.read_bytes())
    return target


# --- model load -------------------------------------------------------------


def test_bundle_loads_the_promoted_frozen_identity(bundle) -> None:
    frozen = json.loads((FROZEN_DIR / V2_PROMOTION_MANIFEST_NAME).read_text(encoding="utf-8"))
    assert bundle.model_manifest["classifier_model_sha256"] == frozen["classifier_model_sha256"]
    assert bundle.model_manifest["model_version"] == frozen["pr_f_version"]
    assert bundle.booster.num_feature() == len(bundle.model_feature_names)
    assert tuple(frozen["selection"]["selected_features"]) == bundle.model_feature_names


def test_a_tampered_model_file_fails_closed(tmp_path) -> None:
    package = _copied_package(tmp_path)
    text = (package / MODEL_FILE).read_text(encoding="utf-8")
    (package / MODEL_FILE).write_text(text + "\n", encoding="utf-8")
    with pytest.raises(DynamicModelRuntimeError, match="classifier hash"):
        load_frozen_model_bundle(model_dir=package, frozen_dir=FROZEN_DIR)


def test_a_tampered_manifest_fails_closed(tmp_path) -> None:
    package = _copied_package(tmp_path)
    manifest = json.loads((package / MODEL_MANIFEST_FILE).read_text(encoding="utf-8"))
    manifest["model_version"] = "something_else"
    (package / MODEL_MANIFEST_FILE).write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(DynamicModelRuntimeError, match="content hash"):
        load_frozen_model_bundle(model_dir=package, frozen_dir=FROZEN_DIR)


def test_a_model_that_is_not_the_promoted_one_is_refused(tmp_path) -> None:
    package = _copied_package(tmp_path)
    frozen_dir = tmp_path / "frozen"
    frozen_dir.mkdir()
    frozen = json.loads((FROZEN_DIR / V2_PROMOTION_MANIFEST_NAME).read_text(encoding="utf-8"))
    frozen["classifier_model_sha256"] = "0" * 64
    (frozen_dir / V2_PROMOTION_MANIFEST_NAME).write_text(json.dumps(frozen), encoding="utf-8")
    with pytest.raises(DynamicModelRuntimeError, match="not the promoted frozen model"):
        load_frozen_model_bundle(model_dir=package, frozen_dir=frozen_dir)


def test_a_missing_package_fails_closed(tmp_path) -> None:
    with pytest.raises(DynamicModelRuntimeError, match="not present"):
        load_frozen_model_bundle(model_dir=tmp_path, frozen_dir=FROZEN_DIR)


# --- feature input ----------------------------------------------------------


def test_model_input_takes_features_by_name_and_keeps_missing_missing(
    bundle, market_provider
) -> None:
    handoff = _handoff(market_provider, IN_HANDOFF_CASE)
    model_input = build_model_input(handoff, bundle=bundle, frozen_dir=FROZEN_DIR)
    assert len(model_input.values) == bundle.booster.num_feature()
    for name, value in zip(bundle.model_feature_names, model_input.values):
        position = handoff["feature_names"].index(name)
        assert value == handoff["feature_values"][position]
        assert (value is None) == bool(handoff["missing_mask"][name])
    assert set(model_input.missing_features) <= set(bundle.model_feature_names)


def test_a_reordered_handoff_is_refused(bundle, market_provider) -> None:
    handoff = dict(_handoff(market_provider, IN_HANDOFF_CASE))
    names = list(handoff["feature_names"])
    handoff["feature_names"] = names[2:] + names[:2]
    with pytest.raises(DynamicModelRuntimeError, match="feature order"):
        build_model_input(handoff, bundle=bundle, frozen_dir=FROZEN_DIR)


def test_a_handoff_whose_mask_disagrees_with_its_values_is_refused(
    bundle, market_provider
) -> None:
    handoff = dict(_handoff(market_provider, IN_HANDOFF_CASE))
    mask = dict(handoff["missing_mask"])
    target = bundle.model_feature_names[0]
    mask[target] = 1 - int(mask[target])
    handoff["missing_mask"] = mask
    with pytest.raises(DynamicModelRuntimeError, match="missing mask"):
        build_model_input(handoff, bundle=bundle, frozen_dir=FROZEN_DIR)


def test_a_missing_feature_is_not_the_same_input_as_zero(bundle, market_provider) -> None:
    """Zero-filling is a different model input, so it must not be silently done."""

    handoff = _handoff(market_provider, "ipo_2024_02460")
    model_input = build_model_input(handoff, bundle=bundle, frozen_dir=FROZEN_DIR)
    assert model_input.missing_features, "this case is chosen because it has missing inputs"
    honest = np.asarray(
        [[np.nan if value is None else value for value in model_input.values]], dtype=float
    )
    zero_filled = np.nan_to_num(honest, nan=0.0)
    assert bundle.booster.predict(honest)[0] != bundle.booster.predict(zero_filled)[0]


def test_the_model_consumes_market_core_features_only(bundle) -> None:
    manifest = bundle.feature_manifest
    assert manifest["document_features_used"] is False
    assert manifest["gold_derived_features_used"] is False
    assert manifest["feature_component"] == "market_core"
    assert manifest["zero_fill_forbidden"] is True


# --- inference --------------------------------------------------------------


def test_inference_is_deterministic_and_does_not_retrain(bundle, market_provider) -> None:
    handoff = _handoff(market_provider, OUTSIDE_HANDOFF_CASE)
    first = infer_case(handoff, bundle=bundle, frozen_dir=FROZEN_DIR)
    second = infer_case(handoff, bundle=bundle, frozen_dir=FROZEN_DIR)
    assert first == second
    assert first["status"] == ChannelStatus.AVAILABLE.value
    assert first["score_semantics"] == "uncalibrated_model_score_not_probability"
    assert first["classifier_model_sha256"] == bundle.model_manifest["classifier_model_sha256"]
    assert first["inference_run_id"] == second["inference_run_id"]


def test_a_case_outside_the_per_case_handoff_still_infers(bundle, market_provider) -> None:
    signal = infer_case(_handoff(market_provider, OUTSIDE_HANDOFF_CASE), bundle=bundle, frozen_dir=FROZEN_DIR)
    assert signal["status"] == ChannelStatus.AVAILABLE.value
    assert isinstance(signal["score"], float)


def test_the_single_case_alert_is_the_frozen_cutoff(bundle, market_provider) -> None:
    policy = bundle.alert_policy["single_case_policy"]
    assert policy["validation_used_for_derivation"] is False
    signal = infer_case(_handoff(market_provider, OUTSIDE_HANDOFF_CASE), bundle=bundle, frozen_dir=FROZEN_DIR)
    assert signal["alert"] == (signal["score"] >= policy["cutoff"])
    assert signal["alert_policy"] == policy["version"]


def test_the_batch_alert_policy_reproduces_the_published_cohort(bundle, market_provider) -> None:
    with PUBLISHED.open(encoding="utf-8", newline="") as handle:
        published = {
            row["case_id"]: (
                float(row["poor_performer_score"]),
                row["predicted_significant_drop_5d"].lower() == "true",
            )
            for row in csv.DictReader(handle)
        }
    handoffs = [_handoff(market_provider, case_id) for case_id in sorted(published)]
    signals = infer_batch(
        handoffs, bundle=bundle, frozen_dir=FROZEN_DIR, use_batch_alert_policy=True
    )
    assert len(signals) == len(published)
    for signal in signals:
        score, alert = published[signal["case_id"]]
        assert signal["score"] == pytest.approx(score, abs=1e-12)
        assert signal["alert"] is alert


# --- native SHAP ------------------------------------------------------------


def test_drivers_come_from_this_inference_and_are_ranked(bundle, market_provider) -> None:
    signal = infer_case(_handoff(market_provider, OUTSIDE_HANDOFF_CASE), bundle=bundle, frozen_dir=FROZEN_DIR)
    drivers = signal["drivers"]
    assert signal["shap_source"] == "lightgbm_native_pred_contrib"
    assert len(drivers) == len(bundle.model_feature_names)
    assert {driver["feature"] for driver in drivers} == {
        f"market_core__{name}" for name in bundle.model_feature_names
    }
    magnitudes = [abs(driver["shap_value"]) for driver in drivers]
    assert magnitudes == sorted(magnitudes, reverse=True)
    total = sum(driver["shap_value"] for driver in drivers) + signal["shap_base_value"]
    assert total == pytest.approx(np.log(signal["score"] / (1 - signal["score"])), abs=1e-9)


def test_two_cases_do_not_share_one_driver_set(bundle, market_provider) -> None:
    first = infer_case(_handoff(market_provider, OUTSIDE_HANDOFF_CASE), bundle=bundle, frozen_dir=FROZEN_DIR)
    second = infer_case(_handoff(market_provider, IN_HANDOFF_CASE), bundle=bundle, frozen_dir=FROZEN_DIR)
    assert first["drivers"] != second["drivers"]
    assert first["input_feature_hash"] != second["input_feature_hash"]


# --- Final Supervisor integration ------------------------------------------


class _StubPrimary:
    def __init__(self, view: ModelPredictionView) -> None:
        self.view = view
        self.calls = 0

    def prediction(self, profile) -> ModelPredictionView:
        self.calls += 1
        return self.view


def _dynamic_provider() -> DynamicFrozenModelPredictionProvider:
    return DynamicFrozenModelPredictionProvider(model_dir=MODEL_DIR, frozen_dir=FROZEN_DIR)


def test_the_handoff_answer_still_wins_where_it_exists(market_provider) -> None:
    handoff_view = ModelPredictionView(
        status=ChannelStatus.AVAILABLE, reason="per-case score", score=0.5
    )
    composite = CompositeModelPredictionProvider(_StubPrimary(handoff_view), _dynamic_provider())
    view = composite.prediction(
        _profile(IN_HANDOFF_CASE),
        market_context=market_provider.context(_profile(IN_HANDOFF_CASE)),
    )
    assert view is handoff_view


def test_an_out_of_scope_case_falls_through_to_real_inference(market_provider) -> None:
    primary = _StubPrimary(
        ModelPredictionView(
            status=ChannelStatus.UNAVAILABLE_ERROR, reason=PRODUCT_HANDOFF_SCOPE_REASON
        )
    )
    composite = CompositeModelPredictionProvider(primary, _dynamic_provider())
    view = composite.prediction(
        _profile(OUTSIDE_HANDOFF_CASE),
        market_context=market_provider.context(_profile(OUTSIDE_HANDOFF_CASE)),
    )
    assert view.status is ChannelStatus.AVAILABLE
    assert len(view.drivers) == 7
    assert view.score_semantics == "uncalibrated_model_score"


def test_a_broken_handoff_is_never_masked_by_inference(market_provider) -> None:
    broken = ModelPredictionView(
        status=ChannelStatus.UNAVAILABLE_ERROR,
        reason="sanitized_pr_f_product_handoff_failed_validation",
    )
    composite = CompositeModelPredictionProvider(_StubPrimary(broken), _dynamic_provider())
    view = composite.prediction(
        _profile(OUTSIDE_HANDOFF_CASE),
        market_context=market_provider.context(_profile(OUTSIDE_HANDOFF_CASE)),
    )
    assert view is broken


def test_no_market_context_means_no_model_answer() -> None:
    view = _dynamic_provider().prediction(_profile(OUTSIDE_HANDOFF_CASE), market_context=None)
    assert view.status is ChannelStatus.UNAVAILABLE
    assert "produced no context" in view.reason


def test_the_prediction_view_never_calls_the_score_a_probability(
    bundle, market_provider
) -> None:
    signal = infer_case(_handoff(market_provider, OUTSIDE_HANDOFF_CASE), bundle=bundle, frozen_dir=FROZEN_DIR)
    view = signal_to_prediction_view(signal)
    assert view.status is ChannelStatus.AVAILABLE
    assert view.calibration_status == "uncalibrated"
    assert "probab" not in view.reason.lower()
    assert all(
        driver.direction == ("increases" if driver.shap_value >= 0 else "decreases")
        for driver in view.drivers
    )
