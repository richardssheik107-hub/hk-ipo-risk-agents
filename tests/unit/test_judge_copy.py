from judge_copy import highest_risk_level, risk_reasoning, risk_review_focus, summarize_risks


def test_known_risk_copy_is_business_facing() -> None:
    assert "客户" in risk_reasoning("customer_concentration")
    assert "合同" in risk_review_focus("customer_concentration")


def test_unknown_risk_copy_fails_safe_to_generic_explanation() -> None:
    assert "受治理" in risk_reasoning("future_unknown_risk")
    assert "复核" in risk_review_focus("future_unknown_risk")


def test_summary_is_presentation_only_counting() -> None:
    risks = [
        {"level": "high", "verification_status": "verified", "evidence": [{}, {}]},
        {"level": "medium", "verification_status": "needs_review", "evidence": [{}]},
    ]
    assert summarize_risks(risks) == {
        "total": 2,
        "high_or_critical": 1,
        "medium": 1,
        "verified": 1,
        "needs_review": 1,
        "evidence_count": 3,
        "highest_level": "high",
    }
    assert highest_risk_level(risks) == "high"
