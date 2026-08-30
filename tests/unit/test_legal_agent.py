from __future__ import annotations

from typing import Any

import pytest

from ipo_risk.agents.legal import LegalAgent
from ipo_risk.providers.llm import LLMFailureKind, LLMProviderError, UnavailableLLMProvider
from ipo_risk.providers.mock import MockLLMProvider
from ipo_risk.schemas import (
    DiagnosticCode,
    DocumentChunk,
    Evidence,
    IPOProfile,
    VerificationStatus,
)


RIGHT_TEXT = (
    "Under the Pre-IPO Investment Agreement, Series B investors hold redemption rights "
    "that survive the Listing and remain effective after Listing."
)
LITIGATION_TEXT = (
    "Proceedings remain pending before the High Court. Management considers the claim "
    "material, involving RMB 2 million and possible operational loss."
)


def _evidence(text: str, evidence_id: str, page: int) -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        document_id="ipo-case",
        chunk_id=f"ipo-case:{page}",
        page=page,
        text=text,
    )


RIGHT_EVIDENCE = _evidence(RIGHT_TEXT, "e-right", 20)
LITIGATION_EVIDENCE = _evidence(LITIGATION_TEXT, "e-litigation", 30)


class RoutedRetriever:
    def __init__(
        self,
        rights: list[Evidence] | None = None,
        litigation: list[Evidence] | None = None,
        fail_rights: bool = False,
    ) -> None:
        self.rights = rights or []
        self.litigation = litigation or []
        self.fail_rights = fail_rights
        self.calls: list[tuple[str, int]] = []

    def retrieve(self, chunks, query, limit=3):
        self.calls.append((query, limit))
        if query == LegalAgent.rights_query:
            if self.fail_rights:
                raise RuntimeError("rights retrieval failed")
            return self.rights[:limit]
        if query == LegalAgent.litigation_query:
            return self.litigation[:limit]
        return []


class ExplodingRightsBuilder:
    def build(self, fact, evidence_by_id):
        raise RuntimeError("rights builder failed")


class FailingLLMProvider:
    name = "failing"
    last_call_metadata = None

    def __init__(self, kind: LLMFailureKind, attempts: int = 2) -> None:
        self.kind = kind
        self.attempts = attempts

    def complete(self, prompt: str) -> str:
        raise AssertionError("unused")

    def generate_structured(self, **kwargs):
        raise LLMProviderError(
            self.kind,
            "safe test failure",
            recoverable=self.kind == LLMFailureKind.TRANSPORT,
            attempts=self.attempts,
        )


def _profile() -> IPOProfile:
    return IPOProfile(company_name="IPO Case")


def test_rights_review_retrieval_is_bounded_to_twenty_without_widening_litigation() -> None:
    retriever = RoutedRetriever()
    agent = LegalAgent(retriever=retriever, llm_provider=MockLLMProvider())

    agent.analyze(_profile(), [])

    assert (LegalAgent.rights_query, 20) in retriever.calls
    assert (LegalAgent.litigation_query, 10) in retriever.calls


