# HK IPO Risk Agents 后续闭环总计划

> Status snapshot: **2026-08-18**  
> Strategy: **End-to-End Closed Loop First**  
> Active target: **v0.4-MVP**  
> 核心原则：先完成可重建、可解释、可审计的完整闭环，再根据实证证据决定是否重开 Retriever / LLM / Agent 优化。

---

## 0. 当前统一状态

仓库当前已经把此前独立开发线统一回 `main`：

- v0.3 Document Intelligence：**RELEASED / FROZEN**；
- Retriever V3 / BM25 / table-aware / LambdaMART / Locked evaluation：**MERGED / FROZEN**；
- Oracle Document Modeling foundations：**MERGED / EVALUATION-ONLY**；
- v0.4 End-to-End Closed Loop：**ACTIVE**。

当前不再把 Retriever 指标提升作为进入市场建模阶段的前置条件。

### 当前 readiness

以 `research/V04_DATA_READINESS.md` 为准：

- 官方 2020–2024 IPO universe：438 cases；
- IPO OHLCV outcome coverage：432 / 438；
- authoritative Document Snapshot pipeline：AVAILABLE；
- latest readiness audit 时已 materialize authoritative snapshots：0 / 438；
- Oracle Document Feature builder：AVAILABLE；
- Oracle Logistic baseline harness：AVAILABLE / WAITING DATASET；
- IPO structure / point-in-time IPO context foundations：AVAILABLE；
- governed IPO EOD filtered-store builder：AVAILABLE；
- HSI history：MISSING；
- authoritative industry benchmark mapping / history：MISSING；
- total-market turnover：MISSING；
- `MODEL_READY_DATA_GATE`：BLOCKED。

因此近期真正的主线是：

```text
Document X materialization
→ minimum Market X closure
→ 5D Outcome freeze
→ canonical model-ready dataset
→ Baseline + Oracle diagnostic
→ LightGBM
→ Market Agent
→ Final Supervisor
→ Full E2E Demo
```

---

## 1. 两条文档信号路径必须永久分开

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
→ Production Document Risk Features
```

它必须满足：

- 可以从真实招股书重新运行；
- 不依赖专家答案；
- 输出可追溯到 Evidence / Calculation / page；
- LLM unavailable 时保持明确降级行为；
- 可进入最终产品。

### 1.2 Oracle Document Path

这是**评测上限 / 错误归因旁路**，不是生产路径：

```text
Reviewed Expert Gold
→ current pass1 + explicit audit overlays
→ EffectiveRiskGoldView
→ Oracle Document Features
```

它只用于回答：

> 招股书风险信号本身有没有预测价值？如果有，Production Document Pipeline 捕获了多少？

Oracle 不允许：

- 接入生产分析运行时；
- 代替 Retriever / Agent 输出最终报告；
- 使用 2025 blind y；
- 因为 Oracle 指标更好而把专家信息偷偷加入 Production X。

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

只有这样，Production vs Oracle 的差距才具有解释意义。

---

## 2. 全局数据治理与时间切分

正式时间切分固定为：

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

### 2.1 Development 可以做什么

2020–2023 可用于：

- 数据清洗规则开发；
- feature policy 开发；
- classification threshold 选择；
- 模型训练；
- 超参数选择；
- rolling / time-aware CV；
- error analysis。

### 2.2 Validation 可以做什么

2024 用于：

- 冻结方案的正式 validation；
- 最终模型族比较；
- Production vs Oracle diagnostic；
- failure analysis。

不要反复根据 2024 结果修改规则后仍把它称为 untouched validation。若确需反复开发，必须优先在 2020–2023 内建立内部时间折叠。

### 2.3 Blind 的硬边界

2025 在 feature policy、target policy、model policy 全部冻结前：

- 可以准备 X；
- 不读取 y；
- 不用于选特征；
- 不用于选阈值；
- 不用于选模型；
- 不用于 Prompt / Retriever / LTR 调优。

一旦正式打开 2025 结果，该数据不再具有 future blind 身份。

---

# Phase CL-1 — Freeze Current Document Intelligence

## 3. 目标

把当前 v0.3 作为第一版生产 Document Intelligence 基线，冻结公共契约和关键回归。

## 4. 必做

- 全量测试保持通过；
- Mock / offline path 保持可运行；
- 已冻结真实案例回归不退化；
- `RiskItem` / Evidence / Calculation / Agent / Verifier / Supervisor 公共语义不被 v0.4 建模代码破坏；
- production failure 必须结构化记录，禁止 silent failure。

## 5. PASS Gate

```text
CI = GREEN
public schemas = unchanged or explicitly versioned
real regression = stable
offline degradation = valid
```

当前状态：**READY**。

---

# Phase CL-2 — Materialize Document Features

CL-2 分成 Production 与 Oracle 两个子阶段，但 Production 是主线，Oracle 只是诊断旁路。

## 6. CL-2A — Production Document Materialization

### 目标

把现有多 Agent 输出真正转成 IPO-level 可建模数据。

### 任务

1. 对 2020–2024 universe 批量运行 authoritative Document Snapshot；
2. 生成每 case 的成功 / 失败 / exclusion 状态；
3. 从 snapshot 生成 deterministic Production Document Feature Vector；
4. 保存：
   - feature schema version；
   - source snapshot version；
   - document identity；
   - provenance；
   - content hash；
   - generation status；
5. 再跑一次，验证相同输入产生相同 feature/hash。

### 产物

建议统一输出：

```text
reports/v04_document_materialization/
  coverage.csv
  failures.csv
  manifest.json
  case_artifacts/

