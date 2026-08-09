from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import pytest

from ipo_risk.agents.financial_verifier import V03FinancialVerifier
from ipo_risk.domain.cash_runway import CashRunwayRiskBuilder
from ipo_risk.extraction import ExtractionStatus, FinancialExtractionResult, FinancialMetricValue
from ipo_risk.schemas import (
    Calculation,
    Evidence,
    EvidenceSourceType,
    RiskCategory,
    RiskItem,
    RiskLevel,
    VerificationResult,
    VerificationStatus,
)


def evidence(evidence_id: str, text: str, *, document_id: str = "doc") -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        document_id=document_id,
        chunk_id=f"chunk-{evidence_id}",
        page=int("".join(char for char in evidence_id if char.isdigit()) or "1"),
        text=text,
    )


def continuous_loss_risk(count: int = 2) -> RiskItem:
    items = []
    embedded = []
    for index in range(count):
        evidence_id = f"loss-{index + 1}"
        value = Decimal(str(-(index + 1) * 100))
        period_end = date(2021 + index, 12, 31)
        items.append(
            {
                "period_end": period_end.isoformat(),
                "period_months": 12,
                "net_result": str(value),
                "currency": "CNY",
                "source_unit": "thousand",
                "evidence_ids": [evidence_id],
            }
        )
        embedded.append(evidence(evidence_id, f"年内亏损 ({abs(value):.0f})"))
    level = RiskLevel.HIGH if count >= 3 else RiskLevel.MEDIUM
    return RiskItem(
        risk_id=f"loss-risk-{count}",
        risk_code="continuous_loss",
        category=RiskCategory.FINANCIAL,
        risk_type="Continuous losses",
        level=level,
        score=80 if level == RiskLevel.HIGH else 60,
        conclusion=f"The latest sequence contains {count} consecutive loss periods.",
        evidence=embedded,
        calculation=Calculation(
            skill_name="continuous_loss",
            skill_version="1.0",
            inputs={"observations": items},
            formula="count latest consecutive comparable net_result values below zero",
            result=count,
            unit="periods",
            evidence_ids=[item.evidence_id for item in embedded],
        ),
        agent_name="financial",
        metadata={
            "rule_version": "v03_contract_v1",
            "score_is_rule_based": True,
            "score_is_probability": False,
            "latest_loss_period_count": count,
            "period_months": 12,
            "periods": [item["period_end"] for item in items],
        },
    )


def revenue_risk(
    previous: str = "5067",
    current: str = "538",
    *,
    level: RiskLevel | None = None,
) -> RiskItem:
    exact = (Decimal(current) - Decimal(previous)) / Decimal(previous) * Decimal("100")
    rounded = exact.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    expected_level = level or (RiskLevel.HIGH if exact <= -20 else RiskLevel.MEDIUM)
    embedded = [
        evidence("revenue-1", f"收入 {Decimal(previous):,.0f}"),
        evidence("revenue-2", f"Revenue {Decimal(current):,.0f}"),
    ]
    return RiskItem(
        risk_id=f"revenue-risk-{previous}-{current}",
        risk_code="revenue_growth",
        category=RiskCategory.FINANCIAL,
        risk_type="Revenue decline",
        level=expected_level,
        score=80 if expected_level == RiskLevel.HIGH else 60,
        conclusion=f"Revenue changed by {rounded}% between comparable periods.",
        evidence=embedded,
        calculation=Calculation(
            skill_name="revenue_growth",
            skill_version="1.0",
            inputs={
                "previous_revenue": previous,
                "current_revenue": current,
                "previous_period_end": "2022-12-31",
                "current_period_end": "2023-12-31",
                "period_months": 12,
                "currency": "CNY",
                "source_unit": "thousand",
            },
            formula="(current_revenue - previous_revenue) / previous_revenue * 100",
            result=str(exact),
            unit="percent",
            evidence_ids=[item.evidence_id for item in embedded],
        ),
        agent_name="financial",
        metadata={
            "rule_version": "v03_contract_v1",
            "score_is_rule_based": True,
            "score_is_probability": False,
            "growth_pct_exact": str(exact),
            "growth_pct_rounded": str(rounded),
            "period_months": 12,
            "previous_period_end": "2022-12-31",
            "current_period_end": "2023-12-31",
            "currency": "CNY",
            "source_unit": "thousand",
        },
    )


