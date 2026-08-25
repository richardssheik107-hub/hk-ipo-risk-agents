# HK IPO Risk Agents

Evidence-backed multi-agent risk analysis and market-warning system for Hong Kong IPO prospectuses.

系统以真实招股书 Evidence 为基础，由 Financial / Legal / Business Agents、LLM semantic reasoning、deterministic Skills、Verifier、governed MarketContext 与 Final Supervisor 形成可审计的港股 IPO 风险分析链。`v0.4.0` 先发布已经可运行、可验证的能力；LLM Market Agent、LLM Final Supervisor、controlled re-check 与完整 competition package 继续作为 `v0.4.5 COMPETITION_READY` Gate。

> 规则分和 `uncalibrated_model_score` 不是实际下跌概率，也不构成投资建议。

## Current status — 2026-08-25

```text
v0.4.0 Competition Preview              RELEASE CANDIDATE
v0.3 Document Intelligence              COMPLETE / FROZEN
PR-A–PR-G                               COMPLETE / FROZEN
PR-H Full E2E                           PARTIAL / BLOCKED
Competition Final Sprint                ACTIVE
Competition target                      v0.4.5 COMPETITION_READY
```

`v0.4.0` 与最终比赛验收分开：前者冻结当前可运行的大版本能力并提供清晰 known limitations；后者只有在赛题硬 Gate 全部满足后才可标记 `COMPETITION_READY`。发布验收见 [`docs/V0.4_RELEASE_ACCEPTANCE.md`](docs/V0.4_RELEASE_ACCEPTANCE.md)。

当前不再按日期拆任务，也不继续展开大规模探索研究。五个人各自拥有一条固定工作流并行推进，A 持续集成到 `main`。

## Competition requirements mapped to the product

赛题核心要求在当前版本中映射为：

```text
数百页 PDF 招股书解析
→ 标准化财务指标 + 非标隐性风险
→ Financial / Legal / Market / Decision Agents
→ Retriever / Cash-runway / IPO-heat / valuation-like Skills
→ Agent conflict / re-check / verification
→ 基本面 + 市场情绪联合预警
→ 1D / 5D / 20D / 60D 真实表现验证
→ Evidence / page / bbox / Agent trace
→ Final Report / Streamlit / Human Review
```

Submission targets:

```text
关键风险要素抽取准确率      >= 80%
关键 Evidence Recall         >= 85%
Agent / Tool / Evidence trace = 100%
1D / 5D / 20D / 60D outcome   required
3–5 stable real IPO demos      required
```

## Five-person ownership

### A — Tech Lead / Integration / Release

负责公共 contract、GitHub、CI、E2E、real-case matrix、release、submission。A 不替其他成员重做领域算法；所有公共 Schema / workflow 边界由 A 审核。

### B — LLM Document Intelligence

负责 Legal + Business 的真实 LLM 能力、Evidence-grounded semantic extraction、related-party / redemption / litigation / commercialization / core-product 等非标风险，以及最小 Document benchmark。

### C — Market Intelligence / Market Agent

负责 governed PIT market facts、IPO Heat / Market Regime Skills、MarketContext、LLM market interpretation 和可用 comparable context；不允许 LLM 生成行情事实。

### D — Quant / Outcome / Evaluation

负责恢复 frozen PR-F product signal、1D/5D/20D/60D outcome、最终预测结果表、最小 Offline-vs-AI 效果验证和 submission evaluation artifacts；不进行大规模新模型搜索。

### E — LLM Final Supervisor / Multi-Agent / Product

负责 LLM Final Supervisor、conflict detection、controlled re-check、Agent Trace、Evidence Viewer、Human Review、最终 Streamlit 与 3–5 stable demo cases。

Detailed ownership: [`docs/V04_FIVE_PERSON_EXECUTION_PLAN.md`](docs/V04_FIVE_PERSON_EXECUTION_PLAN.md).

## Final product path

