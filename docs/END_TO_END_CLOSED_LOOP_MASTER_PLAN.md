# HK IPO Risk Agents 后续闭环总计划

> 规划版本：End-to-End Closed Loop First
>
> 适用阶段：v0.3 已发布后至 v1.0 正式版本
>
> 核心策略：先完成完整闭环并看到真实效果，再逐层优化 Retriever、LLM、Agent 与模型。

## 0. 规划原则

当前项目已经具备真实 PDF 解析、Financial / Legal / Business 三专业 Agent、确定性 Skills、Specialized Verifier、Supervisor、Service、Streamlit、文档风险特征契约以及 v0.4 Market Foundation。下一阶段不再优先追求单模块最优，而是优先完成以下完整链路：

```text
Prospectus PDF
    ↓
Parser
    ↓
Current Stable Retriever
    ↓
Financial / Legal / Business Agents
    ↓
Skills + Specialized Verifier
    ↓
Document Supervisor
    ↓
IPO-level Document Risk Features
    ↓
Pre-IPO Market / IPO Features
    ↓
Model-ready Dataset
    ↓
Logistic / Linear Baseline
    ↓
LightGBM
    ↓
Market Agent
    ↓
Final Supervisor
    ↓
Explainable IPO Risk Report
    ↓
Streamlit Demo
```

本计划的优先级是：

1. 先让系统从招股书输入一直走到上市后风险输出；
2. 先证明完整闭环可运行、可解释、可复现；
3. 再证明文档风险对市场表现是否具有增量预测价值；
4. 最后再返回 Retriever、LLM Reranker、Agent VNext、Fine-tuning 等优化问题。

---

# 1. 版本总路线

| 版本 | 目标 | 核心交付物 | 状态 |
| --- | --- | --- | --- |
| v0.3.0 | 多 Agent 文档风险分析 | Financial / Legal / Business + Verifier + Supervisor | RELEASED / FROZEN |
| v0.4-MVP | 完整端到端闭环 | Document Features + Market Data + Outcome + Baseline Model | NEXT |
| v0.4.1 | 第一版有效预测模型 | LightGBM + 特征重要性 / SHAP | PLANNED |
| v0.4.2 | 市场智能层 | Market Agent + Final Supervisor | PLANNED |
| v0.4.3 | 完整产品演示 | Streamlit Full E2E Demo + Report | PLANNED |
| v0.5.0 | 研究级优化 | Retriever V3 / LLM Reranker / Agent & Verifier VNext | DEFERRED UNTIL LOOP COMPLETE |
| v0.6.0 | 正式评测 | 消融、失败分析、时序验证、Blind Test | PLANNED |
| RC / v1.0 | 正式交付 | 冻结源码、模型、结果、演示、报告 | PLANNED |

---

# 2. 当前阶段的范围控制

在 v0.4-MVP 闭环完成前，以下工作原则上暂停：

- 继续新增 Retriever 算法；
- Retriever V3 / Dense / Embedding / Reranker 的进一步调优；
- LLM Fine-tuning / LoRA；
- 新增更多专业 Agent；
- 大规模 Prompt 重构；
- Streamlit 大规模视觉改版；
- 复杂深度学习市场模型；
- 使用 2025 blind 数据调特征、阈值或超参数。

允许的例外只有两类：

1. 阻断完整闭环的 bug；
2. 会导致明显错误、数据泄漏或不可复现的问题。

---

# 3. Phase CL-1：冻结当前 Document Intelligence

## 3.1 目标

把当前 v0.3 文档分析能力视为第一版生产基线，不再以提高几个百分点的检索指标作为进入下一阶段的前置条件。

## 3.2 固定链路

```text
PDF
↓
Parser
↓
Current Stable Retriever
↓
Financial / Legal / Business
↓
Deterministic Skills
↓
Specialized Verifier
↓
Supervisor
↓
Document Risk Output
```

## 3.3 最小交付物

每个 IPO 至少能够稳定生成：

- 8 类正式风险的结构化输出；
- Evidence ID、物理页码与原文；
- 需要精确数值的 Calculation；
- verified / needs_review / rejected 状态；
- Financial / Legal / Business 域级摘要；
- Supervisor 最终 document risk summary。

## 3.4 PASS 条件

- v0.3 既有测试全部保持；
- 2410.HK 等已冻结真实回归不退化；
- Mock / offline 模式仍可运行；
- 公共 Schema 不因闭环开发被破坏；
- 失败必须结构化记录，不允许 silent failure。

---

# 4. Phase CL-2：生成 IPO-level Document Risk Vector

## 4.1 目标

把 Agent 的复杂结构化结果转换为一个可以直接进入统计 / 机器学习模型的 IPO-level 特征向量。