def concentration_risk(
    concentration_type: str = "customer",
    largest: str = "37.5",
    top_five: str = "68.0",
    *,
    level: RiskLevel | None = None,
) -> RiskItem:
    expected_level = level or (
        RiskLevel.HIGH
        if Decimal(largest) >= 50 or Decimal(top_five) >= 80
        else RiskLevel.MEDIUM
    )
    risk_code = f"{concentration_type}_concentration"
    item = evidence(
        f"{concentration_type}-1",
        f"largest {concentration_type} {largest}%; top five {top_five}%",
    )
    return RiskItem(
        risk_id=f"{risk_code}-{largest}-{top_five}",
        risk_code=risk_code,
        category=RiskCategory.FINANCIAL,
        risk_type=f"{concentration_type.title()} concentration",
        level=expected_level,
        score=80 if expected_level == RiskLevel.HIGH else 60,
        conclusion=(
            f"For the 12-month period, the largest {concentration_type} represented "
            f"{largest}% and the top five represented {top_five}%."
        ),
        evidence=[item],
        calculation=Calculation(
            skill_name=risk_code,
            skill_version="1.0",
            inputs={
                "concentration_type": concentration_type,
                "largest_counterparty_pct": largest,
                "top_five_pct": top_five,
                "period_end": "2023-12-31",
                "period_months": 12,
            },
            formula="use disclosed percentage points without rescaling",
            result=f"largest={largest};top_five={top_five}",
            unit="percent",
            evidence_ids=[item.evidence_id],
        ),
        agent_name="financial",
        metadata={
            "rule_version": "v03_contract_v1",
            "score_is_rule_based": True,
            "score_is_probability": False,
            "concentration_type": concentration_type,
            "largest_counterparty_pct": largest,
            "top_five_pct": top_five,
            "period_end": "2023-12-31",
            "period_months": 12,
        },
    )


def cash_runway_risk() -> RiskItem:
    cash = evidence("cash-1", "Cash and cash equivalents 77,208")
    flow = evidence("cash-2", "Operating cash flow (83,918)")
    extraction = FinancialExtractionResult(
        cash_and_cash_equivalents=FinancialMetricValue(
            metric_name="cash_and_cash_equivalents",
            normalized_value=Decimal("77208"),
            currency="CNY",
            unit="thousand",
            period_end=date(2024, 3, 31),
            evidence_id=cash.evidence_id,
            document_id="doc",
            chunk_id=cash.chunk_id,
            page=cash.page,
            status=ExtractionStatus.EXTRACTED,
        ),
        operating_cash_flow=FinancialMetricValue(
            metric_name="operating_cash_flow",
            normalized_value=Decimal("-83918"),
            currency="CNY",
            unit="thousand",
            period_end=date(2024, 3, 31),
            period_months=3,
            evidence_id=flow.evidence_id,
            document_id="doc",
            chunk_id=flow.chunk_id,
            page=flow.page,
            status=ExtractionStatus.EXTRACTED,
        ),
    )
    built = CashRunwayRiskBuilder().build(
        extraction, {cash.evidence_id: cash, flow.evidence_id: flow}
    )
    assert built.risk_item is not None
    return built.risk_item.model_copy(
        update={"metadata": {**built.risk_item.metadata, "rule_version": "v03_contract_v1"}}
    )


def only_result(result: VerificationResult) -> RiskItem:
    items = result.verified_risks + result.pending_risks + result.rejected_risks
    assert len(items) == 1
    return items[0]


