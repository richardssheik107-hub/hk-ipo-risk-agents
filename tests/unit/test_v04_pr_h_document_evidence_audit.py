from __future__ import annotations

from pathlib import Path

import fitz

from ipo_risk.schemas import (
    AgentLog,
    Calculation,
    Evidence,
    IPOAnalysisResult,
    LogStatus,
    ReportSection,
    RiskCategory,
    RiskItem,
    RiskLevel,
    TaskStatus,
    VerificationStatus,
)
from scripts.audit_v04_pr_h_document_evidence import (
    audit_case,
    build_report,
    determinism_signature,
)


CASE_ID = "ipo_2024_02410"
STOCK_CODE = "2410.HK"
EVIDENCE_TEXT = "The company recorded constrained cash resources before listing."


def _pdf(path: Path) -> Path:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), EVIDENCE_TEXT)
    document.save(path)
    document.close()
    return path


def _result(
    *,
    evidence: Evidence | None = None,
    calculation_ids: list[str] | None = None,
    index_entries: list[dict] | None = None,
    final_evidence_ids: list[str] | None = None,
    final_risk_ids: list[str] | None = None,
    case_id: str = CASE_ID,
    stock_code: str = STOCK_CODE,
    verification_notes: str = "Evidence and score passed deterministic checks.",
    agent_logs: bool = True,
    extra_metadata: dict | None = None,
) -> IPOAnalysisResult:
    evidence = evidence or Evidence(
        evidence_id="e-1",
        document_id="req-1",
        chunk_id="req-1:page:1",
        page=1,
        text=EVIDENCE_TEXT,
        bbox=(60.0, 50.0, 500.0, 90.0),
        metadata={"risk_code": "cash_runway", "case_id": case_id, "stock_code": stock_code},
    )
    risk = RiskItem(
        risk_id="r-1",
        risk_code="cash_runway",
        category=RiskCategory.FINANCIAL,
        risk_type="Cash runway",
        level=RiskLevel.HIGH,
        score=80,
        conclusion="Cash resources are constrained.",
        evidence=[evidence],
        calculation=Calculation(
            skill_name="cash_runway",
            formula="cash / burn",
            result=6,
            unit="months",
            evidence_ids=calculation_ids if calculation_ids is not None else [evidence.evidence_id],
        ),
        agent_name="financial",
        verification_status=VerificationStatus.VERIFIED,
        verification_notes=verification_notes,
    )
    entries = index_entries if index_entries is not None else [
        {
            "evidence_id": evidence.evidence_id,
            "page": evidence.page,
            "section": evidence.section,
            "risk_code": risk.risk_code,
            "text": evidence.text,
            "source_type": evidence.source_type.value,
        }
    ]
    final = {
        "summary": "Document supervision passed through.",
        "referenced_risk_ids": final_risk_ids if final_risk_ids is not None else [risk.risk_id],
        "referenced_evidence_ids": (
            final_evidence_ids if final_evidence_ids is not None else [evidence.evidence_id]
        ),
        "composite_findings": [],
        "conflicts": [],
        "metadata": {"creates_no_new_risk": True},
    }
    metadata = {
        "component_modes": {"parser": "real", "final_supervisor": "v04"},
        "configuration": {"use_mock": False},
        "market_context": {"provenance": {"case_id": case_id}},
        "final_supervision": final,
    }
    metadata.update(extra_metadata or {})
    logs = [
        AgentLog(
            task_id="req-1",
            step=1,
            agent_name="financial",
            action="analyze",
            status=LogStatus.SUCCESS,
            evidence_ids=[evidence.evidence_id],
        )
    ] if agent_logs else []
    return IPOAnalysisResult(
        analysis_id="a-1",
        request_id="req-1",
        company_name="Governed Case",
        stock_code=stock_code,
        workflow_version="enhanced_v2",
        verified_risks=[risk],
        agent_logs=logs,
        report_sections=[
            ReportSection(
                section_id="body",
                title="Financial Risks",
                summary="One governed risk.",
                evidence_ids=[evidence.evidence_id],
                risks=[risk],
            ),
            ReportSection(
                section_id="index",
                title="Evidence Index",
                summary="One Evidence reference.",
                evidence_ids=[evidence.evidence_id],
                metadata={"entries": entries},
            ),
        ],
        status=TaskStatus.COMPLETED,
        metadata=metadata,
    )


def _audit(result: IPOAnalysisResult | None, pdf: Path, **kwargs) -> dict:
    return audit_case(
        result,
        case_id=CASE_ID,
        stock_code=STOCK_CODE,
        pdf_path=pdf,
        comparison=result,
        **kwargs,
    )


def test_valid_trace_is_complete_and_deterministic(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path / "case.pdf")
    result = _result()
    audited = _audit(result, pdf)
    assert audited["overall_status"] == "PASS"
    assert audited["physical_page_passed"] == "PASS"
    assert audited["evidence_text_status"] == "PASS"
    assert audited["bbox_status"] == "PASS"
    assert audited["calculation_linkage"] == "PASS"
    assert audited["evidence_index_status"] == "PASS"
    assert audited["determinism_status"] == "PASS"
    assert determinism_signature(result) == determinism_signature(result.model_copy(deep=True))


