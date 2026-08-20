# HK IPO Risk Agents — Current Architecture

> Status snapshot: **2026-08-20**  
> Stable document baseline: **v0.3.0 RELEASED / FROZEN**  
> Active program: **v0.4 End-to-End Closed Loop**  
> Current milestone: **PR-A — Document + Oracle Materialization & Coverage**

本文件只描述**当前有效架构与仍有约束力的边界**。历史 v0.2 / v0.3 设计过程、旧 handoff、已删除的 Evidence Intelligence 设计稿和一次性实验计划不再作为当前架构来源；需要追溯时使用 Git history / release。

## 1. 架构形式

项目保持**模块化单体**：一个 Git 仓库、一个主要 Python 应用，通过稳定 Schema / Protocol 连接各模块。

当前不引入与闭环无关的微服务、Kafka、Redis 队列、Neo4j 或 Kubernetes。

核心依赖方向：

```text
Streamlit
  ↓
IPOAnalysisService
  ↓
Workflow
  ↓
Parser / Retriever / Domain Agents / Skills / Verifier / Supervisor
  ↓
Structured IPOAnalysisResult
  ↓
v0.4 Modeling Boundary
  ↓
Document X + Market X + Outcome
  ↓
Prediction / Market Agent / Final Supervisor
```

禁止反向依赖，例如 Agent 不操作前端，Schema 不依赖具体实现，Parser 不依赖 Agent。

## 2. 当前 Production Document Runtime

v0.3 已冻结为 v0.4 第一版 Production Document Intelligence 基线。

```text
Prospectus PDF
    ↓
DocumentParser (parse once)
    ↓
DocumentChunks
    ↓
Stable Retriever / Evidence
    ↓
Financial Agent ─┐
Legal Agent ─────┼→ Specialized Verifier → V03 Supervisor
Business Agent ──┘                          ↓
                                      verified / pending /
                                      rejected risks
                                             ↓
                                      IPOAnalysisResult
```

当前真实主工作流是 `enhanced_v2`；`mvp_v1` 继续作为兼容 / Mock / 回归路径保留。仓库当前实际工作流模块为：

```text
src/ipo_risk/workflows/mvp_v1.py
src/ipo_risk/workflows/enhanced_v2.py
src/ipo_risk/workflows/state.py
```

不再把早期文档中的 `competition_v3`、"第一阶段只实现 mvp_v1" 等表述视为当前事实。

### 2.1 Offline / optional-AI

`configs/v03_offline.yaml` 使用真实 Parser、真实 Retriever、真实 Financial / Legal / Business Agent，但外部 LLM 可由 `UnavailableLLMProvider` 明确降级。

原则：

- LLM unavailable ≠ 伪造成功；
- 精确金融计算必须由 deterministic Skill 完成；
- 无 Evidence 不得产生正式 verified 风险；
- 单组件失败优先形成 structured partial result，而不是整条链静默失败。

## 3. v0.4 Modeling Boundary

v0.4 不直接让模型读取 Retriever candidates 或 LLM 文本，而是在最终文档结果之后建立独立建模边界：

```text
IPOAnalysisResult
  ↓
V04DocumentSnapshotMaterializer
  ↓
V03DocumentRiskSnapshot
  ↓
DOCUMENT_FEATURE_MANIFEST_V1
  ↓
Production Document X
```

关键实现：

```text
src/ipo_risk/modeling/materialization.py
src/ipo_risk/modeling/snapshot.py
src/ipo_risk/modeling/features.py
src/ipo_risk/schemas/modeling.py
```

该边界只消费最终结构化结果，不反向调用 Retriever、Agent 或 LLM。

### 3.1 Production Document Path

```text
PDF
→ Parser
→ Retriever
→ Financial / Legal / Business Agents
→ Skills
→ Verifier
→ Document Supervisor
→ V03DocumentRiskSnapshot
→ Production Document Feature Vector
```

