#!/usr/bin/env python3
"""Run the opt-in v0.4.6 Role-B offline/shadow/gated ablation.

The runner is deliberately separate from every competition entry point.  It
binds the already-frozen Existing-Gold fixed-10 Development cohort, disables
Market and Final-Supervisor LLM channels, and permits remote calls only for the
four frozen Legal/Business structured tasks.

Modes have strict semantics:

``offline``
    Uses ``UnavailableLLMProvider`` and therefore performs zero network calls.
``shadow``
    Calls the real Role-B provider through an immutable local journal, but the
    saved/evaluated canonical result is the exact offline result.
``gated``
    Replays the shadow journal through the ordinary Legal/Business Agents.  A
    missing journal record fails closed; it never causes an additional remote
    call.

No prompt, raw provider response, API key, base URL, local PDF path, Validation
case or 2025 Blind outcome is written by this script.  The local report root is
gitignored and must not be committed as a benchmark artifact.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import date
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Callable, Mapping, Sequence
import unicodedata

import yaml

# A direct ``python scripts/...`` invocation must resolve the source tree from
# this checkout rather than an older editable install from another worktree.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SOURCE_ROOT = _PROJECT_ROOT / "src"
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

from ipo_risk.agents.business_v03 import V03BusinessAgent
from ipo_risk.agents.business_models import CommercializationCandidate, CoreProductCandidate
from ipo_risk.agents.legal import LegalAgent
from ipo_risk.agents.legal_models import (
    LitigationComplianceCandidate,
    ShareholderRightCandidate,
)
from ipo_risk.core.config import Settings, load_settings
from ipo_risk.core.container import DependencyContainer, ComponentRegistry, default_registry
from ipo_risk.evaluation.role_b_waterfall import (
    build_role_b_waterfall_artifacts,
    read_evaluator_csv,
)
from ipo_risk.evaluation.existing_gold_metrics import EVALUATOR_VERSION
from ipo_risk.providers.llm import (
    LLMFailureKind,
    LLMProviderError,
    OpenAICompatibleLLMProvider,
    OpenAIResponsesLLMProvider,
    UnavailableLLMProvider,
)
from ipo_risk.runtime.llm_journal import (
    JournaledLLMProvider,
    LLMJournalRecord,
    LocalLLMJournal,
)
from ipo_risk.runtime.role_b_ablation import (
    ROLE_B_TASK_NAMES,
    RoleBAblationInvariantError,
    RoleBAblationMode,
    ShadowRiskAgent,
    TaskRoutingProvider,
    build_shadow_projection,
    canonical_risk_evidence_calculation_hash,
    validate_development_only_manifest,
)
from ipo_risk.retrieval.role_b_financial_v046 import (
    RoleBFinancialHighRecallRetriever,
)
from ipo_risk.schemas import Evidence, IPOAnalysisRequest, IPOAnalysisResult
from ipo_risk.services.analysis_service import IPOAnalysisService

from scripts.run_v045_role_b_iteration import (
    DEFAULT_BRIDGE,
    DEFAULT_COVERAGE,
    DEFAULT_SUBSET,
    IterationRunnerError,
    _build_runtime_cases_manifest,
    _case_ids,
    _ensure_coverage,
    _evaluate,
    _failure_focus,
    _git_state,
    _load_or_create_subset,
    _write_results_jsonl,
)
from scripts.run_v04_role_e_demo import (
    PROSPECTUS_ROOT_ENV,
    ProspectusIntegrityError,
    _read_catalog,
    deterministic_request_id,
    resolve_prospectus,
)


RUNNER_VERSION = "v046_role_b_ablation_runner_v1"
DEFAULT_CONFIG = Path("configs/experiments/v046_role_b_ai_responses.yaml")
DEFAULT_OUTPUT_ROOT = Path("reports/v046_role_b/ablation")
DEFAULT_SMOKE_SUMMARY = Path(
    "reports/v046_role_b/structured_smoke/structured_smoke_summary.json"
)
DEFAULT_CATALOG = Path("data/catalog/ipo_prospectus_manifest.csv")
REMOTE_PROVIDERS = {
    "openai_responses": OpenAIResponsesLLMProvider,
    "openai_compatible": OpenAICompatibleLLMProvider,
}
ROLE_B_RESPONSE_MODELS = {
    "shareholder_rights_extract": ShareholderRightCandidate,
    "litigation_compliance_extract": LitigationComplianceCandidate,
    "business_precommercial_commercialization_extract": CommercializationCandidate,
    "business_precommercial_core_product_extract": CoreProductCandidate,
}
MODE_ORDER = (
    RoleBAblationMode.OFFLINE.value,
    RoleBAblationMode.SHADOW.value,
    RoleBAblationMode.GATED.value,
)
_MIN_ANCHOR_CHARS = 12
_RISK_QUERY_INTENTS = {
    # ``retrieve_for_risk`` records the governed pool under the canonical risk
    # code, while the legacy free-text path records its two component intents.
    # Accept both so the measurement-only trace cannot discard a valid cash
    # candidate solely because the caller used the risk-pool API.
    "cash_runway": frozenset(
        {"cash_runway", "cash_flow_ending_cash", "operating_cash_flow"}
    ),
    "customer_concentration": frozenset({"customer_concentration"}),
    "supplier_concentration": frozenset({"supplier_concentration"}),
    "redemption_rights": frozenset({"redemption_rights"}),
    "material_litigation_compliance": frozenset(
        {"material_litigation_compliance"}
    ),
}
_DIAGNOSTIC_CANDIDATE_LIMIT = 20


class RoleBAblationRunnerError(RuntimeError):
    """Safe, fail-closed orchestration error."""


class _TracingRetriever:
    """Observe governed candidate identity without changing retrieval output."""

    def __init__(self, delegate: Any, sink: list[dict[str, Any]]) -> None:
        self._delegate = delegate
        self._sink = sink

    def retrieve(self, chunks: list[Any], query: str, limit: int = 3) -> list[Evidence]:
        candidates = list(self._delegate.retrieve(chunks, query, limit=limit))
        diagnostic_candidates = (
            candidates
            if limit >= _DIAGNOSTIC_CANDIDATE_LIMIT
            else list(
                self._delegate.retrieve(
                    chunks,
                    query,
                    limit=_DIAGNOSTIC_CANDIDATE_LIMIT,
                )
            )
        )

        def identity(item: Evidence) -> dict[str, Any]:
            return {
                "evidence_id": item.evidence_id,
                "document_id": item.document_id,
                "chunk_id": item.chunk_id,
                "page": item.page,
                # Text is retained in memory only so the evaluator-side
                # anchor rule can identify a Gold unit. It is never
                # serialized into the trace artifact.
                "text": item.text,
                "query_family": item.metadata.get("query_family"),
                "query_intent": item.metadata.get("query_intent"),
            }

        self._sink.append(
            {
                "query": query,
                "limit": limit,
                "candidates": [identity(item) for item in candidates],
                "diagnostic_limit": _DIAGNOSTIC_CANDIDATE_LIMIT,
                "diagnostic_candidates": [
                    identity(item) for item in diagnostic_candidates
                ],
            }
        )
        return candidates

    def retrieve_for_risk(
        self, chunks: list[Any], risk_code: str, *, limit: int = 10
    ) -> list[Evidence]:
        retrieve_for_risk = getattr(self._delegate, "retrieve_for_risk", None)
        if not callable(retrieve_for_risk):
            raise AttributeError("delegate does not expose retrieve_for_risk")
        candidates = list(retrieve_for_risk(chunks, risk_code, limit=limit))
        diagnostic_candidates = (
            candidates
            if limit >= _DIAGNOSTIC_CANDIDATE_LIMIT
            else list(
                retrieve_for_risk(
                    chunks, risk_code, limit=_DIAGNOSTIC_CANDIDATE_LIMIT
                )
            )
        )

        def identity(item: Evidence) -> dict[str, Any]:
            return {
                "evidence_id": item.evidence_id,
                "document_id": item.document_id,
                "chunk_id": item.chunk_id,
                "page": item.page,
                "text": item.text,
                "query_family": risk_code,
                "query_intent": risk_code,
            }

        self._sink.append(
            {
                "query": risk_code,
                "limit": limit,
                "candidates": [identity(item) for item in candidates],
                "diagnostic_limit": _DIAGNOSTIC_CANDIDATE_LIMIT,
                "diagnostic_candidates": [
                    identity(item) for item in diagnostic_candidates
                ],
            }
        )
        return candidates


class _ReplayOnlyDelegate:
    """Identity carrier proving gated mode never falls through to network."""

    def __init__(self, provider: str, model: str) -> None:
        self.name = provider
        self.model = model
        self.last_call_metadata = None
        self.last_failure_diagnostics = None
        self.last_attempt_trace: list[dict[str, Any]] = []
        self.call_count = 0

    def complete(self, prompt: str) -> str:
        self.call_count += 1
        raise LLMProviderError(
            LLMFailureKind.UNAVAILABLE,
            "Gated Role-B mode permits local journal replay only",
            recoverable=False,
        )

    def generate_structured(self, **_: Any) -> Any:
        self.call_count += 1
        raise LLMProviderError(
            LLMFailureKind.UNAVAILABLE,
            "Required Role-B journal record is unavailable",
            recoverable=False,
        )


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _subset_identity_hash(payload: Mapping[str, Any]) -> str:
    """Hash the actual selected cohort rather than its parent fixed-10 label."""

    return _canonical_hash(
        {key: value for key, value in payload.items() if key != "subset_hash"}
    )


def _safe_json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_profile(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise RoleBAblationRunnerError("Role-B profile is unreadable") from exc
    if not isinstance(payload, dict):
        raise RoleBAblationRunnerError("Role-B profile must be a YAML object")
    profile = payload.get("role_b_ablation_profile")
    if not isinstance(profile, dict):
        raise RoleBAblationRunnerError("role_b_ablation_profile is missing")
    if profile.get("validation_enabled") is not False:
        raise RoleBAblationRunnerError("Role-B profile must keep Validation disabled")
    if profile.get("blind_2025_enabled") is not False:
        raise RoleBAblationRunnerError("Role-B profile must keep 2025 Blind disabled")
    if set(profile.get("allowed_tasks") or []) != set(ROLE_B_TASK_NAMES):
        raise RoleBAblationRunnerError("Role-B task allow-list drift detected")
    return profile


def _safe_settings_identity(settings: Settings, profile: Mapping[str, Any]) -> dict[str, Any]:
    """Return only non-secret, portable fields used to bind replay identity."""

    base_url = str(settings.llm_base_url or "").strip()
    return {
        "runner_version": RUNNER_VERSION,
        "profile_version": profile.get("profile_version"),
        "workflow_version": settings.workflow_version,
        "runtime_mode": settings.runtime_mode,
        "parser": settings.parser,
        "retriever": settings.retriever,
        "financial_agent": settings.financial_agent,
        "financial_extractor": settings.financial_extractor,
        "legal_agent": settings.legal_agent,
        "business_agent": settings.business_agent,
        "market_agent": settings.market_agent,
        "verifier": settings.verifier,
        "supervisor": settings.supervisor,
        "predictor": settings.predictor,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        # Bind replay to the selected endpoint without persisting that endpoint.
        "llm_base_url_hash": sha256(base_url.encode("utf-8")).hexdigest()
        if base_url
        else None,
        "llm_timeout_seconds": int(settings.llm_timeout_seconds),
        "llm_max_retries": int(settings.llm_max_retries),
        "transport": profile.get("transport"),
        "max_transport_attempts_per_structured_attempt": profile.get(
            "max_transport_attempts_per_structured_attempt"
        ),
        "max_structured_attempts": profile.get("max_structured_attempts"),
        "max_transport_or_validation_attempts": profile.get(
            "max_transport_or_validation_attempts"
        ),
        "max_network_calls_per_task": profile.get("max_network_calls_per_task"),
        "smoke_required_before_fixed10": profile.get(
            "smoke_required_before_fixed10"
        ),
        "market_context": settings.market_context,
        "final_supervisor": settings.final_supervisor,
        "allowed_tasks": sorted(profile.get("allowed_tasks") or []),
        "prompt_versions": dict(sorted((profile.get("prompt_versions") or {}).items())),
    }


def _runtime_config_hash(
    settings: Settings,
    profile: Mapping[str, Any],
    code_fingerprint: str,
) -> str:
    return _canonical_hash(
        {
            "safe_runtime": _safe_settings_identity(settings, profile),
            "code_fingerprint": code_fingerprint,
        }
    )


def _prompt_hashes(
    profile: Mapping[str, Any], provider_name: str
) -> dict[tuple[str, str], str]:
    """Hash the exact provider instruction through the provider's own method."""

    provider_class = REMOTE_PROVIDERS.get(provider_name)
    if provider_class is None:
        raise RoleBAblationRunnerError(
            f"unsupported Role-B provider profile:{provider_name}"
        )
    provider = object.__new__(provider_class)
    prompt_versions = profile.get("prompt_versions") or {}
    result: dict[tuple[str, str], str] = {}
    for task_name in sorted(ROLE_B_TASK_NAMES):
        prompt_version = str(prompt_versions.get(task_name) or "")
        if not prompt_version:
            raise RoleBAblationRunnerError(f"prompt version missing for {task_name}")
        result[(task_name, prompt_version)] = provider.structured_prompt_hash(
            task_name, prompt_version
        )
    return result


