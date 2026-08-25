from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from ipo_risk.evaluation.document_intelligence_benchmark import (
    NOT_AVAILABLE,
    ROLE_B_RISK_CODES,
    UNJUDGED,
    audit_annotation_bundles,
    build_real_benchmark_closure,
    load_protocol,
)


FIELDS = [
    "case_id", "stock_code", "company_name", "document_id", "risk_code",
    "applicable", "gold_page", "exact_text", "expected_status",
    "expected_level", "reviewer", "second_reviewer", "review_status", "notes",
]


def _write_csv(path: Path, fields: list[str], rows: list[dict]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _gold_row(
    case_id: str = "ipo_2023_01234",
    risk_code: str = "redemption_rights",
    *,
    stock_code: str = "1234.HK",
    applicable: bool = True,
    review_status: str = "double_reviewed",
    notes: str = "dataset_split=development",
) -> dict[str, str]:
    return {
        "case_id": case_id,
        "stock_code": stock_code,
        "company_name": "Governed issuer",
        "document_id": case_id,
        "risk_code": risk_code,
        "applicable": str(applicable).lower(),
        "gold_page": "8" if applicable else "",
        "exact_text": "bounded human judgement" if applicable else "",
        "expected_status": "verified" if applicable else "rejected",
        "expected_level": "medium" if applicable else "not_applicable",
        "reviewer": "reviewer-a",
        "second_reviewer": "reviewer-b",
        "review_status": review_status,
        "notes": notes,
    }


def _protocol(path: Path, *, authorized: bool = False, opening_count: int = 0) -> Path:
    payload = {
        "protocol_version": "v045_role_b_real_document_benchmark_v1",
        "frozen_before_validation": True,
        "risk_codes": list(ROLE_B_RISK_CODES),
        "llm_execution_policy": {"external_llm_authorized": authorized},
        "validation": {"opening_count": opening_count},
        "blind_2025_outcome_accessed": False,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _manifest(path: Path, case_ids: list[str]) -> Path:
    rows = [
        {
            "case_id": case_id,
            "relative_path": f"2023/{case_id}.pdf",
            "pdf_page_count": "12",
            "dataset_split": "development",
        }
        for case_id in case_ids
    ]
    return _write_csv(
        path,
        ["case_id", "relative_path", "pdf_page_count", "dataset_split"],
        rows,
    )


def _annotation(root: Path, case_id: str = "ipo_2023_01234") -> None:
    target = root / case_id / "pass1"
    target.mkdir(parents=True, exist_ok=True)
    (target / "expert_annotation_v1.json").write_text(
        json.dumps(
            {
                "case_id": case_id,
                "stock_code": "1234.HK",
                "risks": [{"case_id": case_id, "risk_code": "redemption_rights", "applicable": True}],
                "evidence": [
                    {
                        "case_id": case_id,
                        "risk_code": "redemption_rights",
                        "page": 8,
                        "evidence_role": "primary",
                        "source_authority": "legal_disclosure",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _result(
    case_id: str = "ipo_2023_01234",
    *,
    stock_code: str = "1234.HK",
    page: int = 8,
    use_mock: bool = False,
    provider: str = "unavailable",
    llm_status: str = "offline_unavailable",
) -> dict:
    return {
        "stock_code": stock_code,
        "status": "completed",
        "verified_risks": [
            {
                "risk_code": "redemption_rights",
                "evidence": [{"page": page, "relevance_score": 1.0}],
            }
        ],
        "pending_risks": [],
        "rejected_risks": [],
        "agent_logs": [],
        "metadata": {
            "case_id": case_id,
            "configuration": {"use_mock": use_mock},
            "component_modes": {
                "parser": "real",
                "retriever": "real",
                "legal_agent": "real",
                "business_agent": "real",
                "llm_provider": provider,
                "llm_status": llm_status,
            },
        },
    }


def _closure(tmp_path: Path, rows: list[dict], result: dict | None = None, **kwargs):
    golden = _write_csv(tmp_path / "gold.csv", FIELDS, rows)
    manifest = _manifest(tmp_path / "manifest.csv", sorted({row["case_id"] for row in rows}))
    annotation_root = tmp_path / "annotations"
    for case_id in sorted({row["case_id"] for row in rows if not case_id_is_blind(row["case_id"])}):
        _annotation(annotation_root, case_id)
    results = None
    if result is not None:
        results = tmp_path / "results.jsonl"
        results.write_text(json.dumps(result) + "\n", encoding="utf-8")
    return build_real_benchmark_closure(
        protocol_path=_protocol(
            tmp_path / "protocol.json",
            authorized=kwargs.pop("authorized", False),
            opening_count=kwargs.pop("opening_count", 0),
        ),
        golden_path=golden,
        prospectus_manifest_path=manifest,
        data_root=tmp_path / "data",
        annotation_root=annotation_root,
        development_results_path=results,
        **kwargs,
    )


def case_id_is_blind(case_id: str) -> bool:
    return case_id.startswith("ipo_2025_")


def test_protocol_and_governed_gold_schema_load(tmp_path: Path) -> None:
    protocol = load_protocol(_protocol(tmp_path / "protocol.json"))
    assert protocol["frozen_before_validation"] is True
    summary, _, _ = _closure(tmp_path, [_gold_row()])
    assert summary["governed_annotation_bundles"]["valid_bundles"] == 1
    assert summary["development_cases_available"] == 1


def test_non_formally_reviewed_gold_is_filtered(tmp_path: Path) -> None:
    summary, _, _ = _closure(
        tmp_path,
        [_gold_row(review_status="draft")],
    )
    assert summary["development_cases_available"] == 0
    assert summary["risk_micro"]["status"] == NOT_AVAILABLE


def test_missing_runtime_stays_not_available_and_unjudged(tmp_path: Path) -> None:
    summary, _, _ = _closure(tmp_path, [_gold_row()])
    assert summary["result"] == "BLOCKED"
    assert summary["risk_micro"]["status"] == NOT_AVAILABLE
    assert summary["non_annotated_predictions"] == UNJUDGED
    assert summary["offline_cases"] == 0


def test_offline_governed_result_computes_risk_and_evidence(tmp_path: Path) -> None:
    summary, _, evidence = _closure(tmp_path, [_gold_row()], _result())
    assert summary["risk_micro"]["f1"] == 1.0
    assert summary["evidence_end_to_end"]["recall_at_5"] == 1.0
    assert summary["evidence_end_to_end"]["physical_page_correctness"] == 1.0
    assert summary["evidence_end_to_end"]["precision_at_5"] is None
    assert summary["offline_cases"] == 1
    assert summary["runtime_quality"] == {
        "evidence_out_of_scope": 0,
        "schema_invalid_llm_results": 0,
        "needs_review": 0,
        "verifier_rejected": 0,
        "extraction_failed": 0,
        "provider_unavailable": 1,
    }
    assert evidence[0]["recall_at_5"] == 1.0


@pytest.mark.parametrize(
    ("result", "message"),
    [
        (_result(stock_code="9999.HK"), "stock_code mismatch"),
        (_result(use_mock=True), "mock or ungoverned"),
        (_result(page=13), "document bounds"),
    ],
)
def test_invalid_governed_results_fail_closed(
    tmp_path: Path, result: dict, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _closure(tmp_path, [_gold_row()], result)


def test_provider_mode_label_is_required(tmp_path: Path) -> None:
    result = _result()
    result["metadata"]["component_modes"].pop("llm_provider")
    result["metadata"]["component_modes"].pop("llm_status")
    with pytest.raises(ValueError, match="provider mode is not recorded"):
        _closure(tmp_path, [_gold_row()], result)


def test_real_llm_requires_frozen_authorization(tmp_path: Path) -> None:
    result = _result(provider="openai_responses", llm_status="available")
    with pytest.raises(ValueError, match="without frozen authorization"):
        _closure(tmp_path, [_gold_row()], result)
    summary, _, _ = _closure(tmp_path, [_gold_row()], result, authorized=True)
    assert summary["real_llm_cases"] == 1


def test_validation_cannot_open_before_development_completion(tmp_path: Path) -> None:
    validation = tmp_path / "validation.jsonl"
    validation.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="Development is complete"):
        _closure(
            tmp_path,
            [_gold_row()],
            validation_results_path=validation,
            open_validation=True,
        )


def test_validation_single_open_guard(tmp_path: Path) -> None:
    validation = tmp_path / "validation.jsonl"
    validation.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="already consumed"):
        _closure(
            tmp_path,
            [_gold_row()],
            _result(),
            validation_results_path=validation,
            open_validation=True,
            opening_count=1,
        )


def test_2025_blind_is_rejected_before_any_result_access(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="2025 Blind"):
        _closure(tmp_path, [_gold_row(case_id="ipo_2025_01234")])


def test_annotation_audit_returns_no_evidence_text(tmp_path: Path) -> None:
    root = tmp_path / "annotations"
    _annotation(root)
    first = audit_annotation_bundles(["ipo_2023_01234"], annotation_root=root)
    second = audit_annotation_bundles(["ipo_2023_01234"], annotation_root=root)
    assert first == second
    assert "exact_text" not in json.dumps(first)
    assert not list(tmp_path.rglob("*.pdf"))
