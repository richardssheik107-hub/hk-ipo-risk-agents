"""Submission artifacts must render the run, not flatter it.

The reasoning log and case report are what a competition reviewer reads instead
of the raw JSON, so the invariants fixed here are about honesty: a step with no
Evidence keeps the reason it had none, a conflict the bounded budget never
reached is declared rather than dropped, an unavailable channel is stated, and a
run that produced no verified risk says so.

The Gate E1 tests are the strict half.  Gate E1 asks for a *successful* bounded
arbitration by a *real* provider with its call trace retained; a missing
provider, a mock, a transport failure and a judgement the scope guard refused
must each leave the Gate unmet, because an honest degradation that later reads
as a pass would defeat the whole acceptance.
"""

from __future__ import annotations

import pytest

from ipo_risk.runtime.submission_artifacts import (
    CaseRunArtifacts,
    build_agent_reasoning_log,
    build_gate_e1_evidence,
    render_agent_reasoning_log,
    render_case_report,
    summarise_gate_e1,
)


EVIDENCE_ID = "67ef7838-6af2-5ebd-8a5c-7a46c39bb804"
RISK_ID = "69066732-91e7-5238-850d-b162104dcab9"
CONFLICT_ID = "conflict:run-1:unresolved_agent_claim:business:precommercial_product"
BUDGETED_OUT_CONFLICT_ID = "conflict:run-1:agent_verifier_disagreement:legal:redemption_rights"


def _risk(**overrides) -> dict:
    risk = {
        "risk_id": RISK_ID,
        "risk_code": "cash_runway",
        "level": "critical",
        "verification_status": "verified",
        "agent_name": "financial",
        "conclusion": "the estimated cash runway is approximately 2.76 months",
        "verification_notes": "Calculation was independently recalculated",
        "calculation": {
            "skill_name": "cash_runway",
            "skill_version": "1.1",
            "formula": "cash / (abs(operating_cash_flow) / period_months)",
            "result": "2.76",
            "unit": "months",
        },
        "evidence": [
            {"evidence_id": EVIDENCE_ID, "page": 563, "section": "financial_information", "bbox": None}
        ],
    }
    risk.update(overrides)
    return risk


def _event(step: int, **overrides) -> dict:
    event = {
        "event_id": f"trace:run-1:log:{step:03d}",
        "event_type": "agent",
        "status": "completed",
        "agent_name": "financial",
        "action": "extract",
        "tool_or_skill": "financial_agent",
        "provider_name": None,
        "model_name": None,
        "prompt_version": None,
        "request_id": None,
        "raw_response_hash": None,
        "latency_ms": 0,
        "conflict_id": None,
        "recheck_id": None,
        "evidence_ids": [EVIDENCE_ID],
        "calculation_ids": [],
        "occurred_at": "2026-08-26T02:10:07Z",
        "details": {"step": step, "output_summary": "one risk asserted"},
    }
    event.update(overrides)
    return event


def _supervision(**overrides) -> dict:
    supervision = {
        "schema_version": "v04_final_supervision_v1",
        "prompt_version": "v04_final_supervision_v1",
        "status": "unavailable",
        "outcome": "provider_not_configured",
        "reason": "LLM provider is not configured; the deterministic composition is retained in full",
        "fail_closed": False,
        "scope_check": {"status": "not_applicable", "reason": "no judgement was produced to check"},
        "call": {},
        "deterministic_severity_floor": "critical",
        "judgement": None,
    }
    supervision.update(overrides)
    return supervision


def _accepted_supervision(**call_overrides) -> dict:
    call = {
        "provider_name": "openai_compatible",
        "model_name": "doubao-pro",
        "prompt_version": "v04_final_supervision_v1",
        "request_id": "req-8812",
        "raw_response_hash": "9f2c" * 16,
        "latency_ms": 2140,
    }
    call.update(call_overrides)
    return _supervision(
        status="available",
        outcome="accepted",
        reason="grounded supervisory synthesis available",
        scope_check={
            "status": "passed",
            "cited_risk_ids": [RISK_ID],
            "cited_evidence_ids": [EVIDENCE_ID],
            "cited_conflict_ids": [],
            "out_of_scope_reference_count": 0,
            "severity_floor_respected": True,
        },
        call=call,
        judgement={"overall_risk": "critical"},
    )


