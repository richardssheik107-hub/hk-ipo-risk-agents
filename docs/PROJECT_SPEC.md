# HK IPO Risk Agents — Current Project Specification

> Status snapshot: **2026-08-23**  
> Current formal Gate: **PR-F — LightGBM + Explainability**

## 1. Product definition

HK IPO Risk Agents 是一个证据驱动、多智能体协同、可审计的港股 IPO 招股书分析与上市后风险预警系统。

系统不让单一 LLM 直接“读完整招股书然后给结论”，而是拆成：

```text
Document Parsing
→ Evidence Retrieval
→ Domain Agents
→ Deterministic Skills
→ Verification / Supervision
→ Structured Document Features
→ Governed Pre-listing Market Features
→ Post-listing Outcome
→ Statistical Modeling
→ Explainable Final Report
```

输出中的规则分或未经校准的模型分数不是实际下跌概率，也不构成投资建议。

## 2. Current v0.4 state

```text
v0.3 Document Intelligence          RELEASED / FROZEN
PR-A Document X                     COMPLETE / FROZEN
PR-B Market-X Core                  COMPLETE / FROZEN
PR-C 5D Outcome                     COMPLETE / FROZEN
PR-D Canonical Dataset              COMPLETE / FROZEN
Oracle v2                           COMPLETE / FROZEN / EVALUATION-ONLY
PR-E                                COMPLETE / FROZEN
PR-F                                CURRENT FORMAL GATE
```

真实建模 cohort：

```text
424 model-ready IPO
354 Development
70 Validation
```

Oracle v2：

```text
98 materialized
96 strict usable
77 Development
19 Validation
142 features
evaluation_only = true
production_consumable = false
```

## 3. Inputs

正式输入包括：

- 港股 IPO 招股书 PDF；
- 受控 `case_id` / stock code / listing identity；
- 官方 listing date / issue price / IPO metadata；
- 严格 point-in-time 的上市前 Market X；
- versioned configuration / source provenance。

目标 IPO 上市后信息不得进入该 IPO 的输入 X。

## 4. Document risk scope

v0.3 frozen formal risks：

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

正式 RiskItem 必须能回到 Evidence；精确数字必须通过 deterministic Skill / Calculation。

比赛强化阶段再专项覆盖现金消耗、对赌/赎回、关联交易、集中度、核心管线、文本粉饰度等赛题要求；不能为了比赛提前打断 baseline Gate。

## 5. Trust boundaries

### LLM may

- 做语义抽取；
- 判断 Evidence relevance / role；
- 理解条件、状态、上下文；
- 生成受约束结构化解释。

### LLM may not

- 替代 Python 做精确金融计算；
- 无 Evidence 创造 verified 风险；
- 修改底层模型分数；
- 把未校准 score 包装成概率；
- 猜缺失的 HSI / benchmark / turnover 数据；
- 绕过 Verifier / Supervisor。

### Deterministic code owns

- financial calculations；
- schema / identity validation；
- feature vectorization；
- point-in-time guards；
- hashes / manifests；
- model fitting / scoring；
- reproducibility checks。

## 6. Production / Oracle separation

Production：

```text
Prospectus → Parser → Retriever → Agents → Verifier → Snapshot → Production X
```

Oracle：

```text
Reviewed Expert Gold → Oracle feature builder → Oracle X
```

Oracle 只用于研究上限与错误归因。Gold page、Evidence ID、manual answer 不得进入 Production X。

## 7. Modeling objective

PR-E 已冻结以下正式比较：

```text
M   Market only
P   Production Document only
O   Oracle Document only
PM  Market + Production
OM  Market + Oracle
```

解释问题：

```text
PM - M   自动招股书信息的增量价值
OM - M   招股书信号的专家上限
OM - PM  自动 Document Pipeline 距离专家上限的差距
```

2024 Validation 未显示稳健的分类增量（Production `PM-M ROC-AUC -0.0157`；Oracle `OM-M ROC-AUC -0.0571`）。Oracle Validation 仅 19 例，因此该结果用于约束 PR-F 的模型与不确定性分析，不能解释为已证明“没有 Document 信号”。

## 8. Time governance

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

Development 使用 time-aware protocol；2024 不参与模型、预处理或阈值拟合；2025 y 正式开放前不可访问。

## 9. Product success criteria

Baseline E2E 至少满足：

1. 真实 PDF 可进入稳定分析链；
2. 风险结论可追溯 Evidence / Calculation / page / bbox；
3. Market X 有 point-in-time provenance；
4. canonical dataset 可重建；
5. baseline / advanced model 结果可复现；
6. model score semantics 明确，未校准不称概率；
7. Final Supervisor 不创造事实；
8. UI 可展示 Document + Market + Prediction + Evidence + uncertainty；
9. 3–5 个真实 IPO 可完成端到端 demo。

## 10. Out of scope until evidence justifies reopening

当前不把 Retriever tuning、LLM Reranker、Fine-tuning、LoRA、大规模 Prompt 重写、新 Agent、深度市场模型设为 baseline 前置条件。只有 PR-E Oracle gap 或后续冻结比赛指标证明真实瓶颈时才重启。