def _response_schema_hashes() -> dict[str, str]:
    return {
        task_name: _canonical_hash(response_model.model_json_schema())
        for task_name, response_model in sorted(ROLE_B_RESPONSE_MODELS.items())
    }


def _schema_set_hash() -> str:
    return _canonical_hash(_response_schema_hashes())


def _preflight(
    *,
    config_path: Path,
    settings: Settings,
    profile: Mapping[str, Any],
    require_remote: bool,
) -> dict[str, Any]:
    if settings.use_mock:
        raise RoleBAblationRunnerError("Role-B ablation refuses use_mock=true")
    if settings.llm_provider not in REMOTE_PROVIDERS:
        raise RoleBAblationRunnerError("Role-B ablation requires a supported remote provider")
    transport = str(profile.get("transport") or "")
    expected_transport = {
        "openai_responses": "responses",
        "openai_compatible": "openai_compatible_chat_json",
    }[settings.llm_provider]
    if transport != expected_transport:
        raise RoleBAblationRunnerError(
            "Role-B provider/transport profile mismatch"
        )
    if settings.market_agent != "disabled" or settings.market_context != "none":
        raise RoleBAblationRunnerError("Role-B ablation requires all Market channels disabled")
    if settings.final_supervisor != "none":
        raise RoleBAblationRunnerError("Role-B ablation requires Final Supervisor disabled")
    if not settings.llm_model:
        raise RoleBAblationRunnerError("Role-B ablation model identity is missing")
    prompt_hashes = _prompt_hashes(profile, settings.llm_provider)
    api_key_present = bool(settings.llm_api_key)
    base_url_present = bool(settings.llm_base_url)
    if require_remote and not (api_key_present and base_url_present):
        raise RoleBAblationRunnerError("Role-B remote credentials/base URL are incomplete")
    return {
        "config_name": config_path.name,
        "effective_provider": settings.llm_provider,
        "effective_model": settings.llm_model,
        "transport": transport,
        "timeout_seconds": int(settings.llm_timeout_seconds),
        "max_network_calls_per_task": int(
            profile.get("max_network_calls_per_task")
            or (1 + int(settings.llm_max_retries))
        ),
        "api_key_present": api_key_present,
        "base_url_present": base_url_present,
        "prompt_hashes": {
            f"{task_name}:{prompt_version}": digest
            for (task_name, prompt_version), digest in sorted(prompt_hashes.items())
        },
        "market_disabled": True,
        "final_supervisor_disabled": True,
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
    }