def _artifacts(**overrides) -> CaseRunArtifacts:
    payload = {
        "case_id": "ipo_2024_02410",
        "company_name": "同源康醫藥",
        "stock_code": "2410.HK",
        "listing_date": "2024-08-20",
        "config": "configs/v045_competition_offline.yaml",
        "result": {
            "analysis_id": "analysis-1",
            "status": "completed",
            "workflow_version": "enhanced_v2",
            "schema_version": "v04",
            "verified_risks": [_risk()],
            "pending_risks": [],
            "rejected_risks": [],
            "report_sections": [{"title": "s"}],
            "errors": [],
            "metadata": {"document": {"parsed_chunk_count": 706}},
        },
        "sidecar": {
            "identity": {
                "run_id": "run-1",
                "provider_name": "unavailable",
                "provenance": {
                    "workflow": "v04_competition",
                    "trace_schema_version": "v04_e_agent_trace_v1",
                    "conflict_policy_version": "v04_e_conflict_policy_v1",
                    "recheck_policy_version": "v04_e_recheck_policy_v1",
                },
            },
            "trace_events": [
                _event(1),
                _event(
                    2,
                    agent_name="predictor",
                    tool_or_skill="predictor",
                    evidence_ids=[],
                    details={
                        "step": 2,
                        "output_summary": "",
                        "no_evidence_reason": "predictor is an orchestration step",
                    },
                ),
            ],
        },
        "composition": {
            "channel_states": [
                {"channel": "document", "status": "available"},
                {"channel": "market", "status": "unavailable_error"},
                {"channel": "model", "status": "disabled"},
                {"channel": "rule", "status": "available"},
            ]
        },
        "supervision_llm": _supervision(),
        "conflicts": {
            "policy_version": "v04_e_conflict_policy_v1",
            "conflict_count": 2,
            "conflicts": [
                {
                    "conflict_id": CONFLICT_ID,
                    "involved_agents": ["business", "document_supervisor"],
                    "summary": "business held 9 bounded Evidence items and the document channel asserts nothing",
                    "status": "unresolved",
                    "resolution_note": "the gap is in extraction rather than retrieval",
                    "risk_ids": [],
                    "evidence_ids": [EVIDENCE_ID],
                },
                {
                    "conflict_id": BUDGETED_OUT_CONFLICT_ID,
                    "involved_agents": ["legal", "verifier"],
                    "summary": "legal asserted a risk the verifier left pending",
                    "status": "unresolved",
                    "resolution_note": None,
                    "risk_ids": [],
                    "evidence_ids": [],
                },
            ],
        },
        "rechecks": {
            "policy_version": "v04_e_recheck_policy_v1",
            "attempted": 1,
            "outcomes": [
                {
                    "conflict_id": CONFLICT_ID,
                    "recheck_id": f"recheck:{CONFLICT_ID}",
                    "status": "unresolved",
                    "targets": ["precommercial_product"],
                    "new_evidence_ids": [],
                    "revised_risk_ids": [],
                }
            ],
        },
        "traceability": {
            "event_count": 2,
            "agent_traceability": 1.0,
            "tool_traceability": 1.0,
            "evidence_traceability": 1.0,
            "overall_traceability": 1.0,
            "referenced_evidence_count": 1,
            "resolved_evidence_count": 1,
        },
        "verification": {
            "source_filename": "02410_12-08-2024.pdf",
            "sha256": "6c8179a5" * 8,
            "sha256_matches_frozen_catalog": True,
            "file_size_bytes": 7668322,
            "pdf_page_count": 706,
            "dataset_split": "development_exception",
            "path_recorded": False,
        },
    }
    payload.update(overrides)
    return CaseRunArtifacts(**payload)


# --- reasoning log ---------------------------------------------------------


def test_every_trace_event_becomes_one_step_in_recorded_order() -> None:
    log = build_agent_reasoning_log(_artifacts())
    assert [step["step"] for step in log["steps"]] == [1, 2]
    assert log["accounting"]["trace_event_count"] == 2


def test_steps_are_numbered_by_trace_position_not_by_the_workflow_log_counter() -> None:
    """An event the workflow never logged must not renumber the narrative.

    The Final Supervisor's synthesis pass carries no workflow log step, and the
    log step of the events around it restarts; numbering by trace position keeps
    the story readable and still records the workflow counter where it exists.
    """
    artifacts = _artifacts()
    sidecar = dict(artifacts.sidecar)
    sidecar["trace_events"] = [
        _event(7),
        _event(  # the synthesis pass: no workflow log step at all
            0,
            agent_name="llm_final_supervisor",
            evidence_ids=[],
            details={"no_evidence_reason": "the synthesis reasons over composed channel outputs"},
        ),
        _event(3),
    ]
    log = build_agent_reasoning_log(_artifacts(sidecar=sidecar))
    assert [step["step"] for step in log["steps"]] == [1, 2, 3]
    assert [step["workflow_log_step"] for step in log["steps"]] == [7, None, 3]


def test_a_step_without_evidence_keeps_the_reason_it_had_none() -> None:
    log = build_agent_reasoning_log(_artifacts())
    orchestration = log["steps"][1]
    assert orchestration["evidence_ids"] == []
    assert orchestration["no_evidence_reason"] == "predictor is an orchestration step"
    assert orchestration["evidence_accounted"] is True
    assert "predictor is an orchestration step" in render_agent_reasoning_log(log)


