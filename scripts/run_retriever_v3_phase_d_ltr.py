"""Run Development-only 5-fold LambdaMART for Retriever V3 Phase D."""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import gc
import gzip
import json
from pathlib import Path
import re
import shutil
import statistics
import sys
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
for value in (ROOT, ROOT / "src"):
    if str(value) not in sys.path: sys.path.insert(0, str(value))

import lightgbm as lgb
import numpy as np

from ipo_risk.parsers.pymupdf_parser import PyMuPDFDocumentParser
from ipo_risk.ranking.ltr_v3 import (
    CandidateRow, FEATURE_VARIANTS, LANES, audit_feature_names, build_feature_rows, completion_at,
    evidence_recall, mrr_ndcg, rank_scores, sample_training_rows,
)
from ipo_risk.retrieval.bm25_v3 import BM25Config, PageBM25Index
from ipo_risk.retrieval.table_v3 import TABLE_VARIANTS, TableCandidateIndex, table_signal
from ipo_risk.schemas import DocumentParseRequest
from scripts.run_retriever_v3_phase_a import (
    OUTER_ZIP_DEFAULT, _annual_member, _copy_member, _pdf_member, _read_catalog, _sha256,
)
from scripts.run_retriever_v3_phase_b_bm25 import _load_old_candidates, _load_split


BM25_B = BM25Config("BM25-B", "cjk_bigram", 1.5, .75, top_k=100)
TABLE_C = TABLE_VARIANTS[2]
MODEL_PARAMS = {"objective": "lambdarank", "metric": "ndcg", "learning_rate": .05,
                "n_estimators": 250, "num_leaves": 15, "min_child_samples": 20,
                "reg_lambda": 1.0, "random_state": 20260816, "verbosity": -1,
                "force_col_wise": True, "n_jobs": 1}
FEATURE_FILE = "candidate_ltr_features.csv.gz"


