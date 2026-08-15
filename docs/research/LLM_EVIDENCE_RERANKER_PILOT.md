# Phase 0.6C — Two-Stage LLM Evidence Reranker Pilot

This research-only experiment freezes a deterministic V1/V2 candidate union before any Expert annotation is loaded. The configured structured `LLMProvider` labels evidence quality; Python applies a fixed lexicographic tier order. The LLM never emits a numeric final score or rank.

The ten 2020 cases are retrospective development benchmarks, not blind data. Candidate pools, prompts, schema, ranking logic and model identity are frozen before LLM calls. LLM outputs are frozen before annotations are unlocked for evaluation. No Agent, Verifier, Supervisor, Predictor, Workflow, market outcome or 2025 blind data is used.

Commands:

```powershell
python scripts/run_llm_reranker_pilot.py prepare --pdf-root C:\path\to\pdfs
python scripts/run_llm_reranker_pilot.py judge
```

The judge stage requires `IPO_RISK_LLM_API_KEY`, `IPO_RISK_LLM_BASE_URL` and
`IPO_RISK_LLM_MODEL`. Credentials and raw provider responses are never
persisted.

## Revision 4 frozen result

Revision 4 completed all 80 official tasks before Gold was unlocked:

- structured LLM completion: 65 tasks;
- deterministic Stage1 fallback: 15 tasks (18.75%);
- diagnostic replays: 3, excluded from official metrics;
- Gold leakage: none;
- 2025 blind access: none;
- real LLM calls during post-Gold evaluation: zero.

The retrospective 10-case evaluation found positive incremental semantic
ranking value over the Stage1 Union baseline:

| Metric | Stage1 Union | LLM Revision 4 | Delta |
| --- | ---: | ---: | ---: |
| Required Recall@3 | 34.48% | 40.52% | +6.03 pp |
| Required Recall@5 | 42.24% | 50.86% | +8.62 pp |
| Required Completion@5 | 37.50% | 45.00% | +7.50 pp |
| MRR | 0.2690 | 0.3304 | +0.0614 |

The pilot is not production-ready: structured-output reliability is poor,
Business Required@5 regresses against the strongest deterministic baseline,
and Stage1 Required Recall@20 is only 59.48%. The frozen recommendation is
`PHASE_0_6D_RERANKER_V1_1` on a fresh benchmark, without further tuning on
these 10 cases.

## Versioned research artifacts

The branch versions the evidence needed to reproduce and audit the experiment:

- `reports/llm_reranker_pilot/candidate_pools.json`;
- `reports/llm_reranker_pilot/judgments/` (80 official results);
- `reports/llm_reranker_pilot/diagnostic_replay/` (three excluded replays);
- pre-Gold and output-freeze manifests;
- `reports/llm_reranker_pilot/formal_evaluation_rev4/` (16 final artifacts).

Runtime stdout/stderr logs remain ignored. The authoritative report is
`reports/llm_reranker_pilot/formal_evaluation_rev4/15_phase_06c_final_report.md`.
