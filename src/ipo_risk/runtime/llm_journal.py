"""Local, write-once replay journal for governed structured LLM calls.

The journal is deliberately an opt-in wrapper around the existing ``LLMProvider``
protocol.  It does not change that public protocol and it never persists request
prompts, Evidence text, credentials, endpoints, local paths, or raw responses.
Only Development calls are accepted.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from time import perf_counter
from typing import Any, Literal, TypeVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ipo_risk.providers.llm import LLMFailureKind, LLMProviderError
from ipo_risk.schemas import Evidence, LLMCallMetadata


StructuredModel = TypeVar("StructuredModel", bound=BaseModel)
JOURNAL_VERSION = "v046_llm_journal_v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_WINDOWS_ABSOLUTE_RE = re.compile(r"(?i)(?:^|[\s\"'])(?:[a-z]:[\\/]|\\\\)")
_POSIX_HOME_RE = re.compile(r"(?:^|[\s\"'])(?:/Users/|/home/|/root/)")
_SECRET_VALUE_RE = re.compile(
    r"(?i)(?:"
    r"\bbearer\s+\S+"
    r"|\bsk-[a-z0-9_-]{16,}"
    # Volcengine Ark credentials use a UUID-shaped secret identifier, commonly
    # followed by a short suffix.  Do not reject public model identifiers such
    # as ``ark-code-latest`` merely because they share the vendor prefix.
    r"|\bark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    r"(?:-[a-z0-9]{4,})?"
    r")"
)
_BARE_UUID_RE = re.compile(
    r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
)
_EVIDENCE_IDENTIFIER_KEYS = frozenset(
    {
        "evidence_id",
        "evidence_ids",
        "ordered_allowed_evidence_ids",
        "out_of_scope_ids",
    }
)
_FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "base_url",
        "prompt",
        "raw_prompt",
        "raw_evidence",
        "evidence_text",
        "raw_response",
        "response_text",
        "request_body",
        "local_path",
    }
)
_SAFE_DIAGNOSTIC_KEYS = frozenset(
    {
        "stage",
        "failure_kind",
        "recoverable",
        "attempts",
        "structured_attempt",
        "arguments_length",
        "first_char_class",
        "arguments_hash",
        "arguments_present",
        "output_types",
        "errors",
    }
)


class LLMJournalError(RuntimeError):
    """Base class for local journal failures."""


class LLMJournalPolicyError(LLMJournalError):
    """Raised when a call is outside the Development-only policy."""


class LLMJournalIntegrityError(LLMJournalError):
    """Raised when persisted journal content cannot be trusted."""


class LLMJournalCollisionError(LLMJournalIntegrityError):
    """Raised when one immutable identity has two different records."""


class LLMJournalScopeError(LLMJournalError):
    """Raised when structured output cites Evidence outside the allowed set."""


class LLMJournalSecurityError(LLMJournalError):
    """Raised before unsafe content can be persisted."""


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _hash_value(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _hash_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _is_sha256(value: str | None) -> bool:
    return bool(value and _SHA256_RE.fullmatch(value))


def _assert_safe_text(value: str, *, allow_bare_uuid: bool = False) -> None:
    if _WINDOWS_ABSOLUTE_RE.search(value) or _POSIX_HOME_RE.search(value):
        raise LLMJournalSecurityError("Local absolute paths cannot enter the LLM journal")
    if _SECRET_VALUE_RE.search(value) or (
        not allow_bare_uuid and _BARE_UUID_RE.search(value)
    ):
        raise LLMJournalSecurityError("Credential-like values cannot enter the LLM journal")


def _assert_safe_persisted(value: Any, *, key: str = "") -> None:
    normalized_key = key.casefold()
    if normalized_key in _FORBIDDEN_KEYS:
        raise LLMJournalSecurityError("Forbidden raw or credential field in LLM journal")
    if isinstance(value, Mapping):
        for child_key, child_value in value.items():
            _assert_safe_persisted(child_value, key=str(child_key))
    elif isinstance(value, (list, tuple)):
        for child in value:
            # Evidence IDs are stable UUIDs in production.  Keep the parent
            # field context while walking the sequence so those identifiers
            # are not confused with bare-UUID Coding Plan credentials.
            _assert_safe_persisted(child, key=key)
    elif isinstance(value, str):
        _assert_safe_text(
            value,
            allow_bare_uuid=normalized_key in _EVIDENCE_IDENTIFIER_KEYS,
        )


def _safe_token(
    value: str,
    *,
    field_name: str,
    allow_bare_uuid: bool = False,
) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty")
    _assert_safe_text(normalized, allow_bare_uuid=allow_bare_uuid)
    if any(separator in normalized for separator in ("/", "\\")):
        raise ValueError(f"{field_name} cannot contain path separators")
    return normalized


def _evidence_request_identity(evidence: Sequence[Evidence]) -> list[dict[str, Any]]:
    """Mirror only the fields sent by the current structured Providers.

    The returned value exists only long enough to be hashed.  It is never written
    to the journal, so Evidence text and document identity remain local.
    """

    return [
        {
            "evidence_id": item.evidence_id,
            "document_id": item.document_id,
            "chunk_id": item.chunk_id,
            "page": item.page,
            "section": item.section,
            "text": item.text,
            "source_type": item.source_type.value,
            "relevance_score": item.relevance_score,
        }
        for item in evidence
    ]


def _collect_evidence_ids(value: Any) -> set[str]:
    collected: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key == "evidence_ids" and isinstance(child, list):
                collected.update(item for item in child if isinstance(item, str))
            elif key == "evidence_id" and isinstance(child, str):
                collected.add(child)
            else:
                collected.update(_collect_evidence_ids(child))
    elif isinstance(value, list):
        for child in value:
            collected.update(_collect_evidence_ids(child))
    return collected


def _safe_failure_diagnostics(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    safe: dict[str, Any] = {}
    for key in _SAFE_DIAGNOSTIC_KEYS:
        if key not in value:
            continue
        item = value[key]
        if key == "errors" and isinstance(item, list):
            safe[key] = [
                {
                    field: str(error[field])
                    for field in ("path", "type")
                    if isinstance(error, Mapping) and field in error
                }
                for error in item[:8]
                if isinstance(error, Mapping)
            ]
        elif isinstance(item, (str, int, bool)) or item is None:
            safe[key] = item
        elif key == "output_types" and isinstance(item, list):
            safe[key] = [str(output_type) for output_type in item[:16]]
    _assert_safe_persisted(safe)
    return safe


def _attempt_counts(
    value: Any,
    *,
    fallback_attempts: int = 1,
    fallback_failure_kind: str | None = None,
) -> tuple[int, int, int]:
    """Derive request, transport-retry and schema-correction counts safely.

    Responses traces have one ``transport`` row per actual network request and a
    separate ``structured_validation`` row.  Chat-compatible traces have one
    terminal row per request.  Supporting both shapes here keeps the journal
    wrapper Provider-neutral without persisting the trace itself.
    """

    trace = [item for item in value or [] if isinstance(item, Mapping)]
    responses_transport = [
        item
        for item in trace
        if item.get("stage") == "transport" and "structured_attempt" in item
    ]
    if responses_transport:
        attempt_count = len(responses_transport)
        transport_retry_count = sum(
            1
            for item in trace
            if item.get("stage") == "transport"
            and item.get("outcome") == "failure"
            and item.get("retry_scheduled") is True
        )
        structured_correction_count = sum(
            1
            for item in trace
            if item.get("stage") == "structured_validation"
            and item.get("outcome") == "failure"
            and item.get("retry_scheduled") is True
        )
        return attempt_count, transport_retry_count, structured_correction_count

    compatible_attempts = [
        item
        for item in trace
        if item.get("stage") in {"request", "transport", "structured_validation"}
        and isinstance(item.get("attempt"), int)
    ]
    if compatible_attempts:
        attempt_count = len(compatible_attempts)
        transport_retry_count = sum(
            1
            for item in compatible_attempts
            if item.get("stage") == "transport"
            and item.get("outcome") == "failure"
            and item.get("retry_scheduled") is True
        )
        structured_correction_count = sum(
            1
            for item in compatible_attempts
            if item.get("stage") == "structured_validation"
            and item.get("retry_scheduled") is True
        )
        return attempt_count, transport_retry_count, structured_correction_count

    attempt_count = max(0, int(fallback_attempts))
    if fallback_failure_kind == LLMFailureKind.TRANSPORT.value:
        return attempt_count, max(0, attempt_count - 1), 0
    if fallback_failure_kind == LLMFailureKind.RESPONSE_VALIDATION.value:
        return attempt_count, 0, max(0, attempt_count - 1)
    return attempt_count, 0, 0


class LLMJournalIdentity(BaseModel):
    """Complete immutable identity for one replayable structured call."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    journal_version: Literal["v046_llm_journal_v1"] = JOURNAL_VERSION
    case_id: str
    dataset_split: Literal["development"]
    task_name: str
    provider: str
    model: str
    transport: str
    prompt_version: str
    prompt_hash: str
    response_model: str
    response_schema_hash: str
    ordered_allowed_evidence_ids: tuple[str, ...]
    evidence_content_hash: str
    runtime_config_hash: str

    @field_validator(
        "case_id",
        "task_name",
        "provider",
        "model",
        "transport",
        "prompt_version",
        "response_model",
    )
    @classmethod
    def _validate_safe_token(cls, value: str, info: Any) -> str:
        return _safe_token(value, field_name=info.field_name)

    @field_validator(
        "prompt_hash",
        "response_schema_hash",
        "evidence_content_hash",
        "runtime_config_hash",
    )
    @classmethod
    def _validate_hash(cls, value: str, info: Any) -> str:
        if not _is_sha256(value):
            raise ValueError(f"{info.field_name} must be a lowercase SHA-256 digest")
        return value

    @field_validator("ordered_allowed_evidence_ids")
    @classmethod
    def _validate_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("ordered Evidence IDs must be unique")
        for evidence_id in value:
            _safe_token(
                evidence_id,
                field_name="evidence_id",
                allow_bare_uuid=True,
            )
        return value

    @classmethod
    def from_call(
        cls,
        *,
        case_id: str,
        dataset_split: str,
        task_name: str,
        provider: str,
        model: str,
        transport: str,
        prompt_version: str,
        prompt_hash: str,
        response_model: type[BaseModel],
        evidence: Sequence[Evidence],
        runtime_config_hash: str,
    ) -> "LLMJournalIdentity":
        if dataset_split.strip().casefold() != "development":
            raise LLMJournalPolicyError(
                "The reusable LLM journal accepts Development calls only"
            )
        model_name = f"{response_model.__module__}.{response_model.__qualname__}"
        schema_hash = _hash_value(response_model.model_json_schema())
        ordered_ids = tuple(item.evidence_id for item in evidence)
        content_hash = _hash_value(_evidence_request_identity(evidence))
        return cls(
            case_id=case_id,
            dataset_split="development",
            task_name=task_name,
            provider=provider,
            model=model,
            transport=transport,
            prompt_version=prompt_version,
            prompt_hash=prompt_hash,
            response_model=model_name,
            response_schema_hash=schema_hash,
            ordered_allowed_evidence_ids=ordered_ids,
            evidence_content_hash=content_hash,
            runtime_config_hash=runtime_config_hash,
        )

    @property
    def identity_hash(self) -> str:
        return _hash_value(self.model_dump(mode="json"))


