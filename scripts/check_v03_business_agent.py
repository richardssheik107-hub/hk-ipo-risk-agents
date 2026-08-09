"""Run the standalone V3-7 Business Agent on one configured local PDF."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from ipo_risk.agents.business_v03 import PROMPT_VERSION, V03BusinessAgent
from ipo_risk.parsers.pymupdf_parser import DocumentParseError, PyMuPDFDocumentParser
from ipo_risk.schemas import DocumentParseRequest, IPOProfile


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pdf",
        default=os.getenv("IPO_RISK_V37_BUSINESS_PDF"),
        help="Local development-set PDF (or IPO_RISK_V37_BUSINESS_PDF).",
    )
    parser.add_argument(
        "--stock-code",
        default=os.getenv("IPO_RISK_V37_BUSINESS_STOCK_CODE", ""),
    )
    parser.add_argument(
        "--company-name",
        default=os.getenv("IPO_RISK_V37_BUSINESS_COMPANY_NAME", ""),
    )
    return parser.parse_args()


def main() -> int:
    """Execute Parser, official Retriever, and Business Agent safely."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = _arguments()
    if not args.pdf:
        print("status=NOT_TESTED reason=pdf_not_configured")
        return 0

    path = Path(args.pdf)
    if not path.is_file() or path.suffix.lower() != ".pdf":
        print("status=FAIL reason=invalid_pdf")
        return 1

    parser = PyMuPDFDocumentParser()
    document_id = f"v37-business-{args.stock_code or 'local'}"
    try:
        chunks = parser.parse(
            DocumentParseRequest(
                document_id=document_id,
                prospectus_path=str(path),
            )
        )
    except DocumentParseError as exc:
        print(f"status=FAIL reason=parser_error code={exc.error.code}")
        return 1

    agent = V03BusinessAgent()
    risks = agent.analyze(
        IPOProfile(company_name=args.company_name or "Local development case", stock_code=args.stock_code),
        chunks,
    )
    print(f"parsed_chunks={len(chunks)} parser_errors={len(parser.last_errors)}")
    print(f"risk_count={len(risks)} prompt_version={PROMPT_VERSION}")
    for diagnostic in agent.last_diagnostics:
        print(
            f"diagnostic={diagnostic.code.value} "
            f"provider={diagnostic.metadata.get('llm_provider', 'deterministic')} "
            f"llm_mode={diagnostic.metadata.get('llm_mode', 'not_configured')}"
        )
    for risk in risks:
        print(
            f"risk_code={risk.risk_code} "
            f"verification_status={risk.verification_status.value}"
        )
        for evidence in risk.evidence:
            print(f"evidence_page={evidence.page} evidence_id={evidence.evidence_id}")
    print("status=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
