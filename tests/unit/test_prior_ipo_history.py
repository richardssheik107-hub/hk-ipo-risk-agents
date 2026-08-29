"""The governed prior-IPO universe and its optional licensed outcome tier."""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal

import pytest

from ipo_risk.market.outcome_pack import build_prior_ipo_outcome_pack
from ipo_risk.market.prior_ipo_history import (
    PriorIPOHistoryError,
    load_official_prior_ipo_history,
)
from ipo_risk.providers.market import InMemoryMarketDataProvider
from ipo_risk.schemas.market import (
    IPOMarketMetadata,
    MarketDailyBar,
    MarketDataProvenance,
    MarketExchange,
)
from ..dynamic_market_fixture import (
    bridge_row,
    outcome_record,
    prior_ipo_rows,
    write_bridge,
    write_outcome_pack,
)


def _provenance(record: str) -> MarketDataProvenance:
    return MarketDataProvenance(
        source="fixture", dataset_version="fixture-v1", source_record_id=record
    )


def test_coverage_end_is_the_last_source_year_not_the_last_known_listing(tmp_path) -> None:
    rows = prior_ipo_rows(first_listing=date(2024, 1, 3), count=4, source_year=2024)
    # A 2024 prospectus that only listed in 2025: a real fact, but proof that
    # 2025 coverage is partial rather than a reason to claim it is complete.
    rows.append(bridge_row(
        case_id="ipo_2024_09000", stock_code="9000.HK",
        listing_date=date(2025, 3, 1), source_year=2024,
    ))
    history = load_official_prior_ipo_history(write_bridge(tmp_path, rows))
    assert history.history_end_date == date(2024, 12, 31)
    assert history.provenance["records_beyond_coverage_end"] == 1
    # The out-of-coverage tail is known but never counted into a window.
    assert all(
        row["listing_date"] <= date(2024, 12, 31)
        for row in history.rows_before(date(2025, 6, 1))
    )


def test_unmatched_rows_are_skipped_rather_than_name_matched(tmp_path) -> None:
    rows = prior_ipo_rows(first_listing=date(2024, 1, 3), count=3)
    rows.append(bridge_row(
        case_id="ipo_2024_08000", stock_code="8000.HK",
        listing_date=date(2024, 2, 1), match_status="manifest_only_placeholder",
    ))
    history = load_official_prior_ipo_history(write_bridge(tmp_path, rows))
    assert history.provenance["matched_case_count"] == 3
    assert history.provenance["skipped_unmatched_row_count"] == 1


def test_outcome_pack_must_match_the_bridge_it_was_derived_from(tmp_path) -> None:
    rows = prior_ipo_rows(first_listing=date(2024, 1, 3), count=3)
    bridge = write_bridge(tmp_path, rows)
    pack = write_outcome_pack(
        tmp_path,
        bridge,
        [outcome_record(row, return_1d=0.1, return_5d=0.1) for row in rows],
        bridge_sha256="f" * 64,
    )
    with pytest.raises(PriorIPOHistoryError, match="not derived from this official bridge"):
        load_official_prior_ipo_history(bridge, outcome_pack_path=pack)


def test_outcome_pack_rejects_a_tampered_payload(tmp_path) -> None:
    rows = prior_ipo_rows(first_listing=date(2024, 1, 3), count=3)
    bridge = write_bridge(tmp_path, rows)
    pack = write_outcome_pack(
        tmp_path,
        bridge,
        [outcome_record(row, return_1d=0.1, return_5d=0.1) for row in rows],
    )
    payload = json.loads(pack.read_text(encoding="utf-8"))
    payload["records"][0]["return_1d"] = -0.99
    pack.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(PriorIPOHistoryError, match="content_hash"):
        load_official_prior_ipo_history(bridge, outcome_pack_path=pack)


