from datetime import date
import importlib.util
from pathlib import Path

import pytest

from ipo_risk.schemas import IPOAnalysisResult


_SPEC = importlib.util.spec_from_file_location("presenters", Path("app/presenters.py"))
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
build_analysis_request = _MODULE.build_analysis_request
result_payload = _MODULE.result_payload
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


@pytest.mark.parametrize("filename", ["招股書.pdf", "folder/case.PDF", r"C:\fake\case.pdf"])
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