这是最终产品可使用的文档信号路径。

### 3.2 Oracle Document Path

Oracle 是**评测上限 / 错误归因旁路**：

```text
Reviewed Expert Gold
→ EffectiveRiskGoldView
→ expert_oracle_document_features_v1
```

Oracle 不读取 PDF，不调用 Retriever / Agent，不进入 production runtime，也不能向 Production X 泄漏专家答案。

Oracle 的用途仅是后续在相同 Market X、y、split、preprocessing 和 model family 下比较：

```text
M   = Market-only
P   = Production Document-only
O   = Oracle Document-only
PM  = Production Document + Market
OM  = Oracle Document + Market
```

## 4. Market Foundation 与 Market X

市场层与 Document Runtime 解耦。

### 4.1 Market Foundation

```text
Official IPO metadata
+ governed IPO daily bars
→ MarketLabelGenerator
→ MarketOutcomeLabel (1D / 5D / 20D / 60D)
```

核心规则：

- official listing price 是 return base；
- horizon 按 observed trading sessions 计数；
- 缺 listing price / history 时显式 unavailable；
- 2025 blind y 不允许进入开发数据集。

### 4.2 Pre-listing Market X

```text
Governed reference data
+ prior IPO information known before target listing
→ PreListingMarketFeatureEngine
→ Market Feature Vector
```

所有 Market X 必须满足：

```text
market_data_date <= observation_date < target_listing_date
```

目标 IPO 上市日及之后的数据不得进入 X。

目前 HSI、authoritative industry benchmark mapping / history、total-market turnover 仍缺；这些缺失不会被单股成交额或未治理下载结果偷偷替代。

## 5. 当前模块职责

### 5.1 `app/`

Streamlit 展示层，只负责请求、展示、错误和 provenance。不得直接调用 Parser、Agent、Provider 或 Predictor。

### 5.2 `src/ipo_risk/services/`

`IPOAnalysisService` 是前端访问业务能力的统一入口，负责装配受控工作流与返回 `IPOAnalysisResult`。

### 5.3 `src/ipo_risk/workflows/`

定义工作流、状态、节点和失败路由。当前保留 `mvp_v1` 与 `enhanced_v2`。

### 5.4 `src/ipo_risk/agents/`

专业 Agent：Financial、Legal、Business。后续 v0.4 还会加入 Market Agent，但它不能绕过已冻结模型重新“自己预测”。

所有专业 Agent 继续遵守：

```text
RiskAgent.analyze(...) -> list[RiskItem]
```

### 5.5 `src/ipo_risk/skills/`

确定性计算，包括现金跑道、增长率、集中度等。Skill 可独立测试，不把数学计算交给 LLM。

### 5.6 `src/ipo_risk/parsers/`

负责 PDF 解析、页码、文本块、表格和 bbox，统一返回 `list[DocumentChunk]`。

### 5.7 `src/ipo_risk/retrieval/`

负责 Evidence discovery / ranking / location。Retriever V3、BM25、table lane、LambdaMART 是已冻结研究成果，当前 v0.4 不继续调参。

### 5.8 `src/ipo_risk/providers/`

承载 LLM、市场数据、IPO 数据等外部源适配，并转换为内部 Schema。凭证仅允许来自环境变量。

### 5.9 `src/ipo_risk/modeling/`

v0.4 的独立建模边界，负责：

- authoritative document snapshot materialization；
- Production Document feature vectorization；
- Oracle feature path；
- IPO structure / point-in-time context；
- canonical modeling dataset；
- baseline foundations。

该模块不得把 Gold page / Evidence ID / outcome identifier 等泄漏信息作为 Production ranking / modeling features。

### 5.10 `src/ipo_risk/predictors/`

现有 `RuleBasedPredictor` 保留为兼容 / 对照路径。Logistic / Linear / LightGBM 属于 v0.4 市场建模阶段，不得在尚未完成 canonical dataset 前被描述为生产模型。

