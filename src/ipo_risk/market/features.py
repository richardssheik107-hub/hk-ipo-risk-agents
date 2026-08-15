"""Pure point-in-time market feature engine and frozen V04-3 manifest."""

from __future__ import annotations

import math
from collections.abc import Iterable
from datetime import timedelta
from decimal import Decimal
from statistics import pstdev

from ipo_risk.schemas.market import (
    MarketDataProvenance,
    MarketLabelAvailability,
    MarketLabelHorizon,
    MarketOutcomeLabel,
    MarketSecurityEligibility,
    MarketSecurityType,
)
from ipo_risk.schemas.market_features import (
    MARKET_RAW_FEATURE_ORDER,
    MarketActivityObservation,
    MarketFeatureAvailability,
    MarketFeatureDefinition,
    MarketFeatureDType,
    MarketFeatureManifest,
    MarketFeatureMissingReason,
    MarketFeatureProvenance,
    MarketFeatureValue,
    MarketFeatureVector,
    MarketReferenceBar,
    PreListingMarketFeatureContext,
    PreListingMarketFeaturePolicy,
    PreListingMarketFeatureSnapshot,
    PriorIPOReference,
)


class PreListingMarketFeatureError(ValueError):
    """Raised when historical market inputs are ambiguous or inconsistent."""


def _build_manifest() -> MarketFeatureManifest:
    definitions: list[MarketFeatureDefinition] = []
    integer_features = {
        "recent_ipo_1d_sample_count",
        "recent_ipo_5d_sample_count",
    }
    for raw_name in MARKET_RAW_FEATURE_ORDER:
        definitions.append(
            MarketFeatureDefinition(
                index=len(definitions),
                name=raw_name,
                dtype=(
                    MarketFeatureDType.INT32
                    if raw_name in integer_features
                    else MarketFeatureDType.FLOAT64
                ),
                source=f"market_snapshot.{raw_name}",
                missing_semantics="null when unavailable; never imputed as market-neutral zero",
            )
        )
        definitions.append(
            MarketFeatureDefinition(
                index=len(definitions),
                name=f"{raw_name}__missing",
                dtype=MarketFeatureDType.INT8,
                source=f"market_snapshot.{raw_name}.availability",
                missing_semantics="one exactly when the raw feature is unavailable",
            )
        )
    return MarketFeatureManifest(features=tuple(definitions))


MARKET_FEATURE_MANIFEST_V1 = _build_manifest()


def vectorize_market_snapshot(
    snapshot: PreListingMarketFeatureSnapshot,
    manifest: MarketFeatureManifest = MARKET_FEATURE_MANIFEST_V1,
) -> MarketFeatureVector:
    """Vectorize by the explicit manifest, preserving null plus missing indicator."""

    if snapshot.market_feature_schema_version != manifest.version:
        raise ValueError("market snapshot and manifest versions differ")
    by_name = {item.name: item for item in snapshot.features}
    values: dict[str, int | float | None] = {}
    for raw_name in MARKET_RAW_FEATURE_ORDER:
        item = by_name[raw_name]
        if item.availability is MarketFeatureAvailability.AVAILABLE:
            values[raw_name] = (
                item.value if isinstance(item.value, int) else float(item.value)
            )
            values[f"{raw_name}__missing"] = 0
        else:
            values[raw_name] = None
            values[f"{raw_name}__missing"] = 1
    names = tuple(item.name for item in manifest.features)
    return MarketFeatureVector(
        manifest_hash=manifest.content_hash(),
        feature_names=names,
        feature_values=tuple(values[name] for name in names),
    )


