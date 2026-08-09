"""Agent-side mapping, Skill invocation, and v0.3 financial risk construction."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
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

        risk_code = f"{fact.concentration_type}_concentration"
        context, issue = self._map_concentration(fact)
        if issue or context is None:
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
        if level is None:
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
        risk = self._risk(
            risk_code=risk_code,
            risk_type=f"{label} concentration",
            level=level,
            conclusion=(
                f"For the {context.period_months}-month period ended "
                f"{observation.period_end.isoformat()}, the largest {label.lower()} "
                f"represented {metadata['largest_counterparty_pct']}% and the top five "
                f"represented {metadata['top_five_pct']}%."
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
        calculation: Calculation,
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
