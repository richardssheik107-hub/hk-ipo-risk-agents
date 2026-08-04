"""Pure presentation helpers for Streamlit and UI tests."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterator

from ipo_risk.schemas import IPOAnalysisRequest, IPOAnalysisResult


MAX_PDF_UPLOAD_BYTES = 200 * 1024 * 1024


def validate_pdf_upload(filename: str, content: bytes) -> None:
    """Reject empty, oversized, mislabelled, or non-PDF uploads."""

    if Path(filename).suffix.lower() != ".pdf":
        raise ValueError("Only .pdf files are accepted.")
    if not content:
        raise ValueError("The uploaded PDF is empty.")
    if len(content) > MAX_PDF_UPLOAD_BYTES:
        raise ValueError("The uploaded PDF exceeds the 200 MB size limit.")
    if not content.startswith(b"%PDF-"):
        raise ValueError("The uploaded file does not have a valid PDF header.")


@contextmanager
def temporary_pdf(content: bytes) -> Iterator[str]:
    """Write bytes to a random temporary PDF and always remove it afterward."""

    path: Path | None = None
    try:
        with NamedTemporaryFile(prefix="ipo-risk-", suffix=".pdf", delete=False) as handle:
            handle.write(content)
            path = Path(handle.name)
        yield str(path)
    finally:
        if path is not None:
            path.unlink(missing_ok=True)


def build_analysis_request(
    *,
    company_name: str,
    stock_code: str,
    listing_date: date | None,
    prospectus_path: str,
    use_mock: bool,
) -> IPOAnalysisRequest:
    """Build the only request object the UI sends to the service boundary."""

    return IPOAnalysisRequest(
        company_name=company_name,
        stock_code=stock_code,
        listing_date=listing_date,
        prospectus_path=prospectus_path,
        use_mock=use_mock,
    )


def result_payload(result: IPOAnalysisResult) -> dict[str, object]:
    """Serialize service output without deriving financial values or risk states."""

    return {
        "status": result.status.value,
        "component_modes": result.metadata.get("component_modes", {}),
        "document": result.metadata.get("document", {}),
        "real_slice": result.metadata.get("real_slice", {}),
        "verified_risks": [item.model_dump(mode="json") for item in result.verified_risks],
        "pending_risks": [item.model_dump(mode="json") for item in result.pending_risks],
        "rejected_risks": [item.model_dump(mode="json") for item in result.rejected_risks],
        "prediction": (
            result.prediction.model_dump(mode="json") if result.prediction else None
        ),
        "report_sections": [
            item.model_dump(mode="json") for item in result.report_sections
        ],
        "errors": [item.model_dump(mode="json") for item in result.errors],
        "agent_logs": [item.model_dump(mode="json") for item in result.agent_logs],
    }