```text
Prospectus PDF
→ Parser / Retriever / Evidence
→ Financial Agent + deterministic calculations
→ Legal Agent + LLM semantics
→ Business Agent + LLM semantics
→ Verifier
→ governed Market facts + Market Skills + LLM interpretation
→ frozen Model signal if available + Rule signal
→ LLM Final Supervisor
→ conflict → targeted re-check → resolution / uncertainty
→ Final Report / Evidence Viewer / Agent Trace / Human Review
```

上图是 `v0.4.5 COMPETITION_READY` 的目标闭环。当前 `v0.4.0` 已有 governed MarketContext 和 deterministic `V04FinalSupervisor` composition，但正式 runtime 里的 Market Agent 仍未接线，Final Supervisor 也尚未升级为 LLM arbitration。LLM is authoritative only for bounded semantic interpretation. Python remains authoritative for exact calculations, schema/identity, PIT checks, feature materialization, hashes, model scoring and reproducibility.

## What is already real

```text
Official 2020–2024 IPO universe       438
Production Document-X                 438 / 438, 100 dims
Market-X Core                         438 / 438, 30 positions
5D outcome                            424 / 438
Canonical model-ready                 424 = 354 Dev + 70 Val
Oracle v2 strict                      96 = 77 Dev + 19 Val
HSI Extended                          438 / 438
HKEX turnover 20D                     438 / 438
2025 Blind y accessed                 NO
```

Industry return remains `PIT_BLOCKED` until a historically effective company-industry mapping exists.

## LLM responsibilities

```text
Legal      complex rights / litigation / compliance semantics
Business   core product / pipeline / commercialization / revenue semantics
Market     interpretation of governed PIT facts
Supervisor synthesis / conflict / uncertainty / controlled re-check
```

Financial exact math remains deterministic-first.

## Model policy

Frozen PR-F remains an auxiliary signal. Current 2024 Full Production ROC-AUC:

```text
M   0.4246
P   0.5000
PM  0.4246
```

The sprint does not retune 2024, invert score direction or start broad model-family search. If the original frozen PR-F runtime/handoff cannot be recovered, `Model Channel = unavailable` and the rest of the governed pipeline continues honestly.

## Submission definition of done

```text
real LLM Legal / Business semantics active
Market Agent grounded in PIT facts
LLM Final Supervisor active
controlled conflict / re-check path available
1D / 5D / 20D / 60D outcomes generated
>=3 stable real IPO cases
Risk/Evidence benchmark artifact produced
Agent / Tool / Evidence trace complete
Evidence Viewer + Human Review usable
prediction table + reasoning logs + case reports generated
full CI + real-case smoke pass
reproducible runbook + submission package
```

## Governance

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

Formal RiskItem requires Evidence; exact numeric claims require deterministic Calculation. Missing is explicit. 2024 is not recycled into a tuning set; 2025 Blind y remains closed until formally authorized.

## Quick start

### Windows PowerShell

```powershell
python -m pip install -e ".[dev,retrieval-research]"
$env:PYTHONPATH = "src"
python -m streamlit run app/streamlit_app.py
```

### Linux / macOS

```bash
python -m pip install -e '.[dev,retrieval-research]'
export PYTHONPATH=src
python -m streamlit run app/streamlit_app.py
```

Secrets only come from environment variables. Do not commit `.env`, API keys, local absolute paths, licensed raw data or large runtime artifacts.

## Active documentation

1. [`docs/README.md`](docs/README.md)
2. [`docs/ROADMAP.md`](docs/ROADMAP.md)
3. [`docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md)
4. [`docs/V04_FIVE_PERSON_EXECUTION_PLAN.md`](docs/V04_FIVE_PERSON_EXECUTION_PLAN.md)
5. [`docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md)
6. [`docs/V0.4_RELEASE_ACCEPTANCE.md`](docs/V0.4_RELEASE_ACCEPTANCE.md)
7. [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md)
8. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
9. [`docs/DATA_SCHEMA.md`](docs/DATA_SCHEMA.md)
10. [`docs/COMPETITION_DATA_OVERVIEW.md`](docs/COMPETITION_DATA_OVERVIEW.md)
11. [`docs/research/V04_DATA_READINESS.md`](docs/research/V04_DATA_READINESS.md)

Frozen completion reports and `reports/frozen/*.json` remain authoritative for historical claims.
