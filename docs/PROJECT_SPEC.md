# HK IPO Risk Agents — Current Project Specification

> Status snapshot: **2026-08-24**  
> Current formal Gate: **PR-G — A review passed; local freeze manifest pending**  
> PR-H preparation: **UNBLOCKED**

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
PR-F                                COMPLETE / FROZEN
PR-G implementation                 MERGED / A REVIEW PASS
PR-G freeze manifest                REQUIRED LOCAL ACTION
PR-H                                PREPARATION UNBLOCKED
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

Runtime Market-X 以 governed `PreListingMarketFeatureSnapshot` 或其无损受控投影为 source-of-truth；legacy `MarketSnapshot` 只保留 v0.3 compatibility，不得反向声称 PR-B lineage。

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

## 7. Modeling objective and frozen findings

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
OM - M   招股书信号的专家上限诊断
OM - PM  自动 Document Pipeline 与 Oracle 的差距诊断
```

2024 Validation 未显示稳健的分类增量（Production `PM-M ROC-AUC -0.0157`；Oracle `OM-M ROC-AUC -0.0571`）。Oracle Validation 仅 19 例，因此该结果不能解释为已证明“没有 Document 信号”，也不能解释为已验证“Oracle ceiling 很强”。

PR-F frozen LightGBM 结果为：

```text
Full Production 2024
M   ROC-AUC 0.4246
P   ROC-AUC 0.5000
PM  ROC-AUC 0.4246
```

PM 与 M 完全预测等价，Production Document 100 维特征在该 frozen tree policy 下未被模型采用。Oracle `OM-M ROC-AUC -0.0143`，paired-bootstrap interval 跨零。该结果是正式 baseline finding，不允许因为看过 2024 后反转分数方向、继续调参、挑选口径或重写特征再宣称 2024 仍是 untouched Validation。

因此，模型在产品中定位为一个受治理的辅助 warning channel，而不是整个系统的唯一成败标准。PR-G / PR-H 必须保留不确定性，并把分数明确标记为未校准模型分数。

## 8. PR-G product integration contract

PR #104 已实现并合入：

```text
Frozen PR-F cohort evidence
+ optional hash-bound per-case score / SHAP runtime
+ Market Context
+ Document Supervisor result
+ rule score
→ Final Supervisor
→ v0.4 13-section report
```

A Gate Review 已通过。Final Supervisor：

- 不创造 RiskItem / Evidence；
- 引用 id 必须来自输入；
- 未校准 score 不称概率；
- conflicts 保留，不在 CH-4 前假仲裁；
- mock market 数字不得作为真实 context；
- 缺失通道必须显式降级。

PR-G 最终 freeze manifest 仍必须在本地真实 prospectus/runtime 上生成和校验，因为其中包含不能由远程审阅猜测的真实文件与 content hash。

## 9. PR-H runtime requirements

PR-H 的 baseline 产品闭环必须使用：

```text
Document
→ real Evidence / Calculation / page-bbox

Market
→ governed PreListingMarketFeatureSnapshot / lossless projection
→ strict PIT + per-feature provenance + explicit missingness

Model
→ checksummed local PR-F runtime handoff
→ frozen model_result_hash binding
→ per-case uncalibrated score + SHAP drivers
```

PR-F 完整 model/runtime bulk 不因 UI 需要而提交 Git。最小 handoff 不得包含 2025 Blind y、target labels、raw licensed data、secrets、absolute paths 或无关模型资产。

Market-X Extended 当前已接入 governed CSMAR HSI；industry benchmark / total-market turnover 仍显式缺失，不得 fake-fill。

## 10. Product strategy after PR-F

产品价值明确拆成两类：

### Risk Intelligence / Auditability

目标是回答：

```text
风险是什么？
原文证据在哪里？
计算过程是什么？
哪个 Agent 产生了判断？
Verifier 是否通过？
是否存在冲突和人工复核？
```

Competition 直接目标：关键风险要素抽取准确率 `>= 80%`、关键 Evidence recall `>= 85%`、Agent / Tool / Evidence traceability `= 100%`。

### Market Warning / Predictive Validation

目标是回答：

```text
当前 IPO 市场环境如何？
模型给出的风险 score 是什么？
哪些特征驱动该 score？
该 score 的 calibration / uncertainty 状态是什么？
在 1D / 5D / 20D / 60D horizon 上是否存在稳定关系？
```

短期 1D / 5D 预测增强优先从 point-in-time Market Sentiment / IPO heat / liquidity / comparable context 寻找增量；结构性 Document 风险同时在 20D / 60D 上验证。

## 11. Time governance

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

Development 使用 time-aware protocol；2024 不参与模型、预处理或阈值拟合；2025 y 正式开放前不可访问。`ROC-AUC < 0.5` 不授权在查看 2024 后反转 score 并把结果作为正式提升。

## 12. Baseline E2E success criteria

PR-H 至少满足：

1. 真实 PDF 可进入稳定分析链；
2. 风险结论可追溯 Evidence / Calculation / page / bbox；
3. Market X 有 point-in-time provenance；
4. canonical dataset 可重建；
5. baseline / advanced model 结果可复现；
6. model score semantics 明确，未校准不称概率；
7. Final Supervisor 不创造事实；
8. UI 可展示 Document + Market + Prediction + Evidence + uncertainty；
9. 3–5 个真实 IPO 可完成端到端 demo；
10. demo 中 Market channel 与 Model channel 的可用状态来自真实 governed runtime，不由 fake/mock 代替。

PR-H 的通过条件不是重新提高 frozen 5D AUC，而是正确、可追溯、可降级地消费已有研究结果并完成闭环。

## 13. Competition hardening success criteria

PR-H 后的 Competition Hardening 采用直接 benchmark 决定增强路线：

- CH-1：独立 version 1D / 20D / 60D outcome，5D 保持 primary frozen policy；
- CH-2：按风险类别测 Precision / Recall / F1 / Evidence Recall，达标类别不重写；
- 若 CH-2 error attribution 指向 retrieval，优先 Hybrid Retrieval；若指向复杂语义/条件理解，再引入 LLM semantic extraction / reranking；
- CH-3：增强 Market Sentiment 与 Competition Skills，所有输入必须 point-in-time；
- CH-4：Agent conflict detection → re-check → challenge → arbitration，并保留 unresolved uncertainty；
- CH-5：Evidence screenshot / highlight + reviewer audit trail；
- CH-6：统一提交抽取、Evidence、traceability、multi-horizon 和真实案例结果，不用单一漂亮指标代替完整系统评价。

## 14. Out of scope until direct evidence justifies reopening

当前不把 Retriever tuning、LLM Reranker、Fine-tuning、LoRA、大规模 Prompt 重写、新 Agent、深度市场模型设为 PR-H 前置条件。PR-E / PR-F 的 Oracle 结果本身不足以支持大规模 Document 重构；是否重启该研究由 CH-2 的直接 benchmark + error attribution 决定。
