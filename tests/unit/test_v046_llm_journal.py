from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from pydantic import BaseModel, Field
import pytest

from ipo_risk.providers.llm import LLMFailureKind, LLMProviderError
from ipo_risk.runtime.llm_journal import (
    JournaledLLMProvider,
    LLMJournalCollisionError,
    LLMJournalIdentity,
    LLMJournalIntegrityError,
    LLMJournalPolicyError,
    LLMJournalRecord,
    LLMJournalScopeError,
    LLMJournalSecurityError,
    LocalLLMJournal,
)
from ipo_risk.schemas import Evidence, LLMCallMetadata


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


class _Result(BaseModel):
    finding: str
    evidence_ids: list[str] = Field(min_length=1)


class _OtherResult(BaseModel):
    finding: str
    confidence: float
    evidence_ids: list[str] = Field(min_length=1)


class _Delegate:
    name = "openai_responses"
    model = "test-model"

    def __init__(self, result: BaseModel | Exception) -> None:
        self.result = result
        self.calls = 0
        self.last_call_metadata = None
        self.last_failure_diagnostics = None
        self.last_attempt_trace = []

    def complete(self, prompt: str) -> str:
        return "legacy"

    def generate_structured(self, **kwargs):
        self.calls += 1
        self.last_call_metadata = LLMCallMetadata(
            provider_name=self.name,
            model_name=self.model,
            prompt_version=kwargs["prompt_version"],
            latency_ms=9,
            token_usage={"prompt_tokens": 3, "completion_tokens": 2},
            request_id="remote-request-id-must-be-hashed",
            raw_response_hash=_digest("raw remote response not persisted"),
        )
        if isinstance(self.result, Exception):
            self.last_attempt_trace = [
                {
                    "stage": "transport",
                    "structured_attempt": 1,
                    "attempt": 1,
                    "outcome": "failure",
                    "failure_kind": "transport",
                    "recoverable": True,
                    "retry_scheduled": True,
                },
                {
                    "stage": "transport",
                    "structured_attempt": 1,
                    "attempt": 2,
                    "outcome": "failure",
                    "failure_kind": "transport",
                    "recoverable": True,
                    "retry_scheduled": False,
                },
            ]
            self.last_failure_diagnostics = {
                "stage": "transport",
                "failure_kind": "transport",
                "recoverable": True,
                "attempts": 2,
                "secret": "ark-must-never-persist",
                "local_path": r"C:\Users\must-not-persist\response.json",
            }
            raise self.result
        self.last_attempt_trace = [
            {
                "stage": "transport",
                "structured_attempt": 1,
                "attempt": 1,
                "outcome": "success",
            },
            {
                "stage": "structured_validation",
                "structured_attempt": 1,
                "outcome": "success",
            },
        ]
        return self.result


def _evidence(evidence_id: str = "ev-1", text: str = "bounded raw Evidence") -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        document_id="development-document",
        chunk_id=f"chunk:{evidence_id}",
        page=7,
        section="legal",
        text=text,
        metadata={"local_path": r"C:\Users\must-not-persist\prospectus.pdf"},
    )


def _wrapper(
    tmp_path: Path,
    delegate: _Delegate,
    *,
    prompt_hash: str | None = None,
    case_id: str = "ipo_2020_00001",
) -> JournaledLLMProvider:
    return JournaledLLMProvider(
        delegate,
        journal=LocalLLMJournal(tmp_path / "journal"),
        case_id=case_id,
        dataset_split="development",
        transport="responses",
        prompt_hashes={
            ("shareholder_rights_extract", "legal_shareholder_rights_v1"): (
                prompt_hash or _digest("complete structured prompt")
            )
        },
        runtime_config_hash=_digest("safe effective config"),
    )


