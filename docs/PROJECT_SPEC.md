# Project Specification — Competition Scope

## 1. 产品目标

从港股 IPO 招股书、上市前受治理市场数据和冻结模型信号出发，输出：

- 方向性风险预警；
- 财务、法务、业务和市场诱因归因；
- 原 PDF 页码、段落、表格与截图；
- Agent / Tool / Evidence 可追踪链；
- 上市后 1D / 5D / 20D / 60D 业务验证；
- 可运行原型、API 或可复用 Skill。

系统不是让单个 LLM 自由阅读整份 PDF 后写结论，而是：

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

正式主链当前覆盖：

- cash runway / cash-burn mapping；
- continuous loss；
- revenue growth；
- customer concentration；
- supplier concentration；
- redemption rights；
- material litigation / compliance；
- precommercial product。

比赛展示还需补齐：

- core pipeline progress；
- text embellishment / 风险因素粉饰度；
- related-party transaction；
- comparable IPO valuation。

无 Existing Gold 的新增能力必须作为 versioned runtime capability 与 qualitative demonstration，不混入 M1/M2 正式分母。

### 多智能体

- Financial Agent；
- Legal Agent；
- Business Agent；
- Market Agent；
- Final Supervisor；
- reusable Skills；
- deterministic conflict detection；
- bounded re-check；
- Human Review。

### 产品

- 单家与批量分析；
- Evidence Viewer；
- Agent collaboration trace；
- Human Review；
- 风险穿透报告；
- PDF 高亮截图；
- API / Streamlit；
- submission artifacts。

## 3. 不可破坏原则

### Evidence

- 正式风险必须引用本次运行真实 Evidence；
- LLM 不能引用输入作用域外的 Evidence ID；
- page / bbox 不在 UI 层猜测；
- bbox 缺失时明确 unavailable；
- 未召回证据不能伪造“无风险”。

### Calculation

- 财务数值、比率、runway 和收益标签由 deterministic Python 计算；
- LLM 只解释，不是权威数学来源。

### Market / PIT

- 只使用决策时点可获得的 market facts；
- missing 保持 null + reason；
- 不用未来行、zero fill 或未经证明的 proxy。

### Model

- frozen score 只能称 `uncalibrated_model_score`；
- authentic handoff 缺失时 channel unavailable；
- 不为 UI 完整而伪造 score 或 SHAP。

### Split / Gold

```text
2020–2023 Development
2024 Validation
2025 Blind
```

- Existing Gold 不新增、不修改；
- `UNJUDGED` 不当 negative；
- Gold 不输入 runtime；
- Validation 只在冻结后一次性运行；
- 未来开发不使用 2025 Blind 输入或 outcome。

## 4. 指标

```text
M1 Existing-Gold Risk Accuracy >=0.80
M2 Existing-Gold Evidence Coverage Recall >=0.85
M3 Traceability =1.0
M4 human-review explanation rubric
M5 1D / 5D / 20D / 60D；5D 重点
```

Recall@1/@3/@5/@10/@20 是诊断，不是官方额外门槛。

## 5. 当前 runtime

### Document

- PyMuPDF / table-aware parser；
- keyword / domain-aware retrieval；
- Financial deterministic-first；
- Legal structured LLM；
- Business hybrid deterministic + LLM；
- specialized Verifier；
- Document Supervisor。

### Role-B v0.4.6 diagnostic lane

- offline baseline；
- real-LLM shadow probe；
- immutable local journal；
- replay-only gated result；
- structured smoke；
- Financial high-recall adapter；
- retrieval / risk waterfall；
- monotonicity report。

该 lane 默认不替换 production runtime，只有显式 opt-in 才运行。

### Market / Supervision

- governed MarketContext；
- IPOHeatSkill / MarketRegimeSkill；
- bounded Market LLM；
- optional authentic frozen model signal；
- conflict / re-check / Verifier challenge；
- Final Supervisor + deterministic fallback；
- Trace / Human Review / Report。

## 6. 当前限制

- fixed-10 M1/M2 远低于门槛；
- v0.4.6 尚缺完整测量；
- Redemption Rights 仍主要依赖 keyword topK；
- 中间 candidate 生命周期 trace 不完整；
- Market strict contract 1/3；
- Final Supervisor accepted 2/3；
- M4 0/6；
- parser bbox / Evidence screenshot 未闭环；
- 赛题中的管线、粉饰、关联、同行估值缺少完整展示；
- D 有物化证据，但当前 5D 业务效果弱。

## 7. 完成定义

完整条件见 `V0.4_RELEASE_ACCEPTANCE.md` 和 `COMPETITION_CLOSURE_PLAN.md`。fixed-10 达标、某个实现存在或某份文件名含 PASS，都不能单独证明 `COMPETITION_READY`。
