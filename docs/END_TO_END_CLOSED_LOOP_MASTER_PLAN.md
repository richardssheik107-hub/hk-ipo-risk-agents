# HK IPO Risk Agents 后续闭环总计划

> Status snapshot: **2026-08-21**
> Strategy: **End-to-End Closed Loop First**  
> Active target: **v0.4-MVP**  
> PR-A: **COMPLETE / FROZEN**
> PR-B: **COMPLETE / FROZEN**
> Next formal milestone: **PR-C — 5D Outcome Policy Freeze / NOT STARTED**
> 核心原则：先完成可重建、可解释、可审计的完整闭环，再依据实证结果决定是否重开 Retriever / LLM / Agent 优化。

---

## 0. 当前统一状态

仓库此前的独立开发线已经统一回 `main`。当前状态固定为：

- v0.3 Document Intelligence：**RELEASED / FROZEN**；
- Retriever V3 / BM25 / table-aware / LambdaMART / Locked evaluation：**MERGED / FROZEN**；
- Oracle Document Modeling foundations：**MERGED / EVALUATION-ONLY**；
- CL-1 Freeze Current Document Intelligence：**COMPLETE / FROZEN**；
- v0.4 End-to-End Closed Loop：**ACTIVE**；
- PR-A：**COMPLETE / FROZEN**；
- PR-B：**COMPLETE / FROZEN**；
- 下一正式里程碑 PR-C：**NEXT / NOT STARTED**。

当前不再把 Retriever 指标提升、LLM Reranker、Fine-tuning 或 Prompt 优化作为 v0.4 的前置条件。

### 0.1 当前 readiness

以 `docs/research/V04_DATA_READINESS.md` 的最后一次真实审计为准：

- 官方 2020–2024 IPO universe：438 cases；
- IPO OHLCV outcome coverage：432 / 438；
- 438 个目标 case 均有本地招股书；
- authoritative Document Snapshot pipeline：AVAILABLE；
- authoritative snapshots：438 / 438；
- Production Document-X features：438 / 438（`v04_document_features_v1`，100 维）；
- Oracle Document-X：60；`no_reviewed_gold`：378；
- Production failures / silent drops：0 / 0；
- Production Document Feature manifest / vectorizer：AVAILABLE；
- Oracle Document Feature builder：AVAILABLE；
- Oracle Logistic baseline harness：AVAILABLE / WAITING DATASET；
- IPO structure / point-in-time IPO context foundations：AVAILABLE；
- governed IPO EOD filtered-store builder：AVAILABLE；
- Market-X Core：438 / 438，`v04_ipo_market_context_features_v1`，30 positions；
- PR-B determinism：438 checked / 0 mismatches / PASS；
- PR-B 2025 blind y access：NO；
- HSI history：MISSING；
- authoritative industry benchmark mapping / history：MISSING；
- total-market turnover：MISSING；
- `MODEL_READY_DATA_GATE`：BLOCKED。

PR-A 已把 Document pipeline 转成冻结数据资产；PR-B 已把 Market-X Core 转成 438-case、PIT-safe、可重建的冻结数据资产。`MODEL_READY_DATA_GATE` 仍需等待 PR-C target policy 与 PR-D canonical dataset，不因 PR-B 完成而自动开放。

### 0.2 近期严格主线

```text
PR-A  Document + Oracle Materialization & Coverage
  ↓
PR-B  Market-X Core + Governed EOD Store
  ↓
PR-C  5D Outcome Policy Freeze
  ↓
PR-D  Canonical Model-ready Dataset
  ↓
PR-E  Baseline + Oracle Diagnostic
  ↓
PR-F  LightGBM + Explainability
  ↓
PR-G  Market Agent + Final Supervisor
  ↓
PR-H  Streamlit Full E2E + Real-case Demo
  ↓
v0.4 Freeze
```

---

## 1. 两条文档信号路径永久分开

### 1.1 Production Document Path

这是最终产品真正使用的路径：

