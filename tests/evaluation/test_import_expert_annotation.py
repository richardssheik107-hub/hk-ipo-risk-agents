"""Contract tests for immutable, per-Case expert result imports."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from ipo_risk.domain.risk_codes import V03_ENABLED_RISK_CODES


def _load_importer():
    path = Path("scripts/import_expert_annotation.py")
    spec = importlib.util.spec_from_file_location("import_expert_annotation", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _payload() -> dict[str, object]:
    identity = {
        "case_id": "case_alpha",
        "stock_code": "1234.HK",
        "company_name": "示例公司",
        "document_id": "document_alpha",
    }
    return {
        "annotation_version": "gpt_expert_v1.1",
        **identity,
        "risks": [
            {
                "annotation_version": "gpt_expert_v1.1",
                **identity,
                "risk_code": risk_code,
                "applicable": False,
                "expected_status": "rejected",
                "expected_level": "not_applicable",
                "confidence": 0.8,
                "reasoning": "No applicable evidence was found in this test Case.",
                "calculation_required": False,
                "calculation_method": None,
                "calculation_inputs": None,
                "calculation_result": None,
                "review_outcome": "expert_first_pass",
                "annotator_type": "external_gpt_expert",
            }
            for risk_code in V03_ENABLED_RISK_CODES
        ],
        "evidence": [],
        "metadata": {
            "blind_annotation": True,
            "human_golden_visible_to_annotator": False,
        },
    }


def test_import_preserves_raw_output_and_writes_validation_separately(tmp_path: Path) -> None:
    importer = _load_importer()
    annotation = tmp_path / "gpt-output.json"
    raw_text = json.dumps(_payload(), ensure_ascii=False, indent=4) + "\n"
    annotation.write_text(raw_text, encoding="utf-8")
    inventory = tmp_path / "inventory.json"
    inventory.write_text(json.dumps({"cases": [{
        "case_id": "case_alpha",
        "stock_code": "1234.HK",
        "company_name": "示例公司",
        "document_id": "document_alpha",
        "page_count": 10,
    }]}, ensure_ascii=False), encoding="utf-8")

    output = tmp_path / "expert_results"
    destination, validation_path, valid = importer.import_annotation(
        annotation,
        inventory_path=inventory,
        output_dir=output,
        stage="pass1",
    )

    assert valid is True
    assert destination == output / "case_alpha" / "pass1" / "expert_annotation_v1.json"
    assert destination.read_text(encoding="utf-8") == raw_text
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    assert validation == {
        "case_id": "case_alpha",
        "stage": "pass1",
        "source_annotation": "expert_annotation_v1.json",
        "valid": True,
        "issues": [],
    }


def test_import_refuses_to_overwrite_an_existing_pass(tmp_path: Path) -> None:
    importer = _load_importer()
    annotation = tmp_path / "gpt-output.json"
    annotation.write_text(json.dumps(_payload(), ensure_ascii=False), encoding="utf-8")
    inventory = tmp_path / "inventory.json"
    inventory.write_text(json.dumps({"cases": [{
        "case_id": "case_alpha",
        "stock_code": "1234.HK",
        "company_name": "示例公司",
        "document_id": "document_alpha",
        "page_count": 10,
    }]}, ensure_ascii=False), encoding="utf-8")
    output = tmp_path / "expert_results"
    importer.import_annotation(annotation, inventory_path=inventory, output_dir=output, stage="pass1")

    try:
        importer.import_annotation(annotation, inventory_path=inventory, output_dir=output, stage="pass1")
    except FileExistsError as exc:
        assert "refusing to overwrite" in str(exc)
    else:
        raise AssertionError("an existing pass must never be overwritten")
