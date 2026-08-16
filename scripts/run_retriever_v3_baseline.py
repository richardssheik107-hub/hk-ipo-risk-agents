"""Run Retriever V3 60-case preflight and frozen baseline evaluation.

Preflight needs only repository annotations/catalog metadata. The full ranking run
requires the original prospectus PDFs supplied via --pdf-root and never calls an
LLM. Locked validation metrics require an explicit --unlock-locked switch.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable

from ipo_risk.evaluation.retriever_v3_baseline import retrieve_existing_variants, write_baseline_outputs
from ipo_risk.evaluation.retriever_v3_dataset import (
    DEFAULT_EXPERT_ROOT,
    DEFAULT_SOURCE_MANIFEST,
    DEFAULT_SPLIT_PATH,
    build_retrieval_gold_rows,
    evidence_pattern_summary,
    load_source_manifest,
    load_split_manifest,
    validate_gold_against_source_manifest,
    write_preflight_outputs,
)
from ipo_risk.parsers.pymupdf_parser import PyMuPDFDocumentParser
from ipo_risk.schemas import DocumentParseRequest


DEFAULT_OUTPUT_ROOT = Path("reports/retriever_v3")


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _ranking_sha256(rankings: dict[str, object]) -> str:
    payload: list[dict[str, object]] = []
    for case_id in sorted(rankings):
        by_risk = rankings[case_id]  # type: ignore[index]
        for risk_code in sorted(by_risk):
            by_variant = by_risk[risk_code]
            for variant in sorted(by_variant):
                for item in by_variant[variant]:
                    payload.append(item.model_dump(mode="json"))
    return sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _resolve_pdfs_by_hash(*, roots: Iterable[Path], expected: dict[str, str]) -> dict[str, Path]:
    by_hash = {value.lower(): case_id for case_id, value in expected.items()}
    found: dict[str, Path] = {}
    seen_paths: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        candidates = [root] if root.is_file() and root.suffix.lower() == ".pdf" else sorted(root.rglob("*.pdf"))
        for path in candidates:
            path = path.resolve()
            if path in seen_paths:
                continue
            seen_paths.add(path)
            digest = _file_sha256(path)
            case_id = by_hash.get(digest)
            if case_id is not None and case_id not in found:
                found[case_id] = path
    return found


def preflight(*, split_path: Path, expert_root: Path, source_manifest_path: Path, output_root: Path) -> None:
    split = load_split_manifest(split_path)
    source = load_source_manifest(source_manifest_path)
    rows = build_retrieval_gold_rows(expert_root=expert_root, split_manifest=split)
    validation = validate_gold_against_source_manifest(rows, split_manifest=split, source_manifest=source)
    if not validation["valid"]:
        raise SystemExit(f"Retriever V3 preflight failed: {validation['errors']}")
    paths = write_preflight_outputs(rows=rows, split_manifest=split, validation=validation, output_dir=output_root / "preflight")
    development = [row for row in rows if row.retrieval_split == "development"]
    print(json.dumps({
        "status": "passed",
        "cases": validation["case_count"],
        "evidence": validation["evidence_count"],
        "required_evidence": validation["required_evidence_count"],
        "development_cases": split.development_case_count,
        "locked_validation_cases": split.locked_validation_case_count,
        "development_patterns": evidence_pattern_summary(development),
        "outputs": [str(path) for path in paths],
        "production_retriever_modified": False,
        "llm_used": False,
    }, ensure_ascii=False))


def run_baseline(
    *, split_name: str, unlock_locked: bool, pdf_roots: list[Path], split_path: Path,
    expert_root: Path, source_manifest_path: Path, output_root: Path,
) -> None:
    if split_name == "locked_validation" and not unlock_locked:
        raise SystemExit("locked validation requires --unlock-locked")
    split = load_split_manifest(split_path)
    source = load_source_manifest(source_manifest_path)
    case_ids = split.development_cases if split_name == "development" else split.locked_validation_cases
    expected_hashes = {case_id: source[case_id].pdf_sha256 for case_id in case_ids}
    pdfs = _resolve_pdfs_by_hash(roots=pdf_roots, expected=expected_hashes)
    missing = sorted(set(case_ids) - set(pdfs))
    if missing:
        raise SystemExit(f"missing exact prospectus PDFs by SHA-256: {missing}")

    # Freeze rankings before loading any Expert Evidence.
    parser = PyMuPDFDocumentParser()
    all_rankings: dict[str, object] = {}
    chunks_by_case: dict[str, list[object]] = {}
    parser_errors: dict[str, int] = {}
    for index, case_id in enumerate(case_ids, 1):
        chunks = parser.parse(DocumentParseRequest(document_id=case_id, prospectus_path=str(pdfs[case_id])))
        parser_errors[case_id] = len(parser.last_errors)
        chunks_by_case[case_id] = chunks
        all_rankings[case_id] = retrieve_existing_variants(chunks, case_id=case_id, depth=100)
        print(f"ranked={index}/{len(case_ids)} case={case_id} parser_errors={len(parser.last_errors)}")

    candidate_hash = _ranking_sha256(all_rankings)
    out = output_root / split_name
    out.mkdir(parents=True, exist_ok=True)
    freeze_path = out / "candidate_freeze_manifest.json"
    freeze_path.write_text(json.dumps({
        "phase": "R3-A1",
        "split": split_name,
        "split_version": split.split_version,
        "case_ids": case_ids,
        "candidate_ranking_sha256": candidate_hash,
        "candidate_depth_per_variant": 100,
        "variants": ["v1", "v2", "v21"],
        "gold_loaded_at_freeze": False,
        "llm_used": False,
        "production_retriever_modified": False,
        "pdf_identity": "validated_by_catalog_sha256",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Gold is unlocked only after the deterministic candidate freeze above.
    rows = build_retrieval_gold_rows(expert_root=expert_root, split_manifest=split)
    validation = validate_gold_against_source_manifest(rows, split_manifest=split, source_manifest=source)
    if not validation["valid"]:
        raise SystemExit(f"Gold validation failed after candidate freeze: {validation['errors']}")
    gold_rows = [row for row in rows if row.retrieval_split == split_name]

    output_paths = write_baseline_outputs(
        output_dir=out,
        all_rankings=all_rankings,  # type: ignore[arg-type]
        gold_rows=gold_rows,
        chunks_by_case=chunks_by_case,  # type: ignore[arg-type]
        split_name=split_name,
    )
    run_manifest = out / "run_manifest.json"
    run_manifest.write_text(json.dumps({
        "phase": "R3-A1", "split": split_name, "split_version": split.split_version,
        "case_count": len(case_ids), "candidate_ranking_sha256": candidate_hash,
        "gold_loaded_only_after_candidate_freeze": True,
        "locked_metrics_explicitly_unlocked": bool(unlock_locked and split_name == "locked_validation"),
        "parser_error_counts": parser_errors, "pdf_sha256_verified": True,
        "llm_used": False, "agent_used": False, "verifier_used": False,
        "production_retriever_modified": False, "outputs": [str(path) for path in output_paths],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "completed", "split": split_name, "case_count": len(case_ids),
        "candidate_ranking_sha256": candidate_hash, "parser_errors": sum(parser_errors.values()),
        "output_dir": str(out),
    }, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("preflight", "run"))
    parser.add_argument("--split", choices=("development", "locked_validation"), default="development")
    parser.add_argument("--unlock-locked", action="store_true")
    parser.add_argument("--pdf-root", action="append", type=Path, default=[])
    parser.add_argument("--split-manifest", type=Path, default=DEFAULT_SPLIT_PATH)
    parser.add_argument("--expert-root", type=Path, default=DEFAULT_EXPERT_ROOT)
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    if args.stage == "preflight":
        preflight(split_path=args.split_manifest, expert_root=args.expert_root, source_manifest_path=args.source_manifest, output_root=args.output_root)
        return
    if not args.pdf_root:
        raise SystemExit("run stage requires at least one --pdf-root")
    run_baseline(
        split_name=args.split, unlock_locked=args.unlock_locked, pdf_roots=args.pdf_root,
        split_path=args.split_manifest, expert_root=args.expert_root,
        source_manifest_path=args.source_manifest, output_root=args.output_root,
    )


if __name__ == "__main__":
    main()
