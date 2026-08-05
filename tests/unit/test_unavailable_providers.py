from ipo_risk.providers.unavailable import (
    RequestIPODataProvider,
    UnavailableMarketDataProvider,
)
from ipo_risk.schemas import IPOProfile


def test_unavailable_market_provider_has_no_fabricated_features() -> None:
    snapshot = UnavailableMarketDataProvider().get_snapshot(
        IPOProfile(company_name="Demo")
    )
    assert snapshot.source == "unavailable"
    assert snapshot.sentiment_score is None
    assert snapshot.hsi_return_5d is None
    assert snapshot.recent_ipo_break_rate is None
    assert snapshot.metadata == {
        "available": False,
        "reason": "real_market_data_not_integrated_in_v0.2",
    }


def test_request_ipo_provider_preserves_only_request_identity() -> None:
    profile = RequestIPODataProvider().get_profile("同源康", "2410.HK")
    assert profile.company_name == "同源康"
    assert profile.stock_code == "2410.HK"
    assert profile.industry == ""
    assert profile.issue_price is None
    assert profile.issue_size is None
    assert profile.metadata == {"source": "request"}
