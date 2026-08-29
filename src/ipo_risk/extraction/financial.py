"""Rule-based extraction of cash values from prospectus evidence."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from ipo_risk.extraction.models import (
    ConcentrationFact,
    ExtractionStatus,
    FinancialExtractionResult,
    FinancialMetricValue,
    FinancialPeriodFact,
    FinancialPeriodSeriesResult,
    V03FinancialExtractionResult,
)
from ipo_risk.schemas import DocumentChunk, Evidence


_NUMBER_BODY = r"(?:\d{1,3}(?:(?:[,，]|\s)\d{3})+|\d+)(?:\.\d+)?"
_AMOUNT_RE = re.compile(
    rf"^\s*(?P<value>(?:\(\s*{_NUMBER_BODY}\s*\)|（\s*{_NUMBER_BODY}\s*）|[+\-−–—]?\s*{_NUMBER_BODY}))\s*$"
)
_EMPTY_AMOUNT_RE = re.compile(r"^\s*[-−–—]\s*$")
_YEAR_RE = re.compile(r"^(20\d{2})\s*年?$", re.IGNORECASE)
_CHINESE_YEAR_RE = re.compile(r"^([〇零一二三四五六七八九]{4})\s*年?$")
_CHINESE_DATE_RE = re.compile(r"(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
_CHINESE_WORD_DATE_RE = re.compile(
    r"([〇零一二三四五六七八九]{4})\s*年\s*"
    r"([一二三四五六七八九十]{1,3})\s*月\s*"
    r"([一二三四五六七八九十]{1,3})\s*日"
)
_ISO_DATE_RE = re.compile(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})")
# A year that is not the head of a full date, i.e. an enumerated fiscal year
# ("於2022年、2023年、2024年以及截至2025年6月30日止六個月").
# A track record can state its span instead of listing it ("截至2021年12月31日止
# 三個年度及2022年首四個月" covers four periods but names one date and one year).
# Counting the named periods there under-counts the series, so a sentence
# carrying a span phrase yields no count at all rather than a wrong one.
_PERIOD_SPAN_PHRASE = re.compile(
    r"[一二三四五六七八九十兩两\d]+\s*[個个](?:財政|财政)?年度"
    r"|(?:two|three|four|five|six)\s+years\s+ended",
    re.I,
)


_NARRATIVE_BARE_YEAR_RE = re.compile(r"(20\d{2})\s*年(?!\s*\d{1,2}\s*月)")
_ENGLISH_DATE_DAY_FIRST_RE = re.compile(
    r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})",
    re.I,
)
_ENGLISH_DATE_MONTH_FIRST_RE = re.compile(
    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(20\d{2})",
    re.I,
)
_MONTH_NAMES = "january february march april may june july august september october november december".split()

_ROW_NUMBER_BODY = r"(?:\d{1,3}(?:[,，]\d{3})+|\d+)(?:\.\d+)?"
_ROW_AMOUNT_TOKEN_RE = re.compile(
    rf"(?:\(\s*{_ROW_NUMBER_BODY}\s*\)|（\s*{_ROW_NUMBER_BODY}\s*）|[+\-−]?\s*{_ROW_NUMBER_BODY}|[-–—])"
)
_NOTE_COLUMN_HEADER_RE = re.compile(r"^(?:附註|附注|註|注|notes?)$", re.I)
_NOTE_REFERENCE_RE = re.compile(r"^[1-9]\d{0,2}$")
_PERCENT_RE = re.compile(
    r"(?P<value>[+\-−]?\s*\d+(?:\s*\.\s*\d+)?)\s*(?:[%％]|per\s+cent|percent)",
    re.I,
)

_V03_LABELS = {
    "net_result": (
        re.compile(r"年[內内][╱／/]期[內内](?:虧損|亏损|溢利)"),
        re.compile(r"年[╱／/]期[內内](?:虧損|亏损|溢利)"),
        re.compile(r"(?:年|期)[內内](?:虧損|亏损|溢利|利潤|利润)"),
        re.compile(r"(?:淨|净)(?:虧損|亏损|利潤|利润)"),
        re.compile(r"本公司[擁拥]有人(?:應佔|应占).*?(?:虧損|亏损|溢利|利潤|利润)"),
        re.compile(r"(?:溢利|利润)[╱／/]（?(?:虧損|亏损)）?"),
        re.compile(r"(?:loss|profit)(?:/loss)? for the (?:year|period)", re.I),
        re.compile(r"(?:loss|profit) attributable to (?:the )?owners", re.I),
        re.compile(r"net (?:loss|profit)", re.I),
    ),
    "revenue": (
        re.compile(r"^(?:收入|收益|營業收入|营业收入|收入總額|收入总额|收益總額|收益总额)(?:\s|$)"),
        re.compile(r"^(?:total revenue|revenue|turnover)(?:\s|$)", re.I),
    ),
}

_EXCLUDED_NET_RESULT_LABELS = re.compile(
    r"經營活動|经营活动|經營虧損|经营亏损|毛利|研發開支|研发开支|綜合開支|综合开支|operating (?:cash|loss)|gross profit|research and development",
    re.I,
)
_EXCLUDED_REVENUE_LABELS = re.compile(
    r"^(?:利息收入|其他收入|政府補助|政府补助|interest income|other income|government grant)",
    re.I,
)
_EXCLUDED_REVENUE_ROWS = re.compile(
    r"^(?:收入|收益|revenue).*?(?:來自|来自|from|產品|产品|客[戶户]|segment|分部|尚未|not yet|has not)",
    re.I,
)

# A hard line wrap splits a label mid-word ("最大客\n戶"), which used to leave the
# label unmatched. An unmatched label does not merely lose its own percentages:
# the preceding label's segment then runs on to the next match, so those
# percentages are silently attributed to the wrong label. Labels are therefore
# matched wrap-tolerantly. The gap is bounded to the one newline a wrap inserts
# plus at most one indent character, because an unbounded gap would let a label
# match across unrelated table cells.
_WRAP = r"\s{0,2}"


def _wrap_tolerant(label: str) -> str:
    """Allow a single hard wrap between any two characters of a fixed label.

    ``label`` is a plain string except for bracketed character classes, which
    are kept intact so simplified/traditional variants stay expressible.
    """
    tokens = re.findall(r"\[[^\]]+\]|.", label)
    return _WRAP.join(tokens)


def _concentration_pattern(chinese: Sequence[str], english: Sequence[str]) -> re.Pattern[str]:
    alternatives = [_wrap_tolerant(item) for item in chinese]
    alternatives += [_WRAP.join(item.split(" ")) for item in english]
    return re.compile("|".join(alternatives), re.I)


# A concentration percentage means nothing without its denominator. A prospectus
# also discloses *balance-sheet* concentration over the same counterparties —
# "最大客戶的貿易應收款項……佔貿易應收款項總額的16.61%" — which is a different
# metric from the revenue or purchase concentration these risk codes rule on.
# Reading both as one series makes two unrelated figures look like contradictory
# readings of the same fact, so a segment whose denominator is a receivable or
# payable balance contributes no values.
_CONCENTRATION_BALANCE_SCOPE = re.compile(
    r"貿易應收款項|贸易应收款项|應收賬款|应收账款|應收款項|应收款项"
    r"|貿易應付款項|贸易应付款项|應付賬款|应付账款|應付款項|应付款项"
    r"|trade\s+receivables?|trade\s+payables?|accounts?\s+receivable|accounts?\s+payable",
    re.I,
)


_CONCENTRATION_LABELS = {
    "customer": {
        "largest": _concentration_pattern(
            ["單一最大客[戶户]", "单一最大客[戶户]", "最大客[戶户]"],
            ["single largest customer", "largest customer"],
        ),
        "top_five": _concentration_pattern(
            ["前五大客[戶户]", "五大客[戶户]"],
            ["five largest customers", "top five customers"],
        ),
    },
    "supplier": {
        "largest": _concentration_pattern(
            ["單一最大供應商", "单一最大供应商", "最大供應商", "最大供应商"],
            ["single largest supplier", "largest supplier"],
        ),
        "top_five": _concentration_pattern(
            ["前五大供應商", "前五大供应商", "五大供應商", "五大供应商"],
            ["five largest suppliers", "top five suppliers"],
        ),
    },
}

_LABELS = {
    "net_result": (
        re.compile(r"年[內内][╱／/]期[內内](?:虧損|亏损|溢利)"),
        re.compile(r"年[╱／/]期[內内](?:虧損|亏损|溢利)"),
        re.compile(r"(?:年|期)[內内](?:虧損|亏损|溢利|利潤|利润)"),
        re.compile(r"(?:淨|净)(?:虧損|亏损|利潤|利润)"),
        re.compile(r"本公司[擁拥]有人(?:應佔|应占).*?(?:虧損|亏损|溢利|利潤|利润)"),
        re.compile(r"(?:溢利|利润)[╱／/]（?(?:虧損|亏损)）?"),
        re.compile(r"(?:loss|profit)(?:/loss)? for the (?:year|period)", re.I),
        re.compile(r"(?:loss|profit) attributable to (?:the )?owners", re.I),
        re.compile(r"net (?:loss|profit)", re.I),
    ),
    "revenue": (
        re.compile(r"^(?:收入|收益|營業收入|营业收入|收入總額|收入总额|收益總額|收益总额)(?:\s|$)"),
        re.compile(r"^(?:total revenue|revenue|turnover)(?:\s|$)", re.I),
    ),
}

_EXCLUDED_NET_RESULT_LABELS = re.compile(
    r"經營活動|经营活动|經營虧損|经营亏损|毛利|研發開支|研发开支|綜合開支|综合开支|operating (?:cash|loss)|gross profit|research and development",
    re.I,
)
_EXCLUDED_REVENUE_LABELS = re.compile(
    r"^(?:利息收入|其他收入|政府補助|政府补助|interest income|other income|government grant)",
    re.I,
)
_EXCLUDED_REVENUE_ROWS = re.compile(
    r"^(?:收入|收益|revenue).*?(?:來自|来自|from|產品|产品|客[戶户]|segment|分部|尚未|not yet|has not)",
    re.I,
)

_LABELS = {
    "cash_and_cash_equivalents": (
        re.compile(r"現金流量表所述現金及現金等價物"),
        re.compile(r"现金流量表所述现金及现金等价物"),
        re.compile(r"(?:年末|期末|於年末|於期末).*?現金及現金等價物"),
        re.compile(r"(?:年末|期末|于年末|于期末).*?现金及现金等价物"),
        re.compile(r"cash and cash equivalents (?:at|as at) (?:the )?end of (?:the )?(?:year|period)", re.I),
        re.compile(r"cash and cash equivalents as stated in the statement of cash flows", re.I),
    ),
    "operating_cash_flow": (
        re.compile(r"經營活動(?:所用|所得|產生|使用)?(?:之)?淨現金(?:流量)?"),
        re.compile(r"经营活动(?:所用|所得|产生|使用)?(?:之)?净现金(?:流量)?"),
        re.compile(
            r"經營(?:活動)?(?:所得|所用|產生|使用)"
            r"(?:\s*[╱／/]\s*[（(]?(?:所得|所用|產生|使用)[）)]?)?"
            r"\s*現金淨額"
        ),
        re.compile(
            r"经营(?:活动)?(?:所得|所用|产生|使用)"
            r"(?:\s*[╱／/]\s*[（(]?(?:所得|所用|产生|使用)[）)]?)?"
            r"\s*现金净额"
        ),
        re.compile(r"net cash (?:used in|generated from|from) operating activities", re.I),
        re.compile(r"net cash flows? (?:used in|generated from) operating activities", re.I),
    ),
}


@dataclass(frozen=True)
class _Period:
    end: date
    months: int | None


@dataclass
class _Candidate:
    result: FinancialMetricValue
    rank: int
    relevance: float
    intent_priority: int
    context_strength: int
    source_table_rows: int


@dataclass
class _CurrencyUnitResolution:
    currency: str | None
    unit: str | None
    currency_source: DocumentChunk | None
    unit_source: DocumentChunk | None
    issues: list[str]
    reviewed_context: list[DocumentChunk]


class FinancialEvidenceExtractor:
    """Extract two financial metrics without LLMs or company-specific rules."""

    def extract(
        self,
        cash_evidence_candidates: Sequence[Evidence],
        operating_cash_flow_candidates: Sequence[Evidence],
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> FinancialExtractionResult:
        """Extract the latest complete value for cash and operating cash flow."""

        cash = self._extract_metric(
            "cash_and_cash_equivalents", cash_evidence_candidates, chunks_by_id
        )
        cash_flow = self._extract_metric(
            "operating_cash_flow", operating_cash_flow_candidates, chunks_by_id
        )
        compatible = self._latest_compatible_pair(
            cash_evidence_candidates,
            operating_cash_flow_candidates,
            chunks_by_id,
        )
        if compatible is not None:
            cash, cash_flow = compatible
        return FinancialExtractionResult(
            cash_and_cash_equivalents=cash,
            operating_cash_flow=cash_flow,
        )

    def _extract_metric(
        self,
        metric_name: str,
        evidence_candidates: Sequence[Evidence],
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> FinancialMetricValue:
        candidates: list[_Candidate] = []
        for rank, evidence in enumerate(evidence_candidates[:20]):
            result = self._extract_candidate(metric_name, evidence, chunks_by_id)
            if result.status != ExtractionStatus.NOT_FOUND:
                intent_priority = self._intent_priority(metric_name, evidence)
                if intent_priority == 2:
                    result.issues.append("unexpected_query_intent")
                    if result.status == ExtractionStatus.EXTRACTED:
                        result.status = ExtractionStatus.NEEDS_REVIEW
                candidates.append(
                    _Candidate(
                        result,
                        rank,
                        evidence.relevance_score,
                        intent_priority,
                        self._context_strength(evidence),
                        self._source_table_rows(evidence, chunks_by_id),
                    )
                )

        if not candidates:
            return FinancialMetricValue(
                metric_name=metric_name,
                status=ExtractionStatus.NOT_FOUND,
                issues=["bounded_evidence_contains_no_supported_target_row"],
            )

        candidates.sort(key=self._candidate_sort_key)
        chosen_candidate = candidates[0]
        chosen = chosen_candidate.result
        conflict_records: list[dict[str, object]] = []
        conflict_issue_codes: set[str] = set()
        for item in candidates[1:]:
            if (
                item.intent_priority != chosen_candidate.intent_priority
                or item.result.period_end != chosen.period_end
            ):
                continue
            conflict_fields = self._financial_fact_conflicts(chosen, item.result)
            if not conflict_fields:
                continue
            conflict_records.append(
                {
                    **self._candidate_summary(item, selected=False),
                    "conflict_fields": conflict_fields,
                }
            )
            conflict_issue_codes.update(
                {
                    "normalized_value": "conflicting_values_for_same_period",
                    "currency": "conflicting_currency_for_same_period",
                    "unit": "conflicting_unit_for_same_period",
                    "period_months": "conflicting_period_length_for_same_date",
                }[field]
                for field in conflict_fields
            )
        if conflict_records:
            chosen.status = ExtractionStatus.NEEDS_REVIEW
            chosen.issues.extend(sorted(conflict_issue_codes))
            chosen.metadata["conflicting_candidates"] = conflict_records

        older_extracted = any(
            item.intent_priority == chosen_candidate.intent_priority
            and item.result.status == ExtractionStatus.EXTRACTED
            and item.result.period_end is not None
            and chosen.period_end is not None
            and item.result.period_end < chosen.period_end
            for item in candidates[1:]
        )
        if chosen.status == ExtractionStatus.NEEDS_REVIEW and older_extracted:
            chosen.issues.append("newer_period_candidate_unresolved")
            chosen.metadata["selection_reason"] = "latest_period_candidate_requires_review"
        elif chosen.period_end is not None:
            chosen.metadata["selection_reason"] = "latest_supported_period"
        else:
            chosen.metadata["selection_reason"] = "best_supported_candidate_without_period"

        chosen.issues = list(dict.fromkeys(chosen.issues))
        chosen.metadata["evaluated_candidates"] = [
            self._candidate_summary(item, selected=item is chosen_candidate)
            for item in candidates
        ]
        chosen.metadata["evaluated_candidate_count"] = len(candidates)
        return chosen

    def _latest_compatible_pair(
        self,
        cash_evidence_candidates: Sequence[Evidence],
        operating_cash_flow_candidates: Sequence[Evidence],
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> tuple[FinancialMetricValue, FinancialMetricValue] | None:
        """Select the latest clean cash/OCF pair sharing governed semantics.

        Cash is a point-in-time balance while OCF is an interval.  Selecting
        each independently can combine two different reporting dates.  This
        method searches the already-retrieved bounded pool for the latest
        common date with matching document, currency and unit.  It does not
        infer a missing field or weaken conflict checks.
        """

        def collect(
            metric_name: str, evidence_candidates: Sequence[Evidence]
        ) -> list[_Candidate]:
            collected: list[_Candidate] = []
            for rank, evidence in enumerate(evidence_candidates[:20]):
                result = self._extract_candidate(metric_name, evidence, chunks_by_id)
                priority = self._intent_priority(metric_name, evidence)
                if result.status != ExtractionStatus.EXTRACTED or priority > 1:
                    continue
                collected.append(
                    _Candidate(
                        result=result,
                        rank=rank,
                        relevance=evidence.relevance_score,
                        intent_priority=priority,
                        context_strength=self._context_strength(evidence),
                        source_table_rows=self._source_table_rows(
                            evidence, chunks_by_id
                        ),
                    )
                )
            return collected

        cash_candidates = collect(
            "cash_and_cash_equivalents", cash_evidence_candidates
        )
        flow_candidates = collect(
            "operating_cash_flow", operating_cash_flow_candidates
        )
        pairs: list[tuple[_Candidate, _Candidate]] = []
        for cash in cash_candidates:
            for flow in flow_candidates:
                cash_value = cash.result
                flow_value = flow.result
                if (
                    cash_value.period_end is None
                    or cash_value.period_end != flow_value.period_end
                    or cash_value.document_id != flow_value.document_id
                    or cash_value.currency is None
                    or cash_value.currency != flow_value.currency
                    or cash_value.unit is None
                    or cash_value.unit != flow_value.unit
                    or flow_value.period_months not in range(1, 13)
                ):
                    continue
                pairs.append((cash, flow))
        if not pairs:
            return None

        pairs.sort(
            key=lambda pair: (
                -pair[0].result.period_end.toordinal(),
                pair[0].intent_priority + pair[1].intent_priority,
                -pair[0].source_table_rows - pair[1].source_table_rows,
                pair[0].rank + pair[1].rank,
                -pair[0].context_strength - pair[1].context_strength,
                -pair[0].relevance - pair[1].relevance,
            )
        )
        selected_cash, selected_flow = pairs[0]

        # Multiple clean readings for the selected date must agree.  A latest
        # compatible pair is not permission to hide a genuine disclosure
        # conflict.
        for selected, candidates in (
            (selected_cash, cash_candidates),
            (selected_flow, flow_candidates),
        ):
            for candidate in candidates:
                if (
                    candidate is selected
                    or candidate.result.period_end != selected.result.period_end
                ):
                    continue
                if self._financial_fact_conflicts(selected.result, candidate.result):
                    return None

        pair_metadata = {
            "pair_selection": "latest_common_compatible_period",
            "compatible_pair_count": len(pairs),
            "pair_period_end": selected_cash.result.period_end.isoformat(),
        }
        cash_result = selected_cash.result.model_copy(
            update={"metadata": {**selected_cash.result.metadata, **pair_metadata}}
        )
        flow_result = selected_flow.result.model_copy(
            update={"metadata": {**selected_flow.result.metadata, **pair_metadata}}
        )
        return cash_result, flow_result

    @staticmethod
    def _candidate_sort_key(candidate: _Candidate) -> tuple[object, ...]:
        value = candidate.result
        status_order = {
            ExtractionStatus.EXTRACTED: 0,
            ExtractionStatus.NEEDS_REVIEW: 1,
            ExtractionStatus.NOT_FOUND: 2,
        }
        return (
            candidate.intent_priority,
            -(value.period_end.toordinal() if value.period_end else 0),
            status_order[value.status],
            -candidate.context_strength,
            -candidate.relevance,
            candidate.rank,
            value.page or 0,
            value.evidence_id or "",
        )

    @staticmethod
    def _candidate_summary(candidate: _Candidate, *, selected: bool) -> dict[str, object]:
        value = candidate.result
        return {
            "evidence_id": value.evidence_id,
            "page": value.page,
            "query_intent": value.metadata.get("query_intent"),
            "status": value.status.value,
            "period_end": value.period_end.isoformat() if value.period_end else None,
            "period_months": value.period_months,
            "raw_value": value.raw_value,
            "normalized_value": str(value.normalized_value) if value.normalized_value is not None else None,
            "currency": value.currency,
            "unit": value.unit,
            "extraction_method": value.extraction_method,
            "relevance_score": candidate.relevance,
            "context_strength": candidate.context_strength,
            "source_table_rows": candidate.source_table_rows,
            "selected": selected,
        }

    @staticmethod
    def _financial_fact_conflicts(
        first: FinancialMetricValue, second: FinancialMetricValue
    ) -> list[str]:
        conflicts: list[str] = []
        for field in ("normalized_value", "currency", "unit", "period_months"):
            first_value = getattr(first, field)
            second_value = getattr(second, field)
            if first_value is not None and second_value is not None and first_value != second_value:
                conflicts.append(field)
        return conflicts

    @staticmethod
    def _intent_priority(metric_name: str, evidence: Evidence) -> int:
        expected = {
            "cash_and_cash_equivalents": "cash_flow_ending_cash",
            "operating_cash_flow": "operating_cash_flow",
        }[metric_name]
        actual = evidence.metadata.get("query_intent")
        if actual == expected:
            return 0
        if actual == "cash_runway":
            # The v0.4.6 retriever deliberately returns one shared, bounded
            # candidate pool for both metrics.  It is a valid neutral intent,
            # not evidence that a cash row was queried as OCF (or vice versa).
            return 1
        return 1 if not actual else 2

    @staticmethod
    def _context_strength(evidence: Evidence) -> int:
        fields = (
            "audited_context",
            "primary_statement_context",
            "ending_cash_context",
            "cash_flow_companions",
            "table_context",
        )
        return sum(bool(evidence.metadata.get(field)) for field in fields)

    @staticmethod
    def _source_table_rows(
        evidence: Evidence,
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> int:
        """Return the largest parser-proven table row count for the source.

        Prospectus summaries commonly repeat a subset of a financial statement.
        When two clean candidates disclose the same metric, period, currency,
        unit and value, the more complete source table is the stronger Evidence
        binding.  This signal is parser provenance only; it contains no issuer,
        page, case, or Gold identity.
        """

        chunk = chunks_by_id.get(evidence.chunk_id or "")
        if chunk is None:
            return 0
        tables = chunk.metadata.get("tables")
        if not isinstance(tables, Sequence) or isinstance(tables, (str, bytes)):
            return 0
        counts = [
            int(table.get("n_rows") or 0)
            for table in tables
            if isinstance(table, Mapping)
            and isinstance(table.get("n_rows"), int)
            and not isinstance(table.get("n_rows"), bool)
        ]
        return max(counts, default=0)

    def _extract_candidate(
        self,
        metric_name: str,
        evidence: Evidence,
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> FinancialMetricValue:
        chunk = chunks_by_id.get(evidence.chunk_id or "")
        if chunk is None:
            return FinancialMetricValue(
                metric_name=metric_name,
                evidence_id=evidence.evidence_id,
                document_id=evidence.document_id,
                chunk_id=evidence.chunk_id,
                page=evidence.page,
                status=ExtractionStatus.NEEDS_REVIEW,
                issues=["source_chunk_not_available"],
            )

        mismatch_fields = [
            field
            for field in ("chunk_id", "document_id", "page")
            if getattr(evidence, field) != getattr(chunk, field)
        ]
        if mismatch_fields:
            return FinancialMetricValue(
                metric_name=metric_name,
                evidence_id=evidence.evidence_id,
                document_id=evidence.document_id,
                chunk_id=evidence.chunk_id,
                page=evidence.page,
                status=ExtractionStatus.NEEDS_REVIEW,
                issues=["evidence_chunk_identity_mismatch"],
                metadata={
                    "evidence_identity": {
                        "document_id": evidence.document_id,
                        "chunk_id": evidence.chunk_id,
                        "page": evidence.page,
                    },
                    "chunk_identity": {
                        "document_id": chunk.document_id,
                        "chunk_id": chunk.chunk_id,
                        "page": chunk.page,
                    },
                    "mismatch_fields": mismatch_fields,
                },
            )

        lines = [line.strip() for line in chunk.text.splitlines() if line.strip()]
        label_index, raw_label = self._find_label(lines, metric_name)
        if label_index is None:
            return FinancialMetricValue(
                metric_name=metric_name,
                evidence_id=evidence.evidence_id,
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                page=chunk.page,
                status=ExtractionStatus.NOT_FOUND,
                issues=["supported_target_label_not_found"],
            )

        raw_values: list[str] = []
        for line in lines[label_index + 1 :]:
            if _EMPTY_AMOUNT_RE.fullmatch(line):
                raw_values.append(line)
                continue
            if _AMOUNT_RE.fullmatch(line):
                raw_values.append(line)
                continue
            break

        issues: list[str] = []
        context_chunks = self._context_chunks(chunk, chunks_by_id)
        field_sources: dict[str, str] = {"label": chunk.chunk_id, "value": chunk.chunk_id}

        currency_unit = self._find_currency_unit(chunk, context_chunks)
        currency = currency_unit.currency
        unit = currency_unit.unit
        issues.extend(currency_unit.issues)
        if currency_unit.currency_source:
            field_sources["currency"] = currency_unit.currency_source.chunk_id
        if currency_unit.unit_source:
            field_sources["unit"] = currency_unit.unit_source.chunk_id
        if currency is None:
            issues.append("currency_missing_or_ambiguous")
        if unit is None:
            issues.append("unit_missing_or_ambiguous")

        periods, period_source, period_issues = self._find_periods(
            lines[:label_index], chunk, context_chunks
        )
        issues.extend(period_issues)
        if period_source:
            field_sources["period"] = period_source.chunk_id
        ignored_note_reference = None
        if (
            periods
            and len(raw_values) == len(periods) + 1
            and any(_NOTE_COLUMN_HEADER_RE.fullmatch(line) for line in lines[:label_index])
            and _NOTE_REFERENCE_RE.fullmatch(raw_values[0])
        ):
            # HK prospectus statements commonly flatten the ``Notes`` column
            # onto its own line immediately before the period values.  It is a
            # row reference, not an extra financial observation.  Remove it
            # only when one explicit Notes header and an exact N+1 shape prove
            # the column relationship; every other mismatch remains fail-closed.
            ignored_note_reference = raw_values[0]
            raw_values = raw_values[1:]
        numeric_values = [(raw, self._normalize_amount(raw)) for raw in raw_values]
        valid_values = [(raw, value) for raw, value in numeric_values if value is not None]
        if not raw_values:
            issues.append("target_row_has_no_values")
        if len(periods) != len(raw_values):
            issues.append("period_value_column_count_mismatch")
        if not periods:
            issues.append("period_header_missing_or_ambiguous")

        selected_raw = ""
        selected_value: Decimal | None = None
        selected_period: _Period | None = None
        if periods and len(periods) == len(raw_values):
            complete = [
                (period, raw, value)
                for period, (raw, value) in zip(periods, numeric_values, strict=True)
                if value is not None
            ]
            if complete:
                selected_period, selected_raw, selected_value = max(
                    complete, key=lambda item: item[0].end
                )
        elif len(valid_values) == 1 and len(periods) == 1:
            selected_period = periods[0]
            selected_raw, selected_value = valid_values[0]

        if selected_value is None:
            issues.append("latest_complete_value_not_determinable")
        if metric_name == "operating_cash_flow" and (
            selected_period is None or selected_period.months not in range(1, 13)
        ):
            issues.append("operating_cash_flow_period_months_missing")

        context_used = {chunk.chunk_id: chunk}
        for source in (
            currency_unit.currency_source,
            currency_unit.unit_source,
            period_source,
            *currency_unit.reviewed_context,
        ):
            if source is not None:
                context_used[source.chunk_id] = source
        status = ExtractionStatus.EXTRACTED if not issues else ExtractionStatus.NEEDS_REVIEW
        return FinancialMetricValue(
            metric_name=metric_name,
            raw_label=raw_label,
            raw_value=selected_raw,
            normalized_value=selected_value,
            currency=currency,
            unit=unit,
            period_end=selected_period.end if selected_period else None,
            period_months=(
                selected_period.months
                if selected_period and metric_name == "operating_cash_flow"
                else None
            ),
            evidence_id=evidence.evidence_id,
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            page=chunk.page,
            status=status,
            issues=list(dict.fromkeys(issues)),
            context_chunk_ids=list(context_used),
            context_pages=sorted({item.page for item in context_used.values()}),
            extraction_method=(
                "page_text_with_adjacent_context"
                if len(context_used) > 1
                else "page_text_rule"
            ),
            metadata={
                "field_sources": field_sources,
                "row_values": raw_values,
                "period_candidates": [
                    {"period_end": item.end.isoformat(), "period_months": item.months}
                    for item in periods
                ],
                "ignored_note_reference": ignored_note_reference,
                "query_intent": evidence.metadata.get("query_intent"),
            },
        )

    @staticmethod
    def _find_label(lines: Sequence[str], metric_name: str) -> tuple[int | None, str]:
        # Pattern priority is intentional: a cash-flow reconciliation row must
        # beat an earlier, broader ending-cash row that may include a note column.
        for pattern in _LABELS[metric_name]:
            for index, line in enumerate(lines):
                match = pattern.search(line)
                if match:
                    return index, match.group(0)
        return None, ""

    @staticmethod
    def _normalize_amount(raw: str) -> Decimal | None:
        if _EMPTY_AMOUNT_RE.fullmatch(raw):
            return None
        match = _AMOUNT_RE.fullmatch(raw)
        if not match:
            return None
        token = match.group("value").strip().replace("，", ",")
        negative_parentheses = token.startswith(("(", "（")) and token.endswith((")", "）"))
        token = token.strip("()（） ").replace(",", "").replace("−", "-").replace("–", "-").replace("—", "-")
        try:
            value = Decimal(token.replace(" ", ""))
        except InvalidOperation:
            return None
        return -abs(value) if negative_parentheses else value

    @staticmethod
    def _context_chunks(
        target: DocumentChunk, chunks_by_id: Mapping[str, DocumentChunk]
    ) -> list[DocumentChunk]:
        return sorted(
            (
                chunk
                for chunk in chunks_by_id.values()
                if chunk.document_id == target.document_id
                and chunk.chunk_id != target.chunk_id
                and abs(chunk.page - target.page) <= 1
            ),
            key=lambda item: (abs(item.page - target.page), item.page, item.chunk_id),
        )

    @staticmethod
    def _currency_unit_candidates(text: str) -> tuple[set[str], set[str]]:
        currencies = set()
        if re.search(r"人民幣|人民币|\bRMB\b|\bCNY\b", text, re.I):
            currencies.add("CNY")
        if re.search(r"港元|港幣|港币|HK\$|\bHKD\b", text, re.I):
            currencies.add("HKD")
        if re.search(r"美元|US\$|\bUSD\b", text, re.I):
            currencies.add("USD")

        units = set()
        if re.search(r"千元|['’]000|\bthousand\b", text, re.I):
            units.add("thousand")
        if re.search(r"(?<!百)(?:萬元|万元)", text):
            units.add("ten_thousand")
        if re.search(r"百萬元|百万元|\bmillion\b", text, re.I):
            units.add("million")
        text_without_scaled_units = re.sub(
            r"千元|萬元|万元|百萬元|百万元|人民幣|人民币|港元|港幣|港币|美元|HK\$|US\$|\bRMB\b|\bCNY\b|\bHKD\b|\bUSD\b",
            "",
            text,
            flags=re.I,
        )
        if re.search(r"(?<!千)(?<!萬)(?<!万)(?<!百)元|\bunit\b", text_without_scaled_units, re.I):
            units.add("unit")
        return currencies, units

    @classmethod
    def _detect_currency_unit(cls, text: str) -> tuple[str | None, str | None]:
        currencies, units = cls._currency_unit_candidates(text)
        return (
            next(iter(currencies)) if len(currencies) == 1 else None,
            next(iter(units)) if len(units) == 1 else None,
        )

    def _find_currency_unit(
        self, target: DocumentChunk, context: Sequence[DocumentChunk]
    ) -> _CurrencyUnitResolution:
        target_currencies, target_units = self._currency_unit_candidates(target.text)
        currency = next(iter(target_currencies)) if len(target_currencies) == 1 else None
        unit = next(iter(target_units)) if len(target_units) == 1 else None
        issues: list[str] = []
        if len(target_currencies) > 1:
            issues.append("target_currency_ambiguous")
        if len(target_units) > 1:
            issues.append("target_unit_ambiguous")
        currency_source = target if currency is not None else None
        unit_source = target if unit is not None else None
        if currency is not None and unit is not None:
            return _CurrencyUnitResolution(currency, unit, target, target, issues, [])
        if len(target_currencies) > 1 or len(target_units) > 1:
            return _CurrencyUnitResolution(currency, unit, currency_source, unit_source, issues, [])

        resolutions: list[tuple[str, str, DocumentChunk, DocumentChunk]] = []
        reviewed_context: list[DocumentChunk] = []
        for chunk in context:
            other_currencies, other_units = self._currency_unit_candidates(chunk.text)
            if other_currencies or other_units:
                reviewed_context.append(chunk)
            if len(other_currencies) > 1:
                issues.append("context_currency_ambiguous")
                continue
            if len(other_units) > 1:
                issues.append("context_unit_ambiguous")
                continue
            other_currency = next(iter(other_currencies)) if other_currencies else None
            other_unit = next(iter(other_units)) if other_units else None
            if currency and other_currency and currency != other_currency:
                issues.append("context_currency_conflict")
                continue
            if unit and other_unit and unit != other_unit:
                issues.append("context_unit_conflict")
                continue
            candidate_currency = currency or other_currency
            candidate_unit = unit or other_unit
            if candidate_currency is not None and candidate_unit is not None:
                resolutions.append(
                    (
                        candidate_currency,
                        candidate_unit,
                        currency_source or chunk,
                        unit_source or chunk,
                    )
                )

        unique_pairs = {(item[0], item[1]) for item in resolutions}
        if len(unique_pairs) > 1:
            issues.append("context_currency_unit_conflict")
            return _CurrencyUnitResolution(
                currency, unit, currency_source, unit_source, issues, reviewed_context
            )
        if resolutions:
            resolved_currency, resolved_unit, resolved_currency_source, resolved_unit_source = resolutions[0]
            return _CurrencyUnitResolution(
                resolved_currency,
                resolved_unit,
                resolved_currency_source,
                resolved_unit_source,
                list(dict.fromkeys(issues)),
                reviewed_context,
            )
        return _CurrencyUnitResolution(
            currency,
            unit,
            currency_source,
            unit_source,
            list(dict.fromkeys(issues)),
            reviewed_context,
        )

    def _find_periods(
        self,
        header_lines: Sequence[str],
        target: DocumentChunk,
        context: Sequence[DocumentChunk],
    ) -> tuple[list[_Period], DocumentChunk | None, list[str]]:
        periods, issues = self._parse_periods(header_lines)
        if periods:
            return periods, target, issues
        if issues:
            return [], target, issues
        for chunk in context:
            periods, issues = self._parse_periods(
                [line.strip() for line in chunk.text.splitlines() if line.strip()]
            )
            if periods:
                return periods, chunk, issues
            if issues:
                return [], chunk, issues
        return [], None, []

    def _parse_periods(self, lines: Sequence[str]) -> tuple[list[_Period], list[str]]:
        explicit: list[_Period] = []
        for line in lines:
            dates = self._explicit_dates(line)
            if len(dates) <= 1:
                explicit.extend(_Period(item, self._period_months(line)) for item in dates)
                continue

            clauses = re.split(r"\s*(?:以及|及|與|和|；|;|\band\b)\s*", line, flags=re.I)
            clause_periods: list[_Period] = []
            for clause in clauses:
                clause_dates = self._explicit_dates(clause)
                if not clause_dates:
                    continue
                if len(clause_dates) != 1:
                    return [], ["mixed_period_header_ambiguous"]
                clause_periods.append(_Period(clause_dates[0], self._period_months(clause)))
            if len(clause_periods) != len(dates):
                return [], ["mixed_period_header_ambiguous"]
            months = [item.months for item in clause_periods]
            if any(item is None for item in months) and any(item is not None for item in months):
                return [], ["mixed_period_header_ambiguous"]
            explicit.extend(clause_periods)
        if explicit:
            return self._dedupe_periods(explicit), []

        years = [year for line in lines if (year := self._year_value(line)) is not None]
        groups = [
            (self._month_day(line), self._period_months(line))
            for line in lines
            if self._is_period_group(line)
        ]
        if not years or not groups:
            return [], []
        if any(month_day is None for month_day, _ in groups):
            return [], []

        counts = self._column_group_counts(years, len(groups))
        if not counts:
            return [], []
        result: list[_Period] = []
        offset = 0
        for (month_day, months), count in zip(groups, counts, strict=True):
            if month_day is None:
                return [], []
            month, day = month_day
            for year in years[offset : offset + count]:
                try:
                    result.append(_Period(date(year, month, day), months))
                except ValueError:
                    return [], []
            offset += count
        return (result, []) if offset == len(years) else ([], [])

    @staticmethod
    def _explicit_dates(text: str) -> list[date]:
        matches: list[tuple[int, date]] = []
        for pattern in (_CHINESE_DATE_RE, _ISO_DATE_RE):
            for match in pattern.finditer(text):
                try:
                    matches.append(
                        (
                            match.start(),
                            date(int(match.group(1)), int(match.group(2)), int(match.group(3))),
                        )
                    )
                except ValueError:
                    pass
        for match in _CHINESE_WORD_DATE_RE.finditer(text):
            try:
                year = FinancialEvidenceExtractor._year_value(match.group(1))
                month = FinancialEvidenceExtractor._chinese_integer(match.group(2))
                day = FinancialEvidenceExtractor._chinese_integer(match.group(3))
                if year is not None and month is not None and day is not None:
                    matches.append((match.start(), date(year, month, day)))
            except ValueError:
                pass
        for match in _ENGLISH_DATE_DAY_FIRST_RE.finditer(text):
            try:
                matches.append(
                    (
                        match.start(),
                        date(
                            int(match.group(3)),
                            _MONTH_NAMES.index(match.group(2).lower()) + 1,
                            int(match.group(1)),
                        ),
                    )
                )
            except ValueError:
                pass
        for match in _ENGLISH_DATE_MONTH_FIRST_RE.finditer(text):
            try:
                matches.append(
                    (
                        match.start(),
                        date(
                            int(match.group(3)),
                            _MONTH_NAMES.index(match.group(1).lower()) + 1,
                            int(match.group(2)),
                        ),
                    )
                )
            except ValueError:
                pass
        return [item for _, item in sorted(matches, key=lambda match: match[0])]

    @staticmethod
    def _is_period_group(line: str) -> bool:
        return bool(
            re.search(r"截至.*(?:止|ended)", line, re.I)
            or re.search(r"(?:year|months?).*ended", line, re.I)
        )

    @staticmethod
    def _month_day(line: str) -> tuple[int, int] | None:
        match = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日", line)
        if match:
            return int(match.group(1)), int(match.group(2))
        chinese = re.search(
            r"([一二三四五六七八九十]{1,3})\s*月\s*"
            r"([一二三四五六七八九十]{1,3})\s*日",
            line,
        )
        if chinese:
            month = FinancialEvidenceExtractor._chinese_integer(chinese.group(1))
            day = FinancialEvidenceExtractor._chinese_integer(chinese.group(2))
            if month is not None and day is not None:
                return month, day
        english = re.search(
            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})",
            line,
            re.I,
        )
        if english:
            return _MONTH_NAMES.index(english.group(1).lower()) + 1, int(english.group(2))
        english_day_first = re.search(
            r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)",
            line,
            re.I,
        )
        if english_day_first:
            return (
                _MONTH_NAMES.index(english_day_first.group(2).lower()) + 1,
                int(english_day_first.group(1)),
            )
        return None

    @staticmethod
    def _chinese_integer(token: str) -> int | None:
        digits = {"〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
                  "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
        if not token:
            return None
        if "十" not in token:
            if any(character not in digits for character in token):
                return None
            value = 0
            for character in token:
                value = value * 10 + digits[character]
            return value
        if token.count("十") != 1:
            return None
        left, right = token.split("十")
        if len(left) > 1 or len(right) > 1:
            return None
        tens = digits.get(left, 1) if left else 1
        ones = digits.get(right, 0) if right else 0
        return tens * 10 + ones

    @staticmethod
    def _year_value(text: str) -> int | None:
        stripped = text.strip()
        match = _YEAR_RE.fullmatch(stripped)
        if match:
            return int(match.group(1))
        chinese = _CHINESE_YEAR_RE.fullmatch(stripped)
        if not chinese:
            return None
        value = FinancialEvidenceExtractor._chinese_integer(chinese.group(1))
        return value if value is not None and 2000 <= value <= 2099 else None

    @staticmethod
    def _period_months(line: str) -> int | None:
        chinese = re.search(
            r"(?:止|為|为|共)\s*([一二三四五六七八九十兩两0-9]+)\s*[個个]?月",
            line,
        )
        if chinese:
            values = {
                "一": 1,
                "二": 2,
                "三": 3,
                "四": 4,
                "五": 5,
                "六": 6,
                "七": 7,
                "八": 8,
                "九": 9,
                "十": 10,
                "十一": 11,
                "十二": 12,
                "兩": 2,
                "两": 2,
            }
            return values.get(chinese.group(1), int(chinese.group(1)) if chinese.group(1).isdigit() else None)
        english = re.search(r"(3|6|9|12|three|six|nine|twelve)\s+months?", line, re.I)
        if english:
            values = {"three": 3, "six": 6, "nine": 9, "twelve": 12}
            return values.get(english.group(1).lower(), int(english.group(1)) if english.group(1).isdigit() else None)
        if re.search(r"年度|year", line, re.I):
            return 12
        return None

    @staticmethod
    def _column_group_counts(years: Sequence[int], group_count: int) -> list[int]:
        column_count = len(years)
        if group_count <= 0 or column_count < group_count:
            return []
        if group_count == 1:
            return [column_count]
        if column_count == group_count:
            return [1] * group_count

        boundaries = [index for index in range(1, column_count) if years[index] == years[index - 1]]
        if len(boundaries) != group_count - 1:
            return []
        points = [0, *boundaries, column_count]
        counts = [points[index + 1] - points[index] for index in range(group_count)]
        return counts if all(count > 0 for count in counts) else []

    @staticmethod
    def _dedupe_periods(periods: Sequence[_Period]) -> list[_Period]:
        result: list[_Period] = []
        seen: set[tuple[date, int | None]] = set()
        for period in periods:
            key = (period.end, period.months)
            if key not in seen:
                seen.add(key)
                result.append(period)
        return result


class V03FinancialFactExtractor(FinancialEvidenceExtractor):
    """Extract typed v0.3 financial facts from already-retrieved evidence."""

    def extract_v03(
        self,
        net_result_candidates: Sequence[Evidence],
        revenue_candidates: Sequence[Evidence],
        customer_concentration_candidates: Sequence[Evidence],
        supplier_concentration_candidates: Sequence[Evidence],
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> V03FinancialExtractionResult:
        """Extract four fact families without retrieval, LLMs, or risk decisions."""

        return V03FinancialExtractionResult(
            net_results=self._extract_period_series(
                "net_result", net_result_candidates, chunks_by_id
            ),
            revenues=self._extract_period_series(
                "revenue", revenue_candidates, chunks_by_id
            ),
            customer_concentration=self._extract_concentration(
                "customer", customer_concentration_candidates, chunks_by_id
            ),
            supplier_concentration=self._extract_concentration(
                "supplier", supplier_concentration_candidates, chunks_by_id
            ),
        )

    def _extract_period_series(
        self,
        metric_name: str,
        evidence_candidates: Sequence[Evidence],
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> FinancialPeriodSeriesResult:
        observations: list[FinancialPeriodFact] = []
        issues: list[str] = []
        known_evidence_ids = self._evidence_ids(evidence_candidates)
        if not evidence_candidates:
            return FinancialPeriodSeriesResult(
                metric_name=metric_name,
                status=ExtractionStatus.NOT_FOUND,
                issues=["evidence_candidates_empty"],
            )

        for evidence in evidence_candidates:
            facts, candidate_issues = self._period_facts_from_evidence(
                metric_name, evidence, chunks_by_id
            )
            observations.extend(facts)
            issues.extend(candidate_issues)

        if not observations:
            return FinancialPeriodSeriesResult(
                metric_name=metric_name,
                status=(
                    ExtractionStatus.NEEDS_REVIEW
                    if issues and any(item != "metric_label_not_found" for item in issues)
                    else ExtractionStatus.NOT_FOUND
                ),
                issues=self._dedupe_strings(issues or ["metric_label_not_found"]),
                evidence_ids=known_evidence_ids,
            )

        issues.extend(issue for item in observations for issue in item.issues)
        conflicts = self._period_fact_conflicts(observations)
        issues.extend(conflicts)
        observations.sort(
            key=lambda item: (
                item.period_end is None,
                item.period_end or date.min,
                item.page or 0,
                item.chunk_id or "",
            )
        )
        status = (
            ExtractionStatus.EXTRACTED
            if not issues
            and all(item.status == ExtractionStatus.EXTRACTED for item in observations)
            else ExtractionStatus.NEEDS_REVIEW
        )
        return FinancialPeriodSeriesResult(
            metric_name=metric_name,
            observations=observations,
            status=status,
            issues=self._dedupe_strings(issues),
            evidence_ids=self._evidence_ids_from_period_facts(observations),
            metadata={
                "observation_count": len(observations),
                "extraction_method": "deterministic_financial_row_v03",
            },
        )

    def _period_facts_from_evidence(
        self,
        metric_name: str,
        evidence: Evidence,
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> tuple[list[FinancialPeriodFact], list[str]]:
        identity_issues = self._evidence_identity_issues(evidence, chunks_by_id)
        if identity_issues:
            return [], identity_issues
        target = chunks_by_id[evidence.chunk_id or ""]
        lines = [line.strip() for line in target.text.splitlines() if line.strip()]
        label_index, raw_label = self._find_v03_label(lines, metric_name)
        if label_index is None:
            return [], ["metric_label_not_found"]

        raw_values = self._row_values(lines, label_index, raw_label)
        if not raw_values:
            return [], ["unsupported_layout"]

        context = self._context_chunks(target, chunks_by_id)
        periods, period_source, period_issues = self._best_v03_periods(
            lines[:label_index], target, context
        )
        issues = list(period_issues)
        if self._review_only_context(evidence, target):
            issues.append("summary_or_risk_context_requires_review")
        if not periods:
            issues.append("missing_period")
        if periods and len(periods) != len(raw_values):
            issues.append("value_period_count_mismatch")

        resolution = self._find_currency_unit(target, context)
        issues.extend(resolution.issues)
        if resolution.currency is None:
            issues.append("missing_currency")
        if resolution.unit is None:
            issues.append("missing_unit")

        context_used = self._dedupe_chunks(
            [
                item
                for item in [
                    period_source if period_source != target else None,
                    resolution.currency_source if resolution.currency_source != target else None,
                    resolution.unit_source if resolution.unit_source != target else None,
                    *resolution.reviewed_context,
                ]
                if item is not None
            ]
        )
        facts: list[FinancialPeriodFact] = []
        for index, raw_value in enumerate(raw_values):
            period = periods[index] if index < len(periods) else None
            value, value_issues, normalization = self._normalize_period_value(
                metric_name, raw_label, raw_value, evidence, target
            )
            fact_issues = list(issues) + value_issues
            if period is not None and period.months is None:
                fact_issues.append("missing_period_months")
            fact_status = (
                ExtractionStatus.EXTRACTED
                if value is not None
                and period is not None
                and period.months is not None
                and resolution.currency is not None
                and resolution.unit is not None
                and not fact_issues
                else ExtractionStatus.NEEDS_REVIEW
            )
            facts.append(
                FinancialPeriodFact(
                    metric_name=metric_name,
                    period_end=period.end if period else None,
                    period_months=period.months if period else None,
                    normalized_value=value,
                    currency=resolution.currency,
                    unit=resolution.unit,
                    evidence_ids=[evidence.evidence_id],
                    document_id=target.document_id,
                    chunk_id=target.chunk_id,
                    page=target.page,
                    raw_label=raw_label,
                    raw_value=raw_value,
                    status=fact_status,
                    issues=self._dedupe_strings(fact_issues),
                    context_chunk_ids=[item.chunk_id for item in context_used],
                    context_pages=self._dedupe_ints([item.page for item in context_used]),
                    metadata={
                        "value_index": index,
                        "normalization": normalization,
                        "source_context": evidence.metadata.get("source_context"),
                        "period_source_chunk_id": period_source.chunk_id if period_source else None,
                        "currency_source_chunk_id": (
                            resolution.currency_source.chunk_id
                            if resolution.currency_source
                            else None
                        ),
                        "unit_source_chunk_id": (
                            resolution.unit_source.chunk_id if resolution.unit_source else None
                        ),
                    },
                )
            )
        return facts, self._dedupe_strings(issues)

    @staticmethod
    def _find_v03_label(lines: Sequence[str], metric_name: str) -> tuple[int | None, str]:
        for index, line in enumerate(lines):
            if metric_name == "net_result" and _EXCLUDED_NET_RESULT_LABELS.search(line):
                continue
            if metric_name == "revenue" and _EXCLUDED_REVENUE_LABELS.search(line):
                continue
            if metric_name == "revenue" and _EXCLUDED_REVENUE_ROWS.search(line):
                continue
            for pattern in _V03_LABELS[metric_name]:
                match = pattern.search(line)
                if match:
                    return index, match.group(0)
        return None, ""

    @staticmethod
    def _row_values(lines: Sequence[str], label_index: int, raw_label: str) -> list[str]:
        row = lines[label_index]
        label_position = row.find(raw_label)
        suffix = row[label_position + len(raw_label) :] if label_position >= 0 else ""
        values = [match.group(0).strip() for match in _ROW_AMOUNT_TOKEN_RE.finditer(suffix)]
        if values and not re.search(r"[,，()]|（|）", suffix):
            grouped: list[str] = []
            index = 0
            while index < len(values):
                if (
                    index + 1 < len(values)
                    and re.fullmatch(r"[+\-−]?\d{1,2}", values[index])
                    and re.fullmatch(r"\d{3}", values[index + 1])
                ):
                    grouped.append(f"{values[index]} {values[index + 1]}")
                    index += 2
                else:
                    grouped.append(values[index])
                    index += 1
            values = grouped
        if values:
            return values
        for line in lines[label_index + 1 :]:
            if _AMOUNT_RE.fullmatch(line) or _EMPTY_AMOUNT_RE.fullmatch(line):
                values.append(line.strip())
                continue
            if values:
                break
        return values

    def _normalize_period_value(
        self,
        metric_name: str,
        raw_label: str,
        raw_value: str,
        evidence: Evidence,
        target: DocumentChunk,
    ) -> tuple[Decimal | None, list[str], str]:
        if _EMPTY_AMOUNT_RE.fullmatch(raw_value):
            if metric_name == "revenue" and self._is_primary_statement(evidence, target):
                return Decimal("0"), [], "formal_revenue_dash_to_zero"
            return None, ["ambiguous_empty_value_symbol"], "dash_unresolved"
        value = self._normalize_amount(raw_value)
        if value is None:
            return None, ["invalid_numeric_value"], "invalid"
        if metric_name == "net_result" and self._loss_only_label(raw_label):
            value = -abs(value)
        return value, [], "decimal_amount"

    @staticmethod
    def _loss_only_label(label: str) -> bool:
        lowered = label.lower()
        has_loss = bool(re.search(r"虧損|亏损|\bloss\b", lowered, re.I))
        has_profit = bool(re.search(r"溢利|利潤|利润|\bprofit\b", lowered, re.I))
        return has_loss and not has_profit

    @staticmethod
    def _is_primary_statement(evidence: Evidence, target: DocumentChunk) -> bool:
        if evidence.metadata.get("primary_statement_context") is True:
            return True
        if target.metadata.get("primary_statement_context") is True:
            return True
        return bool(
            re.search(
                r"財務報表|财务报表|損益表|损益表|全面收益表|auditor.s report|statement of profit or loss",
                f"{target.section}\n{target.text}",
                re.I,
            )
        )

    @staticmethod
    def _review_only_context(evidence: Evidence, target: DocumentChunk) -> bool:
        if evidence.metadata.get("source_context") in {"summary", "risk_factors"}:
            return True
        return bool(
            re.search(
                r"摘要|風險因素|风险因素|\bsummary\b|\brisk factors?\b",
                target.section,
                re.I,
            )
        )

    def _extract_concentration(
        self,
        concentration_type: str,
        evidence_candidates: Sequence[Evidence],
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> ConcentrationFact:
        known_evidence_ids = self._evidence_ids(evidence_candidates)
        if not evidence_candidates:
            return ConcentrationFact(
                concentration_type=concentration_type,
                status=ExtractionStatus.NOT_FOUND,
                issues=["evidence_candidates_empty"],
            )

        facts: list[ConcentrationFact] = []
        issues: list[str] = []
        for evidence in evidence_candidates:
            fact = self._concentration_from_evidence(
                concentration_type, evidence, chunks_by_id
            )
            if fact.status != ExtractionStatus.NOT_FOUND:
                facts.append(fact)
            issues.extend(fact.issues)
        if not facts:
            return ConcentrationFact(
                concentration_type=concentration_type,
                status=(
                    ExtractionStatus.NEEDS_REVIEW
                    if issues and any(item != "concentration_label_not_found" for item in issues)
                    else ExtractionStatus.NOT_FOUND
                ),
                issues=self._dedupe_strings(issues or ["concentration_label_not_found"]),
                evidence_ids=known_evidence_ids,
            )

        return self._merge_concentration_facts(concentration_type, facts)

    def _concentration_from_evidence(
        self,
        concentration_type: str,
        evidence: Evidence,
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> ConcentrationFact:
        identity_issues = self._evidence_identity_issues(evidence, chunks_by_id)
        if identity_issues:
            return ConcentrationFact(
                concentration_type=concentration_type,
                status=ExtractionStatus.NEEDS_REVIEW,
                issues=identity_issues,
                evidence_ids=[evidence.evidence_id],
            )
        target = chunks_by_id[evidence.chunk_id or ""]
        labels = _CONCENTRATION_LABELS[concentration_type]
        matches: list[tuple[int, int, str]] = []
        for name, pattern in labels.items():
            matches.extend((match.start(), match.end(), name) for match in pattern.finditer(target.text))
        matches.sort()
        if not matches:
            return ConcentrationFact(
                concentration_type=concentration_type,
                status=ExtractionStatus.NOT_FOUND,
                issues=["concentration_label_not_found"],
                evidence_ids=[evidence.evidence_id],
            )

        # A percentage belongs to the nearest label above it, whichever kind that
        # label is. Bounding a segment only by the next label of the *same*
        # concentration type let an intervening supplier paragraph donate its
        # percentages to the customer label that preceded it, so both kinds act
        # as boundaries even though only this kind collects values.
        boundaries = sorted(
            match.start()
            for group in _CONCENTRATION_LABELS.values()
            for pattern in group.values()
            for match in pattern.finditer(target.text)
        )

        # Keep repeated label occurrences local.  Prospectuses often state the
        # aggregate track-record series first, then repeat "five largest" above
        # a detail table.  Concatenating both segments lets a row percentage
        # overwrite the aggregate top-five value when the latest value is read.
        occurrence_series: dict[
            str, list[tuple[int, list[Decimal], list[str], int | None, _Period | None]]
        ] = {"largest": [], "top_five": []}
        scope_skipped = False
        for label_start, start_after_label, name in matches:
            end = next(
                (item for item in boundaries if item >= start_after_label), len(target.text)
            )
            segment = target.text[start_after_label:end]
            if self._is_balance_scope_segment(segment):
                scope_skipped = True
                continue
            occurrence_values: list[Decimal] = []
            occurrence_raw: list[str] = []
            for match in _PERCENT_RE.finditer(segment):
                raw = match.group("value").replace("−", "-").replace(" ", "")
                try:
                    value = Decimal(raw)
                except InvalidOperation:
                    continue
                occurrence_values.append(value)
                occurrence_raw.append(match.group(0))
            if occurrence_values:
                occurrence_series[name].append(
                    (
                        label_start,
                        occurrence_values,
                        occurrence_raw,
                        self._enumerated_period_count(target.text, label_start),
                        self._label_local_period(target.text, label_start),
                    )
                )

        context = self._context_chunks(target, chunks_by_id)
        periods, period_source, period_issues = self._best_v03_periods(
            [line.strip() for line in target.text.splitlines() if line.strip()],
            target,
            context,
        )
        values: dict[str, list[Decimal]] = {"largest": [], "top_five": []}
        raw_percentages: dict[str, list[str]] = {"largest": [], "top_five": []}
        selected_enumerated_counts: dict[str, int | None] = {
            "largest": None,
            "top_five": None,
        }
        occurrence_diagnostics: dict[str, list[dict[str, object]]] = {
            "largest": [],
            "top_five": [],
        }
        occurrence_selection: dict[str, str | None] = {
            "largest": None,
            "top_five": None,
        }
        selected_local_periods: dict[str, _Period | None] = {
            "largest": None,
            "top_five": None,
        }
        selected_label_starts: dict[str, int | None] = {
            "largest": None,
            "top_five": None,
        }
        for name, occurrences in occurrence_series.items():
            selected_index: int | None = None
            selected_basis: str | None = None
            for index, (_, occurrence_values, _, enumerated_count, _) in enumerate(occurrences):
                if enumerated_count is not None and len(occurrence_values) == enumerated_count:
                    selected_index = index
                    selected_basis = "enumerated_period_count"
                    break
                if (
                    enumerated_count is None
                    and periods
                    and len(occurrence_values) == len(periods)
                ):
                    selected_index = index
                    selected_basis = "resolved_period_count"
                    break
            if selected_index is None and occurrences:
                # Preserve fail-closed behaviour when no occurrence aligns.  The
                # existing missing-period/count-mismatch issues stay authoritative;
                # later occurrences simply cannot silently change the value.
                selected_index = 0
                selected_basis = "first_nonempty_fail_closed"

            if selected_index is not None:
                selected_start, selected_values, selected_raw, selected_count, selected_local_period = (
                    occurrences[selected_index]
                )
                values[name] = selected_values
                raw_percentages[name] = selected_raw
                selected_enumerated_counts[name] = selected_count
                occurrence_selection[name] = selected_basis
                selected_local_periods[name] = selected_local_period
                selected_label_starts[name] = selected_start

            occurrence_diagnostics[name] = [
                {
                    "label_start": label_start,
                    "value_count": len(occurrence_values),
                    "enumerated_period_count": enumerated_count,
                    "selected": index == selected_index,
                }
                for index, (
                    label_start,
                    occurrence_values,
                    _,
                    enumerated_count,
                    _,
                ) in enumerate(occurrences)
            ]

        # A concentration sentence can enumerate several bare years and one
        # final full date while the adjacent page contains a newer, unrelated
        # date.  When both percentage series independently align to that same
        # label-local full period, the local period is the governed denominator
        # context.  Neighbouring dates must not re-date the percentages.
        local_period_values = {
            period
            for period in selected_local_periods.values()
            if period is not None
        }
        selected_counts = {
            count for count in selected_enumerated_counts.values() if count is not None
        }
        selected_starts = [
            start for start in selected_label_starts.values() if start is not None
        ]
        shared_value_count = len(values["largest"])
        missing_count_companion_unique_pair = (
            not selected_counts
            and (
                len(occurrence_series["largest"]) == 1
                or len(occurrence_series["top_five"]) == 1
            )
        )
        companion_series_period_aligned = (
            shared_value_count >= 2
            and shared_value_count == len(values["top_five"])
            # Some licensed PDFs preserve the two parallel percentage series
            # and their shared label-local final period, but corrupt the bare
            # comparative years used by ``_enumerated_period_count``.  Equal
            # multi-value companion series remain structurally aligned when
            # neither label exposes a contradictory enumerated count.  A
            # present mismatched count still fails closed.
            and (
                selected_counts == {shared_value_count}
                or missing_count_companion_unique_pair
            )
            and len(local_period_values) == 1
            and len(selected_starts) == 2
            and max(selected_starts) - min(selected_starts) <= 1200
        )
        label_local_period_aligned = (
            len(local_period_values) == 1
            and all(period is not None for period in selected_local_periods.values())
            and selected_enumerated_counts["largest"] is not None
            and selected_enumerated_counts["largest"]
            == selected_enumerated_counts["top_five"]
            == len(values["largest"])
            == len(values["top_five"])
        )
        if companion_series_period_aligned and not label_local_period_aligned:
            for name, count in selected_enumerated_counts.items():
                if count is None:
                    selected_enumerated_counts[name] = shared_value_count
                    occurrence_selection[name] = "companion_series_period_count"
        if label_local_period_aligned or companion_series_period_aligned:
            periods = [next(iter(local_period_values))]
            period_source = target
            period_issues = []

        issues = list(period_issues)
        if self._review_only_context(evidence, target):
            issues.append("summary_or_risk_context_requires_review")
        if not periods:
            issues.append("missing_period")
        if not values["largest"] and not values["top_five"]:
            issues.append("concentration_percentage_missing")

        largest, largest_issue = self._latest_concentration_value(
            values["largest"], periods, selected_enumerated_counts["largest"]
        )
        top_five, top_five_issue = self._latest_concentration_value(
            values["top_five"], periods, selected_enumerated_counts["top_five"]
        )
        issues.extend(largest_issue)
        issues.extend(top_five_issue)
        if largest is None or top_five is None:
            issues.append("incomplete_concentration_values")
        if any(value < 0 or value > 100 for value in [largest, top_five] if value is not None):
            issues.append("percentage_out_of_range")
        if largest is not None and top_five is not None and largest > top_five:
            issues.append("largest_percentage_exceeds_top_five")

        # NOTE: `periods` arrives in document order, not chronological order — a
        # table caption or acquisition date below the narrative appends older
        # entries after it — so this can date a 2025 reading to 2022. Selecting
        # the chronologically latest period instead is correct in isolation but
        # regressed the 2020-2023 development cohort badly (clean customer
        # readings 18 -> 15, supplier 27 -> 18, +48 conflicts): dating facts
        # accurately makes far more of them collide in the merge's
        # latest-period bucket, and the merge voids a period the moment any two
        # candidates disagree by any amount. The brittle merge has to be fixed
        # before this selection can be.
        selected_period = periods[-1] if periods else None
        context_used = self._dedupe_chunks(
            [item for item in [period_source if period_source != target else None] if item]
        )
        status = ExtractionStatus.EXTRACTED if not issues else ExtractionStatus.NEEDS_REVIEW
        return ConcentrationFact(
            concentration_type=concentration_type,
            period_end=selected_period.end if selected_period else None,
            period_months=selected_period.months if selected_period else None,
            largest_counterparty_pct=largest,
            top_five_pct=top_five,
            evidence_ids=[evidence.evidence_id],
            document_id=target.document_id,
            chunk_id=target.chunk_id,
            page=target.page,
            status=status,
            issues=self._dedupe_strings(issues),
            context_chunk_ids=[item.chunk_id for item in context_used],
            context_pages=self._dedupe_ints([item.page for item in context_used]),
            metadata={
                "raw_percentages": raw_percentages,
                "percentage_occurrence_selection": occurrence_selection,
                "percentage_occurrences": occurrence_diagnostics,
                "source_context": evidence.metadata.get("source_context"),
                "period_candidates": [
                    {"period_end": item.end.isoformat(), "period_months": item.months}
                    for item in periods
                ],
                "percentage_semantics": "0_to_100_percent",
                "period_source_chunk_id": period_source.chunk_id if period_source else None,
                "concentration_period_selection": (
                    "aligned_label_local_period"
                    if label_local_period_aligned
                    else (
                        "companion_series_label_local_period"
                        if companion_series_period_aligned
                        else "best_available_period_context"
                    )
                ),
                # Records that a receivable/payable share was read and discarded,
                # so a dropped segment is auditable rather than silently absent.
                "balance_scope_segment_skipped": scope_skipped,
            },
        )

    @staticmethod
    def _is_balance_scope_segment(segment: str) -> bool:
        """True when a segment states a receivable/payable share, not a revenue share.

        Only the text before the first percentage is examined: that is where the
        denominator is named, while later sentences in the same segment may have
        moved on to an unrelated subject.
        """
        first = _PERCENT_RE.search(segment)
        prefix = segment[: first.start()] if first else segment
        return bool(_CONCENTRATION_BALANCE_SCOPE.search(prefix))

    @classmethod
    def _enumerated_period_count(cls, text: str, label_start: int) -> int | None:
        """Count the periods named by the series established just above a label.

        A track-record narrative names its periods once and then quotes one
        percentage per period ("於2022年、2023年、2024年以及截至2025年6月30日止六個
        月，前五大客戶……分別為55.2%、55.9%、51.0%及50.3%"). A following sentence
        refers back to that series rather than repeating it ("於往績記錄期間各年度
        ╱期間"), so the nearest preceding sentence that names periods governs both.

        ``_narrative_periods`` resolves only full dates, so the three bare years
        were invisible and a correct four-value series looked like a count
        mismatch against a single period. Returns ``None`` when no sentence above
        the label names a series, which leaves the caller's behaviour unchanged.
        """
        sentences = [item for item in re.split(r"[。;；]", text[:label_start]) if item.strip()]
        for sentence in reversed(sentences):
            years = {match.group(1) for match in _NARRATIVE_BARE_YEAR_RE.finditer(sentence)}
            dates = {match.group(0) for match in _CHINESE_DATE_RE.finditer(sentence)}
            dates |= {
                match.group(0) for match in _CHINESE_WORD_DATE_RE.finditer(sentence)
            }
            dates |= {match.group(0) for match in _ISO_DATE_RE.finditer(sentence)}
            # A full date carries its own year, which the bare-year pattern is
            # written to skip, so the two counts never double-count a period.
            total = len(years) + len(dates)
            if total >= 2:
                return None if _PERIOD_SPAN_PHRASE.search(sentence) else total
            if total == 1:
                # A lone year is a mention ("於2011年上市"), not a series.
                return None
        return None

    @classmethod
    def _label_local_period(cls, text: str, label_start: int) -> _Period | None:
        """Return the nearest full period in the sentence that owns a label."""

        sentence_start = max(
            text.rfind(delimiter, 0, label_start) for delimiter in ("。", ";", "；")
        )
        prefix = text[sentence_start + 1 : label_start]
        periods = cls._narrative_periods(prefix)
        return periods[-1] if periods else None

    @staticmethod
    def _latest_concentration_value(
        values: Sequence[Decimal],
        periods: Sequence[_Period],
        enumerated_count: int | None = None,
    ) -> tuple[Decimal | None, list[str]]:
        if not values:
            return None, []
        if not periods:
            return values[-1], []
        # The sentence carrying the percentages is the series they were written
        # against, so it outranks `periods`, which `_best_v03_periods` may have
        # taken from a neighbouring table header. That header can name *more*
        # periods than the sentence — a track-record table prints a comparative
        # interim column that the narrative omits — so preferring whichever
        # count is larger produced a false mismatch on a correct series.
        expected = enumerated_count if enumerated_count is not None else len(periods)
        if len(values) != expected:
            return values[-1], ["value_period_count_mismatch"]
        return values[-1], []

    def _merge_concentration_facts(
        self, concentration_type: str, facts: Sequence[ConcentrationFact]
    ) -> ConcentrationFact:
        dated = [item for item in facts if item.period_end is not None]
        selected_date = max((item.period_end for item in dated), default=None)
        selected = [item for item in facts if item.period_end == selected_date] if selected_date else list(facts)
        largest_values = {
            item.largest_counterparty_pct
            for item in selected
            if item.largest_counterparty_pct is not None
        }
        top_five_values = {
            item.top_five_pct for item in selected if item.top_five_pct is not None
        }
        # A page that read the whole series cleanly governs the merged reading.
        # Pages that read it only partially — a risk-factor paragraph quoting the
        # top-five figure but not the largest, or a customer table carrying no
        # percentages at all — describe their own partial view, so their issues
        # must not taint a complete clean reading of the same period. They can
        # still contradict it: the conflict check below runs over every
        # candidate regardless.
        governing = [
            item
            for item in selected
            if item.status is ExtractionStatus.EXTRACTED
            and not item.issues
            and item.largest_counterparty_pct is not None
            and item.top_five_pct is not None
        ]
        issues = [] if governing else [issue for item in selected for issue in item.issues]
        if len(largest_values) > 1 or len(top_five_values) > 1:
            issues.append("conflicting_values_for_same_period")
        if "conflicting_values_for_same_period" in issues and any(
            item.metadata.get("source_context") == "summary" for item in selected
        ) and any(item.metadata.get("source_context") == "primary_statement" for item in selected):
            issues.append("summary_primary_statement_conflict")
        largest = next(iter(largest_values)) if len(largest_values) == 1 else None
        top_five = next(iter(top_five_values)) if len(top_five_values) == 1 else None
        evidence_ids = self._dedupe_strings(
            [evidence_id for item in selected for evidence_id in item.evidence_ids]
        )
        first = selected[0]
        period_month_values = {item.period_months for item in selected if item.period_months is not None}
        if len(period_month_values) > 1:
            issues.append("period_months_conflict")
        if largest is None or top_five is None:
            issues.append("incomplete_concentration_values")
        else:
            issues = [item for item in issues if item != "incomplete_concentration_values"]
        if largest is not None and top_five is not None and largest > top_five:
            issues.append("largest_percentage_exceeds_top_five")
        issues = self._dedupe_strings(issues)
        return ConcentrationFact(
            concentration_type=concentration_type,
            period_end=selected_date,
            period_months=next(iter(period_month_values)) if len(period_month_values) == 1 else None,
            largest_counterparty_pct=largest,
            top_five_pct=top_five,
            evidence_ids=evidence_ids,
            document_id=first.document_id,
            chunk_id=first.chunk_id,
            page=first.page,
            status=ExtractionStatus.EXTRACTED if not issues else ExtractionStatus.NEEDS_REVIEW,
            issues=issues,
            context_chunk_ids=self._dedupe_strings(
                [chunk_id for item in selected for chunk_id in item.context_chunk_ids]
            ),
            context_pages=self._dedupe_ints(
                [page for item in selected for page in item.context_pages]
            ),
            metadata={
                "candidate_count": len(selected),
                "percentage_semantics": "0_to_100_percent",
                "candidate_pages": [item.page for item in selected],
            },
        )

    @staticmethod
    def _period_fact_conflicts(observations: Sequence[FinancialPeriodFact]) -> list[str]:
        values_by_period: dict[tuple[date, int | None], set[tuple[Decimal | None, str | None, str | None]]] = {}
        for item in observations:
            if item.period_end is None:
                continue
            key = (item.period_end, item.period_months)
            values_by_period.setdefault(key, set()).add(
                (item.normalized_value, item.currency, item.unit)
            )
        if any(len(values) > 1 for values in values_by_period.values()):
            issues = ["conflicting_values_for_same_period"]
            contexts = {item.metadata.get("source_context") for item in observations}
            if {"summary", "primary_statement"} <= contexts:
                issues.append("summary_primary_statement_conflict")
            return issues
        return []

    @classmethod
    def _narrative_periods(cls, text: str) -> list[_Period]:
        located: list[tuple[int, _Period]] = []
        for pattern in (_CHINESE_DATE_RE, _ISO_DATE_RE):
            for match in pattern.finditer(text):
                try:
                    end = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                except ValueError:
                    continue
                clause_start = max(0, text.rfind("。", 0, match.start()) + 1)
                clause_end = text.find("。", match.end())
                clause = text[clause_start : clause_end if clause_end >= 0 else len(text)]
                located.append((match.start(), _Period(end, cls._period_months(clause))))
        for match in _CHINESE_WORD_DATE_RE.finditer(text):
            year = cls._year_value(match.group(1))
            month = cls._chinese_integer(match.group(2))
            day = cls._chinese_integer(match.group(3))
            if year is None or month is None or day is None:
                continue
            try:
                end = date(year, month, day)
            except ValueError:
                continue
            clause_start = max(0, text.rfind("。", 0, match.start()) + 1)
            clause_end = text.find("。", match.end())
            clause = text[clause_start : clause_end if clause_end >= 0 else len(text)]
            located.append((match.start(), _Period(end, cls._period_months(clause))))
        located.sort(key=lambda item: item[0])
        return cls._dedupe_periods([period for _, period in located])

    def _best_v03_periods(
        self,
        target_lines: Sequence[str],
        target: DocumentChunk,
        context: Sequence[DocumentChunk],
    ) -> tuple[list[_Period], DocumentChunk | None, list[str]]:
        candidates: list[tuple[list[_Period], DocumentChunk, list[str]]] = []
        target_periods, target_issues = self._parse_periods(target_lines)
        if target_periods or target_issues:
            candidates.append((target_periods, target, target_issues))
        narrative_periods = self._narrative_periods(target.text)
        if narrative_periods:
            candidates.append((narrative_periods, target, []))
        for chunk in context:
            lines = [line.strip() for line in chunk.text.splitlines() if line.strip()]
            periods, issues = self._parse_periods(lines)
            if periods or issues:
                candidates.append((periods, chunk, issues))
        if not candidates:
            return [], None, []
        periods, source, issues = max(
            candidates,
            key=lambda item: (len(item[0]), not item[2], item[1] == target),
        )
        return periods, source, issues

    @staticmethod
    def _evidence_identity_issues(
        evidence: Evidence, chunks_by_id: Mapping[str, DocumentChunk]
    ) -> list[str]:
        if not evidence.evidence_id:
            return ["evidence_id_missing"]
        if not evidence.chunk_id or evidence.chunk_id not in chunks_by_id:
            return ["evidence_chunk_missing"]
        chunk = chunks_by_id[evidence.chunk_id]
        issues: list[str] = []
        if evidence.document_id and evidence.document_id != chunk.document_id:
            issues.append("evidence_document_mismatch")
        if evidence.page and evidence.page != chunk.page:
            issues.append("evidence_page_mismatch")
        return issues

    @staticmethod
    def _evidence_ids(evidence_candidates: Sequence[Evidence]) -> list[str]:
        return V03FinancialFactExtractor._dedupe_strings(
            [item.evidence_id for item in evidence_candidates if item.evidence_id]
        )

    @staticmethod
    def _evidence_ids_from_period_facts(facts: Sequence[FinancialPeriodFact]) -> list[str]:
        return V03FinancialFactExtractor._dedupe_strings(
            [evidence_id for item in facts for evidence_id in item.evidence_ids]
        )

    @staticmethod
    def _dedupe_chunks(chunks: Sequence[DocumentChunk]) -> list[DocumentChunk]:
        result: list[DocumentChunk] = []
        seen: set[str] = set()
        for chunk in chunks:
            if chunk.chunk_id not in seen:
                seen.add(chunk.chunk_id)
                result.append(chunk)
        return result

    @staticmethod
    def _dedupe_strings(values: Sequence[str]) -> list[str]:
        return list(dict.fromkeys(values))

    @staticmethod
    def _dedupe_ints(values: Sequence[int]) -> list[int]:
        return list(dict.fromkeys(values))


class TableAwareV03FinancialFactExtractor(V03FinancialFactExtractor):
    """Structured-first v0.3 extractor.

    When the parser attached a reconstructed grid (``chunk.metadata["tables"]``,
    produced by :mod:`ipo_risk.parsers.table_reconstruction`), period-series
    facts are read from the already column-aligned cells — which structurally
    eliminates ``metric_label_not_found`` (label found on its own table row) and
    ``value_period_count_mismatch`` (cells and periods share the same column
    count).  When no structured table is present, or no table row matches the
    metric label, it transparently falls back to the inherited deterministic
    text-row path, so behaviour is identical to the regex extractor on documents
    without reconstructed tables.

    Concentration facts keep the inherited narrative-percentage path: the target
    prospectuses disclose concentration as prose (e.g. "最大客戶佔 30%"), which the
    year-anchored table reconstruction deliberately does not treat as a numeric
    grid.
    """

    # Issues that only mean "this evidence page is not the statement", not a
    # data defect — safe to drop from the series verdict when another page did
    # yield clean observations.
    _LOCATION_ONLY_ISSUES = frozenset(
        {"metric_label_not_found", "unsupported_layout", "evidence_candidates_empty"}
    )

    # Extra legacy-metric label patterns used ONLY on the structured-table path.
    # They cover wording the frozen base patterns miss — e.g. this issuer writes
    # the operating cash-flow row as "…現金淨額" (net cash) rather than "…淨現金".
    # Kept in the subclass so the base cash-runway path (frozen 2410.HK) is
    # untouched.
    _EXTENDED_METRIC_LABELS = {
        "operating_cash_flow": (
            *_LABELS["operating_cash_flow"],
            re.compile(r"經營活動(?:所得|所用|產生|使用|經營).*?現金淨額"),
            re.compile(r"经营活动(?:所得|所用|产生|使用|经营).*?现金净额"),
        ),
    }

    def _metric_labels(self, metric_name: str) -> tuple:
        return self._EXTENDED_METRIC_LABELS.get(metric_name, _LABELS.get(metric_name, ()))

    # --- Currency/unit forms the frozen base grammar does not cover -----------
    # The base grammar reads the scale from a bare ``元`` suffix (``人民幣千元``),
    # but a large share of the development cohort (2020-2023) writes the scale
    # *in front of* the currency instead — ``千港元`` / ``千美元`` / ``百萬港元`` —
    # which resolves to no unit at all and stalls every fact on ``missing_unit``.
    # Overridden here (opt-in table path) so the frozen regex extractor and the
    # frozen 2410.HK cash-runway slice keep their exact current behaviour.
    _CURRENCY_WORD = r"(?:人民幣|人民币|港元|港幣|港币|美元|新加坡元)"
    _SCALED_CURRENCY_UNITS = (
        (re.compile(rf"(?:百萬|百万)\s*{_CURRENCY_WORD}"), "million"),
        (re.compile(rf"(?<!百)(?:萬|万)\s*{_CURRENCY_WORD}"), "ten_thousand"),
        (re.compile(rf"(?:千|仟)\s*{_CURRENCY_WORD}"), "thousand"),
    )

    @classmethod
    def _currency_unit_candidates(cls, text: str) -> tuple[set[str], set[str]]:
        currencies, units = super()._currency_unit_candidates(text)
        for pattern, unit in cls._SCALED_CURRENCY_UNITS:
            if pattern.search(text):
                units.add(unit)
                # ``千港元`` is a scaled unit, not a bare ``元``; the base grammar
                # cannot see that, so drop the spurious "unit" it inferred.
                units.discard("unit")
        return currencies, units

    # A reconstructed row label keeps the statement's dot leaders glued to the
    # metric name ("收入................."), because the leaders are real glyphs at
    # real coordinates.  The frozen revenue patterns anchor on ``(?:\s|$)`` after
    # the metric name, so the leaders — pure typographic filler — would hide every
    # revenue row on the table path.  Collapse leader runs to a single space for
    # matching only; the flattened-text path is untouched (PyMuPDF already renders
    # the leaders there as spaced dots).
    _DOT_LEADER_RE = re.compile(r"[.．\u2024·・…]{2,}")

    @classmethod
    def _table_row_label(cls, row: Mapping[str, object]) -> str:
        return cls._DOT_LEADER_RE.sub(" ", str(row.get("label", "")))

    @staticmethod
    def _period_basis(months: int | None) -> str | None:
        """Name the reporting basis so a rule never compares a year to a stub."""
        if months is None:
            return None
        return "annual" if months == 12 else "interim"

    @classmethod
    def _periods_from_columns(cls, table: Mapping[str, object]) -> list[_Period | None] | None:
        """Resolve one period per value column from the parser's column map.

        ``period_columns`` pairs every value column with its own year label and
        the period-group caption governing it, so a mixed annual/interim table
        yields ``2024-12-31`` (12 months) and ``2024-09-30`` (9 months) as two
        distinct periods instead of one duplicated ``2024年``.  The result stays
        index-aligned with ``row["cells"]`` — which is what makes
        ``value_period_count_mismatch`` structurally impossible on this path —
        with ``None`` for any column whose period cannot be resolved.
        """
        columns = table.get("period_columns") or []
        if not columns:
            return None
        periods: list[_Period | None] = []
        for column in columns:
            year_label = column.get("year_label")
            group_line = column.get("group_line")
            year_match = _YEAR_RE.fullmatch(str(year_label).strip()) if year_label else None
            month_day = cls._month_day(str(group_line)) if group_line else None
            if year_match is None or month_day is None:
                periods.append(None)
                continue
            month, day = month_day
            try:
                end = date(int(year_match.group(1)), month, day)
            except ValueError:
                periods.append(None)
                continue
            periods.append(_Period(end, cls._period_months(str(group_line))))
        return periods if any(period is not None for period in periods) else None

    def _table_currency_unit(
        self,
        header_lines: Sequence[str],
        target: DocumentChunk,
        context: Sequence[DocumentChunk],
    ) -> _CurrencyUnitResolution:
        """Read the money units off the grid's own caption before the page text.

        A summary page prints the table in 千元 while the prose beside it quotes
        百萬元, so a whole-page scan sees two scales and resolves neither — the
        same page then disagrees with the statement page about the unit of an
        identical figure and the series is thrown out for conflicting values.
        The cash-runway table path already resolves the caption first; this gives
        the period-series path the same rule.
        """
        currency, unit = self._detect_currency_unit("\n".join(header_lines))
        if currency is not None and unit is not None:
            return _CurrencyUnitResolution(currency, unit, target, target, [], [])
        return self._find_currency_unit(target, context)

    def _resolve_table_periods(
        self,
        table: Mapping[str, object] | None,
        raw_values: Sequence[str],
        header_lines: Sequence[str],
        target: DocumentChunk,
        context: Sequence[DocumentChunk],
    ) -> tuple[list[_Period | None], DocumentChunk | None, list[str], str]:
        """Prefer the parser's per-column period map over scanning the header.

        The header scan flattens the caption into a bag of year strings and has
        to re-infer where one period basis ends and the next begins; the column
        map already knows, because the parser kept each column's own caption.
        Falls back to the header scan whenever the map is absent (a page the
        parser could not resolve) or does not cover this row's value columns.
        """
        columns = self._periods_from_columns(table) if table else None
        if columns is not None and len(columns) == len(raw_values):
            return columns, target, [], "period_column_map"
        periods, source, issues = self._best_v03_periods(header_lines, target, context)
        return list(periods), source, issues, "header_scan"

    def _extract_candidate(
        self,
        metric_name: str,
        evidence: Evidence,
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> FinancialMetricValue:
        """Legacy cash-runway metric extraction, structured-table first.

        Fires only for a chunk that carries reconstructed tables whose identity
        matches the evidence and that contains a row for this metric; otherwise
        it defers to the inherited flattened-text path (so the base cash-runway
        behaviour is unchanged wherever no structured table is present).
        """
        chunk = chunks_by_id.get(evidence.chunk_id or "")
        if chunk is None or not self._structured_tables(chunk):
            return super()._extract_candidate(metric_name, evidence, chunks_by_id)
        if any(
            getattr(evidence, field) != getattr(chunk, field)
            for field in ("chunk_id", "document_id", "page")
        ):
            return super()._extract_candidate(metric_name, evidence, chunks_by_id)
        row = self._find_metric_table_row(metric_name, chunk)
        if row is None:
            return super()._extract_candidate(metric_name, evidence, chunks_by_id)
        raw_label, raw_values, header_lines, table = row
        return self._metric_value_from_table(
            metric_name, evidence, chunk, chunks_by_id, raw_label, raw_values,
            header_lines, table,
        )

    def _find_metric_table_row(
        self, metric_name: str, chunk: DocumentChunk
    ) -> tuple[str, list[str], list[str], dict] | None:
        for table in self._structured_tables(chunk) or []:
            if not isinstance(table, dict):
                continue
            header_lines = [
                str(line).strip()
                for line in (table.get("header_lines") or [])
                if str(line).strip()
            ]
            for row in table.get("rows") or []:
                label = self._table_row_label(row)
                for pattern in self._metric_labels(metric_name):
                    match = pattern.search(label)
                    if not match:
                        continue
                    cells = [str(cell).strip() for cell in (row.get("cells") or [])]
                    if any(cells):
                        return match.group(0), cells, header_lines, table
        return None

    def _metric_value_from_table(
        self,
        metric_name: str,
        evidence: Evidence,
        chunk: DocumentChunk,
        chunks_by_id: Mapping[str, DocumentChunk],
        raw_label: str,
        raw_values: list[str],
        header_lines: list[str],
        table: Mapping[str, object] | None = None,
    ) -> FinancialMetricValue:
        """Mirror the base metric assembly, sourcing values/periods from a table."""
        issues: list[str] = []
        context_chunks = self._context_chunks(chunk, chunks_by_id)
        field_sources: dict[str, str] = {"label": chunk.chunk_id, "value": chunk.chunk_id}

        # Resolve currency/unit from the table's own caption first: a statement
        # page often mixes narrative "百萬元" (million) with the table's "千元"
        # (thousand), which makes a whole-page scan ambiguous. The reconstructed
        # header carries the caption sitting directly above the grid.
        currency_unit = None
        header_currency, header_unit = self._detect_currency_unit("\n".join(header_lines))
        if header_currency is not None and header_unit is not None:
            currency, unit = header_currency, header_unit
            field_sources["currency"] = chunk.chunk_id
            field_sources["unit"] = chunk.chunk_id
        else:
            currency_unit = self._find_currency_unit(chunk, context_chunks)
            currency = currency_unit.currency
            unit = currency_unit.unit
            issues.extend(currency_unit.issues)
            if currency_unit.currency_source:
                field_sources["currency"] = currency_unit.currency_source.chunk_id
            if currency_unit.unit_source:
                field_sources["unit"] = currency_unit.unit_source.chunk_id
        if currency is None:
            issues.append("currency_missing_or_ambiguous")
        if unit is None:
            issues.append("unit_missing_or_ambiguous")

        periods, period_source, period_issues, period_axis = self._resolve_table_periods(
            table, raw_values, header_lines, chunk, context_chunks
        )
        issues.extend(period_issues)
        if period_source:
            field_sources["period"] = period_source.chunk_id
        numeric_values = [(raw, self._normalize_amount(raw)) for raw in raw_values]
        valid_values = [(raw, value) for raw, value in numeric_values if value is not None]
        if not raw_values:
            issues.append("target_row_has_no_values")
        if len(periods) != len(raw_values):
            issues.append("period_value_column_count_mismatch")
        if not periods:
            issues.append("period_header_missing_or_ambiguous")

        selected_raw = ""
        selected_value: Decimal | None = None
        selected_period: _Period | None = None
        if periods and len(periods) == len(raw_values):
            complete = [
                (period, raw, value)
                for period, (raw, value) in zip(periods, numeric_values, strict=True)
                if value is not None and period is not None
            ]
            if complete:
                selected_period, selected_raw, selected_value = max(
                    complete, key=lambda item: item[0].end
                )
        elif len(valid_values) == 1 and len(periods) == 1 and periods[0] is not None:
            selected_period = periods[0]
            selected_raw, selected_value = valid_values[0]

        if selected_value is None:
            issues.append("latest_complete_value_not_determinable")
        if metric_name == "operating_cash_flow" and (
            selected_period is None or selected_period.months not in range(1, 13)
        ):
            issues.append("operating_cash_flow_period_months_missing")

        context_used = {chunk.chunk_id: chunk}
        sources = [period_source]
        if currency_unit is not None:
            sources.extend(
                [
                    currency_unit.currency_source,
                    currency_unit.unit_source,
                    *currency_unit.reviewed_context,
                ]
            )
        for source in sources:
            if source is not None:
                context_used[source.chunk_id] = source
        status = ExtractionStatus.EXTRACTED if not issues else ExtractionStatus.NEEDS_REVIEW
        return FinancialMetricValue(
            metric_name=metric_name,
            raw_label=raw_label,
            raw_value=selected_raw,
            normalized_value=selected_value,
            currency=currency,
            unit=unit,
            period_end=selected_period.end if selected_period else None,
            period_months=(
                selected_period.months
                if selected_period and metric_name == "operating_cash_flow"
                else None
            ),
            evidence_id=evidence.evidence_id,
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            page=chunk.page,
            status=status,
            issues=list(dict.fromkeys(issues)),
            context_chunk_ids=list(context_used),
            context_pages=sorted({item.page for item in context_used.values()}),
            extraction_method="structured_table_cash_v03",
            metadata={
                "field_sources": field_sources,
                "row_values": raw_values,
                "period_axis": period_axis,
                "period_basis": self._period_basis(
                    selected_period.months if selected_period else None
                ),
                "period_candidates": [
                    {
                        "period_end": item.end.isoformat(),
                        "period_months": item.months,
                        "period_basis": self._period_basis(item.months),
                    }
                    for item in periods
                    if item is not None
                ],
                "query_intent": evidence.metadata.get("query_intent"),
            },
        )

    @staticmethod
    def _collapse_agreeing_observations(
        result: FinancialPeriodSeriesResult,
    ) -> FinancialPeriodSeriesResult:
        """Merge observations that are the same fact cited from several pages.

        A prospectus prints the same figure in the summary, in MD&A and in the
        audited statements, and the retriever hands back all three.  Identical
        readings of one period are one observation with three citations, not
        three observations — left un-merged, the growth rule sorts by period end,
        picks the latest fact as "current" and its duplicate as "previous", and
        the skill rejects the pair as ``period_order_invalid``.

        Only exact agreement on value, currency, unit and period is merged, so a
        genuine disagreement still reaches ``_period_fact_conflicts`` and is still
        reported as ``conflicting_values_for_same_period``.  Series-level issues
        were aggregated by the base implementation before this runs, so nothing
        is masked; the citations of every merged page are preserved.
        """
        if len(result.observations) < 2:
            return result
        groups: dict[tuple, list[FinancialPeriodFact]] = {}
        for fact in result.observations:
            key = (
                fact.period_end,
                fact.period_months,
                fact.normalized_value,
                fact.currency,
                fact.unit,
            )
            groups.setdefault(key, []).append(fact)
        if len(groups) == len(result.observations):
            return result
        merged: list[FinancialPeriodFact] = []
        merged_away_issues: list[str] = []
        for duplicates in groups.values():
            canonical = next(
                (
                    item
                    for item in duplicates
                    if item.status == ExtractionStatus.EXTRACTED and not item.issues
                ),
                duplicates[0],
            )
            if len(duplicates) > 1:
                # Keep the issues of the readings being merged away attributable,
                # so the series verdict can still account for every one of them.
                merged_away_issues.extend(
                    issue
                    for item in duplicates
                    if item is not canonical
                    for issue in item.issues
                )
                canonical = canonical.model_copy(
                    update={
                        "evidence_ids": V03FinancialFactExtractor._dedupe_strings(
                            [eid for item in duplicates for eid in item.evidence_ids]
                        ),
                        "context_chunk_ids": V03FinancialFactExtractor._dedupe_strings(
                            [
                                chunk_id
                                for item in duplicates
                                for chunk_id in (*item.context_chunk_ids, item.chunk_id)
                                if chunk_id
                            ]
                        ),
                        "context_pages": V03FinancialFactExtractor._dedupe_ints(
                            sorted(
                                {
                                    page
                                    for item in duplicates
                                    for page in (*item.context_pages, item.page)
                                    if page
                                }
                            )
                        ),
                    }
                )
            merged.append(canonical)
        merged.sort(
            key=lambda item: (
                item.period_end is None,
                item.period_end or date.min,
                item.page or 0,
                item.chunk_id or "",
            )
        )
        return result.model_copy(
            update={
                "observations": merged,
                "evidence_ids": V03FinancialFactExtractor._dedupe_strings(
                    [eid for item in merged for eid in item.evidence_ids]
                ),
                "metadata": {
                    **result.metadata,
                    "observation_count": len(merged),
                    "merged_away_issues": V03FinancialFactExtractor._dedupe_strings(
                        merged_away_issues
                    ),
                },
            }
        )

    def _extract_period_series(
        self,
        metric_name: str,
        evidence_candidates: Sequence[Evidence],
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> FinancialPeriodSeriesResult:
        result = super()._extract_period_series(
            metric_name, evidence_candidates, chunks_by_id
        )
        result = self._collapse_agreeing_observations(result)
        if result.status != ExtractionStatus.NEEDS_REVIEW or not result.observations:
            return result
        residual = [i for i in result.issues if i not in self._LOCATION_ONLY_ISSUES]
        observation_issues = [issue for obs in result.observations for issue in obs.issues]
        if (
            not residual
            and not observation_issues
            and all(obs.status == ExtractionStatus.EXTRACTED for obs in result.observations)
        ):
            # Every real fact is clean; the only issues were non-statement pages.
            return result.model_copy(
                update={"status": ExtractionStatus.EXTRACTED, "issues": []}
            )
        return self._keep_clean_subset(result)

    # Conflicts are recomputed over the surviving observations, so the verdict
    # the base drew over the full set must not be carried across.
    _CONFLICT_ISSUES = frozenset(
        {"conflicting_values_for_same_period", "summary_primary_statement_conflict"}
    )

    def _keep_clean_subset(
        self, result: FinancialPeriodSeriesResult
    ) -> FinancialPeriodSeriesResult:
        """Let a complete, clean, self-consistent series survive an unreadable page.

        Retrieval returns the five best pages, and one of them is regularly a
        page whose columns are not periods at all — a statement of changes in
        equity, whose columns are share capital / premium / accumulated losses.
        Its readings arrive already marked defective, but a single issue anywhere
        forces the whole series to review, so a perfect five-period series from
        the income statement is discarded along with it.

        A defective reading is evidence that a page could not be read, not
        evidence about the value, so it cannot outvote a clean one.  Only
        observations carrying their own issues are dropped; a clean observation
        that merely disagrees is kept, conflicts are recomputed over the
        survivors, and any disagreement among them still blocks the series.
        """
        clean = [
            item
            for item in result.observations
            if item.status == ExtractionStatus.EXTRACTED and not item.issues
        ]
        # Both series rules compare two periods, so a lone survivor decides nothing.
        if len(clean) < 2 or len(clean) == len(result.observations):
            return result
        if self._period_fact_conflicts(clean):
            return result
        dropped = [item for item in result.observations if item not in clean]
        dropped_issues = {issue for item in dropped for issue in item.issues}
        dropped_issues.update(result.metadata.get("merged_away_issues") or [])
        residual = [
            issue
            for issue in result.issues
            if issue not in self._LOCATION_ONLY_ISSUES
            and issue not in dropped_issues
            and issue not in self._CONFLICT_ISSUES
        ]
        if residual:
            return result
        return result.model_copy(
            update={
                "observations": clean,
                "status": ExtractionStatus.EXTRACTED,
                "issues": [],
                "evidence_ids": self._dedupe_strings(
                    [eid for item in clean for eid in item.evidence_ids]
                ),
                "metadata": {
                    **result.metadata,
                    "observation_count": len(clean),
                    "unreadable_pages": self._dedupe_ints(
                        sorted({item.page for item in dropped if item.page})
                    ),
                    "unreadable_page_issues": sorted(dropped_issues),
                },
            }
        )

    def _period_facts_from_evidence(
        self,
        metric_name: str,
        evidence: Evidence,
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> tuple[list[FinancialPeriodFact], list[str]]:
        identity_issues = self._evidence_identity_issues(evidence, chunks_by_id)
        if identity_issues:
            return [], identity_issues
        target = chunks_by_id[evidence.chunk_id or ""]
        tables = self._structured_tables(target)
        if tables:
            structured = self._period_facts_from_tables(
                metric_name, evidence, target, tables, chunks_by_id
            )
            if structured is not None:
                return structured
            # The grid is the authority on which rows this page has.  Re-reading
            # the flattened text would only re-introduce what the grid exists to
            # remove: with no coordinates it matches the metric name wherever it
            # appears — in prose, in a segment note, under 非香港財務報告準則計量,
            # or as the tail of a wrapped caption (「…金融資產的公允價值收益」 read
            # as 收益).  On the 2020-2023 development cohort, text-only readings of
            # a page that already has a grid disagree with that grid's column count
            # 79 times out of 126, and inspecting the rest shows agreeing on the
            # count does not make them the metric either.  Report the row as
            # absent — a location-only issue the series verdict already forgives.
            return [], ["metric_label_not_found"]
        return super()._period_facts_from_evidence(metric_name, evidence, chunks_by_id)

    @staticmethod
    def _structured_tables(target: DocumentChunk) -> list[dict] | None:
        tables = target.metadata.get("tables") if target.metadata else None
        if isinstance(tables, list) and tables:
            return tables
        return None

    def _period_facts_from_tables(
        self,
        metric_name: str,
        evidence: Evidence,
        target: DocumentChunk,
        tables: Sequence[dict],
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> tuple[list[FinancialPeriodFact], list[str]] | None:
        """Build facts from the first table row whose label matches the metric."""
        for table in tables:
            header_lines = [
                str(line).strip()
                for line in (table.get("header_lines") or [])
                if str(line).strip()
            ]
            for row in table.get("rows") or []:
                label = self._table_row_label(row)
                index, raw_label = self._find_v03_label([label], metric_name)
                if index is None:
                    continue
                raw_values = [str(cell).strip() for cell in (row.get("cells") or [])]
                if not any(raw_values):
                    continue
                return self._assemble_period_facts(
                    metric_name, evidence, target, chunks_by_id,
                    raw_label, raw_values, header_lines, table,
                )
        return None

    def _assemble_period_facts(
        self,
        metric_name: str,
        evidence: Evidence,
        target: DocumentChunk,
        chunks_by_id: Mapping[str, DocumentChunk],
        raw_label: str,
        raw_values: Sequence[str],
        header_lines: Sequence[str],
        table: Mapping[str, object] | None = None,
    ) -> tuple[list[FinancialPeriodFact], list[str]]:
        """Mirror the parent's fact construction, sourcing periods from the
        reconstructed table header instead of the flattened page lines."""
        context = self._context_chunks(target, chunks_by_id)
        periods, period_source, period_issues, period_axis = self._resolve_table_periods(
            table, raw_values, header_lines, target, context
        )
        issues = list(period_issues)
        if self._review_only_context(evidence, target):
            issues.append("summary_or_risk_context_requires_review")
        if not periods:
            issues.append("missing_period")
        if periods and len(periods) != len(raw_values):
            issues.append("value_period_count_mismatch")
        # A column the map could not date is only a defect when it carries a
        # value; an empty spare column is just table furniture.
        if period_axis == "period_column_map":
            issues.extend(
                "period_column_unresolved"
                for period, raw_value in zip(periods, raw_values, strict=True)
                if period is None and raw_value.strip()
            )

        resolution = self._table_currency_unit(header_lines, target, context)
        issues.extend(resolution.issues)
        if resolution.currency is None:
            issues.append("missing_currency")
        if resolution.unit is None:
            issues.append("missing_unit")

        context_used = self._dedupe_chunks(
            [
                item
                for item in [
                    period_source if period_source != target else None,
                    resolution.currency_source if resolution.currency_source != target else None,
                    resolution.unit_source if resolution.unit_source != target else None,
                    *resolution.reviewed_context,
                ]
                if item is not None
            ]
        )
        facts: list[FinancialPeriodFact] = []
        for value_index, raw_value in enumerate(raw_values):
            period = periods[value_index] if value_index < len(periods) else None
            if period is None and period_axis == "period_column_map":
                # Already accounted for above; emitting a dateless observation
                # here would only pollute the series with an unusable fact.
                continue
            value, value_issues, normalization = self._normalize_period_value(
                metric_name, raw_label, raw_value, evidence, target
            )
            fact_issues = list(issues) + value_issues
            if period is not None and period.months is None:
                fact_issues.append("missing_period_months")
            fact_status = (
                ExtractionStatus.EXTRACTED
                if value is not None
                and period is not None
                and period.months is not None
                and resolution.currency is not None
                and resolution.unit is not None
                and not fact_issues
                else ExtractionStatus.NEEDS_REVIEW
            )
            facts.append(
                FinancialPeriodFact(
                    metric_name=metric_name,
                    period_end=period.end if period else None,
                    period_months=period.months if period else None,
                    normalized_value=value,
                    currency=resolution.currency,
                    unit=resolution.unit,
                    evidence_ids=[evidence.evidence_id],
                    document_id=target.document_id,
                    chunk_id=target.chunk_id,
                    page=target.page,
                    raw_label=raw_label,
                    raw_value=raw_value,
                    status=fact_status,
                    issues=self._dedupe_strings(fact_issues),
                    context_chunk_ids=[item.chunk_id for item in context_used],
                    context_pages=self._dedupe_ints([item.page for item in context_used]),
                    metadata={
                        "value_index": value_index,
                        "normalization": normalization,
                        "extraction_method": "structured_table_v03",
                        "period_axis": period_axis,
                        "period_basis": self._period_basis(
                            period.months if period else None
                        ),
                        "period_group_line": (
                            (table.get("period_columns") or [])[value_index].get("group_line")
                            if table and period_axis == "period_column_map"
                            else None
                        ),
                        "period_basis_mixed": bool(table.get("period_basis_mixed"))
                        if table
                        else False,
                        "source_context": evidence.metadata.get("source_context"),
                        "period_source_chunk_id": period_source.chunk_id if period_source else None,
                        "currency_source_chunk_id": (
                            resolution.currency_source.chunk_id
                            if resolution.currency_source
                            else None
                        ),
                        "unit_source_chunk_id": (
                            resolution.unit_source.chunk_id if resolution.unit_source else None
                        ),
                    },
                )
            )
        return facts, self._dedupe_strings(issues)
