# HK IPO Risk Agents — Current Project Specification

> Status snapshot: **2026-08-23**
> Execution strategy: **Current PR-D → PR-H baseline E2E first; Competition Hardening second.**

## 1. 项目定位

HK IPO Risk Agents 是一个**证据驱动、多智能体协同、可审计**的港股 IPO 招股书分析与上市后风险预警系统。

系统不追求“让一个大模型直接读完整招股书并给结论”，而是把任务拆为：

```text
Document Parsing
→ Evidence Retrieval
→ Domain Agents
→ Deterministic Skills
→ Verification / Supervision
→ Structured Document Features
→ Governed Pre-listing Market Features
→ Market Modeling
→ Explainable Final Report
```

输出中的规则分或未经校准的模型分数，不得描述为真实下跌概率，也不构成投资建议。

## 2. 当前版本状态

### 已冻结稳定层：v0.3

当前文档智能层已经具备：

- 真实 PDF 解析；
- Financial / Legal / Business 三专业 Agent；
- 8 类正式文档风险；
- Evidence、Calculation 与物理页码追踪；
- Specialized Verifier；
- Supervisor；
- `IPOAnalysisService`；
- Streamlit；
- Markdown / JSON 报告；
- Mock / offline / optional-AI 降级路径。

v0.3 作为当前 Document Intelligence 基线冻结，不再要求继续优化 Retriever 才能进入下一阶段。

### 当前主线：v0.4 End-to-End Closed Loop

v0.4 的任务是把文档风险真正连接到上市后市场表现：

```text
Prospectus
→ Document Risk
→ IPO-level Features
→ Pre-IPO Market Features
→ Post-IPO Outcome
→ Prediction Model
→ Market Agent
→ Final Supervisor
→ Full E2E Report
```

当前优先完成完整闭环，再依据 PR-E 的 Oracle diagnostic 与后续赛题 benchmark 决定是否回到 Retriever、LLM Reranker、Agent VNext 等研究优化。

PR-A — Document + Oracle Materialization & Coverage、PR-B — Market-X Core +
Governed EOD Store、PR-C — 5D Outcome Policy Freeze 与 PR-D — Canonical
Model-ready Dataset 均已 **COMPLETE / FROZEN**。当前正式里程碑为 PR-E
Baseline + Oracle Diagnostic；Production 输入已冻结，Oracle v2 仍需独立冻结。

### Post-baseline：Competition Hardening

PR-H baseline E2E 通过后，系统进入赛题专项强化，而不是提前打断当前 Gate。完整要求与验收见 [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md)。

## 3. 输入

系统正式输入包括：

1. 港股 IPO 招股书 PDF；
2. `case_id` / 公司 / 股票代码等受控身份字段；
3. 官方上市日期与 IPO 基础信息；
4. 严格截止于上市前可获得的市场数据；
5. 版本化配置与数据源 provenance。

比赛原型最终还必须支持从**公司名称、股票代码或招股书文件**进入受控分析链路。

不得使用目标 IPO 上市日或上市后信息构造该 IPO 的模型输入 X。

## 4. 文档风险范围

v0.3 冻结的 8 类正式风险为：

### Financial

- `cash_runway`
- `continuous_loss`
- `revenue_growth`
- `customer_concentration`
- `supplier_concentration`

### Legal

- `redemption_rights`
- `material_litigation_compliance`

### Business

- `precommercial_product`

每条正式 RiskItem 必须能追溯到 Evidence；需要精确数字的结论必须通过确定性 Skill / Calculation 生成。

比赛强化阶段需要对赛题明确点名的非标风险建立专项 benchmark / 必要的新增版本，至少覆盖：

```text
现金消耗率 / 现金流消耗压力
特殊股东对赌 / 赎回条款
关联交易
客户 / 供应商集中度
核心管线进度
“文本粉饰度”较高原文切片 / 可解释 diagnostic
```

新增能力不得绕过 Evidence / Verifier；“文本粉饰度”不得成为无来源的主观黑箱标签。

## 5. 信任边界

### LLM 可以做

- 语义提取；
- Evidence relevance / role 判断；
- 状态、条件、上下文理解；
- 受约束的结构化解释。

### LLM 不可以做

- 替代 Python 完成精确金融计算；
- 无 Evidence 创造 verified 风险；
- 修改底层市场模型预测；
- 将规则分或未校准模型分包装为概率；
- 绕过 Verifier / Supervisor 的治理边界；
- 猜 HSI、行业 benchmark 或全市场 turnover 等缺失市场数据。

### 确定性代码负责

- 财务计算；
- Schema 校验；
- 数据时间边界；
- 特征生成；
- 市场标签生成；
- 版本与 provenance；
- 模型评测与数据切分。

## 6. v0.4 Market-X 定义

PR-B 明确区分两层，避免把缺失的 reference-market sources 误写成 Core 的前置阻断。

### 6.1 Market-X Core

当前 Core contract：

