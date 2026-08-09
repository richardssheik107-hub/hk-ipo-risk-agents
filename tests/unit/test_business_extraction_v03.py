from __future__ import annotations

import pytest

from ipo_risk.agents.business_extraction import DeterministicBusinessExtractor
from ipo_risk.schemas import Evidence


def extract(text: str, *, section: str = "業務"):
    return DeterministicBusinessExtractor().extract(
        [Evidence(evidence_id="e1", document_id="doc", chunk_id="c1", page=1, section=section, text=text)]
    )


@pytest.mark.parametrize(
    "text",
    [
        "ABC-101（我们的核心产品）处于临床二期，尚未商业化，尚未从产品销售产生任何收入。",
        "ABC-101（我們的核心產品）處於臨床II期，尚未商業化，尚未從產品銷售產生任何收入。",
        "ABC-101 (our core product) is in Phase II, not yet commercialized, with no revenue from sales of products.",
    ],
)
def test_multilingual_precommercial_facts(text: str) -> None:
    result = extract(text)
    assert result.core_product is not None
    assert result.core_product.product_name == "ABC-101"
    assert result.is_not_commercialized is True
    assert result.has_product_revenue is False


@pytest.mark.parametrize(
    ("phrase", "stage"),
    [
        ("preclinical", "preclinical"),
        ("Phase I", "phase_i"),
        ("Phase II", "phase_ii"),
        ("Phase III", "phase_iii"),
        ("NDA submission", "registration"),
        ("marketing approval", "approved"),
        ("commercially launched", "launched"),
    ],
)
def test_development_stages(phrase: str, stage: str) -> None:
    result = extract(f"ABC-101 (our core product) {phrase}.")
    assert result.commercialization is not None
    assert result.commercialization.development_stage == stage


@pytest.mark.parametrize(
    ("phrase", "source"),
    [
        ("licensing revenue", "licensing"),
        ("milestone income", "milestone"),
        ("R&D service revenue", "rd_service"),
        ("collaboration revenue", "collaboration"),
        ("other service revenue", "other_service"),
    ],
)
def test_non_product_revenue_is_classified_not_product_sales(
    phrase: str, source: str
) -> None:
    result = extract(
        f"ABC-101 (our core product) is in Phase III and not yet commercialized. "
        f"The company records {phrase}, but no product sales revenue."
    )
    assert result.has_product_revenue is False
    assert source in result.revenue_source_types


def test_direct_product_revenue_and_launch_are_explicit_negative_facts() -> None:
    result = extract(
        "ABC-101 (our core product) was commercially launched. "
        "Revenue generated from sales of ABC-101 products amounted to RMB 100 million."
    )
    assert result.is_not_commercialized is False
    assert result.has_product_revenue is True


def test_generic_revenue_is_ambiguous() -> None:
    result = extract("ABC-101 (our core product) is in Phase III. The company recorded revenue.")
    assert result.has_product_revenue is None
    assert result.generic_revenue_ambiguous is True


def test_conflicting_product_revenue_is_not_silently_resolved() -> None:
    result = extract(
        "ABC-101 (our core product) is not yet commercialized and no product sales revenue. "
        "Revenue generated from sales of ABC-101 products amounted to RMB 10 million."
    )
    assert result.conflicting_values is True


def test_approved_but_explicitly_not_launched_remains_precommercial() -> None:
    result = extract(
        "ABC-101 (our core product) received marketing approval but is not yet launched, "
        "and no product sales revenue has been generated."
    )
    assert result.is_not_commercialized is True
    assert result.has_product_revenue is False
    assert result.commercialization is not None
    assert result.commercialization.development_stage == "approved"


def test_generic_risk_factor_language_is_not_a_factual_candidate() -> None:
    result = extract(
        "We may fail to commercialize our product and could lose revenue.",
        section="Risk Factors",
    )
    assert result.factual_evidence_ids == []
    assert result.core_product is None
    assert "risk_factor_only" in result.issues
