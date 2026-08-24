"""The v0.4 report answers all six PR-G questions and stays content-addressable."""
from __future__ import annotations

from datetime import date

import pytest

from ipo_risk.reporting.v03 import V03ReportGenerator
from ipo_risk.reporting.v04 import V04ReportGenerator
from ipo_risk.schemas import (
    Evidence,
    EvidenceSourceType,
    IPOProfile,
    ReportContext,
    RiskCategory,
    RiskItem,
    RiskLevel,
    SupervisionResult,
    VerificationStatus,
)
from ipo_risk.schemas.final_supervision import (
    ChannelStatus,
    FinalSupervisionInput,
    MarketContextView,
)
from ipo_risk.agents.final_supervisor import V04FinalSupervisor

EXPECTED_TITLES = (
    "IPO Profile", "System Runtime and Executive Risk Summary", "Financial Risks",
    "Legal Risks", "Business Risks", "Document Supervisor Summary", "Market Context",
    "Model Signal and Uncertainty", "Final Supervisor Synthesis", "Evidence Index",
    "Calculation Index", "Needs Human Review", "Methodology, Limitations and Governance",
)


def _risk() -> RiskItem:
    return RiskItem(
        risk_id="r-1", risk_code="cash_runway", category=RiskCategory.FINANCIAL,
        risk_type="cash_runway", level=RiskLevel.HIGH, score=70.0, conclusion="short runway",
        evidence=[Evidence(evidence_id="e-1", source_type=EvidenceSourceType.PROSPECTUS,
                           text="cash and cash equivalents", page=42)],
        agent_name="v03_financial", verification_status=VerificationStatus.VERIFIED)


def _context(**options) -> ReportContext:
    return ReportContext(
        analysis_id="a-1",
        profile=IPOProfile(company_name="Demo", stock_code="9999.HK", listing_date=date(2024, 6, 1)),
        verified_risks=[_risk()], pending_risks=[], rejected_risks=[], prediction=None,
        log_summary="0 workflow events", options={"workflow_version": "enhanced_v2", **options})


@pytest.fixture
def sections():
    supervision = SupervisionResult(verified_risks=[_risk()], summary="1 verified risk")
    final = V04FinalSupervisor().finalize(FinalSupervisionInput(document_supervision=supervision))
    market = MarketContextView(status=ChannelStatus.DISABLED, reason="fixture, not market data")
    return V04ReportGenerator().generate(_context(final_supervision=final, market_context=market))


def test_v03_generator_is_untouched() -> None:
    """The frozen ten-section deliverable must not move."""
    assert len(V03ReportGenerator().generate(_context())) == 10


def test_thirteen_sections_in_the_documented_order(sections) -> None:
    assert tuple(section.title for section in sections) == EXPECTED_TITLES
    assert [section.order for section in sections] == list(range(1, 14))


def test_section_ids_are_deterministic(sections) -> None:
    """uuid4 defaults would make the report non-content-addressable."""
    assert [section.section_id for section in sections] == [f"v04-section-{i:02d}" for i in range(1, 14)]


def test_methodology_drops_the_stale_v03_sentence(sections) -> None:
    text = sections[-1].summary
    assert "outside v0.3" not in text
    assert "not probabilities" in text
    # Calibrated probability is still explicitly out of scope.
    assert "calibrated probability remains outside v0.4" in text
    assert "uncalibrated_model_score" in text


def test_every_referenced_id_resolves_within_the_report(sections) -> None:
    """The necessary condition for the traceability target."""
    synthesis = next(section for section in sections if section.order == 9)
    evidence_index = next(section for section in sections if section.title == "Evidence Index")
    known_evidence = {entry["evidence_id"] for entry in evidence_index.metadata["entries"]}
    assert set(synthesis.metadata["referenced_evidence_ids"]) <= known_evidence
    assert set(synthesis.metadata["referenced_risk_ids"]) == {"r-1"}


def test_market_section_states_absence_rather_than_omitting_it(sections) -> None:
    market = next(section for section in sections if section.title == "Market Context")
    assert "disabled" in market.summary
    assert market.metadata["observations"] == []


def test_model_section_never_calls_the_score_a_probability(sections) -> None:
    model = next(section for section in sections if section.title == "Model Signal and Uncertainty")
    assert "probability" not in model.summary.lower()
    assert model.metadata["model_prediction"] is None


def test_channels_that_did_not_run_are_named_not_faked() -> None:
    sections = V04ReportGenerator().generate(_context())
    for title in ("Market Context", "Model Signal and Uncertainty", "Final Supervisor Synthesis"):
        section = next(item for item in sections if item.title == title)
        assert "did not run" in section.summary
        assert section.metadata == {}