def _load_fold_manifest(path: Path, development: set[str], locked: set[str]) -> dict[str, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    folds = {case: int(fold) for fold, cases in payload["folds"].items() for case in cases}
    if set(folds) != development or set(folds) & locked or sorted(Counter(folds.values()).values()) != [10] * 5:
        raise ValueError("LTR_FOLD_MANIFEST_INVALID")
    return folds


def Counter(values):
    output = defaultdict(int)
    for value in values: output[value] += 1
    return output


def _load_gold(path: Path, development: set[str], locked: set[str]) -> tuple[list[dict], dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if {row["case_id"] for row in rows} & locked or not {row["case_id"] for row in rows} <= development:
        raise ValueError("LOCKED_GOLD_LEAKAGE")
    judgements: dict[tuple[str, str], dict[int, int]] = defaultdict(dict)
    for row in rows:
        row["page"] = int(row["page"]); row["gold_label"] = int(row["gold_label"])
        key = (row["case_id"], row["risk_code"])
        judgements[key][row["page"]] = max(row["gold_label"], judgements[key].get(row["page"], -1))
    required = [row for row in rows if row["requirement"] == "required"]
    return required, judgements


def _structure(text: str) -> dict[str, float]:
    numbers = re.findall(r"(?<!\w)\d[\d,.]*%?", text)
    return {"page_text_length": len(text), "numeric_density": sum(map(len, numbers)) / max(1, len(text)),
            "percentage_count": text.count("%"),
            "currency_count": len(re.findall(r"HK\$|US\$|RMB|人民币|人民幣|港元|美元|千元|百萬|million", text, re.I)),
            "year_count": len(set(re.findall(r"(?:19|20)\d{2}", text))),
            "heuristic_table_signal": table_signal(text).score}


def _stream_features(*, cases: list[str], folds: dict[str, int], judgements: dict, old: dict,
                     catalog: dict, outer_zip: Path, temp: Path) -> tuple[list[CandidateRow], int]:
    output: list[CandidateRow] = []; peak = 0
    with zipfile.ZipFile(outer_zip) as outer:
        for year in sorted({catalog[case]["source_year"] for case in cases}):
            annual_path = temp / f"{year}.zip"; _copy_member(outer, _annual_member(outer, year), annual_path)
            peak = max(peak, annual_path.stat().st_size)
            try:
                with zipfile.ZipFile(annual_path) as annual:
                    year_cases = [case for case in cases if catalog[case]["source_year"] == year]
                    for position, case in enumerate(year_cases, 1):
                        pdf_path = temp / "current.pdf"; chunks = None
                        try:
                            _copy_member(annual, _pdf_member(annual, catalog[case]["source_filename"]), pdf_path)
                            peak = max(peak, annual_path.stat().st_size + pdf_path.stat().st_size)
                            if _sha256(pdf_path) != catalog[case]["sha256"]: raise ValueError(f"PDF_HASH:{case}")
                            chunks = PyMuPDFDocumentParser().parse(DocumentParseRequest(document_id=case, prospectus_path=str(pdf_path)))
                            page_text = {chunk.page: chunk.text for chunk in chunks if chunk.page is not None}
                            bm25 = PageBM25Index(chunks, BM25_B); table = TableCandidateIndex(chunks, TABLE_C)
                            risks = sorted(judgements_for_risk for c, judgements_for_risk in judgements if c == case)
                            for risk in risks:
                                bm = bm25.search(risk, top_k=100); tb = table.search(risk, top_k=50)
                                lane_rankings = {
                                    lane: [(page, score, None) for page, score in old[case][risk].get(lane, [])]
                                    for lane in ("v1", "v2", "v21")}
                                lane_rankings["bm25"] = [(item.page, item.score, None) for item in bm]
                                lane_rankings["table"] = [(item.page, item.score, {"table_block_hit_count": item.table_block_hit_count,
                                    "heuristic_table_signal": item.heuristic_table_signal}) for item in tb]
                                union_pages = {page for values in lane_rankings.values() for page, _, _ in values}
                                structures = {page: _structure(page_text.get(page, "")) for page in union_pages}
                                output.extend(build_feature_rows(case_id=case, risk_code=risk, fold=folds[case],
                                    lane_rankings=lane_rankings, page_structures=structures,
                                    judgements=judgements[(case, risk)]))
                            print(f"[{year} {position}/{len(year_cases)}] {case}: LTR features ok", flush=True)
                            del bm25, table, page_text
                        finally:
                            pdf_path.unlink(missing_ok=True)
                            if chunks is not None: del chunks
                            gc.collect()
            finally: annual_path.unlink(missing_ok=True)
    return output, peak


def _write_features(path: Path, rows: list[CandidateRow]) -> None:
    feature_names = FEATURE_VARIANTS["LTR-C"]
    fields = ("case_id", "risk_code", "page", "fold", "gold_label", "judgement_status", "rrf_rank", *feature_names)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for row in rows:
            writer.writerow({"case_id": row.case_id, "risk_code": row.risk_code, "page": row.page,
                             "fold": row.fold, "gold_label": row.gold_label,
                             "judgement_status": row.judgement_status, "rrf_rank": row.rrf_rank,
                             **{name: row.features[name] for name in feature_names}})


def _training_data(rows_by_query: dict, cases: set[str], names: tuple[str, ...], weak_limit: int):
    x, y, groups, sources = [], [], [], []
    for key in sorted(rows_by_query):
        if key[0] not in cases: continue
        sampled = sample_training_rows(rows_by_query[key], weak_limit=weak_limit)
        if not any(label > 0 for _, label, _ in sampled) or not any(label == 0 for _, label, _ in sampled): continue
        groups.append(len(sampled))
        for row, label, source in sampled:
            x.append([row.features[name] for name in names]); y.append(label); sources.append(source)
    return np.asarray(x, dtype=np.float32), np.asarray(y, dtype=np.int32), groups, sources


def _metric_bundle(required: list[dict], rows_by_query: dict, ranks: dict) -> dict:
    result = {f"r{k}": evidence_recall(required, ranks, k) for k in (5, 10, 20, 50, 100)}
    result["completion_at_5"] = completion_at(required, ranks, 5)
    result["completion_at_20"] = completion_at(required, ranks, 20)
    result["mrr"], ndcg = mrr_ndcg(rows_by_query, ranks)
    result.update({f"ndcg_at_{k}": value for k, value in ndcg.items()})
    return result


def _rank_from_rrf(rows_by_query: dict) -> dict:
    return {(case, risk, row.page): row.rrf_rank for (case, risk), rows in rows_by_query.items()
            for row in rows if row.rrf_rank <= 100}


def _oracle_ranks(rows_by_query: dict) -> dict:
    ranks = {}
    for (case, risk), rows in rows_by_query.items():
        positives = sorted((row for row in rows if row.gold_label > 0), key=lambda row: (-row.gold_label, row.page))
        ranks.update({(case, risk, row.page): rank for rank, row in enumerate(positives, 1) if rank <= 100})
    return ranks


def _fit_fold(rows_by_query: dict, folds: dict[str, int], fold: int, names: tuple[str, ...], weak_limit: int):
    train_cases = {case for case, value in folds.items() if value != fold}; valid_cases = {case for case, value in folds.items() if value == fold}
    x_train, y_train, g_train, sources = _training_data(rows_by_query, train_cases, names, weak_limit)
    x_valid, y_valid, g_valid, _ = _training_data(rows_by_query, valid_cases, names, weak_limit)
    model = lgb.LGBMRanker(**MODEL_PARAMS)
    model.fit(x_train, y_train, group=g_train, eval_set=[(x_valid, y_valid)], eval_group=[g_valid],
              eval_at=[5, 20], callbacks=[lgb.early_stopping(25, verbose=False)])
    ranks, scores = {}, {}
    for key in sorted(rows_by_query):
        if key[0] not in valid_cases: continue
        rows = rows_by_query[key]; prediction = model.predict(np.asarray([[row.features[name] for name in names] for row in rows], dtype=np.float32))
        page_ranks = rank_scores(rows, prediction, cap=100)
        ranks.update({(key[0], key[1], page): rank for page, rank in page_ranks.items()})
        scores.update({(key[0], key[1], row.page): float(score) for row, score in zip(rows, prediction)})
    diagnostics = {"fold": fold, "train_rows": len(y_train), "validation_rows": len(y_valid),
                   "train_groups": len(g_train), "validation_groups": len(g_valid),
                   "positive_labels": int((y_train > 0).sum()), "weak_negatives": sources.count("WEAK_UNJUDGED_ZERO"),
                   "best_iteration": int(model.best_iteration_ or MODEL_PARAMS["n_estimators"])}
    return model, ranks, scores, diagnostics


def _oof(rows_by_query: dict, folds: dict, required: list[dict], variant: str, weak_limit: int):
    names = FEATURE_VARIANTS[variant]; audit_feature_names(names)
    all_ranks, all_scores, diagnostics, importances = {}, {}, [], []
    for fold in range(1, 6):
        model, ranks, scores, diag = _fit_fold(rows_by_query, folds, fold, names, weak_limit)
        all_ranks.update(ranks); all_scores.update(scores); diagnostics.append(diag)
        importances.append(model.booster_.feature_importance(importance_type="gain")); del model
    importance = np.mean(np.asarray(importances), axis=0)
    return _metric_bundle(required, rows_by_query, all_ranks), all_ranks, all_scores, diagnostics, dict(zip(names, importance.tolist()))


def _per_risk(required: list[dict], rrf: dict, ltr: dict) -> dict:
    output = {}
    for risk in sorted({row["risk_code"] for row in required}):
        subset = [row for row in required if row["risk_code"] == risk]
        output[risk] = {"gold": len(subset), "rrf_r5": evidence_recall(subset, rrf, 5),
                        "ltr_r5": evidence_recall(subset, ltr, 5), "rrf_r20": evidence_recall(subset, rrf, 20),
                        "ltr_r20": evidence_recall(subset, ltr, 20)}
    return output


def _fold_metrics(required: list[dict], folds: dict, rrf: dict, ltr: dict) -> list[dict]:
    rows = []
    for fold in range(1, 6):
        subset = [row for row in required if folds[row["case_id"]] == fold]
        base, new = evidence_recall(subset, rrf, 20), evidence_recall(subset, ltr, 20)
        rows.append({"fold": fold, "gold": len(subset), "rrf_r20": base, "ltr_r20": new, "delta": new - base})
    return rows


def _write_oof(path: Path, rows: list[CandidateRow], rrf: dict, ranks_by_variant: dict, selected_scores: dict) -> None:
    fields = ("case_id", "risk_code", "page", "fold", "gold_label", "judgement_status", "rrf_rank",
              "ltr_a_rank", "ltr_b_rank", "ltr_c_rank", "selected_ltr_score")
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for row in rows:
            key = (row.case_id, row.risk_code, row.page)
            writer.writerow({"case_id": row.case_id, "risk_code": row.risk_code, "page": row.page, "fold": row.fold,
                "gold_label": row.gold_label, "judgement_status": row.judgement_status, "rrf_rank": rrf.get(key, ""),
                "ltr_a_rank": ranks_by_variant["LTR-A"].get(key, ""), "ltr_b_rank": ranks_by_variant["LTR-B"].get(key, ""),
                "ltr_c_rank": ranks_by_variant["LTR-C"].get(key, ""), "selected_ltr_score": selected_scores.get(key, "")})


def _report(s: dict) -> str:
    p=lambda x:f"{x:.2%}"; best=s["selected_variant"]; m=s["metrics"]
    lines=["# Retriever V3 Phase D — Learning-to-Rank", "", "PHASE R3-D RESULT:", "", s["result"], "",
      "Model:", "LightGBM LambdaMART", "", "Development:", "50 cases", "", "Validation:", "5-fold Group CV", "",
      "Locked:", "10 cases", "", "Locked metrics opened:", "NO", "", "## OOF Ranking Performance", "",
      "| Ranker | R@5 | R@10 | R@20 | R@50 | R@100 |", "|---|---:|---:|---:|---:|---:|",
      f"| Equal-weight RRF | {p(m['RRF']['r5'])} | {p(m['RRF']['r10'])} | {p(m['RRF']['r20'])} | {p(m['RRF']['r50'])} | {p(m['RRF']['r100'])} |"]
    for name in FEATURE_VARIANTS: lines.append(f"| {name} | {p(m[name]['r5'])} | {p(m[name]['r10'])} | {p(m[name]['r20'])} | {p(m[name]['r50'])} | {p(m[name]['r100'])} |")
    lines += ["", f"Selected: **{best}**（仅依据 OOF Development）。", "", "## Completion", "",
      "| Ranker | Completion@5 | Completion@20 |", "|---|---:|---:|",
      f"| RRF | {p(m['RRF']['completion_at_5'])} | {p(m['RRF']['completion_at_20'])} |",
      f"| {best} | {p(m[best]['completion_at_5'])} | {p(m[best]['completion_at_20'])} |", "",
      "## Ranking quality", "", "| Ranker | MRR | NDCG@5 | NDCG@10 | NDCG@20 |", "|---|---:|---:|---:|---:|",
      f"| RRF | {m['RRF']['mrr']:.4f} | {m['RRF']['ndcg_at_5']:.4f} | {m['RRF']['ndcg_at_10']:.4f} | {m['RRF']['ndcg_at_20']:.4f} |",
      f"| {best} | {m[best]['mrr']:.4f} | {m[best]['ndcg_at_5']:.4f} | {m[best]['ndcg_at_10']:.4f} | {m[best]['ndcg_at_20']:.4f} |", "",
      "## Ranking Ceiling", "", f"Candidate Source Oracle@20: {p(s['source_oracle']['at_20'])}", "",
      f"Pre-cap Pool Oracle@20: {p(s['pool_oracle']['r20'])}", "", f"RRF@20: {p(m['RRF']['r20'])}", "",
      f"Best LTR@20: {p(m[best]['r20'])}", "", f"Ranking Gap Closed (source oracle): {p(s['ranking_gap_closed']['at_20'])}", "",
      f"Pre-cap Pool Oracle@5: {p(s['pool_oracle']['r5'])}", "", f"Top5 Gap Closed: {p(s['ranking_gap_closed']['at_5'])}", "",
      "## Per-Risk", "", "| Risk | RRF R@5 | LTR R@5 | RRF R@20 | LTR R@20 |", "|---|---:|---:|---:|---:|"]
    for risk,row in s["per_risk"].items(): lines.append(f"| {risk} | {p(row['rrf_r5'])} | {p(row['ltr_r5'])} | {p(row['rrf_r20'])} | {p(row['ltr_r20'])} |")
    lines += ["", "## Fold Stability", "", "| Fold | RRF R@20 | LTR R@20 | Delta |", "|---|---:|---:|---:|"]
    for row in s["fold_stability"]: lines.append(f"| {row['fold']} | {p(row['rrf_r20'])} | {p(row['ltr_r20'])} | {p(row['delta'])} |")
    movement=s["movement"]
    lines += ["", "## Gold movement", "", f"Top20 promoted: {movement['top20_promoted']}", f"Top20 lost: {movement['top20_lost']}", f"Top20 net: {movement['top20_net']}", "",
      f"Top5 promoted: {movement['top5_promoted']}", f"Top5 lost: {movement['top5_lost']}", f"Top5 net: {movement['top5_net']}", "",
      f"Gold absent from the pre-cap source union: {movement['source_unavailable']}",
      f"RRF Top100 Gold lost specifically to cap/ranking: {movement['rrf_top100_cap_loss']}",
      f"LTR Top100 Gold lost specifically to cap/ranking: {movement['ltr_top100_cap_loss']}", "",
      "## Weak-negative sensitivity", "", f"40/query {best} R@20: {p(m[best]['r20'])}",
      f"20/query {best} R@20: {p(s['weak_negative_sensitivity']['weak20_r20'])}",
      f"Absolute difference: {p(s['weak_negative_sensitivity']['r20_abs_difference'])}", "",
      "## Top feature importance", ""]
    lines += [f"{i}. {row['feature']}: {row['gain']:.2f}" for i,row in enumerate(s["feature_importance"][:20],1)]
    lines += ["", "## Representative promotions", "", "| Case | Risk | Page | RRF rank | LTR rank | Main ranking signals |", "|---|---|---:|---:|---:|---|"]
    for row in s["examples"]: lines.append(f"| {row['case_id']} | {row['risk_code']} | {row['page']} | {row['rrf_rank']} | {row['ltr_rank']} | {row['signals']} |")
    lines += ["", "## Serious regression audit", ""]
    if s["serious_regressions"]:
        for risk in s["serious_regressions"]:
            row=s["per_risk"][risk]
            lines.append(f"- {risk}: R@20 {p(row['rrf_r20'])} → {p(row['ltr_r20'])}（{p(row['ltr_r20']-row['rrf_r20'])}）")
        lines += ["", "这是唯一超过5pp的核心 risk 回退；已显式保留为 Locked validation 前的风险项。", ""]
    else: lines += ["- None", ""]
    d=s["disk"]
    lines += ["", "## Disk and freeze", "", f"- Available disk before: {d['before_gib']:.2f} GiB", f"- Peak temporary disk: {d['peak_mib']:.1f} MiB",
      f"- Available disk after: {d['after_gib']:.2f} GiB", f"- Feature dataset size: {d['feature_dataset_mb']:.3f} MB",
      f"- Final model size: {d['final_model_mb']:.3f} MB", "- Temporary PDFs remaining: 0", "- Temporary ZIPs remaining: 0",
      "- Training checkpoints remaining: 0", "- Temporary dirs: CLEAN", "", "## Locked validation", "",
      "Metrics opened: NO", "", "Gold inspected: NO", "", "Used for training/tuning: NO", "", "Push: NO", "", "Remote GitHub modified: NO", ""]
    if s["pass"]: lines += ["## 简单结论", "", "LTR PASS。", "", f"等权RRF的Top20为{p(m['RRF']['r20'])}；{best}在完全OOF评测中达到{p(m[best]['r20'])}。Top5从{p(m['RRF']['r5'])}提高到{p(m[best]['r5'])}。提升通过fold、risk和Top100回归Gate，因此值得保留为实验性V3排序层。", "", "LTR frozen. Candidate Generation frozen.", "", "Recommended next step: Run final locked validation on the complete frozen V3 package.", "", "Awaiting approval before opening Locked 10.", ""]
    else: lines += ["## 简单结论", "", "LTR FAIL。", "", f"当前50篇监督数据未让LambdaMART稳定越过全部OOF Gate；{best}的Top20为{p(m[best]['r20'])}、Top5为{p(m[best]['r5'])}。不应加入V3。", ""]
    return "\n".join(lines)


def run(args):
    start=time.time(); output=args.output_dir.resolve(); output.mkdir(parents=True,exist_ok=True)
    disk_before=shutil.disk_usage(args.temp_parent).free
    development,locked=_load_split(args.split_manifest); dev=set(development); lock=set(locked)
    folds=_load_fold_manifest(args.cv_manifest,dev,lock); required,judgements=_load_gold(args.gold,dev,lock)
    old=_load_old_candidates(args.old_candidates,dev,lock); catalog=_read_catalog(args.catalog)
    smoke_cases=[case for case in development if case.startswith(("ipo_2020","ipo_2021"))][:3]
    cases=smoke_cases if args.smoke else development
    with tempfile.TemporaryDirectory(prefix=".tmp_retriever_v3_ltr_",dir=args.temp_parent) as temp_name:
        rows,peak=_stream_features(cases=cases,folds=folds,judgements=judgements,old=old,catalog=catalog,
                                  outer_zip=args.outer_zip,temp=Path(temp_name))
        if args.smoke:
            by=defaultdict(list)
            for row in rows: by[(row.case_id,row.risk_code)].append(row)
            train_cases=set(smoke_cases[:2]); valid_cases={smoke_cases[2]}; names=FEATURE_VARIANTS["LTR-A"]
            x,y,g,_=_training_data(by,train_cases,names,20); xv,yv,gv,_=_training_data(by,valid_cases,names,20)
            model=lgb.LGBMRanker(**{**MODEL_PARAMS,"n_estimators":20}); model.fit(x,y,group=g,eval_set=[(xv,yv)],eval_group=[gv],callbacks=[lgb.early_stopping(5,verbose=False)])
            return {"smoke":True,"cases":3,"rows":len(rows),"groups":len(by),"locked_metrics_opened":False,"temporary_directory_removed":True}
        feature_path=output/FEATURE_FILE; _write_features(feature_path,rows)
    rows_by_query=defaultdict(list)
    for row in rows: rows_by_query[(row.case_id,row.risk_code)].append(row)
    # Automatic leakage and one-fold stability audit before the complete CV.
    for names in FEATURE_VARIANTS.values(): audit_feature_names(names)
    one_model,_,_,one_diag=_fit_fold(rows_by_query,folds,1,FEATURE_VARIANTS["LTR-A"],40); del one_model
    if one_diag["positive_labels"]<=0 or one_diag["weak_negatives"]<=0: raise ValueError("ONE_FOLD_LABEL_AUDIT")
    rrf_ranks=_rank_from_rrf(rows_by_query); oracle_ranks=_oracle_ranks(rows_by_query)
    metrics={"RRF":_metric_bundle(required,rows_by_query,rrf_ranks)}; ranks_by_variant={}; scores_by_variant={}; diagnostics={}; importances={}
    for variant in FEATURE_VARIANTS:
        metric,ranks,scores,diag,importance=_oof(rows_by_query,folds,required,variant,40)
        metrics[variant]=metric; ranks_by_variant[variant]=ranks; scores_by_variant[variant]=scores; diagnostics[variant]=diag; importances[variant]=importance
        print(f"{variant}: OOF R@5={metric['r5']:.4f} R@20={metric['r20']:.4f}",flush=True)
    selected=max(FEATURE_VARIANTS,key=lambda name:(metrics[name]["r20"],metrics[name]["r5"],metrics[name]["completion_at_20"],-list(FEATURE_VARIANTS).index(name)))
    weak20,_,_,_,_=_oof(rows_by_query,folds,required,selected,20)
    selected_ranks=ranks_by_variant[selected]; per_risk=_per_risk(required,rrf_ranks,selected_ranks); fold_stability=_fold_metrics(required,folds,rrf_ranks,selected_ranks)
    required_keys=[(row["case_id"],row["risk_code"],row["page"]) for row in required]
    movement={}
    for k in (5,20):
        base={key for key in required_keys if rrf_ranks.get(key,999)<=k}; new={key for key in required_keys if selected_ranks.get(key,999)<=k}
        movement[f"top{k}_promoted"]=len(new-base); movement[f"top{k}_lost"]=len(base-new); movement[f"top{k}_net"]=len(new)-len(base)
    movement["rrf_top100_missed"]=sum(rrf_ranks.get(key,999)>100 for key in required_keys)
    movement["ltr_top100_missed"]=sum(selected_ranks.get(key,999)>100 for key in required_keys)
    source=json.loads((output/"table_phase_c_summary.json").read_text(encoding="utf-8"))["oracle"]["after"]
    pool_oracle=_metric_bundle(required,rows_by_query,oracle_ranks)
    source_unavailable=sum(oracle_ranks.get(key,999)>100 for key in required_keys)
    movement["source_unavailable"]=source_unavailable
    movement["rrf_top100_cap_loss"]=movement["rrf_top100_missed"]-source_unavailable
    movement["ltr_top100_cap_loss"]=movement["ltr_top100_missed"]-source_unavailable
    serious=[risk for risk,row in per_risk.items() if row["ltr_r20"]-row["rrf_r20"] < -.05]
    gates={"A_r20":metrics[selected]["r20"]>=.79 or metrics[selected]["r20"]-metrics["RRF"]["r20"]>=.035,
           "B_r5":metrics[selected]["r5"]>=.57 or metrics[selected]["r5"]-metrics["RRF"]["r5"]>=.025,
           "C_4_of_5_folds":sum(row["ltr_r20"]>=row["rrf_r20"] for row in fold_stability)>=4,
           "D_multi_risk":sum(row["ltr_r20"]>row["rrf_r20"] for row in per_risk.values())>=3,
           "E_serious_regressions_at_most_one":len(serious)<=1,
           "F_top100_not_lower":metrics[selected]["r100"]>=metrics["RRF"]["r100"]}
    passed=all(gates.values())
    names=FEATURE_VARIANTS[selected]; final_model_path=ROOT/"models"/"retriever_v3"/"ltr_v3.txt"; final_size=0.0
    if passed:
        x,y,groups,_=_training_data(rows_by_query,set(development),names,40)
        iterations=max(20,round(statistics.median(row["best_iteration"] for row in diagnostics[selected])))
        model=lgb.LGBMRanker(**{**MODEL_PARAMS,"n_estimators":iterations}); model.fit(x,y,group=groups)
        final_model_path.parent.mkdir(parents=True,exist_ok=True); model.booster_.save_model(str(final_model_path)); final_size=final_model_path.stat().st_size/2**20
        final_importance=dict(zip(names,model.booster_.feature_importance(importance_type="gain").tolist()))
    else: final_importance=importances[selected]
    importance_rows=[{"feature":name,"gain":gain} for name,gain in sorted(final_importance.items(),key=lambda item:(-item[1],item[0]))]
    examples=[]
    for key in required_keys:
        if rrf_ranks.get(key,999)>20 and selected_ranks.get(key,999)<=20:
            row=next(r for r in rows_by_query[(key[0],key[1])] if r.page==key[2])
            available=[]
            for name in names:
                if name.endswith("_rank") and name != "rrf_rank":
                    lane=name.removesuffix("_rank")
                    if row.features.get(f"{lane}_present",0)==0: continue
                if row.features[name] == 0: continue
                available.append((name, final_importance.get(name,0.0)))
            signals=sorted(available,key=lambda item:(-item[1],item[0]))[:3]
            examples.append({"case_id":key[0],"risk_code":key[1],"page":key[2],"rrf_rank":rrf_ranks.get(key),"ltr_rank":selected_ranks.get(key),"signals":", ".join(n for n,_ in signals)})
    _write_oof(output/"ltr_oof_predictions.csv.gz",rows,rrf_ranks,ranks_by_variant,scores_by_variant[selected])
    disk_after=shutil.disk_usage(args.temp_parent).free
    gap=lambda k:(metrics[selected][f"r{k}"]-metrics["RRF"][f"r{k}"])/(source[f"at_{k}" if k<100 else "at_100_native"]-metrics["RRF"][f"r{k}"]) if source.get(f"at_{k}",source.get("at_100_native"))!=metrics["RRF"][f"r{k}"] else 0
    summary={"result":"PASS" if passed else "FAIL","pass":passed,"model":"LightGBM LambdaMART","lightgbm_version":lgb.__version__,"development_cases":50,"locked_cases":10,"locked_metrics_opened":False,
      "candidate_sources":["V1","V2","V2.1","BM25-B","TABLE-C"],"selected_variant":selected,"feature_variants":{k:list(v) for k,v in FEATURE_VARIANTS.items()},"model_config":MODEL_PARAMS,"weak_negative_policy":{"selected_per_query":40,"sensitivity":20,"neighbor_exclusion":1,"deterministic":True},
      "metrics":metrics,"source_oracle":source,"pool_oracle":pool_oracle,"ranking_gap_closed":{"at_5":(metrics[selected]["r5"]-metrics["RRF"]["r5"])/(pool_oracle["r5"]-metrics["RRF"]["r5"]),"at_20":gap(20)},
      "per_risk":per_risk,"macro_risk":{"rrf_r5":statistics.mean(x["rrf_r5"] for x in per_risk.values()),"ltr_r5":statistics.mean(x["ltr_r5"] for x in per_risk.values()),"rrf_r20":statistics.mean(x["rrf_r20"] for x in per_risk.values()),"ltr_r20":statistics.mean(x["ltr_r20"] for x in per_risk.values())},
      "fold_stability":fold_stability,"fold_diagnostics":diagnostics,"one_fold_audit":one_diag,"weak_negative_sensitivity":{"weak20_r20":weak20["r20"],"weak40_r20":metrics[selected]["r20"],"r20_abs_difference":abs(weak20["r20"]-metrics[selected]["r20"])},
      "movement":movement,"serious_regressions":serious,"gates":gates,"feature_importance":importance_rows,"examples":examples[:10],"final_model":{"saved":passed,"path":"models/retriever_v3/ltr_v3.txt" if passed else None,"size_mb":final_size},
      "disk":{"before_bytes":disk_before,"after_bytes":disk_after,"peak_temporary_bytes":peak,"before_gib":disk_before/2**30,"after_gib":disk_after/2**30,"peak_mib":peak/2**20,"feature_dataset_mb":feature_path.stat().st_size/2**20,"final_model_mb":final_size},"runtime_seconds":time.time()-start}
    source_cv=json.loads(args.cv_manifest.read_text(encoding="utf-8"))
    ltr_cv={"manifest_version":"retriever_v3_ltr_cv_v1","reused_from":"bm25_cv_manifest.json",
            "salt":source_cv["salt"],"group":source_cv["group"],"fold_count":source_cv["fold_count"],
            "cases_per_fold":source_cv["cases_per_fold"],"folds":source_cv["folds"],
            "locked_case_count":10,"locked_metrics_opened":False}
    (output/"ltr_cv_manifest.json").write_text(json.dumps(ltr_cv,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (output/"ltr_phase_d_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (output/"RETRIEVER_V3_PHASE_D_LTR_REPORT.md").write_text(_report(summary),encoding="utf-8")
    return {"completed":True,"result":summary["result"],"selected":selected,"r5":metrics[selected]["r5"],"r20":metrics[selected]["r20"],"locked_metrics_opened":False,"temporary_directory_removed":True}


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--outer-zip",type=Path,default=OUTER_ZIP_DEFAULT)
    parser.add_argument("--catalog",type=Path,default=Path("data/catalog/ipo_prospectus_manifest.csv")); parser.add_argument("--split-manifest",type=Path,default=Path("reports/retriever_v3/split_manifest.json"))
    parser.add_argument("--cv-manifest",type=Path,default=Path("reports/retriever_v3/bm25_cv_manifest.json")); parser.add_argument("--gold",type=Path,default=Path("reports/retriever_v3/gold_evidence.csv"))
    parser.add_argument("--old-candidates",type=Path,default=Path("reports/retriever_v3/hard_candidate_dataset.csv.gz")); parser.add_argument("--output-dir",type=Path,default=Path("reports/retriever_v3"))
    parser.add_argument("--temp-parent",type=Path,default=Path("..")); parser.add_argument("--smoke",action="store_true")
    args=parser.parse_args(); print(json.dumps(run(args),ensure_ascii=False)); return 0
if __name__=="__main__": raise SystemExit(main())
