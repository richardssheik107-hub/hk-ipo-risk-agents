# HK IPO Risk Agents

Evidence-backed multi-agent risk analysis and market-risk modeling for Hong Kong IPO prospectuses.

系统读取港股招股书 PDF，以共享 Evidence 为基础运行 Financial、Legal、Business 三个专业 Agent，由确定性 Skills、Specialized Verifier 与 Supervisor 生成可审计的 Document Risk；当前 v0.4 主线进一步把这些风险转成 IPO-level features，并连接上市后市场结果。

> 输出中的规则分或未经校准的模型分数不是实际下跌概率，也不构成投资建议。

## Current Status

```text
v0.3.0 Multi-Agent Document Intelligence  = RELEASED / FROZEN
Retriever V3 research                      = MERGED / FROZEN
Oracle Document Modeling                   = MERGED / EVALUATION-ONLY
v0.4 End-to-End Closed Loop                = ACTIVE
```

当前执行策略是 **End-to-End Closed Loop First**：先把完整项目跑通，再依据实证结果决定是否回头优化 Retriever、LLM Reranker、Agent 与 Verifier。

当前链路目标：

```text
Prospectus PDF
→ Parser / Stable Retriever
→ Financial / Legal / Business Agents
→ Skills / Verifier / Supervisor
→ IPO-level Document Risk Features
→ Pre-IPO Market Features
→ 5D Outcome
→ Model-ready Dataset
→ Logistic / Linear Baseline
→ LightGBM + Explainability
→ Market Agent
→ Final Supervisor
→ Streamlit Full E2E
```

当前唯一正式工作：

> **PR-A — Document + Oracle Materialization & Coverage**

CL-1 Document Intelligence freeze 已完成。PR-A 首先把现有系统批量转换成可审计的 Production Document X / Oracle X 与统一 coverage，不训练模型、不重新调 Retriever。

## Current Data Readiness

以最近一次真实 v0.4 readiness audit 为基准：

- 官方 2020–2024 IPO universe：438 cases；
- local prospectus：438 / 438；
- IPO OHLCV outcome coverage：432 / 438；
- authoritative document snapshot pipeline：available；
- authoritative snapshots：最近一次 audit 时 0 / 438；
- Production Document feature manifest / vectorizer：available；
- Oracle Document feature builder：available；
- HSI、行业 benchmark mapping / history、全市场 turnover：仍缺；
- model-ready gate：blocked。

`0 / 438` 只表示 full materialization 尚未执行，不表示 Document pipeline 不可运行。详细见 [`docs/research/V04_DATA_READINESS.md`](docs/research/V04_DATA_READINESS.md)。

## Document Risk Scope

### Financial

- cash runway
- continuous loss
- revenue growth
- customer concentration
- supplier concentration

### Legal

- redemption / special shareholder rights
- material litigation & compliance

### Business

- pre-commercial / core-product commercialization risk

精确金融计算必须由 deterministic Python Skill 完成；所有正式风险必须有可回查 Evidence。

## Architecture

```text
Prospectus PDF
      ↓
DocumentParser → DocumentChunk
      ↓
Stable DocumentRetriever → Evidence
      ↓
Financial Agent ─┐
Legal Agent ─────┼→ Specialized Verifier → Document Supervisor
Business Agent ──┘                         ↓
                                    Production Document X
                                             ↓
                               Market X + Outcome Modeling
                                             ↓
                                        Market Agent
                                             ↓
                                      Final Supervisor
                                             ↓
                                   Streamlit / Report / JSON
```

项目保持模块化单体架构。Streamlit 只通过 `IPOAnalysisService` / 受控上层 service 调用业务能力，不直接调用 Parser、Agent、Provider 或 Predictor。

Oracle 路径与 Production 永久分离，只做 research ceiling / error attribution，不进入产品 runtime。

## Quick Start

完整测试环境需要 Retriever research 依赖：

### Windows PowerShell

```powershell
python -m pip install -e ".[dev,retrieval-research]"
$env:PYTHONPATH = "src"
pytest -q
python scripts/validate_project.py
```

启动稳定 offline 文档产品：

```powershell
$env:IPO_RISK_CONFIG = "configs/v03_offline.yaml"
python -m streamlit run app/streamlit_app.py
```

### Linux / macOS

```bash
python -m pip install -e '.[dev,retrieval-research]'
export PYTHONPATH=src
pytest -q
python scripts/validate_project.py
```

```bash
export IPO_RISK_CONFIG=configs/v03_offline.yaml
python -m streamlit run app/streamlit_app.py
```

密钥只允许来自环境变量；不得提交 `.env`、Token、API Key 或本地绝对路径。

## Current Components

- Parser: `mock`, `mock_alt`, `pymupdf`
- Retriever: stable production `mock` / `keyword`; Retriever V3 research frozen/deferred
- Financial Agent: `mock`, `cash_runway`, `v03`
- Legal Agent: `mock`, `disabled`, `v03`
- Business Agent: `mock`, `disabled`, `v03`
- Market Agent: `mock`, `disabled` — v0.4 production implementation pending
- Verifier: `rule`, `specialized_v03`
- Supervisor: `rule`, `v03`
- Predictor: current `rule_based` compatibility path; market model pending
- LLMProvider: `mock`, `openai_compatible`, `unavailable`
- MarketDataProvider: market-foundation contracts + governed adapters
- IPODataProvider: `mock`, `request`, `catalog`
- ReportGenerator: `mock`, `v03`
- Modeling boundary: Production snapshot/features + Oracle foundations + Market dataset foundations

## Modeling Governance

正式市场建模使用：

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

2025 不得用于特征、阈值、模型或超参数调优。

Retriever 历史 Locked 10 已正式消费；未来若重启 Retriever 优化必须建立新的 unseen / external / temporal validation set。

## PR-A Execution

当前第一步严格为：

```text
PR-A0  Freeze execution context / hashes
PR-A1  Implement thin scripts/run_v04_pr_a.py + tests
PR-A2  Run deterministic Development pilot
PR-A3  Materialize 2020–2024 Production snapshots/features
PR-A4  Materialize Oracle inventory/features
PR-A5  Build unified coverage table
PR-A6  Rerun and verify stable hashes
```

PR-A PASS 后才进入 PR-B Market-X Core。

## Documentation

当前 `docs/` 只保留活文档与仍有约束力的冻结研究参考：

- [`docs/README.md`](docs/README.md) — 文档索引与 source-of-truth 顺序
- [`docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md) — 权威后续总计划
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — 当前进度与 Gate
- [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md) — 当前产品规格
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — 当前架构，不保留旧设计历史
- [`docs/DATA_SCHEMA.md`](docs/DATA_SCHEMA.md) — 公共 Schema / v0.4 建模契约
- [`docs/COMPETITION_DATA_OVERVIEW.md`](docs/COMPETITION_DATA_OVERVIEW.md) — 原始数据宇宙与 v0.4 cohort 区分

开发前请先阅读 [`AGENTS.md`](AGENTS.md)。历史阶段性文档通过 Git history / release 查询，不再作为当前执行入口。
