"""Opt-in multi-lane high-recall retrieval for Role-B v0.4.6.

The forensic fixed-10 showed that parser preservation and candidate generation,
not general LLM validity, are the largest proven first failures.  This adapter
therefore combines the frozen DomainAware V2.1 lane, parser-provided alternate
text views, a case-local window BM25 lane, and bounded page-level rank fusion.

Unknown queries still use the released keyword retriever unchanged.  The hybrid
lane accepts no issuer, security, case, page, or Gold-derived rule and always
maps candidates back to the original physical-page chunk identity.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
import re
from uuid import NAMESPACE_URL, uuid5

from ipo_risk.retrieval.bm25_v3 import BM25Config, PageBM25Index
from ipo_risk.retrieval.domain_aware_v21 import DomainAwareRetrieverV21
from ipo_risk.retrieval.keyword import (
    KeywordDocumentRetriever,
    normalize_for_match,
    normalize_with_index_map,
)
from ipo_risk.schemas import DocumentChunk, Evidence, EvidenceSourceType


_FINANCIAL_RISKS = frozenset(
    {
        "cash_runway",
        "continuous_loss",
        "revenue_growth",
        "customer_concentration",
        "supplier_concentration",
    }
)
_QUERY_TO_RISK = {
    "cash_runway": "cash_runway",
    "continuous_loss": "continuous_loss",
    "revenue_growth": "revenue_growth",
    "customer_concentration": "customer_concentration",
    "supplier_concentration": "supplier_concentration",
    "redemption_rights": "redemption_rights",
    "material_litigation_compliance": "material_litigation_compliance",
    "commercialization_status": "precommercial_product",
    "core_product_pipeline": "precommercial_product",
    "precommercial_product": "precommercial_product",
}
_CONTEXT_LIMIT = 6000
_BM25_WINDOW_SIZE = 5200
_BM25_WINDOW_STRIDE = 3600
_DOMAIN_DEPTH = 60
_BM25_DEPTH = 100
_FUSION_DEPTH = 60
_RRF_K = 60
_BM25_CONFIG = BM25Config(
    name="RoleB-BM25-C",
    tokenizer="cjk_bigram_trigram",
    k1=1.8,
    b=0.50,
    top_k=_BM25_DEPTH,
)


@dataclass(frozen=True, slots=True)
class _SearchSource:
    source_chunk: DocumentChunk
    view_name: str
    text: str


@dataclass(frozen=True, slots=True)
class _WindowSource:
    source: _SearchSource
    start: int
    end: int
    text: str


@dataclass(frozen=True, slots=True)
class _FusedPage:
    page: int
    score: float
    domain_rank: int | None
    bm25_rank: int | None


@dataclass(slots=True)
class _SearchCorpus:
    chunks: list[DocumentChunk]
    sources: dict[str, _SearchSource]
    bm25: PageBM25Index
    windows: dict[int, _WindowSource]


class RoleBFinancialHighRecallRetriever:
    """Opt-in hybrid retrieval while preserving generic keyword semantics."""

    # Keep the public name stable for existing v0.4.6 configs.  The version is
    # the behaviour identity used by Evidence provenance and journal hashes.
    name = "role_b_v046_financial_high_recall"
    version = "role_b_v046_hybrid_high_recall_v2"

    def __init__(self) -> None:
        self._keyword = KeywordDocumentRetriever()
        self._domain = DomainAwareRetrieverV21(
            base=self._keyword,
            candidate_depth=_DOMAIN_DEPTH,
        )
        self._result_cache: dict[tuple[str, str], list[Evidence]] = {}
        self._corpus_cache: dict[str, _SearchCorpus] = {}

    def retrieve(
        self,
        chunks: list[DocumentChunk],
        query: str,
        limit: int = 3,
    ) -> list[Evidence]:
        risk_code = _QUERY_TO_RISK.get(query)
        if risk_code is None:
            return self._keyword.retrieve(chunks, query, limit=limit)
        return self._retrieve_high_recall(chunks, risk_code, limit=limit)

    def retrieve_for_risk(
        self,
        chunks: list[DocumentChunk],
        risk_code: str,
        *,
        limit: int = 10,
    ) -> list[Evidence]:
        if risk_code not in _FINANCIAL_RISKS:
            raise ValueError(f"unsupported Financial risk pool:{risk_code}")
        return self._retrieve_high_recall(chunks, risk_code, limit=limit)

    def _retrieve_high_recall(
        self,
        chunks: list[DocumentChunk],
        risk_code: str,
        *,
        limit: int,
    ) -> list[Evidence]:
        if limit <= 0 or not chunks:
            return []
        fingerprint = self._chunk_fingerprint(chunks)
        cache_key = (fingerprint, risk_code)
        values = self._result_cache.get(cache_key)
        if values is None:
            corpus = self._corpus_cache.get(fingerprint)
            if corpus is None:
                corpus = self._build_corpus(chunks)
                self._corpus_cache[fingerprint] = corpus
            domain = self._domain_candidates(corpus, risk_code)
            bm25 = self._bm25_candidates(corpus, risk_code)
            values = self._fuse(
                risk_code,
                domain,
                bm25,
                limit=_FUSION_DEPTH,
            )
            self._result_cache[cache_key] = values
        return list(values[:limit])

    @staticmethod
    def _chunk_fingerprint(chunks: Sequence[DocumentChunk]) -> str:
        digest = sha256()
        for chunk in chunks:
            digest.update(
                f"{chunk.document_id}|{chunk.chunk_id}|{chunk.page}|".encode("utf-8")
            )
            digest.update(chunk.text.encode("utf-8"))
            variants = chunk.metadata.get("search_text_variants")
            if isinstance(variants, Mapping):
                for name, text in sorted(
                    variants.items(), key=lambda item: str(item[0])
                ):
                    digest.update(str(name).encode("utf-8"))
                    digest.update(str(text).encode("utf-8"))
        return digest.hexdigest()

    def _build_corpus(self, chunks: Sequence[DocumentChunk]) -> _SearchCorpus:
        search_chunks, sources = self._search_chunks(chunks)
        windows: list[DocumentChunk] = []
        window_sources: dict[int, _WindowSource] = {}
        seen_windows: set[tuple[object, ...]] = set()
        pseudo_page = 0
        for chunk in search_chunks:
            source = sources[chunk.chunk_id]
            for start, end in self._window_ranges(len(chunk.text)):
                text = chunk.text[start:end]
                identity = (
                    source.source_chunk.document_id,
                    source.source_chunk.page,
                    sha256(
                        re.sub(r"\s+", "", text).casefold().encode("utf-8")
                    ).hexdigest(),
                )
                if identity in seen_windows:
                    continue
                seen_windows.add(identity)
                pseudo_page += 1
                windows.append(
                    DocumentChunk(
                        document_id=source.source_chunk.document_id,
                        chunk_id=f"role_b_bm25_window:{pseudo_page}",
                        page=pseudo_page,
                        section=source.source_chunk.section,
                        text=text,
                        block_type="retrieval_window",
                        metadata={
                            "source_chunk_id": source.source_chunk.chunk_id,
                            "source_text_view": source.view_name,
                            "window_start": start,
                            "window_end": end,
                        },
                    )
                )
                window_sources[pseudo_page] = _WindowSource(
                    source=source,
                    start=start,
                    end=end,
                    text=text,
                )
        return _SearchCorpus(
            chunks=search_chunks,
            sources=sources,
            bm25=PageBM25Index(windows, _BM25_CONFIG),
            windows=window_sources,
        )

    @staticmethod
    def _search_chunks(
        chunks: Sequence[DocumentChunk],
    ) -> tuple[list[DocumentChunk], dict[str, _SearchSource]]:
        expanded: list[DocumentChunk] = []
        sources: dict[str, _SearchSource] = {}
        for chunk in chunks:
            values: list[tuple[str, str]] = [("primary", chunk.text)]
            variants = chunk.metadata.get("search_text_variants")
            if isinstance(variants, Mapping):
                values.extend(
                    (str(name), str(text))
                    for name, text in sorted(
                        variants.items(), key=lambda item: str(item[0])
                    )
                    if str(text).strip()
                )
            seen: set[str] = set()
            for view_name, raw_text in values:
                text = raw_text.strip()
                identity = re.sub(r"\s+", "", normalize_for_match(text))
                if not text or not identity or identity in seen:
                    continue
                seen.add(identity)
                safe_view = (
                    re.sub(r"[^a-zA-Z0-9_-]+", "_", view_name).strip("_")
                    or "view"
                )
                virtual_id = (
                    chunk.chunk_id
                    if view_name == "primary"
                    else f"{chunk.chunk_id}:role_b_search:{safe_view}"
                )
                virtual = chunk.model_copy(
                    update={
                        "chunk_id": virtual_id,
                        "text": text,
                        "block_type": (
                            chunk.block_type
                            if view_name == "primary"
                            else "retrieval_search_view"
                        ),
                        "metadata": {
                            **chunk.metadata,
                            "source_chunk_id": chunk.chunk_id,
                            "source_text_view": view_name,
                            "retrieval_only_search_view": view_name != "primary",
                        },
                    }
                )
                expanded.append(virtual)
                sources[virtual_id] = _SearchSource(chunk, view_name, text)
        return expanded, sources

    def _domain_candidates(
        self,
        corpus: _SearchCorpus,
        risk_code: str,
    ) -> list[Evidence]:
        raw = self._domain.retrieve_for_risk(
            corpus.chunks,
            risk_code,
            limit=_DOMAIN_DEPTH,
        )
        output: list[Evidence] = []
        seen: set[tuple[object, ...]] = set()
        for evidence in raw:
            source = corpus.sources.get(evidence.chunk_id or "")
            if source is None:
                continue
            start, end = self._context_bounds(evidence, source.text)
            text = source.text[start:end]
            identity = (
                source.source_chunk.document_id,
                source.source_chunk.page,
                sha256(text.encode("utf-8")).hexdigest(),
            )
            if identity in seen:
                continue
            seen.add(identity)
            evidence_id = str(
                uuid5(
                    NAMESPACE_URL,
                    f"{self.version}|domain|{risk_code}|"
                    f"{source.source_chunk.document_id}|"
                    f"{source.source_chunk.chunk_id}|{source.view_name}|{start}|{end}",
                )
            )
            output.append(
                evidence.model_copy(
                    update={
                        "evidence_id": evidence_id,
                        "document_id": source.source_chunk.document_id,
                        "chunk_id": source.source_chunk.chunk_id,
                        "page": source.source_chunk.page,
                        "section": source.source_chunk.section,
                        "text": text,
                        "bbox": source.source_chunk.bbox,
                        "metadata": {
                            **evidence.metadata,
                            "retriever": self.name,
                            "retriever_version": self.version,
                            "retrieval_lane": "domain_v21",
                            "query_intent": risk_code,
                            "query_family": risk_code,
                            "source_text_view": source.view_name,
                            "source_chunk_id": source.source_chunk.chunk_id,
                            "context_adapter": self.version,
                            "snippet_start": start,
                            "snippet_end": end,
                            "source_text_length": len(source.text),
                            "context_truncated": (
                                start > 0 or end < len(source.text)
                            ),
                        },
                    }
                )
            )
        return output

    @staticmethod
    def _context_bounds(evidence: Evidence, text: str) -> tuple[int, int]:
        terms = [
            str(value)
            for value in evidence.metadata.get("matched_terms") or []
            if str(value).strip()
        ]
        for row in evidence.metadata.get("query_provenance") or []:
            if isinstance(row, Mapping) and str(row.get("query_text") or "").strip():
                terms.append(str(row["query_text"]))
        normalized, index_map = normalize_with_index_map(text)
        positions: list[int] = []
        for term in terms:
            position = normalized.find(normalize_for_match(term))
            if 0 <= position < len(index_map):
                positions.append(index_map[position])
        center = min(positions) if positions else 0
        start = max(0, center - _CONTEXT_LIMIT // 3)
        end = min(len(text), start + _CONTEXT_LIMIT)
        return max(0, end - _CONTEXT_LIMIT), end

    def _bm25_candidates(
        self,
        corpus: _SearchCorpus,
        risk_code: str,
    ) -> list[Evidence]:
        if not corpus.windows:
            return []
        ranked = corpus.bm25.search(risk_code, top_k=_BM25_DEPTH)
        grouped: dict[int, list[tuple[int, float, _WindowSource]]] = defaultdict(list)
        first_rank: dict[int, int] = {}
        for candidate in ranked:
            window = corpus.windows.get(candidate.page)
            if window is None or window.source.source_chunk.page is None:
                continue
            physical_page = window.source.source_chunk.page
            first_rank.setdefault(physical_page, candidate.rank)
            if len(grouped[physical_page]) < 2:
                grouped[physical_page].append(
                    (candidate.rank, candidate.score, window)
                )

        output: list[Evidence] = []
        for physical_page in sorted(
            first_rank,
            key=lambda page: (first_rank[page], page),
        ):
            selected = grouped[physical_page]
            if not selected:
                continue
            text = self._merge_fragments([row[2].text for row in selected])
            primary = selected[0][2]
            ranks = [row[0] for row in selected]
            scores = [row[1] for row in selected]
            evidence_id = str(
                uuid5(
                    NAMESPACE_URL,
                    f"{self.version}|bm25|{risk_code}|"
                    f"{primary.source.source_chunk.document_id}|"
                    f"{primary.source.source_chunk.chunk_id}|{physical_page}|"
                    f"{sha256(text.encode('utf-8')).hexdigest()}",
                )
            )
            relevance = max(
                0.15,
                min(0.75, 0.75 - 0.006 * (min(ranks) - 1)),
            )
            output.append(
                Evidence(
                    evidence_id=evidence_id,
                    document_id=primary.source.source_chunk.document_id,
                    chunk_id=primary.source.source_chunk.chunk_id,
                    page=physical_page,
                    section=primary.source.source_chunk.section,
                    text=text,
                    bbox=primary.source.source_chunk.bbox,
                    source_type=EvidenceSourceType.PROSPECTUS,
                    relevance_score=relevance,
                    metadata={
                        "retriever": self.name,
                        "retriever_version": self.version,
                        "retrieval_lane": "bm25_window",
                        "query_intent": risk_code,
                        "query_family": risk_code,
                        "source_chunk_id": primary.source.source_chunk.chunk_id,
                        "source_text_views": [
                            row[2].source.view_name for row in selected
                        ],
                        "bm25_window_ranks": ranks,
                        "bm25_window_scores": scores,
                        "window_ranges": [
                            [row[2].start, row[2].end] for row in selected
                        ],
                        "context_adapter": self.version,
                    },
                )
            )
        return output

    @staticmethod
    def _window_ranges(length: int) -> list[tuple[int, int]]:
        if length <= 0:
            return []
        if length <= _BM25_WINDOW_SIZE:
            return [(0, length)]
        starts = list(
            range(
                0,
                max(1, length - _BM25_WINDOW_SIZE + 1),
                _BM25_WINDOW_STRIDE,
            )
        )
        final_start = max(0, length - _BM25_WINDOW_SIZE)
        if not starts or starts[-1] != final_start:
            starts.append(final_start)
        return [
            (start, min(length, start + _BM25_WINDOW_SIZE))
            for start in starts
        ]

    def _fuse(
        self,
        risk_code: str,
        domain: Sequence[Evidence],
        bm25: Sequence[Evidence],
        *,
        limit: int,
    ) -> list[Evidence]:
        domain_by_page = self._first_by_page(domain)
        bm25_by_page = self._first_by_page(bm25)
        pages = set(domain_by_page) | set(bm25_by_page)
        fused: list[_FusedPage] = []
        for page in pages:
            domain_rank = domain_by_page.get(page, (None, None))[0]
            bm25_rank = bm25_by_page.get(page, (None, None))[0]
            score = 0.0
            if domain_rank is not None:
                score += 2.0 / (_RRF_K + domain_rank)
            if bm25_rank is not None:
                score += 1.0 / (_RRF_K + bm25_rank)
            fused.append(
                _FusedPage(
                    page=page,
                    score=score,
                    domain_rank=domain_rank,
                    bm25_rank=bm25_rank,
                )
            )
        fused.sort(
            key=lambda item: (
                -item.score,
                item.domain_rank or 9999,
                item.bm25_rank or 9999,
                item.page,
            )
        )

        output: list[Evidence] = []
        for final_rank, row in enumerate(fused[:limit], start=1):
            domain_evidence = domain_by_page.get(row.page, (None, None))[1]
            bm25_evidence = bm25_by_page.get(row.page, (None, None))[1]
            base = domain_evidence or bm25_evidence
            if base is None:
                continue
            fragments = [
                evidence.text
                for evidence in (bm25_evidence, domain_evidence)
                if evidence is not None
            ]
            text = self._merge_fragments(fragments)
            text_hash = sha256(text.encode("utf-8")).hexdigest()
            lanes = [
                name
                for name, evidence in (
                    ("domain_v21", domain_evidence),
                    ("bm25_window", bm25_evidence),
                )
                if evidence is not None
            ]
            evidence_id = str(
                uuid5(
                    NAMESPACE_URL,
                    f"{self.version}|fusion|{risk_code}|{base.document_id}|"
                    f"{base.chunk_id}|{row.page}|{text_hash}",
                )
            )
            relevance = max(
                domain_evidence.relevance_score if domain_evidence else 0.0,
                bm25_evidence.relevance_score if bm25_evidence else 0.0,
            )
            if len(lanes) > 1:
                relevance = min(1.0, relevance + 0.10)
            output.append(
                base.model_copy(
                    update={
                        "evidence_id": evidence_id,
                        "text": text,
                        "relevance_score": relevance,
                        "metadata": {
                            **base.metadata,
                            "retriever": self.name,
                            "retriever_version": self.version,
                            "retrieval_lane": "weighted_rrf_fusion",
                            "retrieval_lanes": lanes,
                            "query_intent": risk_code,
                            "query_family": risk_code,
                            "final_rank": final_rank,
                            "domain_rank": row.domain_rank,
                            "bm25_rank": row.bm25_rank,
                            "weighted_rrf_score": row.score,
                            "context_adapter": self.version,
                            "merged_context": len(lanes) > 1,
                            "merged_text_sha256": text_hash,
                        },
                    }
                )
            )
        return output

    @staticmethod
    def _first_by_page(
        values: Sequence[Evidence],
    ) -> dict[int, tuple[int, Evidence]]:
        output: dict[int, tuple[int, Evidence]] = {}
        for rank, evidence in enumerate(values, start=1):
            if evidence.page is not None and evidence.page not in output:
                output[evidence.page] = (rank, evidence)
        return output

    @staticmethod
    def _merge_fragments(values: Sequence[str]) -> str:
        retained: list[str] = []
        canonical: list[str] = []
        for raw in values:
            text = (raw or "").strip()
            identity = re.sub(r"\s+", "", normalize_for_match(text))
            if not text or not identity:
                continue
            if any(identity in previous for previous in canonical):
                continue
            superseded = [
                index
                for index, previous in enumerate(canonical)
                if previous in identity
            ]
            for index in reversed(superseded):
                del retained[index]
                del canonical[index]
            retained.append(text)
            canonical.append(identity)
        if not retained:
            return ""
        if len(retained) == 1:
            return retained[0][:_CONTEXT_LIMIT]

        primary = retained[0][:_BM25_WINDOW_SIZE]
        separator = "\n"
        supplement_budget = max(
            0,
            _CONTEXT_LIMIT - len(primary) - len(separator),
        )
        supplement = retained[1][:supplement_budget]
        if not supplement:
            return primary[:_CONTEXT_LIMIT]
        return f"{primary}{separator}{supplement}"[:_CONTEXT_LIMIT]
