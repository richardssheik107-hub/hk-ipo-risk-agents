"""End-to-end guard for the PR-G channels through the real analysis service.

The service persists every result and re-reads it with a strict equality check,
so anything non-JSON-native in ``metadata`` silently demotes a run to partial.
That makes ``status is COMPLETED`` a single canary for serialization regressions.
"""
from __future__ import annotations

import json
import hashlib
import math
from pathlib import Path
from dataclasses import replace
from datetime import date

import pytest

from app.presenters import result_payload
from ipo_risk.core.config import load_settings
from ipo_risk.modeling.pr_f_product_handoff import (
    CHECKSUMMED_PRODUCT_FILES,
    PRODUCT_CHECKSUMS_NAME,
    PRODUCT_MANIFEST_NAME,
    PRODUCT_README,
    PRODUCT_README_NAME,
    PRODUCT_SIGNALS_NAME,
)
from ipo_risk.schemas import IPOAnalysisRequest, TaskStatus
from ipo_risk.services.analysis_service import IPOAnalysisService
from ..v04_market_context_fixture import (
    write_governed_extended_fixture,
    write_governed_pr_b_fixture,
)


@pytest.fixture
def service(tmp_path) -> IPOAnalysisService:
    feature_dir, bridge_path = write_governed_pr_b_fixture(tmp_path / "market")
    extended_path = write_governed_extended_fixture(tmp_path / "market")
    settings = replace(load_settings("configs/v04_offline.yaml"),
                       parser="mock", retriever="mock", financial_agent="mock",
                       legal_agent="mock", business_agent="mock", use_mock=True,
                       llm_provider="mock", data_dir=str(tmp_path / "repo"),
                       market_feature_dir=str(feature_dir),
                       market_official_bridge=str(bridge_path),
                       market_extended_readiness=str(extended_path))
    return IPOAnalysisService(settings=settings)


@pytest.fixture
def result(service):
    return service.analyze(IPOAnalysisRequest(
        company_name="同源康医药-B", stock_code="2410.HK",
        listing_date=date(2024, 8, 20), use_mock=True))


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


def test_the_market_channel_uses_the_governed_pr_b_projection(result) -> None:
    market = result.metadata["market_context"]
    assert market["status"] == "available"
    assert len(market["observations"]) == 21
    assert market["feature_manifest_hash"] == "c2f4a1699e2bf9149f24cb35ea32dbc4851c017001ec509a0eaccd93720d729d"
    assert market["provenance"]["feature_pipeline"] == "governed_pr_b_core"
    assert market["provenance"]["case_id"] == "ipo_2024_02410"
    by_name = {item["name"]: item for item in market["observations"]}
    assert by_name["industry_return_5d"]["value"] is None
    assert by_name["industry_return_5d"]["availability"] == "unavailable"
    assert by_name["industry_return_5d"]["missing_reason"] == "INDUSTRY_MAPPING_PIT_BLOCKED"


def test_known_frozen_0368_case_is_available_from_backend_artifact(tmp_path) -> None:
    feature_dir, bridge_path = write_governed_pr_b_fixture(tmp_path / "market")
    settings = replace(
        load_settings("configs/v04_ai.yaml"),
        parser="mock",
        retriever="mock",
        financial_agent="mock",
        legal_agent="mock",
        business_agent="mock",
        use_mock=True,
        llm_provider="unavailable",
        data_dir=str(tmp_path / "repo"),
        market_feature_dir=str(feature_dir),
        market_official_bridge=str(bridge_path),
    )
    outcome = IPOAnalysisService(settings=settings).analyze(IPOAnalysisRequest(
        company_name="德合集团",
        stock_code="0368.HK",
        listing_date=date(2020, 7, 17),
        use_mock=True,
    ))
    market = outcome.metadata["market_context"]
    assert market["status"] == "available"
    assert market["provenance"]["case_id"] == "ipo_2020_00368"
    assert market["provenance"]["feature_pipeline"] == "governed_pr_b_core"
    assert market["provenance"]["runtime_path"] == "frozen"


