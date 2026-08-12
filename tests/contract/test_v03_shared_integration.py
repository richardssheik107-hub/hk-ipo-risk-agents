"""Contracts for the owner-waiver v0.3 shared integration boundary."""

from __future__ import annotations

from dataclasses import replace

from ipo_risk.agents.supervisor_v03 import V03Supervisor
from ipo_risk.agents.verifier_router import SpecializedVerifierRouter
from ipo_risk.core.config import Settings, load_settings
from ipo_risk.core.container import DependencyContainer, default_registry
from ipo_risk.reporting.v03 import V03ReportGenerator
from ipo_risk.schemas import (
    Evidence,
    IPOAnalysisRequest,
    IPOProfile,
    ReportContext,
    RiskCategory,
    RiskItem,
    RiskLevel,
    VerificationResult,
    VerificationStatus,
    SupervisionResult,
)
from ipo_risk.workflows.enhanced_v2 import EnhancedV2Workflow


def _risk(
    code: str,
    category: RiskCategory,
    agent: str,
    *,
    status: VerificationStatus = VerificationStatus.PENDING,
    metadata: dict | None = None,
) -> RiskItem:
    evidence = Evidence(
        evidence_id=f"ev-{code}",
        document_id="doc",
        chunk_id=f"chunk-{code}",
        page=1,
        text=f"Evidence for {code}",
    )
    return RiskItem(
        risk_code=code,
        category=category,
        risk_type=code,
        level=RiskLevel.MEDIUM,
        score=60,
        conclusion=f"Candidate {code}",
        evidence=[evidence],
        agent_name=agent,
        verification_status=status,
        metadata=metadata or {},
    )


class _BatchVerifier:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    def verify(self, risks, evidence_by_code):
        if self.fail:
            raise RuntimeError("isolated failure")
        return VerificationResult(
            verified_risks=[
                item.model_copy(
                    update={"verification_status": VerificationStatus.VERIFIED}
                )
                for item in risks
            ]
        )


class _LegalResult:
    def __init__(self, risk: RiskItem) -> None:
        self.status = VerificationStatus.VERIFIED
        self.reviewed_risk = risk.model_copy(
            update={"verification_status": VerificationStatus.VERIFIED}
        )
        self.verified_risk = self.reviewed_risk


class _LegalVerifier:
    def verify(self, risk, available):
        return _LegalResult(risk)


def test_specialized_router_isolates_one_domain_failure() -> None:
    financial = _risk("revenue_growth", RiskCategory.FINANCIAL, "financial")
    business = _risk("precommercial_product", RiskCategory.BUSINESS, "business")
    legal = _risk("redemption_rights", RiskCategory.LEGAL, "legal")
    router = SpecializedVerifierRouter(
        financial_verifier=_BatchVerifier(fail=True),
        legal_rights_verifier=_LegalVerifier(),
        litigation_verifier=_LegalVerifier(),
        business_verifier=_BatchVerifier(),
    )

    result = router.verify([financial, business, legal], {})

    assert {item.risk_code for item in result.verified_risks} == {
        "precommercial_product",
        "redemption_rights",
    }
    assert [item.risk_code for item in result.pending_risks] == ["revenue_growth"]
    assert result.pending_risks[0].verification_status == VerificationStatus.NEEDS_REVIEW
    assert router.last_diagnostics["financial"]["failed"] is True
    assert router.last_diagnostics["output_count"] == 3


def test_v03_supervisor_distinguishes_generic_and_product_revenue() -> None:
    financial = _risk(
        "revenue_growth",
        RiskCategory.FINANCIAL,
        "financial",
        status=VerificationStatus.VERIFIED,
    )
    business = _risk(
        "precommercial_product",
        RiskCategory.BUSINESS,
        "business",
        status=VerificationStatus.VERIFIED,
        metadata={"has_product_revenue": False, "revenue_source_types": ["licensing"]},
    )

    result = V03Supervisor().supervise([financial, business])

    assert not result.conflicts
    assert result.composite_findings[0].metadata["classification"] == (
        "NO_CONFLICT_DIFFERENT_REVENUE_SEMANTICS"
    )
    assert len(result.verified_risks) == 2


