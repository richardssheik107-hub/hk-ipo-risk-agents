"""Opt-in Financial-only high-recall adapter for Role-B v0.4.6.

Legal and Business continue to receive the released keyword output through
``retrieve``.  Only Financial agents that explicitly request a governed risk
pool use the frozen deterministic V2.1 lane.  The adapter has no Gold, issuer,
stock-code, or physical-page inputs.
"""

from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from ipo_risk.retrieval.domain_aware_v21 import DomainAwareRetrieverV21
from ipo_risk.retrieval.keyword import (
    KeywordDocumentRetriever,
    normalize_for_match,
    normalize_with_index_map,
)
from ipo_risk.schemas import DocumentChunk, Evidence


_FINANCIAL_RISKS = frozenset(
    {
        "cash_runway",
        "continuous_loss",
        "revenue_growth",
        "customer_concentration",
        "supplier_concentration",
    }
)
_CONTEXT_LIMIT = 6000


class RoleBFinancialHighRecallRetriever:
    """Preserve keyword semantics except for explicit Financial risk pools."""

    name = "role_b_v046_financial_high_recall"
    version = "role_b_v046_financial_high_recall_v1"

    def __init__(self) -> None:
        self._keyword = KeywordDocumentRetriever()
        self._domain = DomainAwareRetrieverV21(base=self._keyword)

    def retrieve(
        self, chunks: list[DocumentChunk], query: str, limit: int = 3
    ) -> list[Evidence]:
        return self._keyword.retrieve(chunks, query, limit=limit)

    def retrieve_for_risk(
        self, chunks: list[DocumentChunk], risk_code: str, *, limit: int = 10
    ) -> list[Evidence]:
        if risk_code not in _FINANCIAL_RISKS:
            raise ValueError(f"unsupported Financial risk pool:{risk_code}")
        values = self._domain.retrieve_for_risk(chunks, risk_code, limit=limit)
        by_id = {chunk.chunk_id: chunk for chunk in chunks}
        return [self._expand(value, by_id) for value in values]

    def _expand(
        self, evidence: Evidence, by_id: dict[str, DocumentChunk]
    ) -> Evidence:
        chunk = by_id.get(evidence.chunk_id or "")
        if chunk is None or len(chunk.text) <= len(evidence.text):
            return evidence

        start = self._context_start(evidence, chunk)
        end = min(len(chunk.text), start + _CONTEXT_LIMIT)
        start = max(0, end - _CONTEXT_LIMIT)
        metadata = {
            **evidence.metadata,
            "query_intent": evidence.metadata.get("risk_code"),
            "query_family": evidence.metadata.get("risk_code"),
            "context_adapter": self.version,
            "snippet_start": start,
            "snippet_end": end,
            "source_text_length": len(chunk.text),
            "context_truncated": start > 0 or end < len(chunk.text),
        }
        evidence_id = str(
            uuid5(
                NAMESPACE_URL,
                f"{self.version}|{chunk.document_id}|{chunk.chunk_id}|{start}|{end}",
            )
        )
        return evidence.model_copy(
            update={
                "evidence_id": evidence_id,
                "text": chunk.text[start:end],
                "metadata": metadata,
            }
        )

    @staticmethod
    def _context_start(evidence: Evidence, chunk: DocumentChunk) -> int:
        terms = evidence.metadata.get("matched_terms") or []
        normalized, index_map = normalize_with_index_map(chunk.text)
        normalized_text = normalize_for_match(normalized)
        positions: list[int] = []
        for term in terms:
            normalized_term = normalize_for_match(str(term))
            position = normalized_text.find(normalized_term)
            if position >= 0 and position < len(index_map):
                positions.append(index_map[position])
        center = min(positions) if positions else 0
        return max(0, center - _CONTEXT_LIMIT // 3)
