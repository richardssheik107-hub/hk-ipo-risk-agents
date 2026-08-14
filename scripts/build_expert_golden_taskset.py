"""Build the frozen Expert Golden 100 collaboration taskset from catalog metadata."""

from __future__ import annotations

import csv
import json
from pathlib import Path

TASKSET_VERSION = "expert_golden_100_v1"
PROTOCOL_VERSION = "gpt_expert_v1.1"
ROOT = Path("docs/annotation/gpt_expert_v1_1")
ACTIVE_RISK_ORDER = (
    "cash_runway",
    "continuous_loss",
    "revenue_growth",
    "customer_concentration",
    "supplier_concentration",
    "redemption_rights",
    "material_litigation_compliance",
    "precommercial_product",
)
YEARLY_CODES = {
    2020: "0368 1167 1408 1942 1961 2057 2135 2263 2599 3347 6063 6618 6688 6900 6968 8489 9600 9633 9901 9986".split(),
    2021: "0013 0606 1024 1413 1927 2015 2137 2160 2190 2215 2235 2518 3658 6601 6628 6668 6821 9626 9898 9982".split(),
    2022: "0314 0816 1204 1406 1880 2121 2145 2179 2237 2372 2407 2450 2602 6610 6698 6922 9638 9863 9886 9985".split(),
    2023: "0666 1111 1274 1405 1541 1973 2105 2268 2405 2451 2473 2486 2501 2503 2511 2517 2521 6682 9690 9930".split(),
    2024: "0300 0805 0999 1318 1471 2228 2410 2431 2460 2495 2506 2519 2533 2550 2567 2585 2613 6657 6936 9639".split(),
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _expected_split(year: int, stock_code: str) -> str:
    if year < 2024:
        return "development"
    return "development_exception" if stock_code == "2410.HK" else "validation"


def _blank(row: dict[str, object]) -> dict[str, object]:
    identity = {
        "case_id": row["case_id"],
        "stock_code": row["stock_code"],
        "company_name": row["company_name"],
        "document_id": row["case_id"],
    }
    return {
        "annotation_version": PROTOCOL_VERSION,
        **identity,
        "risks": [{
            "annotation_version": PROTOCOL_VERSION,
            **identity,
            "risk_code": risk_code,
            "applicable": None,
            "expected_status": None,
            "expected_level": None,
            "confidence": None,
            "reasoning": None,
            "calculation_required": None,
            "calculation_method": None,
            "calculation_inputs": None,
            "calculation_result": None,
            "review_outcome": "expert_first_pass",
            "annotator_type": "external_gpt_expert",
        } for risk_code in ACTIVE_RISK_ORDER],
        "evidence": [],
        "metadata": {
            "blind_annotation": True,
            "human_golden_visible_to_annotator": False,
            "output_contract": "ExpertAnnotationBundle",
            "confidence_constraint": "risk and evidence confidence must be numbers in inclusive range 0.0 to 1.0",
            "evidence_object_schema": {
                "case_id": "non-empty string; must equal bundle case_id",
                "risk_code": "one of the eight active risk codes assessed in risks[]",
                "page": "integer >= 1; physical PDF page number",
                "evidence_role": ["primary", "supporting", "context", "cross_check"],
                "requirement": ["required", "alternative", "supporting_only"],
                "source_authority": [
                    "audited_financial_statement", "accountants_report",
                    "financial_information", "business_section", "legal_disclosure",
                    "corporate_structure", "pre_ipo_investment", "summary",
                    "risk_factors", "other",
                ],
                "exact_text": "non-empty verbatim text copied from the prospectus",
                "evidence_reason": "non-empty explanation of how the text supports the risk assessment",
                "confidence": "number from 0.0 to 1.0 inclusive",
            },
        },
    }


def _case_readme(row: dict[str, object]) -> str:
    return f"""# Expert Golden Blind Case Packet

- Task index: `{row['task_index']}`
- Taskset: `{TASKSET_VERSION}`
- Case ID: `{row['case_id']}`
- Stock code: `{row['stock_code']}`
- Company: `{row['company_name']}`
- Source year: `{row['source_year']}`
- Annotation protocol: `{PROTOCOL_VERSION}`

Use the public `GPT_EXPERT_ANNOTATION_PROTOCOL.md`,
`annotation_instructions.md`, `PRIMARY_BLIND_ANNOTATION_PROMPT.md`, and this
directory's `blank_annotation.json`. The annotator must obtain the original PDF
from the authorized local data source and must not receive Human Golden, prior GPT
answers, Retriever/Agent output, audit output, or market outcome labels.
"""


def build_taskset(
    *,
    split_path: Path = Path("data/catalog/dataset_split.csv"),
    manifest_path: Path = Path("data/catalog/ipo_prospectus_manifest.csv"),
    output_root: Path = ROOT,
) -> dict[str, int]:
    """Create deterministic answer-free packets without reading prospectus content."""
    splits = _read_csv(split_path)
    manifests = _read_csv(manifest_path)
    split_by_stock: dict[str, list[dict[str, str]]] = {}
    manifest_by_stock: dict[str, list[dict[str, str]]] = {}
    for row in splits:
        split_by_stock.setdefault(row["stock_code_wind"], []).append(row)
    for row in manifests:
        manifest_by_stock.setdefault(row["stock_code_wind"], []).append(row)

    selected: list[dict[str, object]] = []
    for task_index, (year, raw_code) in enumerate(
        ((year, code) for year, codes in YEARLY_CODES.items() for code in codes),
        start=1,
    ):
        stock_code = f"{raw_code.zfill(4)}.HK"
        split_rows = split_by_stock.get(stock_code, [])
        manifest_rows = manifest_by_stock.get(stock_code, [])
        if len(split_rows) != 1 or len(manifest_rows) != 1:
            raise ValueError(
                f"TASKSET_SOURCE_CONFLICT {stock_code}: "
                f"split_matches={len(split_rows)} manifest_matches={len(manifest_rows)}"
            )
        split_row, manifest_row = split_rows[0], manifest_rows[0]
        expected_split = _expected_split(year, stock_code)
        if (
            int(split_row["source_year"]) != year
            or split_row["dataset_split"] != expected_split
            or split_row["is_blind_test"].lower() != "false"
            or manifest_row["case_id"] != split_row["case_id"]
            or manifest_row["dataset_split"] != expected_split
        ):
            raise ValueError(f"TASKSET_SOURCE_CONFLICT {stock_code}: split/year/catalog mismatch")
        if not manifest_row["pdf_page_count"] or not manifest_row["sha256"]:
            raise ValueError(f"TASKSET_SOURCE_CONFLICT {stock_code}: unresolved page count or SHA")
        selected.append({
            "task_index": task_index,
            "taskset_version": TASKSET_VERSION,
            "case_id": manifest_row["case_id"],
            "stock_code": stock_code,
            "company_name": manifest_row["company_short_name"],
            "source_year": year,
            "dataset_split": expected_split,
            "page_count": int(manifest_row["pdf_page_count"]),
            "pdf_sha256": manifest_row["sha256"],
            "packet_path": f"docs/annotation/gpt_expert_v1_1/case_packets/{manifest_row['case_id']}",
            "source_validation_status": "validated_from_catalog_metadata",
        })

    output_root.mkdir(parents=True, exist_ok=True)
    packet_root = output_root / "case_packets"
    packet_root.mkdir(parents=True, exist_ok=True)
    for row in selected:
        case_dir = packet_root / str(row["case_id"])
        case_dir.mkdir(parents=True, exist_ok=True)
        metadata = {
            "taskset_version": TASKSET_VERSION,
            "annotation_protocol_version": PROTOCOL_VERSION,
            "case_id": row["case_id"],
            "stock_code": row["stock_code"],
            "company_name": row["company_name"],
            "document_id": row["case_id"],
            "source_year": row["source_year"],
            "dataset_split": row["dataset_split"],
            "page_count": row["page_count"],
            "pdf_sha256": row["pdf_sha256"],
            "source_validation_status": row["source_validation_status"],
        }
        (case_dir / "case_metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (case_dir / "blank_annotation.json").write_text(
            json.dumps(_blank(row), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (case_dir / "README.md").write_text(_case_readme(row), encoding="utf-8")

    taskset_fields = (
        "task_index", "taskset_version", "case_id", "stock_code", "company_name",
        "source_year", "dataset_split", "packet_path",
    )
    _write_csv(output_root / "expert_golden_100_taskset.csv", taskset_fields, selected)
    source_fields = (
        "taskset_version", "case_id", "stock_code", "company_name", "source_year",
        "dataset_split", "page_count", "pdf_sha256", "packet_path", "source_validation_status",
    )
    _write_csv(output_root / "source_manifest.csv", source_fields, selected)
    assignment_fields = (
        "task_index", "taskset_version", "case_id", "stock_code", "company_name",
        "source_year", "dataset_split", "primary_annotator", "primary_status",
        "second_pass_annotator", "second_pass_status", "adjudication_status",
        "final_status", "notes",
    )
    assignments = [{
        **row,
        "primary_annotator": "",
        "primary_status": "not_started",
        "second_pass_annotator": "",
        "second_pass_status": "not_started",
        "adjudication_status": "not_started",
        "final_status": "not_started",
        "notes": "",
    } for row in selected]
    _write_csv(output_root / "team_case_assignment.csv", assignment_fields, assignments)
    return {
        "cases": len(selected),
        "risk_inspections": len(selected) * len(ACTIVE_RISK_ORDER),
        "development": sum(row["dataset_split"] == "development" for row in selected),
        "validation": sum(row["dataset_split"] == "validation" for row in selected),
        "development_exception": sum(row["dataset_split"] == "development_exception" for row in selected),
    }


def main() -> int:
    print(json.dumps(build_taskset(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
