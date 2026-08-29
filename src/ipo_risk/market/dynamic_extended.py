"""Market-X Extended for IPOs that have no frozen readiness row.

The Extended sources are governed and accepted -- CSMAR HSI, HKEX total-market
turnover, and the twelve Hang Seng Composite industry series. What only served
the frozen 438 was the *projection*: ``v04_c_extended_readiness_438.csv`` is
indexed by ``case_id``, so a new prospectus could never be looked up in it.

``PreListingMarketFeatureEngine`` has no such limitation. It takes a listing
date as an exclusive cutoff and nothing else, so the missing piece was a
composition layer that reads the same governed series for an arbitrary date.
That is all this module is.

Two governance rules are carried through unchanged:

* ``industry_return_5d`` / ``industry_return_20d`` stay
  ``INDUSTRY_MAPPING_PIT_BLOCKED``. The delivered HSICS classification has no
  effective dates, so it cannot be shown to be the listing-time classification.
  Nothing here unblocks it, and no proxy stands in for it.
* The normalized CSMAR/HKEX caches are licensed and stay out of Git. Absent
  them, the six Extended names simply do not appear -- they are not zero-filled
  and not faked into an "unavailable" row that implies a source was consulted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from ipo_risk.market.csmar_hsi import CSMAR_HSI_REFERENCE_ID, CSMARHSIProvider
from ipo_risk.market.features import PreListingMarketFeatureEngine
from ipo_risk.market.ipo_market_context_features import (
    IPO_MARKET_CONTEXT_FEATURE_UNITS,
)
from ipo_risk.market.official_market_sources import OfficialHKEXTurnoverProvider
from ipo_risk.schemas.final_supervision import MarketObservation
from ipo_risk.schemas.market import MarketDataProvenance, expected_market_split
from ipo_risk.schemas.market_features import (
    MARKET_RAW_FEATURE_ORDER,
    PreListingMarketFeatureContext,
)

DYNAMIC_EXTENDED_SOURCE = "dynamic_market_x_extended"
DYNAMIC_EXTENDED_DERIVATION = "dynamic point-in-time Market-X Extended feature"
DYNAMIC_EXTENDED_VERSION = "v046_dynamic_market_x_extended_v1"

# The governed reason the C lane recorded, reproduced verbatim rather than
# paraphrased: the classification cannot be shown to be point-in-time.
INDUSTRY_MAPPING_PIT_BLOCKED = "INDUSTRY_MAPPING_PIT_BLOCKED"
OUTSIDE_GOVERNED_SPLIT = "listing_year_outside_governed_market_split"

# The six Extended names are exactly those not already carried by Core.
EXTENDED_ONLY_FEATURE_ORDER = tuple(
    name
    for name in MARKET_RAW_FEATURE_ORDER
    if name not in IPO_MARKET_CONTEXT_FEATURE_UNITS
)
_INDUSTRY_FEATURES = frozenset({"industry_return_5d", "industry_return_20d"})
_EXTENDED_UNITS = {
    "hsi_return_5d": "ratio",
    "hsi_return_20d": "ratio",
    "industry_return_5d": "ratio",
    "industry_return_20d": "ratio",
    "market_turnover_20d_mean": "currency",
    "market_volatility_20d": "ratio",
}


class DynamicExtendedMarketError(ValueError):
    """The governed Extended caches could not be loaded or validated."""


@dataclass(frozen=True)
class DynamicExtendedResult:
    observations: tuple[MarketObservation, ...]
    provenance: dict[str, Any]


class DynamicExtendedMarketSource:
    """Serve governed HSI and turnover context for an arbitrary listing date."""

    name = DYNAMIC_EXTENDED_SOURCE

    def __init__(
        self,
        *,
        hsi_normalized_csv: str | Path,
        turnover_normalized_csv: str | Path,
        hsi_manifest: str | Path = "data/catalog/csmar_hsi_source_manifest.json",
        external_manifest: str | Path = (
            "data/catalog/v04_c_external_market_source_manifest.json"
        ),
    ) -> None:
        self.hsi_normalized_csv = Path(hsi_normalized_csv)
        self.turnover_normalized_csv = Path(turnover_normalized_csv)
        self.hsi_manifest = Path(hsi_manifest)
        self.external_manifest = Path(external_manifest)
        self._hsi: CSMARHSIProvider | None = None
        self._turnover: OfficialHKEXTurnoverProvider | None = None
        self._engine = PreListingMarketFeatureEngine()

    def _providers(self) -> tuple[CSMARHSIProvider, OfficialHKEXTurnoverProvider]:
        if self._hsi is None or self._turnover is None:
            try:
                self._hsi = CSMARHSIProvider(
                    self.hsi_normalized_csv, self.hsi_manifest
                )
                self._turnover = OfficialHKEXTurnoverProvider(
                    self.turnover_normalized_csv, self.external_manifest
                )
            except (OSError, ValueError) as exc:
                self._hsi = None
                self._turnover = None
                raise DynamicExtendedMarketError(str(exc)) from exc
        return self._hsi, self._turnover

    def context(
        self,
        *,
        listing_date: date,
        case_id: str | None = None,
        stock_code: str | None = None,
    ) -> DynamicExtendedResult:
        """Return the six Extended observations for one point-in-time cutoff."""

        hsi, turnover = self._providers()
        identity = {
            "case_id": case_id or f"dynamic_{listing_date.isoformat()}",
            "stock_code": stock_code or "UNKNOWN.HK",
        }
        try:
            feature_context = PreListingMarketFeatureContext(
                case_id=identity["case_id"],
                stock_code=identity["stock_code"],
                cohort_year=listing_date.year,
                listing_date=listing_date,
                dataset_split=expected_market_split(listing_date.year),
                benchmark_reference_id=CSMAR_HSI_REFERENCE_ID,
                # Deliberately None: the classification is not PIT-safe, so the
                # engine is never handed an industry series to compute from.
                industry_reference_id=None,
                source="governed official Market-X Extended sources",
                provenance=MarketDataProvenance(
                    source="governed_market_x_extended",
                    dataset_version=DYNAMIC_EXTENDED_VERSION,
                    source_record_id=identity["case_id"],
                    metadata={
                        "hsi_source_version": hsi.manifest.source_version(),
                        "industry_mapping_pit_status": INDUSTRY_MAPPING_PIT_BLOCKED,
                    },
                ),
            )
        except ValueError:
            # expected_market_split only recognises 2020-2025. Widening it would
            # change a frozen split-governance contract, so the honest answer is
            # that this listing year has no governed Extended projection.
            return DynamicExtendedResult(
                observations=tuple(
                    MarketObservation(
                        name=name,
                        availability="unavailable",
                        missing_reason=(
                            INDUSTRY_MAPPING_PIT_BLOCKED
                            if name in _INDUSTRY_FEATURES
                            else OUTSIDE_GOVERNED_SPLIT
                        ),
                        source=DYNAMIC_EXTENDED_SOURCE,
                    )
                    for name in EXTENDED_ONLY_FEATURE_ORDER
                ),
                provenance=self._provenance(
                    hsi, listing_date, available_count=0, observation_date=None
                ),
            )

        snapshot = self._engine.build(
            feature_context,
            benchmark_bars=hsi.get_benchmark_bars(
                CSMAR_HSI_REFERENCE_ID, end_date_exclusive=listing_date
            ),
            activity_observations=turnover.get_market_activity(
                end_date_exclusive=listing_date
            ),
        )
        by_name = {item.name: item for item in snapshot.features}
        observations: list[MarketObservation] = []
        for name in EXTENDED_ONLY_FEATURE_ORDER:
            if name in _INDUSTRY_FEATURES:
                observations.append(
                    MarketObservation(
                        name=name,
                        availability="unavailable",
                        missing_reason=INDUSTRY_MAPPING_PIT_BLOCKED,
                        source=DYNAMIC_EXTENDED_SOURCE,
                    )
                )
                continue
            value = by_name[name]
            if value.availability == "available" and value.value is not None:
                observations.append(
                    MarketObservation(
                        name=name,
                        value=float(value.value),
                        unit=_EXTENDED_UNITS[name],
                        availability="available",
                        derivation=DYNAMIC_EXTENDED_DERIVATION,
                        source=DYNAMIC_EXTENDED_SOURCE,
                    )
                )
                continue
            observations.append(
                MarketObservation(
                    name=name,
                    availability="unavailable",
                    missing_reason=(
                        value.missing_reason.value
                        if value.missing_reason is not None
                        else "source_unavailable"
                    ),
                    source=DYNAMIC_EXTENDED_SOURCE,
                )
            )
        available = sum(item.availability == "available" for item in observations)
        return DynamicExtendedResult(
            observations=tuple(observations),
            provenance=self._provenance(
                hsi,
                listing_date,
                available_count=available,
                observation_date=snapshot.observation_date,
            ),
        )

    def _provenance(
        self,
        hsi: CSMARHSIProvider,
        listing_date: date,
        *,
        available_count: int,
        observation_date: date | None,
    ) -> dict[str, Any]:
        return {
            "extended_pipeline": self.name,
            "extended_version": DYNAMIC_EXTENDED_VERSION,
            "extended_benchmark_reference_id": CSMAR_HSI_REFERENCE_ID,
            "extended_hsi_source_version": hsi.manifest.source_version(),
            "extended_observation_date": (
                observation_date.isoformat() if observation_date is not None else None
            ),
            "extended_pit_cutoff_date": listing_date.isoformat(),
            "extended_cutoff_semantics": "benchmark_session_strictly_before_listing_date",
            "extended_available_observation_count": available_count,
            "industry_mapping_pit_status": INDUSTRY_MAPPING_PIT_BLOCKED,
        }
