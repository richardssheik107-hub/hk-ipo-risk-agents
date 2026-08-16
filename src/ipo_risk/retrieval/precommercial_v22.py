"""V2.2 research-only candidate extension for ``precommercial_product``.

This module is deliberately absent from the production registry.  It preserves
the complete V2.1 ordering and only appends candidates produced by a small,
development-set-derived lexical policy.  Consequently it cannot improve the
existing head by reranking it; it only tests whether missing pages can enter a
bounded candidate pool.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from ipo_risk.retrieval.domain_aware_v21 import DomainAwareRetrieverV21
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.schemas import DocumentChunk, Evidence, EvidenceSourceType


@dataclass(frozen=True)
class CandidateQueryFamily:
    name: str
    phrases: tuple[str, ...]


# Frozen after inspecting only historical_development + development cases.
# No company, product, stock-code, page or case-specific token is permitted.
PRECOMMERCIAL_V22_QUERY_FAMILIES = (
    CandidateQueryFamily(
        "commercial_revenue_source",
        ("收益主要來自", "收入主要來自", "收益源自"),
    ),
    CandidateQueryFamily(
        "revenue_disaggregation_heading",
        ("收入分拆", "收入明細", "貨品或服務類型", "商品或服務類型"),
    ),
    CandidateQueryFamily(
        "product_or_goods_sales",
        ("產品銷售", "銷售產品", "商品收入"),
    ),
)


class PrecommercialCandidateRetrieverV22:
    """Append-only V2.1 candidate experiment; not a production retriever."""

    name = "precommercial_candidate_v22_experiment"
    version = "precommercial_candidate_v22_round1_frozen"

    def __init__(
        self,
        *,
        base: Any | None = None,
        baseline: Any | None = None,
        query_depth: int = 5,
        neighbour_radius: int = 1,
    ) -> None:
        self._base = base or KeywordDocumentRetriever()
        self._baseline = baseline or DomainAwareRetrieverV21(base=self._base)
        self._query_depth = max(1, query_depth)
        self._neighbour_radius = max(0, neighbour_radius)

    def retrieve(self, chunks: list[DocumentChunk], query: str, limit: int = 3) -> list[Evidence]:
        if query == "precommercial_product":
            return self.retrieve_for_risk(chunks, query, limit=limit)
        return self._baseline.retrieve(chunks, query, limit=limit)

    def retrieve_for_risk(
        self,
        chunks: list[DocumentChunk],
        risk_code: str,
        *,
        limit: int = 20,
    ) -> list[Evidence]:
        if limit <= 0:
            return []
        baseline = self._baseline.retrieve_for_risk(chunks, risk_code, limit=limit)
        if risk_code != "precommercial_product" or len(baseline) >= limit:
            return baseline

        output = list(baseline)
        seen_pages = {item.page for item in output if item.page is not None}
        by_page = {chunk.page: chunk for chunk in chunks}
        for family in PRECOMMERCIAL_V22_QUERY_FAMILIES:
            for phrase in family.phrases:
                hits = self._base.retrieve(chunks, phrase, limit=self._query_depth)
                for local_rank, hit in enumerate(hits, 1):
                    if hit.page is None:
                        continue
                    for page, neighbour_distance in self._expanded_pages(hit.page):
                        if page in seen_pages or page not in by_page:
                            continue
                        output.append(self._candidate_evidence(
                            by_page[page], family.name, phrase, local_rank,
                            seed_page=hit.page, neighbour_distance=neighbour_distance,
                            final_rank=len(output) + 1,
                        ))
                        seen_pages.add(page)
                        if len(output) >= limit:
                            return output
        return output

    def _expanded_pages(self, seed_page: int) -> Iterable[tuple[int, int]]:
        yield seed_page, 0
        for distance in range(1, self._neighbour_radius + 1):
            yield seed_page - distance, -distance
            yield seed_page + distance, distance

    def _candidate_evidence(
        self,
        chunk: DocumentChunk,
        family: str,
        phrase: str,
        local_rank: int,
        *,
        seed_page: int,
        neighbour_distance: int,
        final_rank: int,
    ) -> Evidence:
        evidence_id = str(uuid5(
            NAMESPACE_URL,
            f"{self.version}|{chunk.document_id}|{chunk.page}|{family}|{phrase}",
        ))
        return Evidence(
            evidence_id=evidence_id,
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            page=chunk.page,
            section=chunk.section,
            text=" ".join(chunk.text.split())[:1600],
            bbox=chunk.bbox,
            source_type=EvidenceSourceType.PROSPECTUS,
            relevance_score=max(0.0, min(1.0, 1.0 / local_rank)),
            metadata={
                "retriever": self.name,
                "retriever_version": self.version,
                "risk_code": "precommercial_product",
                "candidate_generation_only": True,
                "baseline_order_preserved": True,
                "query_family": family,
                "query_text": phrase,
                "local_query_rank": local_rank,
                "seed_page": seed_page,
                "neighbour_distance": neighbour_distance,
                "final_rank": final_rank,
            },
        )


def frozen_query_phrases() -> tuple[str, ...]:
    """Expose the exact experiment config for reporting and tests."""
    return tuple(phrase for family in PRECOMMERCIAL_V22_QUERY_FAMILIES for phrase in family.phrases)
