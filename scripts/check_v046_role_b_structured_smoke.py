#!/usr/bin/env python3
"""Bounded synthetic structured-call preflight for the v0.4.6 Role-B profile.

This is deliberately not a prospectus benchmark.  It makes exactly three
Development-only structured calls with sanitized synthetic Evidence and records
only safe transport/schema/scope diagnostics.  A 3/3 PASS is a prerequisite for
running the much more expensive fixed-10 experiment; it is not metric evidence.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any, NamedTuple

from pydantic import BaseModel

# Resolve imports from this checkout, not an older editable install in another
# worktree.  The smoke is an identity gate, so cross-checkout imports are unsafe.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SOURCE_ROOT = _PROJECT_ROOT / "src"
for candidate in (_PROJECT_ROOT, _SOURCE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from ipo_risk.agents.business_models import CommercializationCandidate
from ipo_risk.agents.legal_models import (
    LitigationComplianceCandidate,
    ShareholderRightCandidate,
)
from ipo_risk.core.config import load_settings
from ipo_risk.core.container import DependencyContainer, default_registry
from ipo_risk.providers.llm import LLMProviderError, UnavailableLLMProvider
from ipo_risk.schemas import Evidence, EvidenceSourceType


SMOKE_VERSION = "v046_role_b_structured_smoke_v1"
DEFAULT_CONFIG = Path("configs/experiments/v046_role_b_ai_responses.yaml")
DEFAULT_OUTPUT = Path("reports/v046_role_b/structured_smoke")


class SmokeTask(NamedTuple):
    task_name: str
    prompt_version: str
    response_model: type[BaseModel]
    evidence: list[Evidence]


def _synthetic_evidence(evidence_id: str, text: str) -> list[Evidence]:
    return [
        Evidence(
            evidence_id=evidence_id,
            document_id="synthetic_development_role_b_smoke",
            chunk_id=f"chunk:{evidence_id}",
            page=1,
            section="synthetic contract probe",
            text=text,
            source_type=EvidenceSourceType.PROSPECTUS,
        )
    ]


def smoke_tasks() -> tuple[SmokeTask, ...]:
    return (
        SmokeTask(
            "shareholder_rights_extract",
            "legal_shareholder_rights_v1",
            ShareholderRightCandidate,
            _synthetic_evidence(
                "smoke:rights:1",
                "A pre-listing investor redemption right terminates on listing and is restored only if the listing fails.",
            ),
        ),
        SmokeTask(
            "litigation_compliance_extract",
            "legal_litigation_compliance_v1",
            LitigationComplianceCandidate,
            _synthetic_evidence(
                "smoke:legal:1",
                "The issuer states that it is not involved in any material litigation as of the document date.",
            ),
        ),
        SmokeTask(
            "business_precommercial_commercialization_extract",
            "business_precommercial_v1",
            CommercializationCandidate,
            _synthetic_evidence(
                "smoke:business:1",
                "Candidate Alpha is a core product in phase II and the issuer has no direct product-sales revenue.",
            ),
        ),
    )


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _safe_metadata(
    provider: Any,
    *,
    task_name: str,
    prompt_version: str,
    response_model: type[BaseModel],
) -> dict[str, Any]:
    metadata = getattr(provider, "last_call_metadata", None)
    request_id = str(getattr(metadata, "request_id", "") or "")
    prompt_hash_method = getattr(provider, "structured_prompt_hash", None)
    if not callable(prompt_hash_method):
        raise RuntimeError("provider does not expose the structured prompt identity")
    return {
        "provider": str(getattr(metadata, "provider_name", getattr(provider, "name", "unknown"))),
        "model": str(getattr(metadata, "model_name", getattr(provider, "model", "unknown"))),
        "prompt_version": prompt_version,
        "prompt_hash": str(prompt_hash_method(task_name, prompt_version)),
        "response_schema_hash": _canonical_hash(response_model.model_json_schema()),
        "request_id_hash": sha256(request_id.encode("utf-8")).hexdigest() if request_id else None,
        "raw_response_hash": getattr(metadata, "raw_response_hash", None),
        "latency_ms": getattr(metadata, "latency_ms", None),
        "token_usage": dict(getattr(metadata, "token_usage", {}) or {}),
        "attempt_trace": list(getattr(provider, "last_attempt_trace", []) or []),
    }


def run_probe(provider: Any) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for task in smoke_tasks():
        allowed = {item.evidence_id for item in task.evidence}
        try:
            candidate = provider.generate_structured(
                task_name=task.task_name,
                prompt_version=task.prompt_version,
                evidence=task.evidence,
                response_model=task.response_model,
            )
            validated = task.response_model.model_validate(candidate)
            cited = set(getattr(validated, "evidence_ids", []) or [])
            scope_valid = bool(cited) and cited.issubset(allowed)
            results.append(
                {
                    "task_name": task.task_name,
                    "response_model": task.response_model.__name__,
                    "structured_valid": True,
                    "scope_valid": scope_valid,
                    "allowed_evidence_count": len(allowed),
                    "cited_evidence_count": len(cited),
                    "failure_kind": None if scope_valid else "evidence_out_of_scope",
                    **_safe_metadata(
                        provider,
                        task_name=task.task_name,
                        prompt_version=task.prompt_version,
                        response_model=task.response_model,
                    ),
                }
            )
        except LLMProviderError as exc:
            results.append(
                {
                    "task_name": task.task_name,
                    "response_model": task.response_model.__name__,
                    "structured_valid": False,
                    "scope_valid": False,
                    "allowed_evidence_count": len(allowed),
                    "cited_evidence_count": 0,
                    "failure_kind": exc.kind.value,
                    "recoverable": exc.recoverable,
                    "attempts": exc.attempts,
                    **_safe_metadata(
                        provider,
                        task_name=task.task_name,
                        prompt_version=task.prompt_version,
                        response_model=task.response_model,
                    ),
                }
            )
    passed = len(results) == 3 and all(
        item["structured_valid"] and item["scope_valid"] for item in results
    )
    return {
        "smoke_version": SMOKE_VERSION,
        "dataset_split": "development",
        "synthetic_sanitized_payload": True,
        "full_pdf_opened": False,
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
        "call_count": len(results),
        "passed_count": sum(
            item["structured_valid"] and item["scope_valid"] for item in results
        ),
        "passed": passed,
        "tasks": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    settings = load_settings(str(args.config))
    provider = DependencyContainer(settings, default_registry()).create_llm_provider()
    if isinstance(provider, UnavailableLLMProvider):
        print("status=blocked reason=credentials_or_provider_unavailable")
        return 2
    summary = run_probe(provider)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "structured_smoke_summary.json"
    output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"status={'pass' if summary['passed'] else 'fail'} "
        f"structured={summary['passed_count']}/{summary['call_count']} "
        "scope=development_synthetic_only validation=false blind_2025=false"
    )
    print(f"summary={output}")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