def test_v03_supervisor_deduplicates_different_risk_ids() -> None:
    first = _risk(
        "revenue_growth",
        RiskCategory.FINANCIAL,
        "financial",
        status=VerificationStatus.VERIFIED,
    )
    second = first.model_copy(
        update={"risk_id": "different-id", "score": 80, "conclusion": "stronger"}
    )

    result = V03Supervisor().supervise([first, second])

    assert len(result.verified_risks) == 1
    assert result.verified_risks[0].risk_id == "different-id"
    assert result.duplicate_groups[0].source_risk_ids == [first.risk_id, "different-id"]


def test_v03_report_has_stable_governance_sections() -> None:
    pending = _risk("precommercial_product", RiskCategory.BUSINESS, "business")
    sections = V03ReportGenerator().generate(
        ReportContext(
            analysis_id="analysis",
            profile=IPOProfile(company_name="Example"),
            pending_risks=[pending],
            options={
                "workflow_version": "enhanced_v2",
                "owner_waiver": {
                    "financial_second_review_deferred": True,
                    "business_second_review_deferred": True,
                },
            },
        )
    )

    assert [item.order for item in sections] == list(range(1, 11))
    assert sections[-1].title == "Limitations and Governance"
    assert "must not be represented as completed" in sections[-1].summary


def test_v03_configs_select_enhanced_workflow_and_preserve_mvp_default() -> None:
    offline = load_settings("configs/v03_offline.yaml")
    ai = load_settings("configs/v03_ai.yaml")
    assert offline.workflow_version == ai.workflow_version == "enhanced_v2"
    assert offline.llm_provider == "unavailable"
    assert ai.llm_provider == "openai_compatible"
    assert isinstance(
        DependencyContainer(offline, default_registry()).create_workflow(),
        EnhancedV2Workflow,
    )
    assert Settings().workflow_version == "mvp_v1"


def test_unregistered_workflow_fails_clearly() -> None:
    settings = replace(Settings(), workflow_version="missing")
    try:
        DependencyContainer(settings, default_registry()).create_workflow()
    except ValueError as exc:
        assert "Unregistered workflow version" in str(exc)
    else:  # pragma: no cover - explicit contract failure
        raise AssertionError("missing workflow must fail")


class _Parser:
    name = "test"
    last_errors: list = []

    def parse(self, request):
        return []


class _Provider:
    def get_profile(self, company_name, stock_code):
        return IPOProfile(company_name=company_name, stock_code=stock_code)


class _MarketProvider:
    def get_snapshot(self, profile):
        from ipo_risk.schemas import MarketSnapshot

        return MarketSnapshot(source="test")


class _Agent:
    def __init__(self, name: str, *, fail: bool = False) -> None:
        self.name = name
        self.fail = fail

    def analyze(self, profile, chunks, market):
        if self.fail:
            raise RuntimeError("agent failed")
        return []


class _EmptyVerifier:
    last_diagnostics = {"input_count": 0, "output_count": 0}

    def verify(self, risks, evidence):
        return VerificationResult()


class _Supervisor:
    def supervise(self, risks):
        return SupervisionResult(summary="supervised")


class _Predictor:
    def predict(self, risks, market):
        return None


def test_enhanced_workflow_isolates_agent_failure_and_still_reports() -> None:
    workflow = EnhancedV2Workflow(
        _Parser(),
        object(),
        [_Agent("financial", fail=True), _Agent("legal"), _Agent("business")],
        _EmptyVerifier(),
        _Supervisor(),
        _Predictor(),
        V03ReportGenerator(),
        _MarketProvider(),
        _Provider(),
    )

    state = workflow.invoke(
        {
            "request": IPOAnalysisRequest(company_name="Example", workflow_version="enhanced_v2"),
            "candidates": [],
            "verified_risks": [],
            "pending_risks": [],
            "rejected_risks": [],
            "agent_logs": [],
            "errors": [],
        }
    )

    assert any(error.component == "financial" for error in state["errors"])
    assert state["component_diagnostics"]["financial"] == {}
    assert len(state["report_sections"]) == 10
    assert state["component_diagnostics"]["supervisor"]["summary"] == "supervised"
