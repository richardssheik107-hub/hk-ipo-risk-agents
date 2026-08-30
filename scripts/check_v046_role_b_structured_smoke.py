#!/usr/bin/env python3
"""Bounded synthetic structured-call preflight for the v0.4.6 Role-B profile.

This is deliberately not a prospectus benchmark.  It makes one
Development-only structured call for every task allowed by the frozen Role-B
profile, using sanitized synthetic Evidence and recording only safe
transport/schema/scope diagnostics.  A complete task-set PASS is a prerequisite
for running the much more expensive experiment; it is not metric evidence.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any, Mapping, NamedTuple

import yaml
from pydantic import BaseModel

# Resolve imports from this checkout, not an older editable install in another
# worktree.  The smoke is an identity gate, so cross-checkout imports are unsafe.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SOURCE_ROOT = _PROJECT_ROOT / "src"
for candidate in (_PROJECT_ROOT, _SOURCE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from ipo_risk.agents.business_models import (
    CommercializationCandidate,
    CoreProductCandidate,
)
from ipo_risk.agents.legal_models import (
    LitigationComplianceCandidate,
    ShareholderRightCandidate,
)
from ipo_risk.core.config import load_settings
from ipo_risk.core.container import DependencyContainer, default_registry
from ipo_risk.providers.llm import LLMProviderError, UnavailableLLMProvider
from ipo_risk.schemas import Evidence, EvidenceSourceType


SMOKE_VERSION = "v046_role_b_structured_smoke_v2"
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


def _smoke_task_catalog() -> dict[str, tuple[type[BaseModel], list[Evidence]]]:
    return {
        "shareholder_rights_extract": (
            ShareholderRightCandidate,
            _synthetic_evidence(
                "smoke:rights:1",
                "A pre-listing investor redemption right terminates on listing and is restored only if the listing fails.",
            ),
        ),
        "litigation_compliance_extract": (
            LitigationComplianceCandidate,
            _synthetic_evidence(
                "smoke:legal:1",
                "The issuer states that it is not involved in any material litigation as of the document date.",
            ),
        ),
        "business_precommercial_commercialization_extract": (
            CommercializationCandidate,
            _synthetic_evidence(
                "smoke:business:commercialization:1",
                "Candidate Alpha is in phase II and the issuer has no direct product-sales revenue.",
            ),
        ),
        "business_precommercial_core_product_extract": (
            CoreProductCandidate,
            _synthetic_evidence(
                "smoke:business:core-product:1",
                "The prospectus expressly designates Candidate Alpha as a core product; it is not yet approved or launched.",
            ),
        ),
    }


def smoke_tasks(profile: Mapping[str, Any]) -> tuple[SmokeTask, ...]:
    catalog = _smoke_task_catalog()
    allowed_tasks = [str(item) for item in profile.get("allowed_tasks") or []]
    if (
        not allowed_tasks
        or len(allowed_tasks) != len(set(allowed_tasks))
        or set(allowed_tasks) != set(catalog)
    ):
        raise ValueError("structured smoke allowed_tasks do not match the frozen task catalog")
    prompt_versions = profile.get("prompt_versions") or {}
    tasks: list[SmokeTask] = []
    for task_name in allowed_tasks:
        prompt_version = str(prompt_versions.get(task_name) or "")
        if not prompt_version:
            raise ValueError(f"structured smoke prompt version missing for {task_name}")
        response_model, evidence = catalog[task_name]
        tasks.append(
            SmokeTask(
                task_name,
                prompt_version,
                response_model,
                evidence,
            )
        )
    return tuple(tasks)


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def smoke_profile_identity(profile: Mapping[str, Any]) -> dict[str, Any]:
    """Return the deterministic frozen task/schema identity bound into a smoke."""

    tasks = smoke_tasks(profile)
    profile_version = str(profile.get("profile_version") or "")
    if not profile_version:
        raise ValueError("structured smoke profile_version is missing")
    return {
        "profile_version": profile_version,
        "allowed_tasks": sorted(task.task_name for task in tasks),
        "prompt_versions": {
            task.task_name: task.prompt_version
            for task in sorted(tasks, key=lambda item: item.task_name)
        },
        "response_schema_hashes": {
            task.task_name: _canonical_hash(task.response_model.model_json_schema())
            for task in sorted(tasks, key=lambda item: item.task_name)
        },
    }


def _read_smoke_profile(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError("structured smoke profile is unreadable") from exc
    if not isinstance(payload, dict):
        raise ValueError("structured smoke config must be a YAML object")
    profile = payload.get("role_b_ablation_profile")
    if not isinstance(profile, dict):
        raise ValueError("role_b_ablation_profile is missing")
    # Materialize once here so malformed or drifted frozen identities fail
    # before a provider can be called.
    smoke_profile_identity(profile)
    return profile


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


def run_probe(provider: Any, *, profile: Mapping[str, Any]) -> dict[str, Any]:
    task_plan = smoke_tasks(profile)
    profile_identity = smoke_profile_identity(profile)
    expected_tasks = set(profile_identity["allowed_tasks"])
    results: list[dict[str, Any]] = []
    for task in task_plan:
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
    observed_tasks = {str(item.get("task_name") or "") for item in results}
    passed = (
        len(results) == len(expected_tasks)
        and observed_tasks == expected_tasks
        and all(item["structured_valid"] and item["scope_valid"] for item in results)
    )
    return {
        "smoke_version": SMOKE_VERSION,
        "profile_identity": profile_identity,
        "profile_identity_hash": _canonical_hash(profile_identity),
        "allowed_tasks": profile_identity["allowed_tasks"],
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
    profile = _read_smoke_profile(args.config)
    provider = DependencyContainer(settings, default_registry()).create_llm_provider()
    if isinstance(provider, UnavailableLLMProvider):
        print("status=blocked reason=credentials_or_provider_unavailable")
        return 2
    summary = run_probe(provider, profile=profile)
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
