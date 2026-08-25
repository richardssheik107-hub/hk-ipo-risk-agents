# HK IPO Risk Agents

Evidence-backed multi-agent risk analysis and market-warning system for Hong Kong IPO prospectuses.

系统以真实招股书 Evidence 为基础，由 Financial / Legal / Business Agents、LLM semantic reasoning、deterministic Skills、Verifier、governed MarketContext、controlled re-check 与 Final Supervisor 形成可审计的港股 IPO 风险分析链。

> 规则分和 `uncalibrated_model_score` 不是实际下跌概率，也不构成投资建议。

## Current status — 2026-08-25

```text
v0.4.0 Competition Preview              RELEASE CANDIDATE
v0.4.5 competition runtime              IMPLEMENTED / HARDENING
v0.3 Document Intelligence              COMPLETE / FROZEN
PR-A–PR-G                               COMPLETE / FROZEN
Historical PR-H formal freeze           PARTIAL / BLOCKED
Competition Final Sprint                ACTIVE
Competition target                      v0.4.5 COMPETITION_READY
```

`v0.4.0` 与最终比赛验收分开：前者是当前 package/release checkpoint；`v0.4.5` 是比赛 runtime 和最终验收目标。只有赛题硬 Gate 全部闭合后才能标记 `COMPETITION_READY`。发布验收与剩余 blocker 见 [`docs/V0.4_RELEASE_ACCEPTANCE.md`](docs/V0.4_RELEASE_ACCEPTANCE.md)。

## Competition runtime now implemented

当前 `configs/v045_competition_ai.yaml` 的主链已经实现：

```text
Prospectus PDF
→ Parser / Retriever / Evidence
→ Financial Agent + deterministic calculations
→ Legal Agent + bounded LLM semantics
→ Business Agent + bounded LLM semantics
→ Verifier / Document Supervisor
→ governed Market-X
→ IPOHeatSkill / MarketRegimeSkill
→ MarketIntelligenceAgent + bounded LLM interpretation
→ Rule signal + frozen Model signal if available
→ deterministic conflict detection
→ bounded targeted re-check
→ LLM Final Supervisor synthesis
→ Agent / Tool / Evidence trace
→ Evidence Viewer / Human Review / Final Report
```

Market Agent formal runtime wiring、LLM Final Supervisor、conflict detection、最多一次的 targeted re-check、Agent Trace、Evidence Viewer、Human Review 和五工作区 Streamlit 均已进入 `main`。缺失通道必须显式降级，不能用 mock、零值或代理变量补位。

### Market missingness contract

`governed_pr_b_core` 可以在没有 C-lane Extended readiness 的情况下运行。此时 HSI / volatility / turnover 等 Extended-only feature 可能完全不在 `MarketContextView.observations` 中；Skill 必须把“feature 不存在”视为 `source_unavailable`，而不是访问空对象或制造数值。

Competition config 默认：

```text
market_context              governed_pr_b_core
market_extended_readiness   ""   # optional local governed artifact
```

因此 Core-only 运行允许 `MarketRegime = INSUFFICIENT_DATA`。若本地有经过治理的 Extended readiness，可通过 YAML 或环境变量 `IPO_RISK_MARKET_EXTENDED_READINESS` 显式接入；industry return 仍保持 PIT-blocked，不做替代。

## Real-case hardening status

当前正式 demo matrix：

```text
ipo_2024_02410   2410.HK   浙江同源康医药股份有限公司   2024-08-20
ipo_2024_02460   2460.HK   华润饮料控股有限公司       2024-10-23
ipo_2024_01318   1318.HK   毛戈平化妆品股份有限公司   2024-12-10
```

2410.HK 已多次用于真实 E2E smoke。最新 AI smoke 暴露了 Core-only Market Intelligence 的 absent-feature bug：`'NoneType' object has no attribute 'missing_reason'`。代码现已将 absent source feature 映射为显式 `source_unavailable` 并新增 regression tests；该真实案例仍需在更新后的 `main` 上重跑后才能记为最终 PASS。

PR #128 的 E-lane真实受控案例已证明 conflict / re-check / trace 链可以工作：6 conflicts、3 controlled re-checks、22 trace events、83/83 Evidence refs resolved、overall traceability 1.0；该完成报告见 [`docs/V04_ROLE_E_COMPLETION_REPORT.md`](docs/V04_ROLE_E_COMPLETION_REPORT.md)。这不替代最终 3–5 case 验收。

## Competition requirements mapped to the product

```text
数百页 PDF 招股书解析
→ 标准化财务指标 + 非标隐性风险
→ Financial / Legal / Business / Market / Decision roles
→ Retriever / deterministic Calculation / IPO Heat / Market Regime Skills
→ Evidence-grounded LLM semantics
→ Agent conflict / targeted re-check / verification
→ 基本面 + 市场情绪联合预警
→ 1D / 5D / 20D / 60D 真实表现验证
→ Evidence / page / bbox / Agent trace
→ Final Report / Streamlit / Human Review
```

Submission targets:

```text
关键风险要素抽取准确率       >= 80%
关键 Evidence Recall          >= 85%
Agent / Tool / Evidence trace = 100%
1D / 5D / 20D / 60D outcome   required
3–5 stable real IPO demos      required
```

