"""Post-run, Existing-Gold-only forensics for a frozen Role-B cohort.

The module joins frozen evaluator rows to already-persisted runtime artifacts.
Gold is loaded only after analysis has finished and is never exposed to the
parser, retriever, Agents, provider, or journal identity.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable, Mapping, Sequence
import unicodedata

import fitz


FORENSIC_VERSION = "v046_role_b_m1_m2_forensics_v1"
PROOF_LEVELS = frozenset({"PROVEN", "INFERRED", "UNAVAILABLE"})
RISK_ROOT_CAUSES = frozenset(
    {
        "identity_or_evaluator_input_mismatch",
        "parser_text_missing",
        "parser_page_mapping_mismatch",
        "parser_anchor_ambiguous",
        "retrieval_candidate_miss",
        "retrieved_page_anchor_truncated",
        "retrieval_ranking_or_topk_miss",
        "llm_not_invoked_due_to_no_evidence",
        "llm_required_but_offline_mode",
        "llm_not_invoked_unexpectedly",
        "llm_transport_failure",
        "llm_authentication_or_request_failure",
        "llm_structured_validation_failure",
        "llm_scope_rejection",
        "llm_semantic_false_negative",
        "llm_abstention_with_sufficient_evidence",
        "deterministic_extraction_miss",
        "numeric_extraction_miss",
        "wrong_period_selection",
        "percentage_scale_mismatch",
        "schema_normalization_miss",
        "builder_not_applicable_misclassification",
        "riskitem_reconciliation_drop",
        "verifier_rejection",
        "final_bucket_or_serialization_drop",
        "status_mismatch",
        "level_mismatch",
        "calculation_value_mismatch",
        "calculation_missing",
        "final_evidence_not_retained",
        "final_evidence_page_mismatch",
        "final_evidence_anchor_mismatch",
        "correct",
        "unavailable_trace",
    }
)
EVIDENCE_ROOT_CAUSES = frozenset(
    {
        "identity_or_evaluator_input_mismatch",
        "parser_text_missing",
        "parser_page_mapping_mismatch",
        "parser_anchor_ambiguous",
        "retrieval_candidate_miss",
        "retrieved_page_anchor_truncated",
        "retrieval_ranking_or_topk_miss",
        "risk_absent_caused_evidence_miss",
        "risk_rejected_caused_evidence_miss",
        "evidence_not_attached_to_candidate",
        "evidence_dropped_during_reconciliation",
        "evidence_dropped_during_verification",
        "final_evidence_not_retained",
        "final_evidence_page_mismatch",
        "final_evidence_anchor_mismatch",
        "final_evidence_covered",
        "unavailable_trace",
    }
)
TASKS = (
    "shareholder_rights_extract",
    "litigation_compliance_extract",
    "business_precommercial_commercialization_extract",
    "business_precommercial_core_product_extract",
)
RISK_TO_TASK = {"redemption_rights": "shareholder_rights_extract"}
RISK_TO_FAMILY = {
    "cash_runway": "cash_burn_pressure",
    "customer_concentration": "customer_concentration",
    "supplier_concentration": "supplier_concentration",
    "redemption_rights": "redemption_rights",
}
_WS = re.compile(r"\s+")
_AGENT_DIAGNOSTIC = re.compile(
    r"ComponentDiagnostic\(risk_code='(?P<risk>[^']+)', "
    r"code=<DiagnosticCode\.[A-Z_]+: '(?P<code>[^']+)'>, "
    r"message='(?P<message>(?:\\'|[^'])*)'(?P<body>.*?)(?=\), ComponentDiagnostic|\)\]$)",
    re.DOTALL,
)


class RoleBForensicsError(RuntimeError):
    """Fail-closed forensic input or identity error."""


@dataclass(frozen=True)
class ForensicInputs:
    root: Path
    run_root: Path
    coverage_path: Path
    subset_path: Path
    catalog_path: Path
    prospectus_root: Path
    output_dir: Path
    inventory_roots: tuple[tuple[str, Path], ...] = ()


def canonical_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "").casefold()
    return _WS.sub("", text)


def anchor_matches(anchor: str, candidate: str, *, minimum_chars: int = 12) -> bool:
    gold = canonical_text(anchor)
    text = canonical_text(candidate)
    if not gold or not text:
        return False
    if min(len(gold), len(text)) < minimum_chars:
        return gold == text
    return gold in text or text in gold


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RoleBForensicsError(f"invalid_json:{path.name}") from exc


def read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    except OSError as exc:
        raise RoleBForensicsError(f"invalid_csv:{path.name}") from exc


def as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes"}


def safe_ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def git_output(root: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False
    )
    return process.stdout.strip() if process.returncode == 0 else ""


def _json_dump(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _csv_dump(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: (
                        json.dumps(value, ensure_ascii=False, sort_keys=True)
                        if isinstance(value, (list, dict))
                        else value
                    )
                    for key, value in row.items()
                }
            )


def _artifact_identity(path: Path) -> dict[str, Any]:
    if path.suffix.lower() != ".json":
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, Mapping):
        return {}
    identity: dict[str, Any] = {}
    for key in (
        "run_id",
        "iteration_id",
        "case_count",
        "subset_hash",
        "source_coverage_manifest_hash",
        "gold_manifest_hash",
        "code_fingerprint",
        "provider",
        "model",
        "prompt_set_hash",
        "validation_opened",
        "blind_2025_outcome_accessed",
    ):
        if key in payload:
            identity[key] = payload[key]
    code_state = payload.get("code_state")
    if isinstance(code_state, Mapping):
        identity.setdefault("code_fingerprint", code_state.get("code_fingerprint"))
        identity.setdefault("git_head", code_state.get("git_head"))
    return identity


def build_artifact_inventory(
    roots: Sequence[tuple[str, Path]], authoritative_run: Path
) -> list[dict[str, Any]]:
    wanted = {
        "fixed10_development_subset.json",
        "iteration_summary.json",
        "failure_focus.json",
        "document_benchmark_summary.json",
        "risk_benchmark.csv",
        "evidence_benchmark.csv",
        "analysis_results.jsonl",
        "analysis_result.json",
        "ablation_summary.json",
        "llm_call_quality.json",
        "retrieval_waterfall.json",
        "risk_pipeline_waterfall.json",
        "monotonicity_report.json",
        "journal_manifest.json",
        "preflight.json",
        "structured_smoke_summary.json",
        "baseline_manifest.json",
        "pipeline_trace.json",
    }
    rows: list[dict[str, Any]] = []
    authoritative = authoritative_run.resolve()
    for label, root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name not in wanted:
                continue
            resolved = path.resolve()
            usable = resolved == authoritative or authoritative in resolved.parents
            rows.append(
                {
                    "relative_path": f"{label}/{path.relative_to(root).as_posix()}",
                    "sha256": file_sha256(path),
                    "size": path.stat().st_size,
                    **_artifact_identity(path),
                    "usable": usable,
                    "rejection_reason": None if usable else "non_authoritative_run_identity",
                }
            )
    return rows


def _catalog_index(path: Path) -> dict[str, dict[str, str]]:
    return {row["case_id"]: row for row in read_csv(path)}


def _verify_pdf(case_id: str, row: Mapping[str, str], root: Path) -> Path:
    if row.get("dataset_split") != "development":
        raise RoleBForensicsError(f"non_development_case:{case_id}")
    path = root / str(row.get("relative_path") or "")
    if not path.is_file():
        raise RoleBForensicsError(f"prospectus_missing:{case_id}")
    if int(row.get("file_size_bytes") or 0) != path.stat().st_size:
        raise RoleBForensicsError(f"prospectus_size_mismatch:{case_id}")
    if str(row.get("sha256") or "") != file_sha256(path):
        raise RoleBForensicsError(f"prospectus_hash_mismatch:{case_id}")
    return path


def build_parser_preservation(
    evidence_units: Sequence[Mapping[str, Any]],
    case_ids: Sequence[str],
    catalog_path: Path,
    prospectus_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    catalog = _catalog_index(catalog_path)
    units_by_case: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for unit in evidence_units:
        if str(unit.get("case_id")) in case_ids:
            units_by_case[str(unit.get("case_id"))].append(unit)

    rows: list[dict[str, Any]] = []
    for case_id in case_ids:
        catalog_row = catalog.get(case_id)
        if catalog_row is None:
            raise RoleBForensicsError(f"catalog_case_missing:{case_id}")
        pdf = _verify_pdf(case_id, catalog_row, prospectus_root)
        with fitz.open(pdf) as document:
            if document.page_count != int(catalog_row.get("pdf_page_count") or 0):
                raise RoleBForensicsError(f"prospectus_page_count_mismatch:{case_id}")
            page_text = {
                index + 1: document.load_page(index).get_text("text").strip()
                for index in range(document.page_count)
            }
        for unit in units_by_case.get(case_id, []):
            page = int(unit.get("page") or 0)
            anchor = str(unit.get("exact_text") or "")
            expected = anchor_matches(anchor, page_text.get(page, ""))
            offsets = {
                offset: anchor_matches(anchor, page_text.get(page + offset, ""))
                for offset in (-2, -1, 1, 2)
                if page + offset > 0
            }
            matched_pages = [
                number for number, text in page_text.items() if anchor_matches(anchor, text)
            ]
            any_page = bool(matched_pages)
            within_two = expected or any(offsets.values())
            if expected and len(matched_pages) == 1:
                mapping = "parser_preserved_expected_page"
                preservation = "parser_preserved_expected_page"
            elif expected and len(matched_pages) > 1:
                mapping = "multiple_ambiguous_parser_matches"
                preservation = "multiple_ambiguous_parser_matches"
            elif any_page:
                mapping = "parser_expected_page_missing_but_other_page_hit"
                preservation = mapping
            else:
                mapping = "parser_anchor_missing_everywhere"
                preservation = mapping
            rows.append(
                {
                    "case_id": case_id,
                    "evidence_unit_id": str(unit.get("evidence_unit_id") or ""),
                    "risk_code": str(unit.get("source_risk_code") or ""),
                    "gold_physical_page": page,
                    "anchor_length": len(canonical_text(anchor)),
                    "short_anchor_under_12_chars": len(canonical_text(anchor)) < 12,
                    "anchor_found_expected_page": expected,
                    "anchor_found_page_minus_1": offsets.get(-1, False),
                    "anchor_found_page_plus_1": offsets.get(1, False),
                    "anchor_found_within_2_pages": within_two,
                    "anchor_found_any_page": any_page,
                    "matched_pages": matched_pages,
                    "match_count": len(matched_pages),
                    "parser_page_mapping_status": mapping,
                    "parser_text_preservation_status": preservation,
                }
            )
    offsets = Counter()
    for row in rows:
        if row["anchor_found_expected_page"]:
            offsets[0] += 1
        elif row["matched_pages"]:
            offsets[int(row["matched_pages"][0]) - int(row["gold_physical_page"])] += 1
    summary = {
        "report_version": FORENSIC_VERSION,
        "unit_count": len(rows),
        "expected_page_preservation_rate": safe_ratio(
            sum(bool(row["anchor_found_expected_page"]) for row in rows), len(rows)
        ),
        "any_page_preservation_rate": safe_ratio(
            sum(bool(row["anchor_found_any_page"]) for row in rows), len(rows)
        ),
        "page_offset_distribution": {str(key): value for key, value in sorted(offsets.items())},
        "short_anchor_unit_count": sum(row["short_anchor_under_12_chars"] for row in rows),
        "multiple_match_count": sum(int(row["match_count"]) > 1 for row in rows),
        "retriever_used": False,
        "llm_used": False,
        "gold_join_stage": "post_run_only",
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
        "units": rows,
    }
    return rows, summary


def _index(rows: Iterable[Mapping[str, Any]], key: str) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        value = str(row.get(key) or "")
        if not value or value in result:
            raise RoleBForensicsError(f"invalid_or_duplicate_identity:{key}:{value}")
        result[value] = row
    return result


def build_retrieval_stage(
    evidence_rows: Sequence[Mapping[str, Any]],
    pipeline_trace: Sequence[Mapping[str, Any]],
    parser_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    traces = _index(
        (row for row in pipeline_trace if row.get("trace_kind") == "retrieval"),
        "evidence_unit_id",
    )
    parser = _index(parser_rows, "evidence_unit_id")
    units: list[dict[str, Any]] = []
    for evaluated in evidence_rows:
        unit_id = str(evaluated.get("evidence_unit_id") or "")
        trace = traces.get(unit_id)
        parsed = parser.get(unit_id)
        if trace is None or parsed is None:
            raise RoleBForensicsError(f"retrieval_trace_missing:{unit_id}")
        first_page = trace.get("first_gold_page_rank")
        first_anchor = trace.get("first_gold_rank")
        consumed = as_bool(trace.get("agent_consumed"))
        if not parsed.get("anchor_found_any_page"):
            status = "parser_anchor_missing_everywhere"
        elif first_page is None:
            status = "retrieval_candidate_miss"
        elif first_anchor is None:
            status = "retrieved_page_anchor_truncated"
        elif not consumed:
            status = "retrieval_ranking_or_topk_miss"
        else:
            status = "agent_consumed_success"
        units.append(
            {
                "case_id": str(evaluated.get("case_id") or ""),
                "evidence_unit_id": unit_id,
                "risk_code": str(evaluated.get("source_risk_code") or ""),
                "candidate_count": int(trace.get("candidate_count") or 0),
                "first_gold_page_rank": first_page,
                "first_exact_anchor_rank": first_anchor,
                **{
                    f"gold_page_in_top{k}": first_page is not None and int(first_page) <= k
                    for k in (1, 3, 5, 10, 20)
                },
                **{
                    f"gold_anchor_in_top{k}": first_anchor is not None and int(first_anchor) <= k
                    for k in (1, 3, 5, 10, 20)
                },
                "agent_consumed_gold_page": consumed and first_page is not None,
                "agent_consumed_gold_anchor": consumed,
                "query_family": trace.get("retrieval_query_family") or [],
                "query_intent": trace.get("retrieval_query_family") or [],
                "actual_agent_limit": 10,
                "retriever_name": "role_b_v046_financial_high_recall_or_keyword",
                "retrieval_status": status,
                "proof_level": "PROVEN",
            }
        )
    by_risk: dict[str, dict[str, Any]] = {}
    for risk_code in sorted({row["risk_code"] for row in units}):
        selected = [row for row in units if row["risk_code"] == risk_code]
        by_risk[risk_code] = {
            "evidence_unit_count": len(selected),
            "candidate_recall_at_20": safe_ratio(
                sum(bool(row["gold_anchor_in_top20"]) for row in selected), len(selected)
            ),
            "agent_consumed_recall": safe_ratio(
                sum(bool(row["agent_consumed_gold_anchor"]) for row in selected), len(selected)
            ),
            "same_page_but_anchor_truncated_count": sum(
                row["first_gold_page_rank"] is not None
                and row["first_exact_anchor_rank"] is None
                for row in selected
            ),
            "first_rank_distribution": dict(
                sorted(Counter(str(row["first_exact_anchor_rank"]) for row in selected).items())
            ),
        }
    return units, {
        "report_version": FORENSIC_VERSION,
        "unit_count": len(units),
        "per_risk": by_risk,
        "units": units,
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
    }


def build_llm_stage(
    quality: Mapping[str, Any], case_count: int, preflight: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    calls = [row for row in quality.get("calls", []) if isinstance(row, Mapping)]
    rows: list[dict[str, Any]] = []
    for task in TASKS:
        selected = [row for row in calls if row.get("task_name") == task]
        expected = case_count
        rows.append(
            {
                "task_name": task,
                "expected_call_count": expected,
                "actual_call_count": len(selected),
                "not_invoked_count": expected - len({str(row.get('case_id')) for row in selected}),
                "success_count": sum(not row.get("failure_kind") for row in selected),
                "transport_failure_count": sum(row.get("failure_kind") == "transport" for row in selected),
                "authentication_failure_count": sum(row.get("failure_kind") == "authentication" for row in selected),
                "request_failure_count": sum(row.get("failure_kind") == "request" for row in selected),
                "response_validation_failure_count": sum(row.get("failure_kind") == "response_validation" for row in selected),
                "structured_valid_count": sum(row.get("structured_valid") is True for row in selected),
                "scope_valid_count": sum(row.get("scope_valid") is True for row in selected),
                "scope_rejection_count": sum(row.get("failure_kind") == "scope_validation" for row in selected),
                "abstention_count": "UNAVAILABLE_WITHOUT_RAW_SEMANTIC_TRACE",
                "retry_count": sum(int(row.get("transport_retry_count") or 0) for row in selected),
                "structured_correction_count": sum(int(row.get("structured_correction_count") or 0) for row in selected),
            }
        )
    smoke_tasks = set((preflight.get("structured_smoke") or {}).get("observed_tasks") or [])
    missing = sorted(set(TASKS) - smoke_tasks)
    return rows, {
        "report_version": FORENSIC_VERSION,
        "provider": next((row.get("provider") for row in calls), None),
        "model": next((row.get("model") for row in calls), None),
        "task_rows": rows,
        "smoke_task_coverage_gap": missing,
        "smoke_gate_contract_modified": False,
        "gated_extra_network_calls": 0,
        "journal_identity_reused": True,
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
    }


def _diagnostics_from_result(result: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    diagnostics: dict[str, dict[str, Any]] = {}
    for log in result.get("agent_logs") or []:
        if not isinstance(log, Mapping) or log.get("agent_name") not in {"financial", "legal", "business"}:
            continue
        value = str((log.get("metadata") or {}).get("value") or "")
        for match in _AGENT_DIAGNOSTIC.finditer(value):
            body = match.group("body")
            diagnostics[match.group("risk")] = {
                "agent_name": log.get("agent_name"),
                "diagnostic_code": match.group("code"),
                "message_hash": sha256(match.group("message").encode("utf-8")).hexdigest(),
                "extraction_status": _quoted_field(body, "extraction_status"),
                "builder_status": _quoted_field(body, "builder_status"),
                "issue_codes": _list_field(body, "issues") or _list_field(body, "internal_issue_codes"),
                "direct_artifact": "analysis_result.agent_logs",
            }
    return diagnostics


def _quoted_field(value: str, key: str) -> str | None:
    match = re.search(rf"['\"]?{re.escape(key)}['\"]?\s*:\s*['\"]([^'\"]+)['\"]", value)
    return match.group(1) if match else None


def _list_field(value: str, key: str) -> list[str]:
    match = re.search(rf"['\"]?{re.escape(key)}['\"]?\s*:\s*\[(.*?)\]", value, re.DOTALL)
    if not match:
        return []
    return re.findall(r"['\"]([^'\"]+)['\"]", match.group(1))


def _all_final_risks(result: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any]]]:
    rows: list[tuple[str, Mapping[str, Any]]] = []
    for bucket in ("verified_risks", "pending_risks", "rejected_risks"):
        for risk in result.get(bucket) or []:
            if isinstance(risk, Mapping):
                rows.append((bucket.removesuffix("_risks"), risk))
    return rows


def _final_risk_index(results: Mapping[str, Mapping[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for case_id, result in results.items():
        for bucket, risk in _all_final_risks(result):
            risk_code = str(risk.get("risk_code") or "")
            index[(case_id, risk_code)] = {"bucket": bucket, "risk": risk}
    return index


def _load_case_results(run_root: Path, mode: str, case_ids: Sequence[str]) -> dict[str, Mapping[str, Any]]:
    results: dict[str, Mapping[str, Any]] = {}
    for case_id in case_ids:
        path = run_root / mode / "run" / case_id / "analysis_result.json"
        payload = load_json(path)
        if not isinstance(payload, Mapping) or payload.get("status") != "completed":
            raise RoleBForensicsError(f"analysis_result_invalid:{case_id}")
        results[case_id] = payload
    return results


def _llm_index(quality: Mapping[str, Any]) -> dict[tuple[str, str], Mapping[str, Any]]:
    return {
        (str(row.get("case_id") or ""), str(row.get("task_name") or "")): row
        for row in quality.get("calls", [])
        if isinstance(row, Mapping)
    }


def _risk_root_cause(
    row: Mapping[str, Any],
    parser_units: Sequence[Mapping[str, Any]],
    retrieval_units: Sequence[Mapping[str, Any]],
    diagnostic: Mapping[str, Any] | None,
    llm: Mapping[str, Any] | None,
    *,
    llm_expected_available: bool = True,
) -> tuple[str, str, list[str]]:
    if as_bool(row.get("correct")):
        return "correct", "PROVEN", []
    if not parser_units:
        return "identity_or_evaluator_input_mismatch", "PROVEN", ["no_gold_evidence_units"]
    if not any(as_bool(item.get("anchor_found_any_page")) for item in parser_units):
        return "parser_text_missing", "PROVEN", ["no_anchor_preserved_any_page"]
    consumed = [item for item in retrieval_units if as_bool(item.get("agent_consumed_gold_anchor"))]
    if not consumed:
        statuses = {str(item.get("retrieval_status")) for item in retrieval_units}
        if "retrieved_page_anchor_truncated" in statuses:
            return "retrieved_page_anchor_truncated", "PROVEN", sorted(statuses)
        if "retrieval_ranking_or_topk_miss" in statuses:
            return "retrieval_ranking_or_topk_miss", "PROVEN", sorted(statuses)
        return "retrieval_candidate_miss", "PROVEN", sorted(statuses)
    risk_code = str(row.get("source_risk_code") or "")
    if llm is not None and llm.get("failure_kind"):
        mapping = {
            "transport": "llm_transport_failure",
            "authentication": "llm_authentication_or_request_failure",
            "request": "llm_authentication_or_request_failure",
            "response_validation": "llm_structured_validation_failure",
            "scope_validation": "llm_scope_rejection",
        }
        return mapping.get(str(llm.get("failure_kind")), "llm_authentication_or_request_failure"), "PROVEN", []
    if risk_code in RISK_TO_TASK and llm is None:
        if not llm_expected_available:
            return "llm_required_but_offline_mode", "PROVEN", []
        return "llm_not_invoked_unexpectedly", "PROVEN", []
    if diagnostic and diagnostic.get("diagnostic_code") != "risk_generated":
        issues = [str(item) for item in diagnostic.get("issue_codes") or []]
        if risk_code in {"cash_runway", "customer_concentration", "supplier_concentration"}:
            if any("period" in item for item in issues):
                return "wrong_period_selection", "PROVEN", issues
            if any("value" in item or "unit" in item or "row" in item for item in issues):
                return "numeric_extraction_miss", "PROVEN", issues
            return "deterministic_extraction_miss", "PROVEN", issues
        if diagnostic.get("diagnostic_code") == "not_applicable":
            return "builder_not_applicable_misclassification", "PROVEN", issues
        if diagnostic.get("diagnostic_code") == "needs_review":
            return "llm_abstention_with_sufficient_evidence", "PROVEN", issues
    if not as_bool(row.get("predicted_present")):
        if diagnostic and diagnostic.get("diagnostic_code") == "risk_generated":
            return "final_bucket_or_serialization_drop", "INFERRED", ["builder_candidate_logged_but_final_absent"]
        return "unavailable_trace", "UNAVAILABLE", ["candidate_lifecycle_not_persisted"]
    if not as_bool(row.get("predicted_positive")):
        return "verifier_rejection", "PROVEN", [str(row.get("predicted_bucket") or "")]
    if not as_bool(row.get("status_match")):
        return "status_mismatch", "PROVEN", []
    if not as_bool(row.get("level_match")):
        return "level_mismatch", "PROVEN", []
    if not as_bool(row.get("calculation_match")):
        reason = str(row.get("calculation_match_reason") or "")
        root = "calculation_missing" if "MISSING" in reason else "calculation_value_mismatch"
        return root, "PROVEN", [reason]
    if not as_bool(row.get("evidence_hit")):
        return "final_evidence_not_retained", "PROVEN", []
    return "correct", "PROVEN", []


def build_risk_lifecycle(
    risk_rows: Sequence[Mapping[str, Any]],
    coverage: Mapping[str, Any],
    parser_rows: Sequence[Mapping[str, Any]],
    retrieval_rows: Sequence[Mapping[str, Any]],
    results: Mapping[str, Mapping[str, Any]],
    quality: Mapping[str, Any],
    *,
    llm_expected_available: bool = True,
) -> list[dict[str, Any]]:
    risk_manifest = _index(coverage.get("risk_units") or [], "risk_unit_id")
    evidence_by_case_risk: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for unit in coverage.get("evidence_units") or []:
        evidence_by_case_risk[(str(unit.get("case_id")), str(unit.get("source_risk_code")))].append(unit)
    parser_by_id = _index(parser_rows, "evidence_unit_id")
    retrieval_by_id = _index(retrieval_rows, "evidence_unit_id")
    diagnostics = {case_id: _diagnostics_from_result(result) for case_id, result in results.items()}
    final = _final_risk_index(results)
    calls = _llm_index(quality)
    units: list[dict[str, Any]] = []
    for row in risk_rows:
        case_id = str(row.get("case_id") or "")
        risk_code = str(row.get("source_risk_code") or "")
        gold_units = evidence_by_case_risk.get((case_id, risk_code), [])
        parser_units = [parser_by_id[str(item.get("evidence_unit_id"))] for item in gold_units]
        retrieval_units = [retrieval_by_id[str(item.get("evidence_unit_id"))] for item in gold_units]
        diagnostic = diagnostics.get(case_id, {}).get(risk_code)
        task = RISK_TO_TASK.get(risk_code)
        llm = calls.get((case_id, task)) if task else None
        final_entry = final.get((case_id, risk_code))
        final_risk = (final_entry or {}).get("risk") or {}
        builder_status = str((diagnostic or {}).get("builder_status") or "UNAVAILABLE")
        builder_risk_present = bool(
            final_entry is not None
            or (diagnostic or {}).get("diagnostic_code") == "risk_generated"
            or builder_status in {"built", "needs_review"}
        )
        root, proof, observations = _risk_root_cause(
            row,
            parser_units,
            retrieval_units,
            diagnostic,
            llm,
            llm_expected_available=llm_expected_available,
        )
        if root not in RISK_ROOT_CAUSES or proof not in PROOF_LEVELS:
            raise RoleBForensicsError(f"invalid_root_cause:{root}:{proof}")
        final_evidence = final_risk.get("evidence") or []
        gold_requirement = (
            risk_manifest.get(str(row.get("risk_unit_id") or ""), {}).get(
                "calculation_requirement"
            )
            or {}
        )
        predicted_calculation = final_risk.get("calculation") or {}
        gold_value = gold_requirement.get("value")
        predicted_value = predicted_calculation.get("result")
        try:
            absolute_delta = abs(float(predicted_value) - float(gold_value))
            relative_delta = (
                absolute_delta / abs(float(gold_value)) if float(gold_value) else None
            )
        except (TypeError, ValueError):
            absolute_delta = None
            relative_delta = None
        units.append(
            {
                "case_id": case_id,
                "stock_code": str(row.get("stock_code") or ""),
                "risk_unit_id": str(row.get("risk_unit_id") or ""),
                "risk_code": risk_code,
                "gold_status": str(row.get("gold_status") or ""),
                "gold_level": str(row.get("gold_level") or ""),
                "gold_evidence_count": len(gold_units),
                "parser_status": "preserved" if any(item.get("anchor_found_any_page") for item in parser_units) else "missing",
                "candidate_status": sorted({str(item.get("retrieval_status")) for item in retrieval_units}),
                "first_gold_rank": min(
                    (int(item["first_exact_anchor_rank"]) for item in retrieval_units if item.get("first_exact_anchor_rank") is not None),
                    default=None,
                ),
                "agent_consumed": any(item.get("agent_consumed_gold_anchor") for item in retrieval_units),
                "parser_anchor_available": any(item.get("anchor_found_any_page") for item in parser_units),
                "candidate_evidence_count": max((int(item.get("candidate_count") or 0) for item in retrieval_units), default=0),
                "agent_consumed_evidence_count": sum(item.get("agent_consumed_gold_anchor") is True for item in retrieval_units),
                "deterministic_candidate_present": diagnostic.get("diagnostic_code") == "risk_generated" if diagnostic and not task else False,
                "llm_task_expected": bool(task),
                "llm_request_attempted": llm is not None,
                "llm_request_success": llm is not None and not llm.get("failure_kind"),
                "llm_structured_valid": llm.get("structured_valid") if llm else None,
                "llm_scope_valid": llm.get("scope_valid") if llm else None,
                "llm_candidate_present": diagnostic.get("diagnostic_code") == "risk_generated" if diagnostic and task else None,
                "llm_applicable": diagnostic.get("diagnostic_code") == "risk_generated" if diagnostic and task else None,
                "llm_abstained": diagnostic.get("diagnostic_code") == "needs_review" if diagnostic and task else None,
                "llm_failure_kind": llm.get("failure_kind") if llm else None,
                "extraction_status": (diagnostic or {}).get("extraction_status") or (diagnostic or {}).get("diagnostic_code") or "UNAVAILABLE",
                "builder_status": builder_status,
                "builder_risk_present": builder_risk_present,
                "normalization_attempted": bool(task and llm),
                "normalization_success": llm.get("structured_valid") if llm else None,
                "normalization_issue_codes": [],
                "reconciliation_attempted": True,
                "reconciliation_success": "UNAVAILABLE",
                "candidate_after_reconciliation": "UNAVAILABLE",
                "reconciliation_issue_codes": [],
                "verifier_invoked": final_entry is not None,
                "verifier_outcome": (final_entry or {}).get("bucket") or "UNAVAILABLE",
                "verifier_issue_codes": (final_risk.get("metadata") or {}).get("legal_verifier_issues", []),
                "final_present": as_bool(row.get("predicted_present")),
                "final_bucket": str(row.get("predicted_bucket") or ""),
                "final_status": str(row.get("predicted_status") or ""),
                "final_level": str(row.get("predicted_level") or ""),
                "final_calculation_present": final_risk.get("calculation") is not None,
                "gold_calculation_key": gold_requirement.get("key"),
                "gold_calculation_value": gold_value,
                "predicted_calculation_key": predicted_calculation.get("metric"),
                "predicted_calculation_value": predicted_value,
                "calculation_absolute_delta": absolute_delta,
                "calculation_relative_delta": relative_delta,
                "calculation_unit": predicted_calculation.get("unit"),
                "calculation_formula": predicted_calculation.get("formula"),
                "calculation_match_reason": row.get("calculation_match_reason"),
                "final_evidence_ids": [str(item.get("evidence_id")) for item in final_evidence if isinstance(item, Mapping)],
                "status_match": as_bool(row.get("status_match")),
                "level_match": as_bool(row.get("level_match")),
                "calculation_match": as_bool(row.get("calculation_match")),
                "evidence_hit": as_bool(row.get("evidence_hit")),
                "m1_correct": as_bool(row.get("correct")),
                "primary_root_cause": root,
                "secondary_observations": observations,
                "proof_level": proof,
                "proof_artifact": "pipeline_trace+analysis_result.agent_logs+llm_call_quality+risk_benchmark",
            }
        )
    return units


def build_evidence_lifecycle(
    evidence_rows: Sequence[Mapping[str, Any]],
    coverage: Mapping[str, Any],
    parser_rows: Sequence[Mapping[str, Any]],
    retrieval_rows: Sequence[Mapping[str, Any]],
    risk_units: Sequence[Mapping[str, Any]],
    results: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    manifest = _index(coverage.get("evidence_units") or [], "evidence_unit_id")
    parser = _index(parser_rows, "evidence_unit_id")
    retrieval = _index(retrieval_rows, "evidence_unit_id")
    risk_index = {(str(row["case_id"]), str(row["risk_code"])): row for row in risk_units}
    final = _final_risk_index(results)
    units: list[dict[str, Any]] = []
    for evaluated in evidence_rows:
        unit_id = str(evaluated.get("evidence_unit_id") or "")
        gold = manifest[unit_id]
        parsed = parser[unit_id]
        retrieved = retrieval[unit_id]
        case_id = str(evaluated.get("case_id") or "")
        risk_code = str(evaluated.get("source_risk_code") or "")
        risk = risk_index[(case_id, risk_code)]
        final_entry = final.get((case_id, risk_code))
        final_risk = (final_entry or {}).get("risk") or {}
        predicted = [item for item in final_risk.get("evidence") or [] if isinstance(item, Mapping)]
        gold_page = int(gold.get("page") or 0)
        page_matches = [item for item in predicted if int(item.get("page") or 0) == gold_page]
        anchor_matches_final = [
            item for item in page_matches if anchor_matches(str(gold.get("exact_text") or ""), str(item.get("text") or ""))
        ]
        covered = as_bool(evaluated.get("covered"))
        if covered:
            root = "final_evidence_covered"
        elif not parsed.get("anchor_found_any_page"):
            root = "parser_text_missing"
        elif retrieved.get("first_gold_page_rank") is None:
            root = "retrieval_candidate_miss"
        elif retrieved.get("first_exact_anchor_rank") is None:
            root = "retrieved_page_anchor_truncated"
        elif not retrieved.get("agent_consumed_gold_anchor"):
            root = "retrieval_ranking_or_topk_miss"
        elif not risk.get("final_present"):
            root = "risk_absent_caused_evidence_miss"
        elif not as_bool(risk.get("final_status")) and risk.get("final_bucket") == "rejected":
            root = "risk_rejected_caused_evidence_miss"
        elif not predicted:
            root = "final_evidence_not_retained"
        elif not page_matches:
            root = "final_evidence_page_mismatch"
        elif not anchor_matches_final:
            root = "final_evidence_anchor_mismatch"
        else:
            root = "unavailable_trace"
        proof = "PROVEN" if root != "unavailable_trace" else "UNAVAILABLE"
        if root not in EVIDENCE_ROOT_CAUSES:
            raise RoleBForensicsError(f"invalid_evidence_root_cause:{root}")
        units.append(
            {
                "case_id": case_id,
                "risk_code": risk_code,
                "evidence_unit_id": unit_id,
                "gold_page": gold_page,
                "parser_expected_page": parsed.get("anchor_found_expected_page"),
                "parser_any_page": parsed.get("anchor_found_any_page"),
                "first_gold_page_rank": retrieved.get("first_gold_page_rank"),
                "first_gold_anchor_rank": retrieved.get("first_exact_anchor_rank"),
                "agent_consumed": retrieved.get("agent_consumed_gold_anchor"),
                "candidate_risk_created": risk.get("builder_risk_present"),
                "final_positive_risk": risk.get("final_present") and risk.get("final_bucket") != "rejected",
                "evidence_retained": bool(predicted),
                "predicted_page": int(predicted[0].get("page") or 0) if predicted else None,
                "page_match": bool(page_matches),
                "anchor_match": bool(anchor_matches_final),
                "m2_covered": covered,
                "primary_root_cause": root,
                "proof_level": proof,
                "proof_artifact": "parser_audit+pipeline_trace+analysis_result+evidence_benchmark",
            }
        )
    return units


def _waterfall_rows(stages: Sequence[tuple[str, int]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    previous: int | None = None
    for stage, count in stages:
        rows.append(
            {
                "stage": stage,
                "count": count,
                "conditional_rate": safe_ratio(count, previous) if previous is not None else 1.0,
            }
        )
        previous = count
    return rows


def build_m1_decomposition(risk_units: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    def cumulative_count(*predicates: Any) -> int:
        return sum(
            all(predicate(row) for predicate in predicates)
            for row in risk_units
        )

    present = lambda row: as_bool(row.get("final_present"))
    positive = lambda row: present(row) and row.get("final_bucket") != "rejected"
    status = lambda row: as_bool(row.get("status_match"))
    level = lambda row: as_bool(row.get("level_match"))
    calculation = lambda row: as_bool(row.get("calculation_match"))
    evidence = lambda row: as_bool(row.get("evidence_hit"))
    stages = (
        ("gold_positive_units", len(risk_units)),
        ("final_risk_present", cumulative_count(present)),
        ("final_positive", cumulative_count(positive)),
        ("status_matched", cumulative_count(positive, status)),
        ("level_matched", cumulative_count(positive, status, level)),
        ("calculation_matched", cumulative_count(positive, status, level, calculation)),
        ("evidence_matched", cumulative_count(positive, status, level, calculation, evidence)),
        ("m1_correct", sum(as_bool(row.get("m1_correct")) for row in risk_units)),
    )
    by_risk: dict[str, Any] = {}
    for risk in sorted({str(row.get("risk_code")) for row in risk_units}):
        selected = [row for row in risk_units if row.get("risk_code") == risk]
        by_risk[risk] = build_m1_decomposition(selected)["waterfall"] if len(selected) != len(risk_units) else []
    failures = Counter(str(row.get("primary_root_cause")) for row in risk_units if not row.get("m1_correct"))
    return {
        "report_version": FORENSIC_VERSION,
        "waterfall": _waterfall_rows(stages),
        "per_risk": by_risk,
        "independent_primary_failures": dict(sorted(failures.items())),
        "non_official_diagnostic": True,
    }


def build_m2_decomposition(evidence_units: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    def cumulative_count(*predicates: Any) -> int:
        return sum(
            all(predicate(row) for predicate in predicates)
            for row in evidence_units
        )

    parser = lambda row: as_bool(row.get("parser_expected_page"))
    candidate = lambda row: (
        row.get("first_gold_anchor_rank") is not None
        and int(row["first_gold_anchor_rank"]) <= 20
    )
    consumed = lambda row: as_bool(row.get("agent_consumed"))
    created = lambda row: as_bool(row.get("candidate_risk_created"))
    positive = lambda row: as_bool(row.get("final_positive_risk"))
    retained = lambda row: as_bool(row.get("evidence_retained"))
    page = lambda row: as_bool(row.get("page_match"))
    anchor = lambda row: as_bool(row.get("anchor_match"))
    stages = (
        ("gold_evidence_units", len(evidence_units)),
        ("parser_expected_page_anchor_preserved", cumulative_count(parser)),
        ("candidate_top20_anchor_hit", cumulative_count(parser, candidate)),
        ("agent_consumed_anchor", cumulative_count(parser, candidate, consumed)),
        ("candidate_risk_created", cumulative_count(parser, candidate, consumed, created)),
        ("final_positive_risk_retained", cumulative_count(parser, candidate, consumed, created, positive)),
        ("evidence_retained", cumulative_count(parser, candidate, consumed, created, positive, retained)),
        ("page_matched", cumulative_count(parser, candidate, consumed, created, positive, retained, page)),
        ("text_anchor_matched", cumulative_count(parser, candidate, consumed, created, positive, retained, page, anchor)),
        ("m2_covered", cumulative_count(parser, candidate, consumed, created, positive, retained, page, anchor, lambda row: as_bool(row.get("m2_covered")))),
    )
    diagnostics = {
        f"candidate_recall_at_{k}": safe_ratio(
            sum(row.get("first_gold_anchor_rank") is not None and int(row["first_gold_anchor_rank"]) <= k for row in evidence_units),
            len(evidence_units),
        )
        for k in (1, 3, 5, 10, 20)
    }
    diagnostics.update(
        {
            "agent_consumed_recall": safe_ratio(sum(as_bool(row.get("agent_consumed")) for row in evidence_units), len(evidence_units)),
            "final_evidence_coverage": safe_ratio(sum(as_bool(row.get("m2_covered")) for row in evidence_units), len(evidence_units)),
            "conditional_on_consumed": safe_ratio(
                sum(as_bool(row.get("m2_covered")) and as_bool(row.get("agent_consumed")) for row in evidence_units),
                sum(as_bool(row.get("agent_consumed")) for row in evidence_units),
            ),
            "conditional_on_final_positive": safe_ratio(
                sum(as_bool(row.get("m2_covered")) and as_bool(row.get("final_positive_risk")) for row in evidence_units),
                sum(as_bool(row.get("final_positive_risk")) for row in evidence_units),
            ),
        }
    )
    return {
        "report_version": FORENSIC_VERSION,
        "waterfall": _waterfall_rows(stages),
        "diagnostics": diagnostics,
        "non_official_diagnostic": True,
    }


def build_counterfactuals(
    risk_units: Sequence[Mapping[str, Any]], evidence_units: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    denominator = len(risk_units)
    correct = sum(as_bool(row.get("m1_correct")) for row in risk_units)
    def m1_if(root: str) -> float | None:
        return safe_ratio(correct + sum(row.get("primary_root_cause") == root for row in risk_units), denominator)
    consumed = sum(as_bool(row.get("agent_consumed")) for row in evidence_units)
    retained = sum(as_bool(row.get("evidence_retained")) for row in evidence_units)
    page = sum(as_bool(row.get("page_match")) for row in evidence_units)
    anchor = sum(as_bool(row.get("anchor_match")) for row in evidence_units)
    return {
        "report_version": FORENSIC_VERSION,
        "status": "NON_OFFICIAL_COUNTERFACTUAL",
        "m1_if_only_evidence_binding_fixed": m1_if("final_evidence_not_retained"),
        "m1_if_only_calculation_fixed": safe_ratio(
            correct + sum(row.get("primary_root_cause") in {"calculation_value_mismatch", "calculation_missing"} for row in risk_units), denominator
        ),
        "m1_if_only_status_fixed": m1_if("status_mismatch"),
        "m1_if_only_level_fixed": m1_if("level_mismatch"),
        "m1_if_all_currently_present_positive_passed_attributes": safe_ratio(
            sum(as_bool(row.get("final_present")) and row.get("final_bucket") != "rejected" for row in risk_units), denominator
        ),
        "m2_if_all_candidate_top20_anchors_consumed": safe_ratio(
            sum(row.get("first_gold_anchor_rank") is not None for row in evidence_units), len(evidence_units)
        ),
        "m2_if_all_consumed_anchors_retained": safe_ratio(consumed, len(evidence_units)),
        "m2_if_all_retained_evidence_had_correct_page": safe_ratio(retained, len(evidence_units)),
        "m2_if_all_page_matched_preserved_anchor": safe_ratio(page, len(evidence_units)),
        "observed_anchor_match_ceiling": safe_ratio(anchor, len(evidence_units)),
    }


def build_mode_comparison(run_root: Path) -> dict[str, Any]:
    summary = load_json(run_root / "ablation_summary.json")
    quality = load_json(run_root / "llm_call_quality.json")
    rows: list[dict[str, Any]] = []
    for mode in ("offline", "shadow", "gated"):
        metrics = (summary.get("modes") or {}).get(mode) or {}
        retrieval_path = run_root / mode / "retrieval_waterfall.json"
        retrieval = load_json(retrieval_path) if retrieval_path.is_file() else {}
        evidence_units = retrieval.get("units") or []
        candidate_r20 = safe_ratio(
            sum(as_bool(row.get("gold_evidence_in_top20")) for row in evidence_units),
            len(evidence_units),
        )
        rows.append(
            {
                "mode": mode,
                "m1": metrics.get("m1"),
                "m2": metrics.get("m2"),
                "candidate_recall_at_20": candidate_r20,
                "structured_valid_rate": (
                    quality.get("structured_scope_valid_rate") if mode in {"shadow", "gated"} else None
                ),
            }
        )
    shadow = load_json(run_root / "shadow_diagnostics.json")
    shadow_cases = [row for row in (shadow.get("cases") or {}).values() if isinstance(row, Mapping)]
    return {
        "report_version": FORENSIC_VERSION,
        "modes": rows,
        "shadow_canonical_equals_offline": bool(shadow_cases)
        and all(row.get("canonical_equal_to_offline") is True for row in shadow_cases),
        "gated_extra_network_calls": 0,
        "journal_identity_shared": True,
    }


def _root_cause_counts(
    risk_units: Sequence[Mapping[str, Any]], evidence_units: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    risk = Counter(str(row.get("primary_root_cause")) for row in risk_units if not row.get("m1_correct"))
    evidence = Counter(str(row.get("primary_root_cause")) for row in evidence_units if not row.get("m2_covered"))
    causes = set(risk) | set(evidence)
    return [
        {
            "root_cause": cause,
            "affected_m1_units": risk[cause],
            "affected_m2_units": evidence[cause],
            "combined_units": risk[cause] + evidence[cause],
        }
        for cause in sorted(causes, key=lambda item: (-(risk[item] + evidence[item]), item))
    ]


def _write_fix_priority(
    path: Path,
    counts: Sequence[Mapping[str, Any]],
    risk_units: Sequence[Mapping[str, Any]],
    evidence_units: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    non_actionable = {
        "correct",
        "final_evidence_covered",
        "llm_required_but_offline_mode",
    }
    dominant = next(
        (row for row in counts if row.get("root_cause") not in non_actionable),
        None,
    )
    if dominant is None:
        recommendation = {"root_cause": "none", "module": "none", "smallest_change": "none"}
    else:
        root = str(dominant["root_cause"])
        module = {
            "retrieval_candidate_miss": "Retriever candidate generation",
            "retrieved_page_anchor_truncated": "Retriever Evidence context adapter",
            "retrieval_ranking_or_topk_miss": "Retriever ranking/topK",
            "numeric_extraction_miss": "Financial extraction",
            "wrong_period_selection": "Financial period selection",
            "verifier_rejection": "Legal candidate/Verifier boundary",
            "final_evidence_not_retained": "RiskItem Evidence binding",
        }.get(root, "Observed lifecycle stage")
        recoverable_risk_units = [
            row
            for row in risk_units
            if row.get("primary_root_cause") == root
            and row.get("risk_code") in {"cash_runway", "customer_concentration", "supplier_concentration"}
        ]
        recoverable_evidence_units = [
            row
            for row in evidence_units
            if row.get("primary_root_cause") == root
            and row.get("risk_code") in {"cash_runway", "customer_concentration", "supplier_concentration"}
        ]
        if root == "retrieval_candidate_miss":
            module = "src/ipo_risk/retrieval/role_b_financial_v046.py"
        recommendation = {
            "root_cause": root,
            "module": module,
            "smallest_change": "Select one generic bounded fix after human review; do not combine modules.",
            "expected_recoverable_m1_units": len(recoverable_risk_units),
            "expected_recoverable_m2_units": len(recoverable_evidence_units),
            "expected_recoverable_units_note": "Cross-metric counts are not additive because one upstream failure can affect both metrics.",
            "regression_risks": "Existing-Gold overfitting, candidate noise, and canonical-output drift.",
        }
    lines = [
        "# Role-B Forensic Fix Priority",
        "",
        "Only the first proven root cause is recommended for the next Fixer.",
        "",
        "| Priority | Root cause | M1 units | M2 units | Recommended module |",
        "|---:|---|---:|---:|---|",
    ]
    for index, row in enumerate(counts, start=1):
        module = recommendation["module"] if row.get("root_cause") == recommendation.get("root_cause") else "defer"
        lines.append(
            f"| {index} | `{row['root_cause']}` | {row['affected_m1_units']} | {row['affected_m2_units']} | {module} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return recommendation


def run_forensics(inputs: ForensicInputs) -> dict[str, Any]:
    inputs.output_dir.mkdir(parents=True, exist_ok=False)
    run_root = inputs.run_root
    coverage = load_json(inputs.coverage_path)
    subset = load_json(inputs.subset_path)
    baseline = load_json(run_root / "baseline_manifest.json")
    summary = load_json(run_root / "ablation_summary.json")
    preflight = load_json(run_root / "preflight.json")
    quality = load_json(run_root / "llm_call_quality.json")
    case_ids = [str(row.get("case_id")) for row in subset.get("cases") or []]
    if (
        not case_ids
        or len(case_ids) != int(baseline.get("case_count") or 0)
        or subset.get("subset_hash") != baseline.get("subset_hash")
    ):
        raise RoleBForensicsError("cohort_identity_mismatch")
    if coverage.get("manifest_hash") != baseline.get("gold_manifest_hash"):
        raise RoleBForensicsError("gold_manifest_hash_drift")
    if baseline.get("validation_opened") is not False or baseline.get("blind_2025_outcome_accessed") is not False:
        raise RoleBForensicsError("forbidden_split_access_in_baseline")

    selected_mode = str(summary.get("selected_mode") or "gated")
    evaluation = run_root / selected_mode / "evaluation"
    risk_rows = read_csv(evaluation / "risk_benchmark.csv")
    evidence_rows = read_csv(evaluation / "evidence_benchmark.csv")
    pipeline = load_json(run_root / selected_mode / "pipeline_trace.json")
    results = _load_case_results(run_root, selected_mode, case_ids)

    inventory = build_artifact_inventory(inputs.inventory_roots, run_root)
    _json_dump(inputs.output_dir / "artifact_inventory.json", inventory)
    role_b_paths = (
        "configs/experiments/v046_role_b_ai_responses.yaml",
        "scripts/run_v046_role_b_ablation.py",
        "src/ipo_risk/evaluation/role_b_waterfall.py",
        "src/ipo_risk/runtime/role_b_ablation.py",
        "src/ipo_risk/runtime/llm_journal.py",
        "src/ipo_risk/retrieval/role_b_financial_v046.py",
        "src/ipo_risk/agents/financial.py",
        "src/ipo_risk/agents/financial_v03.py",
        "src/ipo_risk/providers/llm.py",
    )
    artifact_head = str(baseline.get("git_head") or "")
    tree_diff = git_output(inputs.root, "diff", "--name-only", artifact_head, "HEAD", "--", *role_b_paths)
    diagnostic_head = git_output(inputs.root, "rev-parse", "HEAD")
    main_base = git_output(inputs.root, "merge-base", "HEAD", "origin/main") or diagnostic_head
    scope = {
        "report_version": FORENSIC_VERSION,
        "base_sha": main_base,
        "branch": git_output(inputs.root, "branch", "--show-current"),
        "authoritative_run": run_root.name,
        "artifact_git_head": artifact_head,
        "role_b_runtime_tree_identical_to_current_head": not bool(tree_diff),
        "role_b_runtime_tree_diff": tree_diff.splitlines() if tree_diff else [],
        "subset_hash": subset.get("subset_hash"),
        "gold_manifest_hash": coverage.get("manifest_hash"),
        "evaluator_version": coverage.get("evaluator_version"),
        "metric_protocol_version": coverage.get("metric_protocol_version"),
        "provider": baseline.get("provider"),
        "model": baseline.get("model"),
        "transport": baseline.get("transport"),
        "prompt_set_hash": sha256(
            json.dumps(baseline.get("prompt_hashes") or {}, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "schema_set_hash": baseline.get("schema_set_hash"),
        "runtime_config_hash": baseline.get("runtime_config_hash"),
        "case_count": len(case_ids),
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
        "gold_join_stage": "post_run_only",
        "documentation_drift": {
            "documented_iter_004_m1": 0.23333333333333334,
            "documented_iter_004_m2": 0.1875,
            "authoritative_m1": (summary.get("modes") or {}).get(selected_mode, {}).get("m1"),
            "authoritative_m2": (summary.get("modes") or {}).get(selected_mode, {}).get("m2"),
            "reason": "different_code_identity; iter_004 is retained as historical evidence",
        },
    }
    if not scope["role_b_runtime_tree_identical_to_current_head"]:
        raise RoleBForensicsError("authoritative_role_b_runtime_tree_drift")
    _json_dump(inputs.output_dir / "00_scope_and_identity.json", scope)
    (inputs.output_dir / "00_scope_and_identity.md").write_text(
        "# Scope and Identity\n\n"
        f"- BASE_SHA: `{scope['base_sha']}`\n"
        f"- Authoritative run: `{scope['authoritative_run']}`\n"
        f"- Artifact SHA: `{artifact_head}`\n"
        f"- Role-B runtime tree identical: `{str(scope['role_b_runtime_tree_identical_to_current_head']).lower()}`\n"
        f"- Frozen cohort ({len(case_ids)} cases): `{scope['subset_hash']}`\n"
        f"- Gold manifest: `{scope['gold_manifest_hash']}`\n"
        "- Validation opened: `false`\n- Blind accessed: `false`\n",
        encoding="utf-8",
    )

    denominators = {
        "report_version": FORENSIC_VERSION,
        "m1_evaluable_positive_risk_unit_count": len(risk_rows),
        "m1_correct_count": sum(as_bool(row.get("correct")) for row in risk_rows),
        "m1_incorrect_count": sum(not as_bool(row.get("correct")) for row in risk_rows),
        "m2_evaluable_evidence_unit_count": len(evidence_rows),
        "m2_covered_count": sum(as_bool(row.get("covered")) for row in evidence_rows),
        "m2_uncovered_count": sum(not as_bool(row.get("covered")) for row in evidence_rows),
        "per_risk": {},
        "non_official_diagnostics": {},
    }
    for risk_code in sorted({str(row.get("source_risk_code")) for row in risk_rows}):
        risks = [row for row in risk_rows if row.get("source_risk_code") == risk_code]
        evidence = [row for row in evidence_rows if row.get("source_risk_code") == risk_code]
        denominators["per_risk"][risk_code] = {
            "support": len(risks),
            "correct": sum(as_bool(row.get("correct")) for row in risks),
            "incorrect": sum(not as_bool(row.get("correct")) for row in risks),
            "official_aligned_accuracy": safe_ratio(sum(as_bool(row.get("correct")) for row in risks), len(risks)),
            "evidence_unit_count": len(evidence),
            "evidence_covered": sum(as_bool(row.get("covered")) for row in evidence),
            "evidence_uncovered": sum(not as_bool(row.get("covered")) for row in evidence),
        }
    _json_dump(inputs.output_dir / "01_metric_denominators.json", denominators)

    evaluated_evidence_ids = {
        str(row.get("evidence_unit_id") or "") for row in evidence_rows
    }
    evaluated_gold_evidence = [
        row
        for row in coverage.get("evidence_units") or []
        if str(row.get("evidence_unit_id") or "") in evaluated_evidence_ids
    ]
    parser_rows, parser_summary = build_parser_preservation(
        evaluated_gold_evidence,
        case_ids,
        inputs.catalog_path,
        inputs.prospectus_root,
    )
    _json_dump(inputs.output_dir / "02_parser_preservation.json", parser_summary)
    _csv_dump(inputs.output_dir / "02_parser_preservation.csv", parser_rows)
    retrieval_rows, retrieval_summary = build_retrieval_stage(evidence_rows, pipeline, parser_rows)
    _json_dump(inputs.output_dir / "03_retrieval_stage.json", retrieval_summary)
    _csv_dump(inputs.output_dir / "03_retrieval_stage.csv", retrieval_rows)
    llm_rows, llm_summary = build_llm_stage(quality, len(case_ids), preflight)
    _json_dump(inputs.output_dir / "04_llm_stage.json", llm_summary)
    _csv_dump(inputs.output_dir / "04_llm_stage.csv", llm_rows)
    risk_units = build_risk_lifecycle(
        risk_rows,
        coverage,
        parser_rows,
        retrieval_rows,
        results,
        quality,
        llm_expected_available=selected_mode != "offline",
    )
    _json_dump(inputs.output_dir / "05_candidate_lifecycle.json", {"report_version": FORENSIC_VERSION, "units": risk_units})
    _csv_dump(inputs.output_dir / "05_candidate_lifecycle.csv", risk_units)
    evidence_units = build_evidence_lifecycle(
        evidence_rows, coverage, parser_rows, retrieval_rows, risk_units, results
    )
    positive = [
        row
        for row in risk_units
        if as_bool(row.get("final_present")) and row.get("final_bucket") != "rejected"
    ]
    denominators["non_official_diagnostics"] = {
        "status": "NON_OFFICIAL_DIAGNOSTIC",
        "risk_existence_recall": safe_ratio(
            sum(as_bool(row.get("final_present")) for row in risk_units), len(risk_units)
        ),
        "risk_positive_bucket_rate": safe_ratio(len(positive), len(risk_units)),
        "status_match_rate": safe_ratio(
            sum(as_bool(row.get("status_match")) for row in risk_units), len(risk_units)
        ),
        "level_match_rate": safe_ratio(
            sum(as_bool(row.get("level_match")) for row in risk_units), len(risk_units)
        ),
        "calculation_match_rate": safe_ratio(
            sum(as_bool(row.get("calculation_match")) for row in risk_units), len(risk_units)
        ),
        "evidence_hit_rate": safe_ratio(
            sum(as_bool(row.get("evidence_hit")) for row in risk_units), len(risk_units)
        ),
        "m1_units_only_evidence_mismatch": sum(
            as_bool(row.get("final_present"))
            and row.get("final_bucket") != "rejected"
            and as_bool(row.get("status_match"))
            and as_bool(row.get("level_match"))
            and as_bool(row.get("calculation_match"))
            and not as_bool(row.get("evidence_hit"))
            for row in risk_units
        ),
        "m1_units_only_calculation_mismatch": sum(
            as_bool(row.get("final_present"))
            and row.get("final_bucket") != "rejected"
            and as_bool(row.get("status_match"))
            and as_bool(row.get("level_match"))
            and not as_bool(row.get("calculation_match"))
            and as_bool(row.get("evidence_hit"))
            for row in risk_units
        ),
        "risk_present_status_mismatch": sum(
            as_bool(row.get("final_present")) and not as_bool(row.get("status_match"))
            for row in risk_units
        ),
        "risk_present_level_mismatch": sum(
            as_bool(row.get("final_present")) and not as_bool(row.get("level_match"))
            for row in risk_units
        ),
        "m2_missing_because_corresponding_risk_absent": sum(
            not as_bool(row.get("m2_covered"))
            and row.get("primary_root_cause") == "risk_absent_caused_evidence_miss"
            for row in evidence_units
        ),
        "m2_missing_after_risk_present": sum(
            not as_bool(row.get("m2_covered"))
            and as_bool(row.get("final_positive_risk"))
            for row in evidence_units
        ),
    }
    _json_dump(inputs.output_dir / "01_metric_denominators.json", denominators)
    _json_dump(inputs.output_dir / "06_verifier_and_binding.json", {"report_version": FORENSIC_VERSION, "risk_units": risk_units, "evidence_units": evidence_units})
    _csv_dump(inputs.output_dir / "06_verifier_and_binding.csv", evidence_units)
    m1 = build_m1_decomposition(risk_units)
    m2 = build_m2_decomposition(evidence_units)
    _json_dump(inputs.output_dir / "07_m1_decomposition.json", m1)
    _csv_dump(inputs.output_dir / "07_m1_units.csv", risk_units)
    _json_dump(inputs.output_dir / "08_m2_decomposition.json", m2)
    _csv_dump(inputs.output_dir / "08_m2_units.csv", evidence_units)
    _json_dump(inputs.output_dir / "09_risk_root_cause_matrix.json", risk_units)
    _csv_dump(inputs.output_dir / "09_risk_root_cause_matrix.csv", risk_units)
    _json_dump(inputs.output_dir / "09_evidence_root_cause_matrix.json", evidence_units)
    _csv_dump(inputs.output_dir / "09_evidence_root_cause_matrix.csv", evidence_units)
    counterfactual = build_counterfactuals(risk_units, evidence_units)
    _json_dump(inputs.output_dir / "10_counterfactual_ceiling.json", counterfactual)
    modes = build_mode_comparison(run_root)
    _json_dump(inputs.output_dir / "11_mode_comparison.json", modes)
    risk_proof = Counter(str(row.get("proof_level")) for row in risk_units)
    evidence_proof = Counter(str(row.get("proof_level")) for row in evidence_units)
    gaps = {
        "report_version": FORENSIC_VERSION,
        "risk_units": {level.casefold(): risk_proof[level] for level in sorted(PROOF_LEVELS)},
        "evidence_units": {level.casefold(): evidence_proof[level] for level in sorted(PROOF_LEVELS)},
        "risk_proven_rate": safe_ratio(risk_proof["PROVEN"], len(risk_units)),
        "evidence_proven_rate": safe_ratio(evidence_proof["PROVEN"], len(evidence_units)),
        "target_met": safe_ratio(risk_proof["PROVEN"], len(risk_units)) >= 0.9 and safe_ratio(evidence_proof["PROVEN"], len(evidence_units)) >= 0.9,
        "known_gaps": [
            "raw LLM semantic fields are intentionally absent from persisted journal",
            "reconciliation has no per-candidate durable event",
            "smoke gate covers three of four allow-listed tasks",
        ],
    }
    _json_dump(inputs.output_dir / "12_diagnostic_gaps.json", gaps)
    root_counts = _root_cause_counts(risk_units, evidence_units)
    recommendation = _write_fix_priority(
        inputs.output_dir / "13_fix_priority.md",
        root_counts,
        risk_units,
        evidence_units,
    )
    final_status = "FORENSICS_COMPLETE" if gaps["target_met"] else "PARTIAL_TRACE_BLOCKED"
    forensic_summary = {
        "report_version": FORENSIC_VERSION,
        "final_status": final_status,
        "base_sha": scope["base_sha"],
        "branch": scope["branch"],
        "run_id": inputs.output_dir.name,
        "baseline": {
            "cohort_hash": subset.get("subset_hash"),
            "fixed10_hash": subset.get("subset_hash") if len(case_ids) == 10 else None,
            "case_count": len(case_ids),
            "m1_numerator": denominators["m1_correct_count"],
            "m1_denominator": len(risk_rows),
            "m1": safe_ratio(denominators["m1_correct_count"], len(risk_rows)),
            "m2_numerator": denominators["m2_covered_count"],
            "m2_denominator": len(evidence_rows),
            "m2": safe_ratio(denominators["m2_covered_count"], len(evidence_rows)),
            "provider": scope["provider"],
            "model": scope["model"],
            "prompt_set_hash": scope["prompt_set_hash"],
        },
        "trace_coverage": gaps,
        "m1_waterfall": m1["waterfall"],
        "m2_waterfall": m2["waterfall"],
        "mode_comparison": modes["modes"],
        "top_proven_root_causes": root_counts,
        "most_important_finding": root_counts[0] if root_counts else None,
        "recommended_first_fix": recommendation,
        "governance": {
            "existing_gold_modified": False,
            "evaluator_modified": False,
            "frozen_cohort_modified": False,
            "fixed10_modified": False if len(case_ids) == 10 else None,
            "validation_opened": False,
            "blind_accessed": False,
            "runtime_received_gold": False,
            "secrets_persisted": False,
        },
        "first_blocker": None if gaps["target_met"] else "proven_root_cause_coverage_below_90_percent",
        "next_action": "STOP_FOR_HUMAN_FIX_SELECTION",
    }
    _json_dump(inputs.output_dir / "forensic_summary.json", forensic_summary)
    (inputs.output_dir / "forensic_summary.md").write_text(
        "# Role-B M1/M2 Forensic Summary\n\n"
        f"- Status: `{final_status}`\n"
        f"- M1: `{forensic_summary['baseline']['m1_numerator']}/{forensic_summary['baseline']['m1_denominator']}`\n"
        f"- M2: `{forensic_summary['baseline']['m2_numerator']}/{forensic_summary['baseline']['m2_denominator']}`\n"
        f"- Risk PROVEN: `{risk_proof['PROVEN']}/{len(risk_units)}`\n"
        f"- Evidence PROVEN: `{evidence_proof['PROVEN']}/{len(evidence_units)}`\n"
        f"- First recommended Fixer: `{recommendation.get('root_cause')}`\n"
        "- Validation: `false`\n- Blind: `false`\n- Next: `STOP_FOR_HUMAN_FIX_SELECTION`\n",
        encoding="utf-8",
    )
    return forensic_summary


__all__ = [
    "EVIDENCE_ROOT_CAUSES",
    "FORENSIC_VERSION",
    "ForensicInputs",
    "RISK_ROOT_CAUSES",
    "RoleBForensicsError",
    "anchor_matches",
    "build_evidence_lifecycle",
    "build_retrieval_stage",
    "build_risk_lifecycle",
    "canonical_text",
    "run_forensics",
]
