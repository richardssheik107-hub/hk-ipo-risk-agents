from __future__ import annotations

from dataclasses import replace
from datetime import date
from hashlib import sha256
from pathlib import Path
import json

from pydantic import BaseModel, Field
import pytest

from ipo_risk.core.config import Settings
from ipo_risk.runtime.llm_journal import JournaledLLMProvider, LocalLLMJournal
from ipo_risk.runtime.role_b_ablation import RoleBAblationScopeError
from ipo_risk.schemas import Evidence, IPOAnalysisResult, TaskStatus
from scripts.run_v046_role_b_ablation import (
    CaseInputs,
    RoleBAblationRunnerError,
    _TracingRetriever,
    _build_journaled_router,
    _canonical_hash,
    _experiment_registry,
    _mode_identity,
    _journal_manifest,
    _offline_settings,
    _preflight,
    _prompt_hashes,
    _retrieval_pipeline_trace,
    _runtime_config_hash,
    _safe_settings_identity,
    _response_schema_hashes,
    _schema_set_hash,
    _smoke_gate,
    _subset_identity_hash,
    _write_governed_run_artifacts,
    _TracingRetriever,
    orchestrate_case_modes,
)


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _profile() -> dict:
    return {
        "profile_version": "v046_role_b_ablation_v1",
        "transport": "responses",
        "validation_enabled": False,
        "blind_2025_enabled": False,
        "allowed_tasks": [
            "shareholder_rights_extract",
            "litigation_compliance_extract",
            "business_precommercial_commercialization_extract",
            "business_precommercial_core_product_extract",
        ],
        "prompt_versions": {
            "shareholder_rights_extract": "legal_shareholder_rights_v1",
            "litigation_compliance_extract": "legal_litigation_compliance_v1",
            "business_precommercial_commercialization_extract": "business_precommercial_v1",
            "business_precommercial_core_product_extract": "business_precommercial_v1",
        },
    }


def _settings(**overrides) -> Settings:
    base = Settings(
        workflow_version="enhanced_v2",
        use_mock=False,
        runtime_mode="ai_enhanced",
        parser="pymupdf",
        retriever="keyword",
        financial_agent="v03",
        legal_agent="v03",
        business_agent="v03",
        market_agent="disabled",
        verifier="specialized_v03",
        supervisor="v03",
        llm_provider="openai_responses",
        llm_api_key="runtime-secret",
        llm_base_url="https://provider.invalid/v3",
        llm_model="ark-code-latest",
        llm_timeout_seconds=300,
        llm_max_retries=1,
        market_data_provider="unavailable",
        ipo_data_provider="catalog",
        report_generator="v04",
        market_context="none",
        final_supervisor="none",
    )
    return replace(base, **overrides)


def _case() -> CaseInputs:
    return CaseInputs(
        case_id="ipo_2020_00001",
        company_name="Synthetic Development Issuer",
        stock_code="0001.HK",
        listing_date=date(2020, 1, 2),
        prospectus_path=Path("synthetic.pdf"),
        prospectus_sha256=_digest("synthetic PDF"),
    )


def _result(metadata: dict | None = None) -> IPOAnalysisResult:
    return IPOAnalysisResult(
        request_id="request-1",
        company_name="Synthetic Development Issuer",
        stock_code="0001.HK",
        workflow_version="enhanced_v2",
        status=TaskStatus.COMPLETED,
        metadata=metadata or {},
    )


def test_tracing_retriever_is_observational_and_keeps_text_in_memory_only() -> None:
    evidence = Evidence(
        evidence_id="ev-1",
        document_id="document-1",
        chunk_id="chunk-1",
        page=12,
        section="customers",
        text="The five largest customers represented 65% of total revenue.",
        metadata={"query_family": "customer_concentration"},
    )

    class _Delegate:
        limits: list[int] = []

        def retrieve(self, chunks, query, limit=3):
            self.limits.append(limit)
            return [evidence]

    delegate = _Delegate()
    sink: list[dict] = []
    observed = _TracingRetriever(delegate, sink).retrieve([], "五大客戶", limit=5)

    assert observed == [evidence]
    assert delegate.limits == [5, 20]
    assert sink[0]["candidates"][0]["text"] == evidence.text
    assert sink[0]["diagnostic_candidates"][0]["text"] == evidence.text
    assert sink[0]["candidates"][0]["query_family"] == "customer_concentration"


