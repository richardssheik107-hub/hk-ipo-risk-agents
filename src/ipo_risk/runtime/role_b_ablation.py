"""Opt-in Role-B ablation primitives with no effect on the v0.4.5 runtime.

The production container deliberately has one shared LLM provider.  A Role-B
ablation must be narrower: only the two Legal and two Business structured tasks
may reach the journaled provider, while every other task degrades through the
ordinary zero-network unavailable provider.  This module supplies that routing,
a shadow Agent wrapper, and a semantic Risk/Evidence/Calculation projection
used for monotonicity. Durable record/replay is owned exclusively by
``runtime.llm_journal``.

Nothing in this module is registered by the default container.  Callers must
opt in explicitly from the v0.4.6 ablation runner.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import StrEnum
from hashlib import sha256
import json
from typing import Any, TypeVar

from pydantic import BaseModel

from ipo_risk.providers.llm import UnavailableLLMProvider
from ipo_risk.runtime.llm_journal import LLMJournalIdentity
from ipo_risk.schemas import Evidence, LLMCallMetadata, RiskItem


StructuredModel = TypeVar("StructuredModel", bound=BaseModel)

ROLE_B_TASK_NAMES = frozenset(
    {
        "shareholder_rights_extract",
        "litigation_compliance_extract",
        "business_precommercial_commercialization_extract",
        "business_precommercial_core_product_extract",
    }
)


class RoleBAblationMode(StrEnum):
    OFFLINE = "offline"
    SHADOW = "shadow"
    GATED = "gated"


class RoleBAblationError(RuntimeError):
    """Fail-closed Role-B experiment error without provider payloads."""


class RoleBAblationScopeError(RoleBAblationError):
    """The requested cohort is not the frozen Development-only cohort."""


class RoleBAblationInvariantError(RoleBAblationError):
    """A shadow/journal monotonicity invariant was violated."""


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _hash(payload: Any) -> str:
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


_SAFE_DIAGNOSTIC_SCALARS = frozenset(
    {
        "task_name",
        "stage",
        "status",
        "outcome",
        "failure_kind",
        "error_type",
        "recoverable",
        "attempts",
        "attempt_count",
        "transport_retry_count",
        "structured_correction_count",
        "latency_ms",
        "request_id_hash",
        "raw_response_hash",
        "prompt_hash",
        "response_schema_hash",
    }
)


def _safe_diagnostic_projection(value: Any) -> dict[str, Any]:
    """Retain bounded observability without copying model or Evidence prose."""

    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    if not isinstance(value, Mapping):
        return {
            "diagnostic_type": type(value).__name__,
            "diagnostic_hash": _hash(value),
        }
    safe = {
        key: item
        for key, item in value.items()
        if key in _SAFE_DIAGNOSTIC_SCALARS
        and (isinstance(item, (str, int, float, bool)) or item is None)
    }
    safe["diagnostic_keys"] = sorted(str(key) for key in value)
    safe["diagnostic_hash"] = _hash(value)
    return safe


def _model_payload(value: BaseModel | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError("expected a Pydantic model or mapping")


def _evidence_projection(value: BaseModel | Mapping[str, Any]) -> dict[str, Any]:
    payload = _model_payload(value)
    text = str(payload.get("text") or "")
    # The hash binds the exact Evidence text without copying licensed source
    # prose into an ablation summary.
    return {
        "evidence_id": payload.get("evidence_id"),
        "document_id": payload.get("document_id"),
        "chunk_id": payload.get("chunk_id"),
        "page": payload.get("page"),
        "section": payload.get("section") or "",
        "text_sha256": sha256(text.encode("utf-8")).hexdigest(),
        "bbox": payload.get("bbox"),
        "source_type": payload.get("source_type"),
        "relevance_score": payload.get("relevance_score"),
    }


def _calculation_projection(
    value: BaseModel | Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if value is None:
        return None
    payload = _model_payload(value)
    return {
        "skill_name": payload.get("skill_name"),
        "skill_version": payload.get("skill_version"),
        "inputs": payload.get("inputs") or {},
        "formula": payload.get("formula"),
        "result": payload.get("result"),
        "unit": payload.get("unit") or "",
        "evidence_ids": sorted(str(item) for item in payload.get("evidence_ids") or []),
        "success": payload.get("success"),
        "error": payload.get("error"),
    }


def _risk_projection(value: RiskItem | Mapping[str, Any]) -> dict[str, Any]:
    payload = _model_payload(value)
    evidence = [_evidence_projection(item) for item in payload.get("evidence") or []]
    evidence.sort(key=_canonical_json)
    return {
        # risk_id and created_at are intentionally excluded: they are runtime
        # identities/timestamps rather than a semantic Risk decision.
        "risk_code": payload.get("risk_code"),
        "category": payload.get("category"),
        "risk_type": payload.get("risk_type"),
        "level": payload.get("level"),
        "score": payload.get("score"),
        "conclusion": payload.get("conclusion"),
        "evidence": evidence,
        "calculation": _calculation_projection(payload.get("calculation")),
        "agent_name": payload.get("agent_name"),
        "confidence": payload.get("confidence"),
        "verification_status": payload.get("verification_status"),
        "verification_notes": payload.get("verification_notes") or "",
        # metadata is excluded because it carries diagnostics and transport
        # observations.  Those belong to the shadow sidecar, not canonical risk.
    }


def canonical_risk_evidence_calculation_projection(
    result: BaseModel | Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Project only final Risk/Evidence/Calculation semantics.

    Analysis ids, request ids, timestamps, logs, report prose, component
    diagnostics and other run metadata are deliberately not part of this hash.
    """

    payload = _model_payload(result)
    projected: dict[str, list[dict[str, Any]]] = {}
    for bucket in ("verified_risks", "pending_risks", "rejected_risks"):
        risks = [_risk_projection(item) for item in payload.get(bucket) or []]
        risks.sort(key=_canonical_json)
        projected[bucket] = risks
    return projected


