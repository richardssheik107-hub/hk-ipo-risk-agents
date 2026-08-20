# 公共数据 Schema 与 v0.4 建模契约

> Status snapshot: **2026-08-20**

本文件描述当前仍有效的跨模块数据边界。**代码中的 Pydantic Schema 是最终权威实现**；本文用于解释语义，不应替代源码做字段推断。

## 1. 设计原则

所有跨模块数据必须通过明确、可版本化的 Pydantic 模型传递。

原则：

1. 字段含义与类型明确；
2. 支持校验、序列化和版本管理；
3. 新字段优先保持向后兼容；
4. 不同模块不得自行创造含义相近但不兼容的 dict；
5. 缺失值必须有明确语义，不能自动当作“安全 / 0”；
6. provenance、source version、feature version、model version 必须可追踪。

## 2. DocumentChunk

表示 PDF 解析后的文档片段，核心字段包括：

- `document_id`
- `chunk_id`
- `page`
- `section`
- `text`
- `block_type`
- `bbox`
- `metadata`

`page` 必须保留真实 PDF 页码；`bbox` 可为空。Parser 统一返回：

```text
list[DocumentChunk]
```

## 3. Evidence

表示支持风险结论的证据，核心语义包括：

- 来源 document / chunk / page / section；
- 原文 `text`；
- 可选 `bbox`；
- `source_type`；
- relevance / metadata。

正式 RiskItem 所依赖的 Evidence 必须可回到原始招股书或受控数据源，不允许虚构页码、文本或来源。

## 4. Calculation

表示确定性计算过程，必须能够审计：

```text
skill_name / skill_version
inputs
formula
result
unit
evidence_ids
success / error
```

精确金融计算由 deterministic Skill 完成，不能把 LLM 自然语言计算直接当作正式 Calculation。

## 5. RiskItem

RiskItem 是专业 Agent 的统一公共风险边界。核心语义包括：

- `risk_id`
- `risk_code`
- `category`
- `risk_type`
- `level`
- `score`
- `conclusion`
- `evidence`
- `calculation`
- `agent_name`
- `confidence`
- `verification_status`
- `verification_notes`
- `created_at`
- `metadata`

专业 Agent 统一返回：

```text
list[RiskItem]
```

风险是否必须有 Evidence / Calculation 由 domain 风险注册表决定，不通过解析 conclusion 文本来猜。

## 6. Verification / Supervision

当前正式 verification 状态包括：

```text
verified
pending
rejected
needs_review
```

`VerificationResult` 负责结构化划分 verified / pending / rejected；`SupervisionResult` 负责最终去重、冲突、组合发现和摘要，同时保持 `IPOAnalysisResult` 对外兼容。

Verifier / Supervisor 不得创造新的原始 Evidence。

## 7. AgentLog 与 AnalysisError

Agent / Skill / Workflow 的失败必须结构化记录，而不是静默吞掉。

`AgentLog` 用于记录执行步骤、组件、状态、摘要、Evidence IDs、错误和耗时；`AnalysisError` 用于记录 stage、component、code、message、recoverable、context、occurred_at 等失败信息。

日志不得保存 API Key / Token 等敏感信息。

## 8. PredictionResult

`PredictionResult` 是 Predictor 的统一公共返回类型。

当前 `RuleBasedPredictor` 只提供兼容 / 对照风险评分；其分数不得描述为经过校准的真实概率。

v0.4 的 Logistic / Linear / LightGBM 市场模型在正式接入公共预测输出前，必须先完成：

```text
PR-A Document X
→ PR-B Market X
→ PR-C target policy
→ PR-D canonical model-ready dataset
→ PR-E baseline diagnostic
```

未经校准的任何 score 仍不能表述为真实下跌概率。

## 9. MarketSnapshot：legacy runtime compatibility

现有 `MarketSnapshot` 属于旧 runtime / compatibility 输入边界，不能与 v0.4 建模的 `PreListingMarketFeatureSnapshot` 混为一谈。

特别是：

- legacy `sentiment_score` 不属于 `v04_market_features_v1`；
- 单股成交额不能替代 total-market turnover；
- legacy snapshot 缺失不允许被偷偷补成 market-neutral 0。

v0.4 正式 Market X 以 `PreListingMarketFeatureSnapshot` + `MarketFeatureManifest` 为准。

## 10. IPOAnalysisRequest / IPOAnalysisResult

`IPOAnalysisRequest` 是一次分析请求；`IPOAnalysisResult` 是 Document Runtime 的最终公共结果。

`IPOAnalysisResult` 保留：

