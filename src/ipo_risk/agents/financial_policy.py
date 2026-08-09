"""Typed v0.3 financial risk policy loaded from the frozen YAML contract."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping

import yaml

from ipo_risk.schemas import RiskLevel


RULE_VERSION = "v03_contract_v1"


@dataclass(frozen=True, slots=True)
class ConcentrationThresholds:
    high_largest_gte: Decimal
    high_top_five_gte: Decimal
    medium_largest_gte: Decimal
    medium_top_five_gte: Decimal


@dataclass(frozen=True, slots=True)
class V03FinancialPolicy:
    """Frozen financial thresholds and deterministic level decisions."""

    version: str
    cash_runway_critical_lt: Decimal
    cash_runway_high_lt: Decimal
    cash_runway_medium_lt: Decimal
    continuous_loss_high_min: int
    continuous_loss_medium_min: int
    revenue_high_lte: Decimal
    revenue_medium_lt: Decimal
    customer: ConcentrationThresholds
    supplier: ConcentrationThresholds

    def cash_runway_level(self, runway_months: Decimal) -> RiskLevel:
        if runway_months < self.cash_runway_critical_lt:
            return RiskLevel.CRITICAL
        if runway_months < self.cash_runway_high_lt:
            return RiskLevel.HIGH
        if runway_months < self.cash_runway_medium_lt:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def loss_level(self, latest_loss_periods: int) -> RiskLevel | None:
        if latest_loss_periods >= self.continuous_loss_high_min:
            return RiskLevel.HIGH
        if latest_loss_periods >= self.continuous_loss_medium_min:
            return RiskLevel.MEDIUM
        return None

    def revenue_level(self, growth_pct: Decimal) -> RiskLevel | None:
        if growth_pct <= self.revenue_high_lte:
            return RiskLevel.HIGH
        if growth_pct < self.revenue_medium_lt:
            return RiskLevel.MEDIUM
        return None

    def concentration_level(
        self,
        concentration_type: str,
        largest_pct: Decimal | None,
        top_five_pct: Decimal | None,
    ) -> RiskLevel | None:
        thresholds = self.customer if concentration_type == "customer" else self.supplier
        if (
            largest_pct is not None
            and largest_pct >= thresholds.high_largest_gte
        ) or (
            top_five_pct is not None
            and top_five_pct >= thresholds.high_top_five_gte
        ):
            return RiskLevel.HIGH
        if (
            largest_pct is not None
            and largest_pct >= thresholds.medium_largest_gte
        ) or (
            top_five_pct is not None
            and top_five_pct >= thresholds.medium_top_five_gte
        ):
            return RiskLevel.MEDIUM
        return None


def load_v03_financial_policy(path: Path | None = None) -> V03FinancialPolicy:
    """Load and strictly validate the frozen financial rule configuration."""

    config_path = path or Path(__file__).resolve().parents[3] / "configs" / "v03_risk_rules.yaml"
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("v03_risk_rules_invalid")
    if payload.get("version") != RULE_VERSION or payload.get("status") != "frozen":
        raise ValueError("v03_risk_rules_version_or_status_invalid")
    risks = payload.get("risks")
    if not isinstance(risks, Mapping):
        raise ValueError("v03_risk_rules_missing_risks")

    cash = _mapping(risks, "cash_runway", "thresholds_months")
    loss = _mapping(risks, "continuous_loss", "thresholds")
    revenue = _mapping(risks, "revenue_growth", "thresholds_pct")
    customer = _concentration_thresholds(risks, "customer_concentration")
    supplier = _concentration_thresholds(risks, "supplier_concentration")
    for risk_code in (
        "cash_runway",
        "continuous_loss",
        "revenue_growth",
        "customer_concentration",
        "supplier_concentration",
    ):
        settings = risks.get(risk_code)
        if not isinstance(settings, Mapping) or settings.get("owner") != "financial":
            raise ValueError(f"v03_risk_owner_invalid:{risk_code}")

    return V03FinancialPolicy(
        version=RULE_VERSION,
        cash_runway_critical_lt=_decimal(cash, "critical_lt"),
        cash_runway_high_lt=_decimal(cash, "high_lt"),
        cash_runway_medium_lt=_decimal(cash, "medium_lt"),
        continuous_loss_high_min=_integer(loss, "high_min_comparable_periods"),
        continuous_loss_medium_min=_integer(loss, "medium_min_comparable_periods"),
        revenue_high_lte=_decimal(revenue, "high_lte"),
        revenue_medium_lt=_decimal(revenue, "medium_lt"),
        customer=customer,
        supplier=supplier,
    )


def _mapping(root: Mapping[str, Any], risk_code: str, field: str) -> Mapping[str, Any]:
    settings = root.get(risk_code)
    if not isinstance(settings, Mapping) or not isinstance(settings.get(field), Mapping):
        raise ValueError(f"v03_risk_rules_missing:{risk_code}.{field}")
    return settings[field]


def _integer(settings: Mapping[str, Any], field: str) -> int:
    value = settings.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"v03_risk_rule_integer_invalid:{field}")
    return value


def _decimal(settings: Mapping[str, Any], field: str) -> Decimal:
    value = settings.get(field)
    if value is None or isinstance(value, bool):
        raise ValueError(f"v03_risk_rule_decimal_invalid:{field}")
    try:
        converted = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"v03_risk_rule_decimal_invalid:{field}") from exc
    if not converted.is_finite():
        raise ValueError(f"v03_risk_rule_decimal_invalid:{field}")
    return converted


def _concentration_thresholds(
    risks: Mapping[str, Any], risk_code: str
) -> ConcentrationThresholds:
    settings = _mapping(risks, risk_code, "thresholds_pct")
    return ConcentrationThresholds(
        high_largest_gte=_decimal(settings, "high_largest_gte"),
        high_top_five_gte=_decimal(settings, "high_top_five_gte"),
        medium_largest_gte=_decimal(settings, "medium_largest_gte"),
        medium_top_five_gte=_decimal(settings, "medium_top_five_gte"),
    )