```text
Prospectus PDF
→ Parser
→ Current Stable Retriever
→ Financial / Legal / Business Agents
→ Deterministic Skills
→ Specialized Verifier
→ Document Supervisor
→ V03DocumentRiskSnapshot
→ Production Document Feature Vector
```

它必须满足：

- 从真实招股书可重新运行；
- 不依赖专家答案；
- 关键结论可回溯到 Evidence / Calculation / page；
- LLM unavailable 时采用明确降级，而不是伪造结果；
- 可进入最终产品。

### 1.2 Oracle Document Path

这是**评测上限 / 错误归因旁路**，不是生产路径：

```text
Reviewed Expert Gold
→ current pass1 + explicit audit overlays
→ EffectiveRiskGoldView
→ Oracle Document Features
```

它只回答：

> 招股书风险信号本身有没有预测价值？如果有，Production Document Pipeline 捕获了多少？

Oracle 永远不允许：

- 接入生产实时或离线分析运行时；
- 代替 Retriever / Agent 生成最终产品结论；
- 使用 2025 blind y；
- 把专家 Gold、Gold page、Evidence ID 或人工答案作为 Production X；
- 因 Oracle 指标更高而把专家信息反向泄漏进 Production Pipeline。

### 1.3 最终诊断框架

```text
Same Market X
Same y
Same time split
Same model family
        │
        ├── Production Document X
        └── Oracle Document X
```

只有在相同 cohort / split / target / preprocessing / model 下比较，Production vs Oracle 的差距才具有解释意义。

---

## 2. 全局数据治理与时间切分

正式切分固定为：

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

### 2.1 Development

2020–2023 可用于数据清洗规则开发、feature policy 开发、classification threshold 选择、模型训练、超参数选择、time-aware CV 和 error analysis。

### 2.2 Validation

2024 用于冻结方案的正式 validation、模型族比较、Production vs Oracle diagnostic 和 failure analysis。不得反复基于 2024 调参后仍将其描述为 untouched validation。

### 2.3 Blind

2025 在 feature policy、target policy、model policy 全部冻结前：

- 可以准备 X；
- 不读取 y；
- 不用于选特征；
- 不用于选阈值；
- 不用于选模型；
- 不用于 Prompt / Retriever / LTR / LLM 调优。

一旦正式打开 2025 结果，该数据不再具有 future blind 身份。

---

# Phase CL-1 — Freeze Current Document Intelligence

## 3. 状态

**COMPLETE / FROZEN**。

当前 v0.3 已作为 v0.4 第一版 Production Document Intelligence 基线。后续 PR-A 不修改 Retriever、专业 Agent、Verifier、Supervisor 的业务语义，仅执行和物化现有结果。

## 4. 冻结边界

```text
CI = GREEN
public schemas = frozen
Mock / offline degradation = preserved
real regression = preserved
Retriever V3 = frozen research baseline
historical Locked 10 = consumed, not reusable as future blind
```

只有阻断闭环的 bug、数据泄漏、错误 provenance 或不可复现问题可以打断冻结。

---

# Phase CL-2 / PR-A — Document + Oracle Materialization & Coverage

PR-A 已于 source revision `13e0281f5e65a970caaf1255e56d08597e1ead70` 完成物化，并通过 A6 全量 determinism 验证。其冻结结论见 [`V04_PR_A_COMPLETION_REPORT.md`](V04_PR_A_COMPLETION_REPORT.md)。PR-B 也已完成并冻结；下一正式里程碑为尚未启动的 PR-C。

它不是训练模型，也不是优化 Agent。它的作用是把已经存在的 Document Intelligence 真正变成后续建模可以使用的一行一个 IPO 的数据资产，并把成功、失败和缺失全部审计清楚。

## 5. PR-A 最终必须回答四个问题

```text
1. 438 个 IPO 中 Production Document X 实际成功多少？
2. 哪些 case 失败、跳过或降级？为什么？
3. Oracle Gold 实际可 materialize 多少 case？
4. Production 与 Oracle 的公平交集有多少 case？
```

在这四个问题没有被一个冻结 manifest 回答之前，不进入 PR-B。

## 6. 现有能力：不要重写