def test_case_identity_mismatch_fails(tmp_path: Path) -> None:
    result = _result(case_id="ipo_2024_other")
    assert _audit(result, _pdf(tmp_path / "case.pdf"))["overall_status"] == "FAIL"


def test_dangling_evidence_reference_fails(tmp_path: Path) -> None:
    result = _result(final_evidence_ids=["missing"])
    audit = _audit(result, _pdf(tmp_path / "case.pdf"))
    assert audit["evidence_index"]["final_supervisor_invented_evidence_ids"] == ["missing"]


def test_duplicate_evidence_id_fails(tmp_path: Path) -> None:
    result = _result()
    second = result.verified_risks[0].model_copy(
        deep=True,
        update={"risk_id": "r-2", "risk_code": "continuous_loss"},
    )
    result = result.model_copy(update={"verified_risks": [*result.verified_risks, second]})
    audit = _audit(result, _pdf(tmp_path / "case.pdf"))
    assert audit["evidence"]["duplicate_evidence_ids"] == ["e-1"]
    assert audit["overall_status"] == "FAIL"


def test_cross_case_evidence_reference_fails(tmp_path: Path) -> None:
    evidence = _result().verified_risks[0].evidence[0].model_copy(
        update={"metadata": {"case_id": "ipo_2024_other", "stock_code": STOCK_CODE}}
    )
    audit = _audit(_result(evidence=evidence), _pdf(tmp_path / "case.pdf"))
    assert audit["cross_case_evidence_ids"] == ["e-1"]


def test_invalid_physical_page_fails(tmp_path: Path) -> None:
    evidence = _result().verified_risks[0].evidence[0].model_copy(update={"page": 2})
    audit = _audit(_result(evidence=evidence), _pdf(tmp_path / "case.pdf"))
    assert audit["physical_page_passed"] == "FAIL"


def test_invalid_bbox_fails(tmp_path: Path) -> None:
    evidence = _result().verified_risks[0].evidence[0].model_copy(
        update={"bbox": (500.0, 50.0, 60.0, 90.0)}
    )
    audit = _audit(_result(evidence=evidence), _pdf(tmp_path / "case.pdf"))
    assert audit["bbox_status"] == "FAIL"


def test_calculation_missing_evidence_fails(tmp_path: Path) -> None:
    audit = _audit(_result(calculation_ids=["missing"]), _pdf(tmp_path / "case.pdf"))
    assert audit["calculation_linkage"] == "FAIL"


def test_evidence_risk_code_mismatch_fails(tmp_path: Path) -> None:
    evidence = _result().verified_risks[0].evidence[0].model_copy(
        update={"metadata": {"risk_code": "continuous_loss", "case_id": CASE_ID}}
    )
    audit = _audit(_result(evidence=evidence), _pdf(tmp_path / "case.pdf"))
    assert audit["evidence"]["risk_code_mismatch_evidence_ids"] == ["e-1"]


def test_evidence_index_missing_entry_fails(tmp_path: Path) -> None:
    audit = _audit(_result(index_entries=[]), _pdf(tmp_path / "case.pdf"))
    assert audit["evidence_index"]["missing_index_evidence_ids"] == ["e-1"]


def test_evidence_index_orphan_entry_fails(tmp_path: Path) -> None:
    entries = [
        {
            "evidence_id": "orphan",
            "page": 1,
            "risk_code": "cash_runway",
            "text": EVIDENCE_TEXT,
        }
    ]
    audit = _audit(_result(index_entries=entries), _pdf(tmp_path / "case.pdf"))
    assert audit["evidence_index"]["orphan_index_evidence_ids"] == ["orphan"]


def test_final_supervisor_invented_evidence_fails(tmp_path: Path) -> None:
    audit = _audit(_result(final_evidence_ids=["e-1", "invented"]), _pdf(tmp_path / "case.pdf"))
    assert audit["evidence_index"]["final_supervisor_invented_evidence_ids"] == ["invented"]


def test_gold_oracle_leakage_key_fails(tmp_path: Path) -> None:
    audit = _audit(
        _result(extra_metadata={"oracle": {"gold": "not inspected"}}),
        _pdf(tmp_path / "case.pdf"),
    )
    assert audit["leakage_status"] == "FAIL"
    assert audit["forbidden_metadata_paths"] == ["metadata.oracle", "metadata.oracle.gold"]


def test_missing_optional_provenance_is_partial(tmp_path: Path) -> None:
    audit = _audit(
        _result(verification_notes="", agent_logs=False),
        _pdf(tmp_path / "case.pdf"),
    )
    assert audit["verifier_provenance"] == "PARTIAL"
    assert audit["agent_provenance"] == "PARTIAL"
    assert audit["overall_status"] == "PARTIAL"


def test_empty_runtime_is_blocked() -> None:
    case = audit_case(None, case_id=CASE_ID, stock_code=STOCK_CODE)
    report = build_report([case])
    assert case["overall_status"] == "BLOCKED_INPUT_MISSING"
    assert report["result"] == "BLOCKED"


def test_audit_creates_no_temporary_files(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path / "case.pdf")
    before = sorted(path.name for path in tmp_path.iterdir())
    _audit(_result(), pdf)
    after = sorted(path.name for path in tmp_path.iterdir())
    assert after == before
