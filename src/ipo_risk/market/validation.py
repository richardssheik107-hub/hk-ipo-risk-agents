"""Lightweight integrity validation for V04-1 market datasets."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from ipo_risk.schemas.market import (
    IPOMarketMetadata,
    MarketDailyBar,
    MarketDatasetSplit,
    MarketLabelAvailability,
    MarketLabelMissingReason,
    MarketOutcomeLabel,
    MarketValidationIssue,
    MarketValidationResult,
    MarketValidationSeverity,
    expected_market_split,
)


class MarketDataValidator:
    """Report fatal integrity errors separately from accepted unavailability."""

    def validate(
        self,
        metadata_rows: Iterable[IPOMarketMetadata],
        bars: Iterable[MarketDailyBar],
        labels: Iterable[MarketOutcomeLabel] = (),
        *,
        development_use: bool = False,
    ) -> MarketValidationResult:
        metadata = list(metadata_rows)
        daily_bars = list(bars)
        outcome_labels = list(labels)
        errors: list[MarketValidationIssue] = []
        warnings: list[MarketValidationIssue] = []

        metadata_by_stock: dict[str, IPOMarketMetadata] = {}
        case_counts = Counter(item.case_id for item in metadata)
        for item in metadata:
            if item.stock_code in metadata_by_stock:
                errors.append(self._error("duplicate_stock_mapping", item, "duplicate stock metadata"))
            metadata_by_stock[item.stock_code] = item
            if case_counts[item.case_id] > 1:
                errors.append(self._error("duplicate_case_mapping", item, "duplicate case metadata"))
            if item.listing_date is None:
                warnings.append(self._warning("missing_listing_date", item, "listing date unavailable"))
            if item.listing_price is None:
                warnings.append(self._warning("missing_listing_price", item, "official listing price unavailable"))
            if item.currency is None:
                warnings.append(self._warning("missing_currency", item, "currency unavailable"))

        bar_keys = Counter((bar.stock_code, bar.trading_date) for bar in daily_bars)
        bars_by_stock: dict[str, list[MarketDailyBar]] = {}
        last_date_by_stock = {}
        for bar in daily_bars:
            bars_by_stock.setdefault(bar.stock_code, []).append(bar)
            previous_date = last_date_by_stock.get(bar.stock_code)
            if previous_date is not None and bar.trading_date < previous_date:
                errors.append(
                    self._issue(
                        MarketValidationSeverity.ERROR,
                        "invalid_date_order",
                        f"bar date {bar.trading_date} precedes {previous_date}",
                        stock_code=bar.stock_code,
                    )
                )
            last_date_by_stock[bar.stock_code] = bar.trading_date
            if bar_keys[(bar.stock_code, bar.trading_date)] > 1:
                errors.append(
                    self._issue(
                        MarketValidationSeverity.ERROR,
                        "duplicate_market_bar",
                        f"duplicate bar on {bar.trading_date}",
                        stock_code=bar.stock_code,
                    )
                )
            if bar.stock_code not in metadata_by_stock:
                errors.append(
                    self._issue(
                        MarketValidationSeverity.ERROR,
                        "missing_stock_mapping",
                        "daily bar has no IPO metadata",
                        stock_code=bar.stock_code,
                    )
                )

        for item in metadata:
            stock_bars = bars_by_stock.get(item.stock_code, [])
            if not stock_bars:
                warnings.append(self._warning("missing_daily_bars", item, "no daily bars available"))
            elif item.listing_date is not None and max(bar.trading_date for bar in stock_bars) < item.listing_date:
                errors.append(
                    self._error(
                        "listing_date_after_price_window",
                        item,
                        "listing date is after the available price window",
                    )
                )

        label_keys = Counter(
            (label.case_id, label.horizon, label.label_policy_version)
            for label in outcome_labels
        )
        for label in outcome_labels:
            if label.case_id not in {item.case_id for item in metadata}:
                errors.append(
                    self._issue(
                        MarketValidationSeverity.ERROR,
                        "missing_listing_metadata",
                        "outcome label has no IPO metadata",
                        stock_code=label.stock_code,
                        case_id=label.case_id,
                    )
                )
            if label_keys[(label.case_id, label.horizon, label.label_policy_version)] > 1:
                errors.append(
                    self._issue(
                        MarketValidationSeverity.ERROR,
                        "duplicate_outcome_label",
                        f"duplicate {label.horizon.value} outcome label",
                        stock_code=label.stock_code,
                        case_id=label.case_id,
                    )
                )
            expected = expected_market_split(label.cohort_year)
            if label.dataset_split is not expected:
                errors.append(
                    self._issue(
                        MarketValidationSeverity.ERROR,
                        "unexpected_year_split",
                        "label split conflicts with cohort year",
                        stock_code=label.stock_code,
                        case_id=label.case_id,
                    )
                )
            if development_use and label.dataset_split is MarketDatasetSplit.BLIND:
                errors.append(
                    self._issue(
                        MarketValidationSeverity.ERROR,
                        "blind_leakage",
                        "2025 blind label is forbidden in development",
                        stock_code=label.stock_code,
                        case_id=label.case_id,
                    )
                )
            elif development_use and label.dataset_split is not MarketDatasetSplit.DEVELOPMENT:
                errors.append(
                    self._issue(
                        MarketValidationSeverity.ERROR,
                        "non_development_split",
                        "non-development label supplied to development validation",
                        stock_code=label.stock_code,
                        case_id=label.case_id,
                    )
                )
            if (
                label.availability is MarketLabelAvailability.UNAVAILABLE
                and label.missing_reason is MarketLabelMissingReason.INSUFFICIENT_FORWARD_HISTORY
            ):
                warnings.append(
                    self._issue(
                        MarketValidationSeverity.WARNING,
                        "insufficient_forward_history",
                        f"{label.horizon.value} label is unavailable",
                        stock_code=label.stock_code,
                        case_id=label.case_id,
                    )
                )

        return MarketValidationResult(
            status="invalid" if errors else "valid",
            errors=self._deduplicate(errors),
            warnings=self._deduplicate(warnings),
            counts={
                "metadata": len(metadata),
                "bars": len(daily_bars),
                "labels": len(outcome_labels),
                "errors": len(self._deduplicate(errors)),
                "warnings": len(self._deduplicate(warnings)),
            },
        )

    @staticmethod
    def _deduplicate(issues: list[MarketValidationIssue]) -> list[MarketValidationIssue]:
        seen: set[tuple[str, str | None, str | None, str]] = set()
        result = []
        for issue in issues:
            key = (issue.code, issue.stock_code, issue.case_id, issue.message)
            if key not in seen:
                seen.add(key)
                result.append(issue)
        return result

    def _error(self, code: str, item: IPOMarketMetadata, message: str) -> MarketValidationIssue:
        return self._issue(
            MarketValidationSeverity.ERROR,
            code,
            message,
            stock_code=item.stock_code,
            case_id=item.case_id,
        )

    def _warning(self, code: str, item: IPOMarketMetadata, message: str) -> MarketValidationIssue:
        return self._issue(
            MarketValidationSeverity.WARNING,
            code,
            message,
            stock_code=item.stock_code,
            case_id=item.case_id,
        )

    @staticmethod
    def _issue(
        severity: MarketValidationSeverity,
        code: str,
        message: str,
        *,
        stock_code: str | None = None,
        case_id: str | None = None,
    ) -> MarketValidationIssue:
        return MarketValidationIssue(
            severity=severity,
            code=code,
            message=message,
            stock_code=stock_code,
            case_id=case_id,
        )
