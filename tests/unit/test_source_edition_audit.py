from ipo_risk.evaluation.source_edition_audit import (
    distinctive_numeric_tokens,
    document_supports_risk_fact,
    page_supports_risk_fact,
)


def test_numeric_tokens_exclude_years_and_small_ordinals() -> None:
    assert distinctive_numeric_tokens("2022 first 5 suppliers 68.3% and 1,234.5") == {
        "68.3%",
        "1234.5",
    }


def test_concentration_fact_requires_terms_and_matching_numbers() -> None:
    anchor = "The five largest suppliers represented 68.3% of purchases."
    assert page_supports_risk_fact(
        "五大供應商佔採購額68.3%。",
        risk_family="supplier_concentration",
        gold_anchor_texts=[anchor],
    )
    assert not page_supports_risk_fact(
        "五大客戶佔收益68.3%。",
        risk_family="supplier_concentration",
        gold_anchor_texts=[anchor],
    )


def test_nonnumeric_redemption_fact_requires_lifecycle_language() -> None:
    assert page_supports_risk_fact(
        "投資者的贖回權將於上市時終止。",
        risk_family="redemption_rights",
        gold_anchor_texts=["The redemption rights will terminate upon listing."],
    )
    assert not page_supports_risk_fact(
        "投資者享有贖回權。",
        risk_family="redemption_rights",
        gold_anchor_texts=["The redemption rights will terminate."],
    )


def test_document_scan_returns_boolean_only() -> None:
    assert document_supports_risk_fact(
        ["unrelated", "最大客戶佔收益50.1%。"],
        risk_family="customer_concentration",
        gold_anchor_texts=["The largest customer accounted for 50.1%."],
    )
