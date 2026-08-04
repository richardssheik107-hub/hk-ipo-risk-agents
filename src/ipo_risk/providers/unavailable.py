"""Honest providers for data that is unavailable in the v0.2 real slice."""

from ipo_risk.schemas import IPOProfile, MarketSnapshot


class UnavailableMarketDataProvider:
    def get_snapshot(self, profile: IPOProfile) -> MarketSnapshot:
        """Return an explicit absence marker without fabricated market values."""

        return MarketSnapshot(
            source="unavailable",
            metadata={
                "available": False,
                "reason": "real_market_data_not_integrated_in_v0.2",
            },
        )


class RequestIPODataProvider:
    def get_profile(self, company_name: str, stock_code: str = "") -> IPOProfile:
        """Preserve only IPO identity supplied by the analysis request."""

        return IPOProfile(
            company_name=company_name,
            stock_code=stock_code,
            metadata={"source": "request"},
        )
