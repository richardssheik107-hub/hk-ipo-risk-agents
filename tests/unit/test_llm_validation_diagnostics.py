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