def test_retrieval_trace_joins_gold_only_after_runtime_and_redacts_text() -> None:
    unit_id = _digest("evidence unit")
    coverage = {
        "evidence_units": [
            {
                "evidence_unit_id": unit_id,
                "case_id": "ipo_2020_00001",
                "source_risk_code": "customer_concentration",
                "page": 12,
                "exact_text": "five largest customers represented 65% of total revenue",
            }
        ]
    }
    evaluator_rows = [
        {
            "evidence_unit_id": unit_id,
            "case_id": "ipo_2020_00001",
            "source_risk_code": "customer_concentration",
        }
    ]
    calls = {
        "ipo_2020_00001": [
            {
                "query": "五大客戶",
                "limit": 5,
                "candidates": [
                    {
                        "evidence_id": "ev-supplier",
                        "document_id": "document-1",
                        "chunk_id": "chunk-8",
                        "page": 8,
                        "text": "top five suppliers",
                        "query_family": "supplier_concentration",
                        "query_intent": "supplier_concentration",
                    },
                ],
                "diagnostic_candidates": [
                    {
                        "evidence_id": "ev-supplier",
                        "document_id": "document-1",
                        "chunk_id": "chunk-8",
                        "page": 8,
                        "text": "top five suppliers",
                        "query_family": "supplier_concentration",
                        "query_intent": "supplier_concentration",
                    },
                    {
                        "evidence_id": "ev-customer",
                        "document_id": "document-1",
                        "chunk_id": "chunk-12",
                        "page": 12,
                        "text": "The five largest customers represented 65% of total revenue.",
                        "query_family": "customer_concentration",
                        "query_intent": "customer_concentration",
                    },
                ],
            }
        ]
    }

    trace = _retrieval_pipeline_trace(
        coverage=coverage,
        evidence_rows=evaluator_rows,
        calls_by_case=calls,
    )

    assert trace[0]["candidate_count"] == 1
    assert trace[0]["first_gold_page_rank"] == 2
    assert trace[0]["first_gold_rank"] == 2
    assert trace[0]["agent_consumed"] is False
    assert "text" not in json.dumps(trace)
    assert "exact_text" not in json.dumps(trace)


class _RiskPoolDelegate:
    def retrieve_for_risk(self, chunks, risk_code, *, limit=10):
        return [
            Evidence(
                evidence_id=f"ev-{limit}",
                document_id="doc",
                chunk_id="doc:page:1",
                page=1,
                text="bounded financial evidence",
            )
        ]


def test_tracing_retriever_records_actual_financial_risk_pool() -> None:
    sink: list[dict] = []
    retriever = _TracingRetriever(_RiskPoolDelegate(), sink)

    observed = retriever.retrieve_for_risk([], "cash_runway", limit=10)

    assert observed[0].evidence_id == "ev-10"
    assert sink[0]["query"] == "cash_runway"
    assert sink[0]["limit"] == 10
    assert sink[0]["candidates"][0]["query_intent"] == "cash_runway"
    assert sink[0]["diagnostic_candidates"][0]["evidence_id"] == "ev-20"


