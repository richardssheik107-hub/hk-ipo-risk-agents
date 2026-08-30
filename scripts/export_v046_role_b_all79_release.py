#!/usr/bin/env python3
"""Export the final ALL79 Role-B run as a compact repository-safe receipt.

The source run is intentionally local and ignored because it contains full
analysis payloads, runtime caches, and private LLM journals.  This exporter
copies only an explicit allowlist of benchmark and governance artifacts after
checking them for raw prompts/responses, secrets, evidence text, PDFs, and
local home paths.
"""

from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from ipo_risk.runtime.llm_journal import LLMJournalRecord


EXPORT_VERSION = "v046_role_b_all79_release_receipt_v1"
DEFAULT_OUTPUT = Path("reports/v045_role_b")

ROOT_EXPORTS = {
    "gated/evaluation/document_benchmark_summary.json": "document_benchmark_summary.json",
    "gated/evaluation/risk_benchmark.csv": "risk_benchmark.csv",
    "gated/evaluation/evidence_benchmark.csv": "evidence_benchmark.csv",
}

DETAIL_EXPORTS = {
    "ablation_summary.json": "ablation_summary.json",
    "baseline_manifest.json": "baseline_manifest.json",
    "best_iteration.json": "best_iteration.json",
    "case_statuses.json": "case_statuses.json",
    "failure_focus.json": "failure_focus.json",
    "llm_call_quality.json": "llm_call_quality.json",
    "monotonicity_report.json": "monotonicity_report.json",
    "gated/pipeline_trace.json": "gated_pipeline_trace.json",
    "gated/retrieval_waterfall.json": "gated_retrieval_waterfall.json",
    "gated/risk_pipeline_waterfall.json": "gated_risk_pipeline_waterfall.json",
    "offline/evaluation/document_benchmark_summary.json": "offline_document_benchmark_summary.json",
    "offline/evaluation/risk_benchmark.csv": "offline_risk_benchmark.csv",
    "offline/evaluation/evidence_benchmark.csv": "offline_evidence_benchmark.csv",
    "offline/pipeline_trace.json": "offline_pipeline_trace.json",
    "offline/retrieval_waterfall.json": "offline_retrieval_waterfall.json",
    "offline/risk_pipeline_waterfall.json": "offline_risk_pipeline_waterfall.json",
}

FORBIDDEN_VALUE_KEYS = frozenset(
    {
        "raw_prompt",
        "raw_response",
        "structured_payload",
        "prompt_text",
        "response_text",
        "api_key_value",
        "authorization",
        "prospectus_path",
        "local_path",
        "evidence_text",
        "exact_text",
        "company_name",
        "issuer_name",
    }
)
RISK_BENCHMARK_COLUMNS = (
    "risk_unit_id",
    "case_id",
    "stock_code",
    "split",
    "source_manifest_key",
    "source_annotation_hash",
    "source_risk_code",
    "competition_risk_family",
    "gold_status",
    "gold_level",
    "predicted_present",
    "predicted_positive",
    "predicted_bucket",
    "predicted_status",
    "predicted_level",
    "status_match",
    "level_match",
    "calculation_match",
    "calculation_match_reason",
    "evidence_required",
    "evidence_hit",
    "correct",
    "failure_reason",
)
EVIDENCE_BENCHMARK_COLUMNS = (
    "evidence_unit_id",
    "case_id",
    "stock_code",
    "split",
    "source_manifest_key",
    "source_annotation_hash",
    "source_risk_code",
    "competition_risk_family",
    "page",
    "exact_text_hash",
    "evidence_role",
    "requirement",
    "source_authority",
    "covered",
    "rank",
    "predicted_evidence_count",
)
FORBIDDEN_STRING_PATTERNS = (
    re.compile(r"(?i)bearer\s+[0-9a-z._-]{12,}"),
    re.compile(r"(?i)sk-[0-9a-z_-]{16,}"),
    re.compile(r"(?i)[A-Z]:[\\/](?:Users|Documents and Settings)[\\/]"),
    re.compile(r"/(?:Users|home)/[^/\s]+/"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
)


def _sha256_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256_bytes(encoded)


def _inspect_value(value: Any, *, source: Path, trail: tuple[str, ...] = ()) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).casefold()
            # Governance flags such as raw_response_persisted=false and fields
            # such as exact_text_hash are safe; only raw values are forbidden.
            if lowered in FORBIDDEN_VALUE_KEYS:
                location = ".".join((*trail, str(key)))
                raise ValueError(f"forbidden JSON field in {source}: {location}")
            _inspect_value(item, source=source, trail=(*trail, str(key)))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _inspect_value(item, source=source, trail=(*trail, str(index)))
    elif isinstance(value, str):
        for pattern in FORBIDDEN_STRING_PATTERNS:
            if pattern.search(value):
                location = ".".join(trail)
                raise ValueError(f"forbidden string in {source}: {location}")


