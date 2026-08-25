"""Stream the ten Role-B Development PDFs from a nested ZIP and analyse offline.

Prediction generation is deliberately separated from Gold evaluation: this
module never imports or reads the Human Golden or expert annotations.  It stages
one yearly ZIP and one PDF at a time, validates frozen catalog identity, runs the
non-mock offline Document pipeline, persists a compact projection, and cleans the
staged files in ``finally`` blocks.
"""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import os
import shutil
import subprocess
import time
import zipfile
from dataclasses import fields, replace
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

import yaml

from ipo_risk.core.config import Settings
from ipo_risk.core.container import DependencyContainer, default_registry
from ipo_risk.providers.catalog import CatalogIPODataProvider
from ipo_risk.schemas import IPOAnalysisRequest
from ipo_risk.services.analysis_service import IPOAnalysisService


BUFFER_BYTES = 4 * 1024 * 1024
DISK_FLOOR_BYTES = 3 * 1024**3
ROLE_B_RISKS = {
    "redemption_rights",
    "material_litigation_compliance",
    "precommercial_product",
}
YEAR_ARCHIVES = {
    2020: "2020_138份.zip",
    2021: "2021_88份.zip",
    2022: "2022_87份.zip",
    2023: "2023_63份.zip",
}
CASE_ORDER = (
    "ipo_2021_09898",
    "ipo_2020_01167",
    "ipo_2020_01942",
    "ipo_2020_01961",
    "ipo_2020_09600",
    "ipo_2020_09633",
    "ipo_2022_06698",
    "ipo_2022_09863",
    "ipo_2023_02451",
    "ipo_2023_02517",
)
CASE_ALLOWLIST = frozenset(CASE_ORDER)


class OfflineBenchmarkError(RuntimeError):
    """A governed input, policy, or cleanup invariant failed."""


class _MemoryRepository:
    """Round-trip repository used to avoid persisting full Evidence text."""

    def __init__(self) -> None:
        self._items: dict[str, Any] = {}

    def save(self, result: Any) -> None:
        self._items[result.analysis_id] = result

    def get(self, analysis_id: str) -> Any:
        return self._items.get(analysis_id)


def free_bytes(path: Path) -> int:
    return int(shutil.disk_usage(path).free)


def enforce_disk_floor(path: Path, floor_bytes: int = DISK_FLOOR_BYTES) -> int:
    available = free_bytes(path)
    if available < floor_bytes:
        raise OfflineBenchmarkError(
            f"available disk {available} is below the {floor_bytes} byte safety floor"
        )
    return available


def _safe_member_name(name: str) -> None:
    pure = PurePosixPath(name)
    if not name or pure.is_absolute() or ".." in pure.parts or "\\" in name:
        raise OfflineBenchmarkError(f"unsafe ZIP member path: {name!r}")


def validate_archive_members(infos: Iterable[zipfile.ZipInfo]) -> list[zipfile.ZipInfo]:
    materialized = list(infos)
    seen: set[str] = set()
    for info in materialized:
        _safe_member_name(info.filename)
        if info.filename in seen:
            raise OfflineBenchmarkError(f"duplicate ZIP member path: {info.filename!r}")
        seen.add(info.filename)
    return materialized


def exact_member(
    infos: Iterable[zipfile.ZipInfo], *, basename: str, minimum_size: int = 1
) -> zipfile.ZipInfo:
    matches = [
        info
        for info in infos
        if not info.is_dir()
        and PurePosixPath(info.filename).name == basename
        and info.file_size >= minimum_size
    ]
    if len(matches) != 1:
        raise OfflineBenchmarkError(
            f"expected exactly one ZIP member named {basename!r}; found {len(matches)}"
        )
    return matches[0]


def stream_member(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    target: Path,
    *,
    buffer_bytes: int = BUFFER_BYTES,
) -> None:
    if target.exists():
        raise OfflineBenchmarkError(f"refusing to overwrite staged file: {target}")
    with archive.open(info, "r") as source, target.open("xb") as destination:
        shutil.copyfileobj(source, destination, length=buffer_bytes)
    if target.stat().st_size != info.file_size:
        target.unlink(missing_ok=True)
        raise OfflineBenchmarkError(f"streamed size mismatch for {info.filename!r}")