def canonical_risk_evidence_calculation_hash(
    result: BaseModel | Mapping[str, Any],
) -> str:
    return _hash(canonical_risk_evidence_calculation_projection(result))


def validate_development_only_manifest(manifest: Mapping[str, Any]) -> tuple[str, ...]:
    """Validate the fixed cohort before any provider can be called."""

    if manifest.get("split") != "development":
        raise RoleBAblationScopeError("Role-B ablation requires split=development")
    if manifest.get("validation_opened") is not False:
        raise RoleBAblationScopeError("Role-B ablation requires validation_opened=false")
    if manifest.get("blind_2025_outcome_accessed") is not False:
        raise RoleBAblationScopeError(
            "Role-B ablation requires blind_2025_outcome_accessed=false"
        )
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise RoleBAblationScopeError("Role-B ablation requires a non-empty cases list")

    case_ids: list[str] = []
    for case in cases:
        if not isinstance(case, Mapping):
            raise RoleBAblationScopeError("Role-B ablation case rows must be objects")
        case_id = str(case.get("case_id") or "")
        if not case_id or case_id in case_ids:
            raise RoleBAblationScopeError(
                "Role-B ablation case ids must be unique and non-empty"
            )
        observed_split = case.get("split", case.get("dataset_split"))
        if observed_split is not None and observed_split != "development":
            raise RoleBAblationScopeError(
                f"Role-B ablation rejected non-Development case {case_id}"
            )
        # The frozen repository policy defines 2024 as Validation and 2025 as
        # Blind.  Refuse both even when a malformed row omits its split.
        if case_id.startswith("ipo_2024_") or case_id.startswith("ipo_2025_"):
            raise RoleBAblationScopeError(
                f"Role-B ablation rejected governed non-Development case {case_id}"
            )
        case_ids.append(case_id)
    return tuple(case_ids)


class TaskRoutingProvider:
    """Route only the frozen Role-B structured tasks to a delegate."""

    name = "role_b_task_router"

    def __init__(
        self,
        role_b_provider: Any,
        unavailable_provider: UnavailableLLMProvider | None = None,
    ) -> None:
        self.role_b_provider = role_b_provider
        self.unavailable_provider = unavailable_provider or UnavailableLLMProvider(
            "This task is outside the Role-B ablation scope"
        )
        self.last_call_metadata: LLMCallMetadata | None = None
        self.last_route: dict[str, Any] = {}

    def complete(self, prompt: str) -> str:
        self.last_route = {"task_name": None, "route": "unavailable"}
        return self.unavailable_provider.complete(prompt)

    def generate_structured(
        self,
        *,
        task_name: str,
        prompt_version: str,
        evidence: list[Evidence],
        response_model: type[StructuredModel],
    ) -> StructuredModel:
        provider = (
            self.role_b_provider
            if task_name in ROLE_B_TASK_NAMES
            else self.unavailable_provider
        )
        route = "role_b" if task_name in ROLE_B_TASK_NAMES else "unavailable"
        self.last_route = {"task_name": task_name, "route": route}
        try:
            return provider.generate_structured(
                task_name=task_name,
                prompt_version=prompt_version,
                evidence=evidence,
                response_model=response_model,
            )
        finally:
            self.last_call_metadata = getattr(provider, "last_call_metadata", None)


