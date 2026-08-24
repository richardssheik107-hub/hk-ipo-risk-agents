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
