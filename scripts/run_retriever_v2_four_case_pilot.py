"""Run the frozen four-case V1/V2 Retriever pilot without downstream components."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess

from ipo_risk.evaluation.expert_annotation import ExpertAnnotationBundle
from ipo_risk.evaluation.raw_retrieval_audit import build_raw_retrieval_audit, write_raw_retrieval_outputs
from ipo_risk.evaluation.retriever_v2_pilot import (
    build_v2_retrieval_audit,
    compare_audits,
    load_audits,
)
from ipo_risk.parsers.pymupdf_parser import PyMuPDFDocumentParser
from ipo_risk.retrieval.domain_aware_v2 import query_plan_sha256
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.schemas import DocumentParseRequest


DEVELOPMENT_CASES = ("ipo_2020_00368", "ipo_2020_01167", "ipo_2020_01408")
HOLDOUT_CASES = ("ipo_2020_01961",)
ALL_CASES = (*DEVELOPMENT_CASES, *HOLDOUT_CASES)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _catalog(catalog: Path) -> dict[str, dict[str, str]]:
    with catalog.open(encoding="utf-8-sig", newline="") as handle:
        return {row["case_id"]: row for row in csv.DictReader(handle)}


def _resolve_pdf(row: dict[str, str], roots: list[Path]) -> Path:
    matches: list[Path] = []
    for root in roots:
        matches.extend(root.rglob(row["source_filename"]))
    for path in sorted(set(item.resolve() for item in matches), key=lambda item: str(item).lower()):
        if path.is_file() and _sha256(path) == row["sha256"]:
            return path
    raise FileNotFoundError(f"SOURCE_PDF_NOT_FOUND:{row['case_id']}")


def _source_hash() -> str:
    return _sha256(Path("src/ipo_risk/retrieval/domain_aware_v2.py"))


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()


def _run_case(
    case_id: str,
    *,
    rows: dict[str, dict[str, str]],
    pdf_roots: list[Path],
    output_root: Path,
) -> None:
    row = rows[case_id]
    annotation_path = Path("expert_results") / case_id / "pass1" / "expert_annotation_v1.json"
    annotation_text = annotation_path.read_text(encoding="utf-8")
    bundle = ExpertAnnotationBundle.model_validate_json(annotation_text)
    if bundle.case_id != case_id or bundle.stock_code != row["stock_code_wind"]:
        raise ValueError(f"annotation identity mismatch: {case_id}")
    pdf_path = _resolve_pdf(row, pdf_roots)
    parser = PyMuPDFDocumentParser()
    chunks = parser.parse(DocumentParseRequest(document_id=case_id, prospectus_path=str(pdf_path)))
    common = {
        "bundle": bundle,
        "chunks": chunks,
        "annotation_sha256": hashlib.sha256(annotation_text.encode("utf-8")).hexdigest(),
        "pdf_sha256": row["sha256"],
        "pdf_page_count": int(row["pdf_page_count"]),
        "parser_error_count": len(parser.last_errors),
    }
    v1 = build_raw_retrieval_audit(
        **common,
        retriever=KeywordDocumentRetriever(),
        configured_retriever_name="keyword_production_v1",
    )
    v2 = build_v2_retrieval_audit(**common)
    write_raw_retrieval_outputs(v1, output_root / "v1" / case_id)
    write_raw_retrieval_outputs(v2, output_root / "v2" / case_id)


def _write_comparison(output_root: Path, cases: tuple[str, ...], name: str) -> Path:
    comparison = compare_audits(
        load_audits(output_root / "v1", cases),
        load_audits(output_root / "v2", cases),
    )
    path = output_root / f"{name}_comparison.json"
    path.write_text(comparison.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def _development(args: argparse.Namespace) -> dict[str, object]:
    rows = _catalog(args.catalog)
    for case_id in DEVELOPMENT_CASES:
        _run_case(case_id, rows=rows, pdf_roots=args.pdf_root, output_root=args.output_root)
    comparison_path = _write_comparison(args.output_root, DEVELOPMENT_CASES, "development")
    freeze = {
        "candidate": "domain_aware_v2_candidate",
        "source_sha256": _source_hash(),
        "query_plan_sha256": query_plan_sha256(),
        "development_cases": list(DEVELOPMENT_CASES),
        "holdout_cases": list(HOLDOUT_CASES),
        "holdout_gold_opened": False,
        "working_head_before_freeze": _git_head(),
        "blind_2025_accessed": False,
    }
    freeze_path = args.output_root / "v2_freeze_manifest.json"
    freeze_path.write_text(json.dumps(freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"stage": "development", "comparison": str(comparison_path), "freeze": freeze}


def _holdout(args: argparse.Namespace) -> dict[str, object]:
    freeze_path = args.output_root / "v2_freeze_manifest.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze["source_sha256"] != _source_hash() or freeze["query_plan_sha256"] != query_plan_sha256():
        raise ValueError("V2_CHANGED_AFTER_FREEZE")
    rows = _catalog(args.catalog)
    for case_id in HOLDOUT_CASES:
        _run_case(case_id, rows=rows, pdf_roots=args.pdf_root, output_root=args.output_root)
    comparison_path = _write_comparison(args.output_root, HOLDOUT_CASES, "holdout")
    return {
        "stage": "holdout",
        "comparison": str(comparison_path),
        "frozen_source_sha256": freeze["source_sha256"],
        "frozen_query_plan_sha256": freeze["query_plan_sha256"],
        "blind_2025_accessed": False,
    }


def _all(args: argparse.Namespace) -> dict[str, object]:
    path = _write_comparison(args.output_root, ALL_CASES, "four_case")
    comparison = json.loads(path.read_text(encoding="utf-8"))
    return {
        "stage": "aggregate",
        "comparison": str(path),
        "v2_beats_v1": comparison["v2_beats_v1"],
        "degradation_flags": comparison["degradation_flags"],
        "blind_2025_accessed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("development", "holdout", "aggregate"), required=True)
    parser.add_argument("--pdf-root", type=Path, action="append", default=[])
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog/ipo_prospectus_manifest.csv"))
    parser.add_argument("--output-root", type=Path, default=Path("reports/retriever_v2_four_case_pilot"))
    args = parser.parse_args()
    if args.stage in {"development", "holdout"} and not args.pdf_root:
        parser.error("--pdf-root is required for development/holdout")
    try:
        result = {"development": _development, "holdout": _holdout, "aggregate": _all}[args.stage](args)
    except (FileNotFoundError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"completed": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"completed": True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
