from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from pydantic import BaseModel
import pytest
import yaml

from ipo_risk.core.config import load_settings
from ipo_risk.providers.llm import LLMFailureKind, LLMProviderError
from ipo_risk.runtime.llm_journal import JournaledLLMProvider, LocalLLMJournal
from ipo_risk.runtime.role_b_ablation import (
    ROLE_B_TASK_NAMES,
    RoleBAblationInvariantError,
    RoleBAblationScopeError,
    ShadowRiskAgent,
    TaskRoutingProvider,
    build_shadow_projection,
    canonical_risk_evidence_calculation_hash,
    validate_development_only_manifest,
)
from ipo_risk.schemas import (
    Calculation,
    Evidence,
    EvidenceSourceType,
    LLMCallMetadata,
    RiskCategory,
    RiskItem,
    RiskLevel,
    VerificationStatus,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "experiments" / "v046_role_b_ai_responses.yaml"
GLM_CONFIG = (
    ROOT / "configs" / "experiments" / "v046_role_b_glm_openai_compatible.yaml"
)


class _StructuredDecision(BaseModel):
    label: str
    evidence_ids: list[str]


class _FakeStructuredProvider:
    name = "openai_responses"
    model = "ark-code-latest"

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.last_call_metadata = None

    def generate_structured(self, *, task_name, prompt_version, evidence, response_model):
        self.calls.append(task_name)
        self.last_call_metadata = LLMCallMetadata(
            provider_name=self.name,
            model_name=self.model,
            prompt_version=prompt_version,
            latency_ms=7,
            token_usage={"total_tokens": 11},
            request_id="safe-request-id",
            raw_response_hash="a" * 64,
        )
        return response_model.model_validate(
            {"label": "candidate", "evidence_ids": [evidence[0].evidence_id]}
        )


def _evidence(text: str = "Synthetic in-scope prospectus evidence") -> Evidence:
    return Evidence(
        evidence_id="ev-1",
        document_id="doc-1",
        chunk_id="chunk-1",
        page=7,
        section="Risk Factors",
        text=text,
        source_type=EvidenceSourceType.PROSPECTUS,
        relevance_score=0.9,
    )


def _risk(*, risk_id: str, evidence_text: str = "Synthetic supporting fact") -> RiskItem:
    evidence = Evidence(
        evidence_id="ev-risk-1",
        document_id="doc-1",
        chunk_id="chunk-2",
        page=8,
        section="Financial Information",
        text=evidence_text,
        source_type=EvidenceSourceType.PROSPECTUS,
        relevance_score=0.8,
        metadata={"diagnostic_only": risk_id},
    )
    return RiskItem(
        risk_id=risk_id,
        risk_code="customer_concentration",
        category=RiskCategory.FINANCIAL,
        risk_type="Customer concentration",
        level=RiskLevel.MEDIUM,
        score=60,
        conclusion="Customer concentration exceeds the frozen threshold.",
        evidence=[evidence],
        calculation=Calculation(
            skill_name="concentration",
            skill_version="1.0",
            inputs={"largest_customer_pct": 31.0},
            formula="largest_customer_pct",
            result=31.0,
            unit="percent",
            evidence_ids=[evidence.evidence_id],
        ),
        agent_name="financial",
        confidence=0.9,
        verification_status=VerificationStatus.VERIFIED,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        metadata={"component_diagnostics": {"run": risk_id}},
    )


def test_task_router_allows_exactly_the_four_role_b_tasks() -> None:
    delegate = _FakeStructuredProvider()
    router = TaskRoutingProvider(delegate)
    evidence = [_evidence()]

    for task_name in sorted(ROLE_B_TASK_NAMES):
        result = router.generate_structured(
            task_name=task_name,
            prompt_version="test-v1",
            evidence=evidence,
            response_model=_StructuredDecision,
        )
        assert result.label == "candidate"
        assert router.last_route == {"task_name": task_name, "route": "role_b"}

    with pytest.raises(LLMProviderError) as exc_info:
        router.generate_structured(
            task_name="final_supervision_synthesis",
            prompt_version="v1",
            evidence=evidence,
            response_model=_StructuredDecision,
        )
    assert exc_info.value.kind is LLMFailureKind.UNAVAILABLE
    assert router.last_route == {
        "task_name": "final_supervision_synthesis",
        "route": "unavailable",
    }
    assert set(delegate.calls) == ROLE_B_TASK_NAMES


def test_gated_call_consumes_the_same_durable_shadow_replay(
    tmp_path: Path,
) -> None:
    shadow_delegate = _FakeStructuredProvider()
    journal = LocalLLMJournal(tmp_path / "journal")
    provider_kwargs = {
        "journal": journal,
        "case_id": "ipo_2020_00001",
        "dataset_split": "development",
        "transport": "responses",
        "prompt_hashes": {
            (
                "shareholder_rights_extract",
                "legal_shareholder_rights_v1",
            ): "a" * 64,
        },
        "runtime_config_hash": "b" * 64,
    }
    shadow_provider = JournaledLLMProvider(shadow_delegate, **provider_kwargs)
    evidence = [_evidence()]

    recorded = shadow_provider.generate_structured(
        task_name="shareholder_rights_extract",
        prompt_version="legal_shareholder_rights_v1",
        evidence=evidence,
        response_model=_StructuredDecision,
    )
    assert shadow_provider.last_journal_identity is not None

    gated_delegate = _FakeStructuredProvider()
    gated_provider = JournaledLLMProvider(gated_delegate, **provider_kwargs)
    replayed = gated_provider.generate_structured(
        task_name="shareholder_rights_extract",
        prompt_version="legal_shareholder_rights_v1",
        evidence=evidence,
        response_model=_StructuredDecision,
    )

    assert replayed == recorded
    assert shadow_delegate.calls == ["shareholder_rights_extract"]
    assert gated_delegate.calls == []
    assert gated_provider.last_journal_reused is True
    assert gated_provider.last_journal_identity == shadow_provider.last_journal_identity
    persisted = journal.record_path(shadow_provider.last_journal_identity).read_text(
        encoding="utf-8"
    )
    assert evidence[0].text not in persisted


def test_canonical_hash_ignores_runtime_identity_time_logs_and_diagnostics() -> None:
    first = {
        "verified_risks": [_risk(risk_id="runtime-risk-a")],
        "pending_risks": [],
        "rejected_risks": [],
        "analysis_id": "analysis-a",
        "agent_logs": [{"finished_at": "2026-01-01T00:00:00Z"}],
        "metadata": {"component_diagnostics": {"llm": "first"}},
    }
    second_risk = _risk(risk_id="runtime-risk-b").model_copy(
        update={"created_at": datetime(2026, 2, 1, tzinfo=timezone.utc)}
    )
    second = {
        "verified_risks": [second_risk],
        "pending_risks": [],
        "rejected_risks": [],
        "analysis_id": "analysis-b",
        "agent_logs": [{"finished_at": "2026-02-01T00:00:00Z"}],
        "metadata": {"component_diagnostics": {"llm": "second"}},
    }

    assert canonical_risk_evidence_calculation_hash(first) == (
        canonical_risk_evidence_calculation_hash(second)
    )

    changed = dict(second)
    changed["verified_risks"] = [
        _risk(risk_id="runtime-risk-c", evidence_text="Different supporting fact")
    ]
    assert canonical_risk_evidence_calculation_hash(first) != (
        canonical_risk_evidence_calculation_hash(changed)
    )


class _StaticAgent:
    name = "business"

    def __init__(self, risks: list[RiskItem], diagnostic: str) -> None:
        self.risks = risks
        self.last_diagnostics = {"source": diagnostic}
        self.call_count = 0

    def analyze(self, profile, chunks, market=None):
        self.call_count += 1
        return self.risks


def test_shadow_agent_calls_probe_but_returns_only_offline_canonical_result() -> None:
    baseline_risk = _risk(risk_id="offline-risk")
    probe_risk = baseline_risk.model_copy(
        update={"level": RiskLevel.CRITICAL, "score": 95}
    )
    baseline = _StaticAgent([baseline_risk], "offline")
    probe = _StaticAgent([probe_risk], "real-llm-probe")
    shadow = ShadowRiskAgent(baseline, probe)

    returned = shadow.analyze(object(), [], None)

    assert returned == [baseline_risk]
    assert baseline.call_count == 1
    assert probe.call_count == 1
    assert shadow.last_diagnostics == {"source": "offline"}
    probe_diagnostics = shadow.probe_summary()["probe_diagnostics"]
    assert len(probe_diagnostics) == 1
    assert probe_diagnostics[0]["diagnostic_keys"] == ["source"]
    assert len(probe_diagnostics[0]["diagnostic_hash"]) == 64

    offline_result = {"verified_risks": returned, "pending_risks": [], "rejected_risks": []}
    shadow_result = {"verified_risks": returned, "pending_risks": [], "rejected_risks": []}
    projection = build_shadow_projection(
        offline_result,
        shadow_result,
        journal_identities=[],
        probe_diagnostics=[shadow.probe_summary()],
    )
    assert projection["canonical_equal_to_offline"] is True
    assert projection["llm_may_modify_final"] is False
    assert "probe_result" not in projection

    with pytest.raises(RoleBAblationInvariantError, match="differs from offline"):
        build_shadow_projection(
            offline_result,
            {"verified_risks": [probe_risk], "pending_risks": [], "rejected_risks": []},
            journal_identities=[],
        )


def test_shadow_diagnostics_do_not_copy_prompt_evidence_or_response_text() -> None:
    baseline = _StaticAgent([], "offline")
    probe = _StaticAgent([], "probe")
    probe.last_diagnostics = {
        "task_name": "litigation_compliance_extract",
        "status": "completed",
        "raw_response": "licensed prospectus clause",
        "prompt": "secret prompt text",
        "evidence_text": "full evidence text",
    }
    shadow = ShadowRiskAgent(baseline, probe)

    shadow.analyze(object(), [], None)
    summary = shadow.probe_summary()
    serialized = json.dumps(summary, ensure_ascii=False)

    assert summary["probe_diagnostics"][0]["status"] == "completed"
    assert "licensed prospectus clause" not in serialized
    assert "secret prompt text" not in serialized
    assert "full evidence text" not in serialized


def _development_manifest() -> dict:
    return {
        "split": "development",
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
        "cases": [
            {"case_id": "ipo_2020_00001", "split": "development"},
            {"case_id": "ipo_2023_00002", "dataset_split": "development"},
        ],
    }


def test_development_guard_accepts_only_frozen_development_scope() -> None:
    assert validate_development_only_manifest(_development_manifest()) == (
        "ipo_2020_00001",
        "ipo_2023_00002",
    )

    for mutation in (
        {"split": "validation"},
        {"validation_opened": True},
        {"blind_2025_outcome_accessed": True},
        {"cases": [{"case_id": "ipo_2024_00001"}]},
        {"cases": [{"case_id": "ipo_2025_00001", "split": "development"}]},
    ):
        manifest = _development_manifest()
        manifest.update(mutation)
        with pytest.raises(RoleBAblationScopeError):
            validate_development_only_manifest(manifest)


def test_role_b_config_is_isolated_and_machine_readable(monkeypatch) -> None:
    for variable in (
        "IPO_RISK_RUNTIME_MODE",
        "IPO_RISK_LLM_PROVIDER",
        "IPO_RISK_LLM_MODEL",
        "IPO_RISK_LLM_TIMEOUT_SECONDS",
        "IPO_RISK_LLM_MAX_RETRIES",
        "IPO_RISK_MARKET_AGENT",
        "IPO_RISK_FINAL_SUPERVISOR",
    ):
        monkeypatch.delenv(variable, raising=False)

    settings = load_settings(str(CONFIG))
    raw = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    profile = raw["role_b_ablation_profile"]

    assert settings.llm_provider == "openai_responses"
    assert settings.llm_model == "ark-code-latest"
    assert settings.llm_timeout_seconds == 300
    assert settings.llm_max_retries == 1
    assert settings.market_agent == "disabled"
    assert settings.final_supervisor == "none"
    assert set(profile["allowed_tasks"]) == ROLE_B_TASK_NAMES
    assert profile["max_transport_attempts_per_structured_attempt"] == 2
    assert profile["max_structured_attempts"] == 2
    assert profile["max_network_calls_per_task"] == 4
    assert profile["smoke_required_before_fixed10"] is True
    assert profile["validation_enabled"] is False
    assert profile["blind_2025_enabled"] is False
    assert profile["prompt_versions"] == {
        "shareholder_rights_extract": "legal_shareholder_rights_v1",
        "litigation_compliance_extract": "legal_litigation_compliance_v1",
        "business_precommercial_commercialization_extract": "business_precommercial_v1",
        "business_precommercial_core_product_extract": "business_precommercial_v1",
    }


def test_glm_transport_profile_is_separate_and_requires_smoke(monkeypatch) -> None:
    for variable in (
        "IPO_RISK_RUNTIME_MODE",
        "IPO_RISK_LLM_PROVIDER",
        "IPO_RISK_LLM_MODEL",
        "IPO_RISK_LLM_TIMEOUT_SECONDS",
        "IPO_RISK_LLM_MAX_RETRIES",
        "IPO_RISK_MARKET_AGENT",
        "IPO_RISK_FINAL_SUPERVISOR",
    ):
        monkeypatch.delenv(variable, raising=False)

    settings = load_settings(str(GLM_CONFIG))
    raw = yaml.safe_load(GLM_CONFIG.read_text(encoding="utf-8"))
    profile = raw["role_b_ablation_profile"]

    assert settings.llm_provider == "openai_compatible"
    assert settings.llm_model == "glm-5.3"
    assert settings.llm_timeout_seconds == 300
    assert settings.llm_max_retries == 1
    assert settings.market_agent == "disabled"
    assert settings.final_supervisor == "none"
    assert profile["transport"] == "openai_compatible_chat_json"
    assert profile["max_network_calls_per_task"] == 2
    assert profile["smoke_required_before_fixed10"] is True
    assert set(profile["allowed_tasks"]) == ROLE_B_TASK_NAMES
