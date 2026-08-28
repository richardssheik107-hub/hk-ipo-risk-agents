"""Run the governed current fixed-10 offline from the nested prospectus ZIP.

This is a benchmark adapter, not a production loader.  A nested annual archive
is opened through ``ZipExtFile`` and never copied to disk.  At most one PDF is
staged because the production PyMuPDF parser requires a real path; that file is
always deleted in ``finally``.  Predictions contain only final RiskItem fields
and their bounded Evidence, never parsed pages or document chunks.
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
import os
import tempfile
import time
import zipfile
from dataclasses import fields, replace
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from ipo_risk.core.config import Settings
try:
    from run_v045_role_b_offline_pdf_benchmark import (
        _MemoryRepository, exact_member, sha256_file, stream_member,
        validate_archive_members, validate_pdf_identity,
    )
except ModuleNotFoundError:  # imported as ``scripts.*`` by tests
    from scripts.run_v045_role_b_offline_pdf_benchmark import (
        _MemoryRepository, exact_member, sha256_file, stream_member,
        validate_archive_members, validate_pdf_identity,
    )
from ipo_risk.core.container import DependencyContainer, default_registry
from ipo_risk.providers.catalog import CatalogIPODataProvider
from ipo_risk.schemas import IPOAnalysisRequest
from ipo_risk.services.analysis_service import IPOAnalysisService


YEAR_ARCHIVES = {2020: "2020_138份.zip", 2021: "2021_88份.zip", 2022: "2022_87份.zip", 2023: "2023_63份.zip"}


class Fixed10ZipError(RuntimeError):
    pass


def load_subset(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("split") != "development" or payload.get("validation_opened") is not False:
        raise Fixed10ZipError("fixed subset is not governed Development-only")
    if payload.get("blind_2025_outcome_accessed") is not False:
        raise Fixed10ZipError("fixed subset accessed Blind data")
    case_ids = [str(row["case_id"]) for row in payload.get("cases", [])]
    if len(case_ids) != 10 or len(set(case_ids)) != 10:
        raise Fixed10ZipError("fixed subset must contain ten unique cases")
    return case_ids


def load_catalog(path: Path, case_ids: list[str]) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        all_rows = {row["case_id"]: row for row in csv.DictReader(handle)}
    rows = {case_id: all_rows[case_id] for case_id in case_ids if case_id in all_rows}
    if len(rows) != len(case_ids):
        raise Fixed10ZipError("one or more fixed cases are absent from prospectus catalog")
    if any(row["dataset_split"] != "development" for row in rows.values()):
        raise Fixed10ZipError("non-Development catalog row rejected")
    return rows


def offline_settings(path: Path) -> tuple[Settings, str]:
    values = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    defaults = Settings()
    known = {item.name for item in fields(Settings)}
    settings = Settings(**{name: values.get(name, getattr(defaults, name)) for name in known})
    settings = replace(
        settings,
        runtime_mode="offline", use_mock=False, parser="pymupdf",
        retriever="hybrid_bm25", llm_provider="unavailable",
        market_data_provider="unavailable", market_agent="disabled",
        market_context="none", final_supervisor="none", pr_f_run_dir="",
    )
    if settings.retriever != "hybrid_bm25" or settings.llm_provider != "unavailable":
        raise Fixed10ZipError("offline current-baseline policy mismatch")
    return settings, sha256_file(path)


def build_service(settings: Settings, catalog_dir: Path) -> tuple[IPOAnalysisService, CatalogIPODataProvider]:
    provider = CatalogIPODataProvider(catalog_dir)
    registry = default_registry()
    registry.register("ipo_data_provider", "catalog", lambda: provider)
    container = DependencyContainer(settings, registry)
    return IPOAnalysisService(settings, container, _MemoryRepository()), provider


def compact_evidence(item: Any) -> dict[str, Any]:
    return {
        "evidence_id": item.evidence_id, "document_id": item.document_id,
        "chunk_id": item.chunk_id, "page": item.page, "section": item.section,
        "text": item.text, "relevance_score": item.relevance_score,
    }


def compact_risk(item: Any) -> dict[str, Any]:
    calculation = None
    if item.calculation is not None:
        calculation = {
            "result": item.calculation.result, "unit": item.calculation.unit,
            "success": item.calculation.success,
            "evidence_ids": list(item.calculation.evidence_ids),
        }
    return {
        "risk_id": item.risk_id, "risk_code": item.risk_code,
        "level": item.level.value, "verification_status": item.verification_status.value,
        "evidence": [compact_evidence(value) for value in item.evidence],
        "calculation": calculation,
    }


def compact_result(result: Any, case_id: str, elapsed: float, pdf_identity: dict[str, Any]) -> dict[str, Any]:
    modes = (result.metadata or {}).get("component_modes") or {}
    return {
        "case_id": case_id,
        "stock_code": result.stock_code,
        "verified_risks": [compact_risk(item) for item in result.verified_risks],
        "pending_risks": [compact_risk(item) for item in result.pending_risks],
        "rejected_risks": [compact_risk(item) for item in result.rejected_risks],
        "status": result.status.value,
        "metadata": {
            "case_id": case_id,
            "component_modes": modes,
            "configuration": {"runtime_mode": "offline", "use_mock": False},
            "pdf_sha256": pdf_identity["sha256"],
            "pdf_page_count": pdf_identity["physical_pages"],
            "elapsed_seconds": round(elapsed, 3),
            "compact_projection": True,
            "parsed_document_text_persisted": False,
            "gold_used_for_prediction": False,
        },
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    case_ids = load_subset(args.subset)
    catalog = load_catalog(args.catalog, case_ids)
    settings, config_hash = offline_settings(args.config)
    results: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fixed10_zip_", dir=args.temp_parent) as temporary:
        pdf_path = Path(temporary) / "current.pdf"
        try:
            with zipfile.ZipFile(args.outer_zip) as outer:
                outer_infos = validate_archive_members(outer.infolist())
                for year in sorted({int(catalog[case_id]["source_year"]) for case_id in case_ids}):
                    annual_info = exact_member(outer_infos, basename=YEAR_ARCHIVES[year])
                    with outer.open(annual_info) as annual_stream, zipfile.ZipFile(annual_stream) as annual:
                        annual_infos = validate_archive_members(annual.infolist())
                        for case_id in [value for value in case_ids if int(catalog[value]["source_year"]) == year]:
                            row = catalog[case_id]
                            started = time.perf_counter()
                            try:
                                pdf_info = exact_member(annual_infos, basename=row["source_filename"])
                                if pdf_info.file_size > 100 * 1024**2:
                                    raise Fixed10ZipError("single PDF exceeds 100 MiB safety boundary")
                                stream_member(annual, pdf_info, pdf_path)
                                identity = validate_pdf_identity(pdf_path, row)
                                service, provider = build_service(settings, args.catalog_dir)
                                profile = provider.get_by_case_id(case_id)
                                result = service.analyze(IPOAnalysisRequest(
                                    company_name=profile.company_name, stock_code=profile.stock_code,
                                    listing_date=profile.listing_date, prospectus_path=str(pdf_path),
                                    workflow_version=settings.workflow_version,
                                    parser_name=settings.parser, predictor_name=settings.predictor,
                                    use_mock=False, options={"case_id": case_id},
                                ))
                                projected = compact_result(result, case_id, time.perf_counter() - started, identity)
                                results.append(projected)
                                statuses.append({"case_id": case_id, "status": projected["status"], "error_type": ""})
                                args.output.write_text("".join(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n" for value in results), encoding="utf-8")
                                print(f"case={case_id} status={projected['status']} elapsed={projected['metadata']['elapsed_seconds']}")
                            except Exception as exc:
                                statuses.append({"case_id": case_id, "status": "failed", "error_type": type(exc).__name__})
                                print(f"case={case_id} status=failed error={type(exc).__name__}")
                            finally:
                                if pdf_path.exists():
                                    pdf_path.unlink()
                                gc.collect()
        finally:
            if pdf_path.exists():
                pdf_path.unlink()
    manifest = {
        "benchmark": "current_fixed10_offline_zip_v1", "case_ids": case_ids,
        "successful_case_count": len(results), "statuses": statuses,
        "retriever": settings.retriever, "llm_provider": settings.llm_provider,
        "network_llm_calls": 0, "config_sha256": config_hash,
        "nested_year_archives_persisted": 0, "temporary_pdf_remaining": False,
        "gold_used_for_prediction": False, "validation_opened": False,
        "blind_2025_outcome_accessed": False,
    }
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outer_zip", type=Path)
    parser.add_argument("--subset", type=Path, default=Path("reports/v045_role_b/fixed10_development_subset.json"))
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog/ipo_prospectus_manifest.csv"))
    parser.add_argument("--catalog-dir", type=Path, default=Path("data/catalog"))
    parser.add_argument("--config", type=Path, default=Path("configs/v045_competition_offline.yaml"))
    parser.add_argument("--temp-parent", type=Path, default=Path("reports/experiments"))
    parser.add_argument("--output", type=Path, default=Path("reports/experiments/fixed10_offline_predictions.jsonl"))
    parser.add_argument("--manifest", type=Path, default=Path("reports/experiments/fixed10_offline_run_manifest.json"))
    args = parser.parse_args()
    print(json.dumps(run(args), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