def test_a_step_with_neither_evidence_nor_a_reason_is_marked_unaccounted() -> None:
    """The log must expose the same gap the traceability measurement counts."""
    artifacts = _artifacts()
    sidecar = dict(artifacts.sidecar)
    sidecar["trace_events"] = [_event(1, evidence_ids=[], details={"step": 1, "output_summary": ""})]
    log = build_agent_reasoning_log(_artifacts(sidecar=sidecar))
    assert log["steps"][0]["evidence_accounted"] is False
    assert log["accounting"]["unaccounted_step_count"] == 1
    assert "**unaccounted**" in render_agent_reasoning_log(log)


def test_the_log_cites_no_evidence_id_the_run_did_not_produce() -> None:
    artifacts = _artifacts()
    produced = {
        evidence_id
        for event in artifacts.trace_events
        for evidence_id in event.get("evidence_ids", [])
    }
    log = build_agent_reasoning_log(artifacts)
    cited = {item for step in log["steps"] for item in step["evidence_ids"]}
    assert cited <= produced


def test_a_conflict_the_bounded_budget_never_reached_is_declared_not_dropped() -> None:
    log = build_agent_reasoning_log(_artifacts())
    unreached = [item for item in log["conflicts"] if not item["recheck_attempted"]]
    assert [item["conflict_id"] for item in unreached] == [BUDGETED_OUT_CONFLICT_ID]
    assert log["recheck_budget"]["conflicts_not_attempted"] == [BUDGETED_OUT_CONFLICT_ID]
    assert "the bounded budget was already spent" in render_agent_reasoning_log(log)


def test_the_rendered_log_carries_the_provider_trace_of_an_arbitrated_run() -> None:
    log = build_agent_reasoning_log(_artifacts(supervision_llm=_accepted_supervision()))
    rendered = render_agent_reasoning_log(log)
    assert "openai_compatible" in rendered
    assert "doubao-pro" in rendered
    assert "2140 ms" in rendered


# --- honesty about what a run does not show --------------------------------


def test_a_run_without_a_verified_risk_says_so_instead_of_implying_coverage() -> None:
    empty = dict(_artifacts().result, verified_risks=[])
    log = build_agent_reasoning_log(_artifacts(result=empty))
    assert any("No formal RiskItem was verified" in item for item in log["not_demonstrated"])


def test_an_unavailable_market_channel_is_stated_rather_than_omitted() -> None:
    log = build_agent_reasoning_log(_artifacts())
    assert any("Market channel is `unavailable_error`" in item for item in log["not_demonstrated"])
    assert any("Model channel is `disabled`" in item for item in log["not_demonstrated"])


def test_evidence_without_a_bbox_is_declared_rather_than_drawn() -> None:
    log = build_agent_reasoning_log(_artifacts())
    assert any("no bbox" in item for item in log["not_demonstrated"])


def test_a_fully_available_arbitrated_run_has_nothing_to_disclaim() -> None:
    """The disclaimer list is derived, so a clean run must not manufacture one."""
    artifacts = _artifacts(
        composition={
            "channel_states": [
                {"channel": "document", "status": "available"},
                {"channel": "market", "status": "available"},
                {"channel": "model", "status": "available"},
            ]
        },
        supervision_llm=_accepted_supervision(),
        result=dict(
            _artifacts().result,
            verified_risks=[
                _risk(evidence=[{"evidence_id": EVIDENCE_ID, "page": 563, "bbox": [1, 2, 3, 4]}])
            ],
        ),
    )
    assert build_agent_reasoning_log(artifacts)["not_demonstrated"] == []


# --- Gate E1 ---------------------------------------------------------------


def test_a_deterministic_fallback_never_counts_as_a_successful_arbitration() -> None:
    evidence = build_gate_e1_evidence(_artifacts())
    assert evidence["successful_llm_arbitration"] is False
    assert evidence["deterministic_fallback_used"] is True
    assert evidence["satisfied"] is False
    assert evidence["out_of_scope_reference_check"]["status"] == "not_applicable"


def test_a_refused_out_of_scope_judgement_is_recorded_as_fail_closed_not_as_success() -> None:
    refused = _supervision(
        outcome="rejected_out_of_scope",
        reason="LLM final supervision unavailable: ScopeViolation: cited a risk_id that was not supplied",
        fail_closed=True,
        scope_check={"status": "failed", "violation": "cited a risk_id that was not supplied"},
        call={
            "provider_name": "openai_compatible",
            "model_name": "doubao-pro",
            "prompt_version": "v04_final_supervision_v1",
            "request_id": "req-1",
            "raw_response_hash": "ab" * 32,
            "latency_ms": 1800,
        },
    )
    evidence = build_gate_e1_evidence(_artifacts(supervision_llm=refused))
    assert evidence["out_of_scope_reference_check"]["fail_closed_fired"] is True
    assert evidence["successful_llm_arbitration"] is False
    assert evidence["satisfied"] is False
    # The refused call is still auditable: the guard fired against a real response.
    assert evidence["provider_trace"]["request_id"] == "req-1"