class ShadowRiskAgent:
    """Call a real probe Agent but return only the offline baseline result."""

    def __init__(self, baseline_agent: Any, probe_agent: Any) -> None:
        if getattr(baseline_agent, "name", None) != getattr(probe_agent, "name", None):
            raise RoleBAblationInvariantError("shadow Agent names must match")
        self.name = baseline_agent.name
        self.baseline_agent = baseline_agent
        self.probe_agent = probe_agent
        self.last_diagnostics: Any = None
        self.last_probe_diagnostics: Any = None
        self.last_probe_error_type: str | None = None

    def analyze(self, profile: Any, chunks: list[Any], market: Any = None) -> list[RiskItem]:
        baseline = self.baseline_agent.analyze(profile, chunks, market)
        self.last_diagnostics = getattr(self.baseline_agent, "last_diagnostics", None)
        try:
            self.probe_agent.analyze(profile, chunks, market)
            self.last_probe_diagnostics = getattr(
                self.probe_agent, "last_diagnostics", None
            )
            self.last_probe_error_type = None
        except Exception as exc:  # shadow failure cannot change canonical output
            self.last_probe_diagnostics = None
            self.last_probe_error_type = type(exc).__name__
        return baseline

    def probe_summary(self) -> dict[str, Any]:
        diagnostics = self.last_probe_diagnostics
        if isinstance(diagnostics, Sequence) and not isinstance(diagnostics, (str, bytes)):
            projected = [_safe_diagnostic_projection(item) for item in diagnostics]
        else:
            projected = [_safe_diagnostic_projection(diagnostics)]
        return {
            "agent": self.name,
            "probe_error_type": self.last_probe_error_type,
            "probe_diagnostics": projected,
        }


def build_shadow_projection(
    offline_result: BaseModel | Mapping[str, Any],
    shadow_final_result: BaseModel | Mapping[str, Any],
    *,
    journal_identities: Sequence[LLMJournalIdentity] = (),
    probe_diagnostics: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Bind probe observability to an unchanged offline canonical result."""

    offline_projection = canonical_risk_evidence_calculation_projection(offline_result)
    shadow_projection = canonical_risk_evidence_calculation_projection(shadow_final_result)
    offline_hash = _hash(offline_projection)
    shadow_hash = _hash(shadow_projection)
    if shadow_hash != offline_hash:
        raise RoleBAblationInvariantError(
            "shadow final Risk/Evidence/Calculation output differs from offline"
        )
    identity_summaries: list[dict[str, Any]] = []
    for identity in journal_identities:
        if not isinstance(identity, LLMJournalIdentity):
            raise TypeError("journal identities must be durable LLMJournalIdentity values")
        summary = identity.model_dump(mode="json")
        summary["identity_hash"] = identity.identity_hash
        identity_summaries.append(summary)
    return {
        "mode": RoleBAblationMode.SHADOW.value,
        "final_canonical_projection": offline_projection,
        "final_canonical_hash": offline_hash,
        "offline_canonical_hash": offline_hash,
        "canonical_equal_to_offline": True,
        "llm_may_modify_final": False,
        "journal_identities": identity_summaries,
        "llm_call_diagnostics": [
            _safe_diagnostic_projection(item) for item in probe_diagnostics
        ],
    }


__all__ = [
    "ROLE_B_TASK_NAMES",
    "RoleBAblationError",
    "RoleBAblationInvariantError",
    "RoleBAblationMode",
    "RoleBAblationScopeError",
    "ShadowRiskAgent",
    "TaskRoutingProvider",
    "build_shadow_projection",
    "canonical_risk_evidence_calculation_hash",
    "canonical_risk_evidence_calculation_projection",
    "validate_development_only_manifest",
]
