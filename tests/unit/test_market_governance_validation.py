from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from ipo_risk.market.exceptions import (
    BlindDataLeakageError,
    IneligibleMarketSecurityError,
    MarketDatasetGovernanceError,
    UnexpectedCohortYearError,
)
from ipo_risk.market.governance import (
    MarketDatasetGuard,
    MarketDatasetSplitPolicy,
    MarketSecurityEligibilityPolicy,
)
from ipo_risk.market.labels import MarketLabelGenerator
from ipo_risk.market.validation import MarketDataValidator
from ipo_risk.schemas.market import (
    IPOMarketMetadata,
    MarketDailyBar,
    MarketDataProvenance,
    MarketDatasetSplit,
    MarketExchange,
    MarketSecurityEligibility,
    MarketSecurityType,
)


def provenance(record: str) -> MarketDataProvenance:
    return MarketDataProvenance(
        source="fixture", dataset_version="fixture-v1", source_record_id=record
    )


def metadata(year: int, code: str = "0001.HK", case_id: str | None = None) -> IPOMarketMetadata:
    return IPOMarketMetadata(
        case_id=case_id or f"ipo_{year}_{code[:4]}",
        stock_code=code,
        cohort_year=year,
        listing_date=date(year, 1, 2),
        listing_price=Decimal("10"),
        currency="HKD",
        exchange=MarketExchange.HKEX,
        source="fixture",
        provenance=provenance(f"metadata-{year}-{code}"),
    )


def bars(info: IPOMarketMetadata, count: int = 60) -> list[MarketDailyBar]:
    return [
        MarketDailyBar(
            stock_code=info.stock_code,
            trading_date=info.listing_date + timedelta(days=index),
            open=Decimal("10"),
            high=Decimal("11"),
            low=Decimal("9"),
            close=Decimal("10.5"),
            source="fixture",
            provenance=provenance(f"bar-{index}"),
        )
        for index in range(count)
    ]


@pytest.mark.parametrize(
    "year,expected",
    [
        (2020, MarketDatasetSplit.DEVELOPMENT),
        (2023, MarketDatasetSplit.DEVELOPMENT),
        (2024, MarketDatasetSplit.VALIDATION),
        (2025, MarketDatasetSplit.BLIND),
    ],
)
def test_frozen_year_split(year: int, expected: MarketDatasetSplit) -> None:
    assert MarketDatasetSplitPolicy().split_for_year(year) is expected


def test_ordinary_equity_is_accepted_and_policy_version_is_preserved() -> None:
    policy = MarketSecurityEligibilityPolicy()
    decision = policy.assess(MarketSecurityType.ORDINARY_EQUITY)
    info = IPOMarketMetadata(
        case_id="ipo_2024_00001",
        stock_code="0001.HK",
        cohort_year=2024,
        listing_date=date(2024, 1, 2),
        listing_price=Decimal("10"),
        currency="HKD",
        exchange=MarketExchange.HKEX,
        security_type=decision.security_type,
        modeling_eligibility=decision.eligibility,
        eligibility_reason=decision.reason,
        eligibility_policy_version=decision.policy_version,
        source="fixture",
        provenance=provenance("ordinary-equity"),
    )

    assert policy.require_eligible(info).eligibility is MarketSecurityEligibility.ELIGIBLE
    assert info.eligibility_policy_version == "v04_market_security_eligibility_v1"


@pytest.mark.parametrize(
    "security_type",
    [
        MarketSecurityType.REIT,
        MarketSecurityType.SPAC,
        MarketSecurityType.WARRANT,
        MarketSecurityType.UNKNOWN,
    ],
)
def test_nonordinary_and_unknown_security_types_are_explicitly_ineligible(
    security_type: MarketSecurityType,
) -> None:
    policy = MarketSecurityEligibilityPolicy()
    decision = policy.assess(security_type)
    info = IPOMarketMetadata(
        case_id="ipo_2024_00001",
        stock_code="0001.HK",
        cohort_year=2024,
        listing_date=date(2024, 1, 2),
        exchange=MarketExchange.HKEX,
        security_type=decision.security_type,
        modeling_eligibility=decision.eligibility,
        eligibility_reason=decision.reason,
        eligibility_policy_version=decision.policy_version,
        source="fixture",
        provenance=provenance(security_type.value),
    )

    assert decision.eligibility is MarketSecurityEligibility.INELIGIBLE
    with pytest.raises(IneligibleMarketSecurityError):
        policy.require_eligible(info)