def test_cash_runway_risk_pool_survives_pipeline_trace_join() -> None:
    sink: list[dict] = []
    retriever = _TracingRetriever(_RiskPoolDelegate(), sink)
    retriever.retrieve_for_risk([], "cash_runway", limit=10)
    unit_id = _digest("cash evidence unit")

    trace = _retrieval_pipeline_trace(
        coverage={
            "evidence_units": [
                {
                    "evidence_unit_id": unit_id,
                    "case_id": "ipo_2020_00001",
                    "source_risk_code": "cash_runway",
                    "page": 1,
                    "exact_text": "bounded financial evidence",
                }
            ]
        },
        evidence_rows=[
            {
                "evidence_unit_id": unit_id,
                "case_id": "ipo_2020_00001",
                "source_risk_code": "cash_runway",
            }
        ],
        calls_by_case={"ipo_2020_00001": sink},
    )

    assert trace[0]["candidate_count"] == 1
    assert trace[0]["first_gold_page_rank"] == 1
    assert trace[0]["first_gold_rank"] == 1
    assert trace[0]["agent_consumed"] is True
    assert trace[0]["retrieval_query_family"] == ["cash_runway"]


def test_experiment_registry_exposes_financial_high_recall_only_opt_in() -> None:
    observed = _experiment_registry().create(
        "retriever", "role_b_v046_financial_high_recall"
    )

    assert observed.name == "role_b_v046_financial_high_recall"


def test_offline_settings_remove_remote_provider_and_credentials(tmp_path: Path) -> None:
    settings = _offline_settings(_settings(), tmp_path / "data", tmp_path / "reports")

    assert settings.llm_provider == "unavailable"
    assert settings.llm_api_key == ""
    assert settings.llm_base_url == ""
    assert settings.market_agent == "disabled"
    assert settings.market_context == "none"
    assert settings.final_supervisor == "none"


def test_offline_orchestration_performs_no_remote_action() -> None:
    remote_calls = 0

    def execute(mode, _case, _baseline):
        nonlocal remote_calls
        if mode != "offline":
            remote_calls += 1
        return _result()

    results = orchestrate_case_modes(
        case=_case(), modes=("offline",), execute_mode=execute
    )

    assert tuple(results) == ("offline",)
    assert remote_calls == 0


def test_shadow_saved_result_is_the_exact_offline_canonical_object() -> None:
    offline = _result({"source": "offline"})

    def execute(mode, _case, baseline):
        if mode == "offline":
            return offline
        assert mode == "shadow"
        assert baseline is offline
        # Probe-only metadata may differ, while Risk/Evidence/Calculation is
        # identical.  The runner must still persist the original offline object.
        return _result({"source": "real shadow probe"})

    results = orchestrate_case_modes(
        case=_case(), modes=("offline", "shadow"), execute_mode=execute
    )

    assert results["offline"] is offline
    assert results["shadow"] is offline


class _StructuredResult(BaseModel):
    finding: str
    evidence_ids: list[str] = Field(min_length=1)


class _CaptureDelegate:
    name = "openai_responses"
    model = "ark-code-latest"

    def __init__(self) -> None:
        self.calls = 0
        self.last_call_metadata = None
        self.last_failure_diagnostics = None
        self.last_attempt_trace = []

    def generate_structured(self, **_: object) -> _StructuredResult:
        self.calls += 1
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
        return _StructuredResult(finding="supported", evidence_ids=["ev-1"])


def test_gated_router_reuses_shadow_journal_without_delegate_call(tmp_path: Path) -> None:
    journal = LocalLLMJournal(tmp_path / "journal")
    task = "shareholder_rights_extract"
    version = "legal_shareholder_rights_v1"
    prompt_hashes = {(task, version): _digest("exact prompt")}
    runtime_hash = _digest("safe config and code")
    evidence = [
        Evidence(
            evidence_id="ev-1",
            document_id="development-document",
            chunk_id="chunk-1",
            page=3,
            section="legal",
            text="sanitized synthetic Evidence",
        )
    ]
    capture_delegate = _CaptureDelegate()
    capture = JournaledLLMProvider(
        capture_delegate,
        journal=journal,
        case_id="ipo_2020_00001",
        dataset_split="development",
        transport="responses",
        prompt_hashes=prompt_hashes,
        runtime_config_hash=runtime_hash,
    )
    first = capture.generate_structured(
        task_name=task,
        prompt_version=version,
        evidence=evidence,
        response_model=_StructuredResult,
    )
    assert capture_delegate.calls == 1

    router, replay_only = _build_journaled_router(
        mode="gated",
        case_id="ipo_2020_00001",
        settings=_settings(),
        profile=_profile(),
        journal=journal,
        prompt_hashes=prompt_hashes,
        runtime_config_hash=runtime_hash,
    )
    replayed = router.generate_structured(
        task_name=task,
        prompt_version=version,
        evidence=evidence,
        response_model=_StructuredResult,
    )

    assert replayed == first
    assert replay_only is not None
    assert replay_only.call_count == 0