def _responses(
    *,
    rights: dict[str, Any] | None = None,
    litigation: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    return {
        "shareholder_rights_extract": rights
        or {
            "right_type": "redemption_right",
            "holder": "Series B investors",
            "is_effective": True,
            "survives_listing": True,
            "termination_event": "",
            "termination_timing": "after_listing",
            "restoration_clause": False,
            "restoration_condition": "",
            "impact_on_public_shareholders": "preferential exit right",
            "evidence_ids": ["e-right"],
        },
        "litigation_compliance_extract": litigation
        or {
            "matter_type": "litigation",
            "subject": "supplier claim",
            "counterparty_or_authority": "supplier",
            "event_date": "2023-01-01",
            "amount": "2",
            "currency": "RMB",
            "amount_unit": "million",
            "current_status": "pending",
            "is_pending": True,
            "is_resolved": False,
            "management_materiality": "material",
            "potential_impact": "operational loss",
            "evidence_ids": ["e-litigation"],
        },
    }


def _diagnostic(agent: LegalAgent, risk_code: str):
    return next(item for item in agent.last_diagnostics if item.risk_code == risk_code)


def test_legal_agent_aggregates_both_risks_as_pending_candidates() -> None:
    agent = LegalAgent(
        retriever=RoutedRetriever([RIGHT_EVIDENCE], [LITIGATION_EVIDENCE]),
        llm_provider=MockLLMProvider(_responses()),
    )

    risks = agent.analyze(_profile(), [])

    assert [item.risk_code for item in risks] == [
        "redemption_rights",
        "material_litigation_compliance",
    ]
    assert all(item.verification_status == VerificationStatus.PENDING for item in risks)
    assert all(item.evidence for item in risks)
    assert all(item.verification_status != VerificationStatus.VERIFIED for item in risks)
    assert len(agent.last_diagnostics) == 2
    assert all(item.code == DiagnosticCode.RISK_GENERATED for item in agent.last_diagnostics)


def test_invalid_rights_llm_json_does_not_stop_litigation_component() -> None:
    responses = _responses()
    responses["shareholder_rights_extract"] = {"right_type": "redemption_right"}
    agent = LegalAgent(
        retriever=RoutedRetriever([RIGHT_EVIDENCE], [LITIGATION_EVIDENCE]),
        llm_provider=MockLLMProvider(responses),
    )

    risks = agent.analyze(_profile(), [])

    assert [item.risk_code for item in risks] == ["material_litigation_compliance"]
    rights = _diagnostic(agent, "redemption_rights")
    litigation = _diagnostic(agent, "material_litigation_compliance")
    assert rights.code == DiagnosticCode.EXTRACTION_FAILED
    assert "llm_structured_output_invalid" in rights.metadata["internal_issue_codes"]
    assert rights.metadata["failure_isolated"] is True
    assert litigation.code == DiagnosticCode.RISK_GENERATED


def test_rights_builder_failure_does_not_stop_litigation_component() -> None:
    agent = LegalAgent(
        retriever=RoutedRetriever([RIGHT_EVIDENCE], [LITIGATION_EVIDENCE]),
        llm_provider=MockLLMProvider(_responses()),
        rights_builder=ExplodingRightsBuilder(),
    )

    risks = agent.analyze(_profile(), [])

    assert [item.risk_code for item in risks] == ["material_litigation_compliance"]
    rights = _diagnostic(agent, "redemption_rights")
    assert rights.code == DiagnosticCode.COMPONENT_FAILURE
    assert rights.metadata["component"] == "risk_builder"


def test_rights_retrieval_failure_does_not_stop_litigation_component() -> None:
    agent = LegalAgent(
        retriever=RoutedRetriever(
            [RIGHT_EVIDENCE], [LITIGATION_EVIDENCE], fail_rights=True
        ),
        llm_provider=MockLLMProvider(_responses()),
    )

    risks = agent.analyze(_profile(), [])

    assert [item.risk_code for item in risks] == ["material_litigation_compliance"]
    assert _diagnostic(agent, "redemption_rights").code == DiagnosticCode.COMPONENT_FAILURE


def test_terminated_right_is_not_a_current_risk() -> None:
    responses = _responses(
        rights={
            "right_type": "redemption_right",
            "holder": "Series B investors",
            "is_effective": False,
            "survives_listing": False,
            "termination_event": "listing",
            "termination_timing": "on_listing",
            "restoration_clause": False,
            "restoration_condition": "",
            "impact_on_public_shareholders": "",
            "evidence_ids": ["e-right"],
        }
    )
    agent = LegalAgent(
        retriever=RoutedRetriever([RIGHT_EVIDENCE], []),
        llm_provider=MockLLMProvider(responses),
    )

    risks = agent.analyze(_profile(), [])

    assert not any(item.risk_code == "redemption_rights" for item in risks)
    diagnostic = _diagnostic(agent, "redemption_rights")
    assert diagnostic.code == DiagnosticCode.NOT_APPLICABLE
    assert "historical_right_only" in diagnostic.metadata["internal_issue_codes"]


def test_restorable_right_generates_pending_candidate() -> None:
    responses = _responses(
        rights={
            "right_type": "redemption_right",
            "holder": "Series B investors",
            "is_effective": False,
            "survives_listing": False,
            "termination_event": "listing",
            "termination_timing": "on_listing",
            "restoration_clause": True,
            "restoration_condition": "the Listing does not occur",
            "impact_on_public_shareholders": "conditional preferential exit right",
            "evidence_ids": ["e-right"],
        }
    )
    agent = LegalAgent(
        retriever=RoutedRetriever([RIGHT_EVIDENCE], []),
        llm_provider=MockLLMProvider(responses),
    )

    risks = agent.analyze(_profile(), [])

    rights = next(item for item in risks if item.risk_code == "redemption_rights")
    assert rights.verification_status == VerificationStatus.PENDING
    assert rights.metadata["restoration_clause"] is True


def test_ambiguous_rights_state_emits_needs_review_risk_and_diagnostic() -> None:
    responses = _responses(
        rights={
            "right_type": "redemption_right",
            "holder": "Series B investors",
            "is_effective": None,
            "survives_listing": None,
            "termination_event": "",
            "termination_timing": "",
            "restoration_clause": None,
            "restoration_condition": "",
            "impact_on_public_shareholders": "unclear",
            "evidence_ids": ["e-right"],
        }
    )
    agent = LegalAgent(
        retriever=RoutedRetriever([RIGHT_EVIDENCE], []),
        llm_provider=MockLLMProvider(responses),
    )

    risks = agent.analyze(_profile(), [])

    rights = next(item for item in risks if item.risk_code == "redemption_rights")
    assert rights.verification_status == VerificationStatus.NEEDS_REVIEW
    diagnostic = _diagnostic(agent, "redemption_rights")
    assert diagnostic.code == DiagnosticCode.NEEDS_REVIEW
    assert "termination_clause_not_found" in diagnostic.metadata["internal_issue_codes"]


def test_negative_litigation_short_circuits_without_llm_key() -> None:
    negative = _evidence(
        "The Group is not involved in any material litigation.", "e-negative", 30
    )
    agent = LegalAgent(
        retriever=RoutedRetriever([], [negative]),
        llm_provider=UnavailableLLMProvider("test unavailable"),
    )

    risks = agent.analyze(_profile(), [])

    assert risks == []
    diagnostic = _diagnostic(agent, "material_litigation_compliance")
    assert diagnostic.code == DiagnosticCode.NOT_APPLICABLE
    assert "negation_detected" in diagnostic.metadata["internal_issue_codes"]


def test_explicit_rights_without_llm_key_emits_fail_closed_review_candidate() -> None:
    agent = LegalAgent(
        retriever=RoutedRetriever([RIGHT_EVIDENCE], [LITIGATION_EVIDENCE]),
        llm_provider=UnavailableLLMProvider("test unavailable"),
    )

    risks = agent.analyze(_profile(), [])

    assert [item.risk_code for item in risks] == ["redemption_rights"]
    rights = risks[0]
    assert rights.verification_status == VerificationStatus.NEEDS_REVIEW
    assert rights.metadata["extraction_method"] == (
        "deterministic_explicit_signal_needs_review_v1"
    )
    assert len(agent.last_diagnostics) == 2
    rights_diagnostic = _diagnostic(agent, "redemption_rights")
    assert rights_diagnostic.code == DiagnosticCode.NEEDS_REVIEW
    assert "llm_provider_unavailable" in rights_diagnostic.metadata[
        "internal_issue_codes"
    ]
    assert rights_diagnostic.metadata["provider_fallback_reason"] == (
        "provider_unavailable"
    )
    litigation_diagnostic = _diagnostic(agent, "material_litigation_compliance")
    assert litigation_diagnostic.code == DiagnosticCode.EXTRACTION_FAILED
    assert "llm_provider_unavailable" in litigation_diagnostic.metadata[
        "internal_issue_codes"
    ]


def test_ordinary_share_redemption_without_llm_key_remains_unavailable() -> None:
    ordinary = _evidence(
        "The articles permit all ordinary shareholders to redeem shares before Listing.",
        "e-ordinary-right",
        21,
    )
    agent = LegalAgent(
        retriever=RoutedRetriever([ordinary], []),
        llm_provider=UnavailableLLMProvider("test unavailable"),
    )

    risks = agent.analyze(_profile(), [])

    assert risks == []
    diagnostic = _diagnostic(agent, "redemption_rights")
    assert diagnostic.code == DiagnosticCode.EXTRACTION_FAILED
    assert diagnostic.metadata["failure_kind"] == "unavailable"


def test_transport_failure_does_not_use_deterministic_rights_fallback() -> None:
    agent = LegalAgent(
        retriever=RoutedRetriever([RIGHT_EVIDENCE], []),
        llm_provider=FailingLLMProvider(LLMFailureKind.TRANSPORT),
    )

    risks = agent.analyze(_profile(), [])

    assert risks == []
    diagnostic = _diagnostic(agent, "redemption_rights")
    assert diagnostic.code == DiagnosticCode.COMPONENT_FAILURE
    assert diagnostic.metadata["failure_kind"] == "transport"


@pytest.mark.parametrize(
    ("kind", "expected_code", "expected_issue"),
    [
        (
            LLMFailureKind.RESPONSE_VALIDATION,
            DiagnosticCode.EXTRACTION_FAILED,
            "llm_structured_output_invalid",
        ),
        (
            LLMFailureKind.AUTHENTICATION,
            DiagnosticCode.COMPONENT_FAILURE,
            "llm_authentication_failure",
        ),
        (
            LLMFailureKind.TRANSPORT,
            DiagnosticCode.COMPONENT_FAILURE,
            "llm_transport_failure",
        ),
    ],
)
def test_public_llm_failures_map_to_safe_diagnostics(
    kind: LLMFailureKind,
    expected_code: DiagnosticCode,
    expected_issue: str,
) -> None:
    agent = LegalAgent(
        retriever=RoutedRetriever([RIGHT_EVIDENCE], [LITIGATION_EVIDENCE]),
        llm_provider=FailingLLMProvider(kind, attempts=3),
    )

    assert agent.analyze(_profile(), []) == []

    for diagnostic in agent.last_diagnostics:
        assert diagnostic.code == expected_code
        assert expected_issue in diagnostic.metadata["internal_issue_codes"]
        assert diagnostic.metadata["failure_kind"] == kind.value
        assert diagnostic.metadata["attempts"] == 3
        assert "safe test failure" not in diagnostic.message


def test_resolved_litigation_is_not_a_current_risk() -> None:
    resolved = _evidence(
        "The historical litigation was settled and closed after payment.",
        "e-litigation",
        30,
    )
    responses = _responses(
        litigation={
            "matter_type": "litigation",
            "subject": "historical supplier claim",
            "counterparty_or_authority": "supplier",
            "event_date": "2020-01-01",
            "amount": "2",
            "currency": "RMB",
            "amount_unit": "million",
            "current_status": "resolved",
            "is_pending": False,
            "is_resolved": True,
            "management_materiality": "not_material",
            "potential_impact": "paid with no continuing impact",
            "evidence_ids": ["e-litigation"],
        }
    )
    agent = LegalAgent(
        retriever=RoutedRetriever([], [resolved]),
        llm_provider=MockLLMProvider(responses),
    )

    risks = agent.analyze(_profile(), [])

    assert not any(item.risk_code == "material_litigation_compliance" for item in risks)
    diagnostic = _diagnostic(agent, "material_litigation_compliance")
    assert diagnostic.code == DiagnosticCode.NOT_APPLICABLE
    assert "matter_resolved" in diagnostic.metadata["internal_issue_codes"]


def test_unclear_litigation_materiality_emits_needs_review() -> None:
    responses = _responses(
        litigation={
            "matter_type": "litigation",
            "subject": "supplier claim",
            "counterparty_or_authority": "supplier",
            "event_date": "2023-01-01",
            "amount": "2",
            "currency": "RMB",
            "amount_unit": "million",
            "current_status": "pending",
            "is_pending": True,
            "is_resolved": False,
            "management_materiality": "",
            "potential_impact": "operational loss",
            "evidence_ids": ["e-litigation"],
        }
    )
    agent = LegalAgent(
        retriever=RoutedRetriever([], [LITIGATION_EVIDENCE]),
        llm_provider=MockLLMProvider(responses),
    )

    risks = agent.analyze(_profile(), [])

    litigation = next(
        item for item in risks if item.risk_code == "material_litigation_compliance"
    )
    assert litigation.verification_status == VerificationStatus.NEEDS_REVIEW
    diagnostic = _diagnostic(agent, "material_litigation_compliance")
    assert diagnostic.code == DiagnosticCode.NEEDS_REVIEW
    assert "materiality_unclear" in diagnostic.metadata["internal_issue_codes"]


def test_no_evidence_returns_empty_with_two_explicit_diagnostics() -> None:
    agent = LegalAgent(retriever=RoutedRetriever())

    assert agent.analyze(_profile(), []) == []
    assert len(agent.last_diagnostics) == 2
    assert all(
        item.code == DiagnosticCode.EVIDENCE_NOT_FOUND
        for item in agent.last_diagnostics
    )
