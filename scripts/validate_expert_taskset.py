"""Validate the frozen Expert Golden 100 taskset and blind packet safety."""

from __future__ import annotations

import csv
from collections import Counter
import json
from pathlib import Path

from ipo_risk.domain.risk_codes import V03_ENABLED_RISK_CODES


ROOT = Path("docs/annotation/gpt_expert_v1_1")
TASKSET_VERSION = "expert_golden_100_v1"
ANSWER_FIELDS = (
    "applicable", "expected_status", "expected_level", "confidence", "reasoning",
    "calculation_required", "calculation_method", "calculation_inputs", "calculation_result",
)
FORBIDDEN_KEYS = {
    "gold_page", "gold_exact_text", "review_status", "second_reviewer",
    "source_pdf_path", "agent_output", "retriever_output",
}
WINDOWS_HOME_MARKER = "C:" + "\\" + "Users" + "\\"
UNIX_HOME_MARKER = "/" + "Users" + "/"
EVIDENCE_SCHEMA_FIELDS = {
    "case_id", "risk_code", "page", "evidence_role", "requirement",
    "source_authority", "exact_text", "evidence_reason", "confidence",
}
EVIDENCE_ROLES = ["primary", "supporting", "context", "cross_check"]
EVIDENCE_REQUIREMENTS = ["required", "alternative", "supporting_only"]
SOURCE_AUTHORITIES = [
    "audited_financial_statement", "accountants_report", "financial_information",
    "business_section", "legal_disclosure", "corporate_structure",
    "pre_ipo_investment", "summary", "risk_factors", "other",
]
FORBIDDEN_PACKET_MARKERS = (
    '"gold_page"',
    '"gold_exact_text"',
    '"review_status"',
    '"second_reviewer"',
    "source_pdf_path",
    "v03_golden_case_manifest",
    "PILOT_DIAGNOSTIC_ONLY.json",
    WINDOWS_HOME_MARKER,
    UNIX_HOME_MARKER,
)


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_taskset(root: Path = ROOT) -> dict[str, object]:
    """Raise ValueError on identity, split, blank-state, or contamination failures."""
    taskset = _csv(root / "expert_golden_100_taskset.csv")
    manifest = _csv(root / "source_manifest.csv")
    assignments = _csv(root / "team_case_assignment.csv")
    errors: list[str] = []
    if len(taskset) != 100 or len(manifest) != 100 or len(assignments) != 100:
        errors.append("taskset, source manifest, and assignment must each contain 100 rows")
    case_ids = [row["case_id"] for row in taskset]
    stocks = [row["stock_code"] for row in taskset]
    if len(set(case_ids)) != 100 or len(set(stocks)) != 100:
        errors.append("case_id and stock_code must each be unique")
    if [int(row["task_index"]) for row in taskset] != list(range(1, 101)):
        errors.append("task_index must be exactly 1..100 in frozen order")
    year_counts = Counter(int(row["source_year"]) for row in taskset)
    if year_counts != Counter({2020: 20, 2021: 20, 2022: 20, 2023: 20, 2024: 20}):
        errors.append(f"invalid year distribution: {dict(year_counts)}")
    split_counts = Counter(row["dataset_split"] for row in taskset)
    if split_counts != Counter({"development": 80, "validation": 19, "development_exception": 1}):
        errors.append(f"invalid split distribution: {dict(split_counts)}")
    if any("2025" in row["case_id"] or row["source_year"] == "2025" for row in taskset):
        errors.append("2025 case selected")
    if {row["case_id"] for row in manifest} != set(case_ids):
        errors.append("source manifest case set differs from taskset")
    if {row["case_id"] for row in assignments} != set(case_ids):
        errors.append("assignment case set differs from taskset")

    manifest_by_case = {row["case_id"]: row for row in manifest}
    for row in taskset:
        case_id = row["case_id"]
        packet_dir = root / "case_packets" / case_id
        metadata = json.loads((packet_dir / "case_metadata.json").read_text(encoding="utf-8"))
        blank = json.loads((packet_dir / "blank_annotation.json").read_text(encoding="utf-8"))
        source = manifest_by_case[case_id]
        identity = (case_id, row["stock_code"], row["company_name"])
        if (metadata["case_id"], metadata["stock_code"], metadata["company_name"]) != identity:
            errors.append(f"{case_id}: metadata identity mismatch")
        if (blank["case_id"], blank["stock_code"], blank["company_name"]) != identity:
            errors.append(f"{case_id}: blank identity mismatch")
        if metadata["taskset_version"] != TASKSET_VERSION or source["taskset_version"] != TASKSET_VERSION:
            errors.append(f"{case_id}: taskset version mismatch")
        risks = blank.get("risks", [])
        if len(risks) != 8 or {risk.get("risk_code") for risk in risks} != set(V03_ENABLED_RISK_CODES):
            errors.append(f"{case_id}: active risk coverage mismatch")
        for risk in risks:
            if any(risk.get(field) is not None for field in ANSWER_FIELDS):
                errors.append(f"{case_id}/{risk.get('risk_code')}: answer field is not blank")
        if blank.get("evidence") != []:
            errors.append(f"{case_id}: evidence must be empty")
        contract_metadata = blank.get("metadata", {})
        evidence_schema = contract_metadata.get("evidence_object_schema", {})
        if contract_metadata.get("output_contract") != "ExpertAnnotationBundle":
            errors.append(f"{case_id}: output contract is not ExpertAnnotationBundle")
        if "0.0 to 1.0" not in contract_metadata.get("confidence_constraint", ""):
            errors.append(f"{case_id}: confidence range is not explicit")
        if set(evidence_schema) != EVIDENCE_SCHEMA_FIELDS:
            errors.append(f"{case_id}: Evidence Object schema fields mismatch")
        if evidence_schema.get("evidence_role") != EVIDENCE_ROLES:
            errors.append(f"{case_id}: evidence_role enum mismatch")
        if evidence_schema.get("requirement") != EVIDENCE_REQUIREMENTS:
            errors.append(f"{case_id}: requirement enum mismatch")
        if evidence_schema.get("source_authority") != SOURCE_AUTHORITIES:
            errors.append(f"{case_id}: source_authority enum mismatch")
        serialized = json.dumps({"metadata": metadata, "blank": blank}, ensure_ascii=False)
        if any(f'"{key}"' in serialized for key in FORBIDDEN_KEYS):
            errors.append(f"{case_id}: forbidden answer/provenance key detected")
        if WINDOWS_HOME_MARKER in serialized or UNIX_HOME_MARKER in serialized:
            errors.append(f"{case_id}: absolute local path detected")
        for path in packet_dir.iterdir():
            if path.is_file() and path.suffix.lower() in {".json", ".md", ".txt"}:
                text = path.read_text(encoding="utf-8-sig")
                if any(marker in text for marker in FORBIDDEN_PACKET_MARKERS):
                    errors.append(f"{case_id}: forbidden marker in {path.name}")

    packet_pdfs = list((root / "case_packets").rglob("*.pdf"))
    if packet_pdfs:
        errors.append(f"PDF binaries found: {[str(path) for path in packet_pdfs]}")
    if errors:
        raise ValueError("BLIND_PACKET_CONTAMINATION_DETECTED\n" + "\n".join(errors))
    return {
        "taskset_version": TASKSET_VERSION,
        "cases": 100,
        "risk_inspections": 800,
        "year_counts": dict(sorted(year_counts.items())),
        "split_counts": dict(split_counts),
        "selected_2025": 0,
        "all_packets_blank": True,
        "raw_pdf_count": 0,
    }


def main() -> int:
    try:
        result = validate_taskset()
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"valid": True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