def test_journal_manifest_verifies_record_before_summarizing(tmp_path: Path) -> None:
    journal = LocalLLMJournal(tmp_path / "journal")
    task = "shareholder_rights_extract"
    version = "legal_shareholder_rights_v1"
    provider = JournaledLLMProvider(
        _CaptureDelegate(),
        journal=journal,
        case_id="ipo_2020_00001",
        dataset_split="development",
        transport="responses",
        prompt_hashes={(task, version): _digest("exact prompt")},
        runtime_config_hash=_digest("safe config and code"),
    )
    evidence = [
        Evidence(
            evidence_id="ev-1",
            document_id="development-document",
            chunk_id="chunk-1",
            page=3,
            section="legal",
            text="sanitized synthetic Evidence",
        )
    ]
    provider.generate_structured(
        task_name=task,
        prompt_version=version,
        evidence=evidence,
        response_model=_StructuredResult,
    )

    manifest = _journal_manifest(journal)
    assert manifest["record_count"] == 1
    assert len(manifest["records"][0]["prompt_hash"]) == 64
    path = next(journal.root.glob("*.json"))
    tampered = json.loads(path.read_text(encoding="utf-8"))
    tampered["attempt_count"] += 1
    path.write_text(json.dumps(tampered), encoding="utf-8")

    with pytest.raises(RoleBAblationRunnerError, match="invalid record"):
        _journal_manifest(journal)


def test_filtered_subset_gets_distinct_child_identity() -> None:
    parent = {
        "split": "development",
        "case_count": 2,
        "cases": [{"case_id": "a"}, {"case_id": "b"}],
        "subset_hash": "parent",
    }
    child = {
        **parent,
        "cases": [{"case_id": "a"}],
        "case_count": 1,
        "selection_scope": "fixed10_child_filter",
        "parent_subset_hash": "parent",
    }
    child["subset_hash"] = _subset_identity_hash(child)

    assert child["subset_hash"] != parent["subset_hash"]
    assert child["parent_subset_hash"] == parent["subset_hash"]


def test_governed_run_writes_every_required_top_level_artifact(tmp_path: Path) -> None:
    summary = {
        "risk_extraction": {
            "official_aligned_accuracy": 0.9,
            "per_risk": {},
            "evaluable_positive_count": 10,
        },
        "evidence_coverage": {
            "coverage_recall": 0.9,
            "evaluable_existing_gold_count": 10,
        },
        "retrieval_diagnostics": {"recall_at_20": 0.9},
    }
    mode_payload = {
        "summary": summary,
        "failure_focus": {"dominant_failure_reason": None},
        "artifacts": {
            "retrieval_waterfall": {"report_version": "test", "units": []},
            "risk_pipeline_waterfall": {"report_version": "test", "units": []},
        },
    }
    evaluation = {
        "modes": {mode: mode_payload for mode in ("offline", "shadow", "gated")},
        "monotonicity": {"status": "PROVEN", "satisfied": True},
    }
    _write_governed_run_artifacts(
        output_root=tmp_path,
        subset={"subset_hash": _digest("subset"), "case_count": 10},
        coverage={
            "manifest_hash": _digest("gold"),
            "metric_protocol_version": "metric-v2",
        },
        git_state={
            "git_head": _digest("head"),
            "code_fingerprint": _digest("code"),
            "git_dirty": True,
        },
        preflight={
            "effective_provider": "openai_responses",
            "effective_model": "ark-code-latest",
            "transport": "responses",
            "prompt_hashes": {},
            "runtime_config_hash": _digest("runtime"),
        },
        profile=_profile(),
        journal_manifest={"records": []},
        evaluation=evaluation,
        modes=("offline", "shadow", "gated"),
    )

    required = {
        "baseline_manifest.json",
        "ablation_summary.json",
        "llm_call_quality.json",
        "retrieval_waterfall.json",
        "risk_pipeline_waterfall.json",
        "failure_focus.json",
        "best_iteration.json",
    }
    assert required.issubset({path.name for path in tmp_path.iterdir()})
    best = json.loads((tmp_path / "best_iteration.json").read_text(encoding="utf-8"))
    assert best["selected_mode"] == "gated"
    assert best["fixed10_target_reached"] is False


