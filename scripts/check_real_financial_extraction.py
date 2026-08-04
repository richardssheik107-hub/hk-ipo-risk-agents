"""Local A3 acceptance check against the provisional 2410.HK gold fixture."""

from __future__ import annotations

import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from ipo_risk.extraction import ExtractionStatus, FinancialEvidenceExtractor, FinancialMetricValue
from ipo_risk.parsers.pymupdf_parser import PyMuPDFDocumentParser
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.schemas import DocumentChunk, DocumentParseRequest, Evidence


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "real_case_001" / "expected_evidence.json"
DEFAULT_PDF = ROOT / "data" / "local" / "real_case_001" / "prospectus.pdf"


def _assert_metric(
    metric: FinancialMetricValue,
    expected: dict[str, Any],
    candidates: list[Evidence],
    chunks_by_id: dict[str, DocumentChunk],
) -> None:
    checks = {
        "status": metric.status == ExtractionStatus.EXTRACTED,
        "page": metric.page == expected["page"],
        "chunk_id": metric.chunk_id == expected["chunk_id"],
        "raw_label": metric.raw_label == expected["label"],
        "raw_value": metric.raw_value == expected["raw_value"],
        "normalized_value": metric.normalized_value == Decimal(str(expected["normalized_value"])),
        "currency": metric.currency == expected["currency"],
        "unit": metric.unit == expected["unit"],
        "period_end": metric.period_end is not None
        and metric.period_end.isoformat() == expected["period_end"],
        "evidence_id": metric.evidence_id in {item.evidence_id for item in candidates},
        "issues": metric.issues == [],
        "extraction_method": metric.extraction_method == "page_text_rule",
    }
    if "period_months" in expected:
        checks["period_months"] = metric.period_months == expected["period_months"]
    else:
        checks["period_months"] = metric.period_months is None

    source = chunks_by_id.get(metric.chunk_id or "")
    checks["source_chunk"] = source is not None
    checks["raw_label_in_source"] = source is not None and metric.raw_label in source.text
    checks["raw_value_in_source"] = source is not None and metric.raw_value in source.text
    context = [chunks_by_id.get(chunk_id) for chunk_id in metric.context_chunk_ids]
    checks["context_chunks"] = all(item is not None for item in context)
    checks["context_document"] = source is not None and all(
        item is not None and item.document_id == source.document_id for item in context
    )
    checks["context_distance"] = source is not None and all(
        item is not None and abs(item.page - source.page) <= 1 for item in context
    )
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise AssertionError(f"{metric.metric_name} acceptance mismatch: {', '.join(failed)}")


def _print_metric(metric: FinancialMetricValue) -> None:
    print(f"metric={metric.metric_name}")
    print(f"  status={metric.status}")
    print(f"  page={metric.page} chunk_id={metric.chunk_id} evidence_id={metric.evidence_id}")
    print(f"  raw_label={metric.raw_label}")
    print(f"  raw_value={metric.raw_value} normalized_value={metric.normalized_value}")
    print(f"  currency={metric.currency} unit={metric.unit}")
    print(f"  period_end={metric.period_end} period_months={metric.period_months}")
    print(f"  context_pages={metric.context_pages}")
    print(f"  extraction_method={metric.extraction_method}")
    print(f"  issues={metric.issues}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    pdf_path = Path(os.getenv("IPO_RISK_REAL_CASE_PDF", str(DEFAULT_PDF)))
    expected = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    chunks = PyMuPDFDocumentParser().parse(
        DocumentParseRequest(document_id="real_case_001", prospectus_path=str(pdf_path))
    )
    retriever = KeywordDocumentRetriever()
    cash_evidence = retriever.retrieve(chunks, "现金流量表期末现金及现金等价物", limit=5)
    ocf_evidence = retriever.retrieve(chunks, "经营活动现金流", limit=5)
    result = FinancialEvidenceExtractor().extract(
        cash_evidence,
        ocf_evidence,
        chunks_by_id := {item.chunk_id: item for item in chunks},
    )

    _print_metric(result.cash_and_cash_equivalents)
    _print_metric(result.operating_cash_flow)
    _assert_metric(
        result.cash_and_cash_equivalents,
        expected["cash_and_cash_equivalents"],
        cash_evidence,
        chunks_by_id,
    )
    _assert_metric(
        result.operating_cash_flow,
        expected["operating_cash_flow"],
        ocf_evidence,
        chunks_by_id,
    )
    print("A3 real financial extraction acceptance: passed")


if __name__ == "__main__":
    main()