@pytest.mark.parametrize(
    "risk_factory",
    [cash_runway_risk, continuous_loss_risk, revenue_risk, concentration_risk,
     lambda: concentration_risk("supplier", "22.6", "68.0")],
)
def test_all_five_valid_financial_risks_are_verified(risk_factory) -> None:
    risk = risk_factory()
    result = V03FinancialVerifier().verify([risk], {})
    assert result.verified_risks[0].risk_id == risk.risk_id
    assert result.verified_risks[0].verification_status == VerificationStatus.VERIFIED
    assert "independently recalculated" in result.verified_risks[0].verification_notes
    assert result.pending_risks == []
    assert result.rejected_risks == []


def test_protocol_returns_three_lists_and_preserves_input_order_and_ids() -> None:
    risks = [continuous_loss_risk(), revenue_risk(), concentration_risk()]
    result = V03FinancialVerifier().verify(risks, {})
    assert V03FinancialVerifier.name == "verifier"
    assert isinstance(result, VerificationResult)
    assert [item.risk_id for item in result.verified_risks] == [
        item.risk_id for item in risks
    ]
    assert result.pending_risks == []
    assert result.rejected_risks == []


def test_non_financial_risk_is_not_verified_or_rejected() -> None:
    risk = concentration_risk().model_copy(
        update={
            "risk_code": "redemption_rights",
            "category": RiskCategory.LEGAL,
            "agent_name": "legal",
        }
    )
    result = V03FinancialVerifier().verify([risk], {})
    assert not result.verified_risks and not result.rejected_risks
    assert result.pending_risks[0].verification_status == VerificationStatus.PENDING
    assert "outside" in result.pending_risks[0].verification_notes


def test_empty_embedded_evidence_stays_pending() -> None:
    risk = revenue_risk().model_copy(update={"evidence": []})
    reviewed = only_result(V03FinancialVerifier().verify([risk], {}))
    assert reviewed.verification_status == VerificationStatus.PENDING


def test_missing_external_reference_stays_pending() -> None:
    risk = revenue_risk()
    unrelated = evidence("other-9", "unrelated")
    reviewed = only_result(
        V03FinancialVerifier().verify([risk], {risk.risk_code: [unrelated]})
    )
    assert reviewed.verification_status == VerificationStatus.PENDING


def test_complete_embedded_evidence_is_sufficient_when_external_mapping_is_empty() -> None:
    assert V03FinancialVerifier().verify([revenue_risk()], {}).verified_risks


@pytest.mark.parametrize(
    "mutator",
    [
        lambda risk: risk.model_copy(update={"calculation": None}),
        lambda risk: risk.model_copy(
            update={
                "calculation": risk.calculation.model_copy(update={"inputs": {}})
            }
        ),
        lambda risk: risk.model_copy(
            update={
                "calculation": risk.calculation.model_copy(
                    update={
                        "inputs": {**risk.calculation.inputs, "currency": ""}
                    }
                )
            }
        ),
        lambda risk: risk.model_copy(
            update={
                "calculation": risk.calculation.model_copy(
                    update={
                        "inputs": {**risk.calculation.inputs, "source_unit": ""}
                    }
                )
            }
        ),
        lambda risk: risk.model_copy(
            update={
                "calculation": risk.calculation.model_copy(
                    update={
                        "inputs": {**risk.calculation.inputs, "period_months": None}
                    }
                )
            }
        ),
        lambda risk: risk.model_copy(
            update={"metadata": {**risk.metadata, "issues": ["conflicting_values"]}}
        ),
        lambda risk: risk.model_copy(
            update={"metadata": {**risk.metadata, "issues": ["unsupported_layout"]}}
        ),
    ],
)
def test_missing_or_ambiguous_information_needs_review(mutator) -> None:
    risk = mutator(revenue_risk())
    reviewed = only_result(V03FinancialVerifier().verify([risk], {}))
    assert reviewed.verification_status == VerificationStatus.NEEDS_REVIEW