@pytest.mark.parametrize(
    "manifest",
    [
        {
            "split": "validation",
            "validation_opened": False,
            "blind_2025_outcome_accessed": False,
            "cases": [{"case_id": "ipo_2024_00001"}],
        },
        {
            "split": "development",
            "validation_opened": True,
            "blind_2025_outcome_accessed": False,
            "cases": [{"case_id": "ipo_2020_00001"}],
        },
        {
            "split": "development",
            "validation_opened": False,
            "blind_2025_outcome_accessed": True,
            "cases": [{"case_id": "ipo_2025_00001"}],
        },
    ],
)
def test_development_validation_blind_guards_fail_closed(manifest: dict) -> None:
    from ipo_risk.runtime.role_b_ablation import validate_development_only_manifest

    with pytest.raises(RoleBAblationScopeError):
        validate_development_only_manifest(manifest)


def test_preflight_binds_exact_prompt_hashes_and_has_no_secret_or_url() -> None:
    settings = _settings()
    profile = _profile()
    report = _preflight(
        config_path=Path("configs/experiments/v046_role_b_ai_responses.yaml"),
        settings=settings,
        profile=profile,
        require_remote=True,
    )
    safe_identity = _safe_settings_identity(settings, profile)
    runtime_hash = _runtime_config_hash(settings, profile, _digest("code"))

    assert len(_prompt_hashes(profile, settings.llm_provider)) == 4
    assert all(len(value) == 64 for value in report["prompt_hashes"].values())
    assert "llm_api_key" not in safe_identity
    assert "llm_base_url" not in safe_identity
    assert len(safe_identity["llm_base_url_hash"]) == 64
    assert "runtime-secret" not in str(safe_identity)
    assert "provider.invalid" not in str(safe_identity)
    assert len(runtime_hash) == 64


def test_mode_identity_contains_every_waterfall_alignment_key() -> None:
    settings = _settings()
    profile = _profile()
    prompt_set_hash = _canonical_hash(
        {
            f"{task}:{version}": digest
            for (task, version), digest in _prompt_hashes(
                profile, settings.llm_provider
            ).items()
        }
    )
    identity = _mode_identity(
        mode="gated",
        subset={"subset_hash": _digest("subset")},
        coverage={"manifest_hash": _digest("gold")},
        code_fingerprint=_digest("code"),
        runtime_config_hash=_digest("runtime"),
        journal_hash=_digest("journal"),
        settings=settings,
        profile=profile,
        prompt_set_hash=prompt_set_hash,
        schema_set_hash=_schema_set_hash(),
    )

    assert all(
        identity[key]
        for key in (
            "code_fingerprint",
            "subset_hash",
            "gold_manifest_hash",
            "evaluator_version",
            "provider",
            "model",
            "transport",
            "prompt_set_hash",
            "schema_set_hash",
            "llm_journal_hash",
        )
    )