- case / company / stock / workflow / schema identity；
- verified / pending / rejected risks；
- prediction（可为空）；
- agent logs；
- report sections（可为空）；
- status；
- structured errors；
- timestamps / metadata。

`status=partial` 是合法状态：表示部分组件失败但已有结果仍可返回。

## 11. V03DocumentRiskSnapshot

`V03DocumentRiskSnapshot` 是 v0.4 Document Modeling 的权威中间层，只从最终 `IPOAnalysisResult` 构造。

它为 8 个 canonical risk 保留固定位置及显式状态：

```text
verified
pending
needs_review
rejected
not_emitted
unavailable
```

同时保留：

- case / document / stock identity；
- cohort / listing date / split；
- workflow / schema version；
- document pipeline version / commit；
- source analysis identity / status；
- feature schema version；
- eligibility / provenance。

不同 provenance 的 artifact 不允许静默覆盖。

## 12. Production Document Feature Contract

`DocumentFeatureManifest` 当前版本：

```text
v04_document_features_v1
```

冻结 100 个有序数值位置：

- 每个风险 11 项，共 88 项；
- aggregate 12 项；
- 总计 100 项。

缺失语义：

- 未 verified 的 score / level 保留 null；
- 每类状态有独立 indicator；
- `missing` 是显式特征；
- Evidence count 为 0 只表示没有附着 Evidence，不表示风险为 0。

向量携带 feature schema version 与 deterministic manifest hash。

## 13. Oracle Document Feature Contract

Oracle 路径是 evaluation-only：

```text
Reviewed Expert Gold
→ EffectiveRiskGoldView
→ expert_oracle_document_features_v1
```

Oracle 不能：

- 进入 Production runtime；
- 把 Gold page / Evidence ID / 专家答案写进 Production X；
- 读取 2025 blind y；
- 代替 Retriever / Agent 输出最终产品结论。

Oracle artifact 必须保留 pass1 / audit provenance 与 deterministic content hash。

## 14. MarketOutcomeLabel

Market Foundation 提供 1D / 5D / 20D / 60D outcome contract。

核心规则：

- return base 使用 official listing price；
- horizon 按 observed eligible trading sessions；
- 缺 listing price / forward history 时显式 unavailable；
- benchmark / excess return 在 governed benchmark 不存在时保持 unavailable；
- 2025 blind outcome 不允许进入 development / validation modeling record。

## 15. PreListingMarketFeatureSnapshot

`PreListingMarketFeatureSnapshot` 记录严格早于目标上市日的 Market X。

必须满足：

```text
market_data_date <= observation_date < listing_date
```

`MarketFeatureManifest` 当前版本：

```text
v04_market_features_v1
```

其 10 个 raw feature 均带独立 `__missing` indicator，共 20 个有序位置。

当前 contract 包括 HSI、industry、recent IPO、turnover、volatility 等 feature family；某数据源缺失时保留显式 missing reason，不允许用不等价代理静默替换。

## 16. V04 Modeling Dataset

`V04ModelingRecord` / `V04ModelingDataset` 只在 identity / cohort / listing date / split / eligibility / policy 全部一致后连接 Document X 与非-blind outcome。

Market-augmented dataset 明确顺序：

```text
[100 Production Document features]
+
[20 Market features]
```

Oracle comparison 使用独立 Oracle X，但必须与 Production comparison 保持相同：

```text
cohort
split
target
preprocessing
model family
```

2025 使用 feature-only blind export，不包含 outcome / target 字段。

## 17. 时间治理

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

Development 用于训练、CV、feature policy、threshold 和超参数；2024 用于冻结方案 validation / model-family comparison；2025 在所有政策冻结前只能准备 X，不能读取 y。

## 18. Schema 版本升级规则

以下变化需要明确 schema / policy version bump：

- 字段删除或重命名；
- 特征名称 / 顺序 / dtype 改变；
- missing semantics 改变；
- canonical risk set 改变；
- level mapping 改变；
- target / return / session policy 改变；
- trusted source boundary 改变。

仅新增输入数据、在同一冻结规则下重新 materialize artifact，不自动要求 schema version bump，但必须产生新的 provenance / content hash。

## 19. 当前 source of truth

- 公共 Schema 实现：`src/ipo_risk/schemas/`
- Document modeling：`src/ipo_risk/modeling/`
- 风险注册表：`src/ipo_risk/domain/risk_codes.py`
- 当前执行计划：`END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`
- 架构边界：`ARCHITECTURE.md`

本文不再保留“第一阶段只做 RuleBasedPredictor”等历史阶段表述。
