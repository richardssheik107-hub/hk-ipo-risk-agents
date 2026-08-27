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
from ipo_risk.runtime.submission_artifacts import (
    REAL_LLM_PROVIDERS,
    CaseRunArtifacts,
    build_agent_reasoning_log,
    build_gate_e1_evidence,
)
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


def test_the_ai_config_names_the_verified_real_transport() -> None:
    """Gate E1 is an acceptance run, so it may not ride an unverified transport.

    Only ``openai_responses`` has been proven end to end on a real prospectus
    (1167.HK, ark-code-latest). Pointing the competition AI config at the other
    transport would make the E1 evidence describe a path nobody has exercised.
    """
    settings = load_settings("configs/v045_competition_ai.yaml")
    assert settings.llm_provider == "openai_responses"
    assert settings.llm_provider in REAL_LLM_PROVIDERS
    # One bounded attempt, as the verified runtime was configured.
    assert settings.llm_timeout_seconds == 300
    assert settings.llm_max_retries == 0


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


def _case_artifacts(result, config: str = "configs/v045_competition_offline.yaml") -> CaseRunArtifacts:
    """Assemble the submission artifacts exactly as the demo runner does."""
    diagnostics = _diagnostics(result)
    runtime = diagnostics["competition_runtime"]
    return CaseRunArtifacts(
        case_id="ipo_2024_02410",
        company_name="同源康医药-B",
        stock_code="2410.HK",
        listing_date="2024-08-20",
        config=config,
        result=json.loads(result.model_dump_json()),
        sidecar=runtime["sidecar"],
        composition=result.metadata["final_supervision"],
        supervision_llm=diagnostics["final_supervision_llm"],
        conflicts=diagnostics["conflict_detection"],
        rechecks=diagnostics["targeted_recheck"],
        traceability=runtime["traceability"],
        verification={"source_filename": "fixture.pdf", "sha256_matches_frozen_catalog": True},
    )


def test_the_reasoning_log_covers_every_trace_event_of_a_real_run(result) -> None:
    """The submission log is a rendering of the run, so it cannot be shorter."""
    artifacts = _case_artifacts(result)
    log = build_agent_reasoning_log(artifacts)
    assert len(log["steps"]) == len(artifacts.sidecar["trace_events"])
    assert log["accounting"]["unaccounted_step_count"] == 0
    produced = {
        evidence_id
        for event in artifacts.sidecar["trace_events"]
        for evidence_id in event["evidence_ids"]
    }
    cited = {item for step in log["steps"] for item in step["evidence_ids"]}
    assert cited <= produced


def test_the_gate_evidence_is_built_from_what_the_run_actually_recorded(result) -> None:
    """Gate E1 evidence comes off the run, not off the script that wrote it out.

    This run degrades honestly, so every Gate condition must read as unmet: that
    is the reading the acceptance depends on.
    """
    evidence = build_gate_e1_evidence(_case_artifacts(result))
    assert evidence["synthesis_outcome"] is not None, "the run must record why it degraded"
    assert evidence["successful_llm_arbitration"] is False
    assert evidence["deterministic_fallback_used"] is True
    assert evidence["satisfied"] is False
    assert evidence["unmet_conditions"]


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
    # An accepted synthesis records what it cited and the call that produced it.
    assert synthesis["outcome"] == "accepted"
    assert synthesis["scope_check"]["status"] == "passed"
    assert synthesis["scope_check"]["out_of_scope_reference_count"] == 0
    assert synthesis["call"]["prompt_version"] == "v04_final_supervision_v1"

    # ...and it still cannot satisfy Gate E1, because a mock is not a real provider.
    evidence = build_gate_e1_evidence(_case_artifacts(result))
    assert evidence["synthesis_outcome"] == "accepted"
    assert evidence["out_of_scope_reference_check"]["status"] == "passed"
    assert evidence["provider_is_real_remote"] is False
    assert evidence["satisfied"] is False
