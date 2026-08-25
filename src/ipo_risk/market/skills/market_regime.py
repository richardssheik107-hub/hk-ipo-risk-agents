"""Deterministic Hong Kong market-regime interpretation policy."""

from __future__ import annotations

from ipo_risk.schemas.final_supervision import MarketObservation

from .models import (
    LiquidityCondition,
    MarketRegime,
    MarketRegimeResult,
    SkillDriver,
    TrendCondition,
    VolatilityCondition,
)


MARKET_REGIME_POLICY_VERSION = "v04_market_regime_skill_v1"
MARKET_REGIME_SOURCE_FEATURES = (
    "hsi_return_5d",
    "hsi_return_20d",
    "market_volatility_20d",
    "market_turnover_20d_mean",
)


class MarketRegimeSkill:
    """Fixed competition heuristic; thresholds were not outcome-tuned."""

    name = "MarketRegimeSkill"
    policy_version = MARKET_REGIME_POLICY_VERSION

    def evaluate(self, observations: tuple[MarketObservation, ...]) -> MarketRegimeResult:
        facts = {item.name: item for item in observations}
        selected = {name: facts.get(name) for name in MARKET_REGIME_SOURCE_FEATURES}
        missingness = {
            name: (item.missing_reason or "source_unavailable")
            for name, item in selected.items()
            if item is None or item.availability == "unavailable"
        }
        values = {
            name: float(item.value)
            for name, item in selected.items()
            if item is not None and item.availability == "available" and item.value is not None
        }
        short = values.get("hsi_return_5d")
        medium = values.get("hsi_return_20d")
        volatility = values.get("market_volatility_20d")
        turnover = values.get("market_turnover_20d_mean")

        if short is None or medium is None:
            trend = TrendCondition.UNAVAILABLE
        elif short > 0.01 and medium > 0.02:
            trend = TrendCondition.POSITIVE
        elif short < -0.01 and medium < -0.02:
            trend = TrendCondition.NEGATIVE
        elif short * medium < 0 and (abs(short) > 0.01 or abs(medium) > 0.02):
            trend = TrendCondition.MIXED
        else:
            trend = TrendCondition.FLAT

        volatility_condition = (
            VolatilityCondition.UNAVAILABLE if volatility is None else
            VolatilityCondition.HIGH if volatility >= 0.02 else
            VolatilityCondition.LOW if volatility <= 0.01 else
            VolatilityCondition.NORMAL
        )
        liquidity = (
            LiquidityCondition.OBSERVED_UNBENCHMARKED
            if turnover is not None else LiquidityCondition.UNAVAILABLE
        )

        if trend is TrendCondition.UNAVAILABLE:
            regime = MarketRegime.INSUFFICIENT_DATA
        elif trend is TrendCondition.POSITIVE and volatility_condition is not VolatilityCondition.HIGH:
            regime = MarketRegime.RISK_ON
        elif trend is TrendCondition.NEGATIVE:
            regime = MarketRegime.RISK_OFF
        elif trend is TrendCondition.MIXED or volatility_condition is VolatilityCondition.HIGH:
            regime = MarketRegime.MIXED
        else:
            regime = MarketRegime.NEUTRAL

        drivers: list[SkillDriver] = []
        if trend is not TrendCondition.UNAVAILABLE:
            drivers.append(SkillDriver(
                driver_id="hsi_trend",
                message=f"HSI pre-listing trend is {trend.value.lower()}.",
                source_feature_ids=("hsi_return_5d", "hsi_return_20d"),
            ))
        if volatility_condition is not VolatilityCondition.UNAVAILABLE:
            drivers.append(SkillDriver(
                driver_id="market_volatility",
                message=f"Pre-listing market volatility is {volatility_condition.value.lower()}.",
                source_feature_ids=("market_volatility_20d",),
            ))
        if turnover is not None:
            drivers.append(SkillDriver(
                driver_id="market_turnover_observed",
                message="Market turnover is observed, but no PIT-safe relative baseline is available for a high/low claim.",
                source_feature_ids=("market_turnover_20d_mean",),
            ))

        uncertainties = [
            "Liquidity strength is not classified because an absolute turnover threshold would not be comparable across years."
        ] if turnover is not None else ["Market turnover is unavailable."]
        for industry_name in ("industry_return_5d", "industry_return_20d"):
            industry = facts.get(industry_name)
            if industry is not None and industry.availability == "unavailable":
                uncertainties.append(
                    f"{industry_name} unavailable: {industry.missing_reason}."
                )

        return MarketRegimeResult(
            policy_version=self.policy_version,
            market_regime=regime,
            trend_condition=trend,
            volatility_condition=volatility_condition,
            liquidity_condition=liquidity,
            drivers=tuple(drivers),
            uncertainties=tuple(uncertainties),
            missingness=missingness,
            source_feature_ids=MARKET_REGIME_SOURCE_FEATURES,
        )
