"""Rule-based extraction of cash values from prospectus evidence."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from ipo_risk.extraction.models import (
    ExtractionStatus,
    FinancialExtractionResult,
    FinancialMetricValue,
)
from ipo_risk.schemas import DocumentChunk, Evidence


_NUMBER_BODY = r"(?:\d{1,3}(?:(?:[,，]|\s)\d{3})+|\d+)(?:\.\d+)?"
_AMOUNT_RE = re.compile(
    rf"^\s*(?P<value>(?:\(\s*{_NUMBER_BODY}\s*\)|（\s*{_NUMBER_BODY}\s*）|[+\-−–—]?\s*{_NUMBER_BODY}))\s*$"
)
_EMPTY_AMOUNT_RE = re.compile(r"^\s*[-−–—]\s*$")
_YEAR_RE = re.compile(r"^(20\d{2})\s*年?$", re.IGNORECASE)
_CHINESE_DATE_RE = re.compile(r"(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
_ISO_DATE_RE = re.compile(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})")
_ENGLISH_DATE_DAY_FIRST_RE = re.compile(
    r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})",
    re.I,
)
_ENGLISH_DATE_MONTH_FIRST_RE = re.compile(
    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(20\d{2})",
    re.I,
)
_MONTH_NAMES = "january february march april may june july august september october november december".split()

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

        return FinancialExtractionResult(
            cash_and_cash_equivalents=self._extract_metric(
                "cash_and_cash_equivalents", cash_evidence_candidates, chunks_by_id
            ),
            operating_cash_flow=self._extract_metric(
                "operating_cash_flow", operating_cash_flow_candidates, chunks_by_id
            ),
        )

    def _extract_metric(
        self,
        metric_name: str,
        evidence_candidates: Sequence[Evidence],
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> FinancialMetricValue:
        candidates: list[_Candidate] = []
        for rank, evidence in enumerate(evidence_candidates[:5]):
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
                    )
                )

        if not candidates:
            return FinancialMetricValue(
                metric_name=metric_name,
                status=ExtractionStatus.NOT_FOUND,
                issues=["top_5_evidence_contains_no_supported_target_row"],
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
            selected_period is None or selected_period.months not in {3, 6, 9, 12}
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
        text_without_scaled_units = re.sub(r"千元|萬元|万元|百萬元|百万元", "", text)
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

        years = [int(match.group(1)) for line in lines if (match := _YEAR_RE.fullmatch(line))]
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
    def _period_months(line: str) -> int | None:
        chinese = re.search(r"(?:止|為|为|共)\s*([三六九十二0-9]+)\s*[個个]?月", line)
        if chinese:
            values = {"三": 3, "六": 6, "九": 9, "十二": 12}
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
