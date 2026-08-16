from datetime import date
from ipo_risk.market.ipo_market_context_features import build_ipo_market_context

def test_context_excludes_future_ipo_and_not_yet_known_outcome() -> None:
    t=date(2022,3,1)
    rows=[{"listing_date":date(2022,2,15),"industry":"A","funds_raised":10,"target_1d":date(2022,2,16),"return_1d":-.1,"target_5d":t,"return_5d":-.2}, {"listing_date":t,"industry":"A","funds_raised":100,"target_1d":date(2022,3,2),"return_1d":-.9,"target_5d":date(2022,3,8),"return_5d":-.9}]
    got=build_ipo_market_context(listing_date=t,industry="A",prior_ipos=rows)
    assert got["ipo_count_30d"] == 1
    assert got["recent_ipo_break_rate"] == 1
    assert got["recent_ipo_return_5d"] is None
    assert got["same_industry_recent_5d_sample_count"] == 0

def test_context_zero_sample_keeps_null_rate() -> None:
    got=build_ipo_market_context(listing_date=date(2022,1,1),industry="A",prior_ipos=[])
    assert got["same_industry_ipo_count_180d"] == 0
    assert got["same_industry_recent_break_rate"] is None
