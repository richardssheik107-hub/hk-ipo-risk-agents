from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ipo_risk.evaluation.real_llm_benchmark import (
    AuditedStructuredProvider,
    BudgetedClient,
    DEVELOPMENT_CASE_IDS,
    FROZEN_BASE_URL,
    FROZEN_MODEL_ALIAS,
    RealLLMBenchmarkError,
    RequestBudget,
    assert_evidence_scope,
    assert_gold_free_payload,
    build_protocol,
    canonical_hash,
    compact_call_metadata,
    secret_presence,
    synthetic_evidence,
    validate_case_ids,
    validate_frozen_environment,
    validate_resume_identity,
)
from ipo_risk.agents.legal_models import ShareholderRightCandidate
from ipo_risk.schemas import LLMCallMetadata


SCRIPT = Path(__file__).parents[2] / "scripts" / "run_v045_role_b_real_llm_benchmark.py"
SPEC = importlib.util.spec_from_file_location("role_b_real_llm_benchmark", SCRIPT)
assert SPEC and SPEC.loader
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def _environment() -> dict[str, str]:
    return {
        "IPO_RISK_LLM_API_KEY": "unit-test-secret",
        "IPO_RISK_LLM_BASE_URL": FROZEN_BASE_URL,
        "IPO_RISK_LLM_MODEL": FROZEN_MODEL_ALIAS,
    }


def test_secret_presence_is_boolean_only_and_missing_secret_blocks() -> None:
    status = secret_presence(_environment())
    assert set(status.values()) == {"SET"}
    assert "unit-test-secret" not in json.dumps(status)
    with pytest.raises(RealLLMBenchmarkError, match="BLOCKED_SECRET_NOT_AVAILABLE"):
        validate_frozen_environment({})


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("IPO_RISK_LLM_BASE_URL", "https://example.invalid", "BASE_URL_MISMATCH"),
        ("IPO_RISK_LLM_MODEL", "another-model", "MODEL_MISMATCH"),
    ],
)
def test_endpoint_and_model_alias_are_frozen(field: str, value: str, code: str) -> None:
    environ = _environment()
    environ[field] = value
    with pytest.raises(RealLLMBenchmarkError, match=code):
        validate_frozen_environment(environ)


def test_authorization_protocol_is_frozen_and_contains_no_secret() -> None:
    protocol = build_protocol(
        source_revision="a" * 40,
        offline_baseline_revision="b" * 40,
        evaluator_hash="c" * 64,
        runner_hash="d" * 64,
        control_plane_selection_timestamp="2026-08-26T00:00:00+00:00",
    )
    assert protocol["base_url"] == FROZEN_BASE_URL
    assert protocol["api_model_alias"] == FROZEN_MODEL_ALIAS
    assert protocol["max_retries"] == 0
    assert protocol["max_http_requests"] == 60
    assert protocol["development_case_ids"] == list(DEVELOPMENT_CASE_IDS)
    assert protocol["2024_validation_opened"] is False
    assert protocol["2025_blind_accessed"] is False
    assert "secret" not in json.dumps(protocol).casefold()


def test_synthetic_evidence_is_identity_free_and_scope_checked() -> None:
    evidence = synthetic_evidence()
    serialized = json.dumps([item.model_dump(mode="json") for item in evidence])
    assert "ipo_" not in serialized.casefold()
    assert "1167" not in serialized
    assert_evidence_scope([evidence[0].evidence_id], evidence)
    with pytest.raises(RealLLMBenchmarkError, match="OUT_OF_SCOPE"):
        assert_evidence_scope(["invented-evidence"], evidence)


@pytest.mark.parametrize(
    "payload",
    [
        {"gold": True},
        {"nested": {"expected_level": "high"}},
        [{"expert_annotation": "forbidden"}],
    ],
)
def test_gold_and_annotation_fields_never_enter_model_payload(payload: object) -> None:
    with pytest.raises(RealLLMBenchmarkError, match="GOLD_PAYLOAD_REJECTED"):
        assert_gold_free_payload(payload)


class _FakeCompletions:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **_: object) -> SimpleNamespace:
        self.calls += 1
        return SimpleNamespace(id="response")


def test_request_budget_counts_actual_transport_and_fails_closed() -> None:
    delegate = _FakeCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=delegate))
    budget = RequestBudget(limit=1)
    wrapped = BudgetedClient(client, budget)
    wrapped.chat.completions.create(model=FROZEN_MODEL_ALIAS, messages=[])
    assert budget.count == 1
    assert delegate.calls == 1
    assert "messages" not in wrapped.chat.completions.last_attempt
    with pytest.raises(RealLLMBenchmarkError, match="REQUEST_BUDGET_EXHAUSTED"):
        wrapped.chat.completions.create(model=FROZEN_MODEL_ALIAS, messages=[])
    assert delegate.calls == 1


def test_request_payload_guard_executes_before_transport() -> None:
    delegate = _FakeCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=delegate))
    wrapped = BudgetedClient(client, RequestBudget(limit=2))
    with pytest.raises(RealLLMBenchmarkError, match="GOLD_PAYLOAD_REJECTED"):
        wrapped.chat.completions.create(messages=[{"gold_physical_page": 9}])
    assert delegate.calls == 0


