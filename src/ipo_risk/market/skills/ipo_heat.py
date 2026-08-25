"""Deterministic, PIT-input-only recent IPO heat classification."""

from __future__ import annotations

from ipo_risk.schemas.final_supervision import MarketObservation

from .models import IPOHeat, IPOHeatResult, SampleStrength, SkillDriver


IPO_HEAT_POLICY_VERSION = "v04_ipo_heat_skill_v1"
IPO_HEAT_SOURCE_FEATURES = (
    "recent_ipo_break_rate",
    "recent_ipo_return_5d",
    "recent_ipo_1d_sample_count",
    "recent_ipo_5d_sample_count",
)


class IPOHeatSkill:
    """Simple competition policy, not fitted against any outcome cohort."""

    name = "IPOHeatSkill"
    policy_version = IPO_HEAT_POLICY_VERSION

    def evaluate(self, observations: tuple[MarketObservation, ...]) -> IPOHeatResult:
        facts = {item.name: item for item in observations}
        selected = {name: facts.get(name) for name in IPO_HEAT_SOURCE_FEATURES}
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
        one_count = int(values.get("recent_ipo_1d_sample_count", 0))
        five_count = int(values.get("recent_ipo_5d_sample_count", 0))
        break_rate = values.get("recent_ipo_break_rate")
        recent_return = values.get("recent_ipo_return_5d")

        if one_count == 0 and five_count == 0:
            strength = SampleStrength.NONE
        elif min(one_count, five_count) >= 5:
            strength = SampleStrength.STRONG
        else:
            strength = SampleStrength.LIMITED

        break_condition = (
            "UNAVAILABLE" if break_rate is None else
            "HIGH_PRESSURE" if break_rate >= 0.60 else
            "LOW_PRESSURE" if break_rate <= 0.35 else "BALANCED"
        )
        return_condition = (
            "UNAVAILABLE" if recent_return is None else
            "POSITIVE" if recent_return >= 0.0 else
            "WEAK" if recent_return <= -0.05 else "SOFT"
        )

        drivers: list[SkillDriver] = []
        if break_rate is not None:
            drivers.append(SkillDriver(
                driver_id="recent_break_pressure",
                message=f"Recent IPO break pressure is {break_condition.lower()}.",
                source_feature_ids=("recent_ipo_break_rate", "recent_ipo_1d_sample_count"),
            ))
        if recent_return is not None:
            drivers.append(SkillDriver(
                driver_id="recent_return_condition",
                message=f"Recent IPO five-session return condition is {return_condition.lower()}.",
                source_feature_ids=("recent_ipo_return_5d", "recent_ipo_5d_sample_count"),
            ))

        usable_break = break_rate is not None and one_count > 0
        usable_return = recent_return is not None and five_count > 0
        if not usable_break and not usable_return:
            heat = IPOHeat.INSUFFICIENT_DATA
        elif break_condition == "HIGH_PRESSURE" or return_condition == "WEAK":
            heat = IPOHeat.COLD
        elif usable_break and usable_return and break_condition == "LOW_PRESSURE" and return_condition == "POSITIVE":
            heat = IPOHeat.HOT
        else:
            heat = IPOHeat.NEUTRAL

        return IPOHeatResult(
            policy_version=self.policy_version,
            ipo_heat=heat,
            sample_strength=strength,
            recent_break_pressure=break_condition,
            recent_return_condition=return_condition,
            drivers=tuple(drivers),
            missingness=missingness,
            source_feature_ids=IPO_HEAT_SOURCE_FEATURES,
        )
