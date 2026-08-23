# HK IPO Risk Agents 后续闭环总计划

> Status snapshot: **2026-08-23**
> Strategy: **End-to-End Closed Loop First, Competition Hardening Second**  
> Active target: **v0.4-MVP → Baseline E2E Freeze → Competition Submission Freeze**  
> PR-A: **COMPLETE / FROZEN**
> PR-B: **COMPLETE / FROZEN ON MAIN**
> PR-C: **COMPLETE / FROZEN**
> PR-D: **COMPLETE / FROZEN**
> PR-E: **COMPLETE / FROZEN**. Current formal milestone: **PR-F — READY / FORMAL RUN NEXT**
> Oracle v2: **COMPLETE / FROZEN / A FINAL SIGN-OFF PASSED**
> 核心原则：先完成可重建、可解释、可审计的完整闭环；baseline E2E 跑通后再逐项补齐赛题专项能力和技术指标；广泛 Retriever / LLM / Agent 优化仍由实证瓶颈决定。

---

## 0. 当前统一状态

仓库此前的独立开发线已经统一回 `main`。当前状态固定为：

- v0.3 Document Intelligence：**RELEASED / FROZEN**；
- Retriever V3 / BM25 / table-aware / LambdaMART / Locked evaluation：**MERGED / FROZEN**；
- Oracle Document Modeling foundations：**MERGED / EVALUATION-ONLY**；
- CL-1 Freeze Current Document Intelligence：**COMPLETE / FROZEN**；
- v0.4 End-to-End Closed Loop：**ACTIVE**；
- PR-A：**COMPLETE / FROZEN**；
- PR-B：**COMPLETE / FROZEN ON MAIN**；
- PR-C：**COMPLETE / FROZEN**；
- PR-D：**COMPLETE / FROZEN**；
- PR-E：**COMPLETE / FROZEN**；
- PR-F：**READY / FORMAL RUN NEXT**；
- Competition Hardening：**PLANNED AFTER PR-H BASELINE E2E**。

当前不再把 Retriever 指标提升、LLM Reranker、Fine-tuning 或 Prompt 优化作为 baseline E2E 的前置条件。

### 0.1 当前 readiness

当前受治理事实口径：

- 官方 2020–2024 IPO universe：438 cases；
- 438 个目标 case 均有本地招股书；
- authoritative snapshots：438 / 438；
- Production Document-X features：438 / 438（`v04_document_features_v1`，100 维）；
- frozen PR-A Oracle v1：60 materialized；按当前 outcome eligibility 为 55 Development / 0 Validation，仅作 immutable historical snapshot；
- Production failures / silent drops：0 / 0；
- Market-X Core：438 / 438（`v04_ipo_market_context_features_v1`，30 positions）；
- PR-B EOD/session-ready：432 / 438；
- PR-C 5D outcome-ready：424 / 438；
- PR-C unavailable：14 = 12 `missing_base_price` + 2 `no_eligible_session`；
- PR-C Development available：354 / 368；
- PR-C Validation available：70 / 70；
- PR-B determinism：438 checked / 0 mismatches / PASS；
- PR-B / PR-C governance：2025 blind y access = NO；
- HSI history：MISSING — Extended；
- authoritative industry benchmark mapping / history：MISSING — Extended；
- total-market turnover：MISSING — Extended；
- `MODEL_READY_DATA_GATE`：PASS；438 upstream → 424 model-ready + 14 exclusions → 354 Development + 70 Validation。

PR-A 已冻结 Document X，PR-B 已冻结 Market-X Core，PR-C 已冻结 Outcome Y；PR-D 已把三者正式合并为 424-row canonical model-ready dataset。PR-E baseline / Oracle diagnostic 已完成并冻结，当前正式任务推进到 PR-F LightGBM + Explainability。

### 0.2 近期严格主线

```text
PR-A  Document + Oracle Materialization & Coverage   COMPLETE / FROZEN
  ↓
PR-B  Market-X Core + Governed EOD Store             COMPLETE / FROZEN
  ↓
PR-C  5D Outcome Policy Freeze                       COMPLETE / FROZEN
  ↓
PR-D  Canonical Model-ready Dataset                  COMPLETE / FROZEN
  ↓
PR-E  Baseline + Oracle Diagnostic                   COMPLETE / FROZEN
  ↓
PR-F  LightGBM + Explainability
  ↓
PR-G  Market Agent + Final Supervisor
  ↓
PR-H  Streamlit Full E2E + Real-case Demo
  ↓
v0.4.3 Baseline E2E Freeze
  ↓
CH-0..CH-6 Competition Hardening
  ↓
v0.4.5 Competition Submission Freeze
```

Competition Hardening 的完整 requirement → component → owner → metric → deliverable → Gate 见 [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md)。

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

