"""v0.4.5 concentration period/value reconciliation overlay.

This module is deliberately narrow. It leaves retrieval, policy thresholds,
Verifier rules, Existing Gold, and the public extraction schema unchanged while
repairing two failure modes exposed by the fixed-10 Development benchmark:

1. a narrative candidate can carry correctly extracted latest percentages but be
   dated with the last period in document order instead of the chronologically
   latest period; and
2. a later evidence item that contains no usable concentration percentage can
   become the merge's selected period and veto an earlier valid observation.

The overlay keeps genuine same-period value conflicts fail-closed. It also emits
compact reconciliation metadata so the next benchmark can distinguish period
alignment from value conflicts without reading raw logs.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from ipo_risk.extraction.financial import (
    TableAwareV03FinancialFactExtractor as _BaseTableAwareV03FinancialFactExtractor,
)
from ipo_risk.extraction.financial import (
    V03FinancialFactExtractor as _BaseV03FinancialFactExtractor,
)
from ipo_risk.extraction.models import ConcentrationFact, ExtractionStatus
from ipo_risk.schemas import DocumentChunk, Evidence


_RECONCILIATION_VERSION = "v045_concentration_period_value_reconciliation_v1"


class _ConcentrationReconciliationMixin:
    """Conservative reconciliation shared by regex and table-aware extractors."""

    @staticmethod
    def _period_candidates_from_fact(
        fact: ConcentrationFact,
    ) -> list[tuple[date, int | None]]:
        raw = fact.metadata.get("period_candidates", [])
        if not isinstance(raw, list):
            return []
        result: list[tuple[date, int | None]] = []
        seen: set[tuple[date, int | None]] = set()
        for item in raw:
            if not isinstance(item, Mapping):
                continue
            raw_end = item.get("period_end")
            if not isinstance(raw_end, str):
                continue
            try:
                end = date.fromisoformat(raw_end)
            except ValueError:
                continue
            raw_months = item.get("period_months")
            months = raw_months if isinstance(raw_months, int) and 1 <= raw_months <= 12 else None
            key = (end, months)
            if key not in seen:
                seen.add(key)
                result.append(key)
        return result

    @classmethod
    def _reconcile_concentration_candidate(
        cls, fact: ConcentrationFact
    ) -> ConcentrationFact:
        """Align a candidate's latest percentages with its latest governed period.

        The base extractor records all candidate periods in metadata.  We use
        those existing facts only; no date is invented.  A value-period-count
        mismatch is cleared only in the narrow case where both disclosed
        concentration series have the same multi-period length and the period
        parser has at most one extra contextual period (the known comparative
        interim/header case).  Any other ambiguity remains needs-review.
        """

        if fact.status == ExtractionStatus.NOT_FOUND:
            return fact

        metadata = dict(fact.metadata)
        metadata["reconciliation_version"] = _RECONCILIATION_VERSION
        periods = cls._period_candidates_from_fact(fact)
        metadata["reconciliation_period_candidate_count"] = len(periods)
        if not periods:
            return fact.model_copy(update={"metadata": metadata})

        latest_end = max(item[0] for item in periods)
        latest = [item for item in periods if item[0] == latest_end]
        latest_months = {item[1] for item in latest}
        issues = list(fact.issues)

        if len(latest_months) != 1:
            if "latest_period_months_ambiguous" not in issues:
                issues.append("latest_period_months_ambiguous")
            metadata["period_reconciliation"] = "ambiguous_latest_period_months"
            return fact.model_copy(
                update={
                    "status": ExtractionStatus.NEEDS_REVIEW,
                    "issues": cls._dedupe_strings(issues),
                    "metadata": metadata,
                }
            )

        resolved_months = next(iter(latest_months))
        if fact.period_end != latest_end or fact.period_months != resolved_months:
            metadata["period_reconciliation"] = "chronological_latest_existing_candidate"
            metadata["period_before_reconciliation"] = {
                "period_end": fact.period_end.isoformat() if fact.period_end else None,
                "period_months": fact.period_months,
            }
        else:
            metadata["period_reconciliation"] = "already_chronological_latest"

        raw_percentages = metadata.get("raw_percentages", {})
        largest_raw = raw_percentages.get("largest", []) if isinstance(raw_percentages, Mapping) else []
        top_five_raw = raw_percentages.get("top_five", []) if isinstance(raw_percentages, Mapping) else []
        largest_count = len(largest_raw) if isinstance(largest_raw, list) else 0
        top_five_count = len(top_five_raw) if isinstance(top_five_raw, list) else 0
        metadata["reconciliation_value_counts"] = {
            "largest": largest_count,
            "top_five": top_five_count,
        }

        can_reconcile_count = (
            "value_period_count_mismatch" in issues
            and fact.largest_counterparty_pct is not None
            and fact.top_five_pct is not None
            and largest_count == top_five_count
            and largest_count >= 2
            and largest_count <= len(periods)
            and len(periods) - largest_count <= 1
        )
        if can_reconcile_count:
            issues = [item for item in issues if item != "value_period_count_mismatch"]
            metadata["value_period_count_reconciled"] = True
            metadata["value_period_alignment"] = "dual_series_to_latest_period_suffix"
        else:
            metadata["value_period_count_reconciled"] = False

        if fact.largest_counterparty_pct is not None and fact.top_five_pct is not None:
            issues = [item for item in issues if item != "incomplete_concentration_values"]

        status = ExtractionStatus.EXTRACTED if not issues else ExtractionStatus.NEEDS_REVIEW
        return fact.model_copy(
            update={
                "period_end": latest_end,
                "period_months": resolved_months,
                "status": status,
                "issues": cls._dedupe_strings(issues),
                "metadata": metadata,
            }
        )

    def _concentration_from_evidence(
        self,
        concentration_type: str,
        evidence: Evidence,
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> ConcentrationFact:
        fact = super()._concentration_from_evidence(
            concentration_type, evidence, chunks_by_id
        )
        return self._reconcile_concentration_candidate(fact)

    def _merge_concentration_facts(
        self, concentration_type: str, facts: Sequence[ConcentrationFact]
    ) -> ConcentrationFact:
        """Merge the latest *usable* period while preserving genuine conflicts.

        A candidate with neither concentration percentage is diagnostic context,
        not a newer concentration observation.  Such candidates remain visible in
        metadata but cannot select the period and discard a valid earlier fact.
        For the selected date, differing period lengths or differing non-null
        values still fail closed exactly as before.
        """

        usable = [
            item
            for item in facts
            if item.period_end is not None
            and (
                item.largest_counterparty_pct is not None
                or item.top_five_pct is not None
            )
        ]
        dated = usable or [item for item in facts if item.period_end is not None]
        selected_date = max((item.period_end for item in dated), default=None)
        selected = (
            [item for item in facts if item.period_end == selected_date]
            if selected_date
            else list(facts)
        )

        governing = [
            item
            for item in selected
            if item.status == ExtractionStatus.EXTRACTED
            and not item.issues
            and item.largest_counterparty_pct is not None
            and item.top_five_pct is not None
        ]
        # A clean, complete candidate governs partial same-date disclosures.
        # Partial summaries remain auditable Evidence, but a single quoted
        # percentage must not veto a complete primary reading.  Multiple clean
        # complete candidates still vote together and therefore fail closed if
        # their values genuinely disagree.
        value_candidates = governing or selected
        period_month_values = {
            item.period_months
            for item in value_candidates
            if item.period_months is not None
        }
        issues: list[str] = []
        if len(period_month_values) > 1:
            issues.append("period_months_conflict")
        if not governing:
            issues.extend(issue for item in selected for issue in item.issues)

        largest_values = {
            item.largest_counterparty_pct
            for item in value_candidates
            if item.largest_counterparty_pct is not None
        }
        top_five_values = {
            item.top_five_pct
            for item in value_candidates
            if item.top_five_pct is not None
        }
        if len(largest_values) > 1 or len(top_five_values) > 1:
            issues.append("conflicting_values_for_same_period")
        if "conflicting_values_for_same_period" in issues and any(
            item.metadata.get("source_context") == "summary"
            for item in value_candidates
        ) and any(
            item.metadata.get("source_context") == "primary_statement"
            for item in value_candidates
        ):
            issues.append("summary_primary_statement_conflict")

        largest = next(iter(largest_values)) if len(largest_values) == 1 else None
        top_five = next(iter(top_five_values)) if len(top_five_values) == 1 else None
        if largest is None or top_five is None:
            issues.append("incomplete_concentration_values")
        else:
            issues = [item for item in issues if item != "incomplete_concentration_values"]
        if largest is not None and top_five is not None and largest > top_five:
            issues.append("largest_percentage_exceeds_top_five")

        issues = self._dedupe_strings(issues)
        evidence_ids = self._dedupe_strings(
            [evidence_id for item in selected for evidence_id in item.evidence_ids]
        )
        first = value_candidates[0]
        selected_months = (
            next(iter(period_month_values)) if len(period_month_values) == 1 else None
        )
        discarded = [item for item in facts if item not in selected]

        candidate_diagnostics: list[dict[str, Any]] = []
        for item in facts:
            candidate_diagnostics.append(
                {
                    "page": item.page,
                    "period_end": item.period_end.isoformat() if item.period_end else None,
                    "period_months": item.period_months,
                    "largest_counterparty_pct": (
                        str(item.largest_counterparty_pct)
                        if item.largest_counterparty_pct is not None
                        else None
                    ),
                    "top_five_pct": str(item.top_five_pct) if item.top_five_pct is not None else None,
                    "status": item.status.value,
                    "issues": list(item.issues),
                    "source_context": item.metadata.get("source_context"),
                    "selected_for_merge": item in selected,
                }
            )

        return ConcentrationFact(
            concentration_type=concentration_type,
            period_end=selected_date,
            period_months=selected_months,
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
                "candidate_count": len(facts),
                "selected_candidate_count": len(selected),
                "discarded_nonselected_candidate_count": len(discarded),
                "governing_candidate_count": len(governing),
                "value_candidate_count": len(value_candidates),
                "merge_value_basis": (
                    "clean_complete_governing_candidates"
                    if governing
                    else "all_selected_candidates_fail_closed"
                ),
                "percentage_semantics": "0_to_100_percent",
                "candidate_pages": [item.page for item in facts],
                "selected_candidate_pages": [item.page for item in selected],
                "merge_selection_basis": (
                    "latest_usable_concentration_period"
                    if usable
                    else "latest_dated_candidate"
                ),
                "reconciliation_version": _RECONCILIATION_VERSION,
                "candidate_diagnostics": candidate_diagnostics,
            },
        )


class V03FinancialFactExtractor(
    _ConcentrationReconciliationMixin, _BaseV03FinancialFactExtractor
):
    """Regex financial extractor with v0.4.5 concentration reconciliation."""


class TableAwareV03FinancialFactExtractor(
    _ConcentrationReconciliationMixin, _BaseTableAwareV03FinancialFactExtractor
):
    """Table-aware extractor with the same concentration reconciliation overlay."""
