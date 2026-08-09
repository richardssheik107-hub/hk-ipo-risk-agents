from __future__ import annotations

import inspect

from ipo_risk.agents.base import RiskAgent
from ipo_risk.agents.business_models import CommercializationCandidate, CoreProductCandidate
from ipo_risk.agents.business_v03 import V03BusinessAgent
from ipo_risk.domain.risk_codes import V03_RISK_OWNERS, requirement_for
from ipo_risk.schemas import ComponentDiagnostic, DocumentChunk, IPOProfile, VerificationStatus


def positive_chunk() -> DocumentChunk:
    return DocumentChunk(
        document_id="doc", chunk_id="business", page=1, section="業務",
        text="ABC-101（我們的核心產品）處於臨床III期，尚未商業化，尚未從產品銷售產生任何收入。",
    )


def test_exact_risk_agent_signature_and_runtime_protocol() -> None:
    assert inspect.signature(V03BusinessAgent.analyze) == inspect.signature(RiskAgent.analyze)
    agent = V03BusinessAgent()
    assert agent.name == "business"
    risks = agent.analyze(IPOProfile(company_name="Demo"), [positive_chunk()])
    assert isinstance(risks, list)


def test_business_agent_only_emits_its_owned_pending_code() -> None:
    agent = V03BusinessAgent()
    risks = agent.analyze(IPOProfile(company_name="Demo"), [positive_chunk()])
    assert {item.risk_code for item in risks} <= {"precommercial_product"}
    assert all(V03_RISK_OWNERS[item.risk_code] == "business" for item in risks)
    assert all(item.verification_status == VerificationStatus.PENDING for item in risks)
    assert all(item.calculation is None for item in risks)
    assert all(isinstance(item, ComponentDiagnostic) for item in agent.last_diagnostics)


def test_frozen_candidate_models_retain_exact_fields() -> None:
    assert set(CommercializationCandidate.model_fields) == {
        "product_name", "development_stage", "has_product_revenue",
        "commercialization_dependency", "evidence_ids",
    }
    assert set(CoreProductCandidate.model_fields) == {
        "product_name", "is_core_product", "approval_status", "launch_status", "evidence_ids",
    }


def test_precommercial_requirement_is_evidence_without_calculation() -> None:
    requirement = requirement_for("precommercial_product")
    assert requirement.requires_evidence is True
    assert requirement.requires_calculation is False


def test_no_public_contract_module_was_needed() -> None:
    assert inspect.get_annotations(V03BusinessAgent.analyze)["return"] == "list[RiskItem]"
