"""Opt-in production adapter for the frozen case-local BM25 candidate lane.

The research implementation in :mod:`ipo_risk.retrieval.bm25_v3` works at
physical-page level.  This adapter preserves the existing ``Evidence``
contract, fuses BM25 with the production keyword ranking, and keeps at most
one active document index in memory.  A new document replaces it; nothing is
written to disk.
"""

from __future__ import annotations

from collections import defaultdict
from threading import Lock
from uuid import NAMESPACE_URL, uuid5

from ipo_risk.retrieval.bm25_v3 import (
    BM25_VARIANTS,
    PageBM25Index,
    bounded_rrf_union,
    risk_query_phrases,
)
from ipo_risk.retrieval.keyword import (
    KeywordDocumentRetriever,
    normalize_for_match,
    normalize_with_index_map,
)
from ipo_risk.schemas import DocumentChunk, Evidence, EvidenceSourceType


_INTENT_TO_RISK = {
    "cash_flow_ending_cash": "cash_runway",
    "cash_balance": "cash_runway",
    "cash_and_cash_equivalents": "cash_runway",
    "operating_cash_flow": "cash_runway",
    "continuous_loss": "continuous_loss",
    "revenue": "revenue_growth",
    "customer_concentration": "customer_concentration",
    "supplier_concentration": "supplier_concentration",
    "redemption_rights": "redemption_rights",
    "material_litigation_compliance": "material_litigation_compliance",
    "commercialization_status": "precommercial_product",
    "core_product_pipeline": "precommercial_product",
}

# BM25-B is the frozen five-fold development choice.  Do not retune it here.
_BM25_B = next(config for config in BM25_VARIANTS if config.name == "BM25-B")
_LANE_DEPTH = 100
_SNIPPET_RADIUS = 800
# The development A/B showed top-5 regressions for cash runway and material
# litigation/compliance.  Their mature statement-/authority-aware keyword
# routes therefore remain authoritative; BM25 is candidate recovery for the
# other supported risk families.
_KEYWORD_ONLY_RISKS = frozenset(
    {"cash_runway", "material_litigation_compliance"}
)