def _validate_json(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    _inspect_value(payload, source=path)


def _validate_csv(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for pattern in FORBIDDEN_STRING_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"forbidden string in {path}")
    reader = csv.DictReader(text.splitlines())
    ordered_fields = tuple(str(item) for item in (reader.fieldnames or []))
    expected_fields = (
        EVIDENCE_BENCHMARK_COLUMNS
        if path.name.endswith("evidence_benchmark.csv")
        else RISK_BENCHMARK_COLUMNS
        if path.name.endswith("risk_benchmark.csv")
        else None
    )
    if expected_fields is None or ordered_fields != expected_fields:
        raise ValueError(f"unexpected CSV schema in {path}: {ordered_fields}")
    fields = {item.casefold() for item in ordered_fields}
    if fields & FORBIDDEN_VALUE_KEYS:
        raise ValueError(f"forbidden CSV columns in {path}: {sorted(fields & FORBIDDEN_VALUE_KEYS)}")


def _copy_safe(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.suffix.casefold() == ".json":
        _validate_json(source)
    elif source.suffix.casefold() == ".csv":
        _validate_csv(source)
    else:
        raise ValueError(f"unsupported export type: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        source.read_text(encoding="utf-8"),
        encoding="utf-8",
        newline="\n",
    )


def _gold_receipt(source: Path) -> dict[str, Any]:
    payload = json.loads(source.read_text(encoding="utf-8"))
    required = {
        "manifest_hash",
        "metric_protocol_version",
        "new_manual_annotations_added",
        "existing_gold_modified",
        "blind_2025_outcome_accessed",
        "source_governance",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"Existing-Gold manifest lacks required fields: {missing}")
    receipt_keys = (
        "blind_2025_outcome_accessed",
        "evaluable_development_case_count",
        "evaluable_validation_case_count",
        "evaluator_version",
        "evidence_unit_count",
        "existing_gold_modified",
        "existing_gold_source",
        "manifest_hash",
        "metric_protocol_version",
        "new_manual_annotations_added",
        "official_existing_gold_case_count",
        "positive_development_case_count",
        "positive_risk_unit_count",
        "positive_validation_case_count",
        "primary_evidence_unit_count",
        "primary_positive_risk_unit_count",
        "primary_risk_support",
        "risk_unit_count",
        "source_governance",
    )
    receipt = {key: payload.get(key) for key in receipt_keys}
    receipt.update(
        {
            "manifest_version": "v045_existing_gold_evaluable_manifest_metadata_receipt_v1",
            "artifact_scope": "metadata_receipt_only",
            "source_full_manifest_sha256": _sha256(source),
            "source_full_manifest_included": False,
            "risk_units_included": False,
            "evidence_units_included": False,
            "exact_evidence_text_included": False,
        }
    )
    _inspect_value(receipt, source=source)
    return receipt


def _llm_call_manifest(source_run: Path) -> dict[str, Any]:
    """Project private journal records to hash-only provider-call provenance."""

    journal_dir = source_run / "journal"
    journal_receipt_path = source_run / "journal_manifest.json"
    if not journal_dir.is_dir() or not journal_receipt_path.is_file():
        raise FileNotFoundError("ALL79 journal directory or manifest is missing")
    journal_receipt = json.loads(journal_receipt_path.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    source_receipt_records: list[dict[str, Any]] = []
    for path in sorted(journal_dir.glob("*.json"), key=lambda item: item.name):
        payload = json.loads(path.read_text(encoding="utf-8"))
        try:
            verified = LLMJournalRecord.model_validate(payload)
            verified.verify(verified.identity)
        except Exception as exc:
            raise ValueError(f"invalid governed journal record: {path.name}") from exc
        identity = verified.identity.model_dump(mode="json")

        source_receipt_records.append(
            {
                "identity_hash": payload.get("identity_hash"),
                "record_hash": payload.get("record_hash"),
                "case_id": identity.get("case_id"),
                "task_name": identity.get("task_name"),
                "prompt_version": identity.get("prompt_version"),
                "prompt_hash": identity.get("prompt_hash"),
                "response_schema_hash": identity.get("response_schema_hash"),
                "runtime_config_hash": identity.get("runtime_config_hash"),
                "allowed_evidence_count": len(identity.get("ordered_allowed_evidence_ids") or []),
                "provider": identity.get("provider"),
                "model": identity.get("model"),
                "outcome": payload.get("outcome"),
                "structured_valid": payload.get("structured_valid"),
                "scope_valid": payload.get("scope_valid"),
                "out_of_scope_ids": list(payload.get("out_of_scope_ids") or []),
                "failure_kind": payload.get("failure_kind"),
                "attempt_count": payload.get("attempt_count"),
                "transport_retry_count": payload.get("transport_retry_count"),
                "structured_correction_count": payload.get("structured_correction_count"),
                "latency_ms": payload.get("latency_ms"),
                "token_usage": dict(payload.get("token_usage") or {}),
            }
        )
        record = {
            "identity_hash": payload.get("identity_hash"),
            "case_id": identity.get("case_id"),
            "dataset_split": identity.get("dataset_split"),
            "task_name": identity.get("task_name"),
            "provider_name": identity.get("provider"),
            "model_name": identity.get("model"),
            "transport": identity.get("transport"),
            "prompt_version": identity.get("prompt_version"),
            "prompt_hash": identity.get("prompt_hash"),
            "response_schema_hash": identity.get("response_schema_hash"),
            "runtime_config_hash": identity.get("runtime_config_hash"),
            "request_id_hash": payload.get("request_id_hash"),
            "raw_response_hash": payload.get("response_hash"),
            "record_hash": payload.get("record_hash"),
            "structured_payload_hash": verified.structured_payload_hash,
            "latency_ms": payload.get("latency_ms"),
            "attempt_count": payload.get("attempt_count"),
            "transport_retry_count": payload.get("transport_retry_count"),
            "structured_correction_count": payload.get("structured_correction_count"),
            "outcome": payload.get("outcome"),
            "failure_kind": payload.get("failure_kind"),
            "structured_valid": payload.get("structured_valid"),
            "scope_valid": payload.get("scope_valid"),
        }
        _inspect_value(record, source=path)
        for key in (
            "identity_hash",
            "request_id_hash",
            "raw_response_hash",
            "record_hash",
            "prompt_hash",
            "response_schema_hash",
            "runtime_config_hash",
        ):
            if not re.fullmatch(r"[0-9a-f]{64}", str(record.get(key) or "")):
                raise ValueError(f"journal projection lacks valid {key}: {path.name}")
        if record["structured_payload_hash"] is not None and not re.fullmatch(
            r"[0-9a-f]{64}", str(record["structured_payload_hash"])
        ):
            raise ValueError(f"journal projection has invalid payload hash: {path.name}")
        records.append(record)

    expected = int(journal_receipt.get("record_count") or 0)
    if len(records) != expected:
        raise ValueError(f"journal record count mismatch: projected={len(records)} expected={expected}")
    if source_receipt_records != journal_receipt.get("records"):
        raise ValueError("journal manifest record inventory does not match verified journal files")
    if _canonical_hash(source_receipt_records) != journal_receipt.get("journal_hash"):
        raise ValueError("journal manifest hash does not match verified journal files")
    records.sort(key=lambda item: str(item["identity_hash"]))
    return {
        "schema_version": "v046_role_b_hash_only_llm_call_manifest_v1",
        "journal_hash": journal_receipt.get("journal_hash"),
        "record_count": len(records),
        "network_request_count": sum(int(item.get("attempt_count") or 0) for item in records),
        "failure_count": sum(item.get("outcome") != "success" for item in records),
        "structured_correction_count": sum(
            int(item.get("structured_correction_count") or 0) for item in records
        ),
        "transport_retry_count": sum(
            int(item.get("transport_retry_count") or 0) for item in records
        ),
        "request_ids_hashed": True,
        "provider_responses_hashed": True,
        "raw_prompt_included": False,
        "raw_response_included": False,
        "structured_payload_included": False,
        "evidence_ids_or_text_included": False,
        "api_key_included": False,
        "records": records,
    }


def _readme(gated: dict[str, Any], offline: dict[str, Any], run_id: str) -> str:
    gated_risk = gated.get("risk_extraction") or {}
    gated_evidence = gated.get("evidence_coverage") or {}
    offline_risk = offline.get("risk_extraction") or {}
    offline_evidence = offline.get("evidence_coverage") or {}
    return f"""# Role-B ALL79 final evidence receipt

This directory is the repository-safe export of local run `{run_id}`.

## Frozen results

| Measurement | Cases | M1 | M2 | Real LLM cases |
|---|---:|---:|---:|---:|
| Real-LLM gated | {gated.get('evaluated_case_count')} | {gated_risk.get('correct_positive_count')}/{gated_risk.get('evaluable_positive_count')} = {float(gated_risk.get('official_aligned_accuracy')):.2%} | {gated_evidence.get('covered_existing_gold_count')}/{gated_evidence.get('evaluable_existing_gold_count')} = {float(gated_evidence.get('coverage_recall')):.2%} | {gated.get('real_llm_cases')} |
| Deterministic offline (selected) | {offline.get('evaluated_case_count')} | {offline_risk.get('correct_positive_count')}/{offline_risk.get('evaluable_positive_count')} = {float(offline_risk.get('official_aligned_accuracy')):.2%} | {offline_evidence.get('covered_existing_gold_count')}/{offline_evidence.get('evaluable_existing_gold_count')} = {float(offline_evidence.get('coverage_recall')):.2%} | 0 |

The official thresholds are M1 >= 80% and M2 >= 85%. They are **not met**.
The real-LLM candidate was not promoted because it removed correct deterministic
risks and Evidence. `best_iteration.json` therefore selects `offline`.

The parent directory keeps the formal real-LLM benchmark handoff expected by
the release audit. This directory adds the offline comparator, call-quality
metadata, hash-only request/response provenance, M1/M2 waterfalls, monotonicity
decision, per-case completion hashes, and execution identity.

The call manifest contains 316 logical task records representing 323 network
attempts. Request IDs, provider responses, and successful structured payloads
are represented only by SHA-256 digests; their raw values are not included.

## Deliberately excluded

- prospectus PDFs and licensed source data;
- full per-case analysis results and runtime caches;
- raw prompts, raw provider responses, private LLM journal records, and keys;
- Evidence/exact text and local absolute paths;
- Validation and 2025 Blind inputs or outcomes.

`run_manifest.json` and `SHA256SUMS.txt` bind every exported file. Regenerate
with `scripts/export_v046_role_b_all79_release.py` from the ignored local run.
"""


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--source-gold-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    source_run = args.source_run.resolve()
    source_gold = args.source_gold_manifest.resolve()
    output = args.output_dir
    details = output / "all79_final"

    for source_name, output_name in ROOT_EXPORTS.items():
        _copy_safe(source_run / source_name, output / output_name)
    for source_name, output_name in DETAIL_EXPORTS.items():
        _copy_safe(source_run / source_name, details / output_name)

    receipt = _gold_receipt(source_gold)
    _write_json(output / "existing_gold_manifest_receipt.json", receipt)
    _write_json(details / "llm_call_manifest.json", _llm_call_manifest(source_run))

    gated = json.loads((output / "document_benchmark_summary.json").read_text(encoding="utf-8"))
    offline = json.loads(
        (details / "offline_document_benchmark_summary.json").read_text(encoding="utf-8")
    )
    readme_path = details / "README.md"
    readme_path.write_text(_readme(gated, offline, source_run.name), encoding="utf-8", newline="\n")

    baseline = json.loads((details / "baseline_manifest.json").read_text(encoding="utf-8"))
    ablation = json.loads((details / "ablation_summary.json").read_text(encoding="utf-8"))
    exported_paths = sorted(
        [output / name for name in ROOT_EXPORTS.values()]
        + [output / "existing_gold_manifest_receipt.json"]
        + [details / name for name in DETAIL_EXPORTS.values()]
        + [details / "llm_call_manifest.json"]
        + [readme_path],
        key=lambda path: path.relative_to(output).as_posix(),
    )
    artifacts = [
        {
            "path": path.relative_to(output).as_posix(),
            "sha256": _sha256(path),
            "size_bytes": path.stat().st_size,
        }
        for path in exported_paths
    ]
    run_manifest = {
        "schema_version": EXPORT_VERSION,
        "run_id": source_run.name,
        "source_execution_git_head": baseline.get("git_head"),
        "source_execution_git_dirty": baseline.get("git_dirty_at_execution"),
        "code_fingerprint": baseline.get("code_fingerprint"),
        "runtime_config_hash": baseline.get("runtime_config_hash"),
        "schema_set_hash": baseline.get("schema_set_hash"),
        "gold_manifest_hash": baseline.get("gold_manifest_hash"),
        "subset_hash": baseline.get("subset_hash"),
        "case_count": ablation.get("case_count"),
        "full_development_executed": ablation.get("full_development_executed"),
        "selected_mode": ablation.get("selected_mode"),
        "monotonicity_satisfied": ablation.get("monotonicity_satisfied"),
        "validation_opened": ablation.get("validation_opened"),
        "blind_2025_outcome_accessed": ablation.get("blind_2025_outcome_accessed"),
        "source_root_recorded": False,
        "raw_journal_included": False,
        "raw_prompt_included": False,
        "raw_response_included": False,
        "prospectus_or_evidence_text_included": False,
        "pdf_or_cache_included": False,
        "secret_included": False,
        "artifacts": artifacts,
    }
    _write_json(details / "run_manifest.json", run_manifest)

    manifest_artifacts = artifacts + [
        {
            "path": "all79_final/run_manifest.json",
            "sha256": _sha256(details / "run_manifest.json"),
            "size_bytes": (details / "run_manifest.json").stat().st_size,
        }
    ]
    sums = "".join(f"{item['sha256']}  {item['path']}\n" for item in manifest_artifacts)
    (details / "SHA256SUMS.txt").write_text(sums, encoding="utf-8", newline="\n")

    print(
        json.dumps(
            {
                "run_id": source_run.name,
                "artifact_count": len(manifest_artifacts) + 1,
                "selected_mode": ablation.get("selected_mode"),
                "output": output.as_posix(),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