一旦正式打开 2025 结果，该数据不再具有 future blind 身份。Competition Hardening 不自动授权打开 2025 y。

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

PR-A 已于 source revision `13e0281f5e65a970caaf1255e56d08597e1ead70` 完成物化，并通过 A6 全量 determinism 验证。其冻结结论见 [`V04_PR_A_COMPLETION_REPORT.md`](V04_PR_A_COMPLETION_REPORT.md)。

它不是训练模型，也不是优化 Agent。它的作用是把已经存在的 Document Intelligence 真正变成后续建模可以使用的一行一个 IPO 的数据资产，并把成功、失败和缺失全部审计清楚。

## 5. PR-A 最终必须回答四个问题

```text
1. 438 个 IPO 中 Production Document X 实际成功多少？
2. 哪些 case 失败、跳过或降级？为什么？
3. Oracle Gold 实际可 materialize 多少 case？
4. Production 与 Oracle 的公平交集有多少 case？
```

该 Gate 已在 PR-A 冻结时满足；本节保留为历史 Gate 定义。

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

该缺口已由：

```text
scripts/run_v04_pr_a.py
```

关闭。它保持薄 orchestration，不承载 Agent/Parser/Retriever 业务逻辑。

## 8. PR-A 执行步骤

### PR-A0 — Freeze execution context

记录 base SHA、config hash、official cohort hash、Document / Oracle Feature Manifest hash、Python/dependency 环境与 output root；禁止把本地绝对路径写入 artifact。

### PR-A1 — canonical orchestration CLI

```text
scripts/run_v04_pr_a.py
```

硬规则：拒绝 2025 blind、冲突 provenance fail closed、结构化 failure report、无 silent skip。

### PR-A2 — deterministic Development pilot

先小规模验证 analysis / snapshot / vector / resume / conflict semantics，不根据 pilot 调风险规则。

### PR-A3 — full 438 Production

全量期间单 case 失败不污染其他 case；partial 不伪装 full success；不自动改 Gold / Agent rule；不读取 2025。

### PR-A4 — Oracle materialization

只覆盖真正有 reviewed expert Gold 的 case，并保留完整 annotation provenance。

### PR-A5 — unified coverage

至少记录 Production / Oracle availability、failure、feature/snapshot hash、manifest hash 与 intersection counts。

### PR-A6 — determinism rerun

第二次运行必须复用一致 provenance，feature / Oracle / coverage 语义内容不漂移。

## 9. PR-A 产物 / 测试 / Gate

大型运行产物、原始 PDF、cache 不提交普通 Git；只提交 orchestration、tests、stable schema/manifest 和必要的小型审计 summary。

完整测试：

```text
pip install -e '.[dev,retrieval-research]'
pytest -q
```

PR-A Gate 已完成：438 official coverage、438/438 Production Document-X、60 Oracle inventory、0 Production failure、0 silent drop、438 determinism/0 mismatch、no 2025 y。

## 10. PR-A 禁止事项

不在 PR-A 中做 Retriever 调参、LLM Reranker、Fine-tuning/LoRA、Agent prompt 重写、新风险定义、target threshold、2024 model tuning、2025 y、LightGBM、Streamlit 重构。

---

# Phase CL-3 / PR-B — Market-X Core + Governed EOD Store

## 11. 原则

PR-A 通过后建立高覆盖、严格 point-in-time、可复现的 `Market-X Core`。缺失 HSI / industry benchmark / market turnover 进入 `Market-X Extended`，不通过错误 proxy 伪造。

任何 Market X 必须满足：

```text
information_timestamp < target IPO listing_timestamp
```

Prior IPO 的 1D / 5D outcome 只有在目标 IPO 上市前已经成为已知历史事实时才允许进入 X。

### PR-B Gate — COMPLETE / FROZEN

- [x] Market-X Core manifest 冻结；
- [x] point-in-time tests 全绿；
- [x] coverage 438 / 438，0 silent drop；
- [x] source/version/checksum 可追踪；
- [x] missing semantics 已审计；
- [x] determinism 438 / 0；
- [x] 2025 blind y 未访问。

完整实测见 [`V04_PR_B_COMPLETION_REPORT.md`](V04_PR_B_COMPLETION_REPORT.md) 与 frozen manifest。

---

# Phase CL-4 / PR-C — Freeze 5D Outcome Policy

## 12. 主目标

第一版核心研究对象为上市后 5 个交易日表现：

```text
raw_return_5d
abnormal_return_5d  # 只有 benchmark 数据和定义可靠时才正式启用
poor_performer_5d
```

Classification threshold 只能由 2020–2023 Development 决定。

必须冻结 trading session、D1/D5 mapping、suspension/no-trade、missing price、benchmark、abnormal return、threshold、exclusion policy 和 target hash。

