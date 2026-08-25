# HK IPO Risk Agents

Evidence-backed multi-agent risk analysis and market-warning system for Hong Kong IPO prospectuses.

系统以真实招股书 Evidence 为基础，由 Financial / Legal / Business Agents、LLM semantic reasoning、deterministic Skills、Verifier、Market interpretation 与 Final Supervisor 形成可审计的风险分析闭环。

> 规则分和 `uncalibrated_model_score` 不是实际下跌概率，也不构成投资建议。

## Current Status — 2026-08-25

```text
v0.3 Document Intelligence              COMPLETE / FROZEN
PR-A–PR-G                               COMPLETE / FROZEN
PR-H Streamlit Full E2E                 PARTIAL / BLOCKED
v0.4.3 Baseline E2E Freeze              NOT CREATED
5-Day Competition Submission Sprint     ACTIVE
v0.4.5 Competition Ready                TARGET
```

## Competition delivery mode

Only five days remain, so the project is no longer running a broad research roadmap. The active goal is to return to the competition task and make the working system materially stronger with real LLM capability.

```text
Day 1  real LLM Legal / Business Document intelligence
Day 2  governed Market → LLM interpretation + LLM Final Supervisor + one re-check
Day 3  3–5 real IPO cases + targeted fixes + small Offline-vs-AI check
Day 4  Evidence + AI Analysis + Agent Trace product integration
Day 5  regression + freeze + submission + rehearsal
```

Deferred until after submission:

```text
full multi-horizon research
broad feature audit / P-Core
new model families / tuning
large Retriever research
industry PIT research
new broad market datasets
full benchmark construction
story-only features
```

## Final product path

```text
Prospectus PDF
→ Parser / Retriever / Evidence
→ Financial Agent
→ Legal Agent + LLM semantic extraction
→ Business Agent + LLM semantic cross-check
→ deterministic Calculation
→ Verifier
→ governed Market facts + LLM Market interpretation
→ frozen Model signal if available + Rule signal
→ LLM Final Supervisor
→ conflict / one controlled re-check / uncertainty
→ Final Report / Streamlit / Agent Trace
```

LLM is used where semantic understanding matters. Python remains authoritative for exact math, schema/identity, PIT checks, hashes, model scoring and reproducibility.

## What is already real

```text
Official 2020–2024 IPO universe       438
Production Document-X                 438 / 438, 100 dims
Market-X Core                         438 / 438, 30 positions
5D outcome                            424 / 438
Canonical model-ready                 424 = 354 Dev + 70 Val
Oracle v2                             98 materialized / 96 strict
2025 Blind y accessed                 NO
```

Market Extended readiness:

```text
HSI return / volatility               438 / 438
HKEX turnover 20D                     438 / 438
production industry return              0 / 438 (PIT_BLOCKED)
```

## LLM responsibilities in the competition version

### Legal Agent

Real LLM structured extraction should resolve complex clause semantics such as right effectiveness, post-listing survival, termination/restoration conditions and actual litigation/compliance matters versus generic disclosure.

### Business Agent

LLM should cross-check or fill bounded semantics such as core product identity, development stage, launch/commercialization state and product revenue versus generic revenue.

### Financial Agent

Financial calculations remain deterministic-first. LLM may assist only with already-grounded textual ambiguity.

### Market Agent

LLM interprets governed pre-listing facts into `market_regime / risk_level / key_drivers / uncertainty`; it never invents missing market values.

### Final Supervisor

LLM synthesizes existing Agent/Market/Model/Rule inputs, detects conflict and uncertainty, requests one controlled re-check, and produces the final explanation without creating new Evidence.

## Frozen model finding

PR-F Full Production 2024 remains an honest auxiliary baseline:

```text
M   Market only              ROC-AUC 0.4246
P   Production Document      ROC-AUC 0.5000
PM  Market + Production      ROC-AUC 0.4246
```

The five-day sprint does not spend time trying to make this result look better. No 2024 retuning, score inversion or new model search is part of the active plan.

## PR-H / model runtime

PR-H still formally requires the original frozen PR-F per-case runtime/handoff plus the all-channel real-case matrix. D time-boxes recovery of that original asset.

If it cannot be recovered:

```text
formal PR-H remains BLOCKED
Model Channel = unavailable
Document + Market + Rule + LLM Supervisor continue
```

No retraining or fabricated model score is allowed merely to make the UI look complete.

## Five-person ownership

```text
A  Integration / CI / Release / Submission
B  Legal + Business real LLM semantics / Evidence / Verifier
C  Governed Market facts + LLM Market interpretation
D  Frozen PR-F handoff + minimal Offline-vs-AI effect check
E  LLM Final Supervisor + conflict/re-check + Evidence/AI Trace + UI
```

Detailed plan: [`docs/V04_FIVE_PERSON_EXECUTION_PLAN.md`](docs/V04_FIVE_PERSON_EXECUTION_PLAN.md).

## Submission definition of done

```text
>=3 stable real IPO cases
real LLM provider path active
Legal/Business semantic reasoning visibly useful
Market interpretation grounded in PIT facts
LLM Final Supervisor active
at least one controlled conflict/re-check example
Evidence / Calculation / Verifier authoritative
Agent/LLM trace visible
model state honest
no fake market facts
no 2025 Blind y access
full CI + real-case smoke pass
reproducible runbook and submission package
```

## Architecture

```text
Prospectus PDF
→ Parser
→ Retriever / Evidence
→ Financial / Legal / Business Agents
→ LLM semantic reasoning where needed
→ deterministic Skills
→ Verifier
→ governed Market context
→ Model / Rule auxiliary signals
→ LLM Final Supervisor
→ Streamlit / Final Report / Agent Trace
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

1. [`docs/README.md`](docs/README.md)
2. [`docs/ROADMAP.md`](docs/ROADMAP.md)
3. [`docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md)
4. [`docs/V04_FIVE_PERSON_EXECUTION_PLAN.md`](docs/V04_FIVE_PERSON_EXECUTION_PLAN.md)
5. [`docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md)
6. [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md)
7. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
8. [`docs/DATA_SCHEMA.md`](docs/DATA_SCHEMA.md)
9. [`docs/research/V04_DATA_READINESS.md`](docs/research/V04_DATA_READINESS.md)

Frozen facts remain authoritative in completion reports and `reports/frozen/*.json`.
