"""Hermetic official-bridge and outcome-pack fixtures for the dynamic Market-X."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable

from ipo_risk.market.ipo_market_context_features import content_hash
from ipo_risk.market.prior_ipo_history import (
    PRIOR_IPO_OUTCOME_PACK_SCHEMA_VERSION,
)

BRIDGE_FIELDS = (
    "case_id",
    "stock_code_wind",
    "official_listed_date",
    "source_year",
    "official_match_status",
    "selected_name",
    "official_industry_name",
    "official_funds_raised",
)


def bridge_row(
    *,
    case_id: str,
    stock_code: str,
    listing_date: date,
    industry: str = "软件服务",
    funds_raised: str = "100,000,000",
    source_year: int | None = None,
    match_status: str = "matched",
) -> dict[str, str]:
    return {
        "case_id": case_id,
        "stock_code_wind": stock_code,
        "official_listed_date": listing_date.isoformat(),
        "source_year": str(source_year if source_year is not None else listing_date.year),
        "official_match_status": match_status,
        "selected_name": case_id,
        "official_industry_name": industry,
        "official_funds_raised": funds_raised,
    }


def prior_ipo_rows(
    *,
    first_listing: date,
    count: int,
    step_days: int = 7,
    industry: str = "软件服务",
    source_year: int | None = None,
) -> list[dict[str, str]]:
    """Evenly spaced governed prior IPOs starting at ``first_listing``."""

    rows = []
    for index in range(count):
        listing = first_listing + timedelta(days=step_days * index)
        rows.append(
            bridge_row(
                case_id=f"ipo_{listing.year}_{index:05d}",
                stock_code=f"{1000 + index}.HK",
                listing_date=listing,
                industry=industry,
                source_year=source_year,
            )
        )
    return rows


def write_bridge(root: Path, rows: Iterable[dict[str, str]]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / "ipo_official_master_bridge.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BRIDGE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_outcome_pack(
    root: Path,
    bridge_path: Path,
    records: Iterable[dict[str, Any]],
    *,
    outcome_cohort_years: list[int] | None = None,
    bridge_sha256: str | None = None,
) -> Path:
    """Write a self-consistent outcome pack without needing licensed EOD."""

    body: dict[str, Any] = {
        "schema_version": PRIOR_IPO_OUTCOME_PACK_SCHEMA_VERSION,
        "outcome_source": "test_fixture_derived",
        "outcome_cohort_years": outcome_cohort_years or [2020, 2021, 2022, 2023, 2024],
        "official_bridge_sha256": bridge_sha256
        or hashlib.sha256(bridge_path.read_bytes()).hexdigest(),
        "ipo_eod_sha256": "0" * 64,
        "blind_outcomes_included": False,
        "records": list(records),
    }
    body["content_hash"] = content_hash(body)
    path = root / "prior_ipo_outcome_pack.json"
    path.write_text(json.dumps(body, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return path


def outcome_record(
    row: dict[str, str],
    *,
    return_1d: float | None,
    return_5d: float | None,
    settle_days: int = 1,
) -> dict[str, Any]:
    listing = date.fromisoformat(row["official_listed_date"])
    return {
        "case_id": row["case_id"],
        "stock_code": row["stock_code_wind"],
        "listing_date": row["official_listed_date"],
        "target_1d": (listing + timedelta(days=settle_days)).isoformat(),
        "return_1d": return_1d,
        "target_5d": (listing + timedelta(days=settle_days + 5)).isoformat(),
        "return_5d": return_5d,
    }
