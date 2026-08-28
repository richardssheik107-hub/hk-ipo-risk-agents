"""Reproduce the zero-PDF development A/B for the opt-in BM25 adapter.

The input is the already-frozen Retriever V3 feature table.  Locked cases are
rejected rather than silently included, and no PDF, label source or LLM is
opened by this script.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


KEYWORD_ONLY_RISKS = frozenset(
    {"cash_runway", "material_litigation_compliance"}
)
K_VALUES = (5, 10, 20, 50)


def _rank(group: pd.DataFrame) -> pd.DataFrame:
    group = group.copy()
    group["keyword_rank"] = np.where(
        group["v1_present"] > 0, group["v1_rank"], np.inf
    )
    group["bm25_effective_rank"] = np.where(
        group["bm25_present"] > 0, group["bm25_rank"], np.inf
    )
    group["hybrid_score"] = np.where(
        group["v1_present"] > 0, 1.0 / (60.0 + group["v1_rank"]), 0.0
    ) + np.where(
        group["bm25_present"] > 0, 1.0 / (60.0 + group["bm25_rank"]), 0.0
    )
    ordered = group.sort_values(
        ["hybrid_score", "keyword_rank", "bm25_effective_rank", "page"],
        ascending=[False, True, True, True],
    ).index
    group["hybrid_rank"] = pd.Series(range(1, len(ordered) + 1), index=ordered)
    group["selected_rank"] = np.where(
        group["risk_code"].isin(KEYWORD_ONLY_RISKS),
        group["keyword_rank"],
        group["hybrid_rank"],
    )
    return group


def _metrics(frame: pd.DataFrame, rank: str) -> dict[str, float]:
    values = frame[rank]
    output = {f"recall_at_{k}": float((values <= k).mean()) for k in K_VALUES}
    output["mrr"] = float(
        np.where(np.isfinite(values), 1.0 / values, 0.0).mean()
    )
    required = frame[frame["gold_label"] >= 2]
    output.update(
        {
            f"required_at_{k}": float((required[rank] <= k).mean())
            for k in K_VALUES
        }
    )
    return output


def evaluate(features: Path, split_manifest: Path) -> dict:
    split = json.loads(split_manifest.read_text(encoding="utf-8"))
    development = set(split["historical_development"] + split["new_development"])
    locked = set(split["locked_validation"])
    frame = pd.read_csv(features)
    cases = set(frame["case_id"].unique())
    if cases != development or cases & locked:
        raise ValueError("feature table is not the frozen 50-case development split")

    ranked = pd.concat(
        [_rank(group) for _, group in frame.groupby(["case_id", "risk_code"])]
    )
    gold = ranked[ranked["gold_label"] > 0].copy()
    before = _metrics(gold, "keyword_rank")
    after = _metrics(gold, "selected_rank")
    bm25_enabled = ~gold["risk_code"].isin(KEYWORD_ONLY_RISKS)
    oracle = {
        "before": {
            f"oracle_at_{k}": float((gold["v1_rank"] <= k).mean())
            for k in (20, 50)
        },
        "after": {
            f"oracle_at_{k}": float(
                (
                    (gold["v1_rank"] <= k)
                    | (bm25_enabled & (gold["bm25_rank"] <= k))
                ).mean()
            )
            for k in (20, 50)
        },
    }

    per_risk = {}
    for risk_code, group in gold.groupby("risk_code"):
        per_risk[risk_code] = {
            "gold": int(len(group)),
            "before": _metrics(group, "keyword_rank"),
            "after": _metrics(group, "selected_rank"),
        }

    regressions = []
    for case_id, group in gold.groupby("case_id"):
        before_r20 = float((group["keyword_rank"] <= 20).mean())
        after_r20 = float((group["selected_rank"] <= 20).mean())
        if after_r20 < before_r20:
            regressions.append(
                {
                    "case_id": case_id,
                    "before_recall_at_20": before_r20,
                    "after_recall_at_20": after_r20,
                    "delta": after_r20 - before_r20,
                }
            )

    return {
        "experiment_id": "EXP-RTR-HYBRID-BM25-001",
        "hypothesis": "case-local BM25 candidate recovery improves the keyword ceiling without replacing deterministic extraction",
        "dataset": "Retriever V3 frozen 50-case development feature table",
        "locked_cases_read": False,
        "pdfs_read": 0,
        "llm_calls": 0,
        "gold_rows": int(len(gold)),
        "required_gold_rows": int((gold["gold_label"] >= 2).sum()),
        "policy": {
            "fusion": "equal RRF, keyword-rank tie break",
            "bm25": "frozen BM25-B",
            "keyword_only_risks": sorted(KEYWORD_ONLY_RISKS),
        },
        "before": before,
        "after": after,
        "delta": {key: after[key] - before[key] for key in before},
        "candidate_oracle": oracle,
        "retrieval_misses_at_20": {
            "before": int((gold["keyword_rank"] > 20).sum()),
            "after": int((gold["selected_rank"] > 20).sum()),
        },
        "per_risk": per_risk,
        "case_regressions_at_20": regressions,
        "decision": "KEEP_OPT_IN",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--features",
        type=Path,
        default=Path("reports/retriever_v3/candidate_ltr_features.csv.gz"),
    )
    parser.add_argument(
        "--split-manifest",
        type=Path,
        default=Path("reports/retriever_v3/split_manifest.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/experiments/EXP-RTR-HYBRID-BM25-001.json"),
    )
    args = parser.parse_args()
    result = evaluate(args.features, args.split_manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
