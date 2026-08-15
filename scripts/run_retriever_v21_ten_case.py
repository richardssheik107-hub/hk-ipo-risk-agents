"""Run the frozen ten-case Retriever V2.1 ranking experiment."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

from ipo_risk.evaluation.expert_annotation import ExpertAnnotationBundle
from ipo_risk.evaluation.raw_retrieval_audit import build_raw_retrieval_audit, write_raw_retrieval_outputs
from ipo_risk.evaluation.retriever_v2_pilot import build_v2_retrieval_audit, load_audits
from ipo_risk.evaluation.retriever_v21_ten_case import (
    build_candidate_audit,
    extended_metrics,
    provenance_diagnostics,
    rank_matrix,
)
from ipo_risk.parsers.pymupdf_parser import PyMuPDFDocumentParser
from ipo_risk.retrieval.domain_aware_v21 import DomainAwareRetrieverV21, policy_hashes
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.schemas import DocumentParseRequest


DEVELOPMENT_CASES = ("ipo_2020_00368", "ipo_2020_01167", "ipo_2020_01408")
HISTORICAL_CASES = ("ipo_2020_01961",)
LOCKED_CASES = (
    "ipo_2020_01942", "ipo_2020_02057", "ipo_2020_02135",
    "ipo_2020_02263", "ipo_2020_02599", "ipo_2021_00013",
)
ALL_CASES = (*DEVELOPMENT_CASES, *HISTORICAL_CASES, *LOCKED_CASES)
ANNOTATION_SOURCE_SHA = "4ba86a4ebbb3033b6c9966d07f5351afa18dc206"
VARIANTS = (
    "v1", "v2_direct_only", "v2_direct_current_fusion", "v2_plus_neighbor",
    "v2", "v2_direct_family_rrf", "v21",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _catalog(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row["case_id"]: row for row in csv.DictReader(handle)}


def _resolve_pdf(row: dict[str, str], roots: list[Path]) -> Path:
    for root in roots:
        for path in root.rglob(row["source_filename"]):
            if path.is_file() and _sha256(path) == row["sha256"]:
                return path
    raise FileNotFoundError(f"SOURCE_PDF_NOT_FOUND:{row['case_id']}")


def _git_head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()


def _git_ref(ref: str) -> str:
    return subprocess.run(["git", "rev-parse", ref], check=True, capture_output=True, text=True).stdout.strip()


def _source_hashes() -> dict[str, str]:
    paths = {
        "v1_source_sha256": Path("src/ipo_risk/retrieval/keyword.py"),
        "v2_source_sha256": Path("src/ipo_risk/retrieval/domain_aware_v2.py"),
        "v21_source_sha256": Path("src/ipo_risk/retrieval/domain_aware_v21.py"),
        "runner_source_sha256": Path(__file__),
    }
    return {key: _sha256(path) for key, path in paths.items()}


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run_case(case_id: str, args: argparse.Namespace, variants: tuple[str, ...]) -> None:
    row = _catalog(args.catalog)[case_id]
    annotation_path = Path("expert_results") / case_id / "pass1" / "expert_annotation_v1.json"
    annotation_text = annotation_path.read_text(encoding="utf-8")
    bundle = ExpertAnnotationBundle.model_validate_json(annotation_text)
    if bundle.case_id != case_id or bundle.stock_code != row["stock_code_wind"]:
        raise ValueError(f"annotation identity mismatch: {case_id}")
    pdf_path = _resolve_pdf(row, args.pdf_root)
    parser = PyMuPDFDocumentParser()
    chunks = parser.parse(DocumentParseRequest(document_id=case_id, prospectus_path=str(pdf_path)))
    common = {
        "bundle": bundle, "chunks": chunks,
        "annotation_sha256": hashlib.sha256(annotation_text.encode()).hexdigest(),
        "pdf_sha256": row["sha256"], "pdf_page_count": int(row["pdf_page_count"]),
        "parser_error_count": len(parser.last_errors),
    }
    candidate = DomainAwareRetrieverV21()
    for variant in variants:
        if variant == "v1":
            audit = build_raw_retrieval_audit(
                **common, retriever=KeywordDocumentRetriever(), configured_retriever_name="keyword_production_v1"
            )
        elif variant == "v2":
            audit = build_v2_retrieval_audit(**common)
        else:
            name = "domain_aware_v21_candidate" if variant == "v21" else variant
            audit = build_candidate_audit(
                **common, name=name,
                retrieve=(
                    (lambda current, risk, limit: candidate.retrieve_for_risk(current, risk, limit=limit))
                    if variant == "v21" else
                    (lambda current, risk, limit, selected=variant: candidate.retrieve_ablation(current, risk, variant=selected, limit=limit))
                ),
            )
        write_raw_retrieval_outputs(audit, args.output_root / variant / case_id)
    provenance: list[dict[str, Any]] = []
    for risk_code in sorted({risk.risk_code for risk in bundle.risks}):
        for rank, evidence in enumerate(candidate.retrieve_for_risk(chunks, risk_code, limit=20), 1):
            metadata = evidence.metadata
            provenance.append({
                "case_id": case_id, "risk_code": risk_code, "domain": metadata["domain"],
                "page": evidence.page, "rank": rank, "candidate_tier": metadata["candidate_tier"],
                "query_multiplicity": metadata["query_multiplicity"],
                "query_family_multiplicity": metadata["query_family_multiplicity"],
                "is_direct": metadata["is_direct"], "is_neighbor_only": metadata["is_neighbor_only"],
                "is_round2_only": metadata["is_round2_only"], "is_boilerplate": metadata["is_boilerplate"],
                "v1_candidate_universe_missing_pages": metadata["v1_candidate_universe_missing_pages"],
            })
    _write_json(args.output_root / "provenance" / f"{case_id}.json", provenance)


def _audits(root: Path, variant: str, cases: tuple[str, ...]) -> list[Any]:
    return load_audits(root / variant, cases)


def _summarize(args: argparse.Namespace, cases: tuple[str, ...], label: str, variants: tuple[str, ...]) -> dict[str, Any]:
    summaries = {variant: extended_metrics(_audits(args.output_root, variant, cases)) for variant in variants}
    output: dict[str, Any] = {"split": label, "cases": list(cases), "variants": summaries}
    if all(variant in variants for variant in ("v1", "v2", "v21")):
        output["rank_diagnostics"] = rank_matrix(
            _audits(args.output_root, "v1", cases),
            _audits(args.output_root, "v2", cases),
            _audits(args.output_root, "v21", cases),
        )
        provenance = []
        for case_id in cases:
            provenance.extend(json.loads((args.output_root / "provenance" / f"{case_id}.json").read_text(encoding="utf-8")))
        output["provenance_diagnostics"] = provenance_diagnostics(provenance)
    _write_json(args.output_root / f"{label}_summary.json", output)
    return output


def _manifest_path(args: argparse.Namespace) -> Path:
    return args.output_root / "v21_freeze_manifest.json"


def _verify_freeze(args: argparse.Namespace) -> dict[str, Any]:
    manifest = json.loads(_manifest_path(args).read_text(encoding="utf-8"))
    stored = manifest.pop("freeze_manifest_sha256")
    if stored != _json_hash(manifest):
        raise ValueError("V21_FREEZE_MANIFEST_CHANGED")
    expected = {**_source_hashes(), **policy_hashes()}
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"V21_CHANGED_AFTER_FREEZE:{key}")
    manifest["freeze_manifest_sha256"] = stored
    return manifest


def _diagnose(args: argparse.Namespace) -> dict[str, Any]:
    for case_id in DEVELOPMENT_CASES:
        _run_case(case_id, args, VARIANTS)
    return _summarize(args, DEVELOPMENT_CASES, "development", VARIANTS)


def _freeze(args: argparse.Namespace) -> dict[str, Any]:
    summary_path = args.output_root / "development_summary.json"
    if not summary_path.exists():
        raise ValueError("DEVELOPMENT_DIAGNOSIS_REQUIRED")
    manifest = {
        "phase": "retriever_v21_ten_case_ranking_optimization",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "base_sha": _git_ref("origin/main"),
        "working_head": _git_head(),
        "candidate": "domain_aware_v21_candidate_not_registered",
        "annotation_source_branch": "annotation/gpt-expert-results",
        "annotation_source_sha": ANNOTATION_SOURCE_SHA,
        "development_cases": list(DEVELOPMENT_CASES),
        "historical_regression_cases": list(HISTORICAL_CASES),
        "locked_validation_cases": list(LOCKED_CASES),
        **_source_hashes(), **policy_hashes(),
        "rrf_k": 60,
        "neighbor_policy": "neighbor-only excluded from Top3 and capped at one Top5 slot",
        "round2_policy": "completeness-only tail; Top3 requires high-specificity direct evidence",
        "legal_boilerplate_policy": "deterministic demotion unless transaction/status context overrides",
        "business_fallback_policy": "V1 head anchor with V2 supplemental candidates",
        "head_guard_policy": "lexicographic tiers before family-capped RRF",
        "query_changed_from_v2": False,
        "generic_development_correction_count": 0,
        "locked_validation_gold_loaded": False,
        "locked_validation_run": False,
        "blind_2025_accessed": False,
        "production_default_changed": False,
    }
    manifest["freeze_manifest_sha256"] = _json_hash(manifest)
    _write_json(_manifest_path(args), manifest)
    return manifest


def _historical(args: argparse.Namespace) -> dict[str, Any]:
    freeze = _verify_freeze(args)
    for case_id in HISTORICAL_CASES:
        _run_case(case_id, args, ("v1", "v2", "v21"))
    return {"freeze": freeze, "summary": _summarize(args, HISTORICAL_CASES, "historical", ("v1", "v2", "v21"))}


def _locked(args: argparse.Namespace) -> dict[str, Any]:
    for case_id in LOCKED_CASES:
        _verify_freeze(args)
        _run_case(case_id, args, ("v1", "v2", "v21"))
    return {"freeze": _verify_freeze(args), "summary": _summarize(args, LOCKED_CASES, "locked", ("v1", "v2", "v21"))}


def _aggregate(args: argparse.Namespace) -> dict[str, Any]:
    freeze = _verify_freeze(args)
    return {"freeze": freeze, "summary": _summarize(args, ALL_CASES, "ten_case", ("v1", "v2", "v21"))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("diagnose", "freeze", "historical", "locked", "aggregate"), required=True)
    parser.add_argument("--pdf-root", type=Path, action="append", default=[])
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog/ipo_prospectus_manifest.csv"))
    parser.add_argument("--output-root", type=Path, default=Path("reports/retriever_v21_ten_case"))
    args = parser.parse_args()
    if args.stage in {"diagnose", "historical", "locked"} and not args.pdf_root:
        parser.error("--pdf-root is required for stages that parse PDFs")
    try:
        result = {
            "diagnose": _diagnose, "freeze": _freeze, "historical": _historical,
            "locked": _locked, "aggregate": _aggregate,
        }[args.stage](args)
    except (FileNotFoundError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"completed": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"completed": True, "stage": args.stage, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