class LLMJournalRecord(BaseModel):
    """Safe persisted terminal outcome for one immutable call identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    journal_version: Literal["v046_llm_journal_v1"] = JOURNAL_VERSION
    identity: LLMJournalIdentity
    identity_hash: str
    outcome: Literal["success", "failure"]
    structured_payload: dict[str, Any] | None = None
    structured_payload_hash: str | None = None
    structured_valid: bool
    scope_valid: bool | None = None
    out_of_scope_ids: tuple[str, ...] = ()
    failure_kind: str | None = None
    recoverable: bool | None = None
    attempt_count: int = Field(ge=0)
    transport_retry_count: int = Field(ge=0)
    structured_correction_count: int = Field(ge=0)
    latency_ms: int = Field(ge=0)
    token_usage: dict[str, int] = Field(default_factory=dict)
    request_id_hash: str | None = None
    response_hash: str | None = None
    failure_diagnostics: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    record_hash: str

    @field_validator(
        "identity_hash",
        "structured_payload_hash",
        "request_id_hash",
        "response_hash",
        "record_hash",
    )
    @classmethod
    def _validate_optional_hash(cls, value: str | None, info: Any) -> str | None:
        if value is not None and not _is_sha256(value):
            raise ValueError(f"{info.field_name} must be a lowercase SHA-256 digest")
        return value

    @classmethod
    def build(
        cls,
        *,
        identity: LLMJournalIdentity,
        outcome: Literal["success", "failure"],
        structured_payload: dict[str, Any] | None,
        structured_valid: bool,
        scope_valid: bool | None,
        out_of_scope_ids: Sequence[str] = (),
        failure_kind: str | None = None,
        recoverable: bool | None = None,
        attempt_count: int,
        transport_retry_count: int = 0,
        structured_correction_count: int = 0,
        latency_ms: int,
        token_usage: Mapping[str, int] | None = None,
        request_id: str = "",
        response_hash: str | None = None,
        failure_diagnostics: Mapping[str, Any] | None = None,
    ) -> "LLMJournalRecord":
        payload_hash = _hash_value(structured_payload) if structured_payload is not None else None
        body: dict[str, Any] = {
            "journal_version": JOURNAL_VERSION,
            "identity": identity.model_dump(mode="json"),
            "identity_hash": identity.identity_hash,
            "outcome": outcome,
            "structured_payload": structured_payload,
            "structured_payload_hash": payload_hash,
            "structured_valid": structured_valid,
            "scope_valid": scope_valid,
            "out_of_scope_ids": sorted(set(out_of_scope_ids)),
            "failure_kind": failure_kind,
            "recoverable": recoverable,
            "attempt_count": max(0, int(attempt_count)),
            "transport_retry_count": max(0, int(transport_retry_count)),
            "structured_correction_count": max(0, int(structured_correction_count)),
            "latency_ms": max(0, int(latency_ms)),
            "token_usage": {
                str(key): int(value) for key, value in (token_usage or {}).items()
            },
            "request_id_hash": _hash_text(request_id) if request_id else None,
            "response_hash": response_hash if _is_sha256(response_hash) else None,
            "failure_diagnostics": _safe_failure_diagnostics(failure_diagnostics),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _assert_safe_persisted(body)
        body["record_hash"] = _hash_value(body)
        return cls.model_validate(body)

    def verify(self, expected_identity: LLMJournalIdentity) -> None:
        if self.identity != expected_identity:
            raise LLMJournalIntegrityError("Journal identity does not match the call")
        if self.identity_hash != self.identity.identity_hash:
            raise LLMJournalIntegrityError("Journal identity hash is invalid")
        body = self.model_dump(mode="json", exclude={"record_hash"})
        if self.record_hash != _hash_value(body):
            raise LLMJournalIntegrityError("Journal record hash is invalid")
        if self.structured_payload is None:
            if self.structured_payload_hash is not None:
                raise LLMJournalIntegrityError("Journal payload hash has no payload")
        elif self.structured_payload_hash != _hash_value(self.structured_payload):
            raise LLMJournalIntegrityError("Journal structured payload hash is invalid")
        _assert_safe_persisted(self.model_dump(mode="json"))


class LocalLLMJournal:
    """Development-only immutable JSON journal stored below a caller-owned root."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def record_path(self, identity: LLMJournalIdentity) -> Path:
        return self.root / f"{identity.identity_hash}.json"

    def read(self, identity: LLMJournalIdentity) -> LLMJournalRecord | None:
        path = self.record_path(identity)
        if not path.exists():
            return None
        try:
            raw = path.read_text(encoding="utf-8")
            parsed = json.loads(raw)
            record = LLMJournalRecord.model_validate(parsed)
            record.verify(identity)
            return record
        except LLMJournalError:
            raise
        except Exception:
            raise LLMJournalIntegrityError("Journal record is unreadable or invalid") from None

    def write(self, record: LLMJournalRecord) -> Path:
        record.verify(record.identity)
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.record_path(record.identity)
        if target.exists():
            existing = self.read(record.identity)
            if existing is not None and existing.record_hash == record.record_hash:
                return target
            raise LLMJournalCollisionError(
                "A different immutable record already exists for this identity"
            )

        payload = _canonical_json(record.model_dump(mode="json")) + "\n"
        temporary = self.root / f".{record.identity_hash}.{uuid4().hex}.tmp"
        try:
            with temporary.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary, target)
            except FileExistsError:
                existing = self.read(record.identity)
                if existing is None or existing.record_hash != record.record_hash:
                    raise LLMJournalCollisionError(
                        "Concurrent journal writers produced different records"
                    ) from None
        finally:
            if temporary.exists():
                temporary.unlink()
        return target

    def replay(
        self,
        record: LLMJournalRecord,
        *,
        identity: LLMJournalIdentity,
        response_model: type[StructuredModel],
    ) -> StructuredModel:
        record.verify(identity)
        if record.outcome == "failure":
            if record.failure_kind == "scope_validation":
                raise LLMJournalScopeError("Replayed structured output violated Evidence scope")
            try:
                kind = LLMFailureKind(record.failure_kind or "request")
            except ValueError:
                raise LLMJournalIntegrityError("Unknown replayed failure kind") from None
            raise LLMProviderError(
                kind,
                "Replayed local LLM journal failure",
                recoverable=bool(record.recoverable),
                attempts=record.attempt_count,
            )

        if not record.structured_valid or record.structured_payload is None:
            raise LLMJournalIntegrityError("Successful journal record is not structured-valid")
        try:
            result = response_model.model_validate(record.structured_payload)
        except Exception:
            raise LLMJournalIntegrityError(
                "Replayed payload no longer matches the response model"
            ) from None
        cited_ids = _collect_evidence_ids(result.model_dump(mode="json"))
        allowed_ids = set(identity.ordered_allowed_evidence_ids)
        out_of_scope = sorted(cited_ids - allowed_ids)
        if out_of_scope or record.scope_valid is not True or record.out_of_scope_ids:
            raise LLMJournalScopeError("Replayed structured output violated Evidence scope")
        return result