data/modeling/
  production_document_features.*
```

具体路径可以按现有 Repository 规则调整，但必须只有一个 authoritative manifest。

### PASS Gate

- 438 universe 全部进入 coverage report；
- 每个未成功 case 都有 reason；
- 成功 case 可稳定重建；
- feature names / order / types 固定；
- 无 post-listing 信息；
- 不允许把 missing 自动当作“无风险”。

## 7. CL-2B — Oracle Document Materialization

### 目标

为已有 reviewed expert cases 构建同口径的 Oracle X。

### 任务

```text
python scripts/index_oracle_gold.py ...
python scripts/build_oracle_document_features.py --all-eligible ...
```

生成：

- Oracle eligibility inventory；
- pass1 hash；
- audit hash / audit source hash；
- applied audit risks；
- effective annotation hash；
- Oracle feature artifact；
- failure report。

### PASS Gate

- Oracle artifact 明确 `evaluation_only = true`；
- audit precedence 可重建；
- stale audit 状态显式；
- 不含 reasoning text / Evidence text 作为模型特征；
- 不含 outcome / post-listing 信息；
- 不要求 Oracle 覆盖全部 438 cases。

## 8. CL-2 最终 coverage table

必须形成一张统一表：

```text
case_id
source_year
dataset_split
production_document_available
oracle_document_available
production_failure_reason
oracle_failure_reason
production_feature_hash
oracle_feature_hash
```

该表决定后续两个正式 cohort：

1. **Full Production Cohort**：回答产品真正能覆盖多少 IPO；
2. **Oracle Intersection Cohort**：只在 Production 与 Oracle 都存在的 case 上做公平诊断。

当前主任务：**CL-2A + CL-2B**。

---

# Phase CL-3 — Minimum Real Market X Closure

## 9. 原则

第一版不等待所有理想市场源到齐。先建立一个高覆盖、严格 point-in-time、可复现的 `Market-X Core`，再把缺失的 HSI / industry / turnover 做成 `Market-X Extended`。

### 9.1 Market-X Core

优先使用当前可治理的数据：

- IPO structure features；
- point-in-time prior IPO context；
- offer / listing metadata；
- 已可靠获取且在上市前可得的市场状态变量。

最终字段仍以 `V04_PRELISTING_MARKET_FEATURES.md` 的契约为准，不能因为代码已有某个字段就自动把它升级成正式特征。

### 9.2 Market-X Extended

后续补充：

- HSI pre-listing history；
- industry benchmark mapping / history；
- total-market turnover；
- 其他经 provenance 审核通过的市场变量。

Extended 不应阻塞 Core baseline。

## 10. Governed IPO EOD Store

使用现有 EOD filtered-store builder：

- 只抽取目标证券；
- 记录 raw source SHA；
- 记录 bridge SHA；
- source 变化时禁止静默覆写 cache；
- `--rebuild` 必须是显式行为。

## 11. Point-in-time Gate

任何 Market X 必须满足：

```text
information_timestamp < target IPO listing_timestamp
```

特别是 prior IPO outcome context：

- 只有当 prior IPO 的 1D / 5D outcome 已经在目标 IPO 上市前成为已知历史事实，才允许进入 X；
- 目标 IPO 自身及未来 IPO 永远不能进入其 Market X。

## 12. Unit / Missing Audit

在正式建模前必须审计：

- MarketCap；
- FundsRaised；
- NetProceed；
- shares / issue amount；
- price / NTA；
- turnover / amount（若使用）。

先确认单位，再做 ratio / log transformation。

所有 missing 必须同时保留 missing semantics / indicator，不得猜值。

## 13. PASS Gate

- Market-X Core manifest 冻结；
- point-in-time tests 全绿；
- coverage report 完整；
- source/version/checksum 可追踪；
- 不用错误 proxy 填补缺失官方数据；
- coverage threshold 必须在看正式 validation model results 前预先写入实验配置。

当前状态：**PARTIAL**。

---

# Phase CL-4 — Freeze 5D Outcome Policy

## 14. 主目标

第一版核心研究对象为**上市后 5 个交易日表现**。

必须保留连续 target：

```text
raw_return_5d
abnormal_return_5d   # 仅当 benchmark 定义和数据源可靠时作为正式目标
```

同时保留：

```text
1D / 20D / 60D
```

用于 robustness，不让其阻断 v0.4-MVP。

## 15. 为什么连续目标要保留

当前总体样本规模约数百个 IPO，2024 validation 更小。只做二分类会损失信息，因此第一版应同时保留：

- Regression：连续 5D return；
- Classification：poor performer 5D。

二分类用于产品化风险表达，连续变量用于研究稳健性和排序能力判断。

## 16. Classification threshold

阈值只能从 **2020–2023 Development** 决定，并写进 versioned target policy。

禁止：

- 看 2024 后改阈值；
- 看 2025 后改阈值；
- 为了提高 AUC/F1 临时更换标签定义。

## 17. 必须冻结的规则

- trading session convention；
- D1 / D5 的交易日映射；
- suspension / no-trade；
- missing price；
- benchmark convention；
- abnormal return formula；
- classification threshold；
- exclusion policy；
- target version hash。

## 18. PASS Gate

同一 raw data + policy 必须可重复生成完全一致的 y。

---

# Phase CL-5 — Canonical Model-ready Dataset

## 19. 只允许一个 canonical builder

禁止分别为不同实验人工拼接不同 CSV。

标准记录：

```text
case_id
stock_code
listing_date
source_year
dataset_split

