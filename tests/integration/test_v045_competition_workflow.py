"""The competition workflow, end to end through the real analysis service.

The service persists every result and re-reads it with strict equality, so a
COMPLETED status also proves the whole competition sidecar -- conflicts,
re-checks, trace -- serialises cleanly. The rest of these tests fix what the
chain must contain and what it must never contain.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date

import pytest

from ipo_risk.core.config import load_settings
from ipo_risk.core.container import DependencyContainer, default_registry
from ipo_risk.agents.final_supervision_llm import LLMFinalSupervisor
from ipo_risk.schemas import IPOAnalysisRequest, TaskStatus
from ipo_risk.services.analysis_service import IPOAnalysisService
from ipo_risk.workflows.v04_competition import V04CompetitionWorkflow
from ..v04_market_context_fixture import write_governed_pr_b_fixture

COMPETITION_CONFIGS = ["configs/v045_competition_offline.yaml", "configs/v045_competition_ai.yaml"]


@pytest.mark.parametrize("config", COMPETITION_CONFIGS)
def test_the_competition_configs_build_the_competition_workflow(config: str) -> None:
    container = DependencyContainer(load_settings(config), default_registry())
    workflow = container.create_workflow()
    assert isinstance(workflow, V04CompetitionWorkflow)
    assert isinstance(workflow.final_supervisor, LLMFinalSupervisor)


def test_the_frozen_v04_configs_keep_their_historical_supervisor() -> None:
    """PR-H's runtime identity must not move because the E lane shipped."""
    for config in ("configs/v04_offline.yaml", "configs/v04_ai.yaml"):
        assert load_settings(config).final_supervisor == "v04"


@pytest.fixture
def result(tmp_path):
    feature_dir, bridge_path = write_governed_pr_b_fixture(tmp_path / "market")
    settings = replace(
        load_settings("configs/v045_competition_offline.yaml"),
        parser="mock", retriever="mock", financial_agent="mock", legal_agent="mock",
        business_agent="mock", use_mock=True, llm_provider="mock",
        data_dir=str(tmp_path / "repo"), market_feature_dir=str(feature_dir),
        market_official_bridge=str(bridge_path),
    )
    service = IPOAnalysisService(settings=settings)
    # The mock provider answers only tasks it was given, so the Final Supervisor
    # degrades honestly here; the deterministic chain still has to be complete.
    return service.analyze(IPOAnalysisRequest(
        company_name="同源康医药-B", stock_code="2410.HK",
        listing_date=date(2024, 8, 20), use_mock=True))


def _diagnostics(result) -> dict:
    return result.metadata["component_diagnostics"]


def test_the_competition_run_round_trips_through_the_repository(result) -> None:
    assert result.status is TaskStatus.COMPLETED, result.errors


def test_conflict_detection_and_the_recheck_both_report_their_policy_version(result) -> None:
    diagnostics = _diagnostics(result)
    assert diagnostics["conflict_detection"]["policy_version"] == "v04_e_conflict_policy_v1"
    assert diagnostics["targeted_recheck"]["policy_version"] == "v04_e_recheck_policy_v1"


def test_the_trace_sidecar_reaches_the_result_and_measures_traceability(result) -> None:
    runtime = _diagnostics(result)["competition_runtime"]
    assert runtime["status"] == "completed"
    sidecar = runtime["sidecar"]
    assert sidecar["identity"]["schema_version"] == "competition_runtime_v1"
    assert sidecar["identity"]["provenance"]["conflict_policy_version"] == "v04_e_conflict_policy_v1"
    assert sidecar["trace_events"], "a completed run must produce trace events"
    report = runtime["traceability"]
    assert report["agent_traceability"] == 1.0
    assert report["tool_traceability"] == 1.0
    assert report["evidence_traceability"] == 1.0
    assert report["unresolved_evidence_ids"] == []


def test_every_trace_event_names_an_actor_a_tool_and_accounts_for_evidence(result) -> None:
    for event in _diagnostics(result)["competition_runtime"]["sidecar"]["trace_events"]:
        assert event["agent_name"], event
        assert event["tool_or_skill"], event
        accounted = (
            event["evidence_ids"] or event["calculation_ids"]
            or event["details"].get("no_evidence_reason")
        )
        assert accounted, event