PR-A 必须复用当前已有组件：

### 6.1 Production analysis

现有：

```text
scripts/run_v03_batch_analysis.py
ipo_risk.evaluation.batch.run_batch
configs/v03_offline.yaml
```

`v03_offline` 使用真实 PyMuPDF Parser、真实 Retriever、Financial / Legal / Business Agents，且不要求外部付费 LLM。LLM 不可用能力必须显式降级。

### 6.2 Authoritative snapshot boundary

现有：

```text
src/ipo_risk/modeling/materialization.py
V04DocumentSnapshotMaterializer
```

它只接受：

```text
workflow_version = enhanced_v2
status = completed | partial
use_mock = false
parser = real
retriever = real
financial_agent = real
legal_agent = real
business_agent = real
cohort_year <= 2024
```

它禁止 2025 blind，且同一 case 已存在不同内容或不同 provenance 时 fail closed，不允许静默覆盖。

### 6.3 Production feature vector

现有：

```text
src/ipo_risk/modeling/features.py
DOCUMENT_FEATURE_MANIFEST_V1
vectorize_document_snapshot(...)
```

Feature schema 为 `v04_document_features_v1`。缺失值不会自动变成“安全的 0”。

### 6.4 Oracle

现有：

```text
scripts/index_oracle_gold.py
scripts/build_oracle_document_features.py
src/ipo_risk/modeling/oracle_document.py
```

Oracle 必须保留 `evaluation_only = true` 和完整 pass1 / audit provenance。

## 7. PR-A 实施前缺口（已关闭）

PR-A 启动前，底层组件已经存在，但仓库缺少一个面向 PR-A 的**单一、规范、可恢复、可审计的执行入口**，把下面这些动作完整串起来：

```text
Official 438-case universe
→ Production batch analysis
→ authoritative snapshot validation/materialization
→ Production feature vectorization
→ Oracle inventory/materialization
→ unified coverage table
→ deterministic rerun audit
```

该缺口已由以下薄 orchestration CLI 关闭：

```text
scripts/run_v04_pr_a.py
```

它是一个**薄 orchestration CLI**，不承载 Agent/Parser/Retriever 业务逻辑，只调用既有模块。

如果需要新增内部 helper，可放在 `src/ipo_risk/modeling/`，但不修改受保护公共接口。

## 8. PR-A 执行步骤

### PR-A0 — Freeze execution context

从最新 `main` 创建 PR-A 分支，并记录：

- base commit SHA；
- `v03_offline` config hash；
- official 438-case manifest / bridge hash；
- Document Feature Manifest hash；
- Oracle Feature Manifest hash；
- Python / dependency environment；
- output root。

禁止把本地绝对路径写进 artifact。

### PR-A1 — 实现 canonical orchestration CLI

新增：

```text
scripts/run_v04_pr_a.py
```

建议参数：

```text
--catalog-dir
--data-root
--output-dir
--config          # default configs/v03_offline.yaml
--limit           # pilot only
--case-ids        # diagnostic/pilot only
--resume
--production-only
--oracle-only
```

硬规则：

- 默认只允许 2020–2024；
- 2025 blind 必须 fail closed；
- 默认不覆盖不同 provenance 的既有 artifact；
- `resume` 只复用 hash / provenance 一致的结果；
- 失败必须进入结构化 failure report；
- 不允许 silent skip。

### PR-A2 — 先跑小规模 Development pilot

不要第一行代码写完就直接跑 438 个。

先在 2020–2023 Development 中选一个**确定性、小规模 pilot**，例如按 official manifest 的稳定顺序取前 5 个可用 case：

```text
python scripts/run_v04_pr_a.py \
  --config configs/v03_offline.yaml \
  --data-root <LOCAL_PROSPECTUS_ROOT> \
  --output-dir reports/v04_pr_a_pilot \
  --limit 5
```

Pilot 只检查工程正确性，不根据这 5 个 case 调风险规则。

Pilot 必须验证：

