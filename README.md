# HK IPO Risk Agents

Evidence-backed multi-agent risk analysis and market-risk modeling for Hong Kong IPO prospectuses.

系统读取港股招股书 PDF，以共享 Evidence 为基础运行 Financial、Legal、Business 三个专业 Agent，由确定性 Skills、Specialized Verifier 与 Supervisor 生成可审计的 Document Risk；v0.4 主线进一步把这些风险转成 IPO-level features，并连接上市后市场结果。

> 输出中的规则分或未经校准的模型分数不是实际下跌概率，也不构成投资建议。

## Current Status

```text
v0.3.0 Multi-Agent Document Intelligence  = RELEASED / FROZEN
Retriever V3 research                      = MERGED / FROZEN
Oracle Document Modeling                   = MERGED / EVALUATION-ONLY
PR-A Document + Oracle Materialization      = COMPLETE / FROZEN
v0.4 End-to-End Closed Loop                = ACTIVE
PR-B Market-X Core                          = IMPLEMENTED ON BRANCH / LOCAL GATE EVIDENCE PENDING
```

当前策略是 **End-to-End Closed Loop First**：先完成可信、可重建、可解释的完整闭环，再依据实证结果决定是否回到 Retriever、LLM Reranker、Agent 与 Verifier 的研究优化。

正式 Gate 顺序：

```text
PR-A  Document + Oracle Materialization & Coverage   COMPLETE / FROZEN
→ PR-B Market-X Core + Governed EOD Store            CURRENT
→ PR-C 5D Outcome Policy Freeze
→ PR-D Canonical Model-ready Dataset
→ PR-E Baseline + Oracle Diagnostic
→ PR-F LightGBM + Explainability
→ PR-G Market Agent + Final Supervisor
→ PR-H Streamlit Full E2E + Real-case Demo
→ v0.4 Freeze
```

准备性工作可以并行，但正式 Gate / mainline merge 不越级。

## Current Data Readiness

以 2026-08-21 PR-A A6 与最近市场数据审计为准：

- 官方 2020–2024 IPO universe：438 cases；
- local prospectus：438 / 438；
- authoritative Document snapshots：438 / 438；
- Production Document-X：438 / 438，`v04_document_features_v1`，100 维；
- Production failures / silent drops：0 / 0；
- Oracle Document-X：60；`no_reviewed_gold`：378；
- Production ∩ Oracle：60；
- A6 determinism：438 checked，0 mismatches，PASS；
- IPO OHLCV：432 / 438；
- HSI history：missing；
- authoritative industry benchmark mapping/history：missing；
- total-market turnover：missing；
- 2025 blind outcome access：NO；
- full model-ready gate：仍 blocked。

详细真实 readiness 见 [`docs/research/V04_DATA_READINESS.md`](docs/research/V04_DATA_READINESS.md)。PR-B 的实际 Core coverage 只有在本地全量 materialization 后才能更新，当前不提前虚构数字。

## Architecture

```text
Prospectus PDF
      ↓
Parser / Stable Retriever
      ↓
Financial / Legal / Business Agents
      ↓
Skills / Verifier / Document Supervisor
      ↓
Production Document X (100)
      ↓
Market-X Core (prior-IPO PIT context, 30 positions)
      +
Market-X Extended (HSI / industry / turnover contract, 20 positions when governed sources exist)
      ↓
5D Outcome / Modeling Dataset
      ↓
Baseline / LightGBM / Explainability
      ↓
Market Agent + Final Supervisor
      ↓
Streamlit / Report / JSON
```

项目保持模块化单体。Streamlit 只通过 `IPOAnalysisService` / 受控上层 service 调用业务能力，不直接调用 Parser、Agent、Provider 或 Predictor。

Oracle 路径与 Production 永久分离，只做 evaluation ceiling / error attribution，不进入产品 runtime。

## Document Risk Scope

Financial：`cash_runway`、`continuous_loss`、`revenue_growth`、`customer_concentration`、`supplier_concentration`。

Legal：`redemption_rights`、`material_litigation_compliance`。

Business：`precommercial_product`。

所有正式风险必须可回查 Evidence；精确金融计算必须由 deterministic Python Skill 完成。

## PR-A Frozen Result

PR-A 已把 Document capability 转成正式数据资产：

```text
Official cases                 438
Production analysis            438 / 438
Authoritative snapshots        438 / 438
Production Document-X          438 / 438
Document feature dimension     100
Production failures            0
Silent drops                   0
Oracle materialized            60
No reviewed Gold               378
Production ∩ Oracle            60
A6 mismatches                  0
2025 blind accessed            NO
```

冻结记录：

