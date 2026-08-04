"""Deterministic, explainable prospectus keyword retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable
from unicodedata import normalize
from uuid import NAMESPACE_URL, uuid5

from ipo_risk.schemas import DocumentChunk, Evidence, EvidenceSourceType


# Keep phrase definitions centralized: the scoring rules must never depend on
# a prospectus name, stock code, or physical page number.
_CASH_ALIASES = (
    "现金及现金等价物", "现金和现金等价物", "现金及银行结余", "银行结余及现金", "现金流量表所述现金及现金等价物",
    "現金及現金等價物", "現金及現金等值物", "現金及銀行結餘", "銀行結餘及現金", "現金流量表所述現金及現金等價物",
    "cash and cash equivalents", "cash equivalents", "cash and bank balances", "bank balances and cash",
    "cash and cash equivalent", "cash and bank balance",
)
_OPERATING_CASH_FLOW_ALIASES = (
    "经营活动所用净现金流量", "经营活动产生的净现金流量", "经营活动所用现金净额", "经营活动产生的现金净额",
    "经营活动现金流", "经营活动所用现金", "經營活動所用淨現金流量", "經營活動產生的淨現金流量",
    "經營活動所用現金淨額", "經營活動產生的現金淨額", "經營活動現金流", "經營活動所用現金",
    "經營業務所用現金", "net cash used in operating activities", "net cash generated from operating activities",
    "operating cash flow", "cash flows from operating activities", "net operating cash flow",
)
_FINANCIAL_CONTEXT = ("綜合現金流量表", "现金流量表", "現金流量表", "會計師報告", "财务资料", "財務資料", "人民币千元", "人民幣千元")
_NEGATIVE_CONTEXT = ("主要法律及監管規定概要", "组织章程细则", "組織章程細則概要", "清算", "股东权利", "股東權利")
_CASH_RECONCILIATION_CONTEXT = ("現金流量表所述現金及現金等價物", "现金流量表所述现金及现金等价物")
_AUDITED_STATEMENT_CONTEXT = ("附錄一", "附录一", "會計師報告", "会计师报告")
_BROAD_QUERY_TERMS = ("经营活动", "經營活動", "operating", "activities", "cash")
_SEPARATORS = frozenset("·•….-_—–")


@dataclass(frozen=True)
class _NormalizedText:
    text: str
    index_map: tuple[int, ...]


@dataclass(frozen=True)
class _Match:
    keyword: str
    start: int
    end: int
    kind: str


def normalize_with_index_map(text: str) -> tuple[str, list[int]]:
    """Return matching text and a normalized-index to original-index map.

    Original input is never mutated. Whitespace and common PDF leader
    characters become a single space so a second compact representation can
    also match phrases split by a line break, table spacing, or dot leaders.
    """
    output: list[str] = []
    indexes: list[int] = []
    pending_space: int | None = None
    for original_index, character in enumerate(text):
        converted = normalize("NFKC", character).lower()
        for item in converted:
            if item.isspace() or item in _SEPARATORS:
                if output:
                    pending_space = original_index
                continue
            if pending_space is not None:
                output.append(" ")
                indexes.append(pending_space)
                pending_space = None
            output.append(item)
            indexes.append(original_index)
    return "".join(output), indexes


def normalize_for_match(text: str) -> str:
    """Normalize text for deterministic matching without changing source text."""
    return normalize_with_index_map(text)[0]


def _compact(value: _NormalizedText) -> _NormalizedText:
    return _NormalizedText(
        text="".join(char for char in value.text if not char.isspace()),
        index_map=tuple(original for char, original in zip(value.text, value.index_map) if not char.isspace()),
    )


def _find_all(haystack: str, needle: str) -> Iterable[int]:
    start = 0
    while needle:
        position = haystack.find(needle, start)
        if position < 0:
            return
        yield position
        start = position + 1


class KeywordDocumentRetriever:
    """Retrieve one traceable, stable Evidence object for each matching page."""

    name = "keyword"

    def retrieve(self, chunks: list[DocumentChunk], query: str, limit: int = 3) -> list[Evidence]:
        """Return deterministically ranked evidence; no match never has a fallback."""
        if limit <= 0 or not query or not query.strip():
            return []
        normalized_query = normalize_for_match(query)
        if not normalized_query:
            return []
        intent, aliases = self._resolve_intent(normalized_query)
        evidence = [item for chunk in chunks if (item := self._build_evidence(chunk, query, normalized_query, intent, aliases))]
        evidence.sort(key=lambda item: (-item.relevance_score, item.page or 0, item.chunk_id or "", item.evidence_id))
        return evidence[:limit]

    @staticmethod
    def _resolve_intent(normalized_query: str) -> tuple[str, tuple[str, ...]]:
        compact_query = _compact(_NormalizedText(normalized_query, tuple(range(len(normalized_query))))).text
        for intent, aliases in (
            ("cash_and_cash_equivalents", _CASH_ALIASES),
            ("operating_cash_flow", _OPERATING_CASH_FLOW_ALIASES),
        ):
            normalized_aliases = tuple(normalize_for_match(alias) for alias in aliases)
            compact_aliases = {"".join(char for char in alias if not char.isspace()) for alias in normalized_aliases}
            if compact_query in compact_aliases:
                return intent, aliases
        # A generic query is already scored as the exact query. Returning it
        # again as an alias would double-count the same match.
        return "generic_keyword", ()

    def _build_evidence(
        self,
        chunk: DocumentChunk,
        query: str,
        normalized_query: str,
        intent: str,
        aliases: tuple[str, ...],
    ) -> Evidence | None:
        normalized_text, index_map = normalize_with_index_map(chunk.text)
        source = _NormalizedText(normalized_text, tuple(index_map))
        compact_source = _compact(source)
        matches = self._matches(source, compact_source, normalized_query, aliases)
        if not matches:
            return None

        financial_context = self._matching_context(source.text, _FINANCIAL_CONTEXT)
        negative_context = self._matching_context(source.text, _NEGATIVE_CONTEXT)
        primary_statement_context = self._primary_statement_context(source.text, intent)
        exact_query = any(match.kind == "exact_query" for match in matches)
        aliases_matched = {match.keyword for match in matches if match.kind == "full_alias"}
        compact_query = "".join(character for character in normalized_query if not character.isspace())
        broad_query = compact_query in {
            "".join(character for character in normalize_for_match(term) if not character.isspace())
            for term in _BROAD_QUERY_TERMS
        }
        breakdown = {
            "exact_query": (0.10 if broad_query else 0.45) if exact_query else 0.0,
            "full_alias": 0.30 if aliases_matched else 0.0,
            "additional_aliases": min(0.10, max(0, len(aliases_matched) - 1) * 0.05),
            "financial_context": 0.15 if financial_context else 0.0,
            # A reconciliation label identifies cash-flow-statement cash, while
            # an appendix/auditor label identifies the primary audited statement.
            "primary_statement_context": 0.25 if primary_statement_context else 0.0,
            "negative_context": -0.35 if negative_context else 0.0,
        }
        score = max(0.0, min(1.0, sum(breakdown.values())))
        if not isfinite(score) or score <= 0.0:
            return None

        best_match = max(matches, key=lambda match: (match.kind == "exact_query", match.end - match.start, -match.start))
        snippet_start = max(0, best_match.start - 450)
        snippet_end = min(len(chunk.text), best_match.end + 450)
        snippet = chunk.text[snippet_start:snippet_end]
        evidence_id = str(uuid5(NAMESPACE_URL, f"{chunk.document_id}|{chunk.chunk_id}|{normalized_query}|{snippet_start}|{snippet_end}"))
        return Evidence(
            evidence_id=evidence_id,
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            page=chunk.page,
            section=chunk.section,
            text=snippet,
            bbox=chunk.bbox,
            source_type=EvidenceSourceType.PROSPECTUS,
            relevance_score=score,
            metadata={
                "retriever": self.name,
                "normalized_query": normalized_query,
                "query_intent": intent,
                "broad_query": broad_query,
                "matched_keywords": sorted({match.keyword for match in matches}),
                "match_type": "exact_query" if exact_query else "full_alias",
                "snippet_start": snippet_start,
                "snippet_end": snippet_end,
                "source_text_length": len(chunk.text),
                "score_breakdown": breakdown,
                "financial_context": financial_context,
                "primary_statement_context": primary_statement_context,
                "negative_context": negative_context,
            },
        )

    @staticmethod
    def _matching_context(normalized_text: str, phrases: tuple[str, ...]) -> list[str]:
        return [phrase for phrase in phrases if normalize_for_match(phrase) in normalized_text]

    @classmethod
    def _primary_statement_context(cls, normalized_text: str, intent: str) -> list[str]:
        if intent == "cash_and_cash_equivalents":
            phrases = _CASH_RECONCILIATION_CONTEXT
        elif intent == "operating_cash_flow":
            phrases = _AUDITED_STATEMENT_CONTEXT
        else:
            return []
        return cls._matching_context(normalized_text, phrases)

    def _matches(
        self,
        source: _NormalizedText,
        compact_source: _NormalizedText,
        normalized_query: str,
        aliases: tuple[str, ...],
    ) -> list[_Match]:
        raw_matches: list[_Match] = []
        terms = [(normalized_query, "exact_query")] + [(normalize_for_match(alias), "full_alias") for alias in aliases]
        seen: set[tuple[int, int, str, str]] = set()
        for term, kind in terms:
            for haystack, mapped_term in ((source, term), (compact_source, "".join(char for char in term if not char.isspace()))):
                for position in _find_all(haystack.text, mapped_term):
                    start = haystack.index_map[position]
                    end = haystack.index_map[position + len(mapped_term) - 1] + 1
                    key = (start, end, term, kind)
                    if key not in seen:
                        seen.add(key)
                        raw_matches.append(_Match(term, start, end, kind))
        return raw_matches
