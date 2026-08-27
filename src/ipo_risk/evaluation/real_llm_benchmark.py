"""Fail-closed controls for the Role-B real-LLM Development benchmark.

This module contains no orchestration and performs no network I/O.  It keeps
authorization, request counting, payload isolation, Evidence scope and compact
metadata rules independently testable before any prospectus Evidence is sent.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from threading import Lock
from typing import Any

from ipo_risk.schemas import Evidence, LLMCallMetadata


FROZEN_BASE_URL = "https://ark.cn-beijing.volces.com/api/coding/v3"
FROZEN_MODEL_ALIAS = "glm-5.3"
MAX_HTTP_REQUESTS = 60
DEVELOPMENT_CASE_IDS = (
    "ipo_2020_01167",
    "ipo_2020_01942",
    "ipo_2020_01961",
    "ipo_2020_09600",
    "ipo_2020_09633",
    "ipo_2021_09898",
    "ipo_2022_06698",
    "ipo_2022_09863",
    "ipo_2023_02451",
    "ipo_2023_02517",
)
ROLE_B_RISK_CODES = (
    "redemption_rights",
    "material_litigation_compliance",
    "precommercial_product",
)
FORBIDDEN_MODEL_INPUT_KEYS = frozenset(
    {
        "gold",
        "gold_exact_text",
        "gold_physical_page",
        "applicable",
        "expected_status",
        "expected_level",
        "expert_annotation",
        "validation_receipt",
        "ground_truth",
    }
)


class RealLLMBenchmarkError(RuntimeError):
    """A frozen authorization or benchmark invariant failed."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def secret_presence(environ: Mapping[str, str]) -> dict[str, str]:
    """Return presence booleans only; never expose a secret value."""

    names = (
        "IPO_RISK_LLM_API_KEY",
        "IPO_RISK_LLM_BASE_URL",
        "IPO_RISK_LLM_MODEL",
    )
    return {name: "SET" if environ.get(name) else "MISSING" for name in names}


def validate_frozen_environment(environ: Mapping[str, str]) -> None:
    """Fail before provider construction when authorization is incomplete."""

    if not environ.get("IPO_RISK_LLM_API_KEY"):
        raise RealLLMBenchmarkError("BLOCKED_SECRET_NOT_AVAILABLE")
    if not environ.get("IPO_RISK_LLM_BASE_URL"):
        raise RealLLMBenchmarkError("BLOCKED_BASE_URL_NOT_AVAILABLE")
    if environ["IPO_RISK_LLM_BASE_URL"] != FROZEN_BASE_URL:
        raise RealLLMBenchmarkError("BLOCKED_BASE_URL_MISMATCH")
    if not environ.get("IPO_RISK_LLM_MODEL"):
        raise RealLLMBenchmarkError("BLOCKED_MODEL_NOT_AVAILABLE")
    if environ["IPO_RISK_LLM_MODEL"] != FROZEN_MODEL_ALIAS:
        raise RealLLMBenchmarkError("BLOCKED_MODEL_MISMATCH")


def validate_case_ids(case_ids: Sequence[str]) -> tuple[str, ...]:
    requested = tuple(case_ids)
    if not requested or len(requested) != len(set(requested)):
        raise RealLLMBenchmarkError("INVALID_CASE_SELECTION")
    if any(case_id not in DEVELOPMENT_CASE_IDS for case_id in requested):
        raise RealLLMBenchmarkError("NON_DEVELOPMENT_CASE_REJECTED")
    return tuple(case_id for case_id in DEVELOPMENT_CASE_IDS if case_id in requested)


def _walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            keys.add(str(key).casefold())
            keys.update(_walk_keys(child))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            keys.update(_walk_keys(child))
    return keys


def assert_gold_free_payload(payload: Any) -> None:
    forbidden = sorted(_walk_keys(payload) & FORBIDDEN_MODEL_INPUT_KEYS)
    if forbidden:
        raise RealLLMBenchmarkError("GOLD_PAYLOAD_REJECTED")