- [`docs/V04_PR_A_COMPLETION_REPORT.md`](docs/V04_PR_A_COMPLETION_REPORT.md)
- [`reports/frozen/v04_pr_a_document_materialization_manifest.json`](reports/frozen/v04_pr_a_document_materialization_manifest.json)

## Current PR-B Boundary

PR-B 现在明确分为 Core 与 Extended 两层。

### Market-X Core

已在当前分支实现：

```text
schema:  v04_ipo_market_context_features_v1
policy:  ipo_market_context_policy_v1
15 raw prior-IPO context features
+ 15 adjacent missing indicators
= 30 positions
```

Core 只使用当前已治理的信息：authoritative IPO metadata、prior-IPO offer/context facts、governed IPO EOD，以及在目标 IPO 上市前已经成为历史事实的 prior IPO 1D/5D outcomes。

Canonical entry points:

```text
scripts/build_v04_ipo_eod_store.py
scripts/run_v04_pr_b.py
```

EOD store 已改为按 `official_listed_date.year` 选择 2020–2024 official cohort，而不是使用 document `source_year`；并保留 `OBJECT_ID` source provenance。

### Market-X Extended

现有冻结 contract 保持不变：

```text
v04_prelisting_market_features_v1
v04_market_features_v1
10 raw + 10 missing indicators = 20 positions
```

当前真实来源缺口：

```text
HSI daily history
industry → benchmark authoritative mapping
industry-index histories
HK total-market turnover
```

这些是 Extended gaps，不是 Core 通过所必须伪造的输入。禁止使用不等价 proxy、假 benchmark row 或 neutral zero 补齐。

PR-B Gate 详细标准：

- [`docs/research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`](docs/research/V04_PR_B_INTEGRATION_ACCEPTANCE.md)
- [`docs/V04_ROLE_A_CODEX_HANDOFF.md`](docs/V04_ROLE_A_CODEX_HANDOFF.md)

## Modeling Governance

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

2025 在 feature / target / model policy 冻结前只能准备 X，不得读取 y，也不得用于阈值、模型、Prompt、Retriever 或 LLM 调优。

正式比较至少包含：

```text
M   Market only
P   Production Document only
O   Oracle Document only
PM  Market + Production
OM  Market + Oracle
```

Oracle 只用于研究上限和错误归因。

## Quick Start

### Windows PowerShell

```powershell
python -m pip install -e ".[dev,retrieval-research]"
$env:PYTHONPATH = "src"
pytest -q
python scripts/validate_project.py
```

PR-B Core pilot：

```powershell
python scripts/run_v04_pr_b.py --catalog-dir data/catalog --data-root <LOCAL_MARKET_ROOT> --output-dir reports/v04_pr_b_pilot --limit 5
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
python scripts/run_v04_pr_b.py \
  --catalog-dir data/catalog \
  --data-root <LOCAL_MARKET_ROOT> \
  --output-dir reports/v04_pr_b_pilot \
  --limit 5
```

```bash
export IPO_RISK_CONFIG=configs/v03_offline.yaml
python -m streamlit run app/streamlit_app.py
```

密钥只允许来自环境变量；不得提交 `.env`、Token、API Key 或本地绝对路径。

## Current Components

- Parser: real PyMuPDF + mock compatibility paths
- Retriever: stable production path; Retriever V3 research frozen
- Financial / Legal / Business Agents: v0.3 frozen production baseline
- Verifier / Document Supervisor: v0.3 frozen
- Market Foundation: governed metadata/OHLCV/label contracts available
- Market-X Core: prior-IPO PIT context manifest/vectorization + PR-B orchestration implemented on current branch
- Market-X Extended: frozen 20-position contract available; real HSI/industry/turnover sources still missing
- Predictor: rule-based compatibility path; v0.4 statistical model pending
- Oracle Document path: evaluation-only, materialized for 60 cases
- Streamlit: current Document product path available; full v0.4 E2E pending

## Documentation

Read current guidance in this order:

1. [`AGENTS.md`](AGENTS.md)
2. [`docs/README.md`](docs/README.md)
3. [`docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md)
4. [`docs/V04_FIVE_PERSON_EXECUTION_PLAN.md`](docs/V04_FIVE_PERSON_EXECUTION_PLAN.md)
5. [`docs/V04_ROLE_A_CROSS_TEAM_PREP.md`](docs/V04_ROLE_A_CROSS_TEAM_PREP.md)
6. [`docs/research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`](docs/research/V04_PR_B_INTEGRATION_ACCEPTANCE.md)
7. [`docs/V04_ROLE_A_CODEX_HANDOFF.md`](docs/V04_ROLE_A_CODEX_HANDOFF.md)
8. [`docs/ROADMAP.md`](docs/ROADMAP.md)

Historical stage documents remain in Git history/releases rather than the active reading path.