class JournaledLLMProvider:
    """Same-protocol Provider wrapper with strict local Development replay."""

    def __init__(
        self,
        delegate: Any,
        *,
        journal: LocalLLMJournal,
        case_id: str,
        dataset_split: str,
        transport: str,
        prompt_hashes: Mapping[tuple[str, str], str],
        runtime_config_hash: str,
    ) -> None:
        if dataset_split.strip().casefold() != "development":
            raise LLMJournalPolicyError(
                "The reusable LLM journal accepts Development calls only"
            )
        if not _is_sha256(runtime_config_hash):
            raise ValueError("runtime_config_hash must be a lowercase SHA-256 digest")
        self.delegate = delegate
        self.journal = journal
        self.case_id = _safe_token(case_id, field_name="case_id")
        self.dataset_split = "development"
        self.transport = _safe_token(transport, field_name="transport")
        self.prompt_hashes = dict(prompt_hashes)
        self.runtime_config_hash = runtime_config_hash
        self.name = str(getattr(delegate, "name", "unknown"))
        self.model = str(getattr(delegate, "model", "unknown"))
        self.last_journal_reused = False
        self.last_journal_identity: LLMJournalIdentity | None = None

    @property
    def last_call_metadata(self) -> LLMCallMetadata | None:
        return getattr(self.delegate, "last_call_metadata", None)

    @property
    def last_failure_diagnostics(self) -> dict[str, Any] | None:
        return getattr(self.delegate, "last_failure_diagnostics", None)

    def complete(self, prompt: str) -> str:
        """Keep legacy free text outside the structured replay journal."""

        return self.delegate.complete(prompt)

    def _identity(
        self,
        *,
        task_name: str,
        prompt_version: str,
        evidence: Sequence[Evidence],
        response_model: type[BaseModel],
    ) -> LLMJournalIdentity:
        prompt_hash = self.prompt_hashes.get((task_name, prompt_version))
        if not _is_sha256(prompt_hash):
            raise LLMJournalPolicyError("Exact prompt hash is required before journaling")
        return LLMJournalIdentity.from_call(
            case_id=self.case_id,
            dataset_split=self.dataset_split,
            task_name=task_name,
            provider=self.name,
            model=self.model,
            transport=self.transport,
            prompt_version=prompt_version,
            prompt_hash=prompt_hash,
            response_model=response_model,
            evidence=evidence,
            runtime_config_hash=self.runtime_config_hash,
        )

    @staticmethod
    def _metadata_parts(metadata: Any) -> tuple[dict[str, int], str, str]:
        if metadata is None:
            return {}, "", ""
        token_usage = {
            str(key): int(value)
            for key, value in getattr(metadata, "token_usage", {}).items()
        }
        return (
            token_usage,
            str(getattr(metadata, "request_id", "") or ""),
            str(getattr(metadata, "raw_response_hash", "") or ""),
        )

    def generate_structured(
        self,
        *,
        task_name: str,
        prompt_version: str,
        evidence: list[Evidence],
        response_model: type[StructuredModel],
    ) -> StructuredModel:
        identity = self._identity(
            task_name=task_name,
            prompt_version=prompt_version,
            evidence=evidence,
            response_model=response_model,
        )
        self.last_journal_identity = identity
        existing = self.journal.read(identity)
        if existing is not None:
            self.last_journal_reused = True
            return self.journal.replay(
                existing,
                identity=identity,
                response_model=response_model,
            )

        self.last_journal_reused = False
        before_metadata = getattr(self.delegate, "last_call_metadata", None)
        before_diagnostics = getattr(self.delegate, "last_failure_diagnostics", None)
        before_trace = getattr(self.delegate, "last_attempt_trace", None)
        started = perf_counter()
        try:
            raw_result = self.delegate.generate_structured(
                task_name=task_name,
                prompt_version=prompt_version,
                evidence=evidence,
                response_model=response_model,
            )
            result = response_model.model_validate(raw_result)
        except LLMProviderError as exc:
            metadata = getattr(self.delegate, "last_call_metadata", None)
            if metadata is before_metadata:
                metadata = None
            diagnostics = getattr(self.delegate, "last_failure_diagnostics", None)
            if diagnostics is before_diagnostics:
                diagnostics = None
            token_usage, request_id, response_hash = self._metadata_parts(metadata)
            attempt_trace = getattr(self.delegate, "last_attempt_trace", None)
            if attempt_trace is before_trace:
                attempt_trace = None
            attempt_count, transport_retries, structured_corrections = _attempt_counts(
                attempt_trace,
                fallback_attempts=exc.attempts,
                fallback_failure_kind=exc.kind.value,
            )
            record = LLMJournalRecord.build(
                identity=identity,
                outcome="failure",
                structured_payload=None,
                structured_valid=False,
                scope_valid=None,
                failure_kind=exc.kind.value,
                recoverable=exc.recoverable,
                attempt_count=attempt_count,
                transport_retry_count=transport_retries,
                structured_correction_count=structured_corrections,
                latency_ms=int((perf_counter() - started) * 1000),
                token_usage=token_usage,
                request_id=request_id,
                response_hash=response_hash,
                failure_diagnostics=diagnostics,
            )
            self.journal.write(record)
            raise

        payload = result.model_dump(mode="json")
        cited_ids = _collect_evidence_ids(payload)
        allowed_ids = set(identity.ordered_allowed_evidence_ids)
        out_of_scope = sorted(cited_ids - allowed_ids)
        metadata = getattr(self.delegate, "last_call_metadata", None)
        if metadata is before_metadata:
            metadata = None
        token_usage, request_id, response_hash = self._metadata_parts(metadata)
        diagnostics = getattr(self.delegate, "last_failure_diagnostics", None)
        if diagnostics is before_diagnostics:
            diagnostics = None
        safe_diagnostics = _safe_failure_diagnostics(diagnostics)
        attempt_trace = getattr(self.delegate, "last_attempt_trace", None)
        if attempt_trace is before_trace:
            attempt_trace = None
        attempt_count, transport_retries, structured_corrections = _attempt_counts(
            attempt_trace,
        )

        if out_of_scope:
            record = LLMJournalRecord.build(
                identity=identity,
                outcome="failure",
                structured_payload=None,
                structured_valid=True,
                scope_valid=False,
                out_of_scope_ids=out_of_scope,
                failure_kind="scope_validation",
                recoverable=False,
                attempt_count=attempt_count,
                transport_retry_count=transport_retries,
                structured_correction_count=structured_corrections,
                latency_ms=int((perf_counter() - started) * 1000),
                token_usage=token_usage,
                request_id=request_id,
                response_hash=response_hash,
                failure_diagnostics=safe_diagnostics,
            )
            self.journal.write(record)
            raise LLMJournalScopeError("Structured output cited out-of-scope Evidence")

        record = LLMJournalRecord.build(
            identity=identity,
            outcome="success",
            structured_payload=payload,
            structured_valid=True,
            scope_valid=True,
            attempt_count=attempt_count,
            transport_retry_count=transport_retries,
            structured_correction_count=structured_corrections,
            latency_ms=int((perf_counter() - started) * 1000),
            token_usage=token_usage,
            request_id=request_id,
            response_hash=response_hash,
            # A prior invalid attempt may leave diagnostics after a successful
            # bounded correction.  The safe attempt counters preserve that
            # history without mislabelling the terminal success as a failure.
            failure_diagnostics={},
        )
        self.journal.write(record)
        return result