def test_an_unavailable_provider_degrades_the_synthesis_without_losing_composition(result) -> None:
    synthesis = _diagnostics(result)["final_supervision_llm"]
    assert synthesis["status"] == "unavailable"
    assert synthesis["judgement"] is None
    assert synthesis["deterministic_severity_floor"] in {"low", "medium", "high", "critical"}
    final = result.metadata["final_supervision"]
    assert final["summary"]
    assert final["metadata"]["creates_no_new_risk"] is True
    assert final["metadata"]["probability_claimed"] is False


def test_the_supervisor_references_nothing_the_run_did_not_produce(result) -> None:
    final = result.metadata["final_supervision"]
    risk_ids = {risk.risk_id for risk in result.verified_risks}
    evidence_ids = {item.evidence_id for risk in result.verified_risks for item in risk.evidence}
    assert set(final["referenced_risk_ids"]) <= risk_ids
    assert set(final["referenced_evidence_ids"]) <= evidence_ids


class _GroundedSupervisionProvider:
    """Answers strictly from the bounded payload it is handed.

    Risk ids are minted per run, so a fixture with hard-coded ids would only ever
    prove that out-of-scope citations are rejected.  Reading the supplied payload
    is what a well-behaved provider does, and it is what has to be accepted.
    """

    name = "grounded_stub"

    def __init__(self) -> None:
        self.last_call_metadata = None

    def complete(self, prompt: str) -> str:  # pragma: no cover - unused here
        return ""

    def generate_structured(self, *, task_name, prompt_version, evidence, response_model):
        sections = {item.section: json.loads(item.text) for item in evidence}
        risks = [
            risk
            for group in ("verified_risks", "unsettled_risks", "rejected_risks")
            for risk in sections.get(group, [])
        ]
        finding = {
            "statement": "the document channel is the only severity source in this run",
            "risk_ids": [risks[0]["risk_id"]] if risks else [],
            "evidence_ids": list(risks[0]["evidence_ids"]) if risks else [],
        }
        return response_model.model_validate({
            "overall_risk": sections["deterministic_severity_floor"],
            "overall_risk_rationale": "the deterministic floor is carried through unchanged",
            "key_findings": [finding],
            "conflict_assessments": [
                {"conflict_id": conflict["conflict_id"], "assessment": "carried through unresolved"}
                for conflict in sections.get("conflicts", [])
            ],
            "uncertainties": ["the model channel did not run"],
            "recheck_required": False,
            "recheck_targets": [],
            "final_explanation": "the supervisory view rests on the document channel alone",
        })


def test_a_grounded_llm_judgement_reaches_the_result_metadata(tmp_path) -> None:
    """With a provider that answers in scope, the synthesis is attached in full."""
    feature_dir, bridge_path = write_governed_pr_b_fixture(tmp_path / "market")
    settings = replace(
        load_settings("configs/v045_competition_offline.yaml"),
        parser="mock", retriever="mock", financial_agent="mock", legal_agent="mock",
        business_agent="mock", use_mock=True, llm_provider="mock",
        data_dir=str(tmp_path / "repo"), market_feature_dir=str(feature_dir),
        market_official_bridge=str(bridge_path),
    )
    service = IPOAnalysisService(settings=settings)
    service.workflow.final_supervisor.llm_provider = _GroundedSupervisionProvider()
    result = service.analyze(IPOAnalysisRequest(
        company_name="同源康医药-B", stock_code="2410.HK",
        listing_date=date(2024, 8, 20), use_mock=True))

    assert result.status is TaskStatus.COMPLETED, result.errors
    synthesis = result.metadata["component_diagnostics"]["final_supervision_llm"]
    assert synthesis["status"] == "available", synthesis["reason"]
    judgement = synthesis["judgement"]
    assert judgement["overall_risk"] == synthesis["deterministic_severity_floor"]
    cited = set(judgement["key_findings"][0]["risk_ids"])
    every_risk_id = {
        risk.risk_id
        for risk in (*result.verified_risks, *result.pending_risks, *result.rejected_risks)
    }
    assert cited <= every_risk_id and cited
    # The synthesis is attached to, not substituted for, the frozen composition.
    assert result.metadata["final_supervision"]["metadata"]["creates_no_new_risk"] is True