def assert_evidence_scope(returned_ids: Sequence[str], evidence: Sequence[Evidence]) -> None:
    allowed = {item.evidence_id for item in evidence}
    if any(evidence_id not in allowed for evidence_id in returned_ids):
        raise RealLLMBenchmarkError("LLM_EVIDENCE_OUT_OF_SCOPE")


def synthetic_evidence() -> list[Evidence]:
    """Return identity-free fictional Evidence for the first structured call."""

    return [
        Evidence(
            evidence_id="synthetic-evidence-1",
            document_id="synthetic-document",
            chunk_id="synthetic-chunk-1",
            page=1,
            section="Synthetic clause",
            text=(
                "A fictional company's special right terminates on listing and may "
                "be restored only if its fictional listing application lapses."
            ),
            relevance_score=1.0,
        )
    ]


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()


@dataclass
class RequestBudget:
    """Thread-safe counter placed immediately before each HTTP request."""

    limit: int = MAX_HTTP_REQUESTS
    _count: int = 0
    _lock: Lock = field(default_factory=Lock, repr=False)

    def acquire(self) -> int:
        with self._lock:
            if self._count >= self.limit:
                raise RealLLMBenchmarkError("REQUEST_BUDGET_EXHAUSTED")
            self._count += 1
            return self._count

    @property
    def count(self) -> int:
        with self._lock:
            return self._count


class BudgetedCompletions:
    """Count the actual Chat Completions transport call and retain hashes only."""

    def __init__(self, delegate: Any, budget: RequestBudget) -> None:
        self._delegate = delegate
        self._budget = budget
        self.last_attempt: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> Any:
        assert_gold_free_payload(kwargs)
        attempt = self._budget.acquire()
        self.last_attempt = {
            "attempt": attempt,
            "request_hash": canonical_hash(kwargs),
            "status": "started",
        }
        try:
            response = self._delegate.create(**kwargs)
        except Exception:
            self.last_attempt["status"] = "failed"
            raise
        self.last_attempt["status"] = "completed"
        return response


class BudgetedClient:
    """Minimal OpenAI client facade used by the existing provider unchanged."""

    def __init__(self, client: Any, budget: RequestBudget) -> None:
        self.chat = _ChatFacade(BudgetedCompletions(client.chat.completions, budget))


class AuditedStructuredProvider:
    """Wrap the frozen provider with scope checks and body-free call metadata."""

    name = "openai_compatible"

    def __init__(self, delegate: Any, budget: RequestBudget) -> None:
        self._delegate = delegate
        self._budget = budget
        self.calls: list[dict[str, Any]] = []

    @property
    def last_call_metadata(self) -> LLMCallMetadata | None:
        return self._delegate.last_call_metadata

    def generate_structured(
        self,
        *,
        task_name: str,
        prompt_version: str,
        evidence: list[Evidence],
        response_model: type[Any],
    ) -> Any:
        assert_gold_free_payload(
            {
                "task_name": task_name,
                "prompt_version": prompt_version,
                "evidence": [item.model_dump(mode="json") for item in evidence],
            }
        )
        before = self._budget.count
        try:
            result = self._delegate.generate_structured(
                task_name=task_name,
                prompt_version=prompt_version,
                evidence=evidence,
                response_model=response_model,
            )
        except Exception:
            self.calls.append(
                {
                    "task_name": task_name,
                    "prompt_version": prompt_version,
                    "attempt": self._budget.count,
                    "status": "failed",
                    "request_count_delta": self._budget.count - before,
                }
            )
            raise
        returned_ids = _collect_evidence_ids(result)
        assert_evidence_scope(returned_ids, evidence)
        metadata = self._delegate.last_call_metadata
        transport = self._delegate._client.chat.completions
        attempt = transport.last_attempt or {}
        if metadata is None:
            raise RealLLMBenchmarkError("LLM_CALL_METADATA_MISSING")
        record = compact_call_metadata(
            metadata,
            case_id="pending",
            risk_code="pending",
            task_name=task_name,
            schema_version=response_model.__name__,
            attempt=int(attempt.get("attempt") or self._budget.count),
            request_hash=str(attempt.get("request_hash") or ""),
        )
        record["evidence_input_count"] = len(evidence)
        record["evidence_output_count"] = len(returned_ids)
        self.calls.append(record)
        return result


