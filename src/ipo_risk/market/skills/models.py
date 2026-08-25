"""Private, deterministic result models for competition Market skills."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SkillModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class IPOHeat(StrEnum):
    HOT = "HOT"
    NEUTRAL = "NEUTRAL"
    COLD = "COLD"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class SampleStrength(StrEnum):
    STRONG = "STRONG"
    LIMITED = "LIMITED"
    NONE = "NONE"


class MarketRegime(StrEnum):
    RISK_ON = "RISK_ON"
    NEUTRAL = "NEUTRAL"
    RISK_OFF = "RISK_OFF"
    MIXED = "MIXED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class TrendCondition(StrEnum):
    POSITIVE = "POSITIVE"
    FLAT = "FLAT"
    NEGATIVE = "NEGATIVE"
    MIXED = "MIXED"
    UNAVAILABLE = "UNAVAILABLE"


class VolatilityCondition(StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    UNAVAILABLE = "UNAVAILABLE"


class LiquidityCondition(StrEnum):
    OBSERVED_UNBENCHMARKED = "OBSERVED_UNBENCHMARKED"
    UNAVAILABLE = "UNAVAILABLE"


class SkillDriver(SkillModel):
    driver_id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    source_feature_ids: tuple[str, ...] = Field(min_length=1)


class IPOHeatResult(SkillModel):
    policy_version: str = Field(min_length=1)
    ipo_heat: IPOHeat
    sample_strength: SampleStrength
    recent_break_pressure: str
    recent_return_condition: str
    drivers: tuple[SkillDriver, ...] = ()
    missingness: dict[str, str] = Field(default_factory=dict)
    source_feature_ids: tuple[str, ...]


class MarketRegimeResult(SkillModel):
    policy_version: str = Field(min_length=1)
    market_regime: MarketRegime
    trend_condition: TrendCondition
    volatility_condition: VolatilityCondition
    liquidity_condition: LiquidityCondition
    drivers: tuple[SkillDriver, ...] = ()
    uncertainties: tuple[str, ...] = ()
    missingness: dict[str, str] = Field(default_factory=dict)
    source_feature_ids: tuple[str, ...]
