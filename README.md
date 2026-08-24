# HK IPO Risk Agents

Evidence-backed multi-agent risk analysis and market-risk modeling for Hong Kong IPO prospectuses.

系统以真实招股书 Evidence 为基础运行 Financial / Legal / Business Agents，由 deterministic Skills、Verifier 与 Supervisor 生成可审计 Document Risk；v0.4 再把 Document X 与受治理的 Market X、Outcome Y 连接到正式建模、解释和最终产品闭环。

> 规则分或未经校准的模型分数不是实际下跌概率，也不构成投资建议。

## Current Status — 2026-08-23

```text
v0.3 Document Intelligence              RELEASED / FROZEN
PR-A Document materialization            COMPLETE / FROZEN
PR-B Market-X Core                       COMPLETE / FROZEN
PR-C 5D Outcome                          COMPLETE / FROZEN
PR-D Canonical model-ready dataset       COMPLETE / FROZEN
Oracle v2                                COMPLETE / FROZEN / EVALUATION-ONLY
PR-E Baseline + Oracle Diagnostic        COMPLETE / FROZEN
PR-F LightGBM + Explainability           COMPLETE / FROZEN
PR-G Market Agent + Final Supervisor     CURRENT FORMAL GATE
PR-H Streamlit Full E2E                  WAITING PR-G
Competition Hardening                    STARTS AFTER PR-H BASELINE E2E
```

正式 Gate 顺序：

```text
PR-A → PR-B → PR-C → PR-D → PR-E → PR-F → PR-G → PR-H
                                              ↓
                                  v0.4.3 Baseline E2E Freeze
                                              ↓
                                      CH-0 ... CH-6
                                              ↓
                                  v0.4.5 Competition Freeze
```

准备性工作可以并行，但不能被描述为后续 Gate 已通过，也不能越级进入 `main`。

## What is already real

```text
Official 2020–2024 IPO universe         438
Production analyses                     438 / 438
Authoritative document snapshots        438 / 438
Production Document-X                   438 / 438
Document feature dimension              100
Market-X Core                           438 / 438
5D outcome available                    424 / 438
Explicit outcome exclusions              14
Canonical model-ready cohort            424
Development / Validation                354 / 70
Oracle v2 materialized                   98
Oracle v2 strict usable                  96 = 77 Dev + 19 Val
2025 Blind y accessed                    NO
```

PR-D 已输出正式 M / P / PM matrices；Oracle v2 为独立 evaluation-only 专家旁路。PR-E 与 PR-F 已冻结以下正式比较：

```text
M   Market only
P   Production Document only
O   Oracle Document only
PM  Market + Production
OM  Market + Oracle
```

核心诊断：

```text
Production Increment     = PM - M
Document Signal Ceiling  = OM - M
Pipeline Gap              = OM - PM
```

PR-E 的 2024 Validation 没有显示 Document features 相对 Market-only 的稳健分类增量：Production `PM-M ROC-AUC = -0.0157`，Oracle `OM-M ROC-AUC = -0.0571`。Oracle Validation 仅 19 例，因此结论是信号不稳定，而不是证明“没有招股书信号”。

PR-F 的 frozen LightGBM 结果进一步显示：Full Production `M ROC-AUC = 0.4246`、`P = 0.5000`、`PM = 0.4246`；PM 与 M 预测完全等价，Production Document 100 维特征在该 frozen tree policy 下未被采用。Oracle `OM-M ROC-AUC = -0.0143`，95% paired-bootstrap interval 为 `[-0.3171, 0.2917]`。这些结果是当前数据、特征、目标和固定模型条件下的正式失败/不稳定发现，不得通过反转预测方向、反复查看 2024 后调参或重写口径来“修漂亮”。所有输出仍是未校准模型分数，不是实际概率。

## Post-PR-F strategy

PR-F 的结果不改变 v0.4 的主线顺序。当前策略明确分成两条互补主线：

