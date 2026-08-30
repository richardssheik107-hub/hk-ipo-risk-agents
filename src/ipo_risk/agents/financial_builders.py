"""Agent-side mapping, Skill invocation, and v0.3 financial risk construction."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from ipo_risk.agents.financial_models import (
    ConcentrationObservation,
    LossObservation,
    RevenueObservation,
)
from ipo_risk.agents.financial_policy import V03FinancialPolicy
from ipo_risk.extraction import (
    ConcentrationFact,
    ExtractionStatus,
    FinancialPeriodSeriesResult,
)
from ipo_risk.schemas import (
    Calculation,
    ComponentDiagnostic,
    DiagnosticCode,
    DocumentChunk,
    Evidence,
    EvidenceSourceType,
    RiskCategory,
    RiskItem,
    RiskLevel,
    SkillResult,
    VerificationStatus,
)
from ipo_risk.skills.financial import (
    FinancialPeriodInput,
    continuous_loss,
    customer_concentration,
    revenue_growth,
    supplier_concentration,
)


_LEVEL_SCORES = {RiskLevel.HIGH: 80, RiskLevel.MEDIUM: 60}
_LEVEL_RANK = {None: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}
_DISCLOSED_PERCENTAGE = re.compile(r"\s*([+-]?\d+(?:\s*\.\s*\d+)?)\s*[%％]\s*")


@dataclass(frozen=True, slots=True)
class _ConcentrationContext:
    """Keep frozen observation fields and period length together internally."""

    observation: ConcentrationObservation
    period_months: int


@dataclass(frozen=True, slots=True)
class _RiskDecision:
    risk: RiskItem | None
    diagnostic: ComponentDiagnostic


class V03FinancialRiskBuilder:
    """Convert extracted facts into deterministic pending financial risks."""

    def __init__(
        self,
        policy: V03FinancialPolicy,
        *,
        continuous_loss_skill: Callable[[Sequence[FinancialPeriodInput]], SkillResult] = continuous_loss,
        revenue_growth_skill: Callable[[FinancialPeriodInput, FinancialPeriodInput], SkillResult] = revenue_growth,
        customer_concentration_skill: Callable[..., SkillResult] = customer_concentration,
        supplier_concentration_skill: Callable[..., SkillResult] = supplier_concentration,
    ) -> None:
        self.policy = policy
        self.continuous_loss_skill = continuous_loss_skill
        self.revenue_growth_skill = revenue_growth_skill
        self.customer_concentration_skill = customer_concentration_skill
        self.supplier_concentration_skill = supplier_concentration_skill

    def build_continuous_loss(
        self,
        series: FinancialPeriodSeriesResult,
        evidence_by_id: Mapping[str, Evidence],
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> _RiskDecision:
        """Build a continuous-loss candidate from the latest comparable group."""

        mapped, issue = self._map_loss_observations(series)
        if issue:
            return self._review("continuous_loss", issue, series.evidence_ids)
        assert mapped
        selected, selection_issue = self._latest_comparable_losses(mapped)
        if selection_issue:
            return self._review(
                "continuous_loss",
                selection_issue,
                self._observation_evidence_ids(mapped),
                metadata={"available_period_months": sorted({item.period_months for item in mapped})},
            )
        skill_inputs = [
            FinancialPeriodInput(
                value=item.net_result,
                period_end=item.period_end,
                period_months=item.period_months,
                currency=item.currency,
                source_unit=item.unit,
                evidence_ids=item.evidence_ids,
            )
            for item in selected
        ]
        result = self.continuous_loss_skill(skill_inputs)
        if not result.success:
            return self._skill_review("continuous_loss", result)
        count = result.value
        if isinstance(count, bool) or not isinstance(count, int):
            return self._review(
                "continuous_loss",
                "continuous_loss_skill_output_invalid",
                result.evidence_ids,
            )
        evidence, evidence_issue = self._resolve_evidence(
            result.evidence_ids, evidence_by_id, chunks_by_id
        )
        if evidence_issue:
            return self._review(
                "continuous_loss", evidence_issue, result.evidence_ids
            )
        level = self.policy.loss_level(count)
        period_months = selected[0].period_months
        metadata = {
            "rule_version": self.policy.version,
            "latest_loss_period_count": count,
            "period_months": period_months,
            "periods": [item.period_end.isoformat() for item in selected],
        }
        if level is None:
            return self._not_applicable(
                "continuous_loss",
                "Latest comparable loss streak is below the configured threshold.",
                result.evidence_ids,
                metadata,
            )
        calculation = Calculation(
            skill_name=result.skill_name,
            skill_version=result.skill_version,
            inputs={"observations": result.metadata.get("inputs", [])},
            formula="count latest consecutive comparable net_result values below zero",
            result=count,
            unit="periods",
            evidence_ids=result.evidence_ids,
            success=True,
            error=None,
        )
        risk = self._risk(
            risk_code="continuous_loss",
            risk_type="Continuous losses",
            level=level,
            conclusion=(
                f"The latest comparable reporting sequence contains {count} consecutive "
                f"loss periods of {period_months} months each."
            ),
            evidence=evidence,
            calculation=calculation,
            identity_values=[
                *[item.period_end.isoformat() for item in selected],
                *[str(item.net_result) for item in selected],
                str(period_months),
            ],
            metadata=metadata,
        )
        return self._generated(risk, metadata)

    def build_revenue_growth(
        self,
        series: FinancialPeriodSeriesResult,
        evidence_by_id: Mapping[str, Evidence],
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> _RiskDecision:
        """Build revenue-growth risk from the latest two comparable periods."""

        mapped, issue = self._map_revenue_observations(series)
        if issue:
            return self._review("revenue_growth", issue, series.evidence_ids)
        assert mapped
        pair, pair_issue = self._latest_revenue_pair(mapped)
        if pair_issue or pair is None:
            return self._review(
                "revenue_growth",
                pair_issue or "latest_comparable_revenue_pair_missing",
                self._observation_evidence_ids(mapped),
                metadata={"available_period_months": sorted({item.period_months for item in mapped})},
            )
        previous, current = pair
        previous_input = self._revenue_input(previous)
        current_input = self._revenue_input(current)
        result = self.revenue_growth_skill(previous_input, current_input)
        if not result.success:
            return self._skill_review("revenue_growth", result)
        growth = result.value
        if not isinstance(growth, Decimal) or not growth.is_finite():
            return self._review(
                "revenue_growth", "revenue_growth_skill_output_invalid", result.evidence_ids
            )
        evidence, evidence_issue = self._resolve_evidence(
            result.evidence_ids, evidence_by_id, chunks_by_id
        )
        if evidence_issue:
            return self._review("revenue_growth", evidence_issue, result.evidence_ids)
        rounded = result.metadata.get("rounded_percentage")
        rounded_text = str(rounded if isinstance(rounded, Decimal) else growth)
        level = self.policy.revenue_level(growth)
        metadata = {
            "rule_version": self.policy.version,
            "growth_pct_exact": str(growth),
            "growth_pct_rounded": rounded_text,
            "period_months": current.period_months,
            "previous_period_end": previous.period_end.isoformat(),
            "current_period_end": current.period_end.isoformat(),
            "currency": current.currency,
            "source_unit": current.unit,
        }
        if level is None:
            return self._not_applicable(
                "revenue_growth",
                "Latest comparable revenue growth is not below zero.",
                result.evidence_ids,
                metadata,
            )
        calculation = Calculation(
            skill_name=result.skill_name,
            skill_version=result.skill_version,
            inputs={
                "previous_revenue": str(previous.revenue),
                "current_revenue": str(current.revenue),
                "previous_period_end": previous.period_end.isoformat(),
                "current_period_end": current.period_end.isoformat(),
                "period_months": current.period_months,
                "currency": current.currency,
                "source_unit": current.unit,
            },
            formula="(current_revenue - previous_revenue) / previous_revenue * 100",
            result=str(growth),
            unit="percent",
            evidence_ids=result.evidence_ids,
            success=True,
            error=None,
        )
        risk = self._risk(
            risk_code="revenue_growth",
            risk_type="Revenue decline",
            level=level,
            conclusion=(
                f"Revenue changed by {rounded_text}% between the latest two comparable "
                f"{current.period_months}-month reporting periods."
            ),
            evidence=evidence,
            calculation=calculation,
            identity_values=[
                previous.period_end.isoformat(),
                current.period_end.isoformat(),
                str(previous.revenue),
                str(current.revenue),
                str(current.period_months),
            ],
            metadata=metadata,
        )
        return self._generated(risk, metadata)

    def build_concentration(
        self,
        fact: ConcentrationFact,
        evidence_by_id: Mapping[str, Evidence],
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> _RiskDecision:
        """Build customer or supplier concentration risk with period traceability."""

        fact = self._bind_track_record_period_context(fact)
        fact = self._select_track_record_peak(fact)
        fact = self._select_replicated_threshold_candidate(fact)
        risk_code = f"{fact.concentration_type}_concentration"
        context, issue = self._map_concentration(fact)
        if issue or context is None:
            pending = self._build_unresolved_concentration(
                fact,
                risk_code=risk_code,
                issue=issue or "concentration_mapping_failed",
                evidence_by_id=evidence_by_id,
                chunks_by_id=chunks_by_id,
            )
            if pending is not None:
                return pending
            return self._review(
                risk_code,
                issue or "concentration_mapping_failed",
                fact.evidence_ids,
                metadata={"period_months": fact.period_months},
            )
        observation = context.observation
        skill = (
            self.customer_concentration_skill
            if observation.concentration_type == "customer"
            else self.supplier_concentration_skill
        )
        result = skill(
            largest_counterparty_pct=observation.largest_counterparty_pct,
            top_five_pct=observation.top_five_pct,
            evidence_ids=observation.evidence_ids,
        )
        if not result.success:
            return self._skill_review(
                risk_code,
                result,
                metadata={"period_months": context.period_months},
            )
        values = result.value
        if not isinstance(values, Mapping):
            return self._review(
                risk_code,
                "concentration_skill_output_invalid",
                result.evidence_ids,
                metadata={"period_months": context.period_months},
            )
        largest = values.get("largest_counterparty_pct")
        top_five = values.get("top_five_pct")
        if not all(value is None or isinstance(value, Decimal) for value in (largest, top_five)):
            return self._review(
                risk_code,
                "concentration_skill_output_invalid",
                result.evidence_ids,
                metadata={"period_months": context.period_months},
            )
        evidence, evidence_issue = self._resolve_evidence(
            result.evidence_ids, evidence_by_id, chunks_by_id
        )
        if evidence_issue:
            return self._review(
                risk_code,
                evidence_issue,
                result.evidence_ids,
                metadata={"period_months": context.period_months},
            )
        level = self.policy.concentration_level(
            observation.concentration_type, largest, top_five
        )
        metadata = {
            "rule_version": self.policy.version,
            "concentration_type": observation.concentration_type,
            "period_end": observation.period_end.isoformat(),
            "period_months": context.period_months,
            "largest_counterparty_pct": str(largest) if largest is not None else None,
            "top_five_pct": str(top_five) if top_five is not None else None,
        }
        for field in (
            "decision_basis",
            "track_record_period_binding",
            "track_record_peak_index",
            "track_record_largest_series",
            "track_record_top_five_series",
            "latest_selected_values_before_track_record",
            "replicated_threshold_field",
            "replicated_threshold_value",
            "replicated_threshold_evidence_ids",
            "latest_selected_values_before_replication",
        ):
            if field in fact.metadata:
                metadata[field] = fact.metadata[field]
        if level is None:
            unresolved_history = self._track_record_review_fact(fact)
            if unresolved_history is not None:
                pending = self._build_unresolved_concentration(
                    unresolved_history,
                    risk_code=risk_code,
                    issue="track_record_series_incomplete_or_conflicting",
                    evidence_by_id=evidence_by_id,
                    chunks_by_id=chunks_by_id,
                )
                if pending is not None:
                    return pending
            return self._not_applicable(
                risk_code,
                f"Latest {observation.concentration_type} concentration is below configured thresholds.",
                result.evidence_ids,
                metadata,
            )
        calculation = Calculation(
            skill_name=result.skill_name,
            skill_version=result.skill_version,
            inputs={
                "concentration_type": observation.concentration_type,
                "largest_counterparty_pct": metadata["largest_counterparty_pct"],
                "top_five_pct": metadata["top_five_pct"],
                "period_end": observation.period_end.isoformat(),
                "period_months": context.period_months,
            },
            formula="use disclosed percentage points without rescaling",
            result=(
                f"largest={metadata['largest_counterparty_pct']};"
                f"top_five={metadata['top_five_pct']}"
            ),
            unit="percent",
            evidence_ids=result.evidence_ids,
            success=True,
            error=None,
        )
        label = "Customer" if observation.concentration_type == "customer" else "Supplier"
        track_record_peak = metadata.get("decision_basis") == "track_record_peak_disclosed_series"
        risk = self._risk(
            risk_code=risk_code,
            risk_type=f"{label} concentration",
            level=level,
            conclusion=(
                (
                    f"Across the disclosed track-record series ending "
                    f"{observation.period_end.isoformat()}, peak {label.lower()} "
                    f"concentration was {metadata['largest_counterparty_pct']}% for the "
                    f"largest counterparty and {metadata['top_five_pct']}% for the top five."
                )
                if track_record_peak
                else (
                    f"For the {context.period_months}-month period ended "
                    f"{observation.period_end.isoformat()}, the largest {label.lower()} "
                    f"represented {metadata['largest_counterparty_pct']}% and the top five "
                    f"represented {metadata['top_five_pct']}%."
                )
            ),
            evidence=evidence,
            calculation=calculation,
            identity_values=[
                observation.period_end.isoformat(),
                str(context.period_months),
                str(largest),
                str(top_five),
            ],
            metadata=metadata,
        )
        return self._generated(risk, metadata)

    def _bind_track_record_period_context(self, fact: ConcentrationFact) -> ConcentrationFact:
        """Join an aligned percentage series to separately parsed period headers.

        Wide prospectus tables are sometimes retrieved as overlapping chunks: one
        chunk retains the paired largest/top-five series while another retains the
        complete column headers.  Keep the extractor fail-closed, then perform this
        join only when the series lengths agree and an independently parsed final
        period has an exact month count.
        """

        if fact.status == ExtractionStatus.EXTRACTED and not fact.issues:
            return fact
        diagnostics = fact.metadata.get("candidate_diagnostics", [])
        if not isinstance(diagnostics, Sequence) or isinstance(
            diagnostics, (str, bytes)
        ):
            return fact

        for series_item in diagnostics:
            if not isinstance(series_item, Mapping):
                continue
            if set(series_item.get("issues") or []) != {"latest_period_months_ambiguous"}:
                continue
            raw = series_item.get("raw_percentages")
            if not isinstance(raw, Mapping):
                continue
            largest_series = self._percentage_series(raw.get("largest"))
            top_five_series = self._percentage_series(raw.get("top_five"))
            if (
                largest_series is None
                or top_five_series is None
                or len(largest_series) != len(top_five_series)
                or len(largest_series) < 2
                or any(
                    largest > top_five
                    for largest, top_five in zip(largest_series, top_five_series)
                )
            ):
                continue

            for context_item in diagnostics:
                if not isinstance(context_item, Mapping):
                    continue
                raw_end = context_item.get("period_end")
                raw_months = context_item.get("period_months")
                if (
                    not isinstance(raw_end, str)
                    or isinstance(raw_months, bool)
                    or not isinstance(raw_months, int)
                    or not 1 <= raw_months <= 12
                ):
                    continue
                try:
                    period_end = date.fromisoformat(raw_end)
                except ValueError:
                    continue

                sequence_item: Mapping[str, object] | None = None
                for candidate in diagnostics:
                    if not isinstance(candidate, Mapping):
                        continue
                    periods = candidate.get("period_candidates")
                    if (
                        not isinstance(periods, Sequence)
                        or isinstance(periods, (str, bytes))
                        or len(periods) != len(largest_series)
                    ):
                        continue
                    last = periods[-1]
                    if isinstance(last, Mapping) and last.get("period_end") == raw_end:
                        sequence_item = candidate
                        break
                if sequence_item is None:
                    continue

                evidence_ids = list(
                    dict.fromkeys(
                        str(value)
                        for item in (series_item, sequence_item, context_item)
                        for value in item.get("evidence_ids", [])
                        if isinstance(value, str)
                    )
                )
                if not evidence_ids:
                    continue
                metadata = {
                    **fact.metadata,
                    "decision_basis": "track_record_companion_period_binding",
                    "track_record_period_binding": "aligned_series_companion_headers",
                    "track_record_largest_series": [str(value) for value in largest_series],
                    "track_record_top_five_series": [str(value) for value in top_five_series],
                }
                return fact.model_copy(
                    update={
                        "period_end": period_end,
                        "period_months": raw_months,
                        "largest_counterparty_pct": largest_series[-1],
                        "top_five_pct": top_five_series[-1],
                        "evidence_ids": evidence_ids,
                        "status": ExtractionStatus.EXTRACTED,
                        "issues": [],
                        "metadata": metadata,
                    }
                )
        return fact

    def _select_track_record_peak(self, fact: ConcentrationFact) -> ConcentrationFact:
        """Recover a stronger source-backed point from a clean disclosed series.

        The extractor intentionally keeps a single period in the public fact,
        but a prospectus table often discloses an aligned percentage pair for
        every track-record period.  When a clean candidate retains two equally
        sized, internally valid series, preserve the strongest policy-relevant
        pair instead of silently discarding it with the non-latest columns.

        The selected Evidence still contains the complete disclosed series.  We
        bind ``period_end``/``period_months`` only as the series end and state
        that scope explicitly in metadata and the conclusion; no historical
        date is invented for the peak column.
        """

        diagnostics = fact.metadata.get("candidate_diagnostics", [])
        if not isinstance(diagnostics, Sequence) or isinstance(
            diagnostics, (str, bytes)
        ):
            return fact
        current_level = self.policy.concentration_level(
            fact.concentration_type,
            fact.largest_counterparty_pct,
            fact.top_five_pct,
        )
        best: (
            tuple[
                int,
                int,
                date,
                int,
                Decimal,
                Decimal,
                list[str],
                list[str],
                list[str],
            ]
            | None
        ) = None
        for item in diagnostics:
            if not isinstance(item, Mapping):
                continue
            if item.get("status") != ExtractionStatus.EXTRACTED.value or item.get("issues"):
                continue
            raw = item.get("raw_percentages")
            if not isinstance(raw, Mapping):
                continue
            largest_series = self._percentage_series(raw.get("largest"))
            top_five_series = self._percentage_series(raw.get("top_five"))
            if (
                largest_series is None
                or top_five_series is None
                or len(largest_series) != len(top_five_series)
                or len(largest_series) < 2
            ):
                continue
            if any(
                largest > top_five
                for largest, top_five in zip(largest_series, top_five_series)
            ):
                continue
            raw_end = item.get("period_end")
            raw_months = item.get("period_months")
            evidence_ids = [
                str(value)
                for value in item.get("evidence_ids", [])
                if isinstance(value, str)
            ]
            if (
                not isinstance(raw_end, str)
                or isinstance(raw_months, bool)
                or not isinstance(raw_months, int)
                or not 1 <= raw_months <= 12
                or not evidence_ids
            ):
                continue
            try:
                series_end = date.fromisoformat(raw_end)
            except ValueError:
                continue
            for index, (largest, top_five) in enumerate(
                zip(largest_series, top_five_series)
            ):
                level = self.policy.concentration_level(
                    fact.concentration_type, largest, top_five
                )
                rank = _LEVEL_RANK[level]
                candidate = (
                    rank,
                    index,
                    series_end,
                    raw_months,
                    largest,
                    top_five,
                    evidence_ids,
                    [str(value) for value in largest_series],
                    [str(value) for value in top_five_series],
                )
                if best is None or candidate[:2] > best[:2]:
                    best = candidate
        if best is None or best[0] <= _LEVEL_RANK[current_level]:
            return fact
        (
            _rank,
            peak_index,
            series_end,
            series_end_months,
            peak_largest,
            peak_top_five,
            evidence_ids,
            largest_series_text,
            top_five_series_text,
        ) = best
        metadata = {
            **fact.metadata,
            "decision_basis": "track_record_peak_disclosed_series",
            "track_record_period_binding": "series_end_only",
            "track_record_peak_index": peak_index,
            "track_record_largest_series": largest_series_text,
            "track_record_top_five_series": top_five_series_text,
            "latest_selected_values_before_track_record": {
                "period_end": fact.period_end.isoformat() if fact.period_end else None,
                "period_months": fact.period_months,
                "largest_counterparty_pct": (
                    str(fact.largest_counterparty_pct)
                    if fact.largest_counterparty_pct is not None
                    else None
                ),
                "top_five_pct": (
                    str(fact.top_five_pct) if fact.top_five_pct is not None else None
                ),
            },
        }
        return fact.model_copy(
            update={
                "period_end": series_end,
                "period_months": series_end_months,
                "largest_counterparty_pct": peak_largest,
                "top_five_pct": peak_top_five,
                "evidence_ids": evidence_ids,
                "status": ExtractionStatus.EXTRACTED,
                "issues": [],
                "metadata": metadata,
            }
        )

    def _select_replicated_threshold_candidate(
        self, fact: ConcentrationFact
    ) -> ConcentrationFact:
        """Promote a bounded threshold fact repeated by independent Evidence.

        A complete table row can be marked for review when its number of values
        does not match every period header, and a one-sided disclosure can omit
        the companion largest/top-five metric entirely.  Neither condition
        invalidates a directly disclosed value that independently repeats and
        already crosses the frozen policy threshold.  Keep period binding
        strict and exclude 100% one-sided totals, which are commonly table
        totals rather than top-five concentration facts.
        """

        if fact.status == ExtractionStatus.EXTRACTED and not fact.issues:
            return fact
        diagnostics = fact.metadata.get("candidate_diagnostics", [])
        if not isinstance(diagnostics, Sequence) or isinstance(
            diagnostics, (str, bytes)
        ):
            return fact
        allowed_issues = {
            "value_period_count_mismatch",
            "incomplete_concentration_values",
        }
        best: tuple[
            int,
            int,
            date,
            int,
            Decimal | None,
            Decimal | None,
            str,
            Decimal,
            list[str],
        ] | None = None
        for item in diagnostics:
            if not isinstance(item, Mapping):
                continue
            issues = {str(value) for value in item.get("issues") or []}
            raw_end = item.get("period_end")
            raw_months = item.get("period_months")
            if (
                not issues
                or not issues <= allowed_issues
                or not isinstance(raw_end, str)
                or isinstance(raw_months, bool)
                or not isinstance(raw_months, int)
                or not 1 <= raw_months <= 12
            ):
                continue
            try:
                period_end = date.fromisoformat(raw_end)
                largest = self._optional_decimal(item.get("largest_counterparty_pct"))
                top_five = self._optional_decimal(item.get("top_five_pct"))
            except (ValueError, ArithmeticError):
                continue
            if largest is not None and top_five is not None and largest > top_five:
                continue
            for field, value, level in (
                (
                    "largest_counterparty_pct",
                    largest,
                    self.policy.concentration_level(fact.concentration_type, largest, None),
                ),
                (
                    "top_five_pct",
                    top_five,
                    self.policy.concentration_level(fact.concentration_type, None, top_five),
                ),
            ):
                if value is None or value <= 0 or value >= 100 or level is None:
                    continue
                supporting_ids: list[str] = []
                for other in diagnostics:
                    if not isinstance(other, Mapping):
                        continue
                    try:
                        other_value = self._optional_decimal(other.get(field))
                    except (ValueError, ArithmeticError):
                        continue
                    if other_value != value:
                        continue
                    supporting_ids.extend(
                        str(evidence_id)
                        for evidence_id in other.get("evidence_ids") or []
                        if isinstance(evidence_id, str) and evidence_id
                    )
                supporting_ids = list(dict.fromkeys(supporting_ids))
                if len(supporting_ids) < 2:
                    continue
                candidate = (
                    _LEVEL_RANK[level],
                    int(largest is not None) + int(top_five is not None),
                    period_end,
                    raw_months,
                    largest,
                    top_five,
                    field,
                    value,
                    supporting_ids,
                )
                if best is None or candidate[:3] > best[:3]:
                    best = candidate
        if best is None:
            return fact
        (
            _rank,
            _completeness,
            period_end,
            period_months,
            largest,
            top_five,
            replicated_field,
            replicated_value,
            evidence_ids,
        ) = best
        return fact.model_copy(
            update={
                "period_end": period_end,
                "period_months": period_months,
                "largest_counterparty_pct": largest,
                "top_five_pct": top_five,
                "evidence_ids": evidence_ids,
                "status": ExtractionStatus.EXTRACTED,
                "issues": [],
                "metadata": {
                    **fact.metadata,
                    "decision_basis": "replicated_threshold_disclosure",
                    "replicated_threshold_field": replicated_field,
                    "replicated_threshold_value": str(replicated_value),
                    "replicated_threshold_evidence_ids": evidence_ids,
                    "latest_selected_values_before_replication": {
                        "period_end": fact.period_end.isoformat() if fact.period_end else None,
                        "period_months": fact.period_months,
                        "largest_counterparty_pct": (
                            str(fact.largest_counterparty_pct)
                            if fact.largest_counterparty_pct is not None
                            else None
                        ),
                        "top_five_pct": (
                            str(fact.top_five_pct)
                            if fact.top_five_pct is not None
                            else None
                        ),
                    },
                },
            }
        )

    @staticmethod
    def _optional_decimal(value: object) -> Decimal | None:
        if value is None:
            return None
        converted = Decimal(str(value))
        if not converted.is_finite() or converted < 0 or converted > 100:
            raise ValueError("concentration_percentage_invalid")
        return converted

    def _track_record_review_fact(
        self, fact: ConcentrationFact
    ) -> ConcentrationFact | None:
        """Keep a bounded incomplete companion series visible for review."""

        diagnostics = fact.metadata.get("candidate_diagnostics", [])
        if not isinstance(diagnostics, Sequence) or isinstance(
            diagnostics, (str, bytes)
        ):
            return None
        clean_paired_series = False
        unresolved_evidence_ids: list[str] = []
        unresolved_issue_codes: list[str] = []
        allowed = {
            "missing_period",
            "incomplete_concentration_values",
            "value_period_count_mismatch",
            "latest_period_months_ambiguous",
        }
        for item in diagnostics:
            if not isinstance(item, Mapping):
                continue
            raw = item.get("raw_percentages")
            if not isinstance(raw, Mapping):
                continue
            largest_series = self._percentage_series(raw.get("largest"))
            top_five_series = self._percentage_series(raw.get("top_five"))
            issues = {str(value) for value in item.get("issues", [])}
            if (
                item.get("status") == ExtractionStatus.EXTRACTED.value
                and not issues
                and largest_series is not None
                and top_five_series is not None
                and len(largest_series) == len(top_five_series)
                and len(largest_series) >= 2
            ):
                clean_paired_series = True
                continue
            one_sided_series = (
                largest_series is None
                and top_five_series is not None
                and len(top_five_series) >= 2
            ) or (
                top_five_series is None
                and largest_series is not None
                and len(largest_series) >= 2
            )
            if (
                item.get("status") == ExtractionStatus.NEEDS_REVIEW.value
                and one_sided_series
                and issues
                and issues <= allowed
            ):
                unresolved_evidence_ids.extend(
                    str(value)
                    for value in item.get("evidence_ids", [])
                    if isinstance(value, str)
                )
                unresolved_issue_codes.extend(sorted(issues))
        if not clean_paired_series or not unresolved_evidence_ids:
            return None
        evidence_ids = list(
            dict.fromkeys([*fact.evidence_ids, *unresolved_evidence_ids])
        )
        return fact.model_copy(
            update={
                "evidence_ids": evidence_ids,
                "status": ExtractionStatus.NEEDS_REVIEW,
                "issues": ["track_record_series_incomplete_or_conflicting"],
                "metadata": {
                    **fact.metadata,
                    "decision_basis": "track_record_series_requires_review",
                    "track_record_unresolved_issue_codes": list(
                        dict.fromkeys(unresolved_issue_codes)
                    ),
                },
            }
        )

    @staticmethod
    def _percentage_series(raw: object) -> list[Decimal] | None:
        if not isinstance(raw, list) or not raw:
            return None
        values: list[Decimal] = []
        for item in raw:
            if not isinstance(item, str):
                return None
            matched = _DISCLOSED_PERCENTAGE.fullmatch(item)
            if matched is None:
                return None
            value = Decimal(re.sub(r"\s+", "", matched.group(1)))
            if not value.is_finite() or value < 0 or value > 100:
                return None
            values.append(value)
        return values

    def build_qualitative_concentration_review(
        self,
        *,
        concentration_type: str,
        signal_code: str,
        evidence_ids: Sequence[str],
        evidence_by_id: Mapping[str, Evidence],
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> _RiskDecision:
        """Preserve explicit qualitative ambiguity without inventing a ratio."""

        risk_code = f"{concentration_type}_concentration"
        evidence, evidence_issue = self._resolve_evidence(
            evidence_ids,
            evidence_by_id,
            chunks_by_id,
        )
        if evidence_issue or not evidence:
            return self._review(
                risk_code,
                evidence_issue or "qualitative_concentration_evidence_missing",
                evidence_ids,
            )
        label = "Customer" if concentration_type == "customer" else "Supplier"
        metadata = {
            "rule_version": self.policy.version,
            "concentration_type": concentration_type,
            "issue": signal_code,
            "candidate_state": "qualitative_concentration_signal_requires_review",
            "provisional_level": True,
            "calculation_unavailable": True,
            "percentage_inferred": False,
        }
        risk = self._risk(
            risk_code=risk_code,
            risk_type=f"{label} concentration",
            level=RiskLevel.MEDIUM,
            conclusion=(
                f"Explicit {label.lower()} concentration disclosure requires "
                "human review because no deterministic percentage can be established."
            ),
            evidence=evidence,
            calculation=None,
            identity_values=["qualitative_review", signal_code],
            metadata=metadata,
        )
        return self._generated(risk, metadata)

    def _build_unresolved_concentration(
        self,
        fact: ConcentrationFact,
        *,
        risk_code: str,
        issue: str,
        evidence_by_id: Mapping[str, Evidence],
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> _RiskDecision | None:
        """Preserve a bounded percentage signal as an honest pending risk.

        A concentration candidate may contain one or more deterministic
        percentages while period/value reconciliation remains fail-closed.  A
        diagnostic alone is invisible to the specialized Verifier and Human
        Review.  Emitting a pending RiskItem keeps the real Evidence attached
        without asserting a threshold, calculation, or verified severity.

        Candidates with no parsed percentage remain diagnostics only; this
        prevents a generic retrieval hit from becoming a risk.
        """

        diagnostics = fact.metadata.get("candidate_diagnostics", [])
        bounded_signal = fact.largest_counterparty_pct is not None or fact.top_five_pct is not None
        if isinstance(diagnostics, Sequence) and not isinstance(diagnostics, (str, bytes)):
            bounded_signal = bounded_signal or any(
                isinstance(item, Mapping)
                and (
                    item.get("largest_counterparty_pct") is not None
                    or item.get("top_five_pct") is not None
                )
                for item in diagnostics
            )
        if not bounded_signal or not fact.evidence_ids:
            return None

        evidence, evidence_issue = self._resolve_evidence(
            fact.evidence_ids, evidence_by_id, chunks_by_id
        )
        if evidence_issue or not evidence:
            return None

        label = "Customer" if fact.concentration_type == "customer" else "Supplier"
        metadata = {
            "rule_version": self.policy.version,
            "concentration_type": fact.concentration_type,
            "issue": issue,
            "extraction_issues": list(fact.issues),
            "candidate_state": "bounded_percentage_signal_requires_review",
            "provisional_level": True,
            "calculation_unavailable": True,
            "period_end": fact.period_end.isoformat() if fact.period_end else None,
            "period_months": fact.period_months,
        }
        for field in (
            "decision_basis",
            "track_record_unresolved_issue_codes",
        ):
            if field in fact.metadata:
                metadata[field] = fact.metadata[field]
        risk = self._risk(
            risk_code=risk_code,
            risk_type=f"{label} concentration",
            level=RiskLevel.MEDIUM,
            conclusion=(
                f"Bounded {label.lower()} concentration evidence requires deterministic "
                "period/value reconciliation before verification."
            ),
            evidence=evidence,
            calculation=None,
            identity_values=[
                "unresolved",
                str(fact.period_end or ""),
                str(fact.period_months or ""),
                issue,
            ],
            metadata=metadata,
        )
        return self._generated(risk, metadata)

    @staticmethod
    def _map_loss_observations(
        series: FinancialPeriodSeriesResult,
    ) -> tuple[list[LossObservation], str | None]:
        if series.status != ExtractionStatus.EXTRACTED or series.issues:
            return [], "loss_extraction_not_clean"
        mapped: list[LossObservation] = []
        for fact in series.observations:
            if (
                fact.status != ExtractionStatus.EXTRACTED
                or fact.metric_name != "net_result"
                or fact.period_end is None
                or fact.period_months is None
                or fact.normalized_value is None
                or not fact.currency
                or not fact.unit
                or not fact.evidence_ids
            ):
                return [], "loss_observation_incomplete"
            mapped.append(
                LossObservation(
                    period_end=fact.period_end,
                    period_months=fact.period_months,
                    net_result=fact.normalized_value,
                    currency=fact.currency,
                    unit=fact.unit,
                    evidence_ids=fact.evidence_ids,
                )
            )
        return mapped, None if mapped else "loss_observations_missing"

    @staticmethod
    def _map_revenue_observations(
        series: FinancialPeriodSeriesResult,
    ) -> tuple[list[RevenueObservation], str | None]:
        if series.status != ExtractionStatus.EXTRACTED or series.issues:
            return [], "revenue_extraction_not_clean"
        mapped: list[RevenueObservation] = []
        for fact in series.observations:
            if (
                fact.status != ExtractionStatus.EXTRACTED
                or fact.metric_name != "revenue"
                or fact.period_end is None
                or fact.period_months is None
                or fact.normalized_value is None
                or not fact.currency
                or not fact.unit
                or not fact.evidence_ids
            ):
                return [], "revenue_observation_incomplete"
            mapped.append(
                RevenueObservation(
                    period_end=fact.period_end,
                    period_months=fact.period_months,
                    revenue=fact.normalized_value,
                    currency=fact.currency,
                    unit=fact.unit,
                    evidence_ids=fact.evidence_ids,
                )
            )
        return mapped, None if mapped else "revenue_observations_missing"

    @staticmethod
    def _map_concentration(
        fact: ConcentrationFact,
    ) -> tuple[_ConcentrationContext | None, str | None]:
        if fact.status != ExtractionStatus.EXTRACTED or fact.issues:
            return None, "concentration_extraction_not_clean"
        if fact.period_end is None:
            return None, "concentration_period_end_missing"
        if fact.period_months is None:
            return None, "concentration_period_months_missing"
        if not fact.evidence_ids:
            return None, "concentration_evidence_ids_missing"
        if fact.largest_counterparty_pct is None and fact.top_five_pct is None:
            return None, "concentration_values_missing"
        observation = ConcentrationObservation(
            concentration_type=fact.concentration_type,
            period_end=fact.period_end,
            largest_counterparty_pct=fact.largest_counterparty_pct,
            top_five_pct=fact.top_five_pct,
            evidence_ids=fact.evidence_ids,
        )
        return _ConcentrationContext(observation, fact.period_months), None

    @staticmethod
    def _latest_comparable_losses(
        observations: Sequence[LossObservation],
    ) -> tuple[list[LossObservation], str | None]:
        ordered = sorted(observations, key=lambda item: item.period_end)
        latest = ordered[-1]
        selected = [
            item
            for item in ordered
            if (
                item.period_months,
                item.currency.upper(),
                item.unit.lower(),
            )
            == (
                latest.period_months,
                latest.currency.upper(),
                latest.unit.lower(),
            )
        ]
        if len(selected) < 2 and len(ordered) > 1:
            return [], "latest_loss_period_has_no_comparable_peer"
        return selected, None

    @staticmethod
    def _latest_revenue_pair(
        observations: Sequence[RevenueObservation],
    ) -> tuple[tuple[RevenueObservation, RevenueObservation] | None, str | None]:
        ordered = sorted(observations, key=lambda item: item.period_end)
        current = ordered[-1]
        comparable = [
            item
            for item in ordered[:-1]
            if (
                item.period_months,
                item.currency.upper(),
                item.unit.lower(),
            )
            == (
                current.period_months,
                current.currency.upper(),
                current.unit.lower(),
            )
        ]
        if not comparable:
            return None, "latest_comparable_revenue_pair_missing"
        return (comparable[-1], current), None

    @staticmethod
    def _revenue_input(observation: RevenueObservation) -> FinancialPeriodInput:
        return FinancialPeriodInput(
            value=observation.revenue,
            period_end=observation.period_end,
            period_months=observation.period_months,
            currency=observation.currency,
            source_unit=observation.unit,
            evidence_ids=observation.evidence_ids,
        )

    @staticmethod
    def _resolve_evidence(
        evidence_ids: Sequence[str],
        evidence_by_id: Mapping[str, Evidence],
        chunks_by_id: Mapping[str, DocumentChunk],
    ) -> tuple[list[Evidence], str | None]:
        resolved: list[Evidence] = []
        for evidence_id in dict.fromkeys(evidence_ids):
            evidence = evidence_by_id.get(evidence_id)
            if evidence is None:
                return [], "referenced_evidence_not_found"
            if (
                not evidence.document_id
                or not evidence.chunk_id
                or evidence.page is None
                or evidence.source_type != EvidenceSourceType.PROSPECTUS
            ):
                return [], "referenced_evidence_identity_incomplete"
            chunk = chunks_by_id.get(evidence.chunk_id)
            if chunk is None:
                return [], "referenced_evidence_chunk_not_found"
            if (
                chunk.document_id != evidence.document_id
                or chunk.chunk_id != evidence.chunk_id
                or chunk.page != evidence.page
            ):
                return [], "referenced_evidence_identity_mismatch"
            resolved.append(evidence)
        if len(resolved) != len(dict.fromkeys(evidence_ids)):
            return [], "referenced_evidence_resolution_incomplete"
        return resolved, None

    def _risk(
        self,
        *,
        risk_code: str,
        risk_type: str,
        level: RiskLevel,
        conclusion: str,
        evidence: list[Evidence],
        calculation: Calculation | None,
        identity_values: Sequence[str],
        metadata: Mapping[str, object],
    ) -> RiskItem:
        evidence_ids = [item.evidence_id for item in evidence]
        risk_id = str(
            uuid5(
                NAMESPACE_URL,
                "v03-financial:"
                + ":".join([risk_code, *evidence_ids, *identity_values]),
            )
        )
        return RiskItem(
            risk_id=risk_id,
            risk_code=risk_code,
            category=RiskCategory.FINANCIAL,
            risk_type=risk_type,
            level=level,
            score=_LEVEL_SCORES[level],
            conclusion=conclusion,
            evidence=evidence,
            calculation=calculation,
            agent_name="financial",
            confidence=0.90,
            verification_status=VerificationStatus.PENDING,
            verification_notes="",
            metadata={
                **metadata,
                "score_is_rule_based": True,
                "score_is_probability": False,
            },
        )

    def _generated(
        self, risk: RiskItem, metadata: Mapping[str, object]
    ) -> _RiskDecision:
        return _RiskDecision(
            risk,
            ComponentDiagnostic(
                risk_code=risk.risk_code,
                code=DiagnosticCode.RISK_GENERATED,
                message="A pending financial risk was generated for Verifier review.",
                recoverable=True,
                evidence_ids=[item.evidence_id for item in risk.evidence],
                metadata=dict(metadata),
            ),
        )

    def _not_applicable(
        self,
        risk_code: str,
        message: str,
        evidence_ids: Sequence[str],
        metadata: Mapping[str, object],
    ) -> _RiskDecision:
        return _RiskDecision(
            None,
            ComponentDiagnostic(
                risk_code=risk_code,
                code=DiagnosticCode.NOT_APPLICABLE,
                message=message,
                recoverable=True,
                evidence_ids=list(dict.fromkeys(evidence_ids)),
                metadata=dict(metadata),
            ),
        )

    def _skill_review(
        self,
        risk_code: str,
        result: SkillResult,
        *,
        metadata: Mapping[str, object] | None = None,
    ) -> _RiskDecision:
        return self._review(
            risk_code,
            "deterministic_skill_failed",
            result.evidence_ids,
            metadata={
                "skill_name": result.skill_name,
                "skill_version": result.skill_version,
                "skill_error": result.error,
                **dict(metadata or {}),
            },
        )

    def _review(
        self,
        risk_code: str,
        issue: str,
        evidence_ids: Sequence[str],
        *,
        metadata: Mapping[str, object] | None = None,
    ) -> _RiskDecision:
        return _RiskDecision(
            None,
            ComponentDiagnostic(
                risk_code=risk_code,
                code=DiagnosticCode.NEEDS_REVIEW,
                message="Financial facts or deterministic calculation require review.",
                recoverable=True,
                evidence_ids=list(dict.fromkeys(evidence_ids)),
                metadata={
                    "rule_version": self.policy.version,
                    "issue": issue,
                    **dict(metadata or {}),
                },
            ),
        )

    @staticmethod
    def _observation_evidence_ids(
        observations: Sequence[LossObservation | RevenueObservation],
    ) -> list[str]:
        return list(
            dict.fromkeys(
                evidence_id
                for observation in observations
                for evidence_id in observation.evidence_ids
            )
        )
