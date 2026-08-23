# HK IPO Risk Agents

Evidence-backed multi-agent risk analysis and market-risk modeling for Hong Kong IPO prospectuses.

系统读取港股招股书 PDF，以共享 Evidence 为基础运行 Financial、Legal、Business 三个专业 Agent，由确定性 Skills、Specialized Verifier 与 Supervisor 生成可审计的 Document Risk；v0.4 主线进一步把这些风险转成 IPO-level features，并连接上市后市场结果。baseline E2E 跑通后，再在稳定架构上补齐竞赛要求的多时间窗验证、市场情绪 Agent、冲突查证、证据截图、人机复核和正式指标验收。

> 输出中的规则分或未经校准的模型分数不是实际下跌概率，也不构成投资建议。

## Current Status

```text
v0.3.0 Multi-Agent Document Intelligence  = RELEASED / FROZEN
Retriever V3 research                      = MERGED / FROZEN
Oracle Document Modeling                   = MERGED / EVALUATION-ONLY
PR-A Document + Oracle Materialization      = COMPLETE / FROZEN
PR-B Market-X Core                          = COMPLETE / FROZEN
PR-C 5D Outcome Policy Freeze               = COMPLETE / FROZEN
PR-D Canonical Dataset                      = COMPLETE / FROZEN
PR-E Baseline + Oracle Diagnostic            = READY / FORMAL BASELINE NEXT / NOT STARTED
Oracle v2 refresh                            = COMPLETE / FROZEN / 98 MATERIALIZED / 96 STRICT USABLE
v0.4 End-to-End Closed Loop                = ACTIVE
Competition Hardening                      = PLANNED AFTER PR-H BASELINE E2E
```

当前策略是 **End-to-End Closed Loop First, Competition Hardening Second**：先完成可信、可重建、可解释的完整闭环，再逐项补齐赛题专项能力与指标；更广泛的 Retriever、LLM Reranker、Agent 与 Verifier 研究优化由 Oracle diagnostic 或比赛指标暴露出的真实瓶颈决定。

正式 Gate 顺序：

```text
PR-A  Document + Oracle Materialization & Coverage   COMPLETE / FROZEN
→ PR-B Market-X Core + Governed EOD Store            COMPLETE / FROZEN
→ PR-C 5D Outcome Policy Freeze                      COMPLETE / FROZEN
→ PR-D Canonical Model-ready Dataset                 COMPLETE / FROZEN
→ PR-E Baseline + Oracle Diagnostic                  READY / FORMAL BASELINE NEXT / NOT STARTED
→ PR-F LightGBM + Explainability
→ PR-G Market Agent + Final Supervisor
→ PR-H Streamlit Full E2E + Real-case Demo
→ v0.4.3 Baseline E2E Freeze
→ CH-0..CH-6 Competition Hardening
→ v0.4.5 COMPETITION_READY / Submission Freeze
```

准备性工作可以并行，但正式 Gate / mainline merge 不越级。Competition Hardening 不是当前 PR-C 的前置条件。

## Current Data Readiness

以 2026-08-23 当前 readiness 为准：

- 官方 2020–2024 IPO universe：438 cases；
- local prospectus：438 / 438；
- authoritative Document snapshots：438 / 438；
- Production Document-X：438 / 438，`v04_document_features_v1`，100 维；
- Production failures / silent drops：0 / 0；
- frozen PR-A Oracle v1：60 materialized，当前 Outcome eligibility 下 55 usable（55 Development / 0 Validation），仅为 immutable historical snapshot；Oracle v2 已完成并冻结 98 materialized / 96 strict usable（77 Development / 19 Validation），并通过 438-case PR-A/PR-C 上游绑定与 A 最终签核；
- A6 determinism：438 checked，0 mismatches，PASS；
- PR-B EOD/session-ready：432 / 438；
- Market-X Core：438 / 438 materialized，0 failed，0 silent drops；
- PR-B PIT audit：438 / 438 PASS；
- PR-B determinism：438 checked，0 mismatches，PASS；
- PR-C 5D outcome available：424 / 438；
- PR-C unavailable：14 = 12 `missing_base_price` + 2 `no_eligible_session`；
- PR-C Development available：354 / 368；Validation available：70 / 70；
- HSI history：missing；
- authoritative industry benchmark mapping/history：missing；
- total-market turnover：missing；
- 2025 blind outcome access：NO；
- PR-D canonical dataset：438 upstream → 424 model-ready + 14 explicit exclusions → 354 Development + 70 Validation；formal materialization、resume 与 freeze 已通过。
- PR-E：已解除前置阻塞，但 formal baseline / Oracle diagnostic 尚未开始。

详细真实 readiness 见 [`docs/ROADMAP.md`](docs/ROADMAP.md) 与 [`docs/research/V04_DATA_READINESS.md`](docs/research/V04_DATA_READINESS.md)。

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

