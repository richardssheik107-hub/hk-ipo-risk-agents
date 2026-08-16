from ipo_risk.market.ipo_structure_features import build_ipo_structure_values

def test_structure_formulas_and_diagnostics() -> None:
    values, diagnostics = build_ipo_structure_values({"LowOfferPrice": 1, "HighOfferPrice": 2, "IPOPrice": 2.5, "MarketCap": 99, "FundsRaised": 9, "NetProceed": 6, "TotalShareAmt": 4, "NewIssueAmt": 2, "IssueCap": 8, "AdjNTA": 0.5, "BoardLot": 100, "ListedDate": "2020-01-01", "LockUpEndDate": "2020-01-11", "ListingBoardID": "P3401"})
    assert values["offer_range_width"] == 1
    assert values["offer_price_position"] == 1.5
    assert values["net_proceeds_ratio"] == 2 / 3
    assert values["lockup_days"] == 10
    assert values["main_board_flag"] == 1
    assert "offer_price_outside_range" in diagnostics

def test_structure_invalid_denominators_are_missing() -> None:
    values, diagnostics = build_ipo_structure_values({"LowOfferPrice": 0, "HighOfferPrice": 0, "FundsRaised": 0, "IssueCap": 0, "TotalShareAmt": 0, "ListedDate": "2020-01-02", "LockUpEndDate": "2020-01-01"})
    assert values["offer_range_width"] is None
    assert values["net_proceeds_ratio"] is None
    assert values["lockup_days"] is None
    assert "lockup_before_listing" in diagnostics