def sha256_file(path: Path, *, buffer_bytes: int = BUFFER_BYTES) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(buffer_bytes):
            digest.update(chunk)
    return digest.hexdigest()


def source_revision() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "unknown"


def offline_settings(config_path: Path) -> tuple[Settings, str]:
    """Load YAML directly, bypassing environment-variable/secret access."""

    values = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    defaults = Settings()
    known = {item.name for item in fields(Settings)}
    settings = Settings(
        **{name: values.get(name, getattr(defaults, name)) for name in known}
    )
    settings = replace(
        settings,
        workflow_version="enhanced_v2",
        runtime_mode="offline",
        use_mock=False,
        parser="pymupdf",
        retriever="keyword",
        legal_agent="v03",
        business_agent="v03",
        market_agent="disabled",
        verifier="specialized_v03",
        llm_provider="unavailable",
        market_data_provider="unavailable",
        ipo_data_provider="catalog",
        market_context="none",
        final_supervisor="none",
        pr_f_run_dir="",
    )
    assert_offline_policy(settings)
    return settings, sha256_file(config_path)


def assert_offline_policy(settings: Settings) -> None:
    required = {
        "runtime_mode": "offline",
        "use_mock": False,
        "parser": "pymupdf",
        "retriever": "keyword",
        "legal_agent": "v03",
        "business_agent": "v03",
        "llm_provider": "unavailable",
        "market_data_provider": "unavailable",
    }
    mismatches = {
        name: getattr(settings, name)
        for name, expected in required.items()
        if getattr(settings, name) != expected
    }
    if mismatches:
        raise OfflineBenchmarkError(f"offline-only policy mismatch: {sorted(mismatches)}")