def test_outcome_pack_rejects_a_blind_cohort_record(tmp_path) -> None:
    rows = prior_ipo_rows(first_listing=date(2025, 1, 6), count=3)
    bridge = write_bridge(tmp_path, rows)
    pack = write_outcome_pack(
        tmp_path,
        bridge,
        [outcome_record(row, return_1d=0.1, return_5d=0.1) for row in rows],
    )
    with pytest.raises(PriorIPOHistoryError, match="outside the allowed cohort years"):
        load_official_prior_ipo_history(bridge, outcome_pack_path=pack)


def test_outcome_pack_rejects_an_identity_it_cannot_join(tmp_path) -> None:
    rows = prior_ipo_rows(first_listing=date(2024, 1, 3), count=3)
    bridge = write_bridge(tmp_path, rows)
    records = [outcome_record(row, return_1d=0.1, return_5d=0.1) for row in rows]
    records[0]["stock_code"] = "7777.HK"
    pack = write_outcome_pack(tmp_path, bridge, records)
    with pytest.raises(PriorIPOHistoryError, match="stock code mismatch"):
        load_official_prior_ipo_history(bridge, outcome_pack_path=pack)


def test_builder_produces_a_pack_the_loader_accepts(tmp_path) -> None:
    """The licensed-EOD builder and the runtime loader agree on one contract."""

    listing = date(2024, 1, 3)
    rows = [bridge_row(case_id="ipo_2024_00001", stock_code="0001.HK", listing_date=listing)]
    bridge = write_bridge(tmp_path, rows)
    metadata = IPOMarketMetadata(
        case_id="ipo_2024_00001",
        stock_code="0001.HK",
        cohort_year=2024,
        listing_date=listing,
        listing_price=Decimal("10"),
        currency="HKD",
        exchange=MarketExchange.HKEX,
        source="fixture",
        provenance=_provenance("ipo-2024"),
    )
    sessions = [listing + timedelta(days=offset) for offset in range(0, 12)]
    bars = [
        MarketDailyBar(
            stock_code="0001.HK",
            trading_date=session,
            open=Decimal("10"),
            high=Decimal("12"),
            low=Decimal("9"),
            close=Decimal("11"),
            volume=Decimal("1000"),
            source="fixture",
            provenance=_provenance(f"bar-{session.isoformat()}"),
        )
        for session in sessions
    ]
    payload = build_prior_ipo_outcome_pack(
        metadata=[metadata],
        bar_source=InMemoryMarketDataProvider(metadata=[metadata], bars=bars),
        bridge_path=bridge,
        ipo_eod_sha256="a" * 64,
    )
    assert payload["blind_outcomes_included"] is False
    assert payload["records"][0]["return_1d"] == pytest.approx(0.1)
    pack = tmp_path / "prior_ipo_outcome_pack.json"
    pack.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    history = load_official_prior_ipo_history(bridge, outcome_pack_path=pack)
    assert history.outcome_history_available is True
    assert history.records[0].return_1d == pytest.approx(0.1)


def test_builder_refuses_to_write_a_blind_cohort_outcome(tmp_path) -> None:
    listing = date(2025, 1, 6)
    rows = [bridge_row(case_id="ipo_2025_00001", stock_code="0001.HK", listing_date=listing)]
    bridge = write_bridge(tmp_path, rows)
    metadata = IPOMarketMetadata(
        case_id="ipo_2025_00001",
        stock_code="0001.HK",
        cohort_year=2025,
        listing_date=listing,
        listing_price=Decimal("10"),
        currency="HKD",
        exchange=MarketExchange.HKEX,
        source="fixture",
        provenance=_provenance("ipo-2025"),
    )
    with pytest.raises(PriorIPOHistoryError, match="outside the allowed cohort years"):
        build_prior_ipo_outcome_pack(
            metadata=[metadata],
            bar_source=InMemoryMarketDataProvider(metadata=[metadata]),
            bridge_path=bridge,
            ipo_eod_sha256="a" * 64,
        )
