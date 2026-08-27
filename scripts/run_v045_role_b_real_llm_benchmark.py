"""Run the frozen Role-B real-LLM benchmark on ten Development IPOs.

This runner freezes a protocol before transport, performs a fictional structured
smoke, then streams one yearly ZIP and one PDF at a time. Prediction generation
never reads Gold; evaluation begins only after all compact predictions exist.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
from dataclasses import fields, replace
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import time
import zipfile
from typing import Any

import yaml

from ipo_risk.agents.legal_models import ShareholderRightCandidate
from ipo_risk.core.config import Settings
from ipo_risk.core.container import DependencyContainer, default_registry
from ipo_risk.evaluation.document_intelligence_benchmark import (
    ROLE_B_RISK_CODES,
    _load_role_b_golden,
)
from ipo_risk.evaluation.golden_eval import evaluate, load_results
from ipo_risk.evaluation.real_llm_benchmark import (
    AuditedStructuredProvider,
    BudgetedClient,
    DEVELOPMENT_CASE_IDS,
    MAX_HTTP_REQUESTS,
    RealLLMBenchmarkError,
    RequestBudget,
    build_protocol,
    secret_presence,
    synthetic_evidence,
    validate_frozen_environment,
)
from ipo_risk.providers.catalog import CatalogIPODataProvider
from ipo_risk.providers.llm import LLMProviderError, OpenAICompatibleLLMProvider
from ipo_risk.schemas import IPOAnalysisRequest
from ipo_risk.services.analysis_service import IPOAnalysisService
from scripts import run_v045_role_b_offline_pdf_benchmark as offline


PROTOCOL_VERSION = "v045_role_b_real_llm_development_v2"
SMOKE_CASE_IDS = ("ipo_2020_01167", "ipo_2020_01961")
CASE_ORDER = (*SMOKE_CASE_IDS, *(c for c in DEVELOPMENT_CASE_IDS if c not in SMOKE_CASE_IDS))
DISK_FLOOR_BYTES = 3 * 1024**3


class RealLLMRunError(RuntimeError):
    pass


class _MemoryRepository:
    def __init__(self) -> None:
        self.items: dict[str, Any] = {}

    def save(self, result: Any) -> None:
        self.items[result.analysis_id] = result

    def get(self, analysis_id: str) -> Any:
        return self.items.get(analysis_id)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def source_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def atomic_jsonl(path: Path, rows: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        for case_id in CASE_ORDER:
            if case_id in rows:
                handle.write(json.dumps(rows[case_id], ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def refreeze_protocol(args: argparse.Namespace) -> tuple[dict[str, Any], str]:
    """Supersede the zero-call protocol after the requested main fast-forward."""

    previous_hash = sha256_file(args.protocol) if args.protocol.is_file() else None
    previous = json.loads(args.protocol.read_text(encoding="utf-8")) if args.protocol.is_file() else {}
    observed = int(previous.get("http_requests_observed") or 0)
    if observed > args.prior_http_requests:
        raise RealLLMRunError("PROTOCOL_ALREADY_CONSUMED")
    payload = build_protocol(
        source_revision=source_revision(),
        offline_baseline_revision="fe3403af0e9a2802192f1c504bcd65f3e8b9f583",
        evaluator_hash=sha256_file(args.evaluator),
        runner_hash=sha256_file(Path(__file__)),
        control_plane_selection_timestamp=datetime.now(timezone.utc).isoformat(),
    )
    payload.update(
        {
            "protocol_version": PROTOCOL_VERSION,
            "supersedes_zero_call_protocol_sha256": previous_hash,
            "refreeze_reason": "origin/main advanced before first HTTP request",
            "http_requests_observed": args.prior_http_requests,
            "prior_failed_synthetic_requests": args.prior_http_requests,
            "synthetic_smoke_required": True,
            "smoke_case_ids": list(SMOKE_CASE_IDS),
            "gold_loaded_during_prediction": False,
        }
    )
    atomic_json(args.protocol, payload)
    return payload, sha256_file(args.protocol)


def load_resume_state(
    args: argparse.Namespace, *, revision: str, model: str
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]:
    """Load an interrupted run without mutating its frozen protocol."""

    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    manifest = json.loads(args.run_manifest.read_text(encoding="utf-8"))
    if manifest.get("result") != "RUNNING":
        raise RealLLMRunError("RESUME_MANIFEST_NOT_RUNNING")
    if int(manifest.get("http_requests") or -1) != args.prior_http_requests:
        raise RealLLMRunError("RESUME_REQUEST_COUNT_MISMATCH")
    if protocol.get("source_revision") != revision:
        raise RealLLMRunError("RESUME_SOURCE_REVISION_MISMATCH")
    if protocol.get("api_model_alias") != model:
        raise RealLLMRunError("RESUME_MODEL_MISMATCH")
    smoke = protocol.get("synthetic_smoke") or {}
    if smoke.get("status") != "PASS":
        raise RealLLMRunError("RESUME_SYNTHETIC_SMOKE_NOT_PASSED")
    protocol_sha256 = sha256_file(args.protocol)
    if manifest.get("protocol_sha256") != protocol_sha256:
        raise RealLLMRunError("RESUME_PROTOCOL_HASH_MISMATCH")
    return protocol, manifest, smoke, protocol_sha256


def prepare_protocol(args: argparse.Namespace) -> tuple[dict[str, Any], str]:
    """Backward-compatible no-network protocol preparation used by unit tests."""

    if args.protocol.exists():
        payload = json.loads(args.protocol.read_text(encoding="utf-8"))
        return payload, sha256_file(args.protocol)
    payload = build_protocol(
        source_revision=source_revision(),
        offline_baseline_revision=args.offline_baseline_revision,
        evaluator_hash=sha256_file(args.evaluator),
        runner_hash=sha256_file(Path(__file__)),
        control_plane_selection_timestamp=datetime.now(timezone.utc).isoformat(),
    )
    atomic_json(args.protocol, payload)
    return payload, sha256_file(args.protocol)


def run_preflight(args: argparse.Namespace, environ: dict[str, str]) -> dict[str, Any]:
    """Presence-only preflight retained as a safe standalone contract."""

    protocol, protocol_sha256 = prepare_protocol(args)
    try:
        validate_frozen_environment(environ)
    except RealLLMBenchmarkError as exc:
        return {
            "result": "BLOCKED",
            "blocker": exc.code,
            "environment_presence": secret_presence(environ),
            "protocol_sha256": protocol_sha256,
            "http_requests": 0,
            "synthetic_smoke": "NOT_RUN",
        }
    return {
        "result": "READY_FOR_SYNTHETIC_SMOKE",
        "environment_presence": secret_presence(environ),
        "protocol_sha256": protocol_sha256,
        "protocol_identity": hashlib.sha256(
            json.dumps(protocol, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "http_requests": 0,
    }


def ai_settings(config_path: Path, environ: dict[str, str]) -> tuple[Settings, str]:
    values = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    defaults = Settings()
    known = {item.name for item in fields(Settings)}
    settings = Settings(**{name: values.get(name, getattr(defaults, name)) for name in known})
    settings = replace(
        settings,
        workflow_version="enhanced_v2",
        runtime_mode="ai_enhanced",
        use_mock=False,
        parser="pymupdf",
        retriever="keyword",
        financial_agent="v03",
        legal_agent="v03",
        business_agent="v03",
        market_agent="disabled",
        verifier="specialized_v03",
        supervisor="v03",
        llm_provider="openai_compatible",
        llm_api_key=environ["IPO_RISK_LLM_API_KEY"],
        llm_base_url=environ["IPO_RISK_LLM_BASE_URL"],
        llm_model=environ["IPO_RISK_LLM_MODEL"],
        llm_timeout_seconds=60,
        llm_max_retries=0,
        market_data_provider="unavailable",
        ipo_data_provider="catalog",
        market_context="none",
        final_supervisor="none",
        pr_f_run_dir="",
        report_generator="v03",
    )
    return settings, sha256_file(config_path)


def build_provider(settings: Settings, budget: RequestBudget) -> AuditedStructuredProvider:
    import httpx
    from openai import OpenAI

    transport = httpx.Client(
        proxy="http://127.0.0.1:7890",
        timeout=settings.llm_timeout_seconds,
        verify=True,
    )
    client = OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout_seconds,
        max_retries=0,
        http_client=transport,
    )
    delegate = OpenAICompatibleLLMProvider(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=0,
        client=client,
    )
    delegate._client = BudgetedClient(delegate._client, budget)
    return AuditedStructuredProvider(delegate, budget)


def build_service(
    settings: Settings, catalog_dir: Path, provider: AuditedStructuredProvider
) -> tuple[IPOAnalysisService, CatalogIPODataProvider]:
    catalog = CatalogIPODataProvider(catalog_dir)
    registry = default_registry()
    registry.register("ipo_data_provider", "catalog", lambda: catalog)
    registry.register("llm_provider", "openai_compatible", lambda **_: provider)
    container = DependencyContainer(settings, registry)
    return IPOAnalysisService(settings, container, _MemoryRepository()), catalog


def synthetic_smoke(provider: AuditedStructuredProvider) -> dict[str, Any]:
    evidence = synthetic_evidence()
    result = provider.generate_structured(
        task_name="shareholder_rights_extract",
        prompt_version="legal_shareholder_rights_v1",
        evidence=evidence,
        response_model=ShareholderRightCandidate,
    )
    metadata = provider.last_call_metadata
    return {
        "status": "PASS",
        "schema": type(result).__name__,
        "resolved_model_identity": metadata.model_name if metadata else "NOT_EXPOSED_BY_API",
        "response_hash": metadata.raw_response_hash if metadata else None,
    }


def compact_result(
    result: Any,
    *,
    case_id: str,
    stock_code: str,
    revision: str,
    config_sha256: str,
    protocol_sha256: str,
    pdf_identity: dict[str, Any],
    elapsed: float,
    calls: list[dict[str, Any]],
) -> dict[str, Any]:
    modes = (result.metadata or {}).get("component_modes") or {}
    expected = {
        "parser": "real",
        "retriever": "real",
        "legal_agent": "real",
        "business_agent": "real",
        "llm_provider": "openai_compatible",
        "llm_status": "available",
    }
    if any(modes.get(key) != value for key, value in expected.items()):
        raise RealLLMRunError("REAL_LLM_COMPONENT_IDENTITY_FAIL")
    buckets = {
        name: [
            offline._compact_risk(risk)
            for risk in getattr(result, name)
            if risk.risk_code in set(ROLE_B_RISK_CODES)
        ]
        for name in ("verified_risks", "pending_risks", "rejected_risks")
    }
    return {
        "stock_code": stock_code,
        **buckets,
        "status": result.status.value,
        "metadata": {
            "case_id": case_id,
            "source_revision": revision,
            "config_sha256": config_sha256,
            "protocol_sha256": protocol_sha256,
            "provider_mode": "real_external_llm",
            "configuration": {
                "workflow_version": "enhanced_v2",
                "runtime_mode": "ai_enhanced",
                "use_mock": False,
            },
            "component_modes": {key: modes[key] for key in expected},
            "pdf_sha256": pdf_identity["sha256"],
            "pdf_file_size_bytes": pdf_identity["file_size_bytes"],
            "pdf_page_count": pdf_identity["physical_pages"],
            "diagnostic_codes": sorted({error.code for error in result.errors}),
            "elapsed_seconds": round(elapsed, 3),
            "llm_calls": calls,
            "compact_projection": True,
            "evidence_text_persisted": False,
            "gold_used_for_prediction": False,
        },
        "agent_logs": [],
    }


def load_existing(path: Path, *, revision: str, config_sha256: str, protocol_sha256: str) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        metadata = payload.get("metadata") or {}
        case_id = str(metadata.get("case_id") or "")
        expected = {"source_revision": revision, "config_sha256": config_sha256, "protocol_sha256": protocol_sha256}
        if case_id not in DEVELOPMENT_CASE_IDS or any(metadata.get(k) != v for k, v in expected.items()):
            raise RealLLMRunError("RESUME_IDENTITY_MISMATCH")
        rows[case_id] = payload
    return rows


def evaluate_results(args: argparse.Namespace, results: Path) -> dict[str, Any]:
    golden, fields = _load_role_b_golden(args.golden)
    golden = [row for row in golden if row["benchmark_split"] == "development"]
    predictions = load_results(results)
    raw = evaluate(predictions, golden, fields)
    per_risk: dict[str, Any] = {}
    for code in ROLE_B_RISK_CODES:
        metric = evaluate(predictions, [row for row in golden if row["risk_code"] == code], fields)
        per_risk[code] = {"risk": metric["risk"], "evidence": metric["evidence"]}
    return {"overall": raw, "per_risk": per_risk}


def run(args: argparse.Namespace, environ: dict[str, str]) -> dict[str, Any]:
    validate_frozen_environment(environ)
    if shutil.disk_usage(args.temp_dir.parent).free < DISK_FLOOR_BYTES:
        raise RealLLMRunError("DISK_FLOOR_FAIL")
    settings, config_sha256 = ai_settings(args.config, environ)
    revision = source_revision()
    catalog = offline.load_catalog_cases(args.prospectus_manifest)
    budget = RequestBudget(MAX_HTTP_REQUESTS, _count=args.prior_http_requests)
    provider = build_provider(settings, budget)
    prior_manifest: dict[str, Any] = {}
    if args.resume:
        protocol, prior_manifest, smoke, protocol_sha256 = load_resume_state(
            args, revision=revision, model=settings.llm_model
        )
    else:
        protocol, protocol_sha256 = refreeze_protocol(args)
        try:
            smoke = synthetic_smoke(provider)
        except Exception as exc:
            protocol["synthetic_smoke"] = {
                "status": "FAIL",
                "error_type": type(exc).__name__,
                "error_code": getattr(exc, "code", type(exc).__name__),
            }
            protocol["http_requests_observed"] = budget.count
            protocol["resolved_model_identity"] = "NOT_AVAILABLE"
            atomic_json(args.protocol, protocol)
            raise
        protocol["synthetic_smoke"] = smoke
        protocol["resolved_model_identity"] = smoke["resolved_model_identity"]
        protocol["http_requests_observed"] = budget.count
        atomic_json(args.protocol, protocol)
        protocol_sha256 = sha256_file(args.protocol)
    if args.temp_dir.exists():
        raise RealLLMRunError("TEMP_DIR_ALREADY_EXISTS")
    args.temp_dir.mkdir(parents=False)
    year_path = args.temp_dir / "current_year.zip"
    pdf_path = args.temp_dir / "current.pdf"
    start_free = shutil.disk_usage(args.temp_dir.parent).free
    minimum_free = start_free
    existing = load_existing(args.results, revision=revision, config_sha256=config_sha256, protocol_sha256=protocol_sha256)
    manifest: dict[str, Any] = {
        "result": "RUNNING",
        "protocol_sha256": protocol_sha256,
        "source_revision": revision,
        "synthetic_smoke": smoke,
        "environment_presence": secret_presence(environ),
        "cases": dict(prior_manifest.get("cases") or {}),
        "http_requests": budget.count,
        "2024_validation_opened": False,
        "2025_blind_accessed": False,
        "available_disk_before_bytes": start_free,
    }
    try:
        for year in (2020, 2021, 2022, 2023):
            case_ids = [case for case in CASE_ORDER if int(catalog[case]["source_year"]) == year and case not in existing]
            if not case_ids:
                continue
            try:
                with zipfile.ZipFile(args.outer_zip) as outer:
                    info = offline.exact_member(offline.validate_archive_members(outer.infolist()), basename=offline.YEAR_ARCHIVES[year], minimum_size=100 * 1024 * 1024)
                    offline.stream_member(outer, info, year_path)
                with zipfile.ZipFile(year_path) as annual:
                    infos = offline.validate_archive_members(annual.infolist())
                    for case_id in case_ids:
                        row = catalog[case_id]
                        started = time.perf_counter()
                        calls_before = len(provider.calls)
                        record: dict[str, Any] = {"status": "RUNNING"}
                        service = source = result = None
                        try:
                            info = offline.exact_member(infos, basename=row["source_filename"])
                            offline.stream_member(annual, info, pdf_path)
                            identity = offline.validate_pdf_identity(pdf_path, row)
                            service, source = build_service(settings, args.catalog_dir, provider)
                            profile = source.get_by_case_id(case_id)
                            result = service.analyze(
                                IPOAnalysisRequest(
                                    company_name=profile.company_name,
                                    stock_code=profile.stock_code,
                                    listing_date=profile.listing_date,
                                    prospectus_path=str(pdf_path),
                                    workflow_version=settings.workflow_version,
                                    parser_name=settings.parser,
                                    predictor_name=settings.predictor,
                                    use_mock=False,
                                    options={"case_id": case_id},
                                )
                            )
                            calls = [dict(call, case_id=case_id) for call in provider.calls[calls_before:]]
                            compact = compact_result(
                                result,
                                case_id=case_id,
                                stock_code=row["stock_code_wind"],
                                revision=revision,
                                config_sha256=config_sha256,
                                protocol_sha256=protocol_sha256,
                                pdf_identity=identity,
                                elapsed=time.perf_counter() - started,
                                calls=calls,
                            )
                            existing[case_id] = compact
                            atomic_jsonl(args.results, existing)
                            record = {"status": "SUCCESS", "http_requests": len(calls), "analysis_status": compact["status"], "pdf_sha_verified": True}
                        except Exception as exc:
                            record = {"status": "FAILED", "error_type": type(exc).__name__, "error_code": getattr(exc, "code", type(exc).__name__)}
                        finally:
                            result = service = source = None
                            pdf_path.unlink(missing_ok=True)
                            gc.collect()
                            record["cleanup"] = "PASS" if not pdf_path.exists() else "FAIL"
                            manifest["cases"][case_id] = record
                            manifest["http_requests"] = budget.count
                            atomic_json(args.run_manifest, manifest)
                            minimum_free = min(minimum_free, shutil.disk_usage(args.temp_dir.parent).free)
                        if record["status"] != "SUCCESS":
                            raise RealLLMRunError(f"CASE_FAILED:{case_id}:{record['error_code']}")
            finally:
                pdf_path.unlink(missing_ok=True)
                year_path.unlink(missing_ok=True)
    finally:
        pdf_path.unlink(missing_ok=True)
        year_path.unlink(missing_ok=True)
        if args.temp_dir.exists() and not any(args.temp_dir.iterdir()):
            args.temp_dir.rmdir()
    metrics = evaluate_results(args, args.results)
    risk = metrics["overall"]["risk"]
    evidence = metrics["overall"]["evidence"]
    passed = risk["f1"] >= 0.8 and evidence["recall_at_5"] >= 0.85
    manifest.update(
        {
            "result": "PASS" if passed else "MEASURED_FAIL",
            "development_cases": len(existing),
            "real_llm_cases": len(existing),
            "metrics": metrics,
            "risk_target": "PASS" if risk["f1"] >= 0.8 else "FAIL",
            "evidence_target": "PASS" if evidence["recall_at_5"] >= 0.85 else "FAIL",
            "http_requests": budget.count,
            "available_disk_after_bytes": shutil.disk_usage(args.outer_zip.parent).free,
            "peak_temporary_disk_bytes": max(0, start_free - minimum_free),
            "temporary_directory_clean": not args.temp_dir.exists(),
        }
    )
    atomic_json(args.run_manifest, manifest)
    atomic_json(args.summary, manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outer-zip", type=Path, default=Path("D:/Multi-Project/07-智能风控与量化建模赛道-东吴证券-基于多智能体协同的港股IPO招股书解析与上市后风险预警探索.zip"))
    parser.add_argument("--temp-dir", type=Path, default=Path("D:/Multi-Project/.tmp_role_b_real_llm"))
    parser.add_argument("--config", type=Path, default=Path("configs/v03_ai.yaml"))
    parser.add_argument("--prospectus-manifest", type=Path, default=Path("data/catalog/ipo_prospectus_manifest.csv"))
    parser.add_argument("--catalog-dir", type=Path, default=Path("data/catalog"))
    parser.add_argument("--golden", type=Path, default=Path("tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv"))
    parser.add_argument("--evaluator", type=Path, default=Path("src/ipo_risk/evaluation/document_intelligence_benchmark.py"))
    parser.add_argument("--protocol", type=Path, default=Path("reports/v045_role_b/real_llm_benchmark_protocol.json"))
    parser.add_argument("--results", type=Path, default=Path("reports/v045_role_b/real_llm_development_analysis_results.jsonl"))
    parser.add_argument("--run-manifest", type=Path, default=Path("reports/v045_role_b/real_llm_run_manifest.json"))
    parser.add_argument("--summary", type=Path, default=Path("reports/v045_role_b/real_llm_benchmark_summary.json"))
    parser.add_argument(
        "--prior-http-requests",
        type=int,
        default=5,
        help="already-attempted transport calls from disclosed pre-run engineering failures",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume an interrupted RUNNING manifest without changing its frozen protocol.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        result = run(parse_args(), dict(os.environ))
    except (RealLLMBenchmarkError, RealLLMRunError, LLMProviderError, OSError, zipfile.BadZipFile) as exc:
        print(json.dumps({"result": "BLOCKED", "blocker": getattr(exc, "code", str(exc)), "environment_presence": secret_presence(os.environ)}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
