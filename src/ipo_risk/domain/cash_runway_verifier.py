"""Deterministic verification for an A4 cash-runway risk item."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from ipo_risk.domain.cash_runway import cash_runway_risk_policy
from ipo_risk.schemas import (
    Evidence,
    EvidenceSourceType,
    RiskCategory,
    RiskItem,
    VerificationStatus,
)
from ipo_risk.skills.financial import cash_runway_from_operating_cash_flow


_FORMULA = "cash / (abs(operating_cash_flow) / period_months)"
_NUMBER_BODY = r"\d+(?:(?:[,，]|\s)\d{3})*(?:\.\d+)?"
_TEXT_AMOUNT_RE = re.compile(
    rf"(?:\(\s*{_NUMBER_BODY}\s*\)|（\s*{_NUMBER_BODY}\s*）|[-−–—]\s*{_NUMBER_BODY}|{_NUMBER_BODY})"
)
_BANNED_CONCLUSION_CLAIMS = (
    "必然破产",
    "必然下跌",
    "股价必跌",
    "will go bankrupt",
    "will decline",
    "guaranteed decline",
)


class CashRunwayVerificationStatus(StrEnum):
    """Outcome of deterministic verification."""

    VERIFIED = "verified"
    PENDING = "pending"
    NEEDS_REVIEW = "needs_review"


class CashRunwayVerificationResult(BaseModel):
    """Typed verifier output retaining both success and review diagnostics."""

    status: CashRunwayVerificationStatus
    verified_risk: RiskItem | None = None
    reviewed_risk: RiskItem
    issues: list[str] = Field(default_factory=list)
    checks: dict[str, bool] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CashRunwayRiskVerifier:
    """Recalculate and verify a cash-runway risk without trusting its score."""

    def verify(
        self,
        risk: RiskItem,
        available_evidence: Mapping[str, Evidence],
    ) -> CashRunwayVerificationResult:
        """Verify identity, evidence, calculation, policy, and conclusion."""

        issues: list[str] = []
        checks: dict[str, bool] = {}

        def record(name: str, passed: bool, issue: str | None = None) -> None:
            checks[name] = passed
            if not passed and issue:
                issues.append(issue)

        record("risk_code", risk.risk_code == "cash_runway", "risk_code_invalid")
        record("category", risk.category == RiskCategory.FINANCIAL, "risk_category_invalid")
        record(
            "canonical_code",
            risk.metadata.get("canonical_code") == "FIN_CASH_RUNWAY",
            "canonical_code_invalid",
        )
        record("agent_name", risk.agent_name == "financial", "agent_name_invalid")
        calculation = risk.calculation
        record("calculation_present", calculation is not None, "calculation_missing")

        embedded = list(risk.evidence)
        embedded_ids = [item.evidence_id for item in embedded]
        record("evidence_count", len(embedded) >= 2, "risk_evidence_insufficient")
        record(
            "evidence_ids_nonempty",
            all(bool(item) for item in embedded_ids),
            "evidence_id_missing",
        )
        record(
            "evidence_ids_unique",
            len(embedded_ids) == len(set(embedded_ids)),
            "duplicate_evidence_id",
        )
        if calculation is not None:
            record(
                "calculation_evidence_order",
                calculation.evidence_ids == embedded_ids,
                "calculation_evidence_ids_mismatch",
            )

        resolved: list[Evidence] = []
        for index, item in enumerate(embedded):
            label = "cash" if index == 0 else "operating_cash_flow" if index == 1 else f"extra_{index}"
            available = available_evidence.get(item.evidence_id)
            if available is None:
                record(f"{label}_available", False, f"{label}_evidence_unavailable")
                continue
            record(f"{label}_available", True)
            identity_ok = all(
                getattr(item, field) == getattr(available, field)
                for field in ("evidence_id", "document_id", "chunk_id", "page", "source_type")
            )
            record(f"{label}_identity", identity_ok, f"{label}_evidence_identity_mismatch")
            text_ok = bool(item.text.strip()) and bool(available.text.strip())
            record(f"{label}_text", text_ok, f"{label}_evidence_text_empty")
            text_matches = (
                text_ok
                and self._normalize_evidence_text(item.text)
                == self._normalize_evidence_text(available.text)
            )
            record(
                f"{label}_text_identity",
                text_matches,
                f"{label}_evidence_text_mismatch",
            )
            source_ok = (
                item.source_type == EvidenceSourceType.PROSPECTUS
                and available.source_type == EvidenceSourceType.PROSPECTUS
            )
            record(f"{label}_source_type", source_ok, "evidence_source_type_invalid")
            if identity_ok and text_matches and source_ok:
                resolved.append(available)
        if len(embedded) >= 2:
            same_document = bool(embedded[0].document_id) and all(
                item.document_id == embedded[0].document_id for item in embedded[1:]
            )
            record("evidence_same_document", same_document, "evidence_document_mismatch")

        parsed: dict[str, Any] = {}
        if calculation is not None:
            record("skill_name", calculation.skill_name == "cash_runway", "skill_name_invalid")
            record("skill_version", calculation.skill_version == "1.1", "skill_version_invalid")
            record("calculation_success", calculation.success is True, "calculation_not_successful")
            record("calculation_error", calculation.error is None, "calculation_error_present")
            record("calculation_unit", calculation.unit == "months", "calculation_unit_invalid")
            record("formula", calculation.formula == _FORMULA, "calculation_formula_invalid")
            required_inputs = (
                "cash",
                "operating_cash_flow",
                "period_months",
                "monthly_burn",
                "currency",
                "source_unit",
                "cash_period_end",
                "operating_cash_flow_period_end",
            )
            missing_inputs = [name for name in required_inputs if name not in calculation.inputs]
            record("required_inputs", not missing_inputs, "calculation_inputs_missing")
            if not missing_inputs:
                parsed = self._parse_inputs(calculation.inputs)
                for name in ("cash", "operating_cash_flow", "monthly_burn"):
                    record(f"{name}_finite", parsed.get(name) is not None, f"{name}_invalid")
                record(
                    "period_months",
                    parsed.get("period_months") in {3, 6, 9, 12},
                    "period_months_invalid",
                )
                record(
                    "cash_non_negative",
                    parsed.get("cash") is not None and parsed["cash"] >= 0,
                    "cash_negative",
                )
                record(
                    "operating_cash_flow_negative",
                    parsed.get("operating_cash_flow") is not None
                    and parsed["operating_cash_flow"] < 0,
                    "operating_cash_flow_not_negative",
                )
                record("currency", bool(parsed.get("currency")), "currency_missing")
                record("source_unit", bool(parsed.get("source_unit")), "source_unit_missing")
                record(
                    "period_ends",
                    parsed.get("cash_period_end") is not None
                    and parsed.get("cash_period_end") == parsed.get("operating_cash_flow_period_end"),
                    "period_end_mismatch",
                )

        skill_result = None
        can_recalculate = (
            calculation is not None
            and parsed.get("cash") is not None
            and parsed.get("operating_cash_flow") is not None
            and parsed.get("period_months") in {3, 6, 9, 12}
            and parsed["cash"] >= 0
            and parsed["operating_cash_flow"] < 0
        )
        if can_recalculate:
            skill_result = cash_runway_from_operating_cash_flow(
                parsed["cash"],
                parsed["operating_cash_flow"],
                parsed["period_months"],
                calculation.evidence_ids,
                currency=parsed.get("currency"),
                source_unit=parsed.get("source_unit"),
            )
            record("skill_recalculation", skill_result.success, "skill_recalculation_failed")
        else:
            checks["skill_recalculation"] = False

        exact = rounded = monthly_burn = None
        if skill_result is not None and skill_result.success:
            exact = self._decimal(skill_result.value)
            rounded = self._decimal(skill_result.metadata.get("rounded_months"))
            monthly_burn = self._decimal(skill_result.metadata.get("monthly_burn"))
            result_value = self._decimal(calculation.result if calculation else None)
            record("calculation_result", result_value == rounded, "calculation_result_mismatch")
            record(
                "monthly_burn",
                parsed.get("monthly_burn") == monthly_burn,
                "monthly_burn_mismatch",
            )
            if len(resolved) >= 2:
                record(
                    "cash_evidence_value",
                    self._text_supports_amount(resolved[0].text, parsed["cash"]),
                    "cash_evidence_value_mismatch",
                )
                record(
                    "operating_cash_flow_evidence_value",
                    self._text_supports_amount(
                        resolved[1].text, parsed["operating_cash_flow"]
                    ),
                    "operating_cash_flow_evidence_value_mismatch",
                )

            metadata_checks = {
                "policy_version": risk.metadata.get("policy_version") == "cash_runway_rule_v1",
                "score_is_rule_based": risk.metadata.get("score_is_rule_based") is True,
                "score_is_probability": risk.metadata.get("score_is_probability") is False,
                "runway_months_exact": self._decimal(risk.metadata.get("runway_months_exact")) == exact,
                "runway_months_rounded": self._decimal(risk.metadata.get("runway_months_rounded")) == rounded,
                "metadata_monthly_burn": self._decimal(risk.metadata.get("monthly_burn")) == monthly_burn,
                "metadata_currency": risk.metadata.get("currency") == parsed.get("currency"),
                "metadata_source_unit": risk.metadata.get("source_unit") == parsed.get("source_unit"),
                "metadata_period_months": risk.metadata.get("period_months") == parsed.get("period_months"),
            }
            for name, passed in metadata_checks.items():
                record(name, passed, f"{name}_mismatch")

            if exact is not None:
                expected_level, expected_score = cash_runway_risk_policy(exact)
                record("risk_level", risk.level == expected_level, "risk_level_mismatch")
                record(
                    "risk_score",
                    self._decimal(risk.score) == Decimal(expected_score),
                    "risk_score_mismatch",
                )

            conclusion = risk.conclusion.lower()
            conclusion_ok = (
                rounded is not None
                and str(rounded) in conclusion
                and "deterministic" in conclusion
                and "rule" in conclusion
                and "not a probability" in conclusion
                and not any(claim in conclusion for claim in _BANNED_CONCLUSION_CLAIMS)
            )
            record("conclusion", conclusion_ok, "risk_conclusion_invalid")

        issues = list(dict.fromkeys(issues))
        pending_issue_codes = {"risk_evidence_insufficient", "evidence_id_missing"}
        if "risk_evidence_insufficient" in issues:
            pending_issue_codes.add("calculation_evidence_ids_mismatch")
        pending_only = bool(issues) and all(
            issue in pending_issue_codes or issue.endswith("_evidence_unavailable")
            for issue in issues
        )
        if not issues and all(checks.values()):
            notes = (
                "Evidence passed; Calculation was independently recalculated; risk level and "
                "deterministic rule score matched policy. The score is not a probability."
            )
            reviewed = risk.model_copy(
                update={
                    "verification_status": VerificationStatus.VERIFIED,
                    "verification_notes": notes,
                }
            )
            return CashRunwayVerificationResult(
                status=CashRunwayVerificationStatus.VERIFIED,
                verified_risk=reviewed,
                reviewed_risk=reviewed,
                checks=checks,
                metadata={"policy_version": "cash_runway_rule_v1"},
            )

        verification_status = (
            VerificationStatus.PENDING if pending_only else VerificationStatus.NEEDS_REVIEW
        )
        status = (
            CashRunwayVerificationStatus.PENDING
            if pending_only
            else CashRunwayVerificationStatus.NEEDS_REVIEW
        )
        reviewed = risk.model_copy(
            update={
                "verification_status": verification_status,
                "verification_notes": "Cash runway verification failed: " + ", ".join(issues),
            }
        )
        return CashRunwayVerificationResult(
            status=status,
            reviewed_risk=reviewed,
            issues=issues,
            checks=checks,
            metadata={"policy_version": "cash_runway_rule_v1"},
        )

    @classmethod
    def _parse_inputs(cls, inputs: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "cash": cls._decimal(inputs.get("cash")),
            "operating_cash_flow": cls._decimal(inputs.get("operating_cash_flow")),
            "period_months": cls._integer(inputs.get("period_months")),
            "monthly_burn": cls._decimal(inputs.get("monthly_burn")),
            "currency": inputs.get("currency") if isinstance(inputs.get("currency"), str) else None,
            "source_unit": inputs.get("source_unit") if isinstance(inputs.get("source_unit"), str) else None,
            "cash_period_end": cls._date(inputs.get("cash_period_end")),
            "operating_cash_flow_period_end": cls._date(
                inputs.get("operating_cash_flow_period_end")
            ),
        }

    @staticmethod
    def _decimal(value: object) -> Decimal | None:
        if value is None or isinstance(value, bool) or (isinstance(value, str) and not value.strip()):
            return None
        try:
            parsed = value if isinstance(value, Decimal) else Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
        return parsed if parsed.is_finite() else None

    @classmethod
    def _integer(cls, value: object) -> int | None:
        parsed = cls._decimal(value)
        if parsed is None or parsed != parsed.to_integral_value():
            return None
        return int(parsed)

    @staticmethod
    def _date(value: object) -> date | None:
        if isinstance(value, date):
            return value
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _normalize_evidence_text(text: str) -> str:
        """Normalize layout-only whitespace before comparing evidence content."""

        return " ".join(text.split())

    @classmethod
    def _text_supports_amount(cls, text: str, expected: Decimal) -> bool:
        for match in _TEXT_AMOUNT_RE.finditer(text):
            token = match.group(0).strip()
            negative = (
                (token.startswith("(") and token.endswith(")"))
                or (token.startswith("（") and token.endswith("）"))
                or token.startswith(("-", "−", "–", "—"))
            )
            normalized = (
                token.strip("()（） ")
                .replace(",", "")
                .replace("，", "")
                .replace(" ", "")
                .replace("−", "-")
                .replace("–", "-")
                .replace("—", "-")
            )
            try:
                value = Decimal(normalized)
            except InvalidOperation:
                continue
            value = -abs(value) if negative else value
            if value == expected:
                return True
        return False