def test_input_needs_review_is_not_promoted_even_if_calculation_is_valid() -> None:
    risk = revenue_risk().model_copy(
        update={"verification_status": VerificationStatus.NEEDS_REVIEW}
    )
    reviewed = only_result(V03FinancialVerifier().verify([risk], {}))
    assert reviewed.verification_status == VerificationStatus.NEEDS_REVIEW


def test_failed_calculation_needs_review_instead_of_rejection() -> None:
    risk = revenue_risk()
    changed = risk.model_copy(
        update={
            "calculation": risk.calculation.model_copy(
                update={"success": False, "error": "upstream_failure"}
            )
        }
    )
    reviewed = only_result(V03FinancialVerifier().verify([changed], {}))
    assert reviewed.verification_status == VerificationStatus.NEEDS_REVIEW


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("agent_name", "legal"),
        ("category", RiskCategory.LEGAL),
        ("level", RiskLevel.MEDIUM),
        ("score", 60),
    ],
)
def test_tampered_identity_level_or_score_is_rejected(field: str, value: object) -> None:
    reviewed = only_result(
        V03FinancialVerifier().verify([revenue_risk().model_copy(update={field: value})], {})
    )
    assert reviewed.verification_status == VerificationStatus.REJECTED


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("skill_name", "wrong"),
        ("skill_version", "9.9"),
        ("formula", "wrong formula"),
        ("unit", "ratio"),
        ("result", "-1"),
    ],
)
def test_tampered_calculation_contract_or_result_is_rejected(
    field: str, value: object
) -> None:
    risk = revenue_risk()
    changed = risk.model_copy(
        update={"calculation": risk.calculation.model_copy(update={field: value})}
    )
    reviewed = only_result(V03FinancialVerifier().verify([changed], {}))
    assert reviewed.verification_status == VerificationStatus.REJECTED


def test_calculation_cannot_reference_evidence_outside_risk() -> None:
    risk = revenue_risk()
    changed = risk.model_copy(
        update={
            "calculation": risk.calculation.model_copy(
                update={"evidence_ids": [*risk.calculation.evidence_ids, "foreign"]}
            )
        }
    )
    assert only_result(V03FinancialVerifier().verify([changed], {})).verification_status == VerificationStatus.REJECTED


def test_external_evidence_identity_and_text_are_checked() -> None:
    risk = revenue_risk()
    conflict = risk.evidence[0].model_copy(update={"page": 99})
    result = V03FinancialVerifier().verify(
        [risk], {risk.risk_code: [conflict, risk.evidence[1]]}
    )
    assert result.rejected_risks[0].verification_status == VerificationStatus.REJECTED


def test_external_evidence_text_mismatch_is_rejected() -> None:
    risk = revenue_risk()
    conflict = risk.evidence[0].model_copy(update={"text": "Revenue 1"})
    result = V03FinancialVerifier().verify(
        [risk], {risk.risk_code: [conflict, risk.evidence[1]]}
    )
    assert result.rejected_risks[0].verification_status == VerificationStatus.REJECTED


def test_cross_document_evidence_is_rejected() -> None:
    risk = revenue_risk()
    changed = risk.evidence[1].model_copy(update={"document_id": "other-doc"})
    risk = risk.model_copy(update={"evidence": [risk.evidence[0], changed]})
    assert V03FinancialVerifier().verify([risk], {}).rejected_risks


def test_non_prospectus_evidence_is_rejected() -> None:
    risk = revenue_risk()
    changed = risk.evidence[0].model_copy(
        update={"source_type": EvidenceSourceType.MARKET_DATA}
    )
    risk = risk.model_copy(update={"evidence": [changed, risk.evidence[1]]})
    assert V03FinancialVerifier().verify([risk], {}).rejected_risks


def test_evidence_without_supporting_values_needs_review() -> None:
    risk = revenue_risk()
    changed = [item.model_copy(update={"text": "ambiguous prose"}) for item in risk.evidence]
    reviewed = only_result(
        V03FinancialVerifier().verify([risk.model_copy(update={"evidence": changed})], {})
    )
    assert reviewed.verification_status == VerificationStatus.NEEDS_REVIEW