Competition Hardening 会在 baseline E2E 之后专项评测并按需增强：现金消耗、对赌/赎回、关联交易、客户/供应商集中度、核心管线进度和“文本粉饰度”原文 diagnostic。

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
Frozen Oracle inventory        60
A6 mismatches                  0
2025 blind accessed            NO
```

冻结记录：

- [`docs/V04_PR_A_COMPLETION_REPORT.md`](docs/V04_PR_A_COMPLETION_REPORT.md)
- [`reports/frozen/v04_pr_a_document_materialization_manifest.json`](reports/frozen/v04_pr_a_document_materialization_manifest.json)

## PR-B Frozen Result

PR-B 明确分为 Core 与 Extended 两层。

### Market-X Core

已完成并冻结：

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

EOD store 按 `official_listed_date.year` 选择 2020–2024 official cohort，而不是使用 document `source_year`；并保留 `OBJECT_ID` source provenance。

```text
official coverage             438 / 438
Core materialized             438 / 438
failed / silent drops         0 / 0
PIT failures                  0
determinism                   438 checked / 0 mismatches / PASS
2025 blind y accessed         NO
```

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

PR-B 冻结记录：

- [`docs/V04_PR_B_COMPLETION_REPORT.md`](docs/V04_PR_B_COMPLETION_REPORT.md)
- [`reports/frozen/v04_pr_b_market_x_core_manifest.json`](reports/frozen/v04_pr_b_market_x_core_manifest.json)
- [`docs/research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`](docs/research/V04_PR_B_INTEGRATION_ACCEPTANCE.md)

## Modeling Governance

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

2025 在 feature / target / model policy 冻结前只能准备 X，不得读取 y，也不得用于阈值、模型、Prompt、Retriever 或 LLM 调优。Competition Hardening 不自动授权打开 2025 y。

正式比较至少包含：

```text
M   Market only
P   Production Document only
O   Oracle Document only
PM  Market + Production
OM  Market + Oracle
```

Oracle 只用于研究上限和错误归因。正式 Development evaluation 必须 time-aware。

## Competition Hardening After Baseline E2E

完整计划见 [`docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md)。最终比赛版本将补齐并验收：

```text
1D / 5D / 20D / 60D 真实表现验证（5D primary）
法务合规 + 财务穿透 + 市场情绪 + 总控决策角色
长文检索 + 同行估值 + 现金消耗 + 情绪热度 Skills
Agent conflict detection → evidence re-check → verifier/arbitration
关键风险抽取准确率 >= 80%
关键 Evidence recall >= 85%
Agent / Tool / Evidence traceability = 100%
PDF page / paragraph / bbox screenshot
human-in-the-loop review
测试集 prediction table / trace logs / Evidence / case reports
可运行 Streamlit / API / batch submission package
```

只有通过 Competition Submission Freeze Gate 才标记 `COMPETITION_READY`。

## Quick Start

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

- Parser: real PyMuPDF + mock compatibility paths
- Retriever: stable production path; Retriever V3 research frozen
- Financial / Legal / Business Agents: v0.3 frozen production baseline
- Verifier / Document Supervisor: v0.3 frozen
- Market Foundation: governed metadata/OHLCV/label contracts available
- Market-X Core: prior-IPO PIT context manifest/vectorization + PR-B orchestration COMPLETE / FROZEN
- Market-X Extended: frozen 20-position contract available; real HSI/industry/turnover sources still missing
- PR-C Outcome: governed materialization complete / frozen
- PR-D Canonical Dataset: complete / frozen
- PR-E Baseline + Oracle Diagnostic: ready / not started
- Predictor: rule-based compatibility path; v0.4 statistical model formal freeze pending
- Oracle Document path: evaluation-only; immutable v1 preserved; versioned v2 complete/frozen and reproducibly bound to frozen upstream inputs
- Streamlit: current Document product path available; full v0.4 E2E pending
- Competition layer: planned after PR-H baseline E2E

## Documentation

Read current guidance in this order:

1. [`AGENTS.md`](AGENTS.md)
2. [`docs/README.md`](docs/README.md)
3. [`docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md)
4. [`docs/V04_FIVE_PERSON_EXECUTION_PLAN.md`](docs/V04_FIVE_PERSON_EXECUTION_PLAN.md)
5. [`docs/ROADMAP.md`](docs/ROADMAP.md)
6. [`docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md)
7. [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md)
8. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
9. [`docs/DATA_SCHEMA.md`](docs/DATA_SCHEMA.md)
10. [`docs/research/V04_DATA_READINESS.md`](docs/research/V04_DATA_READINESS.md)
11. [`docs/V04_PR_C_A_GATE_AUDIT.md`](docs/V04_PR_C_A_GATE_AUDIT.md)
12. [`docs/V04_ROLE_A_INTEGRATION_GATE_HANDOFF.md`](docs/V04_ROLE_A_INTEGRATION_GATE_HANDOFF.md)

`docs/research/V04_PR_B_INTEGRATION_ACCEPTANCE.md` 是冻结的 PR-B 验收契约；`docs/V04_ROLE_A_CROSS_TEAM_PREP.md` 与 `docs/V04_ROLE_A_CODEX_HANDOFF.md` 是历史审计记录，不再属于当前执行入口。
