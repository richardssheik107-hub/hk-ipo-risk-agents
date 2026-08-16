# HK IPO Risk Agents 后续闭环总计划

> Strategy: **End-to-End Closed Loop First**  
> Active target: **v0.4-MVP**  
> Principle: 先完成完整闭环并看到真实效果，再优化 Retriever、LLM、Agent 与模型。

## 1. 当前状态

### 已完成并冻结

v0.3 Document Intelligence 已具备真实 PDF 解析、Financial / Legal / Business 三专业 Agent、8 类正式风险、确定性 Skills、Specialized Verifier、Supervisor、Service、Streamlit 与可审计 Evidence / Calculation 链路。

Retriever V3 研究也已经进入主线历史，包括 BM25、table-aware candidate lane、LambdaMART LTR 和最终 Locked evaluation。该研究现在冻结，不阻塞 v0.4。

**治理约束：历史 Locked 10 已正式消费。** 后续不得基于该 10 case 调参后再次将其描述为 blind。v0.5 若重启 Retriever 研究，必须建立新的 unseen / external / temporal holdout。

### 当前 v0.4 readiness

以 `research/V04_DATA_READINESS.md` 为准：

- 官方 2020–2024 IPO universe：438 cases；
- IPO OHLCV：432 / 438 有 outcome coverage；
- authoritative Document Snapshot pipeline：已具备；
- latest readiness audit 时已存在 authoritative snapshots：0 / 438；
- HSI 历史：缺失；
- authoritative industry benchmark mapping / history：缺失；
- total-market turnover：缺失；
- `MODEL_READY_DATA_GATE`：仍 blocked。

因此当前工作不是重新优化 Retriever，而是把已有文档智能真正转成模型数据，并补齐第一版闭环所需的最小真实市场输入。

## 2. 最终闭环

```text
Prospectus PDF
    ↓
Parser + Current Stable Retriever
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
5D Outcome
    ↓
Model-ready Dataset
    ↓
Logistic / Linear Baseline
    ↓
LightGBM + Explainability
    ↓
Market Agent
    ↓
Final Supervisor
    ↓
Explainable IPO Risk Report
    ↓
Streamlit Full E2E
```

## 3. 当前范围控制

在 v0.4 闭环冻结前，以下工作不作为主线：

- 继续增加 Retriever 算法；
- Retriever V3 / Dense / Reranker 继续调参；
- LLM Fine-tuning / LoRA；
- 新增更多专业 Agent；
- 大规模 Prompt 重构；
- 深度学习市场模型；
- 大规模 UI 视觉重构。

仅以下情况允许打断主线：

1. 阻断完整闭环的 bug；
2. 数据泄漏；
3. 明显错误；
4. 不可复现 / provenance 缺失。

## 4. CL-1 — Freeze Current Document Intelligence

### 目标

把当前 v0.3 作为第一版生产基线，不以继续提高 Retriever 指标作为进入市场闭环的前提。

### Gate

- v0.3 全量测试通过；
- Mock / offline 路径可运行；
- 已冻结真实回归不退化；
- 公共 Schema 不被闭环开发破坏；
- failure 必须结构化记录。

当前状态：**READY / CURRENT**。

## 5. CL-2 — IPO-level Document Risk Features

### 目标

把 Agent 输出转换为一个 IPO 一行、可直接建模、可重建的 Document Risk Vector。

### 第一版原则

优先 20–40 个稳定、可解释、上市前可获得的特征；复用现有 Document Risk Snapshot / feature contract，不重新发明另一套风险口径。

至少覆盖：

```text
cash_runway
continuous_loss
revenue_growth
customer_concentration
supplier_concentration
redemption_rights
material_litigation_compliance
precommercial_product

financial / legal / business risk counts
critical / high counts
verified / needs_review counts
verified ratio
overall document risk score
```

### 必做

1. 批量运行 2020–2024 authoritative `enhanced_v2` snapshots；
2. 输出失败清单与 provenance；
3. 生成 deterministic `case_id × document_features` 表；
4. 重复运行得到相同语义结果。

### Gate

- 438-case materialization 有完整 coverage report；
- 每个失败 case 有明确 reason；
- feature schema/version 固定；
- 不含任何上市后信息。

当前状态：**CURRENT**。

## 6. CL-3 — Minimum Real Market Data Closure

### 目标

只补齐第一版模型真正需要的数据，不因为尚未拥有完整金融数据库而阻断闭环。

已有 IPO OHLCV 可支持 432 / 438 case 的 1D / 5D / 20D / 60D outcome 窗口。

第一版至少需要：

```text
case_id
stock_code
listing_date
offer_price
IPO 1D / 5D / 20D / 60D closes or returns
market benchmark series needed by the frozen target/features
source/version/checksum
```

完整 V04-3 market-X 仍缺 HSI、行业 benchmark mapping/history、全市场 turnover。处理原则是：

- 能以更小的、预先冻结的 feature subset 完成第一版闭环时，可以缩小 MVP market-X；
- 不得用错误代理变量伪造缺失源；
- 每个缺失 case / source 必须显式记录；
- 完整 feature contract 可在后续数据到位后扩展。

当前状态：**PARTIAL**。

## 7. CL-4 — Freeze 5D Outcome Policy

主任务：上市后 5 个交易日弱表现风险。

连续目标优先保存：

```text
return_5d
abnormal_return_5d
```

同时保留 1D / 20D / 60D 作为 robustness。