class PreListingMarketFeatureEngine:
    """Build deterministic features using only observations before listing."""

    def __init__(self, policy: PreListingMarketFeaturePolicy | None = None) -> None:
        self.policy = policy or PreListingMarketFeaturePolicy()

    def build(
        self,
        context: PreListingMarketFeatureContext,
        *,
        benchmark_bars: Iterable[MarketReferenceBar],
        industry_bars: Iterable[MarketReferenceBar] | None = None,
        activity_observations: Iterable[MarketActivityObservation] | None = None,
        prior_ipos: Iterable[PriorIPOReference] | None = None,
        prior_outcomes: Iterable[MarketOutcomeLabel] = (),
    ) -> PreListingMarketFeatureSnapshot:
        benchmark = self._historical_bars(
            benchmark_bars,
            reference_id=context.benchmark_reference_id,
            cutoff=context.listing_date,
        )
        observation_date = benchmark[-1].trading_date if benchmark else None

        features: dict[str, MarketFeatureValue] = {}
        features["hsi_return_5d"] = self._trailing_return(
            "hsi_return_5d", benchmark, 5, MarketFeatureMissingReason.MISSING_BENCHMARK
        )
        features["hsi_return_20d"] = self._trailing_return(
            "hsi_return_20d", benchmark, 20, MarketFeatureMissingReason.MISSING_BENCHMARK
        )
        features["market_volatility_20d"] = self._volatility(benchmark)

        if observation_date is None:
            for name in ("industry_return_5d", "industry_return_20d"):
                features[name] = self._missing(
                    name, MarketFeatureMissingReason.MISSING_BENCHMARK
                )
        elif context.industry_reference_id is None:
            for name in ("industry_return_5d", "industry_return_20d"):
                features[name] = self._missing(
                    name, MarketFeatureMissingReason.MISSING_INDUSTRY_MAPPING
                )
        else:
            industry = self._historical_bars(
                industry_bars or (),
                reference_id=context.industry_reference_id,
                cutoff=context.listing_date,
                through=observation_date,
            )
            features["industry_return_5d"] = self._trailing_return(
                "industry_return_5d",
                industry,
                5,
                MarketFeatureMissingReason.MISSING_INDUSTRY_SERIES,
            )
            features["industry_return_20d"] = self._trailing_return(
                "industry_return_20d",
                industry,
                20,
                MarketFeatureMissingReason.MISSING_INDUSTRY_SERIES,
            )

        features["market_turnover_20d_mean"] = self._turnover(
            activity_observations, context.listing_date, observation_date
        )
        recent = self._recent_ipo_features(
            context,
            observation_date=observation_date,
            prior_ipos=prior_ipos,
            prior_outcomes=prior_outcomes,
        )
        features.update(recent)

        return PreListingMarketFeatureSnapshot(
            case_id=context.case_id,
            stock_code=context.stock_code,
            cohort_year=context.cohort_year,
            listing_date=context.listing_date,
            dataset_split=context.dataset_split,
            observation_date=observation_date,
            industry_reference_id=context.industry_reference_id,
            benchmark_reference_id=context.benchmark_reference_id,
            source=context.source,
            provenance=context.provenance,
            features=tuple(features[name] for name in MARKET_RAW_FEATURE_ORDER),
        )

    @staticmethod
    def _historical_bars(
        bars: Iterable[MarketReferenceBar],
        *,
        reference_id: str,
        cutoff,
        through=None,
    ) -> list[MarketReferenceBar]:
        # Exclusive cutoff is intentional: listing-day and future rows are ignored
        # before validation so they cannot affect a legal historical snapshot.
        historical = [
            bar
            for bar in bars
            if bar.trading_date < cutoff
            and (through is None or bar.trading_date <= through)
        ]
        if any(bar.reference_id != reference_id for bar in historical):
            raise PreListingMarketFeatureError(
                f"reference series contains a row for an unexpected reference id: {reference_id}"
            )
        historical.sort(key=lambda bar: bar.trading_date)
        dates = [bar.trading_date for bar in historical]
        if len(dates) != len(set(dates)):
            raise PreListingMarketFeatureError(
                f"duplicate historical reference bar for {reference_id}"
            )
        return historical

    def _trailing_return(
        self,
        name: str,
        bars: list[MarketReferenceBar],
        sessions: int,
        empty_reason: MarketFeatureMissingReason,
    ) -> MarketFeatureValue:
        if not bars:
            return self._missing(name, empty_reason)
        if len(bars) < sessions + 1:
            return self._missing(name, MarketFeatureMissingReason.INSUFFICIENT_HISTORY)
        selected = bars[-(sessions + 1) :]
        value = selected[-1].close / selected[0].close - Decimal("1")
        return self._available(
            name,
            value,
            selected,
            f"close(t)/close(t-{sessions})-1 over observed trading sessions",
        )

    def _volatility(
        self, bars: list[MarketReferenceBar]
    ) -> MarketFeatureValue:
        name = "market_volatility_20d"
        if not bars:
            return self._missing(name, MarketFeatureMissingReason.MISSING_BENCHMARK)
        if len(bars) < 21:
            return self._missing(name, MarketFeatureMissingReason.INSUFFICIENT_HISTORY)
        selected = bars[-21:]
        returns = [
            math.log(float(selected[index].close / selected[index - 1].close))
            for index in range(1, len(selected))
        ]
        value = Decimal(str(pstdev(returns)))
        return self._available(
            name,
            value,
            selected,
            "population standard deviation of 20 one-session log returns; ddof=0; not annualized",
        )

    def _turnover(
        self,
        observations: Iterable[MarketActivityObservation] | None,
        listing_date,
        observation_date,
    ) -> MarketFeatureValue:
        name = "market_turnover_20d_mean"
        if observations is None:
            return self._missing(name, MarketFeatureMissingReason.MISSING_TURNOVER_SOURCE)
        if observation_date is None:
            return self._missing(name, MarketFeatureMissingReason.MISSING_BENCHMARK)
        historical = [
            item
            for item in observations
            if item.trading_date < listing_date and item.trading_date <= observation_date
        ]
        historical.sort(key=lambda item: item.trading_date)
        dates = [item.trading_date for item in historical]
        if len(dates) != len(set(dates)):
            raise PreListingMarketFeatureError("duplicate historical market activity date")
        if len(historical) < self.policy.turnover_sessions:
            return self._missing(name, MarketFeatureMissingReason.INSUFFICIENT_HISTORY)
        selected = historical[-self.policy.turnover_sessions :]
        value = sum((item.turnover for item in selected), Decimal("0")) / Decimal(
            len(selected)
        )
        provenance = MarketFeatureProvenance(
            source=selected[-1].provenance.source,
            dataset_version=selected[-1].provenance.dataset_version,
            source_record_ids=tuple(
                item.provenance.source_record_id or item.trading_date.isoformat()
                for item in selected
            ),
            derivation="mean of actual total-market turnover over 20 observed sessions",
        )
        return MarketFeatureValue(
            name=name,
            value=value,
            availability=MarketFeatureAvailability.AVAILABLE,
            provenance=provenance,
        )

    def _recent_ipo_features(
        self,
        context: PreListingMarketFeatureContext,
        *,
        observation_date,
        prior_ipos: Iterable[PriorIPOReference] | None,
        prior_outcomes: Iterable[MarketOutcomeLabel],
    ) -> dict[str, MarketFeatureValue]:
        names = (
            "recent_ipo_break_rate",
            "recent_ipo_return_5d",
            "recent_ipo_1d_sample_count",
            "recent_ipo_5d_sample_count",
        )
        if prior_ipos is None:
            return {
                name: self._missing(name, MarketFeatureMissingReason.SOURCE_UNAVAILABLE)
                for name in names
            }
        if observation_date is None:
            return {
                name: self._missing(name, MarketFeatureMissingReason.MISSING_BENCHMARK)
                for name in names
            }

        window_start = context.listing_date - timedelta(
            days=self.policy.recent_ipo_calendar_days
        )
        eligible = [
            item
            for item in prior_ipos
            if window_start <= item.listing_date < context.listing_date
            and item.listing_date <= observation_date
            and item.case_id != context.case_id
            and item.stock_code != context.stock_code
            and item.security_type is MarketSecurityType.ORDINARY_EQUITY
            and item.modeling_eligibility is MarketSecurityEligibility.ELIGIBLE
        ]
        keys = [(item.case_id, item.stock_code) for item in eligible]
        if len(keys) != len(set(keys)):
            raise PreListingMarketFeatureError("duplicate prior IPO identity in recent universe")
        eligible.sort(
            key=lambda item: (item.listing_date, item.case_id, item.stock_code),
            reverse=True,
        )
        eligible = eligible[: self.policy.recent_ipo_max_count]
        by_case = {item.case_id: item for item in eligible}

        known_labels: dict[tuple[str, MarketLabelHorizon], MarketOutcomeLabel] = {}
        for label in prior_outcomes:
            prior = by_case.get(label.case_id)
            if prior is None or label.horizon not in {
                MarketLabelHorizon.ONE_DAY,
                MarketLabelHorizon.FIVE_DAYS,
            }:
                continue
            if (
                label.availability is not MarketLabelAvailability.AVAILABLE
                or label.target_trading_date is None
                or label.target_trading_date > observation_date
            ):
                continue
            if (
                label.stock_code != prior.stock_code
                or label.listing_date != prior.listing_date
                or label.cohort_year != prior.cohort_year
                or label.dataset_split is not prior.dataset_split
            ):
                raise PreListingMarketFeatureError(
                    f"prior IPO label identity mismatch for {label.case_id}"
                )
            key = (label.case_id, label.horizon)
            if key in known_labels:
                raise PreListingMarketFeatureError(
                    f"duplicate known prior IPO label for {label.case_id}/{label.horizon.value}"
                )
            known_labels[key] = label

        one_day = [
            known_labels[(item.case_id, MarketLabelHorizon.ONE_DAY)]
            for item in eligible
            if (item.case_id, MarketLabelHorizon.ONE_DAY) in known_labels
        ]
        five_day = [
            known_labels[(item.case_id, MarketLabelHorizon.FIVE_DAYS)]
            for item in eligible
            if (item.case_id, MarketLabelHorizon.FIVE_DAYS) in known_labels
        ]
        count_provenance = MarketFeatureProvenance(
            source="prior_ipo_outcome_labels",
            dataset_version=self.policy.version,
            source_record_ids=tuple(item.case_id for item in eligible),
            derivation="eligible ordinary-equity prior IPO universe before target listing",
        )
        result = {
            "recent_ipo_1d_sample_count": MarketFeatureValue(
                name="recent_ipo_1d_sample_count",
                value=len(one_day),
                availability=MarketFeatureAvailability.AVAILABLE,
                provenance=count_provenance,
            ),
            "recent_ipo_5d_sample_count": MarketFeatureValue(
                name="recent_ipo_5d_sample_count",
                value=len(five_day),
                availability=MarketFeatureAvailability.AVAILABLE,
                provenance=count_provenance,
            ),
        }
        if one_day:
            broken = sum(label.raw_return < 0 for label in one_day if label.raw_return is not None)
            result["recent_ipo_break_rate"] = self._available_from_labels(
                "recent_ipo_break_rate",
                Decimal(broken) / Decimal(len(one_day)),
                one_day,
                "count(raw_return_1d < 0) / completed known 1D sample count",
            )
        else:
            result["recent_ipo_break_rate"] = self._missing(
                "recent_ipo_break_rate", MarketFeatureMissingReason.NO_RECENT_IPO_SAMPLE
            )
        if five_day:
            total = sum(
                (label.raw_return for label in five_day if label.raw_return is not None),
                Decimal("0"),
            )
            result["recent_ipo_return_5d"] = self._available_from_labels(
                "recent_ipo_return_5d",
                total / Decimal(len(five_day)),
                five_day,
                "mean completed known prior IPO 5D raw return",
            )
        else:
            result["recent_ipo_return_5d"] = self._missing(
                "recent_ipo_return_5d", MarketFeatureMissingReason.NO_RECENT_IPO_SAMPLE
            )
        return result

    @staticmethod
    def _missing(
        name: str, reason: MarketFeatureMissingReason
    ) -> MarketFeatureValue:
        return MarketFeatureValue(
            name=name,
            availability=MarketFeatureAvailability.UNAVAILABLE,
            missing_reason=reason,
        )

    @staticmethod
    def _available(
        name: str,
        value: Decimal,
        bars: list[MarketReferenceBar],
        derivation: str,
    ) -> MarketFeatureValue:
        last = bars[-1]
        return MarketFeatureValue(
            name=name,
            value=value,
            availability=MarketFeatureAvailability.AVAILABLE,
            provenance=MarketFeatureProvenance(
                source=last.provenance.source,
                dataset_version=last.provenance.dataset_version,
                source_record_ids=tuple(
                    item.provenance.source_record_id or item.trading_date.isoformat()
                    for item in bars
                ),
                derivation=derivation,
            ),
        )

    @staticmethod
    def _available_from_labels(
        name: str,
        value: Decimal,
        labels: list[MarketOutcomeLabel],
        derivation: str,
    ) -> MarketFeatureValue:
        return MarketFeatureValue(
            name=name,
            value=value,
            availability=MarketFeatureAvailability.AVAILABLE,
            provenance=MarketFeatureProvenance(
                source="prior_ipo_outcome_labels",
                dataset_version=labels[0].label_policy_version,
                source_record_ids=tuple(
                    f"{label.case_id}:{label.horizon.value}:{label.target_trading_date}"
                    for label in labels
                ),
                derivation=derivation,
            ),
        )
