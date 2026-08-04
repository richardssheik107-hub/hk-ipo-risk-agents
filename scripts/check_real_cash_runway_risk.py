"""Run the A1-to-A4 real 2410.HK cash-runway acceptance path."""

from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path

from ipo_risk.domain.cash_runway import CashRunwayBuildStatus, CashRunwayRiskBuilder
from ipo_risk.extraction import FinancialEvidenceExtractor
from ipo_risk.parsers.pymupdf_parser import PyMuPDFDocumentParser
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
        {item.chunk_id: item for item in chunks},
    )
    evidence_by_id = {
        item.evidence_id: item for item in [*cash_evidence, *cash_flow_evidence]
    }
    result = CashRunwayRiskBuilder().build(extraction, evidence_by_id)

    if result.calculation is not None:
        print(result.calculation.model_dump_json(indent=2))
    if result.risk_item is not None:
        print(result.risk_item.model_dump_json(indent=2))

    cash = extraction.cash_and_cash_equivalents
    cash_flow = extraction.operating_cash_flow
    risk = result.risk_item
    calculation = result.calculation
    checks = {
        "build_status": result.status == CashRunwayBuildStatus.BUILT,
        "cash": cash.normalized_value == Decimal("77208"),
        "operating_cash_flow": cash_flow.normalized_value == Decimal("-83918"),
        "period_months": cash_flow.period_months == 3,
        "calculation": calculation is not None and calculation.success,
        "runway": calculation is not None and calculation.result == "2.76",
        "calculation_unit": calculation is not None and calculation.unit == "months",
        "evidence_ids": calculation is not None
        and calculation.evidence_ids == [cash.evidence_id, cash_flow.evidence_id],
        "risk_code": risk is not None and risk.risk_code == "cash_runway",
        "canonical_code": risk is not None
        and risk.metadata.get("canonical_code") == "FIN_CASH_RUNWAY",
        "level": risk is not None and risk.level == RiskLevel.CRITICAL,
        "score": risk is not None and risk.score == 90,
        "pending": risk is not None
        and risk.verification_status == VerificationStatus.PENDING,
        "evidence_pages": risk is not None
        and [item.page for item in risk.evidence] == [563, 562],
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise AssertionError(f"A4 real acceptance mismatch: {', '.join(failed)}")

    print(f"exact_runway={risk.metadata['runway_months_exact']}")
    print(f"rounded_runway={risk.metadata['runway_months_rounded']}")
    print(f"monthly_burn={risk.metadata['monthly_burn']}")
    print("A4 real cash runway risk acceptance: passed")


if __name__ == "__main__":
    main()
