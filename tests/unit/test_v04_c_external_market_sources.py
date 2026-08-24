from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from scripts.prepare_v04_c_external_market_sources import (
    combine_hkex_market_scopes,
    parse_hkex_archive,
    parse_hsi_chart,
)


def test_parse_hsi_chart_rejects_unexpected_series() -> None:
    payload = json.dumps(
        {"indexCode": "wrong", "indexLevels-5y": [[1629417600000, 1.0]]}
    ).encode()
    with pytest.raises(ValueError, match="unexpected indexCode"):
        parse_hsi_chart(
            payload, benchmark_id="HSCIE", internal_index_code="00011.01"
        )


def test_parse_hkex_archive_and_combine_scopes() -> None:
    def payload(turnover: str) -> bytes:
        return json.dumps(
            {
                "tables": [
                    {
                        "body": [
                            {"row": 2, "col": 0, "text": "2020/01/02"},
                            {"row": 2, "col": 1, "text": ""},
                            {"row": 2, "col": 2, "text": turnover},
                            {"row": 2, "col": 3, "text": "100"},
                            {"row": 2, "col": 4, "text": "10"},
                        ]
                    }
                ]
            }
        ).encode()

    main = parse_hkex_archive(payload("1,000"), market_scope="Main Board")
    gem = parse_hkex_archive(payload("20"), market_scope="GEM")
    combined, audit = combine_hkex_market_scopes(main, gem)

    assert combined[0]["total_market_turnover"] == 1020
    assert combined[0]["market_scope"].startswith("Main Board + GEM")
    assert audit["mismatched_calendar_date_count"] == 0


def test_combine_hkex_market_scopes_does_not_fill_calendar_gaps() -> None:
    main = [{"trading_date": "2020-01-02", "turnover_hkd": 100}]
    gem: list[dict[str, object]] = []
    combined, audit = combine_hkex_market_scopes(main, gem)

    assert combined == []
    assert audit["main_only_dates"] == ["2020-01-02"]


def test_mapping_draft_is_complete_and_does_not_invent_effective_dates() -> None:
    path = Path("data/catalog/v04_c_hsics_benchmark_mapping_draft.csv")
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 12
    assert {row["industry_code"] for row in rows} == {
        "00",
        "05",
        "10",
        "23",
        "25",
        "28",
        "35",
        "40",
        "50",
        "60",
        "70",
        "80",
    }
    assert len({row["benchmark_id"] for row in rows}) == 12
    assert all(row["effective_from"] == "" for row in rows)
    assert all(row["effective_to"] == "" for row in rows)
