"""Safely check V3-3B Business Retriever recall on local development PDFs."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
import sys

from ipo_risk.parsers.pymupdf_parser import DocumentParseError, PyMuPDFDocumentParser
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.schemas import DocumentParseRequest


@dataclass(frozen=True)
class _Case:
    stock_code: str
    pdf_path: str | None
    expected_pages: dict[str, frozenset[int]]


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pdf-1167",
        default=os.getenv("IPO_RISK_V33B_1167_PDF"),
        help="Local 1167.HK development-set PDF (or IPO_RISK_V33B_1167_PDF).",
    )
    parser.add_argument(
        "--pdf-9633",
        default=os.getenv("IPO_RISK_V33B_9633_PDF"),
        help="Local 9633.HK development-set PDF (or IPO_RISK_V33B_9633_PDF).",
    )
    return parser.parse_args()


def _run_case(case: _Case) -> bool | None:
    if not case.pdf_path:
        print(f"stock_code={case.stock_code} status=NOT_TESTED reason=pdf_not_configured")
        return None

    path = Path(case.pdf_path)
    if not path.is_file() or path.suffix.lower() != ".pdf":
        print(f"stock_code={case.stock_code} status=FAIL reason=invalid_pdf")
        return False

    parser = PyMuPDFDocumentParser()
    try:
        chunks = parser.parse(
            DocumentParseRequest(
                document_id=f"v33b-{case.stock_code}",
                prospectus_path=str(path),
            )
        )
    except DocumentParseError as exc:
        print(
            f"stock_code={case.stock_code} status=FAIL "
            f"reason=parser_error code={exc.error.code}"
        )
        return False

    print(
        f"stock_code={case.stock_code} parsed_chunks={len(chunks)} "
        f"parser_errors={len(parser.last_errors)}"
    )
    retriever = KeywordDocumentRetriever()
    passed = True
    for family, expected_pages in case.expected_pages.items():
        evidence = retriever.retrieve(chunks, family, limit=5)
        pages = [item.page for item in evidence]
        evidence_ids = [item.evidence_id for item in evidence]
        hit = any(page in expected_pages for page in pages)
        passed = passed and hit
        print(
            f"stock_code={case.stock_code} query_family={family} "
            f"ranked_pages={pages} evidence_ids={evidence_ids} hit={str(hit).lower()}"
        )
    print(f"stock_code={case.stock_code} status={'PASS' if passed else 'FAIL'}")
    return passed


def main() -> int:
    """Run the two frozen development-set checks without printing local paths."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = _arguments()
    cases = (
        _Case(
            stock_code="1167.HK",
            pdf_path=args.pdf_1167,
            expected_pages={
                "commercialization_status": frozenset({17}),
                "core_product_pipeline": frozenset({13}),
            },
        ),
        _Case(
            stock_code="9633.HK",
            pdf_path=args.pdf_9633,
            expected_pages={
                "commercialization_status": frozenset({107}),
                "core_product_pipeline": frozenset({107}),
            },
        ),
    )
    outcomes = [_run_case(case) for case in cases]
    return 1 if any(result is False for result in outcomes) else 0


if __name__ == "__main__":
    raise SystemExit(main())