X_market_core
X_market_extended   # optional
X_production_document
X_oracle_document   # nullable / evaluation-only

y_5d               # dev / validation only; blind governed separately

feature_manifest_hash
target_policy_hash
source_manifest_hash
```

## 20. 两个正式 cohort

### 20.1 Full Production Cohort

用于回答：

> 当前系统真正能覆盖的 IPO 上，Production Document + Market 是否有效？

### 20.2 Oracle Intersection Cohort

只保留 Production 与 Oracle 同时存在的 cases，用于回答：

> 在完全相同样本上，Production Document Pipeline 捕获了多少专家可见信号？

不要为了 Oracle 实验把主产品 cohort 强行缩小到专家 Gold 子样本。

## 21. 正式 feature groups

至少冻结：

```text
M   = Market-only
P   = Production Document-only
O   = Oracle Document-only
PM  = Production Document + Market
OM  = Oracle Document + Market  # 仅 Oracle intersection
```

所有 matched comparison 必须使用相同：

- row IDs；
- split；
- target；
- model family；
- preprocessing policy。

## 22. PASS Gate

- dataset rebuild hash 稳定；
- manifests 固定；
- no leakage audit 通过；
- 2025 y 不进入 dev artifact；
- group-specific sample manipulation 被禁止；
- Full Production / Oracle Intersection 清晰分离。

---

# Phase CL-6 — Baseline + Oracle Diagnostic

这是 v0.4 最关键的**决策阶段**。

## 23. 第一层模型

### Regression

- Linear Regression；
- Ridge。

### Classification

- Logistic Regression。

预处理必须只在 Development fit，再应用于 Validation。

## 24. 基线比较

### Full Production Cohort

```text
M
P
PM
```

### Oracle Intersection Cohort

```text
M
P
O
PM
OM
```

## 25. 指标

### Classification

- ROC-AUC；
- PR-AUC；
- Precision / Recall / F1；
- LogLoss；
- Brier Score；
- calibration diagnostics。

### Regression

- MAE；
- RMSE；
- Spearman / Rank IC（样本允许时）。

建议同时提供 bootstrap confidence interval 或其他预先定义的不确定性区间，但不能通过反复查看 2024 来调模型。

## 26. Oracle Diagnostic 的核心量

最重要的不是某个单独 AUC，而是：

```text
Document Signal Ceiling ≈ OM - M
Production Increment     ≈ PM - M
Pipeline Gap             ≈ OM - PM
```

如果指标和尺度允许，可报告：

```text
Pipeline Capture Ratio
≈ (PM - M) / (OM - M)
```

但只有当分母具有明确正增量且统计解释合理时才使用，不强行计算。

## 27. CL-6 决策门

### Scenario A — Oracle 也弱

```text
O ≈ M
OM ≈ M
```

结论倾向：

- 文档风险信号本身可能有限；
- target 定义可能不匹配；
- 样本量 / market regime 可能是瓶颈；
- 此时**不应优先投入 Retriever / LLM Fine-tuning**。

下一步：先优化 Market X、target robustness、sample/statistical design。

### Scenario B — Oracle 强，Production 弱

```text
OM >> M
PM ≈ M
```

结论倾向：Production Document Pipeline 存在明显信息损失。

这时才有充分证据在 v0.5 重开：

- Retriever；
- LLM Reranker；
- Agent semantic extraction；
- Verifier。

### Scenario C — Oracle 与 Production 都有效且接近

```text
PM > M
OM ≈ PM
```

说明当前 Document Intelligence 已捕获大部分可用文档信号。

下一步应优先：

- 模型；
- calibration；
- Market Agent；
- E2E 产品化。

### Scenario D — Production 看似超过 Oracle

必须优先检查：

- cohort 是否一致；
- leakage；
- feature definitions；
- Oracle Gold coverage bias；
- preprocessing differences。

不要直接把它解释为 Production “优于专家”。

## 28. PASS Gate

- baseline 可重复运行；
- Production / Oracle 比较完全 matched；
- 2024 validation 没有被用于持续调参；
- 决策门结论有完整表格和 failure analysis。

---

# Phase CL-7 — LightGBM + Explainability

## 29. 何时开始

只有 CL-6 完整后再进入。

## 30. 正式模型

第一版非线性模型：

```text
LightGBM Classifier / Regressor
```

不进入深度神经网络。

## 31. Development 内部验证

主方法优先使用 time-aware / rolling folds，不把跨年份 IPO 完全随机 IID 切分当作唯一证据。

2024 仍作为冻结 validation。

## 32. 必做比较

```text
Market-only
Production Document-only
Production Combined
```

Oracle intersection 再增加 Oracle variants，用于诊断 ceiling，不用于生产选择。

## 33. Explainability

至少输出：

- global feature importance；
- feature-group contribution；
- document vs market contribution；
- 单 IPO driver；
- SHAP summary（依赖允许时）。

## 34. 严禁特征

- company ID 作为预测信号；
- stock code；
- document ID；
- Gold page / Evidence ID；
- post-listing data；
- target-derived features；
- 未来可得信息。

## 35. PASS Gate

- 对 baseline 的改善可重复；
- 无 leakage；
- feature importance 不依赖身份类伪特征；
- model artifact / feature manifest / training split / seed 全部版本化。

---

# Phase CL-8 — Market Agent MVP

## 36. 定位

Market Agent **不是第二个预测模型**。

它负责把：

```text
Frozen Model Output
+ Pre-IPO Market Context
+ Production Document Risks
+ Feature Contributions
```

转换为结构化解释。

## 37. 输出建议

```text
market_risk_level
model_score
model_version
feature_version
main_market_drivers
main_document_drivers
uncertainty_notes
supporting_feature_ids
```

## 38. 约束

- 不修改底层模型预测；
- 不把未经校准 score 说成真实概率；
- 不创造 Evidence；
- 文档 driver 必须可回溯 RiskItem / Evidence；
- 市场 driver 必须可回溯模型输入；
- LLM 不可用时必须有 deterministic / structured fallback。

---

# Phase CL-9 — Final Supervisor

## 39. 目标

形成真正统一的 IPO 风险结论：

```text
Financial / Legal / Business
→ Document Supervisor
→ Production Document Risk Vector
→ Prediction Model
→ Market Agent
→ Final Supervisor
→ Final IPO Report
```

## 40. Final Supervisor 职责

- 合并 Document 与 Market 信号；
- 显式保留冲突；
- 提取主要风险 driver；
- 连接 Evidence / Calculation；
- 记录 model / feature / analysis version；
- 生成可审计最终结论。

## 41. 不允许

- 为了“结论统一”删除冲突；
- 无 Evidence 发明事实；
- 覆盖 deterministic calculation；
- LLM 自行改模型分数；
- 把规则分 / raw score 伪装成真实概率。

---

# Phase CL-10 — Streamlit Full E2E

## 42. 最小页面

1. IPO Overview；
2. Document Risks；
3. Financial / Legal / Business Agents；
4. Evidence & Calculations；
5. Market Features / Prediction；
6. Final Risk Report；
7. Provenance / Model Version / Failure State。

## 43. Demo cases

至少 3–5 个真实 IPO：

- 不同年份；
- 不同风险结构；
- 至少一个较弱市场表现；
- 至少一个较强市场表现；
- 每个 case 都能展示完整链：

```text
Prospectus Page
→ Evidence
→ Risk
→ Feature
→ Model Driver
→ Market Assessment
→ Final Report
```

## 44. 产品 Gate

- API/LLM unavailable 时仍能展示受控降级；
- 不暴露 secrets；
- latency / fallback / error 可记录；
- 报告中的所有关键结论可回溯。

---

# v0.4 Freeze Gate

## 45. v0.4.0-end-to-end-closed-loop

只有以下条件同时满足才冻结：

- PDF → Final Report 完整运行；
- Production Document X 可重建；
- Oracle diagnostic artifacts 可重建；
- Market X 可重建；
- 5D target 可重建；
- canonical model-ready dataset 可重建；
- baseline 完整；
- LightGBM 完整；
- Market Agent 完整；
- Final Supervisor 完整；
- Streamlit E2E 完整；
- 3–5 real cases demo 通过；
- provenance / versions / failures 可审计；
- 2025 blind 没有参与开发调优。

---

# v0.5 — 由 Oracle Gap 决定是否重开 Document AI Optimization

## 46. 不预设 Retriever 一定要继续优化

v0.5 的投入方向由 CL-6 / CL-7 的 Oracle diagnostic 决定。

如果 `Oracle strong / Production weak`，才正式重开 Document Intelligence optimization。

## 47. 若重开，推荐顺序

```text
Candidate Generation
(V1 / V2.1 / BM25 / Table)
        ↓