```text
v04_ipo_market_context_features_v1
ipo_market_context_policy_v1
15 raw prior-IPO context features
+ 15 adjacent missing indicators
= 30 positions
```

Core 使用：

- authoritative IPO identity / listing date；
- prior-IPO offer/context facts；
- governed IPO EOD；
- 只有在目标 IPO 上市前已经完成 target session 的 prior IPO 1D / 5D outcomes。

For target listing date `T`：

```text
prior_listing_date < T
prior_1d_target_trading_date < T
prior_5d_target_trading_date < T
```

同日才形成的 prior outcome 不视为严格上市前可得。

### 6.2 Market-X Extended

既有 frozen contract 保持不变：

```text
v04_prelisting_market_features_v1
v04_market_features_v1
10 raw + 10 missing indicators
= 20 positions
```

Extended 需要 HSI、industry benchmark mapping/history、HKEX total-market turnover 等真实受治理来源。当前这些来源仍缺失，因此对应能力保持显式 missing，不允许用 proxy / fake row / neutral zero 补齐。

`official_industry_name` 可作为 prior-IPO peer grouping 的描述字段，但**不等于 authoritative industry-index mapping**。

Competition Hardening 中的 Market Sentiment Agent / SentimentHeatSkill 必须建立在受治理 Market-X 上；如果 Extended authoritative sources 仍不可得，保持 missing，不为满足赛题形式要求伪造市场数据。

## 7. v0.4 模型任务

第一版主研究对象为**上市后 5 个交易日弱表现风险**。

正式建模保留：

- 5D raw return；
- benchmark-adjusted return（仅当 governed benchmark 可用且 policy 冻结）；
- 5D classification label。

PR-H baseline E2E 后，为赛题业务验证扩展：

```text
return_1d
return_5d   # primary / higher-weight
return_20d
return_60d
```

1D / 20D / 60D 是独立 versioned outcome extension，不得反向篡改已经冻结的 5D threshold / target policy。

分类阈值只允许由 Development 数据决定。

正式比较至少包含：

```text
M   = Market-only
P   = Production Document-only
O   = Oracle Document-only
PM  = Production Document + Market
OM  = Oracle Document + Market
```

核心研究问题为：

```text
Performance(Production Document + Market)
>
Performance(Market-only) ?
```

同时用 Oracle 回答：招股书风险本身是否有信号，以及 Production Pipeline 捕获了多少专家可提取的信息。

## 8. 数据切分与 Blind Policy

市场建模统一使用：

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

规则：

- 2020–2023：训练、CV、特征策略、阈值、超参数；
- 2024：冻结方案的正式 validation / model-family comparison；不得基于 2024 反复调参后继续称其为 untouched validation；
- 2025：feature / target / model policy 冻结后一次性 blind evaluation；
- 2025 不得用于开发调参；
- 一旦 blind 被查看，不能根据其结果调参后继续称其为 blind；
- Competition Hardening 不自动授权打开 2025 y。

Retriever 研究中的历史 Locked 10 已经消费，仅保留为历史评测结果；未来重启 Retriever 研究时必须另建新的 unseen holdout。

## 9. 当前真实数据状态

以 2026-08-23 当前 readiness 为准：

- 官方 2020–2024 IPO universe：438 cases；
- 本地招股书：438 / 438；
- PR-B EOD/session-ready：432 / 438；
- PR-C 5D outcome available：424 / 438；
- PR-C unavailable：14 = 12 `missing_base_price` + 2 `no_eligible_session`；
- Development available：354 / 368；Validation available：70 / 70；
- authoritative Document Risk Snapshot：438 / 438；
- Production Document-X：438 / 438；
- Production Document Feature schema：`v04_document_features_v1`，100 维；
- Production failures：0；silent drops：0；
- frozen PR-A Oracle inventory：60；正式 PR-E 前需基于新增 annotation 重新审计 Oracle coverage；
- A6 determinism：438 checked，0 mismatches，PASS；
- 2025 blind access：NO；
- HSI 历史源仍缺；
- authoritative industry benchmark mapping / history 仍缺；
- total-market turnover 源仍缺；
- PR-B Core：438 / 438 materialized，0 failures，0 PIT failures，438 determinism / 0 mismatches；
- `MODEL_READY_DATA_GATE` 尚未通过；PR-C 已冻结，当前等待 PR-D canonical materialization。

## 10. Production 与 Oracle 永久分离

### Production

```text
Prospectus PDF
→ Parser
→ Retriever
→ Financial / Legal / Business Agents
→ Skills
→ Verifier
→ Document Supervisor
→ V03DocumentRiskSnapshot
→ Production Document X
```

这是最终产品使用的路径，不依赖专家答案。

### Oracle

```text
Reviewed Expert Gold
→ EffectiveRiskGoldView
→ Oracle Document X
```

Oracle 只用于研究上限 / 错误归因：

- 不进入 Production runtime；
- 不替代 Retriever / Agent；
- 不向 Production X 泄漏 Gold page、Evidence ID 或专家答案；
- 不读取 2025 blind y。

## 11. 架构保护边界

