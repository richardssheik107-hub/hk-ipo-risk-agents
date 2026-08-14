"""Synthetic-only tests for external expert annotation governance."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ipo_risk.domain.risk_codes import V03_ENABLED_RISK_CODES
from ipo_risk.evaluation.expert_annotation import (
    ExpertAnnotationBundle,
    ExpertRiskAnnotation,
    validate_expert_annotation_payload,
)


IDENTITY = {
    "case_id": "synthetic_case",
    "stock_code": "0000.HK",
    "company_name": "Synthetic Issuer",
    "document_id": "synthetic_document",
}


def _risk(code: str, *, applicable: bool = False) -> dict[str, object]:
    return {
        "annotation_version": "gpt_expert_v1.1",
        **IDENTITY,
        "risk_code": code,
        "applicable": applicable,
        "expected_status": "needs_review" if applicable else "rejected",
        "expected_level": "medium" if applicable else "not_applicable",
        "confidence": 0.8,
        "reasoning": "Synthetic schema fixture only.",
        "calculation_required": False,
        "calculation_method": None,
        "calculation_inputs": None,
        "calculation_result": None,
        "review_outcome": "expert_first_pass",
        "annotator_type": "external_gpt_expert",
    }


def _evidence(code: str, page: int, *, requirement: str = "required", role: str = "primary") -> dict[str, object]:
    return {
        "case_id": IDENTITY["case_id"],
        "risk_code": code,
        "page": page,
        "evidence_role": role,
        "requirement": requirement,
        "source_authority": "financial_information",
        "exact_text": "Synthetic evidence text.",
        "evidence_reason": "Synthetic relationship fixture.",
        "confidence": 0.9,
    }


def _payload() -> dict[str, object]:
    return {
        "annotation_version": "gpt_expert_v1.1",
        **IDENTITY,
        "risks": [_risk(code) for code in sorted(V03_ENABLED_RISK_CODES)],
        "evidence": [],
        "metadata": {"blind_annotation": True, "human_golden_visible_to_annotator": False},
    }


def _make_applicable(payload: dict[str, object], code: str) -> dict[str, object]:
    for risk in payload["risks"]:  # type: ignore[index]
        if risk["risk_code"] == code:
            risk.update(_risk(code, applicable=True))
    return payload


def test_expert_annotation_schema_valid() -> None:
    assert ExpertAnnotationBundle.model_validate(_payload()).case_id == "synthetic_case"


def test_multiple_required_pages_and_alternative_evidence_supported() -> None:
    payload = _make_applicable(_payload(), "cash_runway")
    payload["evidence"] = [
        _evidence("cash_runway", 10),
        _evidence("cash_runway", 11),
        _evidence("cash_runway", 12, requirement="alternative", role="cross_check"),
    ]
    bundle = ExpertAnnotationBundle.model_validate(payload)
    assert len(bundle.evidence) == 3
    assert [item.requirement.value for item in bundle.evidence] == ["required", "required", "alternative"]


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_confidence_validation(confidence: float) -> None:
    payload = _payload()
    payload["risks"][0]["confidence"] = confidence  # type: ignore[index]
    with pytest.raises(ValidationError):
        ExpertAnnotationBundle.model_validate(payload)


def test_invalid_risk_code_rejected() -> None:
    payload = _payload()
    payload["risks"][0]["risk_code"] = "invented_risk"  # type: ignore[index]
    with pytest.raises(ValidationError):
        ExpertAnnotationBundle.model_validate(payload)


def test_page_outside_pdf_range_reported() -> None:
    payload = _make_applicable(_payload(), "continuous_loss")
    payload["evidence"] = [_evidence("continuous_loss", 101)]
    _, issues = validate_expert_annotation_payload(payload, page_count=100)
    assert [issue.code for issue in issues] == ["PAGE_OUT_OF_RANGE"]


def test_applicable_rejected_is_inconsistent() -> None:
    payload = _make_applicable(_payload(), "continuous_loss")
    payload["risks"][1]["expected_status"] = "rejected"  # type: ignore[index]
    with pytest.raises(ValidationError):
        ExpertAnnotationBundle.model_validate(payload)


def test_non_applicable_requires_rejected_and_not_applicable_level() -> None:
    payload = _payload()
    payload["risks"][0]["expected_status"] = "verified"  # type: ignore[index]
    payload["risks"][0]["expected_level"] = "low"  # type: ignore[index]
    with pytest.raises(ValidationError):
        ExpertAnnotationBundle.model_validate(payload)


@pytest.mark.parametrize(
    ("applicable", "status", "level", "valid"),
    [
        (False, "rejected", "not_applicable", True),
        (False, "rejected", None, False),
        (True, "verified", "high", True),
        (True, "verified", None, False),
        (True, "needs_review", None, True),
        (True, "needs_review", "medium", True),
        (True, "needs_review", "not_applicable", False),
        (True, "rejected", "medium", False),
    ],
)
def test_expected_level_state_matrix(
    applicable: bool,
    status: str,
    level: str | None,
    valid: bool,
) -> None:
    risk = _risk("continuous_loss", applicable=applicable)
    risk["expected_status"] = status
    risk["expected_level"] = level
    if valid:
        assert ExpertRiskAnnotation.model_validate(risk).expected_level == level
    else:
        with pytest.raises(ValidationError):
            ExpertRiskAnnotation.model_validate(risk)


@pytest.mark.parametrize("risk_code", ["customer_concentration", "precommercial_product"])
def test_open_policy_needs_review_accepts_unresolved_level(risk_code: str) -> None:
    risk = _risk(risk_code, applicable=True)
    risk["expected_level"] = None
    assert ExpertRiskAnnotation.model_validate(risk).expected_level is None


@pytest.mark.parametrize(
    ("case_id", "page_count"),
    [
        ("ipo_2020_00368", 420),
        ("ipo_2020_01167", 520),
        ("ipo_2020_01408", 503),
        ("ipo_2020_01961", 598),
    ],
)
def test_preserved_real_pass1_bundles_validate(case_id: str, page_count: int) -> None:
    path = Path("expert_results") / case_id / "pass1" / "expert_annotation_v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    bundle, issues = validate_expert_annotation_payload(payload, page_count=page_count)
    assert bundle is not None
    assert issues == []


def test_financial_calculation_conflict_reported_without_mutation() -> None:
    payload = _make_applicable(_payload(), "cash_runway")
    payload["evidence"] = [_evidence("cash_runway", 10), _evidence("cash_runway", 11)]
    for risk in payload["risks"]:  # type: ignore[index]
        if risk["risk_code"] == "cash_runway":
            risk.update({
                "calculation_required": True,
                "calculation_method": "cash / monthly_cash_burn",
                "calculation_inputs": {"cash": 120.0, "monthly_cash_burn": 20.0},
                "calculation_result": {"months": 5.0},
            })
    original = deepcopy(payload)
    _, issues = validate_expert_annotation_payload(payload, page_count=100)
    assert any(issue.code == "CALCULATION_CONFLICT" for issue in issues)
    assert payload == original