### 5.11 `src/ipo_risk/evaluation/`

负责 document / retrieval / evidence / model 评测、数据切分与回归测试。

### 5.12 `src/ipo_risk/reporting/`

负责结构化报告输出。最终 v0.4 将在现有 Document Report 基础上增加 Market Prediction / explanation / final synthesis。

## 6. 公共接口保护

以下路径属于受保护公共接口 / 架构边界：

```text
src/ipo_risk/schemas/
src/ipo_risk/agents/base.py
src/ipo_risk/parsers/base.py
src/ipo_risk/retrieval/base.py
src/ipo_risk/predictors/base.py
src/ipo_risk/providers/
src/ipo_risk/workflows/state.py
src/ipo_risk/services/analysis_service.py
src/ipo_risk/core/container.py
src/ipo_risk/domain/risk_codes.py
```

修改这些边界必须明确兼容性影响并补充契约测试。

## 7. Evidence / Calculation / Verification 规则

所有正式 RiskItem 必须有 Evidence。

数字结论必须具有可审计 Calculation：

```text
inputs
formula
result
unit
evidence_ids
success / error
```

无 Evidence、Calculation 失败或无法满足 domain 注册表要求的风险，不得进入 verified_risks，应进入 pending / needs_review / rejected 等显式状态。

Verifier 与 Supervisor 不能创造原始 Evidence。

## 8. 数据切分与 no-leakage

正式 v0.4 建模切分：

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

- Development 用于规则开发、阈值、特征策略、CV 和调参；
- 2024 用于冻结方案的正式 validation / model-family comparison，不允许反复调参后仍称 untouched validation；
- 2025 在 feature / target / model policy 冻结前只能准备 X，不读取 y。

历史 Retriever Locked 10 已消费，不得再次作为 blind / locked 调参集。

## 9. 当前架构状态

### 已完成 / 冻结

```text
v0.3 Document Intelligence
Retriever V3 research
V04-1 Market Foundation contracts
V04-2 Document-to-Market feature contract
V04-3 Pre-listing Market feature contract
Oracle Document modeling foundations
```

### 当前执行

```text
PR-A
Official 438-case universe
→ Production analysis/materialization
→ Production Document X
→ Oracle materialization
→ unified coverage
→ deterministic rerun
```

### 尚未完成

```text
PR-B  Market-X Core
PR-C  5D Outcome Policy
PR-D  Canonical Model-ready Dataset
PR-E  Baseline + Oracle Diagnostic
PR-F  LightGBM + Explainability
PR-G  Market Agent + Final Supervisor
PR-H  Streamlit Full E2E
```

## 10. Retriever / LLM 后续位置

旧文档中的 `v0.3.5 Evidence Intelligence` 不再是当前执行阶段，也不应链接到已删除的旧设计稿。

如果 PR-E 证明：

```text
Oracle strong
Production weak
```

才在 v0.5 基于新的 unseen holdout 重新开启 Retriever / LLM Reranker / Agent / Semantic Verifier 优化。

当前仍有约束力的 Retriever 决策见：

[`research/RETRIEVER_V3_PREFLIGHT_AND_RERANKER_V11_DECISIONS.md`](research/RETRIEVER_V3_PREFLIGHT_AND_RERANKER_V11_DECISIONS.md)

## 11. 当前 source of truth

执行优先级：

1. [`END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](END_TO_END_CLOSED_LOOP_MASTER_PLAN.md)
2. [`ROADMAP.md`](ROADMAP.md)
3. [`PROJECT_SPEC.md`](PROJECT_SPEC.md)
4. 本文件
5. [`DATA_SCHEMA.md`](DATA_SCHEMA.md)

当前唯一实现里程碑为 **PR-A**；在 PR-A PASS 前，不重开 Retriever 调参、LLM Reranker、Fine-tuning、模型训练或大规模 UI 重构。
