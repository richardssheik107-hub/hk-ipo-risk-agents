# Project Specification — v0.4.5 Competition Runtime

## 1. Product objective

从真实港股 IPO 招股书与受治理的上市前市场数据出发，产出可解释、可复核、可追溯的风险分析，并用上市后多周期结果验证预警价值。

系统不是“让一个大模型读完整 PDF 后自由写报告”，而是受约束的 Agentic AI 工作流：

```text
PDF → Evidence → specialized analysis → verification
+ governed market context
+ optional authentic frozen model signal
→ conflict / re-check / final supervision
→ trace / human review / report
→ Existing-Gold metric evaluation / submission gate
```

## 2. Non-negotiable invariants

### Evidence

- 正式风险必须引用本次运行真实 Evidence；
- LLM 不得引用输入作用域外的 Evidence ID；
- Evidence identity / page / bbox 不在 UI 层修补；
- 未检索到证据不能伪造“无风险”；
- final M2 primary metric 不固定 Top-5，而按 Existing-Gold Evidence coverage 评价。

### Calculation

- 精确财务数值、比率、runway 等由 deterministic Python 计算；
- LLM 只能解释 Calculation，不应成为权威计算来源。

### Market / PIT

- 市场事实只能来自 listing date 之前可得的 governed source；
- 缺失值保持 null + missing reason；
- 禁止 listing-day/future rows、静态未来分类、zero/proxy 伪装 PIT。

### Model

- frozen PR-F 分数语义为 `uncalibrated_model_score`；
- 不得称 probability；
- authentic per-case runtime/handoff 缺失时明确 unavailable；
- 不允许为了前端完整而重训、重构或翻转分数。

### Split / Blind

```text
2020–2023  Development
2024       Validation
2025       Blind
```

- Development 可以诊断与 targeted remediation；
- Validation 不做 post-hoc tuning；
- Blind outcome 未授权前不得访问；
- metric definition / Existing-Gold source manifest / threshold / evaluator 必须在 Validation 重评前冻结。

### Existing Gold

M1/M2 只使用比赛收尾之前已经存在并冻结的 Expert Annotation / Oracle Gold：

```text
annotation inventory   101
valid annotations      100
official materialized   98
```

禁止新增 M1/M2 人工 Gold、修改旧 Gold、把 UNJUDGED 当 negative、人工重做 Evidence Group。

## 3. Competition Metric Protocol v2

最终比赛评价采用：

```text
v045_competition_metric_protocol_v2_existing_gold_only
```

权威文档：`COMPETITION_METRIC_PROTOCOL.md`。

### M1 Risk extraction

Competition-priority mapping：

```text
redemption_rights
related_party_transaction
customer_concentration
supplier_concentration
cash_burn_pressure
```

但只有 Existing Gold 真正有 support 时才评价；support=0 时 `NOT_EVALUABLE_FROM_EXISTING_GOLD`，不补标。

Primary：

```text
Existing-Gold Official-aligned Accuracy
= correct evaluable positive Existing-Gold Risk Units
  / all evaluable positive Existing-Gold Risk Units
```

Official pass `>=0.80`，project target `>=0.85`。

Precision / Macro F1 只有 Existing Gold 本身足够 exhaustive 时才正式报告，否则 `NOT_AVAILABLE_FROM_EXISTING_GOLD`。

### M2 Evidence

Primary：

```text
Existing-Gold Evidence Coverage Recall >=0.85
```

Project target `>=0.88`。Recall@1/@3/@5/@10/@20 仅为 diagnostics。旧 offline `Recall@5=20%` 不直接代表官方 M2 当前值。

M2 只使用旧 annotation 已存在的 Evidence/page/span/table/anchor；允许 deterministic normalization 和 exact duplicate dedupe，不新增人工 Evidence。

### M3 Traceability

```text
=1.0
```

Development real-LLM 与 final 3-case real-provider 都必须达到 1.0。

### M4 Explanation Quality

沿用当前 final product explanation-quality 方案。本次 Existing-Gold-only 决策不增加 M1/M2 人工标注工作。

### M5 Outcome

必须完成：

```text
return_1d
return_5d
return_20d
return_60d
```

Primary 5D：

```text
significant_drop_5d = (return_5d <= -0.10)
```

赛题没有给 5D 绝对指标及格线，项目不虚构“官方 xx%”。

## 4. Frozen formal risk scope

冻结 formal baseline 仍是 8 个 risk codes：

Financial：`cash_runway`、`continuous_loss`、`revenue_growth`、`customer_concentration`、`supplier_concentration`。

Legal：`redemption_rights`、`material_litigation_compliance`。

Business：`precommercial_product`。

Competition-priority related-party / cash-burn 只作为 metric mapping / additive sidecar 语义，不静默改变 frozen baseline identity，也不为了比赛补新 Gold。

## 5. Current runtime components

### Document

- PyMuPDF / table-aware parser；
- bounded retrieval；
- Financial deterministic-first；
- Legal structured LLM；
- Business hybrid deterministic + structured LLM；
- specialized Verifier；
- deterministic Document Supervisor。

### Market

- frozen PR-B Market-X Core；
- optional governed Extended；
- IPOHeatSkill；
- MarketRegimeSkill；
- bounded Market LLM interpretation。

### Competition supervision

- deterministic conflict detection；
- one bounded targeted re-check；
- Verifier challenge；
- LLM Final Supervisor；
- deterministic fail-closed fallback；
- Agent / Tool / Evidence trace；
- Human Review sidecar。

### Product

五个 Streamlit workspaces：Risk Command Center、Evidence & AI Analysis、Market & Model、Agent Collaboration Trace、Human Review & Final Report。

## 6. Measured current state

### E2E engineering

3 个真实 2024 PDF：2410.HK / 2460.HK / 1318.HK，3/3 integrity verified、0 structured workflow errors、offline traceability 1.0。

### Document quality

旧 10-case governed offline Development diagnostic：

```text
Risk P/R/F1 = 0%
Evidence Recall@5 = 20%
Real LLM = 0
```

它不是 metric-v2 final benchmark，也不是 real-LLM benchmark。

下一步不是补 Gold，而是 Existing-Gold coverage audit → real-LLM Development run → code/Prompt optimization → Full Existing Development Gold benchmark。

### Market

Market Agent 已实现并接入 AI runtime；real-provider Market interpretation 已在真实 IPO 上验证。industry return 无可靠 PIT mapping 时继续 unavailable。

### Evaluation

multi-horizon foundation 已存在，但 final M5 artifacts 尚未关闭。

## 7. Completion definition

`COMPETITION_READY` 需要：

- Existing-Gold source / evaluable manifest frozen；
- M1 Existing-Gold Risk Accuracy >=80%；
- M2 Existing-Gold Evidence Coverage Recall >=85%；
- M3 real final traceability=100%；
- M4 current explanation-quality Gate；
- M5 1D/5D/20D/60D + frozen 5D evaluation；
- C final-matrix Market validation；
- E real-provider final matrix；
- final CI / Blind / provenance / determinism；
- reproducible Runbook / artifact index / submission package。

详细状态见 `V0.4_RELEASE_ACCEPTANCE.md`。
