"""Market context providers for the PR-G Final Supervisor.

Deliberately *not* ``RiskAgent`` implementations.  The market channel is an
explanatory input, not a risk producer; giving it the ``RiskAgent`` shape would
let it inject unverified ``RiskItem`` values into the verified set, which is
precisely the failure mode the governance boundary exists to prevent.

Availability is decided by the snapshot's ``source``, never by whether its fields
happen to be non-null.  ``MockMarketDataProvider`` returns fixture numbers; a
renderer that treated those as market context would be fabricating data.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

from ipo_risk.market.ipo_market_context_features import (
    IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
    IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
    IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,
    IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER,
    content_hash,
    vectorize_ipo_market_context,
)
from ipo_risk.schemas import IPOProfile, MarketSnapshot
from ipo_risk.schemas.final_supervision import ChannelStatus, MarketContextView, MarketObservation

# Retired in PR-G: PR-B is COMPLETE / FROZEN, so no gate blocks this channel any
# more.  What is missing is a governed runtime adapter, which is a capability
# statement, not a gate statement.
MOCK_SOURCE = "mock"
UNAVAILABLE_SOURCE = "unavailable"
LEGACY_PIPELINE_NOTE = "legacy_market_snapshot_not_v04_market_x"

# name -> (unit, derivation, reason when the governed source cannot supply it)
_OBSERVATION_SPECS: dict[str, tuple[str, str, str]] = {
    "hsi_return_5d": ("ratio", "HSI close(t)/close(t-5) - 1 over observed sessions", "missing_benchmark"),
    "hsi_return_20d": ("ratio", "HSI close(t)/close(t-20) - 1 over observed sessions", "missing_benchmark"),
    "industry_return_5d": ("ratio", "industry benchmark close(t)/close(t-5) - 1", "missing_industry_series"),
    "industry_return_20d": ("ratio", "industry benchmark close(t)/close(t-20) - 1", "missing_industry_series"),
    "recent_ipo_break_rate": ("ratio", "share of recent prior IPOs closing below offer on day one", "no_recent_ipo_sample"),
    "recent_ipo_return_5d": ("ratio", "mean 5-session return of recent prior IPOs", "no_recent_ipo_sample"),
    "market_turnover": ("currency", "aggregate market turnover at the observation date", "missing_turnover_source"),
    "market_volatility": ("ratio", "realised volatility of the benchmark over the observation window", "missing_benchmark"),
    "sentiment_score": ("index", "composite pre-listing sentiment index", "source_unavailable"),
}

_CORE_UNITS: dict[str, str] = {
    "ipo_count_30d": "count",
    "ipo_count_60d": "count",
    "log_prior_ipo_funds_raised_30d": "log_currency",
    "log_prior_ipo_funds_raised_60d": "log_currency",
    "prior_ipo_funds_raised_30d_sample_count": "count",
    "prior_ipo_funds_raised_60d_sample_count": "count",
    "recent_ipo_break_rate": "ratio",
    "recent_ipo_return_5d": "ratio",
    "recent_ipo_1d_sample_count": "count",
    "recent_ipo_5d_sample_count": "count",
    "same_industry_ipo_count_180d": "count",
    "same_industry_recent_break_rate": "ratio",
    "same_industry_recent_return_5d": "ratio",
    "same_industry_recent_1d_sample_count": "count",
    "same_industry_recent_5d_sample_count": "count",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class GovernedPRBMarketContextProvider:
    """Load a hash-bound, point-in-time PR-B Core projection for one IPO.

    The provider does not calculate or impute features.  It validates and
    presents the already frozen 30-position PR-B artifact, keeping every
    unavailable raw feature explicit instead of replacing it with zero.
    """

    name = "governed_pr_b_core"

    def __init__(self, *, feature_dir: str | Path, official_bridge_path: str | Path) -> None:
        self.feature_dir = Path(feature_dir)
        self.official_bridge_path = Path(official_bridge_path)

    def context(self, profile: IPOProfile, market: MarketSnapshot | None = None) -> MarketContextView:
        del market  # PR-B is the governed source; the legacy snapshot is not mixed in.
        try:
            row = self._official_row(profile)
            artifact = self._artifact(row)
            observations = self._observations(artifact)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            detail = str(exc) if isinstance(exc, (ValueError, KeyError, TypeError)) else "artifact_io_or_json_error"
            return MarketContextView(
                status=ChannelStatus.UNAVAILABLE_ERROR,
                reason=f"governed PR-B Market-X projection failed validation: {detail}",
                provenance={"feature_pipeline": self.name},
            )
        return MarketContextView(
            status=ChannelStatus.AVAILABLE,
            reason="validated frozen PR-B Market-X Core projection",
            observations=observations,
            feature_manifest_hash=IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
            provenance={
                "feature_pipeline": self.name,
                "case_id": artifact["case_id"],
                "stock_code": artifact["stock_code"],
                "listing_date": artifact["listing_date"],
                "dataset_split": artifact["dataset_split"],
                "artifact_content_hash": artifact["content_hash"],
                "cutoff_semantics": artifact["cutoff_semantics"],
                "source_provenance": artifact["source_provenance"],
            },
        )

    def _official_row(self, profile: IPOProfile) -> dict[str, str]:
        if not profile.stock_code or profile.listing_date is None:
            raise ValueError("stock_code and listing_date are required")
        with self.official_bridge_path.open(encoding="utf-8-sig", newline="") as handle:
            rows = [
                row for row in csv.DictReader(handle)
                if row.get("stock_code_wind") == profile.stock_code
                and row.get("official_listed_date") == profile.listing_date.isoformat()
            ]
        if len(rows) != 1:
            raise ValueError("profile does not resolve to exactly one official IPO case")
        return rows[0]

    def _artifact(self, row: dict[str, str]) -> dict[str, object]:
        path = self.feature_dir / f"{row['case_id']}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        expected = {
            "case_id": row["case_id"],
            "stock_code": row["stock_code_wind"],
            "listing_date": row["official_listed_date"],
            "core_feature_schema_version": IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,
            "core_feature_policy_version": IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
            "core_feature_manifest_hash": IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
        }
        for key, value in expected.items():
            if payload.get(key) != value:
                raise ValueError(f"{key} does not match the frozen PR-B contract")
        expected_split = "development" if int(row["source_year"]) <= 2023 else "validation"
        if payload.get("dataset_split") != expected_split:
            raise ValueError("dataset_split does not match the official cohort")
        provenance = payload.get("source_provenance")
        if not isinstance(provenance, dict):
            raise ValueError("source_provenance is missing")
        if provenance.get("official_bridge_sha256") != _sha256_file(self.official_bridge_path):
            raise ValueError("official bridge provenance hash does not match")
        stored_hash = payload.get("content_hash")
        body = dict(payload)
        body.pop("content_hash", None)
        if stored_hash != content_hash(body):
            raise ValueError("artifact content_hash does not match")
        raw = payload.get("raw_values")
        if not isinstance(raw, dict) or set(raw) != set(IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER):
            raise ValueError("raw feature membership does not match the frozen manifest")
        names, values = vectorize_ipo_market_context(raw)
        if payload.get("feature_names") != list(names) or payload.get("feature_values") != list(values):
            raise ValueError("feature vector is not a lossless projection of raw_values")
        return payload

    @staticmethod
    def _observations(artifact: dict[str, object]) -> tuple[MarketObservation, ...]:
        raw = artifact["raw_values"]
        provenance = artifact["source_provenance"]
        assert isinstance(raw, dict) and isinstance(provenance, dict)
        rows: list[MarketObservation] = []
        for name in IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER:
            value = raw[name]
            if value is None:
                rows.append(MarketObservation(
                    name=name,
                    availability="unavailable",
                    missing_reason="insufficient_governed_prelisting_history",
                    source="pr_b_market_x_core",
                ))
                continue
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"{name} is not finite")
            rows.append(MarketObservation(
                name=name,
                value=numeric,
                unit=_CORE_UNITS[name],
                availability="available",
                derivation="frozen PR-B point-in-time Market-X Core feature",
                source="pr_b_market_x_core",
            ))
        return tuple(rows)


class GatePendingMarketContextProvider:
    """Historical reference implementation; reports the channel as unconfigured."""

    name = "gate_pending"

    def context(self, profile: IPOProfile, market: MarketSnapshot | None = None) -> MarketContextView:
        return MarketContextView(
            status=ChannelStatus.DISABLED,
            reason="market context is not configured in this runtime",
        )


class SnapshotMarketContextProvider:
    """Explains the market snapshot the workflow already loaded, or its absence."""

    name = "snapshot"

    def context(self, profile: IPOProfile, market: MarketSnapshot | None = None) -> MarketContextView:
        if market is None:
            return MarketContextView(
                status=ChannelStatus.UNAVAILABLE_ERROR,
                reason="the market snapshot node did not produce a snapshot",
                provenance={"feature_pipeline": LEGACY_PIPELINE_NOTE},
            )
        metadata = market.metadata or {}
        if market.source == UNAVAILABLE_SOURCE or metadata.get("available") is False:
            return MarketContextView(
                status=ChannelStatus.UNAVAILABLE_ERROR,
                # The provider's own words, not a paraphrase.
                reason=str(metadata.get("reason") or "the market data provider reported no governed snapshot"),
                provenance={"feature_pipeline": LEGACY_PIPELINE_NOTE, "source": market.source},
            )
        if market.source == MOCK_SOURCE:
            return MarketContextView(
                status=ChannelStatus.DISABLED,
                reason="the mock market snapshot is a fixture, not market data",
                provenance={"feature_pipeline": LEGACY_PIPELINE_NOTE, "source": market.source},
            )
        return MarketContextView(
            status=ChannelStatus.AVAILABLE,
            reason=f"derived from the {market.source} pre-listing market snapshot",
            observations=self._observations(market),
            # Deliberately None: a snapshot-derived view did not come from the
            # PR-B Market-X pipeline, and stamping its manifest hash here would
            # claim a lineage this value does not have.
            feature_manifest_hash=None,
            provenance={
                "feature_pipeline": LEGACY_PIPELINE_NOTE,
                "source": market.source,
                "observation_date": market.observation_date.isoformat() if market.observation_date else None,
            },
        )

    @staticmethod
    def _observations(market: MarketSnapshot) -> tuple[MarketObservation, ...]:
        rows = []
        for name, (unit, derivation, missing_reason) in _OBSERVATION_SPECS.items():
            value = getattr(market, name, None)
            if value is None:
                rows.append(MarketObservation(
                    name=name, availability="unavailable",
                    missing_reason=missing_reason, source=market.source))
            else:
                rows.append(MarketObservation(
                    name=name, value=float(value), unit=unit, availability="available",
                    derivation=derivation, source=market.source))
        return tuple(rows)
