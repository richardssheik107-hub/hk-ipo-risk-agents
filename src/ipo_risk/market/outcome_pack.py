"""Build the licensed-derived prior-IPO outcome tier for dynamic Market-X.

The offer-fact tier of the prior-IPO universe is public and committed. The
outcome tier -- each prior IPO's 1D/5D return -- is derived from licensed EOD
prices, so the repository carries this builder and the pack schema rather than
the pack itself. Whoever holds the licensed EOD extract materializes the pack
locally, and dynamic Market-X reports its outcome families as available only
once that pack validates.

Only the 2020-2024 outcome cohort is ever written. A blind-cohort listing is a
hard error here, not a filtered row, so a mis-scoped provider cannot quietly
produce a pack that leaks 2025 outcomes into a feature.
"""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Protocol, Sequence

from ipo_risk.market.ipo_market_context_features import content_hash
from ipo_risk.market.labels import MarketLabelGenerator
from ipo_risk.market.prior_ipo_history import (
    OUTCOME_COHORT_YEARS,
    PRIOR_IPO_OUTCOME_PACK_SCHEMA_VERSION,
    PriorIPOHistoryError,
    csv_content_hashes,
)
from ipo_risk.schemas.market import (
    IPOMarketMetadata,
    MarketDailyBar,
    MarketLabelHorizon,
)

OUTCOME_PACK_SOURCE = "governed_ipo_eod_derived"


class _BarSource(Protocol):
    def get_daily_bars(self, stock_code: str) -> Sequence[MarketDailyBar]: ...


def build_prior_ipo_outcome_pack(
    *,
    metadata: Iterable[IPOMarketMetadata],
    bar_source: _BarSource,
    bridge_path: str | Path,
    ipo_eod_sha256: str,
    generator: MarketLabelGenerator | None = None,
) -> dict[str, Any]:
    """Return a deterministic, content-hashed prior-IPO outcome pack payload."""

    path = Path(bridge_path)
    label_generator = generator or MarketLabelGenerator()
    records: list[dict[str, Any]] = []
    for item in sorted(metadata, key=lambda value: value.case_id):
        if item.listing_date is None:
            raise PriorIPOHistoryError(
                f"outcome pack requires an official listing date: {item.case_id}"
            )
        if item.listing_date.year not in OUTCOME_COHORT_YEARS:
            raise PriorIPOHistoryError(
                "outcome pack refuses a listing outside the allowed cohort years: "
                f"{item.case_id}"
            )
        labels = {
            label.horizon: label
            for label in label_generator.generate(item, bar_source.get_daily_bars(item.stock_code))
        }
        one = labels[MarketLabelHorizon.ONE_DAY]
        five = labels[MarketLabelHorizon.FIVE_DAYS]
        records.append(
            {
                "case_id": item.case_id,
                "stock_code": item.stock_code,
                "listing_date": item.listing_date.isoformat(),
                "target_1d": _iso(one.target_trading_date),
                "return_1d": _float(one.raw_return),
                "target_5d": _iso(five.target_trading_date),
                "return_5d": _float(five.raw_return),
            }
        )
    if not records:
        raise PriorIPOHistoryError("outcome pack would contain no records")

    body: dict[str, Any] = {
        "schema_version": PRIOR_IPO_OUTCOME_PACK_SCHEMA_VERSION,
        "outcome_source": OUTCOME_PACK_SOURCE,
        "outcome_cohort_years": sorted(OUTCOME_COHORT_YEARS),
        "official_bridge_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "ipo_eod_sha256": ipo_eod_sha256,
        "blind_outcomes_included": False,
        "records": records,
    }
    if body["official_bridge_sha256"] not in csv_content_hashes(path):
        raise PriorIPOHistoryError("official bridge hash could not be reproduced")
    body["content_hash"] = content_hash(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    return body


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _float(value: Any) -> float | None:
    return float(value) if value is not None else None
