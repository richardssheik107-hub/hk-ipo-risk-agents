"""Run Phase 0.6C in firewall-separated prepare, judge and evaluate stages."""

from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

from ipo_risk.parsers.pymupdf_parser import PyMuPDFDocumentParser
from ipo_risk.providers.llm import LLMProviderError, OpenAIResponsesLLMProvider
from ipo_risk.retrieval.llm_reranker import build_candidate_pool, judge_pool, pool_sha256, rerank
from ipo_risk.retrieval.llm_reranker_prompts import PROMPT_VERSION, RISK_FACETS
from ipo_risk.retrieval.llm_reranker_schemas import CandidateEvidenceView, LLMCandidateJudgmentBundle
from ipo_risk.schemas import DocumentParseRequest

CASES = ("ipo_2020_00368", "ipo_2020_01167", "ipo_2020_01408", "ipo_2020_01961", "ipo_2020_01942", "ipo_2020_02057", "ipo_2020_02135", "ipo_2020_02263", "ipo_2020_02599", "ipo_2020_00013")
OUT = Path("reports/llm_reranker_pilot")


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _source_hash(path: Path) -> str:
    return _hash(path)


def _pdf_map(roots: list[Path]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for root in roots:
        for path in root.rglob("*.pdf"):
            digits = path.name[:5]
            if digits.isdigit(): result[f"ipo_2020_{digits}"] = path
    return result


def prepare(roots: list[Path]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pdfs = _pdf_map(roots); missing = sorted(set(CASES) - pdfs.keys())
    if missing: raise SystemExit(f"missing PDFs: {missing}")
    parser = PyMuPDFDocumentParser(); candidate_hashes = {}; records = []
    for case in CASES:
        chunks = parser.parse(DocumentParseRequest(document_id=case, prospectus_path=str(pdfs[case])))
        for risk in RISK_FACETS:
            pool = build_candidate_pool(chunks, risk); candidate_hashes[f"{case}:{risk}"] = pool_sha256(pool)
            records.append({"case_id": case, "risk_code": risk, "candidates": [x.model_dump(mode="json") for x in pool]})
    candidates = OUT / "candidate_pools.json"; candidates.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files = [Path("src/ipo_risk/retrieval/llm_reranker.py"), Path("src/ipo_risk/retrieval/llm_reranker_schemas.py"), Path("src/ipo_risk/retrieval/llm_reranker_prompts.py"), Path("src/ipo_risk/providers/llm.py"), Path("src/ipo_risk/providers/prompt_registry.py")]
    manifest = {"phase": "0.6C", "freeze_revision": 2, "supersedes_revision": 1, "revision_1_result": "no_valid_judgment_structured_validation_failure", "prompt_version": PROMPT_VERSION, "model": os.getenv("IPO_RISK_LLM_MODEL", ""), "provider": "openai_responses", "temperature": "not_exposed_by_responses_adapter", "candidate_sha256": _hash(candidates), "candidate_pool_hashes": candidate_hashes, "source_hashes": {str(p): _source_hash(p) for p in files}, "gold_loaded": False, "blind_2025_accessed": False, "agent_used": False, "verifier_used": False}
    (OUT / "llm_reranker_freeze_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"prepared={len(records)} gold_loaded=false freeze={OUT / 'llm_reranker_freeze_manifest.json'}")


def judge() -> None:
    manifest_path = OUT / "llm_reranker_freeze_manifest.json"; candidates_path = OUT / "candidate_pools.json"
    manifest = json.loads(manifest_path.read_text());
    if _hash(candidates_path) != manifest["candidate_sha256"]: raise SystemExit("candidate freeze mismatch")
    key = os.getenv("IPO_RISK_LLM_API_KEY", ""); base = os.getenv("IPO_RISK_LLM_BASE_URL", ""); model = os.getenv("IPO_RISK_LLM_MODEL", "")
    if not all((key, base, model)): raise SystemExit("credentials unavailable")
    provider = OpenAIResponsesLLMProvider(api_key=key, base_url=base, model=model, timeout_seconds=int(os.getenv("IPO_RISK_LLM_TIMEOUT_SECONDS", "300")), max_retries=1)
    cache_dir = OUT / "judgments"; cache_dir.mkdir(exist_ok=True)
    rows = json.loads(candidates_path.read_text(encoding="utf-8"))
    for index, row in enumerate(rows, 1):
        pool = [CandidateEvidenceView.model_validate(x) for x in row["candidates"]]; path = cache_dir / f"{row['case_id']}__{row['risk_code']}.json"
        if path.exists(): continue
        try:
            bundle = judge_pool(provider, pool, row["risk_code"])
            rerank(pool, bundle, row["risk_code"])
            payload = {"status": "completed", "bundle": bundle.model_dump(mode="json")}
        except (LLMProviderError, ValueError) as exc:
            payload = {"status": "failed", "failure_kind": getattr(getattr(exc, "kind", None), "value", "validation"), "fallback": "stage1_union_order"}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"judged={index}/{len(rows)} status={payload['status']} case={row['case_id']} risk={row['risk_code']}")
    output_hashes = {p.name: _hash(p) for p in sorted(cache_dir.glob("*.json"))}
    if len(output_hashes) != len(rows): raise SystemExit("LLM output incomplete")
    (OUT / "llm_output_freeze.json").write_text(json.dumps({"model": model, "prompt_version": PROMPT_VERSION, "judgment_hashes": output_hashes, "gold_loaded": False}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"llm_outputs_frozen={len(output_hashes)}")


def refreeze() -> None:
    candidates = OUT / "candidate_pools.json"
    rows = json.loads(candidates.read_text(encoding="utf-8"))
    candidate_hashes = {f"{row['case_id']}:{row['risk_code']}": pool_sha256([CandidateEvidenceView.model_validate(x) for x in row["candidates"]]) for row in rows}
    files = [Path("src/ipo_risk/retrieval/llm_reranker.py"), Path("src/ipo_risk/retrieval/llm_reranker_schemas.py"), Path("src/ipo_risk/retrieval/llm_reranker_prompts.py"), Path("src/ipo_risk/providers/llm.py"), Path("src/ipo_risk/providers/prompt_registry.py")]
    manifest = {"phase": "0.6C", "freeze_revision": 4, "supersedes_revision": 3, "revision_history": ["r1_chat_structured_validation_failure_no_output", "r2_responses_timeout_60s_no_output", "r3_two_valid_outputs_then_one_validation_failure_outputs_discarded"], "prompt_version": PROMPT_VERSION, "model": os.getenv("IPO_RISK_LLM_MODEL", ""), "provider": "openai_responses", "timeout_seconds": int(os.getenv("IPO_RISK_LLM_TIMEOUT_SECONDS", "300")), "max_retries": 1, "failure_policy": "structured_failure_record_then_stage1_fallback", "temperature": "not_exposed_by_responses_adapter", "candidate_sha256": _hash(candidates), "candidate_pool_hashes": candidate_hashes, "source_hashes": {str(p): _source_hash(p) for p in files}, "gold_loaded": False, "blind_2025_accessed": False, "agent_used": False, "verifier_used": False}
    (OUT / "llm_reranker_freeze_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("refrozen=revision_2 gold_loaded=false")


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("stage", choices=("prepare", "refreeze", "judge")); parser.add_argument("--pdf-root", action="append", type=Path, default=[]); args = parser.parse_args()
    if args.stage == "prepare": prepare(args.pdf_root)
    elif args.stage == "refreeze": refreeze()
    else: judge()


if __name__ == "__main__": main()