def load_catalog_cases(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = {row["case_id"]: row for row in csv.DictReader(handle)}
    selected: dict[str, dict[str, str]] = {}
    for case_id in CASE_ORDER:
        row = rows.get(case_id)
        if row is None:
            raise OfflineBenchmarkError(f"catalog row missing for {case_id}")
        if row.get("dataset_split") != "development":
            raise OfflineBenchmarkError(f"non-Development case rejected: {case_id}")
        if int(row["source_year"]) not in YEAR_ARCHIVES:
            raise OfflineBenchmarkError(f"disallowed source year for {case_id}")
        selected[case_id] = row
    return selected


def validate_case_selection(case_ids: Iterable[str]) -> list[str]:
    requested = list(case_ids)
    if not requested:
        raise OfflineBenchmarkError("at least one Development case is required")
    if len(requested) != len(set(requested)):
        raise OfflineBenchmarkError("duplicate case_id in requested selection")
    rejected = sorted(set(requested) - CASE_ALLOWLIST)
    if rejected:
        raise OfflineBenchmarkError(f"case allowlist rejection: {rejected}")
    return [case_id for case_id in CASE_ORDER if case_id in set(requested)]


def validate_pdf_identity(path: Path, row: dict[str, str]) -> dict[str, Any]:
    if path.name != "current.pdf":
        raise OfflineBenchmarkError("staged PDF must use the fixed current.pdf name")
    size = path.stat().st_size
    expected_size = int(row["file_size_bytes"])
    if size != expected_size:
        raise OfflineBenchmarkError(
            f"INPUT_IDENTITY_FAIL file size for {row['case_id']}: {size} != {expected_size}"
        )
    digest = sha256_file(path)
    if digest != row["sha256"]:
        raise OfflineBenchmarkError(f"INPUT_IDENTITY_FAIL SHA-256 for {row['case_id']}")
    import fitz

    with fitz.open(path) as document:
        pages = int(document.page_count)
    expected_pages = int(row["pdf_page_count"])
    if pages != expected_pages:
        raise OfflineBenchmarkError(
            f"PARSER_PAGE_COUNT_MISMATCH for {row['case_id']}: {pages} != {expected_pages}"
        )
    return {"file_size_bytes": size, "sha256": digest, "physical_pages": pages}


def build_service(settings: Settings, catalog_dir: Path) -> tuple[IPOAnalysisService, CatalogIPODataProvider]:
    assert_offline_policy(settings)
    provider = CatalogIPODataProvider(catalog_dir)
    registry = default_registry()
    registry.register("ipo_data_provider", "catalog", lambda: provider)
    container = DependencyContainer(settings, registry)
    return IPOAnalysisService(settings, container, _MemoryRepository()), provider


def _compact_evidence(evidence: Any, rank: int) -> dict[str, Any]:
    return {
        "evidence_id": evidence.evidence_id,
        "document_id": evidence.document_id,
        "chunk_id": evidence.chunk_id,
        "page": evidence.page,
        "section": evidence.section,
        "relevance_score": evidence.relevance_score,
        "rank": rank,
    }


def _compact_risk(risk: Any) -> dict[str, Any]:
    calculation = None
    if risk.calculation is not None:
        calculation = {
            "skill_name": risk.calculation.skill_name,
            "skill_version": risk.calculation.skill_version,
            "result": risk.calculation.result,
            "unit": risk.calculation.unit,
            "evidence_ids": list(risk.calculation.evidence_ids),
            "success": risk.calculation.success,
            "error": risk.calculation.error,
        }
    return {
        "risk_id": risk.risk_id,
        "risk_code": risk.risk_code,
        "verification_status": risk.verification_status.value,
        "agent_name": risk.agent_name,
        "evidence": [
            _compact_evidence(item, rank)
            for rank, item in enumerate(risk.evidence, start=1)
        ],
        "calculation": calculation,
    }


def compact_result(
    result: Any,
    *,
    case_id: str,
    stock_code: str,
    revision: str,
    config_path: Path,
    config_sha256: str,
    pdf_identity: dict[str, Any],
    elapsed_seconds: float,
) -> dict[str, Any]:
    modes = (result.metadata or {}).get("component_modes") or {}
    required_modes = {
        "parser": "real",
        "retriever": "real",
        "legal_agent": "real",
        "business_agent": "real",
        "llm_provider": "unavailable",
        "llm_status": "offline_unavailable",
    }
    if any(modes.get(key) != expected for key, expected in required_modes.items()):
        raise OfflineBenchmarkError("mock/offline component identity guard failed")
    configuration = (result.metadata or {}).get("configuration") or {}
    if configuration.get("use_mock") is not False or configuration.get("runtime_mode") != "offline":
        raise OfflineBenchmarkError("runtime metadata is not governed offline/non-mock")
    buckets = {
        name: [
            _compact_risk(risk)
            for risk in getattr(result, name)
            if risk.risk_code in ROLE_B_RISKS
        ]
        for name in ("verified_risks", "pending_risks", "rejected_risks")
    }
    diagnostic_codes = sorted({error.code for error in result.errors})
    return {
        "stock_code": stock_code,
        **buckets,
        "status": result.status.value,
        "metadata": {
            "case_id": case_id,
            "source_revision": revision,
            "config_identity": config_path.as_posix(),
            "config_sha256": config_sha256,
            "provider_mode": "unavailable/offline",
            "configuration": {
                "workflow_version": "enhanced_v2",
                "runtime_mode": "offline",
                "use_mock": False,
            },
            "component_modes": {key: modes[key] for key in required_modes},
            "pdf_sha256": pdf_identity["sha256"],
            "pdf_file_size_bytes": pdf_identity["file_size_bytes"],
            "pdf_page_count": pdf_identity["physical_pages"],
            "diagnostic_codes": diagnostic_codes,
            "elapsed_seconds": round(elapsed_seconds, 3),
            "compact_projection": True,
            "evidence_text_persisted": False,
            "gold_used_for_prediction": False,
        },
        "agent_logs": [],
    }


def load_existing_results(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    results: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            case_id = str((payload.get("metadata") or {}).get("case_id") or "")
            if case_id in results:
                raise OfflineBenchmarkError(f"duplicate existing result for {case_id}")
            if case_id not in CASE_ALLOWLIST:
                raise OfflineBenchmarkError(f"non-allowlisted existing result: {case_id}")
            results[case_id] = payload
    return results


def resume_matches(
    payload: dict[str, Any],
    *,
    row: dict[str, str],
    revision: str,
    config_sha256: str,
) -> bool:
    metadata = payload.get("metadata") or {}
    modes = metadata.get("component_modes") or {}
    return all(
        (
            payload.get("stock_code") == row["stock_code_wind"],
            payload.get("status") == "completed",
            metadata.get("case_id") == row["case_id"],
            metadata.get("source_revision") == revision,
            metadata.get("config_sha256") == config_sha256,
            metadata.get("pdf_sha256") == row["sha256"],
            metadata.get("provider_mode") == "unavailable/offline",
            (metadata.get("configuration") or {}).get("use_mock") is False,
            metadata.get("compact_projection") is True,
            metadata.get("evidence_text_persisted") is False,
            metadata.get("gold_used_for_prediction") is False,
            modes.get("parser") == "real",
            modes.get("retriever") == "real",
            modes.get("legal_agent") == "real",
            modes.get("business_agent") == "real",
            modes.get("llm_provider") == "unavailable",
        )
    )


def atomic_write_jsonl(path: Path, results: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        for case_id in CASE_ORDER:
            if case_id in results:
                handle.write(json.dumps(results[case_id], ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _request_for(profile: Any, settings: Settings, pdf_path: Path, case_id: str) -> IPOAnalysisRequest:
    return IPOAnalysisRequest(
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


def _cleanup_file(path: Path) -> None:
    if path.exists():
        path.unlink()


def _manifest_base(
    *, outer_zip: Path, revision: str, config_path: Path, config_sha256: str
) -> dict[str, Any]:
    return {
        "manifest_version": "v045_role_b_offline_pdf_benchmark_v1",
        "outer_zip": outer_zip.name,
        "outer_zip_size_bytes": outer_zip.stat().st_size,
        "source_revision": revision,
        "config_identity": config_path.as_posix(),
        "config_sha256": config_sha256,
        "runtime_mode": "offline",
        "provider_mode": "unavailable/offline",
        "use_mock": False,
        "api_key_accessed": False,
        "network_model_calls": 0,
        "evidence_egress": 0,
        "validation_2024_opened": False,
        "blind_2025_accessed": False,
        "cases": {},
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    outer_zip = args.outer_zip.resolve()
    temp_dir = args.temp_dir.resolve()
    if not outer_zip.is_file():
        raise OfflineBenchmarkError(f"outer ZIP not found: {outer_zip}")
    if temp_dir.exists():
        raise OfflineBenchmarkError(f"temporary directory already exists: {temp_dir}")
    temp_dir.mkdir(parents=False)
    year_path = temp_dir / "current_year.zip"
    pdf_path = temp_dir / "current.pdf"
    available_start = enforce_disk_floor(temp_dir.parent)
    minimum_free = available_start
    settings, config_sha256 = offline_settings(args.config)
    revision = source_revision()
    catalog = load_catalog_cases(args.prospectus_manifest)
    selected = validate_case_selection(args.case_ids or CASE_ORDER)
    existing = load_existing_results(args.results)
    previous_manifest = (
        json.loads(args.run_manifest.read_text(encoding="utf-8"))
        if args.run_manifest.is_file()
        else {}
    )
    if previous_manifest and (
        previous_manifest.get("source_revision") != revision
        or previous_manifest.get("config_sha256") != config_sha256
        or previous_manifest.get("outer_zip_size_bytes") != outer_zip.stat().st_size
    ):
        raise OfflineBenchmarkError("existing run manifest identity mismatch")
    for case_id, payload in existing.items():
        if not resume_matches(
            payload, row=catalog[case_id], revision=revision, config_sha256=config_sha256
        ):
            raise OfflineBenchmarkError(f"existing result identity mismatch for {case_id}")
    pending = [case_id for case_id in selected if case_id not in existing]
    manifest = _manifest_base(
        outer_zip=outer_zip,
        revision=revision,
        config_path=args.config,
        config_sha256=config_sha256,
    )
    manifest["available_disk_before_bytes"] = available_start
    manifest["execution_available_disk_before_bytes"] = previous_manifest.get(
        "execution_available_disk_before_bytes",
        previous_manifest.get("available_disk_before_bytes", available_start),
    )
    manifest["requested_case_ids"] = selected
    manifest["resumed_case_ids"] = [case_id for case_id in selected if case_id in existing]
    for case_id in manifest["resumed_case_ids"]:
        payload = existing[case_id]
        row = catalog[case_id]
        risks = [
            risk
            for bucket in ("verified_risks", "pending_risks", "rejected_risks")
            for risk in payload.get(bucket, [])
        ]
        manifest["cases"][case_id] = {
            "case_id": case_id,
            "stock_code": row["stock_code_wind"],
            "status": "RESUMED_SUCCESS",
            "analysis_status": payload["status"],
            "pdf_located": True,
            "pdf_sha_verified": True,
            "physical_pages_expected": int(row["pdf_page_count"]),
            "physical_pages_parsed": int(payload["metadata"]["pdf_page_count"]),
            "parser_status": "PASS",
            "provider_mode": "unavailable/offline",
            "use_mock": False,
            "risk_output_count": len(risks),
            "evidence_count": sum(len(risk.get("evidence", [])) for risk in risks),
            "elapsed_seconds": payload["metadata"].get("elapsed_seconds"),
            "cleanup_status": "PASS",
        }
    try:
        for year in (2021, 2020, 2022, 2023):
            year_cases = [case_id for case_id in pending if int(catalog[case_id]["source_year"]) == year]
            if not year_cases:
                continue
            minimum_free = min(minimum_free, enforce_disk_floor(temp_dir.parent))
            try:
                with zipfile.ZipFile(outer_zip) as outer:
                    outer_infos = validate_archive_members(outer.infolist())
                    year_info = exact_member(
                        outer_infos,
                        basename=YEAR_ARCHIVES[year],
                        minimum_size=100 * 1024 * 1024,
                    )
                    stream_member(outer, year_info, year_path)
                minimum_free = min(minimum_free, enforce_disk_floor(temp_dir.parent))
                with zipfile.ZipFile(year_path) as annual:
                    annual_infos = validate_archive_members(annual.infolist())
                    for case_id in year_cases:
                        row = catalog[case_id]
                        started = time.perf_counter()
                        case_record: dict[str, Any] = {
                            "case_id": case_id,
                            "stock_code": row["stock_code_wind"],
                            "status": "RUNNING",
                        }
                        service = provider = result = None
                        try:
                            pdf_info = exact_member(
                                annual_infos,
                                basename=row["source_filename"],
                                minimum_size=1,
                            )
                            stream_member(annual, pdf_info, pdf_path)
                            identity = validate_pdf_identity(pdf_path, row)
                            case_record.update(
                                {
                                    "pdf_located": True,
                                    "pdf_sha_verified": True,
                                    "physical_pages_expected": int(row["pdf_page_count"]),
                                    "physical_pages_parsed": identity["physical_pages"],
                                    "parser_status": "PASS",
                                }
                            )
                            service, provider = build_service(settings, args.catalog_dir)
                            profile = provider.get_by_case_id(case_id)
                            if profile.stock_code != row["stock_code_wind"]:
                                raise OfflineBenchmarkError(f"catalog stock identity mismatch for {case_id}")
                            result = service.analyze(
                                _request_for(profile, settings, pdf_path, case_id)
                            )
                            elapsed = time.perf_counter() - started
                            compact = compact_result(
                                result,
                                case_id=case_id,
                                stock_code=row["stock_code_wind"],
                                revision=revision,
                                config_path=args.config,
                                config_sha256=config_sha256,
                                pdf_identity=identity,
                                elapsed_seconds=elapsed,
                            )
                            if compact["status"] == "failed":
                                raise OfflineBenchmarkError("analysis returned failed status")
                            existing[case_id] = compact
                            atomic_write_jsonl(args.results, existing)
                            risk_count = sum(
                                len(compact[name])
                                for name in ("verified_risks", "pending_risks", "rejected_risks")
                            )
                            evidence_count = sum(
                                len(risk["evidence"])
                                for name in ("verified_risks", "pending_risks", "rejected_risks")
                                for risk in compact[name]
                            )
                            case_record.update(
                                {
                                    "status": "SUCCESS",
                                    "analysis_status": compact["status"],
                                    "provider_mode": "unavailable/offline",
                                    "use_mock": False,
                                    "risk_output_count": risk_count,
                                    "evidence_count": evidence_count,
                                    "elapsed_seconds": round(elapsed, 3),
                                }
                            )
                        except Exception as exc:
                            case_record.update(
                                {
                                    "status": "FAILED",
                                    "error_code": (
                                        str(exc).split(":", 1)[0]
                                        if str(exc)
                                        else type(exc).__name__
                                    ),
                                    "error_type": type(exc).__name__,
                                }
                            )
                        finally:
                            result = service = provider = None
                            _cleanup_file(pdf_path)
                            gc.collect()
                            case_record["cleanup_status"] = "PASS" if not pdf_path.exists() else "FAIL"
                            available = enforce_disk_floor(temp_dir.parent)
                            minimum_free = min(minimum_free, available)
                            case_record["available_disk_after_case_bytes"] = available
                            manifest["cases"][case_id] = case_record
                            atomic_write_json(args.run_manifest, manifest)
            finally:
                _cleanup_file(pdf_path)
                _cleanup_file(year_path)
                minimum_free = min(minimum_free, enforce_disk_floor(temp_dir.parent))
    finally:
        _cleanup_file(pdf_path)
        _cleanup_file(year_path)
        if temp_dir.exists():
            if any(temp_dir.iterdir()):
                raise OfflineBenchmarkError("temporary directory contains unexpected files")
            temp_dir.rmdir()
    manifest["minimum_available_disk_bytes"] = min(
        int(previous_manifest.get("minimum_available_disk_bytes", minimum_free)),
        minimum_free,
    )
    manifest["peak_temporary_disk_bytes"] = max(
        int(previous_manifest.get("peak_temporary_disk_bytes", 0)),
        max(0, available_start - minimum_free),
    )
    manifest["available_disk_after_bytes"] = free_bytes(outer_zip.parent)
    manifest["temporary_pdf_remaining"] = False
    manifest["temporary_year_zip_remaining"] = False
    manifest["temporary_directory_clean"] = not temp_dir.exists()
    manifest["successful_case_count"] = sum(
        1
        for item in manifest["cases"].values()
        if item["status"] in {"SUCCESS", "RESUMED_SUCCESS"}
    )
    manifest["failed_case_count"] = sum(
        1 for item in manifest["cases"].values() if item["status"] == "FAILED"
    )
    atomic_write_json(args.run_manifest, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--outer-zip",
        type=Path,
        default=Path(
            "D:/Multi-Project/07-智能风控与量化建模赛道-东吴证券-"
            "基于多智能体协同的港股IPO招股书解析与上市后风险预警探索.zip"
        ),
    )
    parser.add_argument(
        "--temp-dir",
        type=Path,
        default=Path("D:/Multi-Project/.tmp_role_b_offline_benchmark"),
    )
    parser.add_argument(
        "--config", type=Path, default=Path("configs/v045_competition_offline.yaml")
    )
    parser.add_argument(
        "--prospectus-manifest",
        type=Path,
        default=Path("data/catalog/ipo_prospectus_manifest.csv"),
    )
    parser.add_argument("--catalog-dir", type=Path, default=Path("data/catalog"))
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("reports/v045_role_b/offline_development_analysis_results.jsonl"),
    )
    parser.add_argument(
        "--run-manifest",
        type=Path,
        default=Path("reports/v045_role_b/offline_pdf_run_manifest.json"),
    )
    parser.add_argument(
        "--case-id",
        dest="case_ids",
        action="append",
        help="repeatable allowlisted case_id; default runs all ten in frozen order",
    )
    args = parser.parse_args()
    try:
        manifest = run(args)
    except (OfflineBenchmarkError, OSError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        return 2
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 1 if manifest["failed_case_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
