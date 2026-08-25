# HK IPO Risk Agents

Evidence-backed multi-agent risk analysis and market-warning research for Hong Kong IPO prospectuses.

系统以真实招股书 Evidence 为基础，由 Financial / Legal / Business Agents、deterministic Skills、Verifier 与 Supervisor 生成可审计风险；v0.4 进一步连接 Production Document-X、governed Market-X、Outcome、模型解释与 Final Supervisor，形成 PDF → Final Report 的端到端闭环。

> 规则分和 `uncalibrated_model_score` 不是实际下跌概率，也不构成投资建议。

## Current Status — 2026-08-25

```text
v0.3 Document Intelligence              COMPLETE / FROZEN
PR-A Document-X                         COMPLETE / FROZEN
PR-B Market-X Core                      COMPLETE / FROZEN
PR-C 5D Outcome                         COMPLETE / FROZEN
PR-D Canonical Dataset                  COMPLETE / FROZEN
Oracle v2                               COMPLETE / FROZEN / EVALUATION-ONLY
PR-E Baseline + Oracle                  COMPLETE / FROZEN
PR-F LightGBM + Explainability          COMPLETE / FROZEN
PR-G Market Agent + Final Supervisor    COMPLETE / FROZEN
PR-H Streamlit Full E2E                 PARTIAL / BLOCKED — CURRENT GATE
v0.4.3 Baseline E2E Freeze              NOT CREATED
Competition Hardening                   PLANNED
v0.4.5 Competition Ready                PLANNED
```

## What is already real

```text
Official 2020–2024 IPO universe       438
Production Document-X                 438 / 438, 100 dims
Market-X Core                         438 / 438, 30 positions
5D outcome                            424 / 438
Canonical model-ready                 424 = 354 Dev + 70 Val
Oracle v2                             98 materialized / 96 strict
Oracle v2 split                       77 Dev / 19 Val
2025 Blind y accessed                 NO
```

Market Extended current readiness:

```text
HSI return / volatility               438 / 438
HKEX turnover 20D                     438 / 438
production industry return              0 / 438 (PIT_BLOCKED)
```

Industry return is intentionally unavailable until a historically effective/PIT-safe company classification source exists.

## Frozen model finding

PR-F Full Production 2024:

```text
M   Market only              ROC-AUC 0.4246
P   Production Document      ROC-AUC 0.5000
PM  Market + Production      ROC-AUC 0.4246
```

PM and M are prediction-equivalent under the frozen LightGBM policy; all 100 Production Document features have zero split/gain/SHAP use in that run. Oracle `OM-M ROC-AUC = -0.0143`, with a wide 95% paired-bootstrap interval crossing zero on only 19 Validation cases.

The correct conclusion is: **stable Document increment was not validated under the current 5D target/sample/representation/model**. It is not proof that prospectus risk information is intrinsically useless. We therefore diagnose extraction quality, feature representation, time horizon and market context before changing model families.

## Current PR-H objective

2410.HK has already demonstrated the governed real PDF → Document / Market / Rule → Final Supervisor → 13-section report path. PR-H still needs:

1. the original frozen PR-F runtime or a pre-existing hash-bound sanitized handoff;
2. at least three matching real 2024 prospectus PDFs;
3. a 3–5 case matrix with Document / Market / Model / Rule all governed;
4. determinism / provenance / Evidence / Blind checks.

No retraining, reconstruction, score inversion or 2024 retuning is allowed just to unblock UI. PASS creates `v0.4.3 BASELINE E2E FREEZE`.

## Competition plan

After v0.4.3:

```text
CH-0  Scope / Metrics Lock
CH-1  Multi-Horizon Outcome + Predictive Diagnosis
CH-2  Document Benchmark + Targeted Hardening
CH-3  Market Intelligence / IPO Context
CH-4  Multi-Agent Conflict + Full Trace
CH-5  Evidence Viewer + Competition Product
Beta  Integrated competition checkpoint
CH-6  Formal Evaluation / Freeze
→ v0.4.5 COMPETITION_READY
→ Submission + Demo Rehearsal
```

CH-1 / CH-2 / CH-3 run substantially in parallel.

Competition scorecard:

```text
key risk quality target              >= 80%
key Evidence Recall                  >= 85%
Agent / Tool / Evidence traceability = 100%
1D / 5D / 20D / 60D predictive results reported honestly
```

## Five-person ownership

```text
A  Tech Lead / Integration / CI / Gate / Release / Submission
B  Document Intelligence / Evidence / Benchmark
C  Market Intelligence / PIT / Outcome Data
D  Quant / ML / Multi-Horizon / SHAP / Ablation
E  Multi-Agent / Conflict / Supervisor / Evidence Viewer / UI
```

Detailed plan: [`docs/V04_FIVE_PERSON_EXECUTION_PLAN.md`](docs/V04_FIVE_PERSON_EXECUTION_PLAN.md).

## Architecture

```text
Prospectus PDF
→ Parser
→ Retriever / Evidence
→ Financial / Legal / Business Agents
→ deterministic Skills
→ Verifier / Document Supervisor
→ Production Document-X
→ Market-X Core (+ governed Extended)
→ Outcome / Canonical Dataset
→ Baseline / LightGBM / Explainability
→ Market Agent / Final Supervisor
→ Streamlit / Final Report
```

Oracle stays evaluation-only and isolated from Production.

## Governance

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

Formal RiskItem requires Evidence; exact numeric claims require deterministic Calculation. Missing is explicit. 2024 is not recycled into a tuning set; 2025 Blind y remains closed until formally authorized.

## Quick Start

### Windows PowerShell

```powershell
python -m pip install -e ".[dev,retrieval-research]"
Remove-Item Env:IPO_RISK_LLM_PROVIDER -ErrorAction SilentlyContinue
$env:PYTHONPATH = "src"
pytest -q
python scripts/validate_project.py
python -m streamlit run app/streamlit_app.py
```

### Linux / macOS

```bash
python -m pip install -e '.[dev,retrieval-research]'
export PYTHONPATH=src
pytest -q
python scripts/validate_project.py
python -m streamlit run app/streamlit_app.py
```

Secrets only come from environment variables. Do not commit `.env`, API keys, local absolute paths, licensed raw data or large runtime artifacts.

## Documentation

Read current active documents in this order:

1. [`docs/README.md`](docs/README.md) — source-of-truth and active index
2. [`docs/ROADMAP.md`](docs/ROADMAP.md) — current Gate and schedule
3. [`docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md) — program strategy
4. [`docs/V04_FIVE_PERSON_EXECUTION_PLAN.md`](docs/V04_FIVE_PERSON_EXECUTION_PLAN.md) — team ownership
5. [`docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md) — hardening through submission
6. [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md) — product and governance contract
7. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — technical boundaries
8. [`docs/DATA_SCHEMA.md`](docs/DATA_SCHEMA.md) — data/model contracts
9. [`docs/research/V04_DATA_READINESS.md`](docs/research/V04_DATA_READINESS.md) — measured readiness

Frozen facts remain authoritative in completion reports and `reports/frozen/*.json`.
