"""Guards for the competition-facing seven-stage runtime surface."""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

_MODULE_PATH = Path(__file__).resolve().parents[2] / "app" / "pipeline_stages.py"
_SPEC = importlib.util.spec_from_file_location("pipeline_stages", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
pipeline_stages = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = pipeline_stages
_SPEC.loader.exec_module(pipeline_stages)

StageStatus = pipeline_stages.StageStatus
pending_notice = pipeline_stages.pending_notice
resolve_stages = pipeline_stages.resolve_stages

EXPECTED_CHAIN = (
    "Document Analysis", "Document Risk Features", "Market Features", "Prediction",
    "Evidence / Explainability", "Final Supervisor", "Final Risk Report",
)
NUMERIC = re.compile(r"\d")


def _populated_payload() -> dict[str, object]:
    return {
        "risk_status_counts": {"verified": 3, "needs_review": 1, "pending": 0, "rejected": 2},
        "prediction": {"risk_score": 61.5, "risk_level": "high"},
        "supervision": {"duplicate_groups": [{}], "conflicts": [], "composite_findings": [{}, {}]},
        "final_supervision": {},
    }


def _runtime_complete_payload() -> dict[str, object]:
    return {
        **_populated_payload(),
        "status": "completed",
        "verified_risks": [
            {"risk_id": "r-1", "evidence": [{"evidence_id": "e-1"}]},
            {"risk_id": "r-2", "evidence": [{"evidence_id": "e-2"}]},
        ],
        "pending_risks": [],
        "rejected_risks": [],
        "market_context": {
            "status": "available",
            "observations": [
                {"name": "hsi_return_5d", "availability": "available", "value": 0.01},
                {"name": "industry_return_5d", "availability": "unavailable", "missing_reason": "missing_industry_series"},
            ],
        },
        "model_prediction": {
            "status": "available",
            "score": 0.61,
            "score_semantics": "uncalibrated_model_score",
            "drivers": [
                {"feature_name": "market__hsi_return_5d", "shap_value": 0.12, "direction": "positive"},
            ],
        },
        "final_supervision": {
            "channel_states": [
                {"channel": "document", "status": "available"},
                {"channel": "market", "status": "available"},
                {"channel": "model", "status": "available"},
                {"channel": "rule", "status": "available"},
            ],
            "referenced_risk_ids": ["r-1", "r-2"],
            "metadata": {"unresolved_conflict_count": 1},
        },
    }


def test_chain_matches_product_page_order() -> None:
    stages = resolve_stages(_populated_payload())
    assert len(stages) == 7
    assert tuple(stage.ordinal for stage in stages) == tuple(range(1, 8))
    assert tuple(stage.title for stage in stages) == EXPECTED_CHAIN
    assert len({stage.stage_id for stage in stages}) == 7


def test_frontend_chain_carries_no_project_level_release_gate() -> None:
    """Final competition gates live in release acceptance, not the case renderer."""
    assert pipeline_stages.blocking_gates() == ()


def test_pending_gate_stages_render_nothing_numeric() -> None:
    for payload in ({}, _populated_payload()):
        for stage in resolve_stages(payload):
            if stage.status is not StageStatus.PENDING_GATE:
                continue
            assert stage.metrics == ()
            assert not NUMERIC.search(stage.summary)
            assert not NUMERIC.search(stage.blocking_reason)
            assert not any(NUMERIC.search(item) for item in stage.what_appears_when_unblocked)


def test_partial_stages_only_show_values_payload_actually_has() -> None:
    empty = {stage.stage_id: stage for stage in resolve_stages({})}
    populated = {stage.stage_id: stage for stage in resolve_stages(_populated_payload())}
    assert empty["prediction"].status is StageStatus.PARTIAL
    assert empty["prediction"].metrics == ()
    assert populated["prediction"].status is StageStatus.PARTIAL
    assert populated["prediction"].metrics != ()
    assert empty["final_supervisor"].status is StageStatus.PARTIAL
    assert empty["final_supervisor"].metrics == ()
    assert populated["final_supervisor"].metrics != ()
    assert populated["document_features"].metrics == ()


def test_every_genuinely_incomplete_stage_names_reason() -> None:
    for stage in resolve_stages(_populated_payload()):
        if stage.is_available:
            continue
        assert stage.blocking_reason, stage.stage_id
        if stage.status is StageStatus.PENDING_GATE:
            assert stage.blocking_gate, stage.stage_id
            assert stage.what_appears_when_unblocked, stage.stage_id


def test_runtime_document_risk_features_become_completed_after_success() -> None:
    stage = {item.stage_id: item for item in resolve_stages(_runtime_complete_payload())}["document_features"]
    assert stage.status is StageStatus.COMPLETED
    assert pending_notice(stage) is None
    metrics = {metric.label: metric.value for metric in stage.metrics}
    assert metrics["Risk items"] == "2"
    assert metrics["Evidence anchors"] == "2"


def test_governed_market_context_makes_market_stage_completed() -> None:
    stage = {item.stage_id: item for item in resolve_stages(_runtime_complete_payload())}["market_features"]
    assert stage.status is StageStatus.COMPLETED
    assert stage.blocking_gate is None
    assert {metric.label: metric.value for metric in stage.metrics}["Observations available"] == "1 of 2"
    assert pending_notice(stage) is None


@pytest.mark.parametrize("stage_id", ["prediction", "explainability"])
def test_authentic_model_projection_makes_model_surfaces_completed(stage_id: str) -> None:
    stage = {item.stage_id: item for item in resolve_stages(_runtime_complete_payload())}[stage_id]
    assert stage.status is StageStatus.COMPLETED
    assert stage.blocking_gate is None


def test_prediction_stage_never_calls_rule_or_model_score_probability() -> None:
    for payload in (_populated_payload(), _runtime_complete_payload()):
        stage = {item.stage_id: item for item in resolve_stages(payload)}["prediction"]
        assert "probability" in stage.summary
        assert not any("probab" in metric.label.lower() for metric in stage.metrics)


def test_completed_runtime_stays_green_when_optional_market_and_model_are_missing() -> None:
    payload = {
        **_runtime_complete_payload(),
        "market_context": {},
        "model_prediction": {"status": "unavailable"},
        "runtime_completion_status": "completed_with_deterministic_fallback",
        "report_sections": [{"title": "Summary"}],
    }
    stages = {item.stage_id: item for item in resolve_stages(payload)}
    assert all(stage.status is StageStatus.COMPLETED for stage in stages.values())
    assert {metric.label: metric.value for metric in stages["market_features"].metrics}["Market channel"] == "unavailable"
    assert {metric.label: metric.value for metric in stages["prediction"].metrics}["Model channel"] == "unavailable"
    assert {metric.label: metric.value for metric in stages["explainability"].metrics}["Model drivers"] == "unavailable"
    assert "fallback" in stages["final_supervisor"].summary.lower()
    assert "not counted as real-provider acceptance" in stages["final_supervisor"].summary
    assert all(pending_notice(stage) is None for stage in stages.values())


def test_market_partial_state_can_complete_product_surface_without_imputation() -> None:
    payload = {
        **_runtime_complete_payload(),
        "market_context": {
            "status": "partial",
            "observations": [
                {"name": "industry_return_5d", "availability": "unavailable", "value": None, "missing_reason": "INDUSTRY_MAPPING_PIT_BLOCKED"},
            ],
        },
    }
    stage = {item.stage_id: item for item in resolve_stages(payload)}["market_features"]
    assert stage.status is StageStatus.COMPLETED
    metrics = {metric.label: metric.value for metric in stage.metrics}
    assert metrics["Observations available"] == "0 of 1"
    assert metrics["Market channel"] == "partial"
    assert "does not impute" in stage.summary


def test_final_supervisor_completed_with_real_channels() -> None:
    stage = {item.stage_id: item for item in resolve_stages(_runtime_complete_payload())}["final_supervisor"]
    assert stage.status is StageStatus.COMPLETED
    assert stage.blocking_gate is None
    assert {metric.label: metric.value for metric in stage.metrics}["Channels available"] == "4 of 4"


def test_final_supervisor_fallback_is_green_but_explicitly_not_real_provider_acceptance() -> None:
    payload = {
        **_runtime_complete_payload(),
        "runtime_completion_status": "completed_with_deterministic_fallback",
    }
    stage = {item.stage_id: item for item in resolve_stages(payload)}["final_supervisor"]
    assert stage.status is StageStatus.COMPLETED
    assert "fallback" in stage.summary.lower()
    assert "not counted as real-provider acceptance" in stage.summary
    assert {metric.label: metric.value for metric in stage.metrics}["LLM synthesis"] == "deterministic fallback"


def test_document_only_supervision_can_complete_supervisor_surface() -> None:
    payload = {
        **_runtime_complete_payload(),
        "final_supervision": {},
        "supervision": {"duplicate_groups": [{}], "conflicts": [{}], "composite_findings": [{}, {}]},
    }
    stage = {item.stage_id: item for item in resolve_stages(payload)}["final_supervisor"]
    assert stage.status is StageStatus.COMPLETED
    assert {metric.label: metric.value for metric in stage.metrics}["Cross-channel LLM"] == "unavailable"


def test_final_report_without_sections_is_runtime_limitation_not_release_gate() -> None:
    stage = {item.stage_id: item for item in resolve_stages(_runtime_complete_payload())}["final_report"]
    assert stage.status is StageStatus.PARTIAL
    assert stage.blocking_gate is None
    assert "report" in stage.blocking_reason


def test_materialized_final_report_is_completed_independent_of_project_readiness() -> None:
    payload = {**_runtime_complete_payload(), "report_sections": [{"title": "Summary"}]}
    stage = {item.stage_id: item for item in resolve_stages(payload)}["final_report"]
    assert stage.status is StageStatus.COMPLETED
    assert stage.blocking_gate is None
    assert {metric.label: metric.value for metric in stage.metrics}["Report sections"] == "1"
