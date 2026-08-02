from datetime import date
from ipo_risk.schemas import IPOProfile, MarketSnapshot

class MockLLMProvider:
    def complete(self, prompt: str) -> str: return "mock response"
class MockMarketDataProvider:
    def get_snapshot(self, profile: IPOProfile) -> MarketSnapshot:
        return MarketSnapshot(observation_date=profile.listing_date or date.today(), hsi_return_5d=-.04, recent_ipo_break_rate=.42, market_volatility=.31, sentiment_score=35, source="mock")
class MockIPODataProvider:
    def get_profile(self, company_name: str, stock_code: str = "") -> IPOProfile: return IPOProfile(company_name=company_name, stock_code=stock_code, industry="mock")
