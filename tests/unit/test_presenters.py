from datetime import date
import importlib.util
import json
from pathlib import Path

import pytest

from ipo_risk.schemas import (
    AnalysisError,
    Evidence,
    IPOAnalysisResult,
    PredictionResult,
    ReportSection,
    RiskCategory,
    RiskItem,
    RiskLevel,
    TaskStatus,
    VerificationStatus,
)


_SPEC = importlib.util.spec_from_file_location("presenters", Path("app/presenters.py"))
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
build_analysis_request = _MODULE.build_analysis_request
markdown_report = _MODULE.markdown_report
profile_payload = _MODULE.profile_payload
result_payload = _MODULE.result_payload
risk_status_counts = _MODULE.risk_status_counts
safe_download_stem = _MODULE.safe_download_stem
temporary_pdf = _MODULE.temporary_pdf
validate_pdf_upload = _MODULE.validate_pdf_upload


@pytest.mark.parametrize("filename", ["case.txt", "case.docx", "case"])
def test_non_pdf_extension_is_rejected(filename: str) -> None:
    with pytest.raises(ValueError, match=".pdf"):
        validate_pdf_upload(filename, b"%PDF-1.7")


def test_empty_and_invalid_pdf_content_are_rejected() -> None:
    with pytest.raises(ValueError, match="empty"):
        validate_pdf_upload("case.pdf", b"")
    with pytest.raises(ValueError, match="header"):
        validate_pdf_upload("case.pdf", b"not a pdf")


def test_oversized_pdf_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_MODULE, "MAX_PDF_UPLOAD_BYTES", 8)
    with pytest.raises(ValueError, match="200 MB"):
        validate_pdf_upload("case.pdf", b"%PDF-1.7\n")


@pytest.mark.parametrize("filename", ["招股书.pdf", "folder/case.PDF", r"C:\fake\case.pdf"])
def test_pdf_validation_is_filename_and_platform_compatible(filename: str) -> None:
    validate_pdf_upload(filename, b"%PDF-1.7\n")


def test_temporary_pdf_is_deleted_after_success_and_failure() -> None:
    with temporary_pdf(b"%PDF-1.7") as name:
        path = Path(name)
        assert path.exists()
        assert path.read_bytes() == b"%PDF-1.7"
    assert not path.exists()

    with pytest.raises(RuntimeError):
        with temporary_pdf(b"%PDF-1.7") as name:
            failed_path = Path(name)
            raise RuntimeError("boom")
    assert not failed_path.exists()


def test_presenter_only_serializes_service_result() -> None:
    request = build_analysis_request(
        company_name="Demo",
        stock_code="2410.HK",
        listing_date=date(2024, 8, 20),
        prospectus_path="temporary.pdf",
        use_mock=False,
    )
    assert request.company_name == "Demo"
    assert request.use_mock is False
    result = IPOAnalysisResult(
        request_id=request.request_id,
        company_name=request.company_name,
        stock_code=request.stock_code,
        workflow_version="mvp_v1",
        metadata={"component_modes": {"parser": "real"}},
    )
    payload = result_payload(result)
    assert payload["component_modes"] == {"parser": "real"}
    assert payload["prediction"] is None
    assert payload["profile"]["company_name"] == "Demo"
    json.dumps(payload)


def _risk(status: VerificationStatus) -> RiskItem:
    return RiskItem(
        risk_code="precommercial_product",
        category=RiskCategory.BUSINESS,
        risk_type="precommercial_product",
        level=RiskLevel.MEDIUM,
        score=60,
        conclusion="Core product has not reached commercialization.",
        evidence=[
            Evidence(
                evidence_id="ev-business",
                document_id="doc",
                chunk_id="chunk-17",
                page=17,
                text="The core product has not commenced commercial sales.",
            )
        ],
        agent_name="business",
        verification_status=status,
        verification_notes="Evidence contract checked.",
    )


def test_product_payload_exposes_profile_counts_domains_and_component_failures() -> None:
    verified = _risk(VerificationStatus.VERIFIED)
    pending = _risk(VerificationStatus.NEEDS_REVIEW).model_copy(
        update={"risk_id": "pending-risk"}
    )
    result = IPOAnalysisResult(
        request_id="request",
        company_name="Example Biotech",
        stock_code="1167.HK",
        workflow_version="enhanced_v2",
        status=TaskStatus.PARTIAL,
        verified_risks=[verified],
        pending_risks=[pending],
        prediction=PredictionResult(
            model_name="rule_based",
            risk_score=60,
            risk_level=RiskLevel.MEDIUM,
        ),
        errors=[
            AnalysisError(
                stage="predictor",
                component="predictor",
                code="component_failure",
                message="predictor failed",
            )
        ],
        metadata={
            "ipo_profile": {
                "company_name": "Example Biotech",
                "stock_code": "1167.HK",
                "industry": "Biotechnology",
                "metadata": {
                    "source": "catalog",
                    "official_match_status": "matched",
                    "special_security": {"security_category": "reit_units"},
                },
            },
            "component_modes": {"predictor": "rule_based", "business": "v03"},
        },
    )

    payload = result_payload(result)

    assert profile_payload(result)["source"] == "catalog"
    assert profile_payload(result)["match_status"] == "matched"
    assert profile_payload(result)["security_category"] == "reit_units"
    assert risk_status_counts(result) == {
        "verified": 1,
        "needs_review": 1,
        "pending": 0,
        "rejected": 0,
    }
    assert payload["domains"]["business"]["risk_count"] == 2
    assert next(
        row for row in payload["component_statuses"] if row["component"] == "predictor"
    )["status"] == "failed"
    json.dumps(payload)


def test_markdown_report_preserves_evidence_verifier_and_section_metadata() -> None:
    risk = _risk(VerificationStatus.VERIFIED)
    result = IPOAnalysisResult(
        request_id="request",
        company_name="Example Biotech",
        stock_code="1167.HK",
        workflow_version="enhanced_v2",
        verified_risks=[risk],
        report_sections=[
            ReportSection(
                order=5,
                title="Business Risks",
                summary="One verified item.",
                risks=[risk],
                metadata={"audit": "preserved"},
            )
        ],
    )

    report = markdown_report(result)

    assert "PDF page 17" in report
    assert "Evidence contract checked" in report
    assert "Structured section metadata" in report
    assert '"audit": "preserved"' in report


@pytest.mark.parametrize(
    ("stock_code", "expected"),
    [("2410.HK", "2410.HK"), (" 02410 / HK ", "02410-HK"), ("", "ipo")],
)
def test_safe_download_stem(stock_code: str, expected: str) -> None:
    assert safe_download_stem(stock_code) == expected