def test_a_mock_provider_cannot_satisfy_the_gate() -> None:
    """Gate E1 asks for real credentials; a mock answering perfectly is not that."""
    mocked = _accepted_supervision(provider_name="mock", model_name="mock-structured")
    evidence = build_gate_e1_evidence(_artifacts(supervision_llm=mocked))
    assert evidence["provider_is_real_remote"] is False
    assert evidence["successful_llm_arbitration"] is False
    assert evidence["satisfied"] is False
    assert any("real remote provider" in reason for reason in evidence["unmet_conditions"])


def test_a_real_provider_with_a_complete_call_trace_satisfies_the_gate() -> None:
    evidence = build_gate_e1_evidence(_artifacts(supervision_llm=_accepted_supervision()))
    assert evidence["successful_llm_arbitration"] is True
    assert evidence["provider_trace_complete"] is True
    assert evidence["out_of_scope_reference_check"]["status"] == "passed"
    assert evidence["severity_floor_respected"] is True
    assert evidence["satisfied"] is True
    assert evidence["unmet_conditions"] == []


@pytest.mark.parametrize("field", ["request_id", "raw_response_hash", "model_name"])
def test_a_missing_call_trace_field_keeps_the_gate_unmet(field) -> None:
    evidence = build_gate_e1_evidence(
        _artifacts(supervision_llm=_accepted_supervision(**{field: None}))
    )
    assert evidence["provider_trace_complete"] is False
    assert field in evidence["missing_provider_trace_fields"]
    assert evidence["satisfied"] is False


def test_the_matrix_verdict_requires_every_declared_case() -> None:
    passing = build_gate_e1_evidence(_artifacts(supervision_llm=_accepted_supervision()))
    failing = build_gate_e1_evidence(_artifacts())
    verdict = summarise_gate_e1([passing, failing], declared_case_count=3)
    assert verdict["cases_with_successful_llm_arbitration"] == 1
    assert verdict["cases_on_deterministic_fallback"] == 1
    assert verdict["satisfied"] is False
    assert "NOT met" in verdict["verdict"]


def test_the_matrix_verdict_is_unmet_when_no_case_produced_evidence() -> None:
    verdict = summarise_gate_e1([], declared_case_count=3)
    assert verdict["satisfied"] is False
    assert verdict["cases_with_evidence"] == 0


def test_the_matrix_verdict_passes_only_when_every_declared_case_arbitrated() -> None:
    passing = build_gate_e1_evidence(_artifacts(supervision_llm=_accepted_supervision()))
    verdict = summarise_gate_e1([passing, passing, passing], declared_case_count=3)
    assert verdict["satisfied"] is True
    assert verdict["cases_satisfying_gate"] == 3


# --- case report -----------------------------------------------------------


def _report(artifacts: CaseRunArtifacts) -> str:
    log = build_agent_reasoning_log(artifacts)
    return render_case_report(artifacts, log, build_gate_e1_evidence(artifacts))


def test_the_case_report_names_the_frozen_source_identity() -> None:
    report = _report(_artifacts())
    assert "02410_12-08-2024.pdf" in report
    assert "706" in report
    assert "development_exception" in report


def test_the_case_report_renders_a_verified_risk_with_its_calculation_and_page() -> None:
    report = _report(_artifacts())
    assert "cash_runway" in report
    assert "2.76 months" in report
    assert "page 563" in report
    assert "no bbox (parser does not produce one)" in report


def test_the_case_report_states_the_gate_verdict_for_this_case() -> None:
    assert "Gate E1 for this case: NOT satisfied" in _report(_artifacts())
    satisfied = _artifacts(supervision_llm=_accepted_supervision())
    assert "Gate E1 for this case: satisfied" in _report(satisfied)


def test_a_report_without_verified_risks_refuses_to_imply_coverage() -> None:
    artifacts = _artifacts(result=dict(_artifacts().result, verified_risks=[]))
    report = _report(artifacts)
    assert "nothing was written in" in report
    assert "cash_runway" not in report


def test_the_case_report_never_leaks_the_local_archive_path() -> None:
    """The prospectus location is licensed local state; artifacts must not carry it."""
    report = _report(_artifacts())
    assert "path_recorded" not in report
    assert "/Users/" not in report and "IPO_RISK_PROSPECTUS_ROOT" not in report
