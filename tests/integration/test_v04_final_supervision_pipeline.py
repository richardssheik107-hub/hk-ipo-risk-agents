"""End-to-end guard for the PR-G channels through the real analysis service.

The service persists every result and re-reads it with a strict equality check,
so anything non-JSON-native in ``metadata`` silently demotes the run to partial.
That makes ``status is COMPLETED`` a single canary for serialization regressions.
"""
from __future__ import annotations

import json
import math
from dataclasses import replace
from datetime import date

import pytest

from ipo_risk.core.config import load_settings
from ipo_risk.schemas import IPOAnalysisRequest, TaskStatus
from ipo_risk.services.analysis_service import IPOAnalysisService


@pytest.fixture
def service(tmp_path) -> IPOAnalysisService:
    settings = replace(load_settings("configs/v04_offline.yaml"),
                       parser="mock", retriever="mock", financial_agent="mock",
                       legal_agent="mock", business_agent="mock", use_mock=True,
                       data_dir=str(tmp_path / "repo"))
    return IPOAnalysisService(settings=settings)


@pytest.fixture
def result(service):
    return service.analyze(IPOAnalysisRequest(
        company_name="Demo Biotech", stock_code="9999.HK",
        listing_date=date(2024, 6, 1), use_mock=True))


def test_the_analysis_round_trips_with_the_pr_g_channels_attached(result) -> None:
    assert result.status is TaskStatus.COMPLETED, result.errors


def test_final_supervision_reaches_the_result_metadata(result) -> None:
    final = result.metadata["final_supervision"]
    assert final["metadata"]["classification"] == "SUPERVISORY_SYNTHESIS"
    assert final["metadata"]["creates_no_new_risk"] is True
    assert final["metadata"]["probability_claimed"] is False
    assert final["metadata"]["blocking_gates"] == []


def test_every_referenced_id_resolves_to_something_in_the_result(result) -> None:
    """The necessary condition for the traceability target."""
    final = result.metadata["final_supervision"]
    risk_ids = {risk.risk_id for risk in result.verified_risks}
    evidence_ids = {item.evidence_id for risk in result.verified_risks for item in risk.evidence}
    assert set(final["referenced_risk_ids"]) <= risk_ids
    assert set(final["referenced_evidence_ids"]) <= evidence_ids


def test_the_market_channel_passes_the_provider_reason_through(result) -> None:
    """v04_offline runs market_data_provider: unavailable, so the channel says so."""
    market = result.metadata["market_context"]
    assert market["status"] == "unavailable_error"
    assert market["reason"] == "real_market_data_not_integrated_in_v0.2"
    assert market["observations"] == []
    # A snapshot-derived view never claims the PR-B Market-X lineage.
    assert market["feature_manifest_hash"] is None
    assert market["provenance"]["feature_pipeline"] == "legacy_market_snapshot_not_v04_market_x"


def test_a_mock_market_provider_leaks_no_fixture_number(tmp_path) -> None:
    """A mock snapshot is a fixture; rendering its numbers would fabricate data."""
    settings = replace(load_settings("configs/v04_offline.yaml"),
                       parser="mock", retriever="mock", financial_agent="mock",
                       legal_agent="mock", business_agent="mock", use_mock=True,
                       market_data_provider="mock", data_dir=str(tmp_path / "repo"))
    outcome = IPOAnalysisService(settings=settings).analyze(IPOAnalysisRequest(
        company_name="Demo Biotech", stock_code="9999.HK",
        listing_date=date(2024, 6, 1), use_mock=True))
    market = outcome.metadata["market_context"]
    assert market["status"] == "disabled"
    assert market["observations"] == []
    serialized = json.dumps(market)
    for fabricated in ("-0.04", "0.42", "0.31", "35"):
        assert fabricated not in serialized, fabricated


def test_the_model_channel_is_absent_rather_than_invented(result) -> None:
    """No PR-F runtime artifacts are committed, so no per-case score may appear."""
    states = {item["channel"]: item for item in result.metadata["final_supervision"]["channel_states"]}
    assert states["model"]["status"] == "disabled"
    assert states["model"]["blocking_gate"] is None
    assert result.metadata["final_supervision"]["model_prediction"] is None


def test_cohort_level_model_evidence_is_still_stated(result) -> None:
    """Without a per-case score the frozen cohort limits still have to be said."""
    statement = result.metadata["final_supervision"]["uncertainty_statement"]
    assert "not validated at this sample size" in statement
    assert "-0.0143" not in statement


def test_no_non_finite_number_reaches_the_persisted_metadata(result) -> None:
    def walk(value):
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, float):
            assert math.isfinite(value), value

    walk(result.metadata)


def test_component_modes_expose_the_two_new_channels(result) -> None:
    modes = result.metadata["component_modes"]
    assert modes["market_context"] == "snapshot"
    assert modes["final_supervisor"] == "v04"
