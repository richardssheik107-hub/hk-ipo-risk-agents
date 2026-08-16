"""One-shot frozen Retriever V3 evaluation on the ten locked IPO cases."""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from dataclasses import asdict
import gc
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
import zipfile

ROOT = Path(__file__).resolve().parents[1]
for value in (ROOT, ROOT / "src"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import lightgbm as lgb
import numpy as np

from ipo_risk.evaluation.retriever_v3 import resolve_qrels
from ipo_risk.parsers.pymupdf_parser import PyMuPDFDocumentParser
from ipo_risk.ranking.ltr_v3 import (
    FEATURE_VARIANTS, build_feature_rows, completion_at, evidence_recall, mrr_ndcg, rank_scores,
)
from ipo_risk.retrieval.bm25_v3 import BM25Config, PageBM25Index
from ipo_risk.retrieval.table_v3 import TABLE_VARIANTS, TableCandidateIndex
from ipo_risk.schemas import DocumentParseRequest
from scripts.run_retriever_v3_phase_a import (
    OUTER_ZIP_DEFAULT, _annual_member, _copy_member, _pdf_member, _read_catalog, _retrieve, _sha256,
)
from scripts.run_retriever_v3_phase_b_bm25 import _load_split
from scripts.run_retriever_v3_phase_d_ltr import _metric_bundle, _structure


BM25_B = BM25Config("BM25-B", "cjk_bigram", 1.5, .75, top_k=100)
TABLE_C = TABLE_VARIANTS[2]
LANES = ("v1", "v2", "v21", "bm25", "table")
OLD_LANES = ("v1", "v2", "v21")
FEATURES = FEATURE_VARIANTS["LTR-C"]
CAP = 100
PROTOCOL_NAME = "RETRIEVER_V3_PHASE_E_LOCKED_PROTOCOL.json"
PROTOCOL_HASH_NAME = "RETRIEVER_V3_PHASE_E_LOCKED_PROTOCOL.sha256"

FROZEN_FILES = (
    "src/ipo_risk/evaluation/retrieval_40_benchmark.py",
    "src/ipo_risk/retrieval/keyword.py",
    "src/ipo_risk/retrieval/domain_aware_v2.py",
    "src/ipo_risk/retrieval/domain_aware_v21.py",
    "src/ipo_risk/retrieval/bm25_v3.py",
    "src/ipo_risk/retrieval/table_v3.py",
    "src/ipo_risk/ranking/ltr_v3.py",
    "src/ipo_risk/parsers/pymupdf_parser.py",
    "models/retriever_v3/ltr_v3.txt",
    "reports/retriever_v3/split_manifest.json",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare_protocol(output: Path) -> dict:
    """Write the immutable preregistration without opening locked annotations."""
    output.mkdir(parents=True, exist_ok=True)
    protocol_path, hash_path = output / PROTOCOL_NAME, output / PROTOCOL_HASH_NAME
    if protocol_path.exists() or hash_path.exists():
        raise FileExistsError("LOCKED_PROTOCOL_ALREADY_EXISTS")
    missing = [name for name in FROZEN_FILES if not (ROOT / name).is_file()]
    if missing:
        raise FileNotFoundError(f"FROZEN_FILES_MISSING:{missing}")
    split = json.loads((ROOT / "reports/retriever_v3/split_manifest.json").read_text(encoding="utf-8"))
    if len(split["locked_validation"]) != 10 or split.get("locked_metrics_opened") is not False:
        raise ValueError("LOCKED_SPLIT_NOT_PRISTINE")
    payload = {
        "protocol_version": "retriever_v3_phase_e_locked_v1",
        "evaluation_timestamp": utc_now(),
        "protocol_frozen": True,
        "locked_metrics_opened": False,
        "split_manifest_hash": file_sha256(ROOT / "reports/retriever_v3/split_manifest.json"),
        "candidate_sources": ["V1", "V2", "V2.1", "BM25-B", "TABLE-C"],
        "bm25_config": {"tokenizer": "cjk_bigram", "k1": 1.5, "b": .75, "top_k": 100},
        "table_config": {"variant": TABLE_C.name, "description": "table-block multi-hit aggregation", "top_k": 50},
        "ltr_variant": "LTR-C",
        "ltr_model_path": "models/retriever_v3/ltr_v3.txt",
        "ltr_model_sha256": file_sha256(ROOT / "models/retriever_v3/ltr_v3.txt"),
        "feature_schema": list(FEATURES),
        "candidate_cap": CAP,
        "fusion_baseline": {"method": "equal-weight RRF", "rrf_k": 60},
        "primary_ranking_metrics": ["required_recall_at_5", "required_recall_at_10", "required_recall_at_20",
                                    "required_completion_at_5", "required_completion_at_20"],
        "secondary_metrics": ["recall_at_50", "recall_at_100", "mrr", "ndcg_at_5", "ndcg_at_10", "ndcg_at_20"],
        "candidate_metrics": ["old_v1_v2_v21_oracle", "bm25_standalone", "old_plus_bm25_oracle", "full_v3_oracle"],
        "predeclared_risk_watch": ["customer_concentration"],
        "pass_gates": {
            "A_candidate_generalization": "full_oracle_gain_at_50 >= 0.05 OR full_oracle_gain_at_native >= 0.05",
            "B_ltr_r20": "delta_r20 > 0 AND (delta_r20 >= 0.02 OR net_gold_at_20 >= 2)",
            "C_top5": "ltr_r5 >= rrf_r5",
            "D_completion": "ltr_completion_at_20 >= rrf_completion_at_20",
            "E_case_direction": "improved_cases >= regressed_cases",
            "F_per_risk": "at most one risk has r20 delta < -0.05; customer_concentration is always reported",
        },
        "outcome_policy": {
            "CANDIDATE_FAIL": "Gate A fails",
            "CANDIDATE_PASS_RANKING_FAIL": "Gate A passes but Gate B or D fails",
            "CANDIDATE_PASS_RANKING_MIXED": "A/B/D pass but C/E/F is not fully satisfied",
            "FULL_PASS": "all frozen gates pass",
        },
        "frozen_state": {"candidate_sources": True, "bm25_config": True, "table_config": True,
                         "ltr_features": True, "ltr_model": True, "evaluation_gates": True},
        "code_sha256": {name: file_sha256(ROOT / name) for name in FROZEN_FILES},
    }
    protocol_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    protocol_hash = file_sha256(protocol_path)
    hash_path.write_text(f"{protocol_hash}  {PROTOCOL_NAME}\n", encoding="ascii")
    return {"protocol_frozen": True, "protocol_sha256": protocol_hash, "locked_metrics_opened": False}


def verify_protocol(output: Path) -> tuple[dict, str]:
    protocol_path, hash_path = output / PROTOCOL_NAME, output / PROTOCOL_HASH_NAME
    expected = hash_path.read_text(encoding="ascii").split()[0]
    actual = file_sha256(protocol_path)
    if expected != actual:
        raise ValueError("LOCKED_PROTOCOL_HASH_MISMATCH")
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    for name, expected_hash in protocol["code_sha256"].items():
        if file_sha256(ROOT / name) != expected_hash:
            raise ValueError(f"FROZEN_FILE_CHANGED:{name}")
    return protocol, actual


def load_case_qrels(case: str) -> list[dict]:
    annotation = ROOT / "expert_results" / case / "pass1" / "expert_annotation_v1.json"
    rows = [asdict(row) for row in resolve_qrels(annotation, repository_root=ROOT)]
    return rows


def required_rows(qrels: list[dict]) -> list[dict]:
    return [row for row in qrels if row["requirement"] == "required"]


def case_features(case: str, chunks, qrels: list[dict]) -> tuple[dict, dict]:
    risks = sorted({row["risk_code"] for row in qrels})
    old = _retrieve(chunks, risks)
    bm25, table = PageBM25Index(chunks, BM25_B), TableCandidateIndex(chunks, TABLE_C)
    page_text = {chunk.page: chunk.text for chunk in chunks if chunk.page is not None}
    judgements: dict[str, dict[int, int]] = defaultdict(dict)
    for row in qrels:
        risk, page, label = row["risk_code"], int(row["page"]), int(row["gold_label"])
        judgements[risk][page] = max(label, judgements[risk].get(page, -1))
    rows_by_query, lane_pages = {}, {}
    for risk in risks:
        lane_rankings = {
            lane: [(item.page, item.relevance_score, None) for item in old[lane].get(risk, [])]
            for lane in OLD_LANES
        }
        bm = bm25.search(risk, top_k=100)
        tb = table.search(risk, top_k=50)
        lane_rankings["bm25"] = [(item.page, item.score, None) for item in bm]
        lane_rankings["table"] = [(item.page, item.score, {
            "table_block_hit_count": item.table_block_hit_count,
            "heuristic_table_signal": item.heuristic_table_signal,
        }) for item in tb]
        union = {page for values in lane_rankings.values() for page, _, _ in values}
        structures = {page: _structure(page_text.get(page, "")) for page in union}
        rows_by_query[(case, risk)] = build_feature_rows(
            case_id=case, risk_code=risk, fold=0, lane_rankings=lane_rankings,
            page_structures=structures, judgements=judgements[risk],
        )
        lane_pages[(case, risk)] = {lane: [page for page, _, _ in lane_rankings[lane]] for lane in LANES}
    return rows_by_query, lane_pages


def predict_case(model: lgb.Booster, rows_by_query: dict) -> tuple[dict, dict, dict]:
    rrf, ltr, scores = {}, {}, {}
    for key, rows in rows_by_query.items():
        for row in rows:
            if row.rrf_rank <= CAP:
                rrf[(key[0], key[1], row.page)] = row.rrf_rank
        matrix = np.asarray([[row.features[name] for name in FEATURES] for row in rows], dtype=np.float32)
        prediction = model.predict(matrix)
        ranked = rank_scores(rows, prediction, cap=CAP)
        ltr.update({(key[0], key[1], page): rank for page, rank in ranked.items()})
        scores.update({(key[0], key[1], row.page): float(score) for row, score in zip(rows, prediction)})
    return rrf, ltr, scores


def source_oracles(required: list[dict], lane_pages: dict) -> dict:
    groups = {"old": OLD_LANES, "plus_bm25": (*OLD_LANES, "bm25"), "full": LANES}
    result = {}
    for name, lanes in groups.items():
        result[name] = {}
        for cutoff in (20, 50, 100):
            hits = 0
            for row in required:
                pages = lane_pages[(row["case_id"], row["risk_code"])]
                hits += any(int(row["page"]) in pages[lane][:cutoff] for lane in lanes)
            result[name][f"at_{cutoff}"] = hits / len(required) if required else 0.0
        hits = sum(any(int(row["page"]) in lane_pages[(row["case_id"], row["risk_code"])][lane] for lane in lanes)
                   for row in required)
        result[name]["native"] = hits / len(required) if required else 0.0
    return result


def aggregate(required: list[dict], rows_by_query: dict, lane_pages: dict, rrf: dict, ltr: dict) -> dict:
    metrics = {"RRF": _metric_bundle(required, rows_by_query, rrf), "LTR-C": _metric_bundle(required, rows_by_query, ltr)}
    oracles = source_oracles(required, lane_pages)
    per_risk = {}
    for risk in sorted({row["risk_code"] for row in required}):
        subset = [row for row in required if row["risk_code"] == risk]
        groups = len({(row["case_id"], row["risk_code"]) for row in subset})
        per_risk[risk] = {"gold": len(subset), "case_risk_groups": groups,
            "rrf_r5": evidence_recall(subset, rrf, 5), "ltr_r5": evidence_recall(subset, ltr, 5),
            "rrf_r20": evidence_recall(subset, rrf, 20), "ltr_r20": evidence_recall(subset, ltr, 20),
            "rrf_completion_at_5": completion_at(subset, rrf, 5), "ltr_completion_at_5": completion_at(subset, ltr, 5),
            "rrf_completion_at_20": completion_at(subset, rrf, 20), "ltr_completion_at_20": completion_at(subset, ltr, 20)}
    case_metrics = []
    for case in sorted({row["case_id"] for row in required}):
        subset = [row for row in required if row["case_id"] == case]
        base, new = evidence_recall(subset, rrf, 20), evidence_recall(subset, ltr, 20)
        case_metrics.append({"case_id": case, "gold": len(subset), "rrf_r20": base, "ltr_r20": new, "delta": new-base})
    required_keys = [(row["case_id"], row["risk_code"], int(row["page"])) for row in required]
    movement = {}
    for k in (5, 20):
        old = {key for key in required_keys if rrf.get(key, 999) <= k}
        new = {key for key in required_keys if ltr.get(key, 999) <= k}
        movement[f"promoted_at_{k}"] = len(new-old); movement[f"lost_at_{k}"] = len(old-new); movement[f"net_at_{k}"] = len(new)-len(old)
    old_missing = [row for row in required if not any(int(row["page"]) in lane_pages[(row["case_id"], row["risk_code"])][lane] for lane in OLD_LANES)]
    full_missing = [row for row in required if not any(int(row["page"]) in lane_pages[(row["case_id"], row["risk_code"])][lane] for lane in LANES)]
    bm25_unique = sum(int(row["page"]) in lane_pages[(row["case_id"], row["risk_code"])]["bm25"] for row in old_missing)
    table_unique = sum(int(row["page"]) in lane_pages[(row["case_id"], row["risk_code"])]["table"] and
                       int(row["page"]) not in lane_pages[(row["case_id"], row["risk_code"])]["bm25"] for row in old_missing)
    improved = sum(row["delta"] > 1e-12 for row in case_metrics); regressed = sum(row["delta"] < -1e-12 for row in case_metrics)
    serious = [risk for risk, row in per_risk.items() if row["ltr_r20"] - row["rrf_r20"] < -.05]
    gain50 = oracles["full"]["at_50"] - oracles["old"]["at_50"]
    gain_native = oracles["full"]["native"] - oracles["old"]["native"]
    delta20 = metrics["LTR-C"]["r20"] - metrics["RRF"]["r20"]
    gates = {
        "A_candidate_generalization": gain50 >= .05 or gain_native >= .05,
        "B_ltr_r20": delta20 > 0 and (delta20 >= .02 or movement["net_at_20"] >= 2),
        "C_top5": metrics["LTR-C"]["r5"] >= metrics["RRF"]["r5"],
        "D_completion": metrics["LTR-C"]["completion_at_20"] >= metrics["RRF"]["completion_at_20"],
        "E_case_direction": improved >= regressed,
        "F_per_risk": len(serious) <= 1,
    }
    if not gates["A_candidate_generalization"]: outcome = "CANDIDATE_FAIL"
    elif not gates["B_ltr_r20"] or not gates["D_completion"]: outcome = "CANDIDATE_PASS_RANKING_FAIL"
    elif not all(gates.values()): outcome = "CANDIDATE_PASS_RANKING_MIXED"
    else: outcome = "FULL_PASS"
    return {"outcome": outcome, "metrics": metrics, "oracles": oracles, "per_risk": per_risk,
            "case_metrics": case_metrics, "movement": movement, "gates": gates, "serious_regressions": serious,
            "candidate_recovery": {"old_complete_misses": len(old_missing), "full_complete_misses": len(full_missing),
                                   "bm25_unique_recovery": bm25_unique, "table_unique_recovery": table_unique}}


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        if rows: writer.writeheader(); writer.writerows(rows)


def report(summary: dict) -> str:
    p = lambda value: f"{value:.2%}"
    m, o, watch = summary["metrics"], summary["oracles"], summary["per_risk"].get("customer_concentration", {})
    lines = ["# Retriever V3 Phase E — Final Locked Validation", "", "PHASE R3-E FINAL LOCKED RESULT:", "", summary["outcome"], "",
      f"Locked cases: {summary['locked_cases']}", f"Locked Gold: {summary['locked_gold']}", "",
      "## Candidate generalization", "", "| Candidate Sources | Oracle@20 | Oracle@50 | Oracle@100/native |", "|---|---:|---:|---:|",
      f"| V1∪V2∪V2.1 | {p(o['old']['at_20'])} | {p(o['old']['at_50'])} | {p(o['old']['native'])} |",
      f"| + BM25 | {p(o['plus_bm25']['at_20'])} | {p(o['plus_bm25']['at_50'])} | {p(o['plus_bm25']['native'])} |",
      f"| + Table | {p(o['full']['at_20'])} | {p(o['full']['at_50'])} | {p(o['full']['native'])} |", "",
      "## Locked Final Ranking", "", "| Ranker | R@5 | R@10 | R@20 | R@50 | R@100 |", "|---|---:|---:|---:|---:|---:|",
      f"| RRF | {p(m['RRF']['r5'])} | {p(m['RRF']['r10'])} | {p(m['RRF']['r20'])} | {p(m['RRF']['r50'])} | {p(m['RRF']['r100'])} |",
      f"| Frozen LTR-C | {p(m['LTR-C']['r5'])} | {p(m['LTR-C']['r10'])} | {p(m['LTR-C']['r20'])} | {p(m['LTR-C']['r50'])} | {p(m['LTR-C']['r100'])} |", "",
      "## Completion", "", "| Ranker | Completion@5 | Completion@20 |", "|---|---:|---:|",
      f"| RRF | {p(m['RRF']['completion_at_5'])} | {p(m['RRF']['completion_at_20'])} |",
      f"| LTR-C | {p(m['LTR-C']['completion_at_5'])} | {p(m['LTR-C']['completion_at_20'])} |", "",
      "## Ranking quality", "", "| Ranker | MRR | NDCG@5 | NDCG@10 | NDCG@20 |", "|---|---:|---:|---:|---:|",
      f"| RRF | {m['RRF']['mrr']:.4f} | {m['RRF']['ndcg_at_5']:.4f} | {m['RRF']['ndcg_at_10']:.4f} | {m['RRF']['ndcg_at_20']:.4f} |",
      f"| LTR-C | {m['LTR-C']['mrr']:.4f} | {m['LTR-C']['ndcg_at_5']:.4f} | {m['LTR-C']['ndcg_at_10']:.4f} | {m['LTR-C']['ndcg_at_20']:.4f} |", "",
      "## PREDECLARED WATCH: customer_concentration", "",
      f"Gold count: {watch.get('gold', 0)}", f"Case-risk count: {watch.get('case_risk_groups', 0)}",
      f"RRF R@5: {p(watch.get('rrf_r5', 0))}", f"LTR R@5: {p(watch.get('ltr_r5', 0))}",
      f"RRF R@20: {p(watch.get('rrf_r20', 0))}", f"LTR R@20: {p(watch.get('ltr_r20', 0))}",
      f"Delta R@20: {p(watch.get('ltr_r20', 0)-watch.get('rrf_r20', 0))}", "",
      "## Per-risk", "", "| Risk | Gold | RRF R@5 | LTR R@5 | RRF R@20 | LTR R@20 |", "|---|---:|---:|---:|---:|---:|"]
    for risk, row in summary["per_risk"].items():
        lines.append(f"| {risk} | {row['gold']} | {p(row['rrf_r5'])} | {p(row['ltr_r5'])} | {p(row['rrf_r20'])} | {p(row['ltr_r20'])} |")
    lines += ["", "## Case-level direction", "", "| Case | RRF R@20 | LTR R@20 | Delta |", "|---|---:|---:|---:|"]
    for row in summary["case_metrics"]:
        lines.append(f"| {row['case_id']} | {p(row['rrf_r20'])} | {p(row['ltr_r20'])} | {p(row['delta'])} |")
    d = summary["disk"]
    candidate_answer = "YES" if summary["gates"]["A_candidate_generalization"] else "NO"
    ranking_answer = "YES" if summary["outcome"] == "FULL_PASS" else ("MIXED" if summary["outcome"] == "CANDIDATE_PASS_RANKING_MIXED" else "NO")
    lines += ["", "## Frozen gates", ""] + [f"- {name}: {'PASS' if value else 'FAIL'}" for name, value in summary["gates"].items()]
    lines += ["", f"Candidate generalization: **{candidate_answer}**", f"Ranking generalization: **{ranking_answer}**", "",
      "## Data governance", "", "LOCKED VALIDATION:", "", "Cases: 10", "", "Opened: YES", "", "Consumed: YES", "",
      "Used for tuning before evaluation: NO", "", "Can be reused as untouched final test: NO", "",
      "## Disk", "", f"- Available disk before: {d['before_gib']:.2f} GiB", f"- Peak temporary disk: {d['peak_mib']:.1f} MiB",
      f"- Available disk after: {d['after_gib']:.2f} GiB", "- Persistent new index: NO", "- Model downloads: NO",
      "- Temporary PDFs remaining: 0", "- Temporary year ZIP remaining: 0", "- Temporary directories: CLEAN", "",
      "## 简单结论", ""]
    if summary["outcome"] == "FULL_PASS":
        lines += ["最终考试通过。BM25 + Table 在未参与开发的10篇IPO上仍扩大了候选覆盖，冻结的LTR-C也在Top5、Top20和Completion@20上通过预注册门槛。这提供了Retriever V3真实泛化的证据。"]
    else:
        lines += ["最终考试没有完全通过。由于Locked 10已经正式打开并消费，不能再用它们调参后继续称为独立测试集；后续修改必须只使用Development并准备新的未见IPO作为最终验证。"]
    return "\n".join(lines) + "\n"


def run_dry(args) -> dict:
    protocol, protocol_hash = verify_protocol(args.output_dir)
    development, locked = _load_split(args.split_manifest)
    cases = development[:2]
    catalog = _read_catalog(args.catalog); model = lgb.Booster(model_file=str(args.model))
    groups = 0; peak = 0
    with tempfile.TemporaryDirectory(prefix=".tmp_retriever_v3_locked_dry_", dir=args.temp_parent) as temp_name:
        temp = Path(temp_name)
        with zipfile.ZipFile(args.outer_zip) as outer:
            for year in sorted({catalog[c]["source_year"] for c in cases}):
                annual_path = temp / f"{year}.zip"; _copy_member(outer, _annual_member(outer, year), annual_path)
                try:
                    with zipfile.ZipFile(annual_path) as annual:
                        for case in [c for c in cases if catalog[c]["source_year"] == year]:
                            pdf = temp / "current.pdf"; chunks = None
                            try:
                                _copy_member(annual, _pdf_member(annual, catalog[case]["source_filename"]), pdf)
                                peak = max(peak, annual_path.stat().st_size + pdf.stat().st_size)
                                chunks = PyMuPDFDocumentParser().parse(DocumentParseRequest(document_id=case, prospectus_path=str(pdf)))
                                qrels = [row for row in load_development_qrels(args.gold) if row["case_id"] == case]
                                rows, _ = case_features(case, chunks, qrels); predict_case(model, rows); groups += len(rows)
                            finally:
                                pdf.unlink(missing_ok=True); del chunks; gc.collect()
                finally: annual_path.unlink(missing_ok=True)
    return {"dry_run": True, "cases": len(cases), "query_groups": groups, "model_loaded": True,
            "protocol_sha256": protocol_hash, "locked_metrics_opened": False, "temporary_directory_removed": True,
            "peak_temporary_bytes": peak}


def load_development_qrels(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [{**row, "page": int(row["page"]), "gold_label": int(row["gold_label"])} for row in csv.DictReader(handle)]


def run_locked(args) -> dict:
    start = time.time(); output = args.output_dir.resolve(); protocol, protocol_hash = verify_protocol(output)
    development, locked = _load_split(args.split_manifest)
    if len(locked) != 10: raise ValueError("LOCKED_CASE_COUNT")
    disk_before = shutil.disk_usage(args.temp_parent).free
    marker = {"status": "RUNNING", "LOCKED_VALIDATION_CONSUMED": True, "consumed_at": utc_now(),
              "consumed_by": "Phase R3-E", "protocol_sha256": protocol_hash,
              "used_for_tuning_before_evaluation": False}
    summary_path = output / "locked_phase_e_summary.json"
    summary_path.write_text(json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    catalog = _read_catalog(args.catalog); model = lgb.Booster(model_file=str(args.model))
    required, rows_by_query, lane_pages, rrf, ltr, recovery_rows = [], {}, {}, {}, {}, []
    peak = 0
    with tempfile.TemporaryDirectory(prefix=".tmp_retriever_v3_locked_", dir=args.temp_parent) as temp_name:
        temp = Path(temp_name)
        with zipfile.ZipFile(args.outer_zip) as outer:
            for year in sorted({catalog[c]["source_year"] for c in locked}):
                annual_path = temp / f"{year}.zip"; _copy_member(outer, _annual_member(outer, year), annual_path)
                peak = max(peak, annual_path.stat().st_size)
                try:
                    with zipfile.ZipFile(annual_path) as annual:
                        year_cases = [case for case in locked if catalog[case]["source_year"] == year]
                        for index, case in enumerate(year_cases, 1):
                            if shutil.disk_usage(args.temp_parent).free < 3 * 2**30: raise OSError("DISK_SAFETY_STOP_BELOW_3_GIB")
                            pdf = temp / "current.pdf"; chunks = None
                            try:
                                _copy_member(annual, _pdf_member(annual, catalog[case]["source_filename"]), pdf)
                                peak = max(peak, annual_path.stat().st_size + pdf.stat().st_size)
                                if _sha256(pdf) != catalog[case]["sha256"]: raise ValueError(f"PDF_HASH:{case}")
                                chunks = PyMuPDFDocumentParser().parse(DocumentParseRequest(document_id=case, prospectus_path=str(pdf)))
                                qrels = load_case_qrels(case); case_required = required_rows(qrels); required.extend(case_required)
                                case_rows, case_lanes = case_features(case, chunks, qrels); case_rrf, case_ltr, _ = predict_case(model, case_rows)
                                rows_by_query.update(case_rows); lane_pages.update(case_lanes); rrf.update(case_rrf); ltr.update(case_ltr)
                                for row in case_required:
                                    key = (case, row["risk_code"]); page = int(row["page"])
                                    recovery_rows.append({"case_id": case, "risk_code": row["risk_code"], "page": page,
                                        "gold_label": row["gold_label"], "v1_present": int(page in case_lanes[key]["v1"]),
                                        "v2_present": int(page in case_lanes[key]["v2"]), "v21_present": int(page in case_lanes[key]["v21"]),
                                        "bm25_present": int(page in case_lanes[key]["bm25"]), "table_present": int(page in case_lanes[key]["table"]),
                                        "rrf_rank": case_rrf.get((case,row["risk_code"],page), ""), "ltr_rank": case_ltr.get((case,row["risk_code"],page), "")})
                                print(f"[{year} {index}/{len(year_cases)}] {case}: locked evaluation complete", flush=True)
                            finally:
                                pdf.unlink(missing_ok=True)
                                if chunks is not None: del chunks
                                gc.collect()
                finally: annual_path.unlink(missing_ok=True)
    result = aggregate(required, rows_by_query, lane_pages, rrf, ltr)
    disk_after = shutil.disk_usage(args.temp_parent).free
    summary = {**marker, "status": "COMPLETE", "outcome": result["outcome"], "locked_cases": 10,
      "locked_gold": len(required), "metrics": result["metrics"], "oracles": result["oracles"],
      "per_risk": result["per_risk"], "case_metrics": result["case_metrics"], "movement": result["movement"],
      "candidate_recovery": result["candidate_recovery"], "gates": result["gates"],
      "serious_regressions": result["serious_regressions"], "algorithm_or_config_changed_during_evaluation": False,
      "disk": {"before_bytes": disk_before, "after_bytes": disk_after, "peak_temporary_bytes": peak,
               "before_gib": disk_before/2**30, "after_gib": disk_after/2**30, "peak_mib": peak/2**20},
      "runtime_seconds": time.time()-start}
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(output / "locked_case_metrics.csv", result["case_metrics"])
    write_csv(output / "locked_risk_metrics.csv", [{"risk_code": risk, **row} for risk, row in result["per_risk"].items()])
    with gzip.open(output / "locked_recovery_metadata.csv.gz", "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(recovery_rows[0])); writer.writeheader(); writer.writerows(recovery_rows)
    (output / "RETRIEVER_V3_PHASE_E_LOCKED_REPORT.md").write_text(report(summary), encoding="utf-8")
    return {"completed": True, "outcome": summary["outcome"], "locked_consumed": True,
            "locked_gold": len(required), "protocol_sha256": protocol_hash}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-protocol", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--locked", action="store_true")
    parser.add_argument("--outer-zip", type=Path, default=OUTER_ZIP_DEFAULT)
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog/ipo_prospectus_manifest.csv"))
    parser.add_argument("--split-manifest", type=Path, default=Path("reports/retriever_v3/split_manifest.json"))
    parser.add_argument("--gold", type=Path, default=Path("reports/retriever_v3/gold_evidence.csv"))
    parser.add_argument("--model", type=Path, default=Path("models/retriever_v3/ltr_v3.txt"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/retriever_v3"))
    parser.add_argument("--temp-parent", type=Path, default=Path(".."))
    args = parser.parse_args()
    if args.prepare_protocol: result = prepare_protocol(args.output_dir.resolve())
    elif args.dry_run: result = run_dry(args)
    else: result = run_locked(args)
    print(json.dumps(result, ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