当前状态：**COMPLETE / FROZEN**。真实 governed materialization、Development-only q25、438 targets、determinism、freeze validator 与 A final sign-off 均已通过。

正式 Gate：

```text
438 coverage
424 available / 14 unavailable
354 Development available / 70 Validation available
12 missing_base_price / 2 no_eligible_session
real Development-only q25
438 target artifacts
438 determinism / 0 mismatch
no 2025 y
freeze manifest
A final sign-off
```

---

# Phase CL-5 / PR-D — Canonical Model-ready Dataset

## 13. 只允许一个 canonical builder

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

1. **Full Production Cohort**；
2. **Oracle Intersection Cohort**。

正式 feature groups：

```text
M   = Market-only
P   = Production Document-only
O   = Oracle Document-only
PM  = Production Document + Market
OM  = Oracle Document + Market
```

PR-D engineering prep、additive bulk-input binding 与正式 materialization 均已完成。Gate 已验证 upstream freezes、PR-A/PR-B/PR-C 的 438-case aggregate identities 与实际 artifacts，并冻结 424 model-ready / 14 exclusions / 354 Development / 70 Validation。Oracle-only identity drift 被显式隔离，Production identity mismatch 仍 fail closed。

---

# Phase CL-6 / PR-E — Baseline + Oracle Diagnostic

## 14. 第一层模型

Regression：Linear / Ridge。  
Classification：Logistic Regression。

预处理只能在 Development fit，再应用到 Validation。Development evaluation 必须 time-aware / forward-chaining，不采用会混合未来年份的随机 CV。

### 核心比较

```text
Document Signal Ceiling ≈ OM - M
Production Increment     ≈ PM - M
Pipeline Gap             ≈ OM - PM
```

### 决策门

**Scenario A — Oracle 也弱**：优先检查 signal / target / sample / Market X，不优先做 Fine-tuning。

**Scenario B — Oracle 强、Production 弱**：证明 Document Pipeline 存在信息损失，才有充分理由重开 Retriever / LLM Reranker / Agent / Verifier 优化。

**Scenario C — Oracle 与 Production 都有效且接近**：优先模型、calibration、Market Agent 和产品闭环。

**Scenario D — Production 看似超过 Oracle**：先排查 cohort、leakage、coverage bias 和 preprocessing。

更多 annotations 已合入，不能沿用旧 55 Development / 0 Validation snapshot 作为当前 ceiling。Versioned Oracle v2 已按 `V04_ORACLE_REFRESH_GOVERNANCE.md` 完成物化、复现与 438-case PR-A/PR-C 上游绑定：98 materialized、96 strict usable（77 Dev / 19 Val）、98 checked / 0 mismatch。A 最终签核已通过；PR-E 已完成正式 baseline + Oracle diagnostic，并冻结在 `V04_PR_E_COMPLETION_REPORT.md` 与 `reports/frozen/v04_pr_e_baseline_manifest.json`。

---

# Phase CL-7 / PR-F — LightGBM + Explainability

只有 PR-E 完整、可复现后正式进入。

第一版非线性模型使用 LightGBM Classifier / Regressor，不进入深度神经网络。

至少输出：

- global feature importance；
- feature-group contribution；
- document vs market contribution；
- single-IPO drivers；
- SHAP summary；
- calibration assessment；
- ablation / error analysis。

严禁 company ID、stock code、document ID、Gold page、Evidence ID、post-listing data、target-derived feature。

未校准模型输出必须表述为 score / prediction，不能无依据称为概率。

---

# Phase CL-8 / PR-G — Market Agent + Final Supervisor

## 15. Market Agent

Market Agent 不是第二个预测器。它只把 frozen model output + market context + Production Document Risks + feature contributions 转成结构化解释。

它不得修改底层模型预测，不得制造 Evidence，不得把未校准 score 表述成真实概率。

## 16. Final Supervisor

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

A-side contract 已确认：MarketContext 不得作为 RiskAgent 注入未验证 RiskItem；Final Supervisor 只能引用已有 risk/evidence；Model prediction 不是 Evidence。

---

# Phase CL-10 / PR-H — Streamlit Full E2E + Real-case Demo

## 17. 最小页面

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

# v0.4.3 Baseline E2E Freeze Gate

只有以下条件同时满足才冻结 baseline E2E：

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

baseline freeze 的目的，是先确保系统真实跑通；它不是比赛工作的终点。

---

# Competition Hardening — PR-H 之后的赛题专项阶段

完整细则见 [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md)。所有赛题要求必须在最终 Submission Freeze 前有明确 owner、artifact 和 metric。

## CH-0 — Competition Scope Lock / Acceptance Matrix

建立 machine-readable + human-readable requirement matrix，覆盖赛题任务 1/2/3、技术指标、业务验证和最终交付物；不存在无人负责的 requirement。