def test_streamlit_payload_preserves_backend_new_case_unavailable_semantics(tmp_path) -> None:
    feature_dir, bridge_path = write_governed_pr_b_fixture(tmp_path / "market")
    settings = replace(
        load_settings("configs/v04_ai.yaml"),
        parser="mock",
        retriever="mock",
        financial_agent="mock",
        legal_agent="mock",
        business_agent="mock",
        use_mock=True,
        llm_provider="unavailable",
        data_dir=str(tmp_path / "repo"),
        market_feature_dir=str(feature_dir),
        market_official_bridge=str(bridge_path),
    )
    outcome = IPOAnalysisService(settings=settings).analyze(IPOAnalysisRequest(
        company_name="2026 New IPO",
        stock_code="9999.HK",
        listing_date=date(2026, 6, 1),
        use_mock=True,
    ))

    backend = outcome.metadata["market_context"]
    assert backend["status"] == "unavailable"
    assert backend["provenance"]["runtime_path"] == "dynamic_new_case"
    assert backend["provenance"]["reason_code"] == "unsupported_new_case"
    assert backend["provenance"]["frozen_artifact_read_attempted"] is False
    assert outcome.metadata["market_intelligence"]["status"] == "skipped_context_unavailable"

    # Streamlit serializes the backend result; it does not hard-code the channel
    # to available in its presentation payload.
    payload = result_payload(outcome)
    assert payload["market_context"] == backend
    assert payload["market_context"]["status"] == "unavailable"


def test_market_report_names_the_governed_source_instead_of_none(result) -> None:
    market_section = next(section for section in result.report_sections if section.order == 7)
    assert "governed PR-B Market-X Core" in market_section.summary
    assert "from None" not in market_section.summary


def test_a_mock_market_provider_leaks_no_fixture_number(tmp_path) -> None:
    """A mock snapshot is a fixture; rendering its numbers would fabricate data."""
    settings = replace(load_settings("configs/v04_offline.yaml"),
                       parser="mock", retriever="mock", financial_agent="mock",
                       legal_agent="mock", business_agent="mock", use_mock=True,
                       llm_provider="mock",
                       market_data_provider="mock", market_context="snapshot",
                       data_dir=str(tmp_path / "repo"))
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
    assert modes["market_context"] == "governed_pr_b_core"
    assert modes["final_supervisor"] == "v04"


def test_sanitized_model_handoff_reaches_the_final_supervisor(tmp_path) -> None:
    handoff = tmp_path / "handoff"
    handoff.mkdir()
    signals = [{
        "case_id": "ipo_2024_02410",
        "score": 0.42,
        "drivers": [{
            "feature": "market_core__recent_ipo_break_rate",
            "component": "market_core",
            "feature_value": 0.6,
            "shap_value": 0.1,
        }],
    }]
    signal_path = handoff / PRODUCT_SIGNALS_NAME
    signal_path.write_text(json.dumps(signals), encoding="utf-8")
    frozen = json.loads(Path("reports/frozen/v04_pr_f_lightgbm_manifest.json").read_text(encoding="utf-8"))
    manifest = {
        "manifest_version": "v04_pr_f_product_runtime_handoff_v1",
        "source_model_result_hash": frozen["model_result_hash"],
        "case_signal_file": signal_path.name,
        "case_signal_sha256": hashlib.sha256(signal_path.read_bytes()).hexdigest(),
        "case_count": 1,
        "contains_target_labels": False,
        "blind_2025_y_accessed": False,
        "score_semantics": "uncalibrated_model_score",
    }
    (handoff / PRODUCT_MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    (handoff / PRODUCT_README_NAME).write_text(PRODUCT_README, encoding="utf-8")
    checksum_lines = [
        f"{hashlib.sha256((handoff / name).read_bytes()).hexdigest()}  {name}"
        for name in CHECKSUMMED_PRODUCT_FILES
    ]
    (handoff / PRODUCT_CHECKSUMS_NAME).write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8"
    )
    feature_dir, bridge_path = write_governed_pr_b_fixture(tmp_path / "market")
    settings = replace(
        load_settings("configs/v04_offline.yaml"),
        parser="mock", retriever="mock", financial_agent="mock",
        legal_agent="mock", business_agent="mock", use_mock=True,
        llm_provider="mock",
        pr_f_run_dir=str(handoff), data_dir=str(tmp_path / "repo"),
        market_feature_dir=str(feature_dir),
        market_official_bridge=str(bridge_path),
    )
    outcome = IPOAnalysisService(settings=settings).analyze(IPOAnalysisRequest(
        company_name="同源康医药-B", stock_code="2410.HK",
        listing_date=date(2024, 8, 20), use_mock=True,
    ))
    model = outcome.metadata["model_prediction"]
    assert model["status"] == "available"
    assert model["score"] == pytest.approx(0.42)
    assert model["score_semantics"] == "uncalibrated_model_score"
    assert "probability" not in model
    states = {
        row["channel"]: row["status"]
        for row in outcome.metadata["final_supervision"]["channel_states"]
    }
    assert states == {
        "document": "available", "market": "available",
        "model": "available", "rule": "available",
    }
