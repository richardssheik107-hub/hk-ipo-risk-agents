"""Deterministic, standalone verification for v0.3 financial risks."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from ipo_risk.agents.financial_policy import (
    RULE_VERSION,
    V03FinancialPolicy,
    load_v03_financial_policy,
)
from ipo_risk.domain.cash_runway_verifier import (
    CashRunwayRiskVerifier,
    CashRunwayVerificationStatus,
)
from ipo_risk.domain.risk_codes import V03_RISK_OWNERS
from ipo_risk.schemas import (
    Calculation,
    Evidence,
    EvidenceSourceType,
    RiskCategory,
    RiskItem,
    RiskLevel,
    SkillResult,
    VerificationResult,
    VerificationStatus,
)
from ipo_risk.skills.financial import (
    FinancialPeriodInput,
    continuous_loss,
    customer_concentration,
    revenue_growth,
    supplier_concentration,
)


_FINANCIAL_CODES = tuple(
    risk_code for risk_code, owner in V03_RISK_OWNERS.items() if owner == "financial"
)
_NEW_FINANCIAL_CODES = _FINANCIAL_CODES[1:]
_SCORES = {RiskLevel.MEDIUM: Decimal("60"), RiskLevel.HIGH: Decimal("80")}
_FORMULAS = {
    "continuous_loss": "count latest consecutive comparable net_result values below zero",
    "revenue_growth": "(current_revenue - previous_revenue) / previous_revenue * 100",
    "customer_concentration": "use disclosed percentage points without rescaling",
    "supplier_concentration": "use disclosed percentage points without rescaling",
}
_UNITS = {
    "continuous_loss": "periods",
    "revenue_growth": "percent",
    "customer_concentration": "percent",
    "supplier_concentration": "percent",
}
_BANNED_CLAIMS = (
    "必然破产",
    "必然下跌",
    "必然违约",
    "will go bankrupt",
    "will certainly decline",
    "guaranteed default",
)
@dataclass(frozen=True, slots=True)
class _ReviewDecision:
    """Private classification for one input risk."""

    bucket: str
    risk: RiskItem


class V03FinancialVerifier:
    """Recalculate and classify v0.3 financial RiskItems deterministically."""

    name = "verifier"

    def __init__(
        self,
        *,
        policy: V03FinancialPolicy | None = None,
        cash_runway_verifier: CashRunwayRiskVerifier | None = None,
        continuous_loss_skill: Callable[[Sequence[FinancialPeriodInput]], SkillResult] = continuous_loss,
        revenue_growth_skill: Callable[[FinancialPeriodInput, FinancialPeriodInput], SkillResult] = revenue_growth,
        customer_concentration_skill: Callable[..., SkillResult] = customer_concentration,
        supplier_concentration_skill: Callable[..., SkillResult] = supplier_concentration,
    ) -> None:
        self.policy = policy or load_v03_financial_policy()
        self.cash_runway_verifier = cash_runway_verifier or CashRunwayRiskVerifier()
        self.continuous_loss_skill = continuous_loss_skill
        self.revenue_growth_skill = revenue_growth_skill
        self.customer_concentration_skill = customer_concentration_skill
        self.supplier_concentration_skill = supplier_concentration_skill

    def verify(
        self,
        risks: list[RiskItem],
        evidence_by_code: dict[str, list[Evidence]],
    ) -> VerificationResult:
        """Return one stable classification for every input risk."""

        verified: list[RiskItem] = []
        pending: list[RiskItem] = []
        rejected: list[RiskItem] = []
        for risk in risks:
            decision = self._verify_one(risk, evidence_by_code.get(risk.risk_code, []))
            {"verified": verified, "pending": pending, "rejected": rejected}[
                decision.bucket
            ].append(decision.risk)
        return VerificationResult(
            verified_risks=verified,
            pending_risks=pending,
            rejected_risks=rejected,
        )

    def _verify_one(
        self, risk: RiskItem, external_evidence: Sequence[Evidence]
    ) -> _ReviewDecision:
        if risk.risk_code not in _FINANCIAL_CODES:
            status = (
                VerificationStatus.NEEDS_REVIEW
                if risk.verification_status == VerificationStatus.NEEDS_REVIEW
                else VerificationStatus.PENDING
            )
            return self._pending(
                risk,
                status,
                "Risk is outside the v0.3 Financial Verifier scope.",
            )
        if risk.risk_code == "cash_runway":
            return self._verify_cash_runway(risk, external_evidence)
        return self._verify_new_financial_risk(risk, external_evidence)

    def _verify_cash_runway(
        self, risk: RiskItem, external_evidence: Sequence[Evidence]
    ) -> _ReviewDecision:
        available = {item.evidence_id: item for item in risk.evidence}
        for item in external_evidence:
            available[item.evidence_id] = item
        outcome = self.cash_runway_verifier.verify(risk, available)
        if outcome.status == CashRunwayVerificationStatus.VERIFIED:
            if risk.metadata.get("rule_version") != self.policy.version:
                return self._pending(
                    risk,
                    VerificationStatus.NEEDS_REVIEW,
                    "Cash runway verification needs review: rule_version_invalid",
                )
            assert outcome.verified_risk is not None
            return _ReviewDecision("verified", outcome.verified_risk)
        return _ReviewDecision("pending", outcome.reviewed_risk)

    def _verify_new_financial_risk(
        self, risk: RiskItem, external_evidence: Sequence[Evidence]
    ) -> _ReviewDecision:
        identity_error = self._identity_error(risk)
        if identity_error:
            return self._reject(risk, identity_error)
        if risk.verification_status == VerificationStatus.NEEDS_REVIEW:
            return self._pending(
                risk,
                VerificationStatus.NEEDS_REVIEW,
                "Input candidate already requires review.",
            )
        if risk.verification_status != VerificationStatus.PENDING:
            return self._reject(risk, "input_verification_status_invalid")

        evidence_decision = self._evidence_decision(risk, external_evidence)
        if evidence_decision is not None:
            return evidence_decision
        calculation = risk.calculation
        if calculation is None:
            return self._pending(
                risk, VerificationStatus.NEEDS_REVIEW, "Calculation is missing."
            )
        if calculation.success is not True or calculation.error is not None:
            return self._pending(
                risk,
                VerificationStatus.NEEDS_REVIEW,
                "Calculation is not a successful deterministic result.",
            )
        contract_error = self._calculation_contract_error(risk.risk_code, calculation)
        if contract_error:
            return self._reject(risk, contract_error)
        if not isinstance(calculation.inputs, Mapping) or not calculation.inputs:
            return self._pending(
                risk,
                VerificationStatus.NEEDS_REVIEW,
                "Calculation inputs are missing or cannot be parsed.",
            )
        if self._has_ambiguous_upstream_marker(risk.metadata):
            return self._pending(
                risk,
                VerificationStatus.NEEDS_REVIEW,
                "Upstream facts contain a conflict or unsupported-layout marker.",
            )

        recalculated, input_error = self._recalculate(risk.risk_code, calculation)
        if input_error:
            return self._pending(
                risk,
                VerificationStatus.NEEDS_REVIEW,
                f"Calculation inputs require review: {input_error}",
            )
        assert recalculated is not None
        if not recalculated.success:
            return self._pending(
                risk,
                VerificationStatus.NEEDS_REVIEW,
                f"Deterministic Skill could not recalculate: {recalculated.error}",
            )
        deterministic_error = self._deterministic_error(risk, calculation, recalculated)
        if deterministic_error:
            return self._reject(risk, deterministic_error)
        if not self._evidence_supports_inputs(risk, calculation):
            return self._pending(
                risk,
                VerificationStatus.NEEDS_REVIEW,
                "Evidence text does not stably support the Calculation inputs.",
            )
        if not self._conclusion_supported(risk, recalculated):
            return self._pending(
                risk,
                VerificationStatus.NEEDS_REVIEW,
                "Risk conclusion requires human review.",
            )
        verified = risk.model_copy(
            update={
                "verification_status": VerificationStatus.VERIFIED,
                "verification_notes": (
                    "Evidence identity and Calculation references passed; the Decimal Skill "
                    "was independently recalculated; level and deterministic rule score "
                    "matched v03_contract_v1. The score is not a probability."
                ),
            }
        )
        return _ReviewDecision("verified", verified)

    def _identity_error(self, risk: RiskItem) -> str | None:
        if V03_RISK_OWNERS.get(risk.risk_code) != "financial":
            return "risk_owner_invalid"
        if risk.category != RiskCategory.FINANCIAL:
            return "risk_category_invalid"
        if risk.agent_name != "financial":
            return "agent_name_invalid"
        if risk.metadata.get("score_is_rule_based") is not True:
            return "score_is_rule_based_invalid"
        if risk.metadata.get("score_is_probability") is not False:
            return "score_is_probability_invalid"
        if risk.metadata.get("rule_version") != RULE_VERSION:
            return "rule_version_invalid"
        return None

    def _evidence_decision(
        self, risk: RiskItem, external_evidence: Sequence[Evidence]
    ) -> _ReviewDecision | None:
        if not risk.evidence:
            return self._pending(
                risk, VerificationStatus.PENDING, "Embedded Evidence is not available."
            )
        ids = [item.evidence_id for item in risk.evidence]
        if any(not item for item in ids) or len(ids) != len(set(ids)):
            return self._reject(risk, "embedded_evidence_id_invalid")
        for item in risk.evidence:
            if not item.document_id or not item.chunk_id or item.page is None:
                return self._pending(
                    risk,
                    VerificationStatus.NEEDS_REVIEW,
                    "Embedded Evidence identity is incomplete.",
                )
            if item.source_type != EvidenceSourceType.PROSPECTUS:
                return self._reject(risk, "evidence_source_type_invalid")
            if not item.text.strip():
                return self._pending(
                    risk,
                    VerificationStatus.NEEDS_REVIEW,
                    "Embedded Evidence text is empty.",
                )
        documents = {item.document_id for item in risk.evidence}
        if len(documents) != 1:
            return self._reject(risk, "cross_document_evidence")
        calculation = risk.calculation
        if calculation is not None and not set(calculation.evidence_ids) <= set(ids):
            return self._reject(risk, "calculation_evidence_outside_risk")

        if not external_evidence:
            return None
        external_by_id: dict[str, Evidence] = {}
        for item in external_evidence:
            previous = external_by_id.get(item.evidence_id)
            if previous is not None and not self._same_evidence(previous, item):
                return self._reject(risk, "conflicting_external_evidence")
            external_by_id[item.evidence_id] = item
        required_ids = set(calculation.evidence_ids if calculation else ids)
        if not required_ids <= set(external_by_id):
            return self._pending(
                risk,
                VerificationStatus.PENDING,
                "Referenced external Evidence is temporarily unavailable.",
            )
        embedded_by_id = {item.evidence_id: item for item in risk.evidence}
        if any(
            not self._same_evidence(embedded_by_id[evidence_id], external_by_id[evidence_id])
            for evidence_id in required_ids
        ):
            return self._reject(risk, "external_evidence_identity_or_text_mismatch")
        return None

    @staticmethod
    def _same_evidence(left: Evidence, right: Evidence) -> bool:
        return all(
            getattr(left, field) == getattr(right, field)
            for field in (
                "evidence_id",
                "document_id",
                "chunk_id",
                "page",
                "source_type",
            )
        ) and " ".join(left.text.split()) == " ".join(right.text.split())

    @staticmethod
    def _calculation_contract_error(
        risk_code: str, calculation: Calculation
    ) -> str | None:
        expected_skill = risk_code
        if calculation.skill_name != expected_skill:
            return "calculation_skill_name_invalid"
        if calculation.skill_version != "1.0":
            return "calculation_skill_version_invalid"
        if calculation.formula != _FORMULAS[risk_code]:
            return "calculation_formula_invalid"
        if calculation.unit != _UNITS[risk_code]:
            return "calculation_unit_invalid"
        if risk_code.endswith("_concentration") and calculation.inputs.get(
            "concentration_type"
        ) != risk_code.removesuffix("_concentration"):
            return "concentration_type_mismatch"
        return None

    def _recalculate(
        self, risk_code: str, calculation: Calculation
    ) -> tuple[SkillResult | None, str | None]:
        try:
            if risk_code == "continuous_loss":
                raw = calculation.inputs.get("observations")
                if not isinstance(raw, list) or not raw:
                    return None, "observations_missing"
                observations = [self._period_input(item, "net_result") for item in raw]
                if any(item is None for item in observations):
                    return None, "observation_input_incomplete"
                return self.continuous_loss_skill(observations), None  # type: ignore[arg-type]
            if risk_code == "revenue_growth":
                inputs = calculation.inputs
                required = (
                    "previous_revenue",
                    "current_revenue",
                    "previous_period_end",
                    "current_period_end",
                    "period_months",
                    "currency",
                    "source_unit",
                )
                if any(name not in inputs for name in required):
                    return None, "revenue_input_incomplete"
                evidence_ids = list(calculation.evidence_ids)
                previous = FinancialPeriodInput(
                    value=inputs["previous_revenue"],
                    period_end=inputs["previous_period_end"],
                    period_months=inputs["period_months"],
                    currency=inputs["currency"],
                    source_unit=inputs["source_unit"],
                    evidence_ids=evidence_ids,
                )
                current = FinancialPeriodInput(
                    value=inputs["current_revenue"],
                    period_end=inputs["current_period_end"],
                    period_months=inputs["period_months"],
                    currency=inputs["currency"],
                    source_unit=inputs["source_unit"],
                    evidence_ids=evidence_ids,
                )
                return self.revenue_growth_skill(previous, current), None
            concentration_type = calculation.inputs.get("concentration_type")
            expected_type = risk_code.removesuffix("_concentration")
            if concentration_type != expected_type:
                return None, "concentration_type_mismatch"
            required = ("period_end", "period_months")
            if any(name not in calculation.inputs for name in required):
                return None, "concentration_period_incomplete"
            if self._date(calculation.inputs["period_end"]) is None:
                return None, "concentration_period_end_invalid"
            months = calculation.inputs["period_months"]
            if isinstance(months, bool) or not isinstance(months, int) or not 1 <= months <= 12:
                return None, "concentration_period_months_invalid"
            skill = (
                self.customer_concentration_skill
                if expected_type == "customer"
                else self.supplier_concentration_skill
            )
            return skill(
                largest_counterparty_pct=calculation.inputs.get("largest_counterparty_pct"),
                top_five_pct=calculation.inputs.get("top_five_pct"),
                evidence_ids=calculation.evidence_ids,
            ), None
        except (KeyError, TypeError, ValueError, InvalidOperation):
            return None, "calculation_input_parse_failed"
        except Exception as exc:
            return None, f"skill_recalculation_failure:{type(exc).__name__}"

    @classmethod
    def _period_input(
        cls, raw: object, value_key: str
    ) -> FinancialPeriodInput | None:
        if not isinstance(raw, Mapping):
            return None
        required = (
            value_key,
            "period_end",
            "period_months",
            "currency",
            "source_unit",
            "evidence_ids",
        )
        if any(name not in raw for name in required) or not isinstance(raw["evidence_ids"], list):
            return None
        return FinancialPeriodInput(
            value=raw[value_key],
            period_end=raw["period_end"],
            period_months=raw["period_months"],
            currency=raw["currency"],
            source_unit=raw["source_unit"],
            evidence_ids=raw["evidence_ids"],
        )

    def _deterministic_error(
        self, risk: RiskItem, calculation: Calculation, result: SkillResult
    ) -> str | None:
        if list(result.evidence_ids) != list(calculation.evidence_ids):
            return "calculation_evidence_ids_mismatch"
        if risk.risk_code == "continuous_loss":
            if self._decimal(calculation.result) != self._decimal(result.value):
                return "calculation_result_mismatch"
            count = result.value if isinstance(result.value, int) and not isinstance(result.value, bool) else -1
            level = self.policy.loss_level(count)
            if risk.metadata.get("latest_loss_period_count") != count:
                return "risk_metadata_result_mismatch"
            observations = calculation.inputs.get("observations", [])
            period_months = result.metadata.get("period_months")
            periods = [
                item.get("period_end")
                for item in observations
                if isinstance(item, Mapping)
            ]
            if risk.metadata.get("period_months") != period_months:
                return "risk_metadata_period_mismatch"
            if risk.metadata.get("periods") != periods:
                return "risk_metadata_period_mismatch"
        elif risk.risk_code == "revenue_growth":
            exact = self._decimal(result.value)
            if exact is None or self._decimal(calculation.result) != exact:
                return "calculation_result_mismatch"
            level = self.policy.revenue_level(exact)
            if self._decimal(risk.metadata.get("growth_pct_exact")) != exact:
                return "risk_metadata_result_mismatch"
            rounded = result.metadata.get("rounded_percentage")
            if self._decimal(risk.metadata.get("growth_pct_rounded")) != self._decimal(rounded):
                return "risk_metadata_rounded_result_mismatch"
            for metadata_field, input_field in (
                ("period_months", "period_months"),
                ("previous_period_end", "previous_period_end"),
                ("current_period_end", "current_period_end"),
                ("currency", "currency"),
                ("source_unit", "source_unit"),
            ):
                if risk.metadata.get(metadata_field) != calculation.inputs.get(input_field):
                    return "risk_metadata_period_or_unit_mismatch"
        else:
            if not isinstance(result.value, Mapping):
                return "skill_result_invalid"
            largest = self._decimal(result.value.get("largest_counterparty_pct"))
            top_five = self._decimal(result.value.get("top_five_pct"))
            expected_result = f"largest={self._text(largest)};top_five={self._text(top_five)}"
            if calculation.result != expected_result:
                return "calculation_result_mismatch"
            expected_type = risk.risk_code.removesuffix("_concentration")
            level = self.policy.concentration_level(expected_type, largest, top_five)
            if risk.metadata.get("concentration_type") != expected_type:
                return "risk_metadata_concentration_type_mismatch"
            for field, value in (
                ("largest_counterparty_pct", largest),
                ("top_five_pct", top_five),
            ):
                if self._decimal(risk.metadata.get(field)) != value:
                    return "risk_metadata_result_mismatch"
            if risk.metadata.get("period_end") != calculation.inputs.get("period_end"):
                return "risk_metadata_period_mismatch"
            if risk.metadata.get("period_months") != calculation.inputs.get("period_months"):
                return "risk_metadata_period_mismatch"
        if level is None:
            return "risk_below_frozen_threshold"
        if risk.level != level:
            return "risk_level_mismatch"
        if self._decimal(risk.score) != _SCORES.get(level):
            return "risk_score_mismatch"
        return None

    @classmethod
    def _evidence_supports_inputs(cls, risk: RiskItem, calculation: Calculation) -> bool:
        texts = [item.text for item in risk.evidence if item.evidence_id in calculation.evidence_ids]
        if risk.risk_code == "continuous_loss":
            values = [
                cls._decimal(item.get("net_result"))
                for item in calculation.inputs.get("observations", [])
                if isinstance(item, Mapping)
            ]
        elif risk.risk_code == "revenue_growth":
            values = [
                cls._decimal(calculation.inputs.get("previous_revenue")),
                cls._decimal(calculation.inputs.get("current_revenue")),
            ]
        else:
            values = [
                cls._decimal(calculation.inputs.get("largest_counterparty_pct")),
                cls._decimal(calculation.inputs.get("top_five_pct")),
            ]
        return all(
            value is not None and any(cls._text_supports_decimal(text, value) for text in texts)
            for value in values
            if value is not None
        ) and any(value is not None for value in values)

    @classmethod
    def _conclusion_supported(cls, risk: RiskItem, result: SkillResult) -> bool:
        lowered = risk.conclusion.lower()
        if any(claim in lowered for claim in _BANNED_CLAIMS):
            return False
        if risk.risk_code == "continuous_loss":
            return str(result.value) in risk.conclusion
        if risk.risk_code == "revenue_growth":
            rounded = result.metadata.get("rounded_percentage")
            return rounded is not None and str(rounded) in risk.conclusion
        if not isinstance(result.value, Mapping):
            return False
        values = [
            cls._decimal(result.value.get("largest_counterparty_pct")),
            cls._decimal(result.value.get("top_five_pct")),
        ]
        return all(value is None or cls._text(value) in risk.conclusion for value in values)

    @staticmethod
    def _has_ambiguous_upstream_marker(metadata: Mapping[str, Any]) -> bool:
        flattened = " ".join(str(value).lower() for value in metadata.values())
        return "conflict" in flattened or "unsupported_layout" in flattened

    @classmethod
    def _text_supports_decimal(cls, text: str, expected: Decimal) -> bool:
        normalized = text.replace(",", "").replace("，", "")
        # PDF text extraction can insert layout whitespace around a decimal
        # separator (for example ``32 .7%``).  Normalize only separators that
        # are bounded by digits so prose and unrelated tokens remain intact.
        normalized = re.sub(r"(?<=\d)\s*\.\s*(?=\d)", ".", normalized)
        number = re.escape(format(abs(expected), "f"))
        boundary = rf"(?<![\d.]){number}(?![\d.])"
        if expected < 0:
            pattern = rf"(?:\(\s*|（\s*|[-−–—]\s*){boundary}(?:\s*[)）])?"
            return re.search(pattern, normalized) is not None
        return re.search(boundary, normalized) is not None

    @staticmethod
    def _decimal(value: object) -> Decimal | None:
        if value is None or isinstance(value, bool):
            return None
        try:
            parsed = value if isinstance(value, Decimal) else Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
        return parsed if parsed.is_finite() else None

    @staticmethod
    def _date(value: object) -> date | None:
        if isinstance(value, date):
            return value
        if not isinstance(value, str):
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _text(value: Decimal | None) -> str:
        return str(value) if value is not None else "None"

    @staticmethod
    def _pending(
        risk: RiskItem, status: VerificationStatus, note: str
    ) -> _ReviewDecision:
        return _ReviewDecision(
            "pending",
            risk.model_copy(
                update={"verification_status": status, "verification_notes": note}
            ),
        )

    @staticmethod
    def _reject(risk: RiskItem, issue: str) -> _ReviewDecision:
        return _ReviewDecision(
            "rejected",
            risk.model_copy(
                update={
                    "verification_status": VerificationStatus.REJECTED,
                    "verification_notes": f"Financial verification rejected: {issue}",
                }
            ),
        )