def test_audited_provider_accepts_only_in_scope_citations_and_keeps_hashes() -> None:
    evidence = synthetic_evidence()
    metadata = LLMCallMetadata(
        provider_name="openai_compatible",
        model_name=FROZEN_MODEL_ALIAS,
        prompt_version="legal_shareholder_rights_v1",
        latency_ms=5,
        token_usage={"prompt_tokens": 7, "completion_tokens": 3},
        request_id="request",
        raw_response_hash="f" * 64,
    )

    class Delegate:
        last_call_metadata = metadata
        _client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    last_attempt={"attempt": 1, "request_hash": "e" * 64}
                )
            )
        )

        def generate_structured(self, **_: object) -> ShareholderRightCandidate:
            return ShareholderRightCandidate(
                right_type="redemption",
                evidence_ids=[evidence[0].evidence_id],
            )

    audited = AuditedStructuredProvider(Delegate(), RequestBudget(limit=2, _count=1))
    result = audited.generate_structured(
        task_name="shareholder_rights_extract",
        prompt_version="legal_shareholder_rights_v1",
        evidence=evidence,
        response_model=ShareholderRightCandidate,
    )
    assert result.evidence_ids == [evidence[0].evidence_id]
    assert audited.calls[0]["request_hash"] == "e" * 64
    assert "response" not in audited.calls[0]


def test_compact_metadata_has_hashes_but_no_bodies_or_credentials() -> None:
    metadata = LLMCallMetadata(
        provider_name="openai_compatible",
        model_name=FROZEN_MODEL_ALIAS,
        prompt_version="legal_shareholder_rights_v1",
        latency_ms=12,
        token_usage={"prompt_tokens": 10, "completion_tokens": 4},
        request_id="request-1",
        raw_response_hash="f" * 64,
    )
    compact = compact_call_metadata(
        metadata,
        case_id="ipo_2020_01167",
        risk_code="redemption_rights",
        task_name="shareholder_rights_extract",
        schema_version="ShareholderRightCandidate",
        attempt=1,
        request_hash="e" * 64,
    )
    assert compact["response_hash"] == "f" * 64
    assert compact["request_hash"] == "e" * 64
    assert not ({"prompt", "response", "authorization", "api_key"} & set(compact))


def test_only_fixed_development_cases_are_accepted() -> None:
    assert validate_case_ids(["ipo_2020_01167"]) == ("ipo_2020_01167",)
    for case_id in ("ipo_2024_02410", "ipo_2025_00001"):
        with pytest.raises(RealLLMBenchmarkError, match="NON_DEVELOPMENT"):
            validate_case_ids([case_id])


def test_resume_requires_all_frozen_identity_fields() -> None:
    expected = {
        "case_id": "ipo_2020_01167",
        "pdf_sha256": "a",
        "source_revision": "b",
        "config_sha256": "c",
        "protocol_sha256": "d",
    }
    validate_resume_identity(dict(expected), expected)
    with pytest.raises(RealLLMBenchmarkError, match="RESUME_IDENTITY_MISMATCH"):
        validate_resume_identity({**expected, "protocol_sha256": "changed"}, expected)


def test_interrupted_run_reuses_protocol_and_request_count(tmp_path: Path) -> None:
    protocol_path = tmp_path / "protocol.json"
    manifest_path = tmp_path / "manifest.json"
    protocol = {
        "source_revision": "a" * 40,
        "api_model_alias": FROZEN_MODEL_ALIAS,
        "synthetic_smoke": {"status": "PASS", "resolved_model_identity": FROZEN_MODEL_ALIAS},
    }
    protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
    manifest = {
        "result": "RUNNING",
        "http_requests": 24,
        "protocol_sha256": RUNNER.sha256_file(protocol_path),
        "cases": {"ipo_2020_01167": {"status": "SUCCESS"}},
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    args = SimpleNamespace(
        protocol=protocol_path,
        run_manifest=manifest_path,
        prior_http_requests=24,
    )

    loaded_protocol, loaded_manifest, smoke, protocol_hash = RUNNER.load_resume_state(
        args, revision="a" * 40, model=FROZEN_MODEL_ALIAS
    )

    assert loaded_protocol == protocol
    assert loaded_manifest == manifest
    assert smoke["status"] == "PASS"
    assert protocol_hash == manifest["protocol_sha256"]

    args.prior_http_requests = 23
    with pytest.raises(RUNNER.RealLLMRunError, match="RESUME_REQUEST_COUNT_MISMATCH"):
        RUNNER.load_resume_state(args, revision="a" * 40, model=FROZEN_MODEL_ALIAS)


def test_preflight_writes_protocol_atomically_and_blocks_without_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = tmp_path / "protocol.json"
    evaluator = tmp_path / "evaluator.py"
    evaluator.write_text("# evaluator\n", encoding="utf-8")
    monkeypatch.setattr(RUNNER, "source_revision", lambda: "a" * 40)
    monkeypatch.setattr(RUNNER, "__file__", str(SCRIPT))
    args = SimpleNamespace(
        protocol=protocol,
        evaluator=evaluator,
        offline_baseline_revision="b" * 40,
    )
    result = RUNNER.run_preflight(args, {})
    assert result["blocker"] == "BLOCKED_SECRET_NOT_AVAILABLE"
    assert result["http_requests"] == 0
    assert protocol.is_file()
    assert not protocol.with_suffix(".json.tmp").exists()
    assert canonical_hash(json.loads(protocol.read_text(encoding="utf-8")))
