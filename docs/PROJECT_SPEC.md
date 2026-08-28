# Project Specification — Competition Scope

## 1. 产品目标

从港股 IPO 招股书、上市前受治理市场数据和冻结模型信号出发，输出方向性风险预警、财务/法务/业务/市场归因、原 PDF Evidence、Agent Trace、上市后多周期验证和可运行原型。

系统是受约束的 Agentic AI 工作流：

```text
PDF → governed Evidence → specialized analysis → verification
+ governed market context / Skills
+ optional authentic frozen model signal
→ conflict / re-check / final supervision
→ trace / human review / report
→ M1–M5 evaluation / submission gate
```

## 2. 赛题能力范围

### 文档风险

当前正式主链覆盖 cash runway、continuous loss、revenue growth、customer/supplier concentration、redemption rights、material litigation/compliance 和 precommercial product。

比赛展示还需补齐 core pipeline progress、text embellishment、related-party transaction 和 comparable IPO valuation。无 Existing Gold 的新增能力作为 versioned capability 与 qualitative demonstration，不混入 M1/M2 分母。

### 多智能体与产品

Financial、Legal、Business、Market、Final Supervisor、Skills、conflict/re-check、Human Review、单家/批量分析、Evidence Viewer、Trace、report、Screenshot、API/Streamlit 与 submission artifacts。

## 3. 不可破坏原则

- 正式风险引用真实 Evidence；LLM 不能越 scope；page/bbox 不由 UI 猜；
- 财务数值、比率、runway 和 outcome 由 deterministic Python 计算；
- Market 只使用 PIT-safe facts，missing 不补零或 proxy；
- frozen score 只能称 `uncalibrated_model_score`；
- Existing Gold immutable，Gold 不进 runtime，`UNJUDGED` 不当 negative；
- Validation freeze 后 one-shot；从现在起 Blind 输入和 outcome 都不用于优化。

## 4. 指标

```text
M1 Existing-Gold Risk Accuracy >=0.80
M2 Existing-Gold Evidence Coverage Recall >=0.85
M3 Traceability =1.0
M4 human-review explanation rubric
M5 1D / 5D / 20D / 60D；5D 重点
```

Recall@K 是诊断，不是官方额外门槛。

## 5. 当前 runtime 与诊断

### Document

PyMuPDF/table-aware parser、keyword/domain-aware retrieval、Financial deterministic-first、Legal structured LLM、Business hybrid、Verifier、Document Supervisor。

### B v0.4.6

Offline/shadow/gated、LLM journal、structured smoke、Financial high-recall、waterfall、monotonicity，以及 persisted-result read-only Evidence auditor。该 lane 显式 opt-in，不静默替换 production runtime。

### Market / Supervision

Governed MarketContext、IPOHeatSkill/MarketRegimeSkill、bounded Market LLM、optional authentic model signal、conflict/re-check、Final Supervisor、Trace、Human Review、Report/UI。

### D model tracks

- frozen PR-F：正式 receipt 和 product identity；
- v2 candidate：Development-selected、2024 one-shot evaluated、未晋升。

若晋升 v2，必须创建新的 freeze/decision/artifact/handoff，不能覆盖 frozen PR-F 身份。

## 6. 当前限制

- fixed-10 M1/M2 远低于门槛；
- v0.4.6 尚缺完整测量与 lifecycle trace；
- Market strict 1/3、Final accepted 2/3、M4 0/6；
- parser bbox / Evidence screenshot 未闭环；
- 管线、粉饰、关联、同行估值缺少完整展示；
- D v2 有明显高召回改善，但 ROC-AUC 仍低于 0.5，且 promotion 未决。

## 7. 完成定义

完整条件见 `V0.4_RELEASE_ACCEPTANCE.md` 和 `COMPETITION_CLOSURE_PLAN.md`。fixed-10 达标、某个实现存在、候选指标更好或某份文件名含 PASS，都不能单独证明 `COMPETITION_READY`。
