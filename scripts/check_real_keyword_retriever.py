"""Manual acceptance helper for the real prospectus keyword retriever."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from ipo_risk.parsers.pymupdf_parser import PyMuPDFDocumentParser
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.schemas import DocumentParseRequest


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    path = Path(os.getenv("IPO_RISK_REAL_CASE_PDF", "data/local/real_case_001/prospectus.pdf"))
    chunks = PyMuPDFDocumentParser().parse(DocumentParseRequest(document_id="real_case_001", prospectus_path=str(path)))
    retriever = KeywordDocumentRetriever()
    for query, expected_page in (("现金及现金等价物", 563), ("经营活动现金流", 562)):
        results = retriever.retrieve(chunks, query, limit=len(chunks))
        print(f"\n查询：{query}")
        for rank, item in enumerate(results[:5], start=1):
            print(f"#{rank} page={item.page} chunk_id={item.chunk_id} score={item.relevance_score:.2f}")
            print(f"  evidence_id={item.evidence_id}")
            print(f"  matched={item.metadata['matched_keywords']} intent={item.metadata['query_intent']}")
            print(f"  text={item.text}\n")
        ranks = {item.page: rank for rank, item in enumerate(results, start=1)}
        print(f"expected_page_{expected_page}_rank={ranks.get(expected_page, 'not_matched')}")
        print(f"page_665_rank={ranks.get(665, 'not_matched')}")
        print(f"page_683_rank={ranks.get(683, 'not_matched')}")


if __name__ == "__main__":
    main()