class HybridBM25DocumentRetriever:
    """Fuse the existing keyword lane with frozen BM25-B using equal RRF.

    Unsupported free-text queries and any BM25 adapter failure degrade to the
    unchanged keyword result.  Multiple document identities are deliberately
    not fused because physical page numbers are only unique within one IPO.
    """

    name = "hybrid_bm25"

    def __init__(self, keyword: KeywordDocumentRetriever | None = None) -> None:
        self.keyword = keyword or KeywordDocumentRetriever()
        self._index_lock = Lock()
        self._cached_first_chunk: DocumentChunk | None = None
        self._cached_chunk_count = 0
        self._cached_index: PageBM25Index | None = None

    def retrieve(
        self, chunks: list[DocumentChunk], query: str, limit: int = 3
    ) -> list[Evidence]:
        if limit <= 0 or not query or not query.strip():
            return []

        keyword_evidence = self.keyword.retrieve(
            chunks, query, limit=_LANE_DEPTH
        )
        fallback = keyword_evidence[:limit]
        risk_code = self._risk_code(query)
        document_ids = {chunk.document_id for chunk in chunks}
        if (
            risk_code is None
            or risk_code in _KEYWORD_ONLY_RISKS
            or len(document_ids) != 1
        ):
            return fallback

        try:
            bm25 = self._index_for(chunks).search(
                risk_code, top_k=_LANE_DEPTH
            )
            if not bm25:
                return fallback
            fused = bounded_rrf_union(
                {
                    "bm25": [(item.page, item.score) for item in bm25],
                    "keyword": [
                        (item.page, item.relevance_score)
                        for item in keyword_evidence
                        if item.page is not None
                    ],
                },
                limit=min(limit, _LANE_DEPTH),
            )
            # Equal-RRF crossed ranks are true score ties.  Prefer the mature
            # production keyword lane before the page-number tie-break.  This
            # also keeps revenue-denominator evidence ahead of a receivables
            # balance page when BM25 alone reverses those two pages.
            fused = sorted(
                fused,
                key=lambda item: (
                    -item.rrf_score,
                    item.lane_ranks.get("keyword") or _LANE_DEPTH + 1,
                    item.lane_ranks.get("bm25") or _LANE_DEPTH + 1,
                    item.page,
                ),
            )
            keyword_by_page = {
                item.page: item for item in keyword_evidence if item.page is not None
            }
            chunks_by_page: dict[int, list[DocumentChunk]] = defaultdict(list)
            for chunk in chunks:
                chunks_by_page[chunk.page].append(chunk)
            top_score = fused[0].rrf_score if fused else 1.0
            output: list[Evidence] = []
            for fusion_rank, candidate in enumerate(fused, 1):
                base = keyword_by_page.get(candidate.page)
                metadata = {
                    **(base.metadata if base else {}),
                    "retriever": self.name,
                    "query_risk_code": risk_code,
                    "fusion": "equal_rrf",
                    "fusion_rank": fusion_rank,
                    "fusion_score": candidate.rrf_score,
                    "lane_ranks": candidate.lane_ranks,
                    "lane_presence": candidate.lane_presence,
                    "bm25_config": _BM25_B.name,
                    "bm25_score": candidate.bm25_score,
                    "persistent_index": False,
                    "index_scope": "one_active_document_in_memory",
                }
                relevance = min(1.0, candidate.rrf_score / top_score)
                if base is not None:
                    output.append(
                        base.model_copy(
                            update={
                                "relevance_score": relevance,
                                "metadata": metadata,
                            }
                        )
                    )
                    continue
                page_chunks = chunks_by_page.get(candidate.page, [])
                if page_chunks:
                    output.append(
                        self._bm25_evidence(
                            page_chunks, query, risk_code, relevance, metadata
                        )
                    )
            return output
        except (ValueError, ArithmeticError, KeyError, TypeError):
            # Production must remain usable if the opt-in research lane cannot
            # resolve a query or malformed chunk metadata reaches it.
            return fallback

    def _index_for(self, chunks: list[DocumentChunk]) -> PageBM25Index:
        first = chunks[0]
        with self._index_lock:
            if (
                self._cached_index is None
                or self._cached_first_chunk is not first
                or self._cached_chunk_count != len(chunks)
            ):
                self._cached_index = PageBM25Index(chunks, _BM25_B)
                # Keeping one chunk reference prevents object-id reuse from
                # making a later document look like the cached input.  A new
                # document immediately replaces this reference and the index.
                self._cached_first_chunk = first
                self._cached_chunk_count = len(chunks)
            return self._cached_index

    @staticmethod
    def _risk_code(query: str) -> str | None:
        normalized = normalize_for_match(query)
        if not normalized:
            return None
        intent, _ = KeywordDocumentRetriever._resolve_intent(normalized)
        return _INTENT_TO_RISK.get(intent)

    @staticmethod
    def _bm25_evidence(
        chunks: list[DocumentChunk],
        query: str,
        risk_code: str,
        relevance: float,
        metadata: dict,
    ) -> Evidence:
        phrases = sorted(
            risk_query_phrases(risk_code),
            key=lambda value: len(normalize_for_match(value)),
            reverse=True,
        )
        best: tuple[int, int, DocumentChunk] | None = None
        for chunk in chunks:
            normalized, index_map = normalize_with_index_map(chunk.text)
            for phrase in phrases:
                normalized_phrase = normalize_for_match(phrase)
                position = normalized.find(normalized_phrase)
                if position < 0:
                    continue
                start = index_map[position]
                end = index_map[position + len(normalized_phrase) - 1] + 1
                candidate = (len(normalized_phrase), -start, chunk)
                if best is None or candidate[:2] > best[:2]:
                    best = candidate
                break

        chunk = best[2] if best is not None else max(
            chunks, key=lambda item: (len(item.text), item.chunk_id)
        )
        if best is not None and best[2].chunk_id == chunk.chunk_id:
            target_start = -best[1]
            target_end = target_start + best[0]
        else:
            target_start = 0
            target_end = min(len(chunk.text), 1)
        snippet_start = max(0, target_start - _SNIPPET_RADIUS)
        snippet_end = min(len(chunk.text), target_end + _SNIPPET_RADIUS)
        snippet = chunk.text[snippet_start:snippet_end]
        evidence_id = str(
            uuid5(
                NAMESPACE_URL,
                f"{chunk.document_id}|{chunk.chunk_id}|{normalize_for_match(query)}|bm25|{snippet_start}|{snippet_end}",
            )
        )
        return Evidence(
            evidence_id=evidence_id,
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            page=chunk.page,
            section=chunk.section,
            text=snippet,
            bbox=chunk.bbox,
            source_type=EvidenceSourceType.PROSPECTUS,
            relevance_score=relevance,
            metadata={
                **metadata,
                "normalized_query": normalize_for_match(query),
                "snippet_start": snippet_start,
                "snippet_end": snippet_end,
                "source_text_length": len(chunk.text),
                "candidate_origin": "bm25_only",
            },
        )
