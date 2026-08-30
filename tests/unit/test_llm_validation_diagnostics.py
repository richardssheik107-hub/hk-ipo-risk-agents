from __future__ import annotations

from datetime import date
from decimal import Decimal
import json

import pytest
from pydantic import BaseModel, ValidationError

from ipo_risk.providers.llm import OpenAIResponsesLLMProvider


class _DateAmountResult(BaseModel):
    event_date: date | None = None
    amount: Decimal | None = None


class _CoreProductResult(BaseModel):
    product_name: str
    is_core_product: bool


def test_validation_diagnostics_classify_input_without_persisting_value() -> None:
    payload = {"event_date": "not disclosed", "amount": "HKD ten million"}
    with pytest.raises(ValidationError) as captured:
        _DateAmountResult.model_validate(payload)

    errors = OpenAIResponsesLLMProvider._safe_validation_errors(
        captured.value, payload
    )

    assert [(item["path"], item["type"], item["input_class"]) for item in errors] == [
        ("event_date", "date_from_datetime_parsing", "string_placeholder"),
        ("amount", "decimal_parsing", "string_other"),
    ]
    serialized = json.dumps(errors, ensure_ascii=False)
    assert "not disclosed" not in serialized
    assert "HKD ten million" not in serialized


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "null"),
        (12.5, "number"),
        ([], "array"),
        ({}, "object"),
        ("", "string_empty"),
        ("UNKNOWN", "string_placeholder"),
        ("31 June 2023", "string_other"),
    ],
)
def test_safe_input_class_is_structural_only(value: object, expected: str) -> None:
    assert OpenAIResponsesLLMProvider._safe_input_class(
        {"field": value}, ("field",)
    ) == expected


def test_litigation_validation_feedback_prescribes_null_without_echoing_values() -> None:
    payload = {"event_date": "during the year", "amount": "about HKD ten million"}
    with pytest.raises(ValidationError) as captured:
        _DateAmountResult.model_validate(payload)

    feedback = OpenAIResponsesLLMProvider._validation_feedback(
        captured.value,
        payload,
        task_name="litigation_compliance_extract",
    )

    assert "amount must be a plain JSON number" in feedback
    assert "use null rather than prose" in feedback
    assert "event_date must be one exact YYYY-MM-DD date" in feedback
    assert "about HKD ten million" not in feedback
    assert "during the year" not in feedback


def test_core_product_validation_feedback_requires_explicit_boolean() -> None:
    payload = {"product_name": "Example product"}
    with pytest.raises(ValidationError) as captured:
        _CoreProductResult.model_validate(payload)

    feedback = OpenAIResponsesLLMProvider._validation_feedback(
        captured.value,
        payload,
        task_name="business_precommercial_core_product_extract",
    )

    assert "is_core_product is required" in feedback
    assert "explicitly identifies the product as a core product" in feedback


def test_litigation_optional_scalar_normalization_is_narrow_and_fail_closed() -> None:
    original = {
        "event_date": "during the year",
        "amount": "HKD 10-20 million",
        "current_status": "pending",
    }

    normalized, fields = (
        OpenAIResponsesLLMProvider._normalize_optional_litigation_scalars(
            "litigation_compliance_extract",
            original,
        )
    )

    assert normalized == {
        "event_date": None,
        "amount": None,
        "current_status": "pending",
    }
    assert fields == ("amount", "event_date")
    assert original["amount"] == "HKD 10-20 million"


def test_litigation_optional_scalar_normalization_preserves_exact_values() -> None:
    original = {"event_date": "2023-06-30", "amount": "12.5"}

    normalized, fields = (
        OpenAIResponsesLLMProvider._normalize_optional_litigation_scalars(
            "litigation_compliance_extract",
            original,
        )
    )

    assert normalized == original
    assert fields == ()


def test_optional_scalar_normalization_does_not_apply_to_other_tasks() -> None:
    original = {"event_date": "during the year", "amount": "unknown"}

    normalized, fields = (
        OpenAIResponsesLLMProvider._normalize_optional_litigation_scalars(
            "shareholder_rights_extract",
            original,
        )
    )

    assert normalized is original
    assert fields == ()