def _identity(
    *,
    evidence: list[Evidence] | None = None,
    response_model: type[BaseModel] = _Result,
    **overrides,
) -> LLMJournalIdentity:
    values = {
        "case_id": "ipo_2020_00001",
        "dataset_split": "development",
        "task_name": "shareholder_rights_extract",
        "provider": "openai_responses",
        "model": "test-model",
        "transport": "responses",
        "prompt_version": "legal_shareholder_rights_v1",
        "prompt_hash": _digest("prompt"),
        "response_model": response_model,
        "evidence": evidence or [_evidence()],
        "runtime_config_hash": _digest("runtime"),
    }
    values.update(overrides)
    return LLMJournalIdentity.from_call(**values)


@pytest.mark.parametrize("dataset_split", ["validation", "blind", "2025", ""])
def test_journal_is_development_only(tmp_path: Path, dataset_split: str) -> None:
    with pytest.raises(LLMJournalPolicyError):
        JournaledLLMProvider(
            _Delegate(_Result(finding="ok", evidence_ids=["ev-1"])),
            journal=LocalLLMJournal(tmp_path),
            case_id="ipo_2024_00001",
            dataset_split=dataset_split,
            transport="responses",
            prompt_hashes={},
            runtime_config_hash=_digest("runtime"),
        )


def test_identity_binds_every_governed_input_and_evidence_order() -> None:
    baseline = _identity(evidence=[_evidence("ev-1"), _evidence("ev-2")])
    variants = [
        baseline.model_copy(update={"case_id": "ipo_2020_00002"}),
        baseline.model_copy(update={"task_name": "litigation_compliance_extract"}),
        baseline.model_copy(update={"provider": "openai_compatible"}),
        baseline.model_copy(update={"model": "other-model"}),
        baseline.model_copy(update={"transport": "chat"}),
        baseline.model_copy(update={"prompt_version": "other-version"}),
        baseline.model_copy(update={"prompt_hash": _digest("other-prompt")}),
        baseline.model_copy(update={"response_schema_hash": _digest("other-schema")}),
        baseline.model_copy(
            update={"ordered_allowed_evidence_ids": ("ev-2", "ev-1")}
        ),
        baseline.model_copy(update={"evidence_content_hash": _digest("other-evidence")}),
        baseline.model_copy(update={"runtime_config_hash": _digest("other-runtime")}),
    ]
    assert len({baseline.identity_hash, *(item.identity_hash for item in variants)}) == 12

    other_schema = _identity(
        evidence=[_evidence("ev-1"), _evidence("ev-2")],
        response_model=_OtherResult,
    )
    changed_content = _identity(
        evidence=[_evidence("ev-1", "changed"), _evidence("ev-2")]
    )
    assert other_schema.identity_hash != baseline.identity_hash
    assert changed_content.identity_hash != baseline.identity_hash


def test_ark_model_identifier_is_allowed_but_ark_api_key_shape_is_rejected() -> None:
    identity = _identity(model="ark-code-latest")
    assert identity.model == "ark-code-latest"

    with pytest.raises(LLMJournalSecurityError):
        ark_key_shaped_value = "ark-" + "-".join(
            ("0" * 8, "0" * 4, "0" * 4, "0" * 4, "0" * 12)
        )
        _identity(model=ark_key_shaped_value)

    with pytest.raises(LLMJournalSecurityError):
        _identity(model="01234567-89ab-cdef-0123-456789abcdef")


