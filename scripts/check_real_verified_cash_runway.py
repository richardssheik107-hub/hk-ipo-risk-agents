"""Run the real A1-to-A5 verified cash-runway and rule-score acceptance path."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from ipo_risk.agents.rules import RuleVerifier
from ipo_risk.domain.cash_runway import CashRunwayBuildStatus, CashRunwayRiskBuilder
from ipo_risk.extraction import FinancialEvidenceExtractor
from ipo_risk.parsers.pymupdf_parser import PyMuPDFDocumentParser
from ipo_risk.predictors.rule_based import RuleBasedPredictor
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.schemas import DocumentParseRequest, RiskLevel, VerificationStatus


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = ROOT / "data" / "local" / "real_case_001" / "prospectus.pdf"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    pdf_path = Path(os.getenv("IPO_RISK_REAL_CASE_PDF", str(DEFAULT_PDF)))
    chunks = PyMuPDFDocumentParser().parse(
        DocumentParseRequest(document_id="real_case_001", prospectus_path=str(pdf_path))
    )
    retriever = KeywordDocumentRetriever()
    cash_evidence = retriever.retrieve(
        chunks, "现金流量表期末现金及现金等价物", limit=5
    )
    cash_flow_evidence = retriever.retrieve(chunks, "经营活动现金流", limit=5)
    extraction = FinancialEvidenceExtractor().extract(
        cash_evidence,
        cash_flow_evidence,
        {chunk.chunk_id: chunk for chunk in chunks},
    )
    evidence_by_id = {
        item.evidence_id: item for item in [*cash_evidence, *cash_flow_evidence]
    }
    built = CashRunwayRiskBuilder().build(extraction, evidence_by_id)
    if built.status != CashRunwayBuildStatus.BUILT or built.risk_item is None:
        raise AssertionError(f"A4 build failed: {built.issues}")

    verification = RuleVerifier().verify(
        [built.risk_item], {"cash_runway": built.risk_item.evidence}
    )
    prediction = RuleBasedPredictor().predict(
        verification.verified_risks + verification.pending_risks, None
    )

    verified = verification.verified_risks[0] if verification.verified_risks else None
    checks = {
        "cash_page": extraction.cash_and_cash_equivalents.page == 563,
        "cash_flow_page": extraction.operating_cash_flow.page == 562,
        "runway": built.calculation is not None and built.calculation.result == "2.76",
        "verified_count": len(verification.verified_risks) == 1,
        "pending_count": len(verification.pending_risks) == 0,
        "verified_status": verified is not None
        and verified.verification_status == VerificationStatus.VERIFIED,
        "risk_level": verified is not None and verified.level == RiskLevel.CRITICAL,
        "risk_score": verified is not None and verified.score == 90,
        "prediction_score": prediction.risk_score == 90,
        "prediction_level": prediction.risk_level == RiskLevel.CRITICAL,
        "probabilities": prediction.probabilities == {},
        "non_probability": prediction.metadata.get("score_is_probability") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise AssertionError(f"A5 real acceptance mismatch: {', '.join(failed)}")

    assert verified is not None and verified.calculation is not None
    print(f"evidence_ids={verified.calculation.evidence_ids}")
    print(f"evidence_pages={[item.page for item in verified.evidence]}")
    print(f"calculation={verified.calculation.model_dump_json()}")
    print(f"verification_notes={verified.verification_notes}")
    print(f"top_factors={[item.model_dump() for item in prediction.top_factors]}")
    print(f"missing_features={prediction.metadata['missing_features']}")
    print(f"degraded_mode={prediction.metadata['degraded_mode']}")
    print("A5 real verified cash runway acceptance: passed")


if __name__ == "__main__":
    main()