## 4.2 第一版特征原则

第一版不追求高维，优先保留 20–40 个稳定、可解释、上市前可获得的特征。

建议最小集合：

```text
cash_runway_score
continuous_loss_flag
revenue_growth_score
customer_concentration_score
supplier_concentration_score
redemption_rights_flag
material_litigation_compliance_score
precommercial_product_score

financial_risk_count
legal_risk_count
business_risk_count
critical_risk_count
high_risk_count
verified_risk_count
needs_review_count
verified_risk_ratio
cross_domain_risk_count
overall_document_risk_score
```

可以继续复用现有 v0.4 Document Risk Snapshot / feature contract，但第一版模型只使用已验证稳定、不会造成明显泄漏的字段。

## 4.3 规则

- 一个 IPO 对应一行模型特征；
- Feature 必须由上市前信息生成；
- 不允许使用未来市场结果反向构造 Document Feature；
- 保留 `feature_version`、生成时间、来源风险与 Evidence provenance；
- 缺失值处理必须确定性、可审计。

## 4.4 PASS 条件

输出稳定的：

```text
case_id × document_features
```

并能够重复生成相同结果。

---

# 5. Phase CL-3：最小市场数据闭环

## 5.1 目标

不是一次性补齐全部金融数据库，而是先获取完成第一版模型所需的最小真实市场数据。

## 5.2 第一版最小字段

```text
case_id
stock_code
listing_date
offer_price
close_D1
close_D5
close_D20
close_D60
benchmark_D1
benchmark_D5
benchmark_D20
benchmark_D60
```

如果已有更完整 OHLCV，可保留，但不能让额外字段阻断第一版闭环。

## 5.3 必须处理

- 港股交易日历；
- 上市日期映射；
- 股票代码映射；
- 停牌 / 无交易；
- 缺失行情；
- 基准市场数据；
- 数据源 provenance；
- 证券 eligibility；
- 任何 case 的缺失原因都必须显式输出。

## 5.4 PASS 条件

生成 market coverage report：

```text
eligible
available
missing
excluded
reason
```

不允许 silent missing。

---

# 6. Phase CL-4：Outcome / Target Freeze

## 6.1 主任务

第一版主目标统一为：

> 上市后 5 个交易日的市场弱表现风险。

推荐以 5D abnormal return 为主要连续变量：

```text
AR_5D = IPO_Return_5D - Benchmark_Return_5D
```

同时保存：

- 1D；
- 20D；
- 60D；

作为 robustness / 后续分析目标，不让它们阻断第一版模型。

## 6.2 两类任务

### Regression

```text
return_5d
abnormal_return_5d
```

### Classification

```text
poor_performer_5d
```

分类阈值只能使用 Development 样本确定，并在模型冻结后保持不变。

## 6.3 PASS 条件

- target policy 文档化；
- 所有日期按 trading session 而不是自然日处理；
- 2025 blind target 不参与开发；
- y 可以通过固定脚本重复生成。

---

# 7. Phase CL-5：Model-ready Dataset

## 7.1 目标

生成真正用于建模的一张 IPO-level 表：

```text
X_document
+
X_pre_ipo_market
+
Y_post_ipo_outcome
```

## 7.2 最小结构

```text
case_id
listing_date
cohort
industry

# document
cash_runway_score
continuous_loss_flag
...
overall_document_risk_score

# pre-IPO / market
offer_price
market_cap
market_regime
benchmark_pre_listing_return
benchmark_pre_listing_volatility
...

# targets
return_1d
return_5d
return_20d
return_60d
abnormal_return_1d
abnormal_return_5d
abnormal_return_20d
abnormal_return_60d
poor_performer_5d
```

## 7.3 三个正式特征组

必须预先冻结三套输入：

### A. Market-only

只使用传统 IPO / 上市前市场变量。

### B. Document-only

只使用 Multi-Agent 文档风险变量。

### C. Combined

Document + Market。

这三组是后续回答“文档 AI 是否提供增量价值”的核心实验设计。

## 7.4 PASS 条件

- 无上市后特征泄漏进入 X；
- feature schema 固定；
- dataset manifest 固定；
- 2020–2023 / 2024 / 2025 split 固定；
- 可以从原始输入完整重建数据集。

---

# 8. Phase CL-6：最简单 Baseline Model

## 8.1 目标

先证明完整建模链路可运行，不追求复杂算法。

## 8.2 模型

Classification：

```text
Logistic Regression
```

Regression：

```text
Linear Regression / Ridge
```

## 8.3 必做实验

```text
A: Market-only
B: Document-only
C: Combined
```

## 8.4 指标

Classification：

- ROC-AUC；
- PR-AUC；
- Precision；
- Recall；
- F1；
- LogLoss；
- Brier Score；
- calibration diagnostics。