def test_prohibited_certain_conclusion_needs_review() -> None:
    risk = revenue_risk().model_copy(update={"conclusion": "收入下降，股价必然下跌"})
    reviewed = only_result(V03FinancialVerifier().verify([risk], {}))
    assert reviewed.verification_status == VerificationStatus.NEEDS_REVIEW


def test_skill_exception_is_diagnostic_needs_review() -> None:
    def explode(previous, current):
        raise RuntimeError("sensitive detail is not returned")

    reviewed = only_result(
        V03FinancialVerifier(revenue_growth_skill=explode).verify([revenue_risk()], {})
    )
    assert reviewed.verification_status == VerificationStatus.NEEDS_REVIEW
    assert "RuntimeError" in reviewed.verification_notes
    assert "sensitive detail" not in reviewed.verification_notes


@pytest.mark.parametrize(
    "metadata_update",
    [
        {"rule_version": "wrong"},
        {"score_is_rule_based": False},
        {"score_is_probability": True},
    ],
)
def test_tampered_rule_metadata_is_rejected(metadata_update: dict[str, object]) -> None:
    risk = revenue_risk()
    risk = risk.model_copy(update={"metadata": {**risk.metadata, **metadata_update}})
    assert V03FinancialVerifier().verify([risk], {}).rejected_risks


def test_customer_supplier_type_swap_is_rejected() -> None:
    risk = concentration_risk("supplier", "30", "40")
    changed_inputs = {**risk.calculation.inputs, "concentration_type": "customer"}
    risk = risk.model_copy(
        update={
            "calculation": risk.calculation.model_copy(update={"inputs": changed_inputs})
        }
    )
    assert V03FinancialVerifier().verify([risk], {}).rejected_risks


@pytest.mark.parametrize(
    "risk",
    [
        revenue_risk("100", "100", level=RiskLevel.MEDIUM),
        revenue_risk("100", "120", level=RiskLevel.MEDIUM),
        concentration_risk("customer", "29.9", "59.9", level=RiskLevel.MEDIUM),
        concentration_risk("supplier", "29.9", "59.9", level=RiskLevel.MEDIUM),
    ],
)
def test_below_threshold_or_positive_growth_risk_is_rejected(risk: RiskItem) -> None:
    assert V03FinancialVerifier().verify([risk], {}).rejected_risks


@pytest.mark.parametrize(
    "risk",
    [
        continuous_loss_risk(2),
        continuous_loss_risk(3),
        revenue_risk("100", "80"),
        revenue_risk("10000", "9999"),
        concentration_risk("customer", "30", "40"),
        concentration_risk("customer", "50", "50"),
        concentration_risk("customer", "20", "60"),
        concentration_risk("customer", "20", "80"),
        concentration_risk("supplier", "30", "40"),
        concentration_risk("supplier", "50", "50"),
        concentration_risk("supplier", "20", "60"),
        concentration_risk("supplier", "20", "80"),
    ],
)
def test_frozen_boundaries_verify(risk: RiskItem) -> None:
    assert V03FinancialVerifier().verify([risk], {}).verified_risks


def test_verification_is_deterministic_and_does_not_mutate_input() -> None:
    risk = revenue_risk()
    before = risk.model_dump()
    verifier = V03FinancialVerifier()
    first = verifier.verify([risk], {})
    second = verifier.verify([risk], {})
    assert first == second
    assert risk.model_dump() == before


def test_cash_runway_preserves_existing_needs_review_semantics() -> None:
    risk = cash_runway_risk()
    changed = risk.model_copy(
        update={
            "calculation": risk.calculation.model_copy(update={"result": "9.99"})
        }
    )
    result = V03FinancialVerifier().verify([changed], {})
    assert not result.rejected_risks
    assert result.pending_risks[0].verification_status == VerificationStatus.NEEDS_REVIEW