def _smoke_gate(
    *,
    path: Path,
    settings: Settings,
    profile: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the local three-call smoke without exposing its payloads."""

    required = profile.get("smoke_required_before_fixed10") is True
    base = {
        "required_before_fixed10": required,
        "summary_present": path.is_file(),
        "passed": False,
        "expected_provider": settings.llm_provider,
        "expected_model": settings.llm_model,
    }
    if not required:
        return {**base, "passed": True, "reason": "not_required_by_profile"}
    if not path.is_file():
        return {**base, "reason": "summary_missing"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {**base, "reason": "summary_invalid"}
    if not isinstance(payload, dict):
        return {**base, "reason": "summary_invalid"}
    tasks = payload.get("tasks")
    expected_tasks = {
        "shareholder_rights_extract",
        "litigation_compliance_extract",
        "business_precommercial_commercialization_extract",
    }
    observed_tasks = {
        str(item.get("task_name") or "")
        for item in tasks or []
        if isinstance(item, dict)
    }
    provider_model_match = bool(tasks) and all(
        isinstance(item, dict)
        and item.get("provider") == settings.llm_provider
        and item.get("model") == settings.llm_model
        for item in tasks
    )
    prompt_versions = profile.get("prompt_versions") or {}
    expected_prompt_hashes = _prompt_hashes(profile, settings.llm_provider)
    expected_schema_hashes = _response_schema_hashes()
    contract_match = bool(tasks) and all(
        isinstance(item, dict)
        and item.get("prompt_version")
        == prompt_versions.get(str(item.get("task_name") or ""))
        and item.get("prompt_hash")
        == expected_prompt_hashes.get(
            (
                str(item.get("task_name") or ""),
                str(item.get("prompt_version") or ""),
            )
        )
        and item.get("response_schema_hash")
        == expected_schema_hashes.get(str(item.get("task_name") or ""))
        for item in tasks
    )
    passed = (
        payload.get("smoke_version") == "v046_role_b_structured_smoke_v1"
        and payload.get("dataset_split") == "development"
        and payload.get("synthetic_sanitized_payload") is True
        and payload.get("full_pdf_opened") is False
        and payload.get("validation_opened") is False
        and payload.get("blind_2025_outcome_accessed") is False
        and payload.get("call_count") == 3
        and payload.get("passed_count") == 3
        and payload.get("passed") is True
        and observed_tasks == expected_tasks
        and provider_model_match
        and contract_match
    )
    return {
        **base,
        "passed": passed,
        "reason": "pass" if passed else "provider_model_or_contract_mismatch",
        "call_count": payload.get("call_count"),
        "passed_count": payload.get("passed_count"),
        "observed_tasks": sorted(observed_tasks),
        "provider_model_match": provider_model_match,
        "prompt_schema_contract_match": contract_match,
        "validation_opened": payload.get("validation_opened"),
        "blind_2025_outcome_accessed": payload.get("blind_2025_outcome_accessed"),
    }


def _registry_for_mode(
    mode: str,
    role_b_provider: Any,
    provider_name: str,
) -> ComponentRegistry:
    registry = _experiment_registry()
    registry.register("llm_provider", provider_name, lambda **_: role_b_provider)
    if mode == RoleBAblationMode.SHADOW.value:
        registry.register(
            "legal_agent",
            "v03",
            lambda retriever, llm_provider: ShadowRiskAgent(
                LegalAgent(
                    retriever=retriever,
                    llm_provider=UnavailableLLMProvider("offline Role-B baseline"),
                ),
                LegalAgent(retriever=retriever, llm_provider=llm_provider),
            ),
        )
        registry.register(
            "business_agent",
            "v03",
            lambda retriever, llm_provider: ShadowRiskAgent(
                V03BusinessAgent(
                    retriever=retriever,
                    llm_provider=UnavailableLLMProvider("offline Role-B baseline"),
                ),
                V03BusinessAgent(retriever=retriever, llm_provider=llm_provider),
            ),
        )
    return registry


def _experiment_registry() -> ComponentRegistry:
    registry = default_registry()
    registry.register(
        "retriever",
        RoleBFinancialHighRecallRetriever.name,
        RoleBFinancialHighRecallRetriever,
    )
    return registry


def _build_journaled_router(
    *,
    mode: str,
    case_id: str,
    settings: Settings,
    profile: Mapping[str, Any],
    journal: LocalLLMJournal,
    prompt_hashes: Mapping[tuple[str, str], str],
    runtime_config_hash: str,
) -> tuple[TaskRoutingProvider, _ReplayOnlyDelegate | None]:
    if mode == RoleBAblationMode.SHADOW.value:
        provider_class = REMOTE_PROVIDERS.get(settings.llm_provider)
        if provider_class is None:
            raise RoleBAblationRunnerError(
                f"unsupported Role-B provider profile:{settings.llm_provider}"
            )
        delegate: Any = provider_class(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
        replay_only = None
    elif mode == RoleBAblationMode.GATED.value:
        replay_only = _ReplayOnlyDelegate(settings.llm_provider, settings.llm_model)
        delegate = replay_only
    else:
        raise RoleBAblationRunnerError(f"journal provider unsupported for mode={mode}")
    journaled = JournaledLLMProvider(
        delegate,
        journal=journal,
        case_id=case_id,
        dataset_split="development",
        transport=str(profile.get("transport") or "responses"),
        prompt_hashes=prompt_hashes,
        runtime_config_hash=runtime_config_hash,
    )
    return TaskRoutingProvider(journaled), replay_only


def _offline_settings(settings: Settings, data_dir: Path, report_dir: Path) -> Settings:
    return replace(
        settings,
        llm_provider="unavailable",
        llm_api_key="",
        llm_base_url="",
        data_dir=str(data_dir),
        report_dir=str(report_dir),
        market_agent="disabled",
        market_context="none",
        final_supervisor="none",
    )


def _mode_settings(settings: Settings, data_dir: Path, report_dir: Path) -> Settings:
    return replace(
        settings,
        data_dir=str(data_dir),
        report_dir=str(report_dir),
        market_agent="disabled",
        market_context="none",
        final_supervisor="none",
    )


def _canonical_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "").casefold()
    return re.sub(r"\s+", "", text)


def _text_anchor_matches(gold_text: str, candidate_text: str) -> bool:
    """Mirror the frozen evaluator anchor rule for post-run diagnostics only."""

    gold = _canonical_text(gold_text)
    candidate = _canonical_text(candidate_text)
    if not gold or not candidate:
        return False
    if min(len(gold), len(candidate)) < _MIN_ANCHOR_CHARS:
        return gold == candidate
    return gold in candidate or candidate in gold


def _candidate_intent(candidate: Mapping[str, Any]) -> str:
    return str(candidate.get("query_intent") or candidate.get("query_family") or "")


def _retrieval_pipeline_trace(
    *,
    coverage: Mapping[str, Any],
    evidence_rows: Sequence[Mapping[str, Any]],
    calls_by_case: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    """Join runtime-only candidates to Gold only after analysis has completed.

    The returned rows intentionally contain no prospectus or Gold text. Runtime
    retrieval never receives Gold labels, pages, hashes, or Evidence IDs.
    """

    manifest_rows = {
        str(row.get("evidence_unit_id") or ""): row
        for row in coverage.get("evidence_units", [])
        if isinstance(row, Mapping)
    }
    traces: list[dict[str, Any]] = []
    for evaluated in evidence_rows:
        unit_id = str(evaluated.get("evidence_unit_id") or "")
        gold = manifest_rows.get(unit_id)
        if gold is None:
            raise RoleBAblationRunnerError(
                f"evaluator evidence unit missing from manifest:{unit_id}"
            )
        case_id = str(evaluated.get("case_id") or "")
        risk_code = str(evaluated.get("source_risk_code") or "")
        allowed_intents = _RISK_QUERY_INTENTS.get(risk_code, frozenset({risk_code}))
        candidate_identities: set[tuple[object, ...]] = set()
        query_families: set[str] = set()
        first_page_rank: int | None = None
        first_rank: int | None = None
        agent_consumed = False
        gold_page = int(gold.get("page") or 0)
        gold_text = str(gold.get("exact_text") or "")
        for call in calls_by_case.get(case_id, []):
            diagnostic_candidates = call.get("diagnostic_candidates", [])
            if not isinstance(diagnostic_candidates, list):
                continue
            for rank, candidate in enumerate(diagnostic_candidates, start=1):
                if not isinstance(candidate, Mapping):
                    continue
                intent = _candidate_intent(candidate)
                if intent not in allowed_intents:
                    continue
                evidence_id = str(candidate.get("evidence_id") or "")
                source_identity = (
                    candidate.get("document_id"),
                    candidate.get("chunk_id"),
                    candidate.get("page"),
                )
                if not evidence_id:
                    continue
                candidate_identities.add(source_identity)
                query_families.add(intent)
                if (
                    candidate.get("page") == gold_page
                    and (first_page_rank is None or rank < first_page_rank)
                ):
                    first_page_rank = rank
                if (
                    candidate.get("page") == gold_page
                    and _text_anchor_matches(
                        gold_text,
                        str(candidate.get("text") or ""),
                    )
                    and (first_rank is None or rank < first_rank)
                ):
                    first_rank = rank

            for candidate in call.get("candidates", []):
                if not isinstance(candidate, Mapping):
                    continue
                if _candidate_intent(candidate) not in allowed_intents:
                    continue
                if (
                    candidate.get("page") == gold_page
                    and _text_anchor_matches(
                        gold_text,
                        str(candidate.get("text") or ""),
                    )
                ):
                    agent_consumed = True
                    break
        traces.append(
            {
                "trace_version": "v046_role_b_pipeline_trace_v1",
                "trace_kind": "retrieval",
                "evidence_unit_id": unit_id,
                "case_id": case_id,
                "split": "development",
                "retrieval_query_family": sorted(query_families),
                "candidate_count": len(candidate_identities),
                "first_gold_page_rank": first_page_rank,
                "first_gold_rank": first_rank,
                "agent_consumed": agent_consumed,
                "validation_opened": False,
                "blind_2025_outcome_accessed": False,
            }
        )
    return traces


def _analyse(
    *,
    settings: Settings,
    request: IPOAnalysisRequest,
    registry: ComponentRegistry | None = None,
    retrieval_trace_sink: list[dict[str, Any]] | None = None,
) -> IPOAnalysisResult:
    active_registry = registry or default_registry()
    if retrieval_trace_sink is not None:
        delegate = active_registry.create("retriever", settings.retriever)
        active_registry.register(
            "retriever",
            settings.retriever,
            lambda: _TracingRetriever(delegate, retrieval_trace_sink),
        )
    container = DependencyContainer(settings, active_registry)
    return IPOAnalysisService(settings=settings, container=container).analyze(request)


@dataclass(frozen=True)
class CaseInputs:
    case_id: str
    company_name: str
    stock_code: str
    listing_date: date
    prospectus_path: Path
    prospectus_sha256: str

    def request(self) -> IPOAnalysisRequest:
        return IPOAnalysisRequest(
            request_id=deterministic_request_id(
                self.stock_code, self.listing_date, self.prospectus_sha256
            ),
            company_name=self.company_name,
            stock_code=self.stock_code,
            listing_date=self.listing_date,
            prospectus_path=str(self.prospectus_path),
            use_mock=False,
        )


ModeExecutor = Callable[[str, CaseInputs, IPOAnalysisResult | None], IPOAnalysisResult]


def orchestrate_case_modes(
    *,
    case: CaseInputs,
    modes: Sequence[str],
    execute_mode: ModeExecutor,
) -> dict[str, IPOAnalysisResult]:
    """Order modes and enforce shadow canonical equality for real and fake tests."""

    requested = tuple(dict.fromkeys(modes))
    unknown = set(requested) - set(MODE_ORDER)
    if unknown:
        raise RoleBAblationRunnerError(f"unknown ablation modes:{sorted(unknown)}")
    if any(mode in requested for mode in ("shadow", "gated")) and "offline" not in requested:
        raise RoleBAblationRunnerError("shadow/gated require the same-run offline baseline")
    if "gated" in requested and "shadow" not in requested:
        raise RoleBAblationRunnerError("gated requires shadow journal capture in the same run")

    results: dict[str, IPOAnalysisResult] = {}
    for mode in MODE_ORDER:
        if mode not in requested:
            continue
        baseline = results.get(RoleBAblationMode.OFFLINE.value)
        observed = execute_mode(mode, case, baseline)
        if mode == RoleBAblationMode.SHADOW.value:
            if baseline is None:
                raise RoleBAblationInvariantError("shadow baseline unavailable")
            if canonical_risk_evidence_calculation_hash(observed) != canonical_risk_evidence_calculation_hash(baseline):
                raise RoleBAblationInvariantError("shadow canonical result differs from offline")
            # The caller may have used ShadowRiskAgent, but the persisted and
            # evaluated result is exactly the offline object, not a copy with
            # probe metadata mixed into its public result.
            results[mode] = baseline
        else:
            results[mode] = observed
    return results


def _journal_manifest(journal: LocalLLMJournal) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for path in sorted(journal.root.glob("*.json")) if journal.root.is_dir() else []:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            record = LLMJournalRecord.model_validate(payload)
            record.verify(record.identity)
        except Exception as exc:
            raise RoleBAblationRunnerError("local journal contains an invalid record") from exc
        identity = record.identity
        records.append(
            {
                "identity_hash": record.identity_hash,
                "record_hash": record.record_hash,
                "case_id": identity.case_id,
                "task_name": identity.task_name,
                "prompt_version": identity.prompt_version,
                "prompt_hash": identity.prompt_hash,
                "response_schema_hash": identity.response_schema_hash,
                "runtime_config_hash": identity.runtime_config_hash,
                "allowed_evidence_count": len(identity.ordered_allowed_evidence_ids),
                "provider": identity.provider,
                "model": identity.model,
                "outcome": record.outcome,
                "structured_valid": record.structured_valid,
                "scope_valid": record.scope_valid,
                "out_of_scope_ids": list(record.out_of_scope_ids),
                "failure_kind": record.failure_kind,
                "attempt_count": record.attempt_count,
                "transport_retry_count": record.transport_retry_count,
                "structured_correction_count": record.structured_correction_count,
                "latency_ms": record.latency_ms,
                "token_usage": dict(record.token_usage),
            }
        )
    return {
        "journal_version": "v046_llm_journal_v1",
        "record_count": len(records),
        "journal_hash": _canonical_hash(records),
        "records": records,
        "raw_prompt_persisted": False,
        "raw_response_persisted": False,
        "api_key_persisted": False,
        "base_url_persisted": False,
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
    }


def _analysis_json(result: IPOAnalysisResult) -> dict[str, Any]:
    return json.loads(result.model_dump_json())


def _load_case_inputs(
    *,
    case: Mapping[str, Any],
    catalog: Mapping[str, Mapping[str, str]],
    bridge: Mapping[str, Mapping[str, str]],
    prospectus_root: Path,
) -> CaseInputs:
    case_id = str(case.get("case_id") or "")
    catalog_row = catalog.get(case_id)
    bridge_row = bridge.get(case_id)
    if catalog_row is None or bridge_row is None:
        raise RoleBAblationRunnerError(f"frozen catalog/bridge row missing:{case_id}")
    if catalog_row.get("dataset_split") != "development":
        raise RoleBAblationRunnerError(f"non-Development prospectus rejected:{case_id}")
    try:
        prospectus, verification = resolve_prospectus(
            dict(catalog_row), prospectus_root, None
        )
    except (ProspectusIntegrityError, FileNotFoundError) as exc:
        raise RoleBAblationRunnerError(f"prospectus integrity failed:{case_id}") from exc
    return CaseInputs(
        case_id=case_id,
        company_name=str(case.get("company_name") or ""),
        stock_code=str(bridge_row["stock_code_wind"]),
        listing_date=date.fromisoformat(str(bridge_row["official_listed_date"])),
        prospectus_path=prospectus,
        prospectus_sha256=str(verification["sha256"]),
    )


def _runtime_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases") if isinstance(payload, dict) else None
    if not isinstance(cases, list):
        raise RoleBAblationRunnerError("runtime cases manifest is invalid")
    return [dict(item) for item in cases if isinstance(item, dict)]


def _case_executor(
    *,
    settings: Settings,
    profile: Mapping[str, Any],
    prompt_hashes: Mapping[tuple[str, str], str],
    runtime_config_hash: str,
    output_root: Path,
    journal: LocalLLMJournal,
) -> tuple[ModeExecutor, dict[str, Any]]:
    replay_delegates: dict[str, _ReplayOnlyDelegate] = {}
    shadow_projections: dict[str, Any] = {}
    retrieval_calls: dict[str, dict[str, list[dict[str, Any]]]] = {
        mode: {} for mode in MODE_ORDER
    }

    def execute(mode: str, case: CaseInputs, baseline: IPOAnalysisResult | None) -> IPOAnalysisResult:
        mode_root = output_root / mode
        data_dir = mode_root / "runtime_data" / case.case_id
        report_dir = mode_root / "runtime_reports" / case.case_id
        request = case.request()
        trace_sink = retrieval_calls[mode].setdefault(case.case_id, [])
        if mode == RoleBAblationMode.OFFLINE.value:
            return _analyse(
                settings=_offline_settings(settings, data_dir, report_dir),
                request=request,
                registry=_experiment_registry(),
                retrieval_trace_sink=trace_sink,
            )

        provider, replay_only = _build_journaled_router(
            mode=mode,
            case_id=case.case_id,
            settings=settings,
            profile=profile,
            journal=journal,
            prompt_hashes=prompt_hashes,
            runtime_config_hash=runtime_config_hash,
        )
        if replay_only is not None:
            replay_delegates[case.case_id] = replay_only
        mode_settings = _mode_settings(settings, data_dir, report_dir)
        observed = _analyse(
            settings=mode_settings,
            request=request,
            registry=_registry_for_mode(mode, provider, settings.llm_provider),
            retrieval_trace_sink=trace_sink,
        )
        if mode == RoleBAblationMode.SHADOW.value:
            if baseline is None:
                raise RoleBAblationInvariantError("shadow baseline unavailable")
            shadow_projections[case.case_id] = build_shadow_projection(
                baseline,
                observed,
            )
            return observed
        if replay_only is not None and replay_only.call_count:
            raise RoleBAblationInvariantError(
                f"gated journal miss attempted provider call:{case.case_id}"
            )
        return observed

    return execute, {
        "replay_delegates": replay_delegates,
        "shadow_projections": shadow_projections,
        "retrieval_calls": retrieval_calls,
    }


def _mode_identity(
    *,
    mode: str,
    subset: Mapping[str, Any],
    coverage: Mapping[str, Any],
    code_fingerprint: str,
    runtime_config_hash: str,
    journal_hash: str | None,
    settings: Settings,
    profile: Mapping[str, Any],
    prompt_set_hash: str,
    schema_set_hash: str,
) -> dict[str, Any]:
    identity = {
        "split": "development",
        "subset_hash": subset.get("subset_hash"),
        "gold_manifest_hash": coverage.get("manifest_hash"),
        "code_fingerprint": code_fingerprint,
        "runtime_config_hash": runtime_config_hash,
        "evaluator_version": EVALUATOR_VERSION,
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
    }
    if mode in {"shadow", "gated"}:
        identity["llm_journal_hash"] = journal_hash
        identity["provider"] = settings.llm_provider
        identity["model"] = settings.llm_model
        identity["transport"] = str(profile.get("transport") or "")
        identity["prompt_set_hash"] = prompt_set_hash
        identity["schema_set_hash"] = schema_set_hash
    return identity


def _evaluate_modes(
    *,
    root: Path,
    output_root: Path,
    coverage_path: Path,
    coverage: Mapping[str, Any],
    subset: Mapping[str, Any],
    modes: Sequence[str],
    code_fingerprint: str,
    runtime_config_hash: str,
    journal_manifest: Mapping[str, Any],
    settings: Settings,
    profile: Mapping[str, Any],
    retrieval_calls: Mapping[
        str, Mapping[str, Sequence[Mapping[str, Any]]]
    ] | None = None,
) -> dict[str, Any]:
    mode_results: dict[str, dict[str, Any]] = {}
    case_ids = _case_ids(dict(subset))
    prompt_set_hash = _canonical_hash(
        {
            f"{task_name}:{prompt_version}": digest
            for (task_name, prompt_version), digest in sorted(
                _prompt_hashes(profile, settings.llm_provider).items()
            )
        }
    )
    schema_set_hash = _schema_set_hash()
    for mode in modes:
        mode_dir = output_root / mode
        results_path = mode_dir / "analysis_results.jsonl"
        _write_results_jsonl(mode_dir / "run", case_ids, results_path)
        evaluation_dir = mode_dir / "evaluation"
        summary = _evaluate(
            root=root,
            coverage_path=coverage_path,
            results_path=results_path,
            case_ids=case_ids,
            output_dir=evaluation_dir,
            log_path=mode_dir / "evaluation.log",
        )
        risk_rows = read_evaluator_csv(evaluation_dir / "risk_benchmark.csv")
        evidence_rows = read_evaluator_csv(evaluation_dir / "evidence_benchmark.csv")
        pipeline_trace = _retrieval_pipeline_trace(
            coverage=coverage,
            evidence_rows=evidence_rows,
            calls_by_case=(retrieval_calls or {}).get(mode, {}),
        )
        _safe_json_write(mode_dir / "pipeline_trace.json", pipeline_trace)
        canonical_hashes = {
            case_id: canonical_risk_evidence_calculation_hash(
                json.loads(
                    (mode_dir / "run" / case_id / "analysis_result.json").read_text(
                        encoding="utf-8"
                    )
                )
            )
            for case_id in case_ids
        }
        mode_results[mode] = {
            "identity": _mode_identity(
                mode=mode,
                subset=subset,
                coverage=coverage,
                code_fingerprint=code_fingerprint,
                runtime_config_hash=runtime_config_hash,
                journal_hash=str(journal_manifest.get("journal_hash") or "") or None,
                settings=settings,
                profile=profile,
                prompt_set_hash=prompt_set_hash,
                schema_set_hash=schema_set_hash,
            ),
            "canonical_result_hashes": canonical_hashes,
            "summary": summary,
            "risk_rows": risk_rows,
            "evidence_rows": evidence_rows,
            "failure_focus": _failure_focus(evaluation_dir),
        }
        artifacts = build_role_b_waterfall_artifacts(
            coverage_manifest=coverage,
            risk_rows=risk_rows,
            evidence_rows=evidence_rows,
            pipeline_trace=pipeline_trace,
        )
        mode_results[mode]["artifacts"] = artifacts
        _safe_json_write(mode_dir / "retrieval_waterfall.json", artifacts["retrieval_waterfall"])
        _safe_json_write(mode_dir / "risk_pipeline_waterfall.json", artifacts["risk_pipeline_waterfall"])

    monotonicity: dict[str, Any]
    if set(MODE_ORDER).issubset(mode_results):
        monotonicity = build_role_b_waterfall_artifacts(
            coverage_manifest=coverage,
            risk_rows=mode_results["gated"]["risk_rows"],
            evidence_rows=mode_results["gated"]["evidence_rows"],
            mode_results=mode_results,
        )["monotonicity_report"]
        _safe_json_write(output_root / "monotonicity_report.json", monotonicity)
    else:
        monotonicity = {
            "status": "NOT_PROVEN",
            "satisfied": "NOT_PROVEN",
            "reasons": ["offline_shadow_gated_required"],
            "validation_opened": False,
            "blind_2025_outcome_accessed": False,
        }
        _safe_json_write(output_root / "monotonicity_report.json", monotonicity)
    return {"modes": mode_results, "monotonicity": monotonicity}


def _metric_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    risk = summary.get("risk_extraction") or {}
    evidence = summary.get("evidence_coverage") or {}
    return {
        "m1": risk.get("official_aligned_accuracy"),
        "m2": evidence.get("coverage_recall"),
        "per_risk": risk.get("per_risk") or {},
        "retrieval_diagnostics": summary.get("retrieval_diagnostics") or {},
        "evaluable_positive_risk_unit_count": risk.get("evaluable_positive_count"),
        "evaluable_evidence_unit_count": evidence.get("evaluable_existing_gold_count"),
    }


def _llm_call_quality(
    journal_manifest: Mapping[str, Any],
    *,
    transport: str,
    gated_replay_executed: bool,
) -> dict[str, Any]:
    risk_codes = {
        "shareholder_rights_extract": "redemption_rights",
        "litigation_compliance_extract": "material_litigation_compliance",
        "business_precommercial_commercialization_extract": "precommercial_product",
        "business_precommercial_core_product_extract": "precommercial_product",
    }
    calls: list[dict[str, Any]] = []
    for item in journal_manifest.get("records") or []:
        task_name = str(item.get("task_name") or "")
        calls.append(
            {
                "case_id": item.get("case_id"),
                "risk_code": risk_codes.get(task_name),
                "task_name": task_name,
                "provider": item.get("provider"),
                "model": item.get("model"),
                "transport": transport,
                "prompt_version": item.get("prompt_version"),
                "prompt_hash": item.get("prompt_hash"),
                "schema_hash": item.get("response_schema_hash"),
                "allowed_evidence_count": item.get("allowed_evidence_count"),
                "attempt_count": item.get("attempt_count"),
                "transport_retry_count": item.get("transport_retry_count"),
                "structured_correction_count": item.get("structured_correction_count"),
                "latency_ms": item.get("latency_ms"),
                "structured_valid": item.get("structured_valid"),
                "failure_kind": item.get("failure_kind"),
                "scope_valid": item.get("scope_valid"),
                "out_of_scope_ids": item.get("out_of_scope_ids") or [],
                "fallback_used": (
                    item.get("outcome") != "success"
                    or item.get("structured_valid") is not True
                    or item.get("scope_valid") is not True
                ),
                "journal_reused": gated_replay_executed,
            }
        )
    valid = sum(
        item["structured_valid"] is True and item["scope_valid"] is True
        for item in calls
    )
    return {
        "report_version": "v046_role_b_llm_call_quality_v1",
        "call_count": len(calls),
        "real_llm_case_count": len(
            {str(item["case_id"]) for item in calls if item.get("case_id")}
        ),
        "structured_scope_valid_count": valid,
        "structured_scope_valid_rate": valid / len(calls) if calls else None,
        "transport_failure_count": sum(
            item["failure_kind"] == LLMFailureKind.TRANSPORT.value for item in calls
        ),
        "response_validation_failure_count": sum(
            item["failure_kind"] == LLMFailureKind.RESPONSE_VALIDATION.value
            for item in calls
        ),
        "scope_rejection_count": sum(item["scope_valid"] is False for item in calls),
        "fallback_count": sum(item["fallback_used"] for item in calls),
        "calls": calls,
        "raw_prompt_persisted": False,
        "raw_response_persisted": False,
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
    }


def _write_governed_run_artifacts(
    *,
    output_root: Path,
    subset: Mapping[str, Any],
    coverage: Mapping[str, Any],
    git_state: Mapping[str, Any],
    preflight: Mapping[str, Any],
    profile: Mapping[str, Any],
    journal_manifest: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    modes: Sequence[str],
) -> None:
    mode_results = evaluation.get("modes") or {}
    summaries = {
        mode: _metric_summary(payload.get("summary") or {})
        for mode, payload in mode_results.items()
    }
    monotonicity = evaluation.get("monotonicity") or {}
    selected_mode = (
        "gated"
        if monotonicity.get("satisfied") is True and "gated" in mode_results
        else "offline"
    )
    selected = summaries.get(selected_mode) or {}
    prompt_hashes = preflight.get("prompt_hashes") or {}
    baseline_manifest = {
        "manifest_version": "v046_role_b_baseline_manifest_v1",
        "git_head": git_state.get("git_head"),
        "code_fingerprint": git_state.get("code_fingerprint"),
        "git_dirty_at_execution": git_state.get("git_dirty"),
        "subset_hash": subset.get("subset_hash"),
        "parent_subset_hash": subset.get("parent_subset_hash"),
        "case_count": subset.get("case_count"),
        "gold_manifest_hash": coverage.get("manifest_hash"),
        "metric_protocol_version": coverage.get("metric_protocol_version"),
        "provider": preflight.get("effective_provider"),
        "model": preflight.get("effective_model"),
        "transport": preflight.get("transport"),
        "prompt_hashes": prompt_hashes,
        "schema_set_hash": _schema_set_hash(),
        "runtime_config_hash": preflight.get("runtime_config_hash"),
        "modes": list(modes),
        "offline": summaries.get("offline"),
        "new_manual_annotations_added": False,
        "existing_gold_modified": False,
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
    }
    _safe_json_write(output_root / "baseline_manifest.json", baseline_manifest)

    call_quality = _llm_call_quality(
        journal_manifest,
        transport=str(profile.get("transport") or ""),
        gated_replay_executed="gated" in mode_results,
    )
    fixed10_target_reached = (
        subset.get("case_count") == 10
        and call_quality.get("real_llm_case_count") == 10
        and monotonicity.get("satisfied") is True
        and isinstance((summaries.get("gated") or {}).get("m1"), (int, float))
        and isinstance((summaries.get("gated") or {}).get("m2"), (int, float))
        and float(summaries["gated"]["m1"]) >= 0.80
        and float(summaries["gated"]["m2"]) >= 0.85
    )
    _safe_json_write(output_root / "llm_call_quality.json", call_quality)
    ablation_summary = {
        "report_version": "v046_role_b_ablation_summary_v1",
        "case_count": subset.get("case_count"),
        "modes": summaries,
        "llm_quality": {
            key: call_quality.get(key)
            for key in (
                "call_count",
                "real_llm_case_count",
                "structured_scope_valid_count",
                "structured_scope_valid_rate",
                "transport_failure_count",
                "response_validation_failure_count",
                "scope_rejection_count",
                "fallback_count",
            )
        },
        "monotonicity_satisfied": monotonicity.get("satisfied"),
        "fixed10_target_reached": fixed10_target_reached,
        "selected_mode": selected_mode,
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
    }
    _safe_json_write(output_root / "ablation_summary.json", ablation_summary)

    selected_payload = mode_results.get(selected_mode) or {}
    selected_artifacts = selected_payload.get("artifacts") or {}
    for name in ("retrieval_waterfall", "risk_pipeline_waterfall"):
        artifact = dict(selected_artifacts.get(name) or {})
        artifact["selected_mode"] = selected_mode
        _safe_json_write(output_root / f"{name}.json", artifact)
    failure_focus = dict(selected_payload.get("failure_focus") or {})
    failure_focus.update(
        {
            "report_version": "v046_role_b_failure_focus_v1",
            "selected_mode": selected_mode,
            "validation_opened": False,
            "blind_2025_outcome_accessed": False,
        }
    )
    _safe_json_write(output_root / "failure_focus.json", failure_focus)
    _safe_json_write(
        output_root / "best_iteration.json",
        {
            "report_version": "v046_role_b_best_iteration_v1",
            "selected_mode": selected_mode,
            "m1": selected.get("m1"),
            "m2": selected.get("m2"),
            "real_llm_candidate_accepted": selected_mode == "gated",
            "monotonicity_satisfied": monotonicity.get("satisfied"),
            "fixed10_target_reached": fixed10_target_reached,
            "full_development_executed": False,
            "validation_opened": False,
            "blind_2025_outcome_accessed": False,
        },
    )


def _parse_modes(value: str) -> tuple[str, ...]:
    if value == "all":
        return MODE_ORDER
    modes = tuple(item.strip() for item in value.split(",") if item.strip())
    unknown = set(modes) - set(MODE_ORDER)
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown modes:{sorted(unknown)}")
    return modes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--coverage-manifest", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--subset", type=Path, default=DEFAULT_SUBSET)
    parser.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--smoke-summary", type=Path, default=DEFAULT_SMOKE_SUMMARY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", default="run_001")
    parser.add_argument("--modes", type=_parse_modes, default=MODE_ORDER)
    parser.add_argument("--subset-size", type=int, default=10)
    parser.add_argument("--case-id", action="append")
    parser.add_argument("--subset-only", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="required before any PDF analysis or remote Role-B call",
    )
    parser.add_argument("--prospectus-root", type=Path, default=None)
    args = parser.parse_args()

    root = args.root.resolve()
    resolved = lambda path: path if path.is_absolute() else root / path
    config_path = resolved(args.config)
    coverage_path = resolved(args.coverage_manifest)
    subset_path = resolved(args.subset)
    bridge_path = resolved(args.bridge)
    catalog_path = resolved(args.catalog)
    smoke_summary_path = resolved(args.smoke_summary)
    output_root = resolved(args.output_root) / args.run_id

    coverage = _ensure_coverage(root, coverage_path)
    subset = _load_or_create_subset(subset_path, coverage, size=args.subset_size)
    validate_development_only_manifest(subset)
    case_ids = _case_ids(subset)
    if args.case_id:
        requested = tuple(dict.fromkeys(args.case_id))
        if not set(requested).issubset(case_ids):
            raise RoleBAblationRunnerError("case filter is outside the frozen fixed-10")
        subset = dict(subset)
        parent_subset_hash = str(subset.get("subset_hash") or "")
        subset["cases"] = [item for item in subset["cases"] if item["case_id"] in requested]
        subset["case_count"] = len(subset["cases"])
        subset["selection_scope"] = "fixed10_child_filter"
        subset["parent_subset_hash"] = parent_subset_hash
        subset["subset_hash"] = _subset_identity_hash(subset)
        case_ids = list(requested)

    if args.subset_only:
        print(f"subset_hash={subset.get('subset_hash')}")
        print("case_ids=" + ",".join(case_ids))
        print("scope=development_only; validation=false; blind_2025=false")
        return 0

    settings = load_settings(str(config_path))
    profile = _read_profile(config_path)
    modes = tuple(args.modes)
    preflight = _preflight(
        config_path=config_path,
        settings=settings,
        profile=profile,
        require_remote=RoleBAblationMode.SHADOW.value in modes and not args.preflight_only,
    )
    git_state = _git_state(root)
    runtime_hash = _runtime_config_hash(settings, profile, git_state["code_fingerprint"])
    preflight["runtime_config_hash"] = runtime_hash
    preflight["code_fingerprint"] = git_state["code_fingerprint"]
    preflight["structured_smoke"] = _smoke_gate(
        path=smoke_summary_path,
        settings=settings,
        profile=profile,
    )
    _safe_json_write(output_root / "preflight.json", preflight)
    if args.preflight_only:
        print(json.dumps(preflight, ensure_ascii=False, sort_keys=True))
        return 0
    if not args.execute:
        raise RoleBAblationRunnerError(
            "refusing PDF/LLM execution without explicit --execute"
        )
    if (
        RoleBAblationMode.SHADOW.value in modes
        and preflight["structured_smoke"]["passed"] is not True
    ):
        raise RoleBAblationRunnerError(
            "the matching 3/3 synthetic structured smoke must pass before fixed-10"
        )

    prospectus_root = args.prospectus_root
    if prospectus_root is None and os.getenv(PROSPECTUS_ROOT_ENV):
        prospectus_root = Path(os.environ[PROSPECTUS_ROOT_ENV])
    if prospectus_root is None or not prospectus_root.is_dir():
        raise RoleBAblationRunnerError("licensed prospectus root is unavailable")

    runtime_cases_path = output_root / "runtime_cases.json"
    _build_runtime_cases_manifest(subset, bridge_path, runtime_cases_path)
    runtime_cases = _runtime_cases(runtime_cases_path)
    catalog = _read_catalog(catalog_path, "case_id")
    bridge = _read_catalog(bridge_path, "case_id")
    journal = LocalLLMJournal(output_root / "journal")
    prompt_hashes = _prompt_hashes(profile, settings.llm_provider)
    execute_mode, diagnostics = _case_executor(
        settings=settings,
        profile=profile,
        prompt_hashes=prompt_hashes,
        runtime_config_hash=runtime_hash,
        output_root=output_root,
        journal=journal,
    )

    statuses: list[dict[str, Any]] = []
    for ordinal, case_row in enumerate(runtime_cases, start=1):
        case = _load_case_inputs(
            case=case_row,
            catalog=catalog,
            bridge=bridge,
            prospectus_root=prospectus_root,
        )
        results = orchestrate_case_modes(
            case=case,
            modes=modes,
            execute_mode=execute_mode,
        )
        for mode, result in results.items():
            destination = output_root / mode / "run" / case.case_id / "analysis_result.json"
            _safe_json_write(destination, _analysis_json(result))
        statuses.append(
            {
                "ordinal": ordinal,
                "case_id": case.case_id,
                "modes": {
                    mode: {
                        "status": result.status.value,
                        "canonical_hash": canonical_risk_evidence_calculation_hash(result),
                    }
                    for mode, result in results.items()
                },
            }
        )
        print(f"[{ordinal:02d}/{len(runtime_cases):02d}] {case.case_id} modes={','.join(results)}")

    journal_manifest = _journal_manifest(journal)
    _safe_json_write(output_root / "journal_manifest.json", journal_manifest)
    _safe_json_write(output_root / "case_statuses.json", statuses)
    _safe_json_write(
        output_root / "shadow_diagnostics.json",
        {
            "cases": diagnostics["shadow_projections"],
            "raw_prompt_persisted": False,
            "raw_response_persisted": False,
            "validation_opened": False,
            "blind_2025_outcome_accessed": False,
        },
    )

    evaluation = _evaluate_modes(
        root=root,
        output_root=output_root,
        coverage_path=coverage_path,
        coverage=coverage,
        subset=subset,
        modes=modes,
        code_fingerprint=git_state["code_fingerprint"],
        runtime_config_hash=runtime_hash,
        journal_manifest=journal_manifest,
        settings=settings,
        profile=profile,
        retrieval_calls=diagnostics["retrieval_calls"],
    )
    _write_governed_run_artifacts(
        output_root=output_root,
        subset=subset,
        coverage=coverage,
        git_state=git_state,
        preflight=preflight,
        profile=profile,
        journal_manifest=journal_manifest,
        evaluation=evaluation,
        modes=modes,
    )
    print(f"output_root={output_root}")
    print(f"journal_records={journal_manifest['record_count']}")
    print("scope=development_only; validation=false; blind_2025=false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (IterationRunnerError, RoleBAblationRunnerError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
