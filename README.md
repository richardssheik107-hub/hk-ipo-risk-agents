# HK IPO Risk Agents

Evidence-backed multi-agent risk analysis and market-risk modeling for Hong Kong IPO prospectuses.

系统读取港股招股书 PDF，以共享 Evidence 为基础运行 Financial、Legal、Business 三个专业 Agent，由确定性 Skills、Specialized Verifier 与 Supervisor 生成可审计的 Document Risk；当前 v0.4 主线进一步把这些风险转成 IPO-level features，并连接上市后市场结果。

> 输出中的规则分或未经校准的模型分数不是实际下跌概率，也不构成投资建议。

## Current Status

```text
v0.3.0 Multi-Agent Document Intelligence  = RELEASED / FROZEN
Retriever V3 research                      = MERGED / FROZEN
v0.4 End-to-End Closed Loop                = ACTIVE
```

当前执行策略是 **End-to-End Closed Loop First**：先把完整项目跑通，再回头优化 Retriever、LLM Reranker、Agent 与 Verifier。

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

当前下一项正式工作：**CL-1 / CL-2，冻结现有 Document Intelligence，并批量 materialize 第一版 IPO-level Document Risk Feature Dataset。**

## Current Data Readiness

以当前 v0.4 readiness audit 为基准：

- 官方 2020–2024 IPO universe：438 cases；
- IPO OHLCV outcome coverage：432 / 438；
- authoritative document snapshot pipeline：available；
- full 438-case snapshot materialization：尚未执行；
- HSI、行业 benchmark mapping / history、全市场 turnover：完整 market-X 仍缺；
- model-ready gate：blocked。

详细见 [`docs/research/V04_DATA_READINESS.md`](docs/research/V04_DATA_READINESS.md)。

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
Shared DocumentRetriever → Evidence
      ↓
Financial Agent ─┐
Legal Agent ─────┼→ Specialized Verifier → Document Supervisor
Business Agent ──┘                         ↓
                                    Document Risk Features
                                             ↓
                                      Market Modeling
                                             ↓
                                        Market Agent
                                             ↓
                                      Final Supervisor
                                             ↓
                                   Streamlit / Report / JSON
```

项目保持模块化单体架构。Streamlit 只通过 `IPOAnalysisService` 调用业务能力，不直接调用 Parser、Agent、Provider 或 Predictor。

## Quick Start

完整测试环境需要 Retriever research 依赖：

### Windows PowerShell

```powershell
python -m pip install -e ".[dev,retrieval-research]"
$env:PYTHONPATH = "src"
pytest -q
python scripts/validate_project.py
```

启动稳定 offline 产品：

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
- Retriever: stable production `mock` / `keyword`; Retriever V3 research is frozen/deferred
- Financial Agent: `mock`, `cash_runway`, `v03`
- Legal Agent: `mock`, `disabled`, `v03`
- Business Agent: `mock`, `disabled`, `v03`
- Market Agent: `mock`, `disabled` — v0.4 MVP pending
- Verifier: `rule`, `specialized_v03`
- Supervisor: `rule`, `v03`
- Predictor: `rule_based`, `fault`; market prediction model pending
- LLMProvider: `mock`, `openai_compatible`, `unavailable`
- MarketDataProvider: foundation + governed adapters; production coverage still incomplete
- IPODataProvider: `mock`, `request`, `catalog`
- ReportGenerator: `mock`, `v03`

## Modeling Governance

正式市场建模使用：

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

2025 不得用于特征、阈值或超参数调优。

Retriever 历史 Locked 10 已经正式消费，未来若重启 Retriever 优化必须建立新的 unseen / external / temporal validation set。

## Documentation

当前 `docs/` 已精简为活文档。入口：

- [`docs/README.md`](docs/README.md) — 文档索引与 source-of-truth 顺序
- [`docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md) — 后续总计划
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — 当前进度与阻塞项
- [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md) — 当前产品规格
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — 架构
- [`docs/DATA_SCHEMA.md`](docs/DATA_SCHEMA.md) — 公共 Schema
- [`docs/COMPETITION_DATA_OVERVIEW.md`](docs/COMPETITION_DATA_OVERVIEW.md) — 数据宇宙与年度切分

开发前请先阅读 [`AGENTS.md`](AGENTS.md)。历史阶段性文档不再保留在当前活文档树，可从 Git history / release 查询。