def test_unexpected_year_is_rejected() -> None:
    with pytest.raises(UnexpectedCohortYearError):
        MarketDatasetSplitPolicy().split_for_year(2026)


def test_blind_and_validation_labels_cannot_enter_development() -> None:
    generator = MarketLabelGenerator()
    guard = MarketDatasetGuard()
    blind = generator.generate(metadata(2025), bars(metadata(2025)))
    validation = generator.generate(metadata(2024), bars(metadata(2024)))
    development = generator.generate(metadata(2023), bars(metadata(2023)))

    assert guard.require_development(development) == development
    with pytest.raises(BlindDataLeakageError):
        guard.require_development(blind)
    with pytest.raises(MarketDatasetGovernanceError):
        guard.require_development(validation)


def test_partition_never_mixes_year_splits() -> None:
    generator = MarketLabelGenerator()
    labels = []
    for year in (2023, 2024, 2025):
        info = metadata(year, code=f"{year % 10000:04d}.HK")
        labels.extend(generator.generate(info, bars(info, 1)))
    partitions = MarketDatasetGuard().partition(labels)
    assert {label.cohort_year for label in partitions[MarketDatasetSplit.DEVELOPMENT]} == {2023}
    assert {label.cohort_year for label in partitions[MarketDatasetSplit.VALIDATION]} == {2024}
    assert {label.cohort_year for label in partitions[MarketDatasetSplit.BLIND]} == {2025}


def test_validator_detects_duplicate_bars_and_missing_stock_mapping() -> None:
    info = metadata(2023)
    one = bars(info, 1)[0]
    orphan = one.model_copy(update={"stock_code": "9999.HK"})
    result = MarketDataValidator().validate([info], [one, one, orphan])
    assert result.status == "invalid"
    assert {issue.code for issue in result.errors} >= {
        "duplicate_market_bar",
        "missing_stock_mapping",
    }


def test_validator_detects_invalid_input_date_order() -> None:
    info = metadata(2023)
    values = bars(info, 2)
    result = MarketDataValidator().validate([info], list(reversed(values)))
    assert result.status == "invalid"
    assert "invalid_date_order" in {issue.code for issue in result.errors}


def test_validator_allows_explicit_unavailable_labels_with_warning() -> None:
    info = metadata(2023)
    values = bars(info, 1)
    labels = MarketLabelGenerator().generate(info, values)
    result = MarketDataValidator().validate([info], values, labels)
    assert result.status == "valid"
    assert "insufficient_forward_history" in {issue.code for issue in result.warnings}


def test_validator_reports_blind_leakage_for_development_use() -> None:
    info = metadata(2025)
    values = bars(info, 1)
    labels = MarketLabelGenerator().generate(info, values)
    result = MarketDataValidator().validate([info], values, labels, development_use=True)
    assert result.status == "invalid"
    assert "blind_leakage" in {issue.code for issue in result.errors}


def test_validator_detects_listing_date_after_price_window_and_duplicate_mapping() -> None:
    info = metadata(2023)
    old_bar = bars(info, 1)[0].model_copy(update={"trading_date": date(2022, 12, 30)})
    duplicate_case = metadata(2023, code="0002.HK", case_id=info.case_id)
    result = MarketDataValidator().validate([info, duplicate_case], [old_bar])
    assert result.status == "invalid"
    assert {issue.code for issue in result.errors} >= {
        "duplicate_case_mapping",
        "listing_date_after_price_window",
    }
