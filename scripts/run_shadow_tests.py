"""Run the v0.2 Parser/Retriever shadow test against selected ZIP entries."""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile, ZipFile

import fitz

from ipo_risk.parsers.pymupdf_parser import DocumentParseError, PyMuPDFDocumentParser
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.schemas import DocumentParseRequest, Evidence


YEAR_QUOTAS = {2020: 5, 2021: 5, 2022: 5, 2023: 4, 2024: 5}
QUERIES = {
    "cash": "现金流量表期末现金及现金等价物",
    "operating_cash_flow": "经营活动现金流",
}
PARSER_FIELDS = (
    "case_id", "source_year", "stock_code_wind", "company_short_name", "manual_review", "parser_status",
    "failure_code", "failure_message", "pdf_page_count", "nonblank_page_count", "parser_error_count",
    "empty_text_ratio", "average_text_chars", "low_text_density", "suspected_scan",
)
RETRIEVER_FIELDS = (
    "case_id", "source_year", "stock_code_wind", "company_short_name", "manual_review", "parser_status",
    "failure_code", "failure_message", "cash_top5_pages", "cash_top5_scores", "cash_top5_texts",
    "cash_result_count", "cash_negative_context_count", "operating_cash_flow_top5_pages",
    "operating_cash_flow_top5_scores", "operating_cash_flow_top5_texts", "operating_cash_flow_result_count",
    "operating_cash_flow_negative_context_count",
)


@dataclass(frozen=True)
class ShadowCase:
    """One immutable, traceable prospectus selection."""

    case_id: str
    source_year: int
    archive_filename: str
    source_filename: str
    stock_code_raw: str
    stock_code_wind: str
    company_short_name: str
    offering_type: str
    selection_tags: str
    manual_review: bool


def load_selection(path: Path) -> list[ShadowCase]:
    """Load and validate the fixed 24-case development selection."""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    cases = [
        ShadowCase(
            case_id=row["case_id"],
            source_year=int(row["source_year"]),
            archive_filename=row["archive_filename"],
            source_filename=row["source_filename"],
            stock_code_raw=row["stock_code_raw"],
            stock_code_wind=row["stock_code_wind"],
            company_short_name=row["company_short_name"],
            offering_type=row["offering_type"],
            selection_tags=row["selection_tags"],
            manual_review=row["manual_review"].strip().lower() == "true",
        )
        for row in rows
    ]
    validate_selection(cases)
    return cases


def validate_selection(cases: list[ShadowCase]) -> None:
    """Enforce quotas, uniqueness, manual-review count, and blind-set isolation."""
    if len(cases) != 24:
        raise ValueError(f"shadow selection must contain 24 cases, got {len(cases)}")
    if len({case.case_id for case in cases}) != len(cases):
        raise ValueError("case_id values must be unique")
    if len({(case.archive_filename, case.source_filename) for case in cases}) != len(cases):
        raise ValueError("archive/source pairs must be unique")
    if any(case.source_year == 2025 or case.archive_filename.startswith("2025_") for case in cases):
        raise ValueError("2025 blind-test cases are forbidden")
    actual_quotas = Counter(case.source_year for case in cases)
    if actual_quotas != Counter(YEAR_QUOTAS):
        raise ValueError(f"year quotas must be {YEAR_QUOTAS}, got {dict(actual_quotas)}")
    if sum(case.manual_review for case in cases) != 12:
        raise ValueError("exactly 12 cases must be flagged for manual review")
    if any(case.stock_code_raw == "02410" for case in cases):
        raise ValueError("2410.HK is the development case and cannot enter the shadow sample")
    if sum("low_text_density" in case.selection_tags.split("|") for case in cases) < 2:
        raise ValueError("at least two low-text-density cases are required")


def _serialize_evidence(items: list[Evidence]) -> tuple[str, str, str]:
    pages = "|".join(str(item.page) for item in items)
    scores = "|".join(f"{item.relevance_score:.4f}" for item in items)
    texts = " || ".join(item.text.replace("\r", " ").replace("\n", " ") for item in items)
    return pages, scores, texts


def _extract_case(data_root: Path, case: ShadowCase, destination: Path) -> None:
    archive_path = data_root / case.archive_filename
    if not archive_path.is_file():
        raise FileNotFoundError(f"archive not found: {case.archive_filename}")
    with ZipFile(archive_path) as archive:
        try:
            info = archive.getinfo(case.source_filename)
        except KeyError as exc:
            raise FileNotFoundError(
                f"PDF entry not found in {case.archive_filename}: {case.source_filename}"
            ) from exc
        with archive.open(info) as source, destination.open("wb") as target:
            shutil.copyfileobj(source, target, length=1024 * 1024)


