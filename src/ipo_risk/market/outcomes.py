"""Development-only threshold fitting and deterministic PR-C target creation."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, ROUND_CEILING
from typing import Iterable

from ipo_risk.schemas.market import (
    MarketDatasetSplit,
    MarketLabelAvailability,
    MarketLabelHorizon,
    MarketOutcomeLabel,
)
from ipo_risk.schemas.outcomes import (
    FiveDayOutcomePolicy,
    FiveDayOutcomeTarget,
    FrozenFiveDayThreshold,
)


def _canonical_hash(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _label_hash(label: MarketOutcomeLabel) -> str:
    return _canonical_hash(label.model_dump(mode="json"))


class FiveDayOutcomeBuilder:
    """Fit a threshold on Development and apply it to Development/Validation."""

    def __init__(self, policy: FiveDayOutcomePolicy | None = None) -> None:
        self.policy = policy or FiveDayOutcomePolicy()

    def freeze_threshold(
        self,
        labels: Iterable[MarketOutcomeLabel],
    ) -> FrozenFiveDayThreshold:
        usable: list[tuple[str, Decimal]] = []
        seen_cases: set[str] = set()
        for label in labels:
            self._require_five_day(label)
            if label.dataset_split is not MarketDatasetSplit.DEVELOPMENT:
                raise ValueError(
                    "threshold fitting accepts only 2020-2023 Development labels"
                )
            if label.case_id in seen_cases:
                raise ValueError(f"duplicate Development label: {label.case_id}")
            seen_cases.add(label.case_id)
            if label.availability is MarketLabelAvailability.AVAILABLE:
                assert label.raw_return is not None
                usable.append((label.case_id, label.raw_return))

        if not usable:
            raise ValueError("no available Development 5D labels for threshold fitting")

        usable.sort(key=lambda item: (item[1], item[0]))
        count = len(usable)
        rank_decimal = self.policy.threshold_quantile * Decimal(count)
        nearest_rank = int(rank_decimal.to_integral_value(rounding=ROUND_CEILING))
        nearest_rank = max(1, min(count, nearest_rank))
        threshold = usable[nearest_rank - 1][1]
        case_ids = sorted(case_id for case_id, _ in usable)
        ordered_returns = [
            {"case_id": case_id, "raw_return_5d": str(value)}
            for case_id, value in sorted(usable, key=lambda item: item[0])
        ]
        return FrozenFiveDayThreshold(
            policy_hash=self.policy.content_hash(),
            method=self.policy.threshold_method,
            quantile=self.policy.threshold_quantile,
            threshold=threshold,
            nearest_rank=nearest_rank,
            development_sample_count=count,
            development_case_ids_hash=_canonical_hash(case_ids),
            development_returns_hash=_canonical_hash(ordered_returns),
        )

    def build_target(
        self,
        label: MarketOutcomeLabel,
        threshold: FrozenFiveDayThreshold,
    ) -> FiveDayOutcomeTarget:
        self._require_five_day(label)
        if label.dataset_split is MarketDatasetSplit.BLIND or label.cohort_year == 2025:
            raise ValueError("2025 Blind outcomes cannot enter PR-C")
        if threshold.policy_hash != self.policy.content_hash():
            raise ValueError("threshold was fitted under a different outcome policy")
        if label.benchmark_return is not None or label.excess_return is not None:
            raise ValueError(
                "PR-C v1 does not accept ungoverned benchmark or excess returns"
            )

        available = label.availability is MarketLabelAvailability.AVAILABLE
        raw_return = label.raw_return if available else None
        poor_performer = (
            raw_return <= threshold.threshold if raw_return is not None else None
        )
        return FiveDayOutcomeTarget(
            policy_hash=self.policy.content_hash(),
            threshold_hash=threshold.content_hash(),
            case_id=label.case_id,
            stock_code=label.stock_code,
            cohort_year=label.cohort_year,
            dataset_split=label.dataset_split,
            listing_date=label.listing_date.isoformat() if label.listing_date else None,
            target_trading_date=(
                label.target_trading_date.isoformat()
                if label.target_trading_date
                else None
            ),
            raw_return_5d=raw_return,
            abnormal_return_5d=None,
            poor_performer_5d=poor_performer,
            poor_performer_threshold=threshold.threshold,
            availability=label.availability,
            missing_reason=label.missing_reason,
            source_label_policy_version=label.label_policy_version,
            source_label_hash=_label_hash(label),
        )

    @staticmethod
    def _require_five_day(label: MarketOutcomeLabel) -> None:
        if label.horizon is not MarketLabelHorizon.FIVE_DAYS:
            raise ValueError("PR-C accepts only 5D market labels")
