"""Guards for the PR-H seven-stage skeleton, especially the no-fake-data rule."""
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
# dataclasses resolve their own module through sys.modules during class creation.
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
        "market_context": {
            "status": "available",
            "observations": [
                {"name": "hsi_return_5d", "availability": "available", "value": 0.01},
                {"name": "industry_return_5d", "availability": "unavailable", "missing_reason": "missing_industry_series"},
            ],
        },
        "model_prediction": {
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


def test_chain_matches_the_pr_h_page_order() -> None:
    stages = resolve_stages(_populated_payload())
    assert len(stages) == 7
    assert tuple(stage.ordinal for stage in stages) == tuple(range(1, 8))
    assert tuple(stage.title for stage in stages) == EXPECTED_CHAIN
    assert len({stage.stage_id for stage in stages}) == 7


def test_only_pr_h_remains_a_referenced_gate() -> None:
    """PR-B and PR-F are frozen; runtime absence is not a gate statement."""
    assert pipeline_stages.blocking_gates() == ("PR-H",)


def test_pending_gate_stages_render_nothing_numeric() -> None:
    """If a future stage is fully blocked, it must never show a fabricated number."""
    for payload in ({}, _populated_payload()):
        for stage in resolve_stages(payload):
            if stage.status is not StageStatus.PENDING_GATE:
                continue
            assert stage.metrics == ()
            assert not NUMERIC.search(stage.summary)
            assert not NUMERIC.search(stage.blocking_reason)
            assert not any(NUMERIC.search(item) for item in stage.what_appears_when_unblocked)


def test_partial_stages_only_show_values_the_payload_actually_has() -> None:
    """PARTIAL stages may show the half that is genuinely available, and nothing more."""
    empty = {stage.stage_id: stage for stage in resolve_stages({})}
    populated = {stage.stage_id: stage for stage in resolve_stages(_populated_payload())}
    assert empty["prediction"].status is StageStatus.PARTIAL
    assert empty["prediction"].metrics == ()
    assert populated["prediction"].metrics != ()
    assert empty["final_supervisor"].status is StageStatus.PARTIAL
    assert empty["final_supervisor"].metrics == ()
    assert populated["final_supervisor"].metrics != ()
    # The document feature vector needs the PR-A run output, absent from this checkout.
    assert populated["document_features"].metrics == ()


def test_every_nonavailable_stage_names_a_reason() -> None:
    for stage in resolve_stages(_populated_payload()):
        if stage.status is StageStatus.AVAILABLE:
            continue
        assert stage.blocking_reason, stage.stage_id
        if stage.status is StageStatus.PENDING_GATE:
            assert stage.blocking_gate, stage.stage_id
            assert stage.what_appears_when_unblocked, stage.stage_id


def test_market_runtime_absence_is_not_misreported_as_pr_b_gate() -> None:
    stage = {item.stage_id: item for item in resolve_stages(_populated_payload())}["market_features"]
    assert stage.status is StageStatus.PARTIAL
    assert stage.blocking_gate is None
    assert "PR-B itself is not blocking" in stage.blocking_reason


@pytest.mark.parametrize("stage_id", ["prediction", "explainability"])
def test_model_runtime_absence_is_not_misreported_as_pr_f_gate(stage_id: str) -> None:
    stage = {item.stage_id: item for item in resolve_stages({})}[stage_id]
    assert stage.status is StageStatus.PARTIAL
    assert stage.blocking_gate is None
    assert "PR-F" in stage.blocking_reason
    assert "blocking gate" in stage.blocking_reason or "not a blocking gate" in stage.blocking_reason or "COMPLETE / FROZEN" in stage.blocking_reason


def test_prediction_stage_never_calls_the_rule_or_model_score_a_probability() -> None:
    for payload in (_populated_payload(), _runtime_complete_payload()):
        stage = {item.stage_id: item for item in resolve_stages(payload)}["prediction"]
        assert "probability" in stage.summary
        assert not any("probab" in metric.label.lower() for metric in stage.metrics)


def test_governed_market_context_makes_market_stage_available() -> None:
    stage = {item.stage_id: item for item in resolve_stages(_runtime_complete_payload())}["market_features"]
    assert stage.status is StageStatus.AVAILABLE
    assert stage.blocking_gate is None
    assert {metric.label: metric.value for metric in stage.metrics}["Observations available"] == "1 of 2"
    assert pending_notice(stage) is None


def test_hash_bound_model_projection_makes_prediction_and_explainability_available() -> None:
    stages = {item.stage_id: item for item in resolve_stages(_runtime_complete_payload())}
    assert stages["prediction"].status is StageStatus.AVAILABLE
    assert stages["prediction"].blocking_gate is None
    assert {metric.label: metric.value for metric in stages["prediction"].metrics}["Model score"] == "0.61"
    assert stages["explainability"].status is StageStatus.AVAILABLE
    assert {metric.label: metric.value for metric in stages["explainability"].metrics}["Model drivers"] == "1"


def test_final_supervisor_becomes_available_once_pr_g_channels_run() -> None:
    payload = {**_populated_payload(), "final_supervision": {
        "channel_states": [
            {"channel": "document", "status": "available"},
            {"channel": "market", "status": "unavailable_error"},
            {"channel": "model", "status": "disabled"},
            {"channel": "rule", "status": "available"},
        ],
        "referenced_risk_ids": ["r-1", "r-2"],
        "metadata": {"unresolved_conflict_count": 1},
    }}
    stage = {item.stage_id: item for item in resolve_stages(payload)}["final_supervisor"]
    assert stage.status is StageStatus.AVAILABLE
    assert stage.blocking_gate is None
    assert {metric.label: metric.value for metric in stage.metrics}["Channels available"] == "2 of 4"


def test_final_supervisor_without_the_channel_names_no_retired_gate() -> None:
    stage = {item.stage_id: item for item in resolve_stages(_populated_payload())}["final_supervisor"]
    assert stage.status is StageStatus.PARTIAL
    assert stage.blocking_gate is None
    assert stage.blocking_reason


def test_final_report_points_only_to_pr_h() -> None:
    stage = {item.stage_id: item for item in resolve_stages(_runtime_complete_payload())}["final_report"]
    assert stage.status is StageStatus.PARTIAL
    assert stage.blocking_gate == "PR-H"