def _collect_evidence_ids(value: Any) -> list[str]:
    """Collect citation ids from a validated model without retaining its body."""

    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) == "evidence_ids" and isinstance(child, Sequence) and not isinstance(
                child, (str, bytes, bytearray)
            ):
                found.extend(str(item) for item in child)
            else:
                found.extend(_collect_evidence_ids(child))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            found.extend(_collect_evidence_ids(child))
    return list(dict.fromkeys(found))


@dataclass
class _ChatFacade:
    completions: BudgetedCompletions


def compact_call_metadata(
    metadata: LLMCallMetadata,
    *,
    case_id: str,
    risk_code: str,
    task_name: str,
    schema_version: str,
    attempt: int,
    request_hash: str,
) -> dict[str, Any]:
    """Project provider metadata without request/response bodies or credentials."""

    usage = metadata.token_usage
    return {
        "case_id": case_id,
        "risk_code": risk_code,
        "task_name": task_name,
        "provider": metadata.provider_name,
        "model_alias": FROZEN_MODEL_ALIAS,
        "resolved_model": metadata.model_name,
        "prompt_version": metadata.prompt_version,
        "schema_version": schema_version,
        "attempt": attempt,
        "status": "completed",
        "latency_ms": metadata.latency_ms,
        "input_token_usage": usage.get("prompt_tokens"),
        "output_token_usage": usage.get("completion_tokens"),
        "request_hash": request_hash,
        "response_hash": metadata.raw_response_hash,
        "error_category": None,
    }


def build_protocol(
    *,
    source_revision: str,
    offline_baseline_revision: str,
    evaluator_hash: str,
    runner_hash: str,
    control_plane_selection_timestamp: str,
) -> dict[str, Any]:
    return {
        "protocol_version": "v045_role_b_real_llm_development_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_revision,
        "offline_baseline_revision": offline_baseline_revision,
        "evaluator_hash": evaluator_hash,
        "runner_hash": runner_hash,
        "development_case_ids": list(DEVELOPMENT_CASE_IDS),
        "provider": "volcengine_ark_coding_plan",
        "api_protocol": "openai_compatible_chat_completions",
        "base_url": FROZEN_BASE_URL,
        "api_model_alias": FROZEN_MODEL_ALIAS,
        "control_plane_selection": "GLM-5.3",
        "control_plane_selection_timestamp": control_plane_selection_timestamp,
        "resolved_model_identity": "pending",
        "timeout_seconds": 60,
        "max_retries": 0,
        "max_http_requests": MAX_HTTP_REQUESTS,
        "candidate_policy": "frozen keyword Retriever; all three Role-B risks per case",
        "evidence_scope_policy": "only bounded Retriever Evidence IDs; fail closed",
        "metric_definitions": {
            "risk": ["precision", "recall", "f1"],
            "evidence": ["recall_at_1", "recall_at_3", "recall_at_5"],
            "physical_page_correctness": "Gold physical-page equality",
        },
        "risk_codes": list(ROLE_B_RISK_CODES),
        "2024_validation_opened": False,
        "2025_blind_accessed": False,
    }


def validate_resume_identity(existing: Mapping[str, Any], expected: Mapping[str, Any]) -> None:
    identity_fields = (
        "case_id",
        "pdf_sha256",
        "source_revision",
        "config_sha256",
        "protocol_sha256",
    )
    if any(existing.get(key) != expected.get(key) for key in identity_fields):
        raise RealLLMBenchmarkError("RESUME_IDENTITY_MISMATCH")