def test_uuid_evidence_ids_are_allowed_only_in_evidence_identifier_fields(
    tmp_path: Path,
) -> None:
    evidence_id = "3232d18f-8a5e-5599-a18f-2ab9118467ea"
    delegate = _Delegate(_Result(finding="supported", evidence_ids=[evidence_id]))
    wrapper = _wrapper(tmp_path, delegate)

    result = wrapper.generate_structured(
        task_name="shareholder_rights_extract",
        prompt_version="legal_shareholder_rights_v1",
        evidence=[_evidence(evidence_id)],
        response_model=_Result,
    )

    assert result.evidence_ids == [evidence_id]
    identity = wrapper.last_journal_identity
    assert identity is not None
    record = wrapper.journal.read(identity)
    assert record is not None
    assert record.identity.ordered_allowed_evidence_ids == (evidence_id,)
    assert record.structured_payload == {
        "finding": "supported",
        "evidence_ids": [evidence_id],
    }

    with pytest.raises(LLMJournalSecurityError):
        LLMJournalRecord.build(
            identity=identity,
            outcome="success",
            structured_payload={
                "finding": evidence_id,
                "evidence_ids": [evidence_id],
            },
            structured_valid=True,
            scope_valid=True,
            attempt_count=1,
            latency_ms=1,
        )


def test_success_is_write_once_safe_and_replays_without_network(tmp_path: Path) -> None:
    first_delegate = _Delegate(_Result(finding="supported", evidence_ids=["ev-1"]))
    first = _wrapper(tmp_path, first_delegate)

    result = first.generate_structured(
        task_name="shareholder_rights_extract",
        prompt_version="legal_shareholder_rights_v1",
        evidence=[_evidence(text="raw Evidence must not persist")],
        response_model=_Result,
    )
    assert result.finding == "supported"
    assert first_delegate.calls == 1
    assert first.last_journal_reused is False

    identity = first.last_journal_identity
    assert identity is not None
    path = first.journal.record_path(identity)
    persisted = path.read_text(encoding="utf-8")
    assert "raw Evidence must not persist" not in persisted
    assert "remote-request-id-must-be-hashed" not in persisted
    assert "raw remote response not persisted" not in persisted
    assert "C:\\Users" not in persisted
    assert "api_key" not in persisted
    assert "base_url" not in persisted
    assert json.loads(persisted)["structured_payload"] == {
        "finding": "supported",
        "evidence_ids": ["ev-1"],
    }
    persisted_record = json.loads(persisted)
    assert persisted_record["attempt_count"] == 1
    assert persisted_record["transport_retry_count"] == 0
    assert persisted_record["structured_correction_count"] == 0
    assert persisted_record["failure_diagnostics"] == {}
    assert not list(path.parent.glob("*.tmp"))

    second_delegate = _Delegate(AssertionError("network must not be called"))
    second = _wrapper(tmp_path, second_delegate)
    replayed = second.generate_structured(
        task_name="shareholder_rights_extract",
        prompt_version="legal_shareholder_rights_v1",
        evidence=[_evidence(text="raw Evidence must not persist")],
        response_model=_Result,
    )
    assert replayed == result
    assert second_delegate.calls == 0
    assert second.last_journal_reused is True


def test_out_of_scope_result_is_recorded_and_replayed_fail_closed(tmp_path: Path) -> None:
    first_delegate = _Delegate(_Result(finding="bad", evidence_ids=["ev-outside"]))
    first = _wrapper(tmp_path, first_delegate)
    call = {
        "task_name": "shareholder_rights_extract",
        "prompt_version": "legal_shareholder_rights_v1",
        "evidence": [_evidence()],
        "response_model": _Result,
    }
    with pytest.raises(LLMJournalScopeError):
        first.generate_structured(**call)
    assert first_delegate.calls == 1

    identity = first.last_journal_identity
    assert identity is not None
    record = first.journal.read(identity)
    assert record is not None
    assert record.outcome == "failure"
    assert record.failure_kind == "scope_validation"
    assert record.out_of_scope_ids == ("ev-outside",)
    assert record.structured_payload is None

    replay_delegate = _Delegate(AssertionError("network must not be called"))
    replay = _wrapper(tmp_path, replay_delegate)
    with pytest.raises(LLMJournalScopeError):
        replay.generate_structured(**call)
    assert replay_delegate.calls == 0