Frozen LambdaMART LTR-C baseline
        ↓
LLM Reranker V1.1
        ↓
Shared Evidence Pool
        ↓
Financial / Legal / Business Agent VNext
        ↓
Specialized Verifier VNext
        ↓
Supervisor
```

### LLM Reranker V1.1

重点不是“让 LLM 重新搜索整份 PDF”，而是：

- Top-N frozen candidate input；
- deterministic candidate IDs；
- small micro-batches；
- candidate-level validation；
- partial recovery；
- per-candidate fallback；
- judgment cache；
- sanitized reliability telemetry。

### 新 blind requirement

历史 Retriever Locked 10 已消费。

v0.5 必须建立新的：

```text
Development
→ new unseen / external / temporal holdout
→ one frozen evaluation
```

不能继续在旧 Locked 10 上调参。

---

# Fine-tuning — 暂不作为近期主线

## 48. 为什么现在不做 SFT / LoRA

目前更高价值的问题仍然是：

1. 完整闭环能不能运行；
2. Document Risk 有没有增量预测信号；
3. Production Pipeline 与 Oracle Ceiling 差多少；
4. 哪一层才是真正瓶颈。

在这些问题没有回答前，Fine-tuning 很容易变成高成本但不可归因的优化。

## 49. 何时再评估 Fine-tuning

至少积累稳定的：

```text
candidate → expert judgment
agent output → verifier correction
risk reasoning → reviewed outcome
```

再评估 SFT / LoRA 是否值得。

---

# v0.6 — Formal Evaluation / Ablation

## 50. Document Intelligence Ablation

```text
Stable Production Baseline
→ Improved Candidate Generation
→ LTR
→ LLM Reranker
→ Agent VNext
→ Semantic Verifier
→ Full Document System
```

同时报告与 Oracle ceiling 的距离。

## 51. Market Modeling Ablation

```text
Market-only
Production Document-only
Production Combined
Oracle Document-only      # diagnostic
Oracle Combined           # diagnostic
```

## 52. 最终统一指标

至少覆盖：

- Retrieval Recall / MRR / NDCG；
- Evidence grounding；
- Risk extraction；
- unsupported claim rate；
- market prediction；
- calibration；
- latency；
- token / API cost；
- fallback rate；
- reproducibility；
- end-to-end success rate。

---

# 53. 从现在开始的严格 PR / Milestone 顺序

为了避免再次出现多分支长期分叉，建议后续主线最多按以下连续里程碑推进：

```text
PR-A  Document + Oracle Materialization & Coverage
      ↓
