"""Synthetic tests for parser-only Expert Evidence preservation metrics."""

from __future__ import annotations

import inspect

from ipo_risk.evaluation.expert_annotation import ExpertAnnotationBundle
from ipo_risk.evaluation import parser_preservation as preservation
from ipo_risk.evaluation.parser_preservation import (
    EvidenceAuditStatus,
    FailureCode,
    StructureRecoverability,
    audit_evidence,
    extract_critical_numeric_tokens,
    extract_numeric_tokens,
    normalize_text,
    summarize_records,
)
from ipo_risk.schemas import DocumentChunk


def _bundle(*, text: str, page: int = 10, requirement: str = "required", authority: str = "accountants_report", risk_code: str = "cash_runway") -> ExpertAnnotationBundle:
    risks = []
    for code in (
        "cash_runway", "continuous_loss", "revenue_growth", "customer_concentration",
        "supplier_concentration", "redemption_rights", "material_litigation_compliance",
        "precommercial_product",
    ):
        applicable = code == risk_code
        risks.append({
            "annotation_version": "gpt_expert_v1.1",
            "case_id": "synthetic_case",
            "stock_code": "0000.HK",
            "company_name": "Synthetic",
            "document_id": "synthetic_case",
            "risk_code": code,
            "applicable": applicable,
            "expected_status": "needs_review" if applicable else "rejected",
            "expected_level": "medium" if applicable else "not_applicable",
            "confidence": 0.8,
            "reasoning": "Synthetic preservation fixture.",
            "calculation_required": False,
            "calculation_method": None,
            "calculation_inputs": None,
            "calculation_result": None,
            "review_outcome": "expert_first_pass",
            "annotator_type": "external_gpt_expert",
        })
    return ExpertAnnotationBundle.model_validate({
        "annotation_version": "gpt_expert_v1.1",
        "case_id": "synthetic_case",
        "stock_code": "0000.HK",
        "company_name": "Synthetic",
        "document_id": "synthetic_case",
        "risks": risks,
        "evidence": [{
            "case_id": "synthetic_case",
            "risk_code": risk_code,
            "page": page,
            "evidence_role": "primary",
            "requirement": requirement,
            "source_authority": authority,
            "exact_text": text,
            "evidence_reason": "Synthetic preservation relationship.",
            "confidence": 0.9,
        }],
        "metadata": {},
    })


def _chunk(text: str, page: int = 10) -> DocumentChunk:
    return DocumentChunk(
        document_id="synthetic_case",
        chunk_id=f"synthetic_case:page:{page}",
        page=page,
        text=text,
    )


def test_whitespace_normalized_chinese_matches() -> None:
    bundle = _bundle(text="現 金 及 現 金 等 價 物 9,529")
    record = audit_evidence(bundle, [_chunk("現金及現金等價物\n9,529")])[0]
    assert normalize_text("現 金") != normalize_text("現金")
    assert record.normalized_text_match.value == "exact"
    assert record.final_status is EvidenceAuditStatus.PASS


def test_numeric_normalization_and_negative_semantics() -> None:
    assert extract_numeric_tokens("58,342 and 58342") == ["58342", "58342"]
    assert extract_numeric_tokens("(58,342)") == ["-58342"]
    assert extract_numeric_tokens("58,342") == ["58342"]
    assert extract_numeric_tokens("附註24) (1,318)") == ["24", "-1318"]


def test_critical_numeric_tokens_exclude_years_note_numbers_and_plain_small_counts() -> None:
    text = "2019 附註24 逾15年 58,342 45.7 100% (357)"
    assert extract_critical_numeric_tokens(text) == ["58342", "45.7", "100%", "-357"]


def test_missing_page_is_parser_failure() -> None:
    record = audit_evidence(_bundle(text="cash 9,529"), [])[0]
    assert record.final_status is EvidenceAuditStatus.FAIL
    assert record.failure_codes == [FailureCode.PARSER_PAGE_MISSING]


def test_diagram_text_present_but_relationship_lost_is_partial() -> None:
    text = "Owner 100% Holding 100% Issuer 100% Subsidiary"
    record = audit_evidence(
        _bundle(text=text, authority="corporate_structure", risk_code="redemption_rights"),
        [_chunk(text)],
    )[0]
    assert record.structure_recoverability is StructureRecoverability.PARTIALLY_RECOVERABLE
    assert record.final_status is EvidenceAuditStatus.PARTIAL
    assert FailureCode.DIAGRAM_RELATIONSHIP_LOST in record.failure_codes


def test_table_numbers_present_with_reading_order_change_is_partial() -> None:
    bundle = _bundle(
        text="客戶甲 402,087 45.7% 客戶乙 100 10%",
        authority="business_section",
        risk_code="customer_concentration",
    )
    record = audit_evidence(bundle, [_chunk("客戶甲 客戶乙 402087 45.7% 100 10%")])[0]
    assert record.numeric_preservation_rate == 1.0
    assert record.structure_recoverability is StructureRecoverability.PARTIALLY_RECOVERABLE
    assert FailureCode.TABLE_STRUCTURE_PARTIAL in record.failure_codes


def test_required_and_supporting_metrics_are_separate() -> None:
    required = audit_evidence(_bundle(text="cash 9,529"), [_chunk("cash 9,529")])[0]
    supporting = audit_evidence(
        _bundle(text="Owner 100% Holding 100% Issuer 100% Subsidiary", requirement="supporting_only", authority="corporate_structure", risk_code="redemption_rights"),
        [_chunk("Owner 100% Holding 100% Issuer 100% Subsidiary")],
    )[0]
    summary = summarize_records([required, supporting])
    assert summary.required_evidence == 1
    assert summary.required_evidence_preservation_rate == 1.0
    assert summary.required_pass_or_partial_rate == 1.0


def test_audit_module_does_not_import_or_call_retriever() -> None:
    source = inspect.getsource(preservation)
    assert "ipo_risk.retrieval" not in source
    assert "DocumentRetriever" not in source