- analysis 可完成；
- authoritative snapshot 可创建；
- feature vector 可生成；
- manifest hash 正确；
- failure report 可读；
- rerun 时成功 case 被 `reused`，而不是产生不同内容；
- 任何 provenance 冲突会报错而不是覆盖。

### PR-A3 — Production full materialization

Pilot + tests 通过后，再运行 2020–2024 全部 438 case：

```text
python scripts/run_v04_pr_a.py \
  --config configs/v03_offline.yaml \
  --data-root <LOCAL_PROSPECTUS_ROOT> \
  --output-dir reports/v04_pr_a \
  --resume
```

现有单 case smoke 在旧审计机器上约 16 秒；438 case 的历史粗略顺序估计约两小时，但这只是容量参考，不能视为 SLA。

全量运行期间：

- 不因单 case 失败停止整个 batch；
- 每个失败 case 记录异常类型和阶段；
- 不自动修 Gold / feature / Agent 规则；
- 不把 partial 结果偷偷标成 full success；
- 不读取 2025。

### PR-A4 — Oracle materialization

使用现有 Oracle 路径：

```text
python scripts/index_oracle_gold.py \
  --output-dir reports/v04_pr_a/oracle_index

python scripts/build_oracle_document_features.py \
  --all-eligible \
  --output-dir reports/v04_pr_a/oracle_features \
  --resume
```

Oracle 不要求覆盖 438。它只覆盖真正存在 reviewed expert Gold 的 case，并保留完整 annotation provenance。

### PR-A5 — Build unified coverage table

PR-A 必须生成一个 authoritative coverage artifact，字段至少包括：

```text
case_id
stock_code
source_year
dataset_split

production_analysis_status
production_snapshot_status
production_document_available
production_failure_stage
production_failure_reason
production_snapshot_hash
production_feature_hash
production_feature_manifest_hash

oracle_document_available
oracle_failure_reason
oracle_feature_hash
oracle_feature_manifest_hash
oracle_effective_annotation_hash
```

同时计算：

```text
Full Production Cohort count
Oracle Eligible count
Oracle Materialized count
Production ∩ Oracle Intersection count
Production failure count by stage/reason
```

### PR-A6 — Determinism rerun

在不修改输入的情况下第二次运行：

- Production successful snapshots 应 `reused`；
- Production feature hash 不变；
- Oracle content hash 不变；
- coverage manifest 的语义内容不变；
- 不允许第二次运行产生“悄悄不同”的结果。

如果 hash 改变，PR-A 不通过，先定位 nondeterminism / provenance 问题。

## 9. PR-A 建议产物

本地 / CI artifact 建议统一在：

```text
reports/v04_pr_a/
  run_manifest.json
  coverage.csv
  coverage.json
  failure_report.csv
  production/
    analysis_results/
    snapshots/
    features/
  oracle_index/
  oracle_features/
  reproducibility_report.json
```

大型运行结果、原始 PDF 和 cache 不提交 Git。仓库只提交：

- orchestration code；
- tests；
- stable schema / manifest definitions（若必要）；
- 小型、可审计的 summary report（若项目规则允许）。

## 10. PR-A 必测内容

至少覆盖：

```text
tests/unit/test_v04_document_materialization.py
existing document feature manifest tests
existing Oracle document tests
new PR-A orchestration tests
```

新增 orchestration tests 至少验证：

- 2025 被拒绝；
- mock / mvp_v1 被拒绝；
- bad component mode 被拒绝；
- resume 只复用相同 provenance；
- conflict fail closed；
- feature order / manifest hash 稳定；
- one case failure 不污染其他 case；
- coverage table 始终包含 official universe 中的每个目标 case。

提交前运行完整：

```text
pip install -e '.[dev,retrieval-research]'
pytest -q
```

## 11. PR-A PASS Gate

只有以下条件全部满足才进入 PR-B：

```text
[x] 438 official cases 全部出现在 coverage report
[x] 每个 case 都有 success / partial / failed / excluded 的明确状态
[x] 每个失败都有 stage + reason（本轮 failure count = 0）
[x] Production successful cases 均有 snapshot hash + feature hash
[x] Production feature manifest 固定
[x] Oracle eligible/materialized/failure 数量可审计
[x] Production ∩ Oracle intersection 被明确计算
[x] rerun hash 稳定
[x] 无 2025 y / post-listing 信息进入 Document X
[x] 没有把 missing 当成 safe zero
[x] 全量 CI 通过
```

