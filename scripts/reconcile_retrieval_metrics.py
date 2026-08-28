"""Reconcile current Hybrid and historical Retriever V3 on one frozen split."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from evaluate_hybrid_bm25_adapter import KEYWORD_ONLY_RISKS, _rank


def _metrics(frame: pd.DataFrame, rank: str) -> dict[str, float]:
    values = frame[rank]
    result = {f"recall_at_{k}": float((values <= k).mean()) for k in (5, 10, 20, 50)}
    result["mrr"] = float(np.where(np.isfinite(values), 1.0 / values, 0.0).mean())
    return result


def reconcile(features: Path, ltr_predictions: Path, split_manifest: Path, gold_evidence: Path) -> dict:
    feature = pd.read_csv(features)
    split = json.loads(split_manifest.read_text(encoding="utf-8"))
    development = set(split["historical_development"] + split["new_development"])
    if set(feature["case_id"].unique()) != development:
        raise ValueError("feature table is not the frozen 50-case Development split")
    current = pd.concat([_rank(group) for _, group in feature.groupby(["case_id", "risk_code"])])
    current_gold = current[current["gold_label"] > 0].copy()
    ltr = pd.read_csv(ltr_predictions)
    ltr_gold = ltr[ltr["gold_label"] > 0].copy()
    if set(zip(current_gold.case_id, current_gold.risk_code, current_gold.page)) != set(zip(ltr_gold.case_id, ltr_gold.risk_code, ltr_gold.page)):
        raise ValueError("V3 and Hybrid do not share identical positive Evidence rows")
    governed = pd.read_csv(gold_evidence)
    required = governed[
        governed["case_id"].isin(development) & governed["requirement"].eq("required")
    ][["case_id", "risk_code", "page"]]
    current_required = required.merge(current, on=["case_id", "risk_code", "page"], how="left")
    historical_required = required.merge(ltr, on=["case_id", "risk_code", "page"], how="left")
    enabled = ~current_required["risk_code"].isin(KEYWORD_ONLY_RISKS)
    current_oracle = {
        f"oracle_at_{k}": float(((current_required.v1_rank <= k) | (enabled & (current_required.bm25_rank <= k))).mean())
        for k in (20, 50)
    }
    historical_oracle = {
        f"oracle_at_{k}": float(
            np.logical_or.reduce([
                current_required.v1_rank <= k, current_required.v2_rank <= k,
                current_required.v21_rank <= k, current_required.bm25_rank <= k,
                current_required.table_rank <= k,
            ]).mean()
        ) for k in (20, 50)
    }
    return {
        "benchmark": "Retriever V3 frozen 50-case Development feature table",
        "case_count": len(development), "task_count": int(current.groupby(["case_id", "risk_code"]).ngroups),
        "all_positive_evidence_rows": len(current_gold),
        "historical_required_evidence_units": len(required),
        "gold_definition": "gold_evidence.requirement == required",
        "current_hybrid": {**_metrics(current_required, "selected_rank"), **current_oracle},
        "historical_v3_ltr_c": {**_metrics(historical_required, "ltr_c_rank"), **historical_oracle},
        "current_components": ["V1 keyword", "BM25-B", "equal RRF", "keyword-only cash_runway/litigation"],
        "historical_components": ["V1", "V2", "V2.1", "BM25-B", "Table", "LTR-C"],
        "leakage_policy": "Development OOF LTR predictions; locked Validation excluded",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=Path("reports/retriever_v3/candidate_ltr_features.csv.gz"))
    parser.add_argument("--ltr", type=Path, default=Path("reports/retriever_v3/ltr_oof_predictions.csv.gz"))
    parser.add_argument("--split", type=Path, default=Path("reports/retriever_v3/split_manifest.json"))
    parser.add_argument("--gold-evidence", type=Path, default=Path("reports/retriever_v3/gold_evidence.csv"))
    parser.add_argument("--output", type=Path, default=Path("reports/experiments/METRIC_RECONCILIATION.json"))
    args = parser.parse_args()
    result = reconcile(args.features, args.ltr, args.split, args.gold_evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
