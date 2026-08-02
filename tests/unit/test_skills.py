from ipo_risk.skills.financial import cash_runway, concentration_ratio

def test_financial_skills():
    assert cash_runway(120, 10).value == 12
    assert concentration_ratio(25, 100).value == .25
    assert not cash_runway(100, 0).success
