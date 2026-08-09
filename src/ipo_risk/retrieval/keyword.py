"""Deterministic, explainable prospectus keyword retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
import re
from typing import Iterable
from unicodedata import normalize
from uuid import NAMESPACE_URL, uuid5

from ipo_risk.schemas import DocumentChunk, Evidence, EvidenceSourceType
from ipo_risk.retrieval.query_families import QUERY_FAMILIES, QUERY_FAMILY_BY_NAME


# Keep phrase definitions centralized: the scoring rules must never depend on
# a prospectus name, stock code, or physical page number.
_CASH_ALIASES = (
    "现金及现金等价物", "现金和现金等价物", "现金及银行结余", "银行结余及现金", "现金流量表所述现金及现金等价物",
    "現金及現金等價物", "現金及現金等值物", "現金及銀行結餘", "銀行結餘及現金", "現金流量表所述現金及現金等價物",
    "cash and cash equivalents", "cash equivalents", "cash and bank balances", "bank balances and cash",
    "cash and cash equivalent", "cash and bank balance",
)
_CASH_FLOW_ENDING_ALIASES = (
    "现金流量表期末现金及现金等价物", "年末现金及现金等价物", "期末现金及现金等价物",
    "年末之现金及现金等价物", "期末之现金及现金等价物", "于年末的现金及现金等价物",
    "年期末的现金及现金等价物", "于年期末的现金及现金等价物",
    "于期末的现金及现金等价物", "现金及现金等价物期末余额", "现金及现金等价物的期末结余",
    "現金流量表期末現金及現金等價物", "年末現金及現金等價物", "期末現金及現金等價物",
    "年末之現金及現金等價物", "期末之現金及現金等價物", "於年末的現金及現金等價物",
    "年期末的現金及現金等價物", "於年期末的現金及現金等價物",
    "於期末的現金及現金等價物", "現金及現金等價物期末結餘", "現金及現金等價物的期末結餘",
    "cash and cash equivalents at end of year", "cash and cash equivalents at the end of year",
    "cash and cash equivalents at end of period", "cash and cash equivalents at the end of period",
    "cash and cash equivalents at the end of the reporting period",
    "cash and cash equivalents as stated in the statement of cash flows",
)
_CASH_BALANCE_ALIASES = (
    "现金余额", "现金及现金等价物余额", "現金結餘", "現金及現金等價物結餘",
    "cash balance", "cash and cash equivalents balance",
)
_OPERATING_CASH_FLOW_ALIASES = (
    "经营活动所用净现金流量", "经营活动产生的净现金流量", "经营活动所用现金净额", "经营活动产生的现金净额",
    "经营活动产生所用现金流量净额", "经营活动所用所得现金净额", "经营活动所得所用现金净额",
    "经营活动所用所得现金", "经营活动所得所用现金",
    "经营活动所产生的现金净额", "经营活动所得现金净额",
    "经营活动现金流", "经营活动所用现金", "經營活動所用淨現金流量", "經營活動產生的淨現金流量",
    "經營活動所用現金淨額", "經營活動產生的現金淨額", "經營活動現金流", "經營活動所用現金",
    "經營活動產生所用現金流量淨額", "經營活動所用所得現金淨額", "經營活動所得所用現金淨額",
    "經營活動所用所得現金", "經營活動所得所用現金",
    "經營活動所產生的現金淨額", "經營活動所得現金淨額",
    "經營業務所用現金", "net cash used in operating activities", "net cash generated from operating activities",
    "operating cash flow", "cash flows from operating activities", "net operating cash flow",
)
_FORMAL_CASH_FLOW_TITLES = (
    "綜合現金流量表", "综合现金流量表", "合併現金流量表", "合并现金流量表",
    "現金流量表", "现金流量表", "statement of cash flows", "consolidated statement of cash flows",
    "consolidated cash flow statement", "combined statement of cash flows",
)
_FINANCIAL_CONTEXT = (*_FORMAL_CASH_FLOW_TITLES, "會計師報告", "会计师报告", "财务资料", "財務資料", "人民币千元", "人民幣千元")
_NEGATIVE_CONTEXT = ("主要法律及監管規定概要", "组织章程细则", "組織章程細則概要", "清算", "股东权利", "股東權利")
_CASH_RECONCILIATION_CONTEXT = ("現金流量表所述現金及現金等價物", "现金流量表所述现金及现金等价物")
_AUDITED_STATEMENT_CONTEXT = (
    "附錄一", "附录一", "會計師報告", "会计师报告", "歷史財務資料", "历史财务资料",
    "accountants' report", "accountants’ report", "historical financial information",
)
_SUMMARY_CONTEXT = (
    "概要", "摘要", "財務資料概要", "财务资料摘要", "財務資料概覽", "财务资料概览",
    "流動資金及資本資源", "流动资金及资本资源", "風險因素", "风险因素",
)
_NOTE_CONTEXT = (
    "會計政策", "会计政策", "主要會計政策", "主要会计政策", "信用風險", "信用风险",
    "流動資金風險", "流动资金风险", "現金及銀行結餘", "现金及银行结余", "借款",
)
_CASH_FLOW_BEGINNING_CONTEXT = (
    "年初現金及現金等價物", "期初現金及現金等價物", "於年初的現金及現金等價物",
    "年初现金及现金等价物", "期初现金及现金等价物", "于年初的现金及现金等价物",
    "cash and cash equivalents at beginning of year", "cash and cash equivalents at beginning of period",
)
_CASH_FLOW_CHANGE_CONTEXT = (
    "現金及現金等價物增加", "現金及現金等價物減少", "現金及現金等價物的淨增加",
    "现金及现金等价物增加", "现金及现金等价物减少", "现金及现金等价物净增加",
    "net increase in cash and cash equivalents", "net decrease in cash and cash equivalents",
)
_CASH_FLOW_FX_CONTEXT = (
    "匯率變動對現金及現金等價物", "現金及現金等價物的匯率變動", "現金及現金等價物的匯兌",
    "汇率变动对现金及现金等价物", "现金及现金等价物的汇率变动", "现金及现金等价物的汇兑",
    "effect of exchange rate changes on cash and cash equivalents", "exchange differences on cash and cash equivalents",
)
_BROAD_QUERY_TERMS = ("经营活动", "經營活動", "operating", "activities", "cash")
_SEPARATORS = frozenset("·•….-_—–/╱()（）")


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


@dataclass(frozen=True)
class _PageContext:
    """Document-level features inherited from a nearby formal statement title."""

    statement_distance: int | None = None
    statement_titles: tuple[str, ...] = ()
    audited_context: tuple[str, ...] = ()


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
        page_contexts = self._build_page_contexts(chunks)
        evidence = [
            item
            for chunk in chunks
            if (
                item := self._build_evidence(
                    chunk,
                    query,
                    normalized_query,
                    intent,
                    aliases,
                    page_contexts.get(chunk.chunk_id),
                )
            )
        ]
        evidence.sort(key=lambda item: (-item.relevance_score, item.page or 0, item.chunk_id or "", item.evidence_id))
        return evidence[:limit]

    @staticmethod
    def _resolve_intent(normalized_query: str) -> tuple[str, tuple[str, ...]]:
        compact_query = _compact(_NormalizedText(normalized_query, tuple(range(len(normalized_query))))).text
        normalized_ending_aliases = tuple(normalize_for_match(alias) for alias in _CASH_FLOW_ENDING_ALIASES)
        compact_ending_aliases = {
            "".join(char for char in alias if not char.isspace()) for alias in normalized_ending_aliases
        }
        if compact_query in compact_ending_aliases:
            # The target row may use a concrete reporting date instead of the
            # words "year end" or "period end". Base cash aliases are accepted
            # as candidates, while statement-neighborhood features perform the
            # ranking.
            return "cash_flow_ending_cash", (*_CASH_FLOW_ENDING_ALIASES, *_CASH_ALIASES)
        for intent, aliases in (
            ("cash_balance", _CASH_BALANCE_ALIASES),
            ("cash_and_cash_equivalents", _CASH_ALIASES),
            ("operating_cash_flow", _OPERATING_CASH_FLOW_ALIASES),
        ):
            normalized_aliases = tuple(normalize_for_match(alias) for alias in aliases)
            compact_aliases = {"".join(char for char in alias if not char.isspace()) for alias in normalized_aliases}
            if compact_query in compact_aliases:
                return intent, aliases
        for family in QUERY_FAMILIES:
            family_terms = (family.name, *family.aliases)
            compact_terms = {
                "".join(char for char in normalize_for_match(term) if not char.isspace())
                for term in family_terms
            }
            if compact_query in compact_terms:
                return family.name, family.aliases
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
        page_context: _PageContext | None,
    ) -> Evidence | None:
        normalized_text, index_map = normalize_with_index_map(chunk.text)
        source = _NormalizedText(normalized_text, tuple(index_map))
        compact_source = _compact(source)
        matches = self._matches(source, compact_source, normalized_query, aliases)
        if not matches:
            return None

        financial_context = self._matching_context(source.text, _FINANCIAL_CONTEXT)
        negative_context = self._matching_context(source.text, _NEGATIVE_CONTEXT)
        summary_context = self._matching_context(source.text, _SUMMARY_CONTEXT)
        note_context = self._matching_context(source.text, _NOTE_CONTEXT)
        primary_statement_context = self._primary_statement_context(source.text, intent)
        ending_cash_context = self._matching_context(source.text, _CASH_FLOW_ENDING_ALIASES)
        cash_flow_companions = self._cash_flow_companions(source.text)
        statement_neighborhood = page_context is not None and page_context.statement_distance is not None
        audited_context = list(page_context.audited_context) if page_context else []
        table_context = self._looks_like_financial_table(chunk.text)
        query_family = QUERY_FAMILY_BY_NAME.get(intent)
        domain_context = (
            self._matching_context(source.text, query_family.positive_context)
            if query_family
            else []
        )
        domain_negative_context = (
            self._matching_context(source.text, query_family.negative_context)
            if query_family
            else []
        )
        # PyMuPDF currently emits ``section="unknown"``.  Include visible page
        # headings in the deterministic section signal so real parsed pages can
        # still benefit from preferred/discouraged section weighting.
        normalized_section = normalize_for_match(chunk.section or "")
        section_context_source = f"{normalized_section} {source.text}".strip()
        preferred_section_context = (
            self._matching_context(section_context_source, query_family.preferred_sections)
            if query_family
            else []
        )
        discouraged_section_context = (
            self._matching_context(section_context_source, query_family.discouraged_sections)
            if query_family
            else []
        )
        exact_query = any(match.kind == "exact_query" for match in matches)
        aliases_matched = {match.keyword for match in matches if match.kind == "full_alias"}
        compact_query = "".join(character for character in normalized_query if not character.isspace())
        broad_query = compact_query in {
            "".join(character for character in normalize_for_match(term) if not character.isspace())
            for term in _BROAD_QUERY_TERMS
        }
        if query_family is not None:
            breakdown = {
                "exact_query": 0.24 if exact_query else 0.0,
                "full_alias": 0.24 if aliases_matched else 0.0,
                "additional_aliases": min(0.10, max(0, len(aliases_matched) - 1) * 0.05),
                "domain_context": min(0.24, len(domain_context) * 0.06),
                "preferred_section": 0.18 if preferred_section_context else 0.0,
                "financial_table": (
                    0.10 if query_family.financial_table_weight and table_context else 0.0
                ),
                "discouraged_section": -0.12 if discouraged_section_context else 0.0,
                "domain_negative_context": -0.14 if domain_negative_context else 0.0,
            }
        else:
            breakdown = {
                "exact_query": (0.08 if broad_query else 0.24) if exact_query else 0.0,
                "full_alias": 0.18 if aliases_matched else 0.0,
                "additional_aliases": min(0.08, max(0, len(aliases_matched) - 1) * 0.04),
                "financial_context": 0.08 if financial_context else 0.0,
                "statement_neighborhood": (
                    max(0.20, 0.38 - 0.04 * (page_context.statement_distance or 0))
                    if statement_neighborhood
                    else 0.0
                ),
                "audited_context": 0.12 if audited_context else 0.0,
                "primary_statement_context": 0.18 if primary_statement_context else 0.0,
                "ending_cash_context": 0.24 if ending_cash_context and intent in {"cash_flow_ending_cash", "cash_and_cash_equivalents"} else 0.0,
                "cash_flow_companions": min(0.18, len(cash_flow_companions) * 0.06) if intent in {"cash_flow_ending_cash", "cash_and_cash_equivalents"} else 0.0,
                "table_context": 0.08 if table_context else 0.0,
                "summary_context": -0.28 if summary_context else 0.0,
                "note_context": -0.16 if note_context and not statement_neighborhood else 0.0,
                "negative_context": -0.45 if negative_context else 0.0,
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
                "query_family": query_family.name if query_family else None,
                "broad_query": broad_query,
                "matched_keywords": sorted({match.keyword for match in matches}),
                "match_type": "exact_query" if exact_query else "full_alias",
                "snippet_start": snippet_start,
                "snippet_end": snippet_end,
                "source_text_length": len(chunk.text),
                "score_breakdown": breakdown,
                "financial_context": financial_context,
                "primary_statement_context": primary_statement_context,
                "statement_distance": page_context.statement_distance if page_context else None,
                "statement_titles": list(page_context.statement_titles) if page_context else [],
                "audited_context": audited_context,
                "ending_cash_context": ending_cash_context,
                "cash_flow_companions": cash_flow_companions,
                "table_context": table_context,
                "summary_context": summary_context,
                "note_context": note_context,
                "negative_context": negative_context,
                "domain_context": domain_context,
                "domain_negative_context": domain_negative_context,
                "preferred_section_context": preferred_section_context,
                "discouraged_section_context": discouraged_section_context,
            },
        )

    @staticmethod
    def _matching_context(normalized_text: str, phrases: tuple[str, ...]) -> list[str]:
        return [phrase for phrase in phrases if normalize_for_match(phrase) in normalized_text]

    @classmethod
    def _primary_statement_context(cls, normalized_text: str, intent: str) -> list[str]:
        if intent in {"cash_flow_ending_cash", "cash_and_cash_equivalents"}:
            phrases = (*_CASH_RECONCILIATION_CONTEXT, *_CASH_FLOW_ENDING_ALIASES)
        elif intent == "operating_cash_flow":
            phrases = _AUDITED_STATEMENT_CONTEXT
        else:
            return []
        return cls._matching_context(normalized_text, phrases)

    @classmethod
    def _build_page_contexts(cls, chunks: list[DocumentChunk]) -> dict[str, _PageContext]:
        normalized = {chunk.chunk_id: normalize_for_match(chunk.text) for chunk in chunks}
        title_chunks: dict[str, list[tuple[DocumentChunk, tuple[str, ...], tuple[str, ...]]]] = {}
        for chunk in chunks:
            text = normalized[chunk.chunk_id]
            titles = tuple(cls._matching_context(text, _FORMAL_CASH_FLOW_TITLES))
            if titles:
                audited = tuple(cls._matching_context(text, _AUDITED_STATEMENT_CONTEXT))
                title_chunks.setdefault(chunk.document_id, []).append((chunk, titles, audited))

        contexts: dict[str, _PageContext] = {}
        for chunk in chunks:
            candidates = []
            for title_chunk, titles, audited in title_chunks.get(chunk.document_id, []):
                if chunk.page is None or title_chunk.page is None:
                    continue
                distance = chunk.page - title_chunk.page
                if 0 <= distance <= 4:
                    candidates.append((not bool(audited), distance, title_chunk.page, titles, audited))
            if candidates:
                _, distance, _, titles, audited = min(candidates)
                contexts[chunk.chunk_id] = _PageContext(distance, titles, audited)
        return contexts

    @classmethod
    def _cash_flow_companions(cls, normalized_text: str) -> list[str]:
        groups = (
            ("beginning_cash", _CASH_FLOW_BEGINNING_CONTEXT),
            ("net_change", _CASH_FLOW_CHANGE_CONTEXT),
            ("exchange_effect", _CASH_FLOW_FX_CONTEXT),
            ("ending_cash", _CASH_FLOW_ENDING_ALIASES),
        )
        return [name for name, phrases in groups if cls._matching_context(normalized_text, phrases)]

    @staticmethod
    def _looks_like_financial_table(text: str) -> bool:
        digits = len(re.findall(r"\d", text))
        year_or_date_columns = len(re.findall(r"(?:19|20)\d{2}|\d{1,2}月\d{1,2}日", text))
        units = any(term in normalize_for_match(text) for term in ("人民币千元", "人民幣千元", "港币千元", "港幣千元", "rmb'000", "hk$'000", "usd'000"))
        return digits >= 30 and (year_or_date_columns >= 2 or units)

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