def test_provider_failure_is_safely_recorded_and_replayed(tmp_path: Path) -> None:
    failure = LLMProviderError(
        LLMFailureKind.TRANSPORT,
        "safe failure",
        recoverable=True,
        attempts=2,
    )
    first_delegate = _Delegate(failure)
    first = _wrapper(tmp_path, first_delegate)
    call = {
        "task_name": "shareholder_rights_extract",
        "prompt_version": "legal_shareholder_rights_v1",
        "evidence": [_evidence()],
        "response_model": _Result,
    }
    with pytest.raises(LLMProviderError):
        first.generate_structured(**call)

    identity = first.last_journal_identity
    assert identity is not None
    record = first.journal.read(identity)
    assert record is not None
    assert record.failure_kind == "transport"
    assert record.attempt_count == 2
    assert record.transport_retry_count == 1
    assert record.structured_correction_count == 0
    assert record.failure_diagnostics == {
        "stage": "transport",
        "failure_kind": "transport",
        "recoverable": True,
        "attempts": 2,
    }
    persisted = first.journal.record_path(identity).read_text(encoding="utf-8")
    assert "ark-must-never-persist" not in persisted
    assert "must-not-persist" not in persisted

    replay_delegate = _Delegate(AssertionError("network must not be called"))
    replay = _wrapper(tmp_path, replay_delegate)
    with pytest.raises(LLMProviderError) as captured:
        replay.generate_structured(**call)
    assert captured.value.kind == LLMFailureKind.TRANSPORT
    assert captured.value.attempts == 2
    assert replay_delegate.calls == 0


def test_corruption_and_write_collision_fail_closed(tmp_path: Path) -> None:
    delegate = _Delegate(_Result(finding="supported", evidence_ids=["ev-1"]))
    wrapper = _wrapper(tmp_path, delegate)
    wrapper.generate_structured(
        task_name="shareholder_rights_extract",
        prompt_version="legal_shareholder_rights_v1",
        evidence=[_evidence()],
        response_model=_Result,
    )
    identity = wrapper.last_journal_identity
    assert identity is not None
    record = wrapper.journal.read(identity)
    assert record is not None

    different = LLMJournalRecord.build(
        identity=identity,
        outcome="success",
        structured_payload={"finding": "different", "evidence_ids": ["ev-1"]},
        structured_valid=True,
        scope_valid=True,
        attempt_count=1,
        latency_ms=1,
    )
    with pytest.raises(LLMJournalCollisionError):
        wrapper.journal.write(different)

    path = wrapper.journal.record_path(identity)
    path.write_text("{not valid JSON", encoding="utf-8")
    replay = _wrapper(tmp_path, _Delegate(AssertionError("network must not be called")))
    with pytest.raises(LLMJournalIntegrityError):
        replay.generate_structured(
            task_name="shareholder_rights_extract",
            prompt_version="legal_shareholder_rights_v1",
            evidence=[_evidence()],
            response_model=_Result,
        )
    assert replay.delegate.calls == 0


def test_exact_prompt_hash_is_required_before_delegate_call(tmp_path: Path) -> None:
    delegate = _Delegate(_Result(finding="supported", evidence_ids=["ev-1"]))
    wrapper = JournaledLLMProvider(
        delegate,
        journal=LocalLLMJournal(tmp_path),
        case_id="ipo_2020_00001",
        dataset_split="development",
        transport="responses",
        prompt_hashes={},
        runtime_config_hash=_digest("runtime"),
    )
    with pytest.raises(LLMJournalPolicyError):
        wrapper.generate_structured(
            task_name="shareholder_rights_extract",
            prompt_version="legal_shareholder_rights_v1",
            evidence=[_evidence()],
            response_model=_Result,
        )
    assert delegate.calls == 0


