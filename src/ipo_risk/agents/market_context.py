"""Market context provider for the PR-G Final Supervisor.

Deliberately *not* a ``RiskAgent``.  The market channel is an explanatory input,
not a risk producer; giving it the ``RiskAgent`` shape would let it inject
unverified ``RiskItem`` values into the verified set, which is precisely the
failure mode the governance boundary exists to prevent.
"""

from __future__ import annotations

from ipo_risk.schemas import IPOProfile
from ipo_risk.schemas.final_supervision import ChannelStatus, MarketContextView

PENDING_MARKET_GATE = "PR-B"


class GatePendingMarketContextProvider:
    """Reports market context as unavailable until the Market-X gate lands."""

    name = "gate_pending"

    def context(self, profile: IPOProfile) -> MarketContextView:
        return MarketContextView(
            status=ChannelStatus.PENDING_GATE,
            reason="governed pre-listing Market-X is not built yet",
            blocking_gate=PENDING_MARKET_GATE,
        )