Regression：

- MAE；
- RMSE；
- Rank IC / Spearman correlation（如样本规模允许）。

## 8.5 第一版成功标准

Baseline 的首要 PASS 不是高 AUC，而是：

1. train → predict → evaluate 全链路可复现；
2. Market-only / Document-only / Combined 可公平比较；
3. 无未来信息泄漏；
4. 输出可用于下一阶段模型。

---

# 9. Phase CL-7：LightGBM + Explainability

## 9.1 目标

在完整 baseline 基础上获得第一版真正具有表达能力的非线性模型。

## 9.2 模型

```text
LightGBM Classifier / Regressor
```

第一版不进入深度学习。

## 9.3 必做比较

```text
Market-only LightGBM
Document-only LightGBM
Combined LightGBM
```

## 9.4 研究核心问题

最重要的结论不是“模型 AUC 到多少”，而是：

```text
Performance(Combined) > Performance(Market-only) ?
```

如果成立，则支持：

> Multi-Agent 从招股书提取的文档风险，对传统 IPO / 市场变量提供增量预测信息。

如果不成立，也必须保留真实结果并进入 failure analysis，不通过修改 blind/test 数据口径制造提升。

## 9.5 Explainability

至少输出：

- global feature importance；
- SHAP summary（若依赖与运行条件允许）；
- 单 IPO feature contribution；
- document feature 与 market feature 的贡献拆分。

---

# 10. Phase CL-8：Market Agent MVP

## 10.1 定位

Market Agent 第一版不是新的预测器，也不重新训练模型。

它负责把：

```text
Model Prediction
+
Pre-IPO Market Context
+
Document Risks
+
Feature Contribution
```

解释成结构化 `MarketRiskAssessment`。

## 10.2 第一版输出

建议包含：

```text
market_risk_level
model_score
model_version
main_market_drivers
main_document_drivers
uncertainty_notes
supporting_feature_ids
```

## 10.3 约束

- 未经校准的模型输出不得表述为真实概率；
- Market Agent 不得修改底层模型预测；
- 不得创造不存在的 Evidence；
- 文档驱动因素必须能够追溯到 Document Risk / Evidence；
- 市场驱动因素必须能追溯到确定的模型输入。

---

# 11. Phase CL-9：Final Supervisor

## 11.1 目标

将 Document Intelligence 与 Market Intelligence 形成真正统一的 IPO 风险结论。

```text
Financial Agent ─┐
Legal Agent ─────┤
Business Agent ──┤
                 ↓
        Document Supervisor
                 ↓
        Document Risk Vector
                 ↓
          Prediction Model
                 ↓
           Market Agent
                 ↓
         Final Supervisor
                 ↓
          Final IPO Report
```

## 11.2 Final Supervisor 职责

- 合并 Document Risk 与 Market Risk；
- 标记一致信号与冲突信号；
- 提取主要风险驱动；
- 保留证据链；
- 输出总体等级 / score；
- 保留 model version、feature version、document analysis version。

## 11.3 不允许

- 无 Evidence 创造新的事实；
- 覆盖专业 Agent 的确定性计算；
- 将规则分、未经校准模型分数写成“真实下跌概率”；
- 为了让最终结论更一致而删除冲突信息。

---

# 12. Phase CL-10：完整 Streamlit E2E Demo

## 12.1 目标

优先展示整个系统真正能做什么，而不是继续做内部算法优化。

## 12.2 最小页面

1. IPO Overview；
2. Document Risks；
3. Financial / Legal / Business Agents；
4. Evidence & Calculations；
5. Market Prediction；
6. Final Risk Report。

## 12.3 完整用户流程

```text
上传 / 选择招股书
↓
解析
↓
三专业 Agent
↓
Verifier
↓
Document Supervisor
↓
Document Features
↓
Prediction Model
↓
Market Agent
↓
Final Supervisor
↓
可解释报告
```

## 12.4 Demo Gate

选取至少 3–5 个真实 IPO case：

- 至少包含不同年份；
- 至少包含不同风险结构；
- 至少有一个表现较弱案例；
- 至少有一个表现较好案例；
- 每个案例都能完整展示 Evidence → Risk → Feature → Model → Final Report。

完成该 Gate 后，项目首次被视为“完整闭环已经成立”。

---

# 13. v0.4-MVP 冻结标准

v0.4-MVP 不是以预测性能极致为发布条件，而以完整性和可信度为条件。

必须满足：

- PDF 到最终报告完整运行；
- Document Features 可重建；
- Market Data 与 Outcome 可重建；
- Model-ready dataset 可重建；
- Logistic baseline 可运行；
- 至少一个非线性模型可运行；
- Market Agent 可输出结构化解释；
- Final Supervisor 可输出统一报告；
- Streamlit 可展示完整链路；
- provenance / version / failure 状态可审计；
- 2025 blind 没有进入开发调优。

