"""Chronological dataset partitioning and fail-closed blind protection."""

from __future__ import annotations

from collections.abc import Iterable

from ipo_risk.market.exceptions import (
    BlindDataLeakageError,
    MarketDatasetGovernanceError,
    UnexpectedCohortYearError,
)
from ipo_risk.schemas.market import (
    MarketDatasetSplit,
    MarketOutcomeLabel,
    expected_market_split,
)


class MarketDatasetSplitPolicy:
    """Frozen deterministic mapping: 2020-23 dev, 2024 validation, 2025 blind."""

    version = "v04_chronological_split_v1"

    def split_for_year(self, cohort_year: int) -> MarketDatasetSplit:
        try:
            return expected_market_split(cohort_year)
        except ValueError as exc:
            raise UnexpectedCohortYearError(str(exc)) from exc


class MarketDatasetGuard:
    """Prevent validation or blind rows from entering development operations."""

    def __init__(self, policy: MarketDatasetSplitPolicy | None = None) -> None:
        self.policy = policy or MarketDatasetSplitPolicy()

    def require_development(
        self, labels: Iterable[MarketOutcomeLabel]
    ) -> list[MarketOutcomeLabel]:
        materialized = list(labels)
        for label in materialized:
            expected = self.policy.split_for_year(label.cohort_year)
            if label.dataset_split is not expected:
                raise MarketDatasetGovernanceError(
                    f"{label.case_id} declares {label.dataset_split.value}; expected {expected.value}"
                )
            if expected is MarketDatasetSplit.BLIND:
                raise BlindDataLeakageError(
                    f"2025 blind case {label.case_id} cannot enter a development pipeline"
                )
            if expected is not MarketDatasetSplit.DEVELOPMENT:
                raise MarketDatasetGovernanceError(
                    f"{label.case_id} is {expected.value}, not development"
                )
        return materialized

    def partition(
        self, labels: Iterable[MarketOutcomeLabel]
    ) -> dict[MarketDatasetSplit, list[MarketOutcomeLabel]]:
        partitions = {split: [] for split in MarketDatasetSplit}
        for label in labels:
            expected = self.policy.split_for_year(label.cohort_year)
            if label.dataset_split is not expected:
                raise MarketDatasetGovernanceError(
                    f"{label.case_id} split is inconsistent with its cohort year"
                )
            partitions[expected].append(label)
        return partitions