## CH-1 — Multi-horizon Outcome Extension

在 frozen 5D primary target 外增加：

```text
1D
20D
60D
```

统一输出 1D / 5D / 20D / 60D 真实表现验证。5D 保持赛题高权重主目标；新增 horizon 不反向修改 frozen 5D threshold。

## CH-2 — Competition-specific Document Risk Hardening

专项覆盖：

```text
标准化财务指标
cash burn / cash runway
对赌 / 赎回条款
关联交易
客户 / 供应商集中度
核心管线进度
文本粉饰度较高原文切片
```

先建立 reviewed benchmark 测现有系统；达标项只补解释/展示，不达标项做最小范围 enhancement。正式 RiskItem 仍必须 Evidence-first；数值项继续 deterministic Calculation。

## CH-3 — Market Sentiment + Competition Skills

把 PR-G Market Agent 对齐为赛题“市场情绪 Agent”，并正式包装：

```text
LongDocumentRetrievalSkill
ComparableValuationSkill
CashBurnSkill
SentimentHeatSkill
```

市场情绪必须基于受治理 PIT Market-X。若 HSI / industry benchmark / total-market turnover 的 authoritative sources 可得，可加入 Extended；否则明确 missing，不造 proxy。

## CH-4 — Multi-Agent Conflict Resolution / Traceability

赛题要求不同专业 Agent 发生逻辑冲突时有规划、查证和交叉验证能力，因此新增显式 workflow：

```text
Agent findings
→ conflict detector
→ targeted evidence re-check
→ Skill / Verifier challenge
→ supervisor arbitration
→ resolved / needs_review
```

Agent 角色、推理步骤、工具调用和 Evidence 来源追踪率目标 = 100%。系统记录可审计结构化 trace，不要求暴露不可验证的内部自由文本思维链。

## CH-5 — Evidence Screenshot / Human Review / Competition Report

利用现有 `page + bbox` 建立：

```text
Risk → Evidence → PDF page → bbox highlight → screenshot/excerpt card
```

并提供人机复核、reviewer note / decision audit trail。

最终《IPO 风险穿透预警报告》至少包含：

- IPO overview；
- Financial / Legal / Business / non-standard risks；
- Evidence + page / screenshot；
- Market Sentiment；
- 1D / 5D / 20D / 60D view；
- model score + calibration status；
- SHAP / top drivers；
- conflicts / uncertainty / missingness；
- Final Supervisor synthesis；
- provenance / data / model / run versions。

## CH-6 — Competition Evaluation / Case Study / Submission Freeze

正式比赛验收必须测量：

```text
关键风险要素抽取准确率 >= 80%
关键 Evidence 片段召回率 >= 85%
Agent / Tool / Evidence traceability = 100%
逻辑解释有效性 = expert or LLM-assisted rubric assessment
```

业务验证：

```text
1D
5D  # primary / higher-weight
20D
60D
```

最终提交包必须包含：

- 数据处理 / PDF 解析 / 特征 / 预测 / Agent 编排 / 报告完整源码；
- environment / run scripts 或可复用 Skill；
- 可运行 Streamlit / API；
- 公司名称 / 股票代码 / PDF 输入路径；
- 测试集预测结果表；
- 多智能体推理 / tool / verifier logs；
- 关键 Evidence；
- 典型案例报告；
- 3–5 个真实现场 Demo 与批量运行能力。

只有全部 PASS 才标记：

> **v0.4.5 COMPETITION_READY / SUBMISSION FROZEN**。

---

# v0.5 — 由 Oracle Gap 或 Competition Metrics 决定是否重开 Document AI Optimization

不预设 Retriever 一定继续优化。

如果：

```text
Evidence recall < 85%
→ 定向 Retriever / table / evidence targeting 修复

Risk accuracy < 80% 且 Evidence 已正确
→ Agent / Verifier / Skill 语义修复

Oracle strong / Production weak
→ 才有强证据进入更大规模 Retriever / LLM / Agent 研究

Competition metrics 已达标
→ 不为了技术炫技强行 Fine-tuning / LoRA
```

历史 Retriever Locked 10 已消费。任何新 Retriever 研究必须建立新的 unseen / external / temporal holdout。

Fine-tuning 仍不是默认主线；只有积累稳定的 `candidate → expert judgment`、`agent output → verifier correction`、`risk reasoning → reviewed outcome` 后再评估 SFT / LoRA。

---

# 当前执行口令

从 2026-08-23 起，仓库唯一近期执行口令是：

> **PR-A / PR-B / PR-C 已完成并冻结；当前从 PR-D formal materialization 继续严格跑通至 PR-H baseline E2E。PR-H 后再按 Competition Hardening CH-0..CH-6 补齐赛题全部要求。当前不因为赛题专项功能打断 PR-D Gate，也不读取 2025 y。**
