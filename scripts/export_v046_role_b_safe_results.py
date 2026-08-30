#!/usr/bin/env python3
"""Export a compact, repository-safe index of every local Role-B v0.4.6 run.

The local report tree contains licensed PDFs, parser/runtime caches, full
analysis payloads, and private LLM journals.  Those artifacts must never be
committed.  This exporter inventories every run that has a governed summary
artifact and copies only summary-level JSON after rejecting secrets, absolute
home paths, raw prompts/responses, and Evidence text.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


EXPORT_VERSION = "v046_role_b_safe_all_rounds_v1"
DEFAULT_SOURCE = Path("reports/v046_role_b")
DEFAULT_OUTPUT = Path("docs/research/v046_role_b_all_rounds")

SAFE_NAMES = frozenset(
    {
        "ablation_summary.json",
        "iteration_summary.json",
        "campaign_summary.json",
        "forensic_summary.json",
        "financial_conversion_summary.json",
        "concentration_formation_summary.json",
        "period_selection_audit_summary.json",
        "structured_smoke_summary.json",
        "fixed_journal_summary.json",
        "fresh_checkpoint_summary.json",
        "best_checkpoint.json",
        "accepted_fixes.json",
        "failure_focus.json",
        "llm_call_quality.json",
        "monotonicity_report.json",
        "preflight.json",
        "root_alignment_summary.json",
    }
)

PRIMARY_SUMMARY_NAMES = (
    "ablation_summary.json",
    "iteration_summary.json",
    "campaign_summary.json",
    "forensic_summary.json",
    "financial_conversion_summary.json",
    "concentration_formation_summary.json",
    "period_selection_audit_summary.json",
    "structured_smoke_summary.json",
    "fresh_checkpoint_summary.json",
    "fixed_journal_summary.json",
    "root_alignment_summary.json",
)

FORBIDDEN_VALUE_KEYS = frozenset(
    {
    "raw_prompt",
    "raw_response",
    "prompt_text",
    "response_text",
    "api_key_value",
    "authorization",
    "prospectus_path",
    "local_path",
    "evidence_text",
    "exact_text",
    }
)
FORBIDDEN_STRING_PATTERNS = (
    re.compile(r"(?i)ark-[0-9a-z-]{16,}"),
    re.compile(r"(?i)bearer\s+[0-9a-z._-]{12,}"),
    re.compile(r"(?i)[A-Z]:[\\/](?:Users|Documents and Settings)[\\/]"),
    re.compile(r"/(?:Users|home)/[^/\s]+/"),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_safe_json(path: Path) -> Any:
    payload = json.loads(path.read_text(encoding="utf-8"))

    def inspect(value: Any, trail: tuple[str, ...] = ()) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                lowered = str(key).casefold()
                # Governance booleans such as ``raw_prompt_persisted=false``
                # and hashes such as ``exact_text_hash`` are safe and useful.
                # Only actual sensitive-value fields are rejected.
                if lowered in FORBIDDEN_VALUE_KEYS:
                    raise ValueError(f"forbidden summary key:{path}:{'.'.join((*trail, str(key)))}")
                inspect(item, (*trail, str(key)))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                inspect(item, (*trail, str(index)))
        elif isinstance(value, str):
            for pattern in FORBIDDEN_STRING_PATTERNS:
                if pattern.search(value):
                    raise ValueError(f"forbidden summary string:{path}:{'.'.join(trail)}")

    inspect(payload)
    return payload


def _selected_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    selected_mode = summary.get("selected_mode")
    modes = summary.get("modes")
    selected = modes.get(selected_mode) if isinstance(modes, dict) else None
    if not isinstance(selected, dict) and isinstance(modes, dict) and len(modes) == 1:
        selected_mode, selected = next(iter(modes.items()))
    selected = selected if isinstance(selected, dict) else {}
    llm = summary.get("llm_quality")
    llm = llm if isinstance(llm, dict) else {}
    m1_den = selected.get("evaluable_positive_risk_unit_count")
    m2_den = selected.get("evaluable_evidence_unit_count")
    m1 = selected.get("m1")
    m2 = selected.get("m2")
    return {
        "selected_mode": selected_mode,
        "case_count": summary.get("case_count"),
        "m1_numerator": round(float(m1) * int(m1_den)) if m1 is not None and m1_den else None,
        "m1_denominator": m1_den,
        "m1": m1,
        "m2_numerator": round(float(m2) * int(m2_den)) if m2 is not None and m2_den else None,
        "m2_denominator": m2_den,
        "m2": m2,
        "real_llm_case_count": llm.get("real_llm_case_count"),
        "structured_scope_valid_count": llm.get("structured_scope_valid_count"),
        "call_count": llm.get("call_count"),
        "fallback_count": llm.get("fallback_count"),
        "transport_failure_count": llm.get("transport_failure_count"),
        "response_validation_failure_count": llm.get("response_validation_failure_count"),
        "validation_opened": summary.get("validation_opened"),
        "blind_2025_outcome_accessed": summary.get("blind_2025_outcome_accessed"),
    }


def _discover(source: Path) -> list[dict[str, Any]]:
    grouped: dict[Path, list[Path]] = {}
    for path in source.rglob("*.json"):
        if path.name in SAFE_NAMES:
            grouped.setdefault(path.parent, []).append(path)

    runs: list[dict[str, Any]] = []
    for directory in sorted(grouped, key=lambda item: item.as_posix()):
        files = sorted(grouped[directory], key=lambda item: item.name)
        primary_path = next(
            (directory / name for name in PRIMARY_SUMMARY_NAMES if (directory / name).is_file()),
            None,
        )
        payloads: dict[str, Any] = {}
        artifacts: list[dict[str, Any]] = []
        for path in files:
            payloads[path.name] = _load_safe_json(path)
            artifacts.append(
                {
                    "name": path.name,
                    "sha256": _sha256(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        primary = payloads.get(primary_path.name, {}) if primary_path else {}
        metrics = _selected_metrics(primary) if isinstance(primary, dict) else {}
        status = "complete" if primary_path else "preflight_only"
        if primary_path and primary_path.name == "preflight.json":
            status = "preflight_only"
        runs.append(
            {
                "run_id": directory.relative_to(source).as_posix(),
                "category": directory.relative_to(source).parts[0],
                "status": status,
                "primary_summary": primary_path.name if primary_path else None,
                "metrics": metrics,
                "artifacts": artifacts,
                "summaries": payloads,
            }
        )
    return runs


def _write_csv(path: Path, runs: list[dict[str, Any]]) -> None:
    fields = [
        "run_id",
        "category",
        "status",
        "primary_summary",
        "selected_mode",
        "case_count",
        "m1_numerator",
        "m1_denominator",
        "m1",
        "m2_numerator",
        "m2_denominator",
        "m2",
        "real_llm_case_count",
        "structured_scope_valid_count",
        "call_count",
        "fallback_count",
        "transport_failure_count",
        "response_validation_failure_count",
        "validation_opened",
        "blind_2025_outcome_accessed",
        "summary_artifact_count",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for run in runs:
            writer.writerow(
                {
                    "run_id": run["run_id"],
                    "category": run["category"],
                    "status": run["status"],
                    "primary_summary": run["primary_summary"],
                    **run["metrics"],
                    "summary_artifact_count": len(run["artifacts"]),
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    runs = _discover(args.source)
    args.output.mkdir(parents=True, exist_ok=True)
    complete = sum(run["status"] == "complete" for run in runs)
    preflight_only = sum(run["status"] == "preflight_only" for run in runs)
    manifest = {
        "export_version": EXPORT_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_root_recorded": False,
        "run_count": len(runs),
        "complete_run_count": complete,
        "preflight_only_run_count": preflight_only,
        "raw_journal_included": False,
        "raw_prompt_included": False,
        "raw_response_included": False,
        "prospectus_or_evidence_text_included": False,
        "pdf_or_cache_included": False,
        "secret_included": False,
        "validation_opened_by_export": False,
        "blind_2025_accessed_by_export": False,
        "runs": runs,
    }
    manifest_path = args.output / "all_rounds_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _write_csv(args.output / "all_rounds_metrics.csv", runs)
    print(
        json.dumps(
            {
                "run_count": len(runs),
                "complete_run_count": complete,
                "preflight_only_run_count": preflight_only,
                "manifest_sha256": _sha256(manifest_path),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