公共接口与模块边界以 `ARCHITECTURE.md`、`DATA_SCHEMA.md` 和根目录 `AGENTS.md` 为准。

重点保护：

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

Streamlit 只通过 `IPOAnalysisService` / 受控上层 service 访问业务能力，不得直接调用 Parser、Agent、Provider 或 Predictor。

Competition Hardening 的新 Market Sentiment / conflict / human-review 能力也必须尊重这些边界；公共 Schema 变更必须有 contract test 和兼容性说明。

## 12. Baseline E2E 当前非目标

PR-H baseline freeze 前不把以下工作作为当前主线：

- 新 Retriever 算法；
- Retriever V3 继续调参；
- LLM Reranker VNext；
- SFT / LoRA；
- 大规模 Prompt 重构；
- 深度学习市场预测模型；
- 大规模 UI 重构；
- 为赛题提前重写全部 Agent。

只有阻断闭环、造成数据泄漏、明显错误或不可复现的问题可以打断该优先级。

## 13. Baseline v0.4 完成定义

v0.4.3 baseline E2E 首先以**完整、可信、可重建**为成功标准：

- PDF → Document Risk 正常；
- Document Features 可重建；
- Market Data / Outcome 可重建；
- Model-ready Dataset 可重建；
- Logistic / Linear baseline 可运行；
- LightGBM 可运行并解释；
- Market Agent 可输出结构化说明；
- Final Supervisor 可统一 Document + Market 风险；
- Streamlit 可展示 3–5 个真实 IPO 的完整链路；
- provenance、version、failure state 可审计；
- 2025 blind 未参与开发调优。

达到该标准后先冻结 baseline，再进入 Competition Hardening。

## 14. 当前正式任务

当前严格顺序：

```text
PR-A  Document + Oracle Materialization & Coverage   COMPLETE / FROZEN
PR-B  Market-X Core + Governed EOD Store             COMPLETE / FROZEN
PR-C  5D Outcome Policy Freeze                       COMPLETE / FROZEN
PR-D  Canonical Model-ready Dataset                  COMPLETE / FROZEN
PR-E  Baseline + Oracle Diagnostic                   READY / FORMAL BASELINE NEXT / NOT STARTED
PR-F  LightGBM + Explainability
PR-G  Market Agent + Final Supervisor
PR-H  Streamlit Full E2E + Real-case Demo
v0.4.3 Baseline E2E Freeze
```

PR-C 正式 Gate 已由真实 governed run 完成。PR-D 也已在冻结输入上完成 438 → 424 + 14、354 Development / 70 Validation 的正式 materialization、same-provenance resume 与 freeze。当前下一 Gate 为 PR-E formal baseline / Oracle diagnostic，但尚未开始。

## 15. Competition Hardening / Submission Success Criteria

PR-H baseline E2E 完成后，按 [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md) 进入 CH-0..CH-6。最终比赛版本必须覆盖赛题全部内容：

### Document / Agent 能力

```text
标准化财务指标
现金消耗率 / 现金流压力
对赌 / 赎回条款
关联交易
客户 / 供应商集中度
核心管线进度
文本粉饰度较高原文切片
```

角色：

```text
法务合规 Agent
财务穿透 Agent
市场情绪 Agent
总控决策 / Final Supervisor
```

Skills：

```text
长文档检索
同行估值比对
现金流消耗测算
情绪热度打分
```

冲突时：

```text
conflict detection
→ evidence re-check
→ Skill / Verifier challenge
→ arbitration
→ resolved / needs_review
```

### Competition metrics

```text
关键风险要素抽取准确率 >= 80%
关键 Evidence 片段召回率 >= 85%
Agent / Tool / Evidence source traceability = 100%
逻辑解释有效性 = expert or LLM-assisted rubric review
```

### Outcome / business validation

```text
1D
5D   # primary / higher-weight
20D
60D
```

### Product / delivery

- 风险核心诱因；
- PDF 页码 / 段落 / 表格 / bbox evidence screenshot；
- current horizon risk prediction；
- human-in-the-loop review；
- 可运行 Streamlit / API；
- 测试集 prediction table；
- multi-agent / tool / verifier logs；
- Evidence excerpts；
- 典型案例报告；
- environment / run scripts；
- 3–5 个真实 Demo + batch capability。

全部通过后才标记：

> **v0.4.5 COMPETITION_READY / SUBMISSION FROZEN**。

## 16. 后续 Retriever / LLM / Agent 优化触发条件

Competition Hardening 不等于无边界重启 AI 研究：

- Evidence recall < 85% → 定向 Retriever / table / evidence targeting 修复；
- Risk accuracy < 80% 且 Evidence 已正确 → Agent / Verifier / Skill 语义修复；
- Oracle strong / Production weak → 才支持更大规模 Retriever / LLM / Agent 研究；
- 指标已经达标 → 不为技术炫技强行 Fine-tuning / LoRA。

任何新增调优必须使用新的、受治理的 evaluation / holdout；历史 Retriever Locked 10 已消费。