达到以上条件后，再冻结一个闭环版本，例如：

```text
v0.4.0-end-to-end-closed-loop
```

---

# 14. v0.5：闭环之后再做研究级优化

只有在 v0.4-MVP 完成后，重新打开以下工作流。

## 14.1 Retriever Optimization

- Retriever V3；
- BM25 / table-aware / dense lanes；
- Learning-to-Rank；
- Locked validation；
- per-risk failure analysis。

## 14.2 LLM Reranker

- micro-batch；
- candidate-level validation；
- partial fallback；
- semantic reranking；
- reliability telemetry。

## 14.3 Agent VNext

- Financial semantic extraction；
- Legal status / authority reasoning；
- Business multi-evidence reasoning；
- cross-domain risk composition。

## 14.4 Verifier VNext

- deterministic verification；
- semantic grounding verification；
- unsupported claim / hallucination metrics。

## 14.5 Fine-tuning

Fine-tuning 不作为近期必做项。只有当项目已经积累足够稳定的：

```text
candidate → expert judgment
agent output → verifier correction
risk reasoning → reviewed outcome
```

训练样本后，再评估 SFT / LoRA 的收益。

---

# 15. v0.6：正式评测与消融

完整系统至少比较：

```text
Baseline Document Pipeline
↓
+ Improved Retrieval
↓
+ LTR
↓
+ LLM Reranker
↓
+ Domain Agent VNext
↓
+ Semantic Verifier
↓
+ Final Supervisor
```

同时市场模型必须比较：

```text
Market-only
Document-only
Combined
```

建议最终形成统一表：

| System | Retrieval | Risk F1 | Evidence F1 | Market Metric | Unsupported Claim Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline |  |  |  |  |  |
| + Retrieval |  |  |  |  |  |
| + LLM |  |  |  |  |  |
| + Agent VNext |  |  |  |  |  |
| Full System |  |  |  |  |  |

---

# 16. 时间切分与 Blind Policy

市场预测统一遵循：

```text
2020–2023
Development / Training

2024
Validation

2025
Blind Test
```

规则：

- 2020–2023 用于训练、CV、特征选择、阈值和超参数；
- 2024 用于模型选择与正式 validation；
- 模型和 feature policy 冻结后才允许打开 2025；
- 2025 一旦打开，不能继续根据结果调模型并再次称其为 blind；
- 如果 blind 暴露缺陷，必须记录为失败分析并建立新的后续验证设计。

---

# 17. 接下来严格执行的顺序

从当前状态开始，团队执行顺序固定为：

```text
1. Freeze current Document Intelligence
2. Build IPO-level Document Risk Features
3. Close minimum Market Data
4. Freeze 5D Outcome Policy
5. Build Model-ready Dataset
6. Run Logistic / Linear Baseline
7. Run LightGBM + Explainability
8. Implement Market Agent MVP
9. Implement Final Supervisor
10. Integrate Streamlit Full E2E
11. Run 3–5 Real IPO Demos
12. Freeze v0.4 End-to-End Closed Loop
13. Re-open Research Optimization in v0.5
14. Formal Evaluation / Ablation in v0.6
15. RC / v1.0
```

除非出现阻断闭环的 bug，否则不得在步骤 12 之前重新把主线切回 Retriever、LLM Fine-tuning 或其他局部优化。

---

# 18. 团队成功判定

本阶段真正要回答的不是：

> “我们的某一个 Retriever 或 LLM 指标是否已经最优？”

而是以下三个问题：

## 命题 A：完整系统能否运行

```text
Prospectus
→ Evidence
→ Multi-Agent Risks
→ Structured Features
→ Market Prediction
→ Explainable Report
```

## 命题 B：文档风险有没有预测增量

```text
Performance(Document + Market)
>
Performance(Market-only) ?
```

## 命题 C：结果是否可审计

用户能否从最终结论反向追踪：

```text
Final Risk
→ Model Driver
→ Document Risk
→ Calculation
→ Evidence
→ Prospectus Page
```

只有 A 完成，项目才算形成闭环；A+B 完成，项目形成研究价值；A+B+C 完成，项目才具备正式产品 / 比赛展示价值。

---

# 19. 当前下一项任务

当前下一阶段正式定义为：

> **CL-1 / CL-2：冻结现有 Document Intelligence，并生成第一版 IPO-level Document Risk Feature Dataset。**

在该数据集完成后，立即进入最小 Market Data 与 5D Outcome closure，不再等待 Retriever / LLM 的下一轮优化。