PR-B  Market-X Core + Governed EOD Store
      ↓
PR-C  5D Outcome Policy Freeze
      ↓
PR-D  Canonical Model-ready Dataset
      ↓
PR-E  Baseline + Oracle Diagnostic Report
      ↓
PR-F  LightGBM + Explainability
      ↓
PR-G  Market Agent + Final Supervisor
      ↓
PR-H  Streamlit Full E2E + Real-case Demo
      ↓
v0.4 Freeze
```

每个 PR 必须：

- 从最新 `main` 创建；
- 范围单一；
- CI 全绿；
- 生成 manifest / report 的任务必须可重复；
- 不把临时实验文档永久堆进 `docs/`；
- merge 后下一阶段再开新分支。

---

# 54. 当前立刻开始的任务

现在正式进入：

> **PR-A：Document + Oracle Materialization & Coverage**

第一阶段不要训练复杂模型，也不要接新的 LLM。

需要先回答四个最基本的问题：

```text
1. 438 个 IPO 中 Production Document X 实际成功多少？
2. 哪些失败，为什么？
3. Oracle Gold 实际覆盖多少？
4. Production 与 Oracle 的公平交集有多少？
```

PR-A 完成并冻结 coverage / feature manifests 后，立即进入 PR-B Market-X Core；随后按 PR-C → PR-D → PR-E 推进。

**在 PR-E 的 Oracle diagnostic 出来之前，不再以主线身份重启 Retriever / LLM Reranker / Fine-tuning。**
