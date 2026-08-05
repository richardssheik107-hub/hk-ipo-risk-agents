from __future__ import annotations

from decimal import Decimal

from pydantic import TypeAdapter

from ipo_risk.extraction import (
    ExtractionStatus,
    FinancialEvidenceExtractor,
    FinancialExtractionResult,
    FinancialMetricValue,
)
from ipo_risk.schemas import DocumentChunk, Evidence


def test_extractor_contract_accepts_evidence_and_chunk_mapping() -> None:
    source = DocumentChunk(
        document_id="doc",
        chunk_id="doc:page:1",
        page=1,
        text="截至3月31日止三個月\n2024年\n人民幣千元\n現金流量表所述現金及現金等價物\n77,208",
    )
    item = Evidence(
        evidence_id="evidence-1",
        document_id="doc",
        chunk_id=source.chunk_id,
        page=1,
        text=source.text,
    )
    result = FinancialEvidenceExtractor().extract([item], [], {source.chunk_id: source})

    assert isinstance(result, FinancialExtractionResult)
    assert isinstance(result.cash_and_cash_equivalents, FinancialMetricValue)
    assert result.cash_and_cash_equivalents.normalized_value == Decimal("77208")


def test_result_round_trips_through_pydantic_json_contract() -> None:
    original = FinancialExtractionResult(
        cash_and_cash_equivalents=FinancialMetricValue(
            metric_name="cash_and_cash_equivalents",
            normalized_value=Decimal("77208"),
            status=ExtractionStatus.EXTRACTED,
            extraction_method="page_text_rule",
        ),
        operating_cash_flow=FinancialMetricValue(
            metric_name="operating_cash_flow",
            status=ExtractionStatus.NOT_FOUND,
        ),
    )
    payload = original.model_dump_json()
    restored = TypeAdapter(FinancialExtractionResult).validate_json(payload)
    assert restored == original
    assert restored.cash_and_cash_equivalents.extraction_method == "page_text_rule"


def test_list_and_dict_defaults_are_not_shared() -> None:
    first = FinancialMetricValue(metric_name="cash")
    second = FinancialMetricValue(metric_name="cash")
    first.issues.append("x")
    first.metadata["x"] = 1
    assert second.issues == []
    assert second.metadata == {}


def test_extraction_is_deterministic_for_identical_inputs() -> None:
    source = DocumentChunk(
        document_id="doc",
        chunk_id="doc:page:1",
        page=1,
        text="截至12月31日止年度\n2023年\n人民幣千元\n經營活動所用淨現金流量\n(100)",
    )
    item = Evidence(
        evidence_id="stable-evidence",
        document_id="doc",
        chunk_id=source.chunk_id,
        page=1,
        text=source.text,
    )
    extractor = FinancialEvidenceExtractor()
    first = extractor.extract([], [item], {source.chunk_id: source})
    second = extractor.extract([], [item], {source.chunk_id: source})
    assert first == second


def test_extractor_does_not_mutate_evidence_or_chunks() -> None:
    source = DocumentChunk(
        document_id="doc",
        chunk_id="doc:page:1",
        page=1,
        text="截至12月31日止年度\n2023年\n人民幣千元\n現金流量表所述現金及現金等價物\n100",
    )
    item = Evidence(document_id="doc", chunk_id=source.chunk_id, page=1, text=source.text)
    source_before = source.model_dump()
    item_before = item.model_dump()
    FinancialEvidenceExtractor().extract([item], [], {source.chunk_id: source})
    assert source.model_dump() == source_before
    assert item.model_dump() == item_before
