from __future__ import annotations

from ipo_risk.schemas.final_supervision import MarketObservation


def test_known_unavailable_industry_observation_keeps_contract_metadata() -> None:
    observation = MarketObservation(
        name="industry_return_5d",
        availability="unavailable",
        missing_reason="INDUSTRY_MAPPING_PIT_BLOCKED",
        source="v04_c_extended_readiness",
    )

    assert observation.value is None
    assert observation.missing_reason == "INDUSTRY_MAPPING_PIT_BLOCKED"
    assert observation.unit == "ratio"
    assert observation.derivation
    assert "industry benchmark" in observation.derivation


def test_known_unavailable_core_observation_keeps_contract_metadata_without_imputation() -> None:
    observation = MarketObservation(
        name="same_industry_recent_return_5d",
        availability="unavailable",
        missing_reason="insufficient_governed_prelisting_history",
        source="pr_b_market_x_core",
    )

    assert observation.value is None
    assert observation.unit == "ratio"
    assert observation.derivation


def test_explicit_available_metadata_is_not_overwritten() -> None:
    observation = MarketObservation(
        name="hsi_return_5d",
        value=0.012,
        unit="custom_ratio",
        availability="available",
        derivation="explicit governed calculation",
        source="test",
    )

    assert observation.value == 0.012
    assert observation.unit == "custom_ratio"
    assert observation.derivation == "explicit governed calculation"


def test_unknown_unavailable_observation_remains_fail_closed_without_inferred_metadata() -> None:
    observation = MarketObservation(
        name="future_market_metric",
        availability="unavailable",
        missing_reason="source_unavailable",
        source="test",
    )

    assert observation.value is None
    assert observation.unit == ""
    assert observation.derivation == ""