def test_recovered_structured_correction_is_counted_without_terminal_failure(
    tmp_path: Path,
) -> None:
    delegate = _Delegate(_Result(finding="supported", evidence_ids=["ev-1"]))
    original = delegate.generate_structured

    def recovered(**kwargs):
        result = original(**kwargs)
        delegate.last_attempt_trace = [
            {
                "stage": "transport",
                "structured_attempt": 1,
                "attempt": 1,
                "outcome": "success",
            },
            {
                "stage": "structured_validation",
                "structured_attempt": 1,
                "outcome": "failure",
                "failure_kind": "pydantic_validation",
                "retry_scheduled": True,
            },
            {
                "stage": "transport",
                "structured_attempt": 2,
                "attempt": 1,
                "outcome": "success",
            },
            {
                "stage": "structured_validation",
                "structured_attempt": 2,
                "outcome": "success",
            },
        ]
        delegate.last_failure_diagnostics = {
            "stage": "pydantic_validation",
            "structured_attempt": 1,
            "errors": [{"path": "finding", "type": "string_type"}],
        }
        return result

    delegate.generate_structured = recovered
    wrapper = _wrapper(tmp_path, delegate)
    wrapper.generate_structured(
        task_name="shareholder_rights_extract",
        prompt_version="legal_shareholder_rights_v1",
        evidence=[_evidence()],
        response_model=_Result,
    )
    identity = wrapper.last_journal_identity
    assert identity is not None
    record = wrapper.journal.read(identity)
    assert record is not None
    assert record.outcome == "success"
    assert record.attempt_count == 2
    assert record.transport_retry_count == 0
    assert record.structured_correction_count == 1
    assert record.failure_diagnostics == {}


def test_chat_compatible_schema_correction_is_not_counted_as_transport_retry(
    tmp_path: Path,
) -> None:
    delegate = _Delegate(_Result(finding="supported", evidence_ids=["ev-1"]))
    original = delegate.generate_structured

    def recovered(**kwargs):
        result = original(**kwargs)
        delegate.last_attempt_trace = [
            {
                "stage": "structured_validation",
                "attempt": 1,
                "outcome": "failure",
                "failure_kind": "response_validation",
                "retry_scheduled": True,
            },
            {"stage": "request", "attempt": 2, "outcome": "success"},
        ]
        return result

    delegate.generate_structured = recovered
    wrapper = _wrapper(tmp_path, delegate)
    wrapper.generate_structured(
        task_name="shareholder_rights_extract",
        prompt_version="legal_shareholder_rights_v1",
        evidence=[_evidence()],
        response_model=_Result,
    )
    identity = wrapper.last_journal_identity
    assert identity is not None
    record = wrapper.journal.read(identity)
    assert record is not None
    assert record.attempt_count == 2
    assert record.transport_retry_count == 0
    assert record.structured_correction_count == 1


def test_responses_bounded_normalization_is_recorded_as_structured_correction(
    tmp_path: Path,
) -> None:
    delegate = _Delegate(_Result(finding="supported", evidence_ids=["ev-1"]))
    original = delegate.generate_structured

    def normalized(**kwargs):
        result = original(**kwargs)
        delegate.last_attempt_trace = [
            {
                "stage": "transport",
                "structured_attempt": 1,
                "attempt": 1,
                "outcome": "success",
            },
            {
                "stage": "bounded_normalization",
                "structured_attempt": 1,
                "outcome": "success",
                "fields": ["amount"],
            },
            {
                "stage": "structured_validation",
                "structured_attempt": 1,
                "outcome": "success",
            },
        ]
        return result

    delegate.generate_structured = normalized
    wrapper = _wrapper(tmp_path, delegate)
    wrapper.generate_structured(
        task_name="shareholder_rights_extract",
        prompt_version="legal_shareholder_rights_v1",
        evidence=[_evidence()],
        response_model=_Result,
    )
    identity = wrapper.last_journal_identity
    assert identity is not None
    record = wrapper.journal.read(identity)
    assert record is not None
    assert record.attempt_count == 1
    assert record.transport_retry_count == 0
    assert record.structured_correction_count == 1