**PR-A 不设置“必须 438/438 成功”的人为门槛。**真正的目标是先得到可信 coverage；如果有失败，先分类其是否为输入缺失、pipeline error、明确降级或真实不可用，再决定是否需要一个独立修复 PR。

## 12. PR-A 禁止事项

在 PR-A 中不做：

- Retriever 调参；
- LLM Reranker；
- Fine-tuning / LoRA；
- Agent prompt 重写；
- 新风险定义；
- target threshold 选择；
- 2024 validation 上的模型调参；
- 2025 y；
- LightGBM；
- Streamlit 重构。

---

# Phase CL-3 / PR-B — Market-X Core + Governed EOD Store

## 13. 原则

PR-A 通过后，再建立高覆盖、严格 point-in-time、可复现的 `Market-X Core`。缺失的 HSI / industry benchmark / market turnover 进入 `Market-X Extended`，不通过错误 proxy 伪造。

任何 Market X 必须满足：

```text
information_timestamp < target IPO listing_timestamp
```

Prior IPO 的 1D / 5D outcome 只有在目标 IPO 上市前已经成为已知历史事实时才允许进入 X。

### PR-B Gate

- [x] Market-X Core manifest 冻结；
- [x] point-in-time tests 全绿；
- [x] coverage report 完整（438 / 438，0 silent drop）；
- [x] source/version/checksum 可追踪；
- [x] 单位与 missing semantics 已审计；
- [x] deterministic resume：438 checked / 0 mismatches；
- [x] 2025 blind y 未访问。

冻结 source revision：`dd67a17a5d6cfb246f0cb956c43e94aaddbc58a7`。完整实测见 [`V04_PR_B_COMPLETION_REPORT.md`](V04_PR_B_COMPLETION_REPORT.md) 与 [`../reports/frozen/v04_pr_b_market_x_core_manifest.json`](../reports/frozen/v04_pr_b_market_x_core_manifest.json)。

---

# Phase CL-4 / PR-C — Freeze 5D Outcome Policy

## 14. 主目标

第一版核心研究对象为上市后 5 个交易日表现，同时保留连续目标：

```text
raw_return_5d
abnormal_return_5d  # 只有 benchmark 数据和定义可靠时才正式启用
```

以及分类目标：

```text
poor_performer_5d
```

Classification threshold 只能由 2020–2023 Development 决定。

必须冻结 trading session、D1/D5 mapping、suspension/no-trade、missing price、benchmark、abnormal return、threshold、exclusion policy 和 target hash。

---

# Phase CL-5 / PR-D — Canonical Model-ready Dataset

## 15. 只允许一个 canonical builder

标准记录至少包含：

```text
case_id
stock_code
listing_date
source_year
dataset_split
X_market_core
X_market_extended        # optional
X_production_document
X_oracle_document        # nullable / evaluation-only
y_5d                     # dev / validation; blind separately governed
feature_manifest_hash
target_policy_hash
source_manifest_hash
```

正式 cohort：

1. **Full Production Cohort** — 产品真实覆盖；
2. **Oracle Intersection Cohort** — Production 与 Oracle 同时存在，用于公平诊断。

正式 feature groups：

```text
M   = Market-only
P   = Production Document-only
O   = Oracle Document-only
PM  = Production Document + Market
OM  = Oracle Document + Market
```

---

# Phase CL-6 / PR-E — Baseline + Oracle Diagnostic

## 16. 第一层模型

Regression：Linear / Ridge。  
Classification：Logistic Regression。

预处理只能在 Development fit，再应用到 Validation。

### 核心比较

```text
Document Signal Ceiling ≈ OM - M
Production Increment     ≈ PM - M
Pipeline Gap             ≈ OM - PM
```

### 决策门