分类目标：

```text
poor_performer_5d
```

分类阈值只能使用 **2020–2023 Development** 分布决定；不得看 2024 validation 或 2025 blind 后再选阈值。

Gate：target policy、session convention、benchmark convention、missing rule 全部版本化。

## 8. CL-5 — Model-ready Dataset

最终形成：

```text
X_document
+
X_pre_ipo_market
+
y_post_ipo_outcome
```

正式冻结三套特征组：

```text
A. Market-only
B. Document-only
C. Document + Market
```

必须满足：

- 一个 IPO 一行；
- 无未来信息泄漏；
- feature / target / split manifest 固定；
- 原始输入可完整重建；
- 2025 target 不进入开发环境。

## 9. CL-6 — Baseline Models

先跑最简单、最可解释的基线：

- Classification：Logistic Regression；
- Regression：Linear / Ridge。

三组 A/B/C 使用完全相同的时间切分和评测口径。

主要指标：

- Classification：ROC-AUC、PR-AUC、F1、LogLoss、Brier、calibration；
- Regression：MAE、RMSE、Rank IC / Spearman（样本允许时）。

第一版 PASS 是“train → predict → evaluate 可复现且无泄漏”，不是任意设定一个高 AUC 门槛。

## 10. CL-7 — LightGBM + Explainability

在 baseline 跑通后再引入 LightGBM。

仍然比较：

```text
Market-only
Document-only
Combined
```

核心研究命题：

```text
Performance(Combined) > Performance(Market-only) ?
```

至少输出 global importance；若依赖和样本允许，再输出 SHAP summary 与单 IPO feature contribution。

若 Document Features 没有增量价值，保留真实结果并进入 failure analysis，不改 blind/test 口径制造提升。

## 11. CL-8 — Market Agent MVP

Market Agent 第一版不是新的预测器，只负责结构化解释：

```text
model_score
market_risk_level
main_market_drivers
main_document_drivers
uncertainty_notes
model_version
supporting_feature_ids
```

约束：

- 不改模型预测；
- 不创造 Evidence；
- 未校准 score 不写成真实概率；
- 文档驱动必须能回溯到 Risk / Evidence；
- 市场驱动必须能回溯到模型输入。

## 12. CL-9 — Final Supervisor

将 Document Intelligence 与 Market Intelligence 统一：

```text
Domain Agents
→ Document Supervisor
→ Document Risk Vector
→ Prediction Model
→ Market Agent
→ Final Supervisor
→ Final IPO Report
```

Final Supervisor 负责合并信号、保留冲突、提取主要 driver 和版本 provenance，不得删除不一致信息来“美化结论”。

## 13. CL-10 — Streamlit Full E2E

第一版页面只需：

1. IPO Overview；
2. Document Risks；
3. Domain Agents；
4. Evidence & Calculations；
5. Market Prediction；
6. Final Report。

Demo 至少选 3–5 个真实 IPO，覆盖不同年份、不同风险结构、较强和较弱市场表现，并完整展示：

```text
Evidence
→ Risk
→ Feature
→ Model Driver
→ Final Report
```

## 14. v0.4 冻结标准

v0.4 首先以完整性与可信度为发布标准：

- PDF → Final Report 完整运行；
- Document Features、Market Data、Outcome、Model-ready Dataset 均可重建；
- baseline 与 LightGBM 可运行；
- Market Agent / Final Supervisor 可输出；
- Streamlit 完整演示可用；
- provenance / version / failure state 可审计；
- 2025 blind 未参与开发调优。

达到后冻结：

```text
v0.4.0-end-to-end-closed-loop
```

## 15. v0.5 — Research Optimization

闭环完成后才重新打开：

- Retriever V3.x / hybrid / BM25 / table-aware / dense；
- Learning-to-Rank；
- LLM Reranker；
- Financial / Legal / Business Agent VNext；
- Semantic Verifier；
- Supervisor 深化；
- Fine-tuning feasibility。

Retriever 研究必须遵守：

```text
Development-only tuning
→ new unseen holdout
→ one frozen evaluation
```

历史 Locked 10 只作为已经发生的历史结果，不再承担 future blind validation 角色。

## 16. v0.6 — Formal Evaluation

完整系统至少做两组消融：

### Document Intelligence

```text
Baseline
→ Improved Retrieval
→ LTR
→ LLM Reranker
→ Agent VNext
→ Semantic Verifier
→ Full System
```

### Market Modeling

```text
Market-only
Document-only
Combined
```

统一报告 Retrieval、Risk、Evidence、Grounding、Market prediction、latency / fallback / reproducibility 等指标。

## 17. 时间切分与 Blind Policy

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

2025 只有在模型、feature policy、target policy 全部冻结后才能打开。一旦查看结果，不允许根据它继续调参并重新称其为 blind。

## 18. 从现在开始的严格顺序

```text
1. Freeze Document Intelligence
2. Materialize 438-case authoritative snapshots
3. Build IPO-level Document Risk Features
4. Close minimum real market inputs
5. Freeze 5D outcome policy
6. Build model-ready dataset
7. Logistic / Linear baseline
8. LightGBM + Explainability
9. Market Agent
10. Final Supervisor
11. Streamlit Full E2E
12. 3–5 real IPO demos
13. Freeze v0.4
14. Re-open research optimization in v0.5
15. Formal evaluation in v0.6
```

当前下一项任务就是 **CL-1 / CL-2**。