```text
A. Risk Intelligence / Auditability
   Document risk extraction
   → Evidence / Calculation / page / bbox
   → Verifier / conflict / human review
   → Final Supervisor

B. Market Warning / Predictive Validation
   Market context / sentiment
   + governed model score
   + multi-horizon 1D / 5D / 20D / 60D validation
   → uncertainty-aware warning
```

PR-G / PR-H 先完成稳定产品闭环，不以“把 5D AUC 调高”为 Gate 条件。Competition Hardening 再用直接指标判断该增强哪里：关键风险要素抽取准确率目标 `>= 80%`、关键 Evidence recall 目标 `>= 85%`、Agent / Tool / Evidence traceability 目标 `= 100%`。Document Pipeline 是否需要 Hybrid Retrieval / LLM semantic layer，将由 CH-2 的逐风险 benchmark 和 error attribution 决定，而不是仅由当前 5D AUC 决定。短期 5D 预测的新增研发优先考虑受治理的 Market Sentiment / IPO heat / liquidity context；结构性 Document 风险同时在 20D / 60D 等更长 horizon 上验证。

## Architecture

```text
Prospectus PDF
→ Parser
→ Retriever / Evidence
→ Financial / Legal / Business Agents
→ Deterministic Skills
→ Verifier / Document Supervisor
→ Production Document X
→ Market-X Core (+ optional governed Extended)
→ Outcome / Canonical Dataset
→ Baseline / LightGBM / Explainability
→ Market Agent / Final Supervisor
→ Streamlit / Final Report
```

项目保持模块化单体。Streamlit 只通过 `IPOAnalysisService` / 受控上层 service 调用业务能力；Parser、Agent、Provider、Predictor 不反向依赖 UI。Oracle 永久与 Production 分离。

## Governance

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

Validation 不用于反复调参后继续宣称 untouched；不得因为 AUC `< 0.5` 而在看过 2024 后反转 score 方向并把结果作为正式提升。2025 Blind y 在正式开放前不得用于 feature / threshold / model / prompt / Retriever / LLM 调优。

所有正式 RiskItem 必须有可追溯 Evidence；需要精确数字的结论必须通过 deterministic Calculation。Verifier / Supervisor 不得创造原始 Evidence。

## Quick Start

### Windows PowerShell

```powershell
python -m pip install -e ".[dev,retrieval-research]"
$env:PYTHONPATH = "src"
pytest -q
python scripts/validate_project.py
$env:IPO_RISK_CONFIG = "configs/v03_offline.yaml"
python -m streamlit run app/streamlit_app.py
```

### Linux / macOS

```bash
python -m pip install -e '.[dev,retrieval-research]'
export PYTHONPATH=src
pytest -q
python scripts/validate_project.py
export IPO_RISK_CONFIG=configs/v03_offline.yaml
python -m streamlit run app/streamlit_app.py
```

密钥只允许来自环境变量；不得提交 `.env`、Token、API Key、本地绝对路径或大型 runtime artifacts。

## Documentation

当前文档入口按以下顺序阅读：

1. [`docs/README.md`](docs/README.md) — 文档索引与 source-of-truth 层级
2. [`docs/ROADMAP.md`](docs/ROADMAP.md) — 当前进度和下一 Gate
3. [`docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md) — v0.4 总计划
4. [`docs/V04_FIVE_PERSON_EXECUTION_PLAN.md`](docs/V04_FIVE_PERSON_EXECUTION_PLAN.md) — 五人分工
5. [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md) — 产品范围和成功标准
6. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — 技术架构与依赖边界
7. [`docs/DATA_SCHEMA.md`](docs/DATA_SCHEMA.md) — 公共数据 / modeling contracts
8. [`docs/research/V04_DATA_READINESS.md`](docs/research/V04_DATA_READINESS.md) — 最新真实数据 readiness
9. [`docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md) — PR-H 后比赛强化

完成阶段的事实以对应 completion report + `reports/frozen/*.json` 为准。
