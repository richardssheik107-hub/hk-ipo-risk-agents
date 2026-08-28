"""Read-only Role-B audit for PR-H Document Evidence traceability.

The auditor consumes persisted ``IPOAnalysisResult`` JSON and, when supplied,
one governed prospectus PDF. It never calls an Agent, model, Retriever, or
production workflow and retains only bounded Evidence previews.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ipo_risk.schemas import IPOAnalysisResult, RiskItem
from ipo_risk.schemas.canonical_modeling import canonical_hash


AUDIT_VERSION = "v04_pr_h_role_b_document_evidence_audit_v1"
PREVIEW_LIMIT = 200
FORBIDDEN_PRODUCTION_KEYS = {
    "gold",
    "gold_label",
    "oracle",
    "oracle_features",
    "expert_annotation",
    "ground_truth",
    "future_return_label",
    "blind_2025_outcome",
    "blind_2025_y",
    "target_2025",
}
ALLOWED_STATUSES = {
    "PASS",
    "FAIL",
    "PARTIAL",
    "BLOCKED_INPUT_MISSING",
    "NOT_RUN",
    "NOT_AVAILABLE",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid analysis JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"analysis JSON must be an object: {path}")
    return payload


def _key_paths(value: Any, prefix: str = "") -> set[str]:
    paths: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).lower()
            path = f"{prefix}.{key_text}" if prefix else key_text
            paths.add(path)
            paths.update(_key_paths(child, path))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            paths.update(_key_paths(item, prefix))
    return paths


def _forbidden_paths(payload: Mapping[str, Any]) -> list[str]:
    return sorted(
        path
        for path in _key_paths(payload)
        if path.rsplit(".", 1)[-1] in FORBIDDEN_PRODUCTION_KEYS
    )


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _evidence_match(evidence_text: str, page_text: str) -> str:
    if evidence_text in page_text:
        return "exact"
    evidence_normalized = _normalize_text(evidence_text)
    page_normalized = _normalize_text(page_text)
    if evidence_normalized and evidence_normalized in page_normalized:
        return "normalized"
    probe = evidence_normalized[: min(80, len(evidence_normalized))]
    if len(probe) >= 30 and probe in page_normalized:
        return "partial"
    return "not_found"


def _all_risks(result: IPOAnalysisResult) -> list[RiskItem]:
    return [*result.verified_risks, *result.pending_risks, *result.rejected_risks]


def _trusted_case_ids(result: IPOAnalysisResult) -> set[str]:
    metadata = result.metadata
    candidates = (
        ((metadata.get("market_context") or {}).get("provenance") or {}).get("case_id"),
        ((metadata.get("ipo_profile") or {}).get("metadata") or {}).get("case_id"),
        (metadata.get("document") or {}).get("case_id"),
    )
    return {str(item) for item in candidates if item}


def _page_and_text_audit(
    risks: Sequence[RiskItem],
    pdf_path: Path | None,
) -> dict[str, Any]:
    evidence = [item for risk in risks for item in risk.evidence]
    if pdf_path is None:
        return {
            "physical_page_status": "NOT_RUN",
            "bbox_status": "NOT_RUN",
            "text_status": "NOT_RUN",
            "pdf_page_count": None,
            "invalid_page_evidence_ids": [],
            "invalid_bbox_evidence_ids": [],
            "text_match_counts": {},
            "text_not_found_evidence_ids": [],
            "samples": [],
        }
    if not pdf_path.is_file():
        return {
            "physical_page_status": "FAIL",
            "bbox_status": "NOT_RUN",
            "text_status": "NOT_RUN",
            "pdf_page_count": None,
            "invalid_page_evidence_ids": [item.evidence_id for item in evidence][:20],
            "invalid_bbox_evidence_ids": [],
            "text_match_counts": {},
            "text_not_found_evidence_ids": [],
            "samples": [],
        }
    import fitz

    invalid_pages: list[str] = []
    invalid_bbox: list[str] = []
    match_counts: Counter[str] = Counter()
    not_found: list[str] = []
    samples: list[dict[str, Any]] = []
    bbox_present = 0
    bbox_missing = 0
    with fitz.open(pdf_path) as document:
        page_count = document.page_count
        by_page: dict[int, list[Any]] = defaultdict(list)
        for item in evidence:
            if not isinstance(item.page, int) or isinstance(item.page, bool) or not 1 <= item.page <= page_count:
                invalid_pages.append(item.evidence_id)
                continue
            by_page[item.page].append(item)
        for physical_page in sorted(by_page):
            page = document.load_page(physical_page - 1)
            page_text = page.get_text("text")
            width, height = float(page.rect.width), float(page.rect.height)
            for item in by_page[physical_page]:
                match = _evidence_match(item.text, page_text)
                match_counts[match] += 1
                if match == "not_found":
                    not_found.append(item.evidence_id)
                if item.bbox is None:
                    bbox_missing += 1
                else:
                    bbox_present += 1
                    x0, y0, x1, y1 = item.bbox
                    values = (x0, y0, x1, y1)
                    if (
                        any(not math.isfinite(float(value)) for value in values)
                        or not (0 <= x0 < x1 <= width)
                        or not (0 <= y0 < y1 <= height)
                    ):
                        invalid_bbox.append(item.evidence_id)
                if len(samples) < 10:
                    samples.append(
                        {
                            "evidence_id": item.evidence_id,
                            "physical_page": physical_page,
                            "text_match": match,
                            "preview": item.text[:PREVIEW_LIMIT],
                        }
                    )
            del page_text, page
    if invalid_bbox:
        bbox_status = "FAIL"
    elif bbox_present and bbox_missing:
        bbox_status = "PARTIAL"
    elif bbox_present:
        bbox_status = "PASS"
    else:
        bbox_status = "NOT_AVAILABLE"
    return {
        "physical_page_status": "PASS" if not invalid_pages else "FAIL",
        "bbox_status": bbox_status,
        "text_status": "PASS" if not not_found else "FAIL",
        "pdf_page_count": page_count,
        "invalid_page_evidence_ids": sorted(set(invalid_pages))[:20],
        "invalid_bbox_evidence_ids": sorted(set(invalid_bbox))[:20],
        "text_match_counts": dict(sorted(match_counts.items())),
        "text_not_found_evidence_ids": sorted(set(not_found))[:20],
        "samples": samples,
    }


def _evidence_and_calculation_audit(
    risks: Sequence[RiskItem],
    *,
    expected_document_id: str,
) -> dict[str, Any]:
    occurrences: dict[str, list[tuple[RiskItem, Any]]] = defaultdict(list)
    risk_code_mismatches: set[str] = set()
    cross_case_references: set[str] = set()
    calculation_missing: set[str] = set()
    calculation_cross_risk: set[str] = set()
    risks_without_evidence: set[str] = set()
    document_identity_mismatches: set[str] = set()
    for risk in risks:
        local_ids = {item.evidence_id for item in risk.evidence}
        if not local_ids:
            risks_without_evidence.add(risk.risk_id)
        for item in risk.evidence:
            occurrences[item.evidence_id].append((risk, item))
            expected_chunk_id = (
                f"{expected_document_id}:page:{item.page}" if item.page is not None else None
            )
            if (
                item.document_id != expected_document_id
                or (expected_chunk_id is not None and item.chunk_id != expected_chunk_id)
            ):
                document_identity_mismatches.add(item.evidence_id)
            metadata_risk = item.metadata.get("risk_code")
            if metadata_risk and metadata_risk != risk.risk_code:
                risk_code_mismatches.add(item.evidence_id)
            if item.metadata.get("case_id") or item.metadata.get("stock_code"):
                cross_case_references.add(item.evidence_id)
        if risk.calculation is not None:
            if not risk.calculation.evidence_ids:
                calculation_missing.add(risk.risk_id)
            for evidence_id in risk.calculation.evidence_ids:
                if evidence_id not in occurrences and evidence_id not in local_ids:
                    calculation_missing.add(evidence_id)
                elif evidence_id not in local_ids:
                    calculation_cross_risk.add(evidence_id)
    duplicates = sorted(item for item, refs in occurrences.items() if len(refs) > 1)
    return {
        "evidence_count": sum(len(risk.evidence) for risk in risks),
        "unique_evidence_count": len(occurrences),
        "duplicate_evidence_ids": duplicates[:20],
        "risk_code_mismatch_evidence_ids": sorted(risk_code_mismatches)[:20],
        "risk_ids_without_evidence": sorted(risks_without_evidence)[:20],
        "document_identity_mismatch_evidence_ids": sorted(document_identity_mismatches)[:20],
        "evidence_with_identity_metadata": sorted(cross_case_references)[:20],
        "calculation_count": sum(risk.calculation is not None for risk in risks),
        "calculation_missing_evidence_ids": sorted(calculation_missing)[:20],
        "calculation_cross_risk_evidence_ids": sorted(calculation_cross_risk)[:20],
        "calculation_status": (
            "PASS" if not calculation_missing and not calculation_cross_risk else "FAIL"
        ),
    }


def _index_and_supervisor_audit(result: IPOAnalysisResult, risks: Sequence[RiskItem]) -> dict[str, Any]:
    evidence_owner: dict[str, str] = {}
    evidence_payload: dict[str, Any] = {}
    for risk in risks:
        for item in risk.evidence:
            evidence_owner.setdefault(item.evidence_id, risk.risk_code)
            evidence_payload.setdefault(item.evidence_id, item)
    index = next((section for section in result.report_sections if section.title == "Evidence Index"), None)
    entries = list((index.metadata.get("entries") or [])) if index is not None else []
    index_ids = [str(item.get("evidence_id") or "") for item in entries]
    index_counts = Counter(index_ids)
    index_set = {item for item in index_ids if item}
    evidence_set = set(evidence_payload)
    risk_code_mismatch = sorted(
        evidence_id
        for evidence_id, entry in ((str(item.get("evidence_id") or ""), item) for item in entries)
        if evidence_id in evidence_owner and entry.get("risk_code") != evidence_owner[evidence_id]
    )
    content_mismatch = sorted(
        evidence_id
        for evidence_id, entry in ((str(item.get("evidence_id") or ""), item) for item in entries)
        if evidence_id in evidence_payload
        and (
            entry.get("page") != evidence_payload[evidence_id].page
            or entry.get("text") != evidence_payload[evidence_id].text
        )
    )
    body_references = {
        evidence_id
        for section in result.report_sections
        for evidence_id in section.evidence_ids
    }
    final = result.metadata.get("final_supervision") or {}
    final_evidence = {str(item) for item in final.get("referenced_evidence_ids", [])}
    final_risks = {str(item) for item in final.get("referenced_risk_ids", [])}
    known_risks = {risk.risk_id for risk in result.verified_risks}
    invented_finding_evidence = {
        str(evidence_id)
        for group in (final.get("composite_findings", []), final.get("conflicts", []))
        for item in group
        for evidence_id in item.get("evidence_ids", [])
        if str(evidence_id) not in evidence_set
    }
    missing = sorted(evidence_set - index_set)
    orphan = sorted(index_set - evidence_set)
    duplicate = sorted(item for item, count in index_counts.items() if item and count > 1)
    body_missing = sorted(body_references - index_set)
    invented_evidence = sorted((final_evidence - evidence_set) | invented_finding_evidence)
    invented_risks = sorted(final_risks - known_risks)
    creates_no_new = (final.get("metadata") or {}).get("creates_no_new_risk")
    failures = any(
        (
            missing,
            orphan,
            duplicate,
            body_missing,
            risk_code_mismatch,
            content_mismatch,
            invented_evidence,
            invented_risks,
        )
    ) or creates_no_new is not True
    return {
        "index_entry_count": len(entries),
        "missing_index_evidence_ids": missing[:20],
        "orphan_index_evidence_ids": orphan[:20],
        "duplicate_index_evidence_ids": duplicate[:20],
        "body_reference_missing_index_ids": body_missing[:20],
        "index_risk_code_mismatch_ids": risk_code_mismatch[:20],
        "index_content_mismatch_ids": content_mismatch[:20],
        "final_supervisor_invented_evidence_ids": invented_evidence[:20],
        "final_supervisor_invented_risk_ids": invented_risks[:20],
        "creates_no_new_risk": creates_no_new,
        "status": "FAIL" if failures else "PASS",
    }


def _provenance_audit(result: IPOAnalysisResult, risks: Sequence[RiskItem]) -> dict[str, Any]:
    verifier_missing = [
        risk.risk_id
        for risk in risks
        if not risk.verification_status.value or not risk.verification_notes
    ]
    agent_missing = [risk.risk_id for risk in risks if not risk.agent_name]
    logged_agents = {item.agent_name for item in result.agent_logs}
    agent_log_missing = [risk.risk_id for risk in risks if risk.agent_name not in logged_agents]
    return {
        "verifier_status": "PASS" if not verifier_missing else "PARTIAL",
        "verifier_missing_risk_ids": verifier_missing[:20],
        "agent_status": (
            "FAIL" if agent_missing else "PASS" if not agent_log_missing else "PARTIAL"
        ),
        "agent_missing_risk_ids": agent_missing[:20],
        "agent_log_missing_risk_ids": agent_log_missing[:20],
    }


def determinism_signature(result: IPOAnalysisResult) -> dict[str, Any]:
    """Return the stable Evidence/report subset used for existing-run comparison."""

    risks = _all_risks(result)
    index = next((section for section in result.report_sections if section.title == "Evidence Index"), None)
    final = result.metadata.get("final_supervision") or {}
    return {
        "risk_count": len(risks),
        "risk_ids": sorted(risk.risk_id for risk in risks),
        "evidence": sorted(
            (item.evidence_id, item.page, risk.risk_code)
            for risk in risks
            for item in risk.evidence
        ),
        "evidence_index": sorted(
            (str(item.get("evidence_id") or ""), item.get("page"), item.get("risk_code"))
            for item in ((index.metadata.get("entries") or []) if index is not None else [])
        ),
        "final_supervision_hash": canonical_hash(final),
    }


def audit_case(
    result: IPOAnalysisResult | None,
    *,
    case_id: str,
    stock_code: str,
    pdf_path: Path | None = None,
    expected_pdf_sha256: str | None = None,
    comparison: IPOAnalysisResult | None = None,
) -> dict[str, Any]:
    """Audit one real-case result without mutating it or its source PDF."""

    if result is None:
        return {
            "case_id": case_id,
            "stock_code": stock_code,
            "input_status": "BLOCKED_INPUT_MISSING",
            "analysis_status": "NOT_RUN",
            "risk_item_count": 0,
            "evidence_count": 0,
            "evidence_resolved": 0,
            "physical_page_passed": "NOT_RUN",
            "bbox_status": "NOT_RUN",
            "calculation_linkage": "NOT_RUN",
            "verifier_provenance": "NOT_RUN",
            "agent_provenance": "NOT_RUN",
            "evidence_index_status": "NOT_RUN",
            "determinism_status": "NOT_RUN",
            "leakage_status": "NOT_RUN",
            "overall_status": "BLOCKED_INPUT_MISSING",
            "blocker": "analysis_runtime_missing",
        }
    risks = _all_risks(result)
    raw = result.model_dump(mode="json")
    trusted_case_ids = _trusted_case_ids(result)
    identity_failures: list[str] = []
    if result.stock_code != stock_code:
        identity_failures.append("stock_code_mismatch")
    if trusted_case_ids and trusted_case_ids != {case_id}:
        identity_failures.append("case_id_mismatch")
    modes = result.metadata.get("component_modes") or {}
    config = result.metadata.get("configuration") or {}
    governed_input = (
        result.status.value in {"completed", "partial"}
        and config.get("use_mock") is False
        and modes.get("parser") == "real"
    )
    pdf_hash = _sha256(pdf_path) if pdf_path is not None and pdf_path.is_file() else None
    if expected_pdf_sha256 and pdf_hash != expected_pdf_sha256:
        identity_failures.append("prospectus_sha256_mismatch")
    evidence_audit = _evidence_and_calculation_audit(
        risks,
        expected_document_id=result.request_id,
    )
    page_audit = _page_and_text_audit(risks, pdf_path)
    index_audit = _index_and_supervisor_audit(result, risks)
    provenance = _provenance_audit(result, risks)
    forbidden = _forbidden_paths(raw)
    cross_case_evidence = sorted(
        item.evidence_id
        for risk in risks
        for item in risk.evidence
        if (
            item.metadata.get("case_id") not in {None, "", case_id}
            or item.metadata.get("stock_code") not in {None, "", stock_code}
        )
    )
    evidence_failures = any(
        (
            evidence_audit["duplicate_evidence_ids"],
            evidence_audit["risk_code_mismatch_evidence_ids"],
            evidence_audit["risk_ids_without_evidence"],
            evidence_audit["document_identity_mismatch_evidence_ids"],
            cross_case_evidence,
        )
    )
    calculation_fail = evidence_audit["calculation_status"] == "FAIL"
    deterministic = (
        "PASS"
        if comparison is not None and determinism_signature(result) == determinism_signature(comparison)
        else "FAIL"
        if comparison is not None
        else "NOT_RUN"
    )
    hard_fail = any(identity_failures) or any(
        (
            evidence_failures,
            calculation_fail,
            page_audit["physical_page_status"] == "FAIL",
            page_audit["text_status"] == "FAIL",
            page_audit["bbox_status"] == "FAIL",
            index_audit["status"] == "FAIL",
            bool(forbidden),
            deterministic == "FAIL",
        )
    )
    if hard_fail:
        overall = "FAIL"
    elif not governed_input:
        overall = "PARTIAL"
    elif provenance["verifier_status"] == "PARTIAL" or provenance["agent_status"] == "PARTIAL":
        overall = "PARTIAL"
    else:
        overall = "PASS"
    return {
        "case_id": case_id,
        "stock_code": stock_code,
        "input_status": "PASS" if governed_input and not identity_failures else "PARTIAL",
        "analysis_status": result.status.value,
        "analysis_id": result.analysis_id,
        "request_id": result.request_id,
        "risk_item_count": len(risks),
        "evidence_count": evidence_audit["evidence_count"],
        "evidence_resolved": evidence_audit["unique_evidence_count"]
        - len(evidence_audit["duplicate_evidence_ids"]),
        "physical_page_passed": page_audit["physical_page_status"],
        "bbox_status": page_audit["bbox_status"],
        "evidence_text_status": page_audit["text_status"],
        "calculation_linkage": evidence_audit["calculation_status"],
        "verifier_provenance": provenance["verifier_status"],
        "agent_provenance": provenance["agent_status"],
        "evidence_index_status": index_audit["status"],
        "determinism_status": deterministic,
        "leakage_status": "PASS" if not forbidden else "FAIL",
        "overall_status": overall,
        "blocker": None if overall == "PASS" else "see_diagnostics",
        "identity": {
            "trusted_case_ids": sorted(trusted_case_ids),
            "failures": identity_failures,
            "prospectus_sha256": pdf_hash,
        },
        "evidence": evidence_audit,
        "pages": page_audit,
        "provenance": provenance,
        "evidence_index": index_audit,
        "forbidden_metadata_paths": forbidden[:20],
        "cross_case_evidence_ids": cross_case_evidence[:20],
    }


def build_report(cases: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate bounded case diagnostics under the formal three-case Gate."""

    audited = [case for case in cases if case["analysis_status"] != "NOT_RUN"]
    passed = [case for case in audited if case["overall_status"] == "PASS"]
    evidence_count = sum(case["evidence_count"] for case in audited)
    resolved = sum(case["evidence_resolved"] for case in audited)
    formal_pass = len(passed) >= 3 and len(passed) == len(audited)
    return {
        "audit_version": AUDIT_VERSION,
        "result": "PASS" if formal_pass else "PARTIAL" if audited else "BLOCKED",
        "real_cases_required": "3-5",
        "real_cases_available": len(audited),
        "real_cases_audited": len(audited),
        "real_cases_passed": len(passed),
        "evidence_references": evidence_count,
        "evidence_resolved": resolved,
        "physical_page_linkage": (
            "PASS" if audited and all(case["physical_page_passed"] == "PASS" for case in audited)
            else "PARTIAL" if audited else "NOT_RUN"
        ),
        "calculation_linkage": (
            "PASS" if audited and all(case["calculation_linkage"] == "PASS" for case in audited)
            else "PARTIAL" if audited else "NOT_RUN"
        ),
        "verifier_provenance": (
            "PASS" if audited and all(case["verifier_provenance"] == "PASS" for case in audited)
            else "PARTIAL" if audited else "NOT_AVAILABLE"
        ),
        "agent_provenance": (
            "PASS" if audited and all(case["agent_provenance"] == "PASS" for case in audited)
            else "PARTIAL" if audited else "NOT_AVAILABLE"
        ),
        "final_report_evidence_index": (
            "PASS" if audited and all(case["evidence_index_status"] == "PASS" for case in audited)
            else "PARTIAL" if audited else "NOT_RUN"
        ),
        "production_oracle_leakage": (
            "PASS" if audited and all(case["leakage_status"] == "PASS" for case in audited)
            else "FAIL" if audited else "NOT_RUN"
        ),
        "blind_2025_outcome_accessed": False,
        "cases": list(cases),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-json", type=Path, required=True)
    parser.add_argument("--comparison-analysis-json", type=Path)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--stock-code", required=True)
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--expected-pdf-sha256")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = IPOAnalysisResult.model_validate(_read_object(args.analysis_json))
    comparison = (
        IPOAnalysisResult.model_validate(_read_object(args.comparison_analysis_json))
        if args.comparison_analysis_json is not None
        else None
    )
    report = build_report(
        [
            audit_case(
                result,
                case_id=args.case_id,
                stock_code=args.stock_code,
                pdf_path=args.pdf,
                expected_pdf_sha256=args.expected_pdf_sha256,
                comparison=comparison,
            )
        ]
    )
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["result"] in {"PASS", "PARTIAL"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
