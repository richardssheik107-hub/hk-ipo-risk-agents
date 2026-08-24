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


def test_chain_matches_the_pr_h_page_order() -> None:
    stages = resolve_stages(_populated_payload())
    assert len(stages) == 7
    assert tuple(stage.ordinal for stage in stages) == tuple(range(1, 8))
    assert tuple(stage.title for stage in stages) == EXPECTED_CHAIN
    assert len({stage.stage_id for stage in stages}) == 7


def test_referenced_gates_match_the_execution_plan() -> None:
    """The plan document is the source of truth; if it changes, this fails."""
    assert set(pipeline_stages.blocking_gates()) == {"PR-B", "PR-F", "PR-H"}


def test_pending_gate_stages_render_nothing_numeric() -> None:
    """A fully blocked stage must never show a number — not even a zero."""
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
    for stage_id in ("prediction", "final_supervisor"):
        assert empty[stage_id].status is StageStatus.PARTIAL
        assert empty[stage_id].metrics == (), stage_id
        assert populated[stage_id].metrics != (), stage_id
    # The document feature vector needs the PR-A run output, absent from this checkout.
    assert populated["document_features"].metrics == ()


def test_every_blocked_stage_names_its_gate_and_reason() -> None:
    for stage in resolve_stages(_populated_payload()):
        if stage.status is StageStatus.AVAILABLE:
            continue
        assert stage.blocking_reason, stage.stage_id
        if stage.status is StageStatus.PENDING_GATE:
            assert stage.blocking_gate, stage.stage_id
            assert stage.what_appears_when_unblocked, stage.stage_id


def test_market_features_is_the_only_fully_blocked_stage_today() -> None:
    stages = {stage.stage_id: stage for stage in resolve_stages(_populated_payload())}
    blocked = [stage.stage_id for stage in stages.values() if stage.status is StageStatus.PENDING_GATE]
    assert blocked == ["market_features"]
    assert stages["market_features"].blocking_gate == "PR-B"
    assert stages["document_analysis"].status is StageStatus.AVAILABLE


@pytest.mark.parametrize("stage_id", ["prediction", "explainability"])
def test_model_dependent_stages_point_at_the_model_gate(stage_id: str) -> None:
    stages = {stage.stage_id: stage for stage in resolve_stages({})}
    assert stages[stage_id].blocking_gate == "PR-F"


def test_prediction_stage_never_calls_the_rule_score_a_probability() -> None:
    stage = {item.stage_id: item for item in resolve_stages(_populated_payload())}["prediction"]
    assert "never a probability" in stage.summary
    assert not any("probab" in metric.label.lower() for metric in stage.metrics)


def test_final_supervisor_becomes_available_once_pr_g_channels_run() -> None:
    """PR-G is delivered, so the stage stops claiming a gate blocks it."""
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
