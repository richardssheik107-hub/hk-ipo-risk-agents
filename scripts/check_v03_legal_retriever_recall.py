"""Run safe, local-only Legal Retriever development acceptance for cases A-H."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ipo_risk.parsers.pymupdf_parser import PyMuPDFDocumentParser
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.schemas import DocumentParseRequest


CASES = {
    "A": ("9898.HK", "ipo_2021_09898", "redemption_rights", 300),
    "B": ("9863.HK", "ipo_2022_09863", "redemption_rights", 207),
    "C": ("2517.HK", "ipo_2023_02517", "redemption_rights", 152),
    "D": ("1961.HK", "ipo_2020_01961", "redemption_rights", 78),
    "E": ("6698.HK", "ipo_2022_06698", "material_litigation_compliance", 26),
    "F": ("2451.HK", "ipo_2023_02451", "material_litigation_compliance", 298),
    "G": ("9600.HK", "ipo_2020_09600", "material_litigation_compliance", 222),
    "H": ("1942.HK", "ipo_2020_01942", "material_litigation_compliance", 44),
}
ENV_NAME = "IPO_RISK_GATE_A09_PDFS"


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Legal A-H development recall without network access."
    )
    parser.add_argument(
        "--pdf",
        action="append",
        default=[],
        metavar="CASE=PATH",
        help="Repeat for A-H. Alternatively set IPO_RISK_GATE_A09_PDFS as JSON.",
    )
    return parser.parse_args()


def _parse_assignments(values: list[str]) -> dict[str, Path]:
    assignments: dict[str, Path] = {}
    for value in values:
        case_id, separator, raw_path = value.partition("=")
        case_id = case_id.strip().upper()
        if not separator or case_id not in CASES or not raw_path.strip():
            raise ValueError("Each --pdf value must use a known CASE=PATH assignment.")
        assignments[case_id] = Path(raw_path.strip())
    return assignments


def _configured_paths(cli_values: list[str]) -> dict[str, Path]:
    assignments = _parse_assignments(cli_values)
    raw_environment = os.getenv(ENV_NAME, "").strip()
    if raw_environment:
        decoded = json.loads(raw_environment)
        if not isinstance(decoded, dict):
            raise ValueError(f"{ENV_NAME} must be a JSON object of CASE to path.")
        environment_values = [f"{key}={value}" for key, value in decoded.items()]
        assignments = {**_parse_assignments(environment_values), **assignments}
    return assignments


def main() -> int:
    """Return success only when every fixed development target is in Top-5."""
    try:
        paths = _configured_paths(_arguments().pdf)
    except (ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}))
        return 2

    missing = [
        case_id
        for case_id in CASES
        if case_id not in paths
        or not paths[case_id].is_file()
        or paths[case_id].suffix.lower() != ".pdf"
    ]
    if missing:
        print(
            json.dumps(
                {"status": "BLOCKED", "reason": "missing_pdfs", "cases": missing}
            )
        )
        return 2

    parser = PyMuPDFDocumentParser()
    retriever = KeywordDocumentRetriever()
    results: list[dict[str, object]] = []
    for case_id, (stock_code, document_id, family, expected_page) in CASES.items():
        try:
            chunks = parser.parse(
                DocumentParseRequest(
                    document_id=document_id,
                    prospectus_path=str(paths[case_id]),
                )
            )
        except Exception:
            print(
                json.dumps(
                    {
                        "status": "BLOCKED",
                        "reason": "parse_failed",
                        "case_id": case_id,
                        "stock_code": stock_code,
                    }
                )
            )
            return 2
        evidence = retriever.retrieve(chunks, family, limit=5)
        pages = [item.page for item in evidence]
        rank = pages.index(expected_page) + 1 if expected_page in pages else None
        result = {
            "case_id": case_id,
            "stock_code": stock_code,
            "query_family": family,
            "expected_page": expected_page,
            "ranked_pages": pages,
            "evidence_ids": [item.evidence_id for item in evidence],
            "hit": rank is not None,
            "rank": rank,
        }
        results.append(result)
        print(json.dumps(result, ensure_ascii=False))

    summary = {
        "status": "PASS" if all(item["hit"] for item in results) else "MISS",
        "cases": len(results),
        "top1": sum(item["rank"] == 1 for item in results),
        "top3": sum(
            item["rank"] is not None and int(item["rank"]) <= 3
            for item in results
        ),
        "top5": sum(bool(item["hit"]) for item in results),
        "limit": 5,
        "classification": "development_draft_acceptance_not_formal_golden_recall",
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