def test_preflight_rejects_market_or_final_supervisor_channels() -> None:
    with pytest.raises(RoleBAblationRunnerError, match="Market"):
        _preflight(
            config_path=Path("config.yaml"),
            settings=_settings(market_agent="market_intelligence"),
            profile=_profile(),
            require_remote=False,
        )


def test_preflight_rejects_provider_transport_profile_mismatch() -> None:
    with pytest.raises(RoleBAblationRunnerError, match="provider/transport"):
        _preflight(
            config_path=Path("config.yaml"),
            settings=_settings(llm_provider="openai_compatible"),
            profile=_profile(),
            require_remote=False,
        )


def test_glm_openai_compatible_profile_is_separate_and_supported() -> None:
    settings = _settings(llm_provider="openai_compatible", llm_model="glm-5.3")
    profile = {**_profile(), "transport": "openai_compatible_chat_json"}

    report = _preflight(
        config_path=Path("configs/experiments/v046_role_b_glm_openai_compatible.yaml"),
        settings=settings,
        profile=profile,
        require_remote=True,
    )

    assert report["effective_provider"] == "openai_compatible"
    assert report["effective_model"] == "glm-5.3"
    assert report["transport"] == "openai_compatible_chat_json"
    assert len(_prompt_hashes(profile, settings.llm_provider)) == 4


def test_fixed10_smoke_gate_requires_same_provider_model_and_three_tasks(
    tmp_path: Path,
) -> None:
    path = tmp_path / "structured_smoke_summary.json"
    tasks = [
        "shareholder_rights_extract",
        "litigation_compliance_extract",
        "business_precommercial_commercialization_extract",
    ]
    profile = {**_profile(), "smoke_required_before_fixed10": True}
    prompt_hashes = _prompt_hashes(profile, "openai_responses")
    schema_hashes = _response_schema_hashes()
    payload = {
        "smoke_version": "v046_role_b_structured_smoke_v1",
        "dataset_split": "development",
        "synthetic_sanitized_payload": True,
        "full_pdf_opened": False,
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
        "call_count": 3,
        "passed_count": 3,
        "passed": True,
        "tasks": [
            {
                "task_name": task,
                "provider": "openai_responses",
                "model": "ark-code-latest",
                "prompt_version": profile["prompt_versions"][task],
                "prompt_hash": prompt_hashes[(task, profile["prompt_versions"][task])],
                "response_schema_hash": schema_hashes[task],
            }
            for task in tasks
        ],
    }
    path.write_text(__import__("json").dumps(payload), encoding="utf-8")

    assert _smoke_gate(path=path, settings=_settings(), profile=profile)["passed"] is True
    assert (
        _smoke_gate(
            path=path,
            settings=_settings(llm_provider="openai_compatible", llm_model="glm-5.3"),
            profile=profile,
        )["passed"]
        is False
    )
    payload["tasks"][0]["prompt_hash"] = _digest("drifted prompt")
    path.write_text(__import__("json").dumps(payload), encoding="utf-8")
    assert _smoke_gate(path=path, settings=_settings(), profile=profile)["passed"] is False
    with pytest.raises(RoleBAblationRunnerError, match="Final Supervisor"):
        _preflight(
            config_path=Path("config.yaml"),
            settings=_settings(final_supervisor="llm"),
            profile=_profile(),
            require_remote=False,
        )


def test_shadow_and_gated_cannot_run_without_ordered_offline_capture() -> None:
    with pytest.raises(RoleBAblationRunnerError, match="offline baseline"):
        orchestrate_case_modes(
            case=_case(), modes=("shadow",), execute_mode=lambda *_: _result()
        )
    with pytest.raises(RoleBAblationRunnerError, match="shadow journal capture"):
        orchestrate_case_modes(
            case=_case(),
            modes=("offline", "gated"),
            execute_mode=lambda *_: _result(),
        )