**Scenario A — Oracle 也弱**：优先检查 signal / target / sample / Market X，不优先做 Fine-tuning。

**Scenario B — Oracle 强、Production 弱**：证明 Document Pipeline 存在信息损失，v0.5 才有充分理由重开 Retriever / LLM Reranker / Agent / Verifier 优化。

**Scenario C — Oracle 与 Production 都有效且接近**：说明现有 Document Intelligence 已捕获大部分可用信号，优先模型、calibration、Market Agent 和产品闭环。

**Scenario D — Production 看似超过 Oracle**：先排查 cohort、leakage、coverage bias 和 preprocessing，不能直接解释为“AI 优于专家”。

---

# Phase CL-7 / PR-F — LightGBM + Explainability

只有 PR-E 完整后开始。

第一版非线性模型使用 LightGBM Classifier / Regressor，不进入深度神经网络。

至少输出：

- global feature importance；
- feature-group contribution；
- document vs market contribution；
- single-IPO drivers；
- SHAP summary（依赖允许时）。

严禁 company ID、stock code、document ID、Gold page、Evidence ID、post-listing data、target-derived feature。

---

# Phase CL-8 / PR-G — Market Agent + Final Supervisor

## 17. Market Agent

Market Agent 不是第二个预测器。它只把 frozen model output + market context + Production Document Risks + feature contributions 转成结构化解释。

它不得修改底层模型预测，不得制造 Evidence，不得把未校准 score 表述成真实概率。

## 18. Final Supervisor

```text
Financial / Legal / Business
→ Document Supervisor
→ Production Document Risk Vector
→ Prediction Model
→ Market Agent
→ Final Supervisor
→ Final IPO Report
```

Final Supervisor 合并信号、保留冲突、连接 Evidence / Calculation、记录版本和 provenance，不为“结论统一”删除冲突。

---

# Phase CL-10 / PR-H — Streamlit Full E2E + Real-case Demo

## 19. 最小页面

1. IPO Overview；
2. Document Risks；
3. Financial / Legal / Business Agents；
4. Evidence & Calculations；
5. Market Features / Prediction；
6. Final Risk Report；
7. Provenance / Model Version / Failure State。

至少选择 3–5 个真实 IPO，展示完整链：

```text
Prospectus Page
→ Evidence
→ Risk
→ Feature
→ Model Driver
→ Market Assessment
→ Final Report
```

---

# v0.4 Freeze Gate

只有以下条件同时满足才冻结 `v0.4.0-end-to-end-closed-loop`：

- PDF → Final Report 完整运行；
- Production Document X 可重建；
- Oracle diagnostic artifacts 可重建；
- Market X 可重建；
- 5D target 可重建；
- canonical dataset 可重建；
- baseline 与 LightGBM 完整；
- Market Agent / Final Supervisor 完整；
- Streamlit E2E 完整；
- 3–5 real cases demo 通过；
- provenance / versions / failures 可审计；
- 2025 blind 未参与开发调优。

---

# v0.5 — 由 Oracle Gap 决定是否重开 Document AI Optimization

不预设 Retriever 一定继续优化。

只有在 PR-E / PR-F 显示 `Oracle strong / Production weak` 时，才优先重开：

```text
Candidate Generation
→ Frozen LambdaMART LTR-C baseline
→ LLM Reranker V1.1
→ Shared Evidence Pool
→ Financial / Legal / Business Agent VNext
→ Specialized Verifier VNext
→ Supervisor VNext
```

历史 Retriever Locked 10 已消费。任何新 Retriever 研究必须建立新的 unseen / external / temporal holdout。

Fine-tuning 仍不是近期主线；只有积累稳定的 `candidate → expert judgment`、`agent output → verifier correction`、`risk reasoning → reviewed outcome` 后再评估 SFT / LoRA。

---

# 当前执行口令

从 2026-08-19 起，仓库的唯一近期执行口令是：

> **先完成 PR-A。先把 438-case Production Document coverage、Oracle coverage 和两者 intersection 做成可重建的数据资产；在 PR-A PASS 前，不训练市场模型、不重开 Retriever/LLM 优化。**