## Five-person ownership

### A — Tech Lead / Integration / Release

公共 contract、GitHub、CI、E2E、real-case matrix、release、submission。A 不替其他成员重做领域算法；所有公共 Schema / workflow 边界由 A 审核。

### B — LLM Document Intelligence

Legal + Business 真实 LLM、Evidence-grounded semantic extraction、related-party / redemption / litigation / commercialization / core-product 等非标风险和最小 Document benchmark。

### C — Market Intelligence / Market Agent

governed PIT market facts、IPO Heat / Market Regime Skills、MarketContext、LLM market interpretation 与 market provenance；LLM 不生成行情事实。

### D — Quant / Outcome / Evaluation

恢复 frozen PR-F product signal（若原 handoff 可得）、1D/5D/20D/60D outcome、预测结果表、Offline-vs-AI 效果验证和 submission evaluation artifacts；不做大规模新模型搜索。

### E — LLM Final Supervisor / Multi-Agent / Product

LLM Final Supervisor、conflict detection、controlled re-check、Agent Trace、Evidence Viewer、Human Review、最终 Streamlit 与 real demo closure。

Detailed ownership: [`docs/V04_FIVE_PERSON_EXECUTION_PLAN.md`](docs/V04_FIVE_PERSON_EXECUTION_PLAN.md).

## What is already real

```text
Official 2020–2024 IPO universe       438
Production Document-X                 438 / 438, 100 dims
Market-X Core                         438 / 438, 30 positions
5D outcome                            424 / 438
Canonical model-ready                 424 = 354 Dev + 70 Val
Oracle v2 strict                      96 = 77 Dev + 19 Val
HSI Extended readiness                438 / 438
HKEX turnover 20D readiness           438 / 438
production industry return              0 / 438, PIT_BLOCKED
2025 Blind y accessed                 NO
```

Frozen historical reports and `reports/frozen/*.json` remain authoritative for those measured claims.

## LLM responsibilities

```text
Legal       complex rights / litigation / compliance semantics
Business    core product / pipeline / commercialization / revenue semantics
Market      qualitative interpretation of governed PIT facts
Supervisor  bounded synthesis / conflict / uncertainty / re-check decision support
```

Python remains authoritative for exact calculations, schema/identity, PIT checks, feature materialization, hashes, model scoring and reproducibility. Formal `RiskItem` requires Evidence; exact numeric claims require deterministic `Calculation`.

## Model policy

Frozen PR-F remains an auxiliary signal. Current frozen 2024 Full Production ROC-AUC:

```text
M   0.4246
P   0.5000
PM  0.4246
```

The sprint does not retune 2024, invert score direction or start broad model-family search. If the original frozen PR-F runtime/handoff cannot be recovered, `Model Channel = unavailable` and the rest of the governed pipeline continues honestly.

## Remaining competition gates

```text
[ ] rerun 2410.HK after Market missingness fix and close remote AI diagnostics
[ ] complete >=3 stable real IPO E2E cases
[ ] produce 1D / 5D / 20D / 60D evaluation package
[ ] produce Risk extraction / Evidence Recall benchmark artifacts
[ ] confirm real-provider LLM Final Supervisor behavior on final case matrix
[ ] recover original frozen PR-F runtime if available, otherwise keep Model unavailable
[ ] generate final prediction table / reasoning logs / case reports / runbook
[ ] final CI + deterministic + provenance + blind audit
[ ] package submission and bump/release only when Gate passes
```

## Governance

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

2024 is not recycled into a tuning set; 2025 Blind y remains closed until formally authorized.

## Quick start

### Windows PowerShell

```powershell
python -m pip install -e ".[dev,retrieval-research]"
$env:PYTHONPATH = "src"
python -m streamlit run app/streamlit_app.py
```

选择 `v0.4.5 比赛版（AI）` 可运行 competition AI path。Secrets only come from environment variables. Do not commit `.env`, API keys, local absolute paths, licensed raw data or large runtime artifacts.

### Linux / macOS

```bash
python -m pip install -e '.[dev,retrieval-research]'
export PYTHONPATH=src
python -m streamlit run app/streamlit_app.py
```

## Active documentation

1. [`docs/README.md`](docs/README.md)
2. [`docs/ROADMAP.md`](docs/ROADMAP.md)
3. [`docs/V0.4_RELEASE_ACCEPTANCE.md`](docs/V0.4_RELEASE_ACCEPTANCE.md)
4. [`docs/V04_FIVE_PERSON_EXECUTION_PLAN.md`](docs/V04_FIVE_PERSON_EXECUTION_PLAN.md)
5. [`docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md)
6. [`docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md)
7. [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md)
8. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
9. [`docs/DATA_SCHEMA.md`](docs/DATA_SCHEMA.md)
10. [`docs/COMPETITION_DATA_OVERVIEW.md`](docs/COMPETITION_DATA_OVERVIEW.md)
11. [`docs/research/V04_DATA_READINESS.md`](docs/research/V04_DATA_READINESS.md)

Frozen completion reports remain historical records; active docs describe the current competition state and must not rewrite frozen claims.