def run_case(data_root: Path, case: ShadowCase, temp_dir: Path) -> dict[str, object]:
    """Run one case without allowing its failure to terminate the batch."""
    result: dict[str, object] = {
        "case_id": case.case_id,
        "source_year": case.source_year,
        "stock_code_wind": case.stock_code_wind,
        "company_short_name": case.company_short_name,
        "manual_review": case.manual_review,
        "parser_status": "failed",
        "failure_code": "",
        "failure_message": "",
        "pdf_page_count": 0,
        "nonblank_page_count": 0,
        "parser_error_count": 0,
        "empty_text_ratio": 1.0,
        "average_text_chars": 0.0,
        "low_text_density": False,
        "suspected_scan": False,
    }
    pdf_path = temp_dir / f"{case.case_id}.pdf"
    try:
        _extract_case(data_root, case, pdf_path)
        with fitz.open(pdf_path) as document:
            result["pdf_page_count"] = document.page_count
        parser = PyMuPDFDocumentParser()
        chunks = parser.parse(DocumentParseRequest(document_id=case.case_id, prospectus_path=str(pdf_path)))
        page_count = int(result["pdf_page_count"])
        empty_ratio = (page_count - len(chunks)) / page_count if page_count else 1.0
        average_text_chars = sum(len(chunk.text) for chunk in chunks) / len(chunks) if chunks else 0.0
        result.update(
            parser_status="completed" if not parser.last_errors else "partial",
            failure_code="P-05" if parser.last_errors else "",
            failure_message="individual page parse failures" if parser.last_errors else "",
            nonblank_page_count=len(chunks),
            parser_error_count=len(parser.last_errors),
            empty_text_ratio=round(empty_ratio, 6),
            average_text_chars=round(average_text_chars, 2),
            low_text_density=average_text_chars < 800,
            suspected_scan=empty_ratio >= 0.8,
        )
        retriever = KeywordDocumentRetriever()
        for prefix, query in QUERIES.items():
            evidence = retriever.retrieve(chunks, query, limit=5)
            pages, scores, texts = _serialize_evidence(evidence)
            result[f"{prefix}_top5_pages"] = pages
            result[f"{prefix}_top5_scores"] = scores
            result[f"{prefix}_top5_texts"] = texts
            result[f"{prefix}_result_count"] = len(evidence)
            result[f"{prefix}_negative_context_count"] = sum(
                bool(item.metadata.get("negative_context")) for item in evidence
            )
    except DocumentParseError as exc:
        result["failure_code"] = "P-02" if exc.error.code == "empty_pdf" else "P-01"
        result["failure_message"] = f"{exc.error.code}: {exc.error.message}"
    except (BadZipFile, FileNotFoundError, OSError) as exc:
        result["failure_code"] = "P-01"
        result["failure_message"] = str(exc)
    except Exception as exc:  # batch boundary: preserve the other 23 cases
        result["failure_code"] = "P-01"
        result["failure_message"] = f"{type(exc).__name__}: {exc}"
    finally:
        if pdf_path.exists():
            pdf_path.unlink()
    return result


def run_batch(data_root: Path, cases: list[ShadowCase]) -> list[dict[str, object]]:
    """Run all selected cases with per-case isolation."""
    with tempfile.TemporaryDirectory(prefix="ipo-risk-shadow-") as directory:
        temp_dir = Path(directory)
        return [run_case(data_root, case, temp_dir) for case in cases]


def write_results(path: Path, rows: list[dict[str, object]], fieldnames: tuple[str, ...]) -> None:
    """Write deterministic UTF-8 CSV output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fieldnames} for row in rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--selection",
        type=Path,
        default=Path("data/catalog/shadow_sample_24.csv"),
    )
    parser.add_argument(
        "--parser-output",
        type=Path,
        default=Path("reports/v0.2_shadow_parser_results.csv"),
    )
    parser.add_argument(
        "--retriever-output",
        type=Path,
        default=Path("reports/v0.2_shadow_retriever_results.csv"),
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=(Path(value) if (value := os.environ.get("IPO_RISK_COMPETITION_DATA_ROOT")) else None),
    )
    args = parser.parse_args()
    if args.data_root is None or not args.data_root.is_dir():
        parser.error("set IPO_RISK_COMPETITION_DATA_ROOT or pass --data-root")
    cases = load_selection(args.selection)
    rows = run_batch(args.data_root, cases)
    write_results(args.parser_output, rows, PARSER_FIELDS)
    write_results(args.retriever_output, rows, RETRIEVER_FIELDS)
    completed = sum(row["parser_status"] in {"completed", "partial"} for row in rows)
    failed = len(rows) - completed
    print(
        f"shadow_cases={len(rows)} completed={completed} failed={failed} "
        f"parser_output={args.parser_output} retriever_output={args.retriever_output}"
    )
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
