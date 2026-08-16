# HK IPO Risk Agents — Current Project Specification

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

当前优先完成完整闭环，再在 v0.5 回到 Retriever、LLM Reranker、Agent VNext 等研究优化。

## 3. 输入

系统正式输入包括：

1. 港股 IPO 招股书 PDF；
2. `case_id` / 公司 / 股票代码等受控身份字段；
3. 官方上市日期与 IPO 基础信息；
4. 严格截止于上市前可获得的市场数据；
5. 版本化配置与数据源 provenance。

不得使用上市后信息构造模型输入 X。

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
- 将规则分包装为概率；
- 绕过 Verifier / Supervisor 的治理边界。

### 确定性代码负责

- 财务计算；
- Schema 校验；
- 数据时间边界；
- 特征生成；
- 市场标签生成；
- 版本与 provenance；
- 模型评测与数据切分。

## 6. v0.4 模型任务

第一版主研究对象为**上市后 5 个交易日弱表现风险**。

建议同时保留：

- `return_1d / 5d / 20d / 60d`；
- benchmark-adjusted / abnormal return；
- 5D classification label。

分类阈值只允许由 Development 数据决定。

正式比较必须包含：

```text
A. Market-only
B. Document-only
C. Document + Market
```

核心研究问题为：

```text
Performance(Document + Market)
>
Performance(Market-only) ?
```

即：Multi-Agent 招股书风险特征是否提供传统 IPO / 市场变量之外的增量信息。

## 7. 数据切分与 Blind Policy

市场建模统一使用：

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

规则：

- 2020–2023：训练、CV、特征选择、阈值、超参数；
- 2024：模型选择与正式 validation；
- 2025：模型与 feature policy 冻结后一次性 blind evaluation；
- 2025 不得用于开发调参；
- 一旦 blind 被查看，不能根据其结果调参后继续称其为 blind。

Retriever 研究中的历史 Locked 10 已经消费，仅保留为历史评测结果；未来重启 Retriever 研究时必须另建新的 unseen holdout。

## 8. 当前真实数据状态

以当前 v0.4 readiness audit 为基准：

- 官方 2020–2024 IPO universe：438 cases；
- IPO OHLCV：432 / 438 可用，6 个 outcome unavailable；
- authoritative Document Risk Snapshot pipeline 已存在；
- 全 438 case 的 authoritative document snapshot 尚未 materialize；
- HSI 历史源仍缺；
- authoritative industry benchmark mapping / history 仍缺；
- total-market turnover 源仍缺；
- `MODEL_READY_DATA_GATE` 尚未打开。

详细口径见 `research/V04_DATA_READINESS.md`。

## 9. 架构保护边界

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

Streamlit 只通过 `IPOAnalysisService` 访问业务能力，不得直接调用 Parser、Agent、Predictor 或 Repository。

## 10. v0.4 当前非目标

闭环冻结前不把以下工作作为主线：

- 新 Retriever 算法；
- Retriever V3 继续调参；
- LLM Reranker VNext；
- SFT / LoRA；
- 新增专业 Agent；
- 深度学习市场预测模型；
- 大规模 UI 重构。

只有阻断闭环、造成数据泄漏、明显错误或不可复现的问题可以打断该优先级。

## 11. v0.4 完成定义

v0.4 首先以**完整、可信、可重建**为成功标准：

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

## 12. 当前下一项任务

当前正式进入：

> **CL-1 / CL-2：冻结现有 Document Intelligence，并批量生成第一版 IPO-level Document Risk Feature Dataset。**

完成后立即进入最小真实 Market Data、5D Outcome 和 Model-ready Dataset 闭环。