# Competition Metric Protocol v1

> Protocol ID: `v045_competition_metric_protocol_v1`
>
> Scope: v0.4.5 competition evaluation and final submission
>
> Status: **FROZEN BEFORE 2024 VALIDATION RE-EVALUATION**

本文件把赛题中没有给出完整 evaluator 细节的指标，转换成一套预先声明、可复现、可审计的比赛评价协议。它不是对命题方公式的“官方解释”；它是本项目在不事后挑口径的前提下，对官方要求做出的透明对齐方案。

赛题原文件明确要求：

- 关键风险要素抽取准确率 `>= 80%`；
- 关键证据片段召回率 `>= 85%`；
- Agent 推理链路、角色分工、工具调用记录和证据来源可追踪率 `= 100%`；
- 逻辑解释有效性高；
- 用上市首日、5D、20D、60D 真实表现验证预警价值，其中 5D 显著下跌识别给予更高权重。

原文件没有规定：Risk Accuracy 的唯一公式、Evidence 是否采用 Top-K、K 等于多少、5D“显著下跌”的阈值、解释质量的打分表。因此本协议在打开新的 Validation 结果前先冻结这些定义。

## 1. Split 与 anti-tuning 规则

```text
2020–2023  Development
2024       Validation
2025       Blind
```

规则：

- Development：可以标注、诊断、改代码/Prompt、做 targeted remediation；
- Validation：只做冻结方案的一次性确认，不根据 2024 结果回头改阈值/Prompt/模型；
- Blind：未正式授权前不读取 2025 outcome/y；
- metric definition、Gold schema、case allowlist、阈值和 evaluator 版本必须在 Validation 重评前冻结；
- 不允许看完 Validation 再选择“最好看的 Accuracy / Recall / 5D threshold”。

当前 10-case Role-B offline benchmark 继续保留为历史诊断基线；它不等同于本协议的最终 official-aligned competition benchmark。

## 2. M1 — 关键风险要素抽取

### 2.1 Competition-aligned core risk families

赛题点名“包括但不限于”对赌/赎回、关联交易、客户或供应商集中度、现金流消耗压力。为形成可复现 evaluator，本协议将以下 5 类作为 **competition primary risk families**：

| Competition family | 当前项目映射 | 说明 |
|---|---|---|
| `redemption_rights` | existing Legal risk | 对赌/赎回条款 |
| `related_party_transaction` | additive competition sidecar | 不修改 frozen baseline risk identity |
| `customer_concentration` | existing Financial risk | 客户集中度 |
| `supplier_concentration` | existing Financial risk | 供应商集中度 |
| `cash_burn_pressure` | mapped from `cash_runway` / deterministic cash-burn calculation | 比赛评价族，不静默重命名 frozen `cash_runway` |

`material_litigation_compliance`、`precommercial_product`、`continuous_loss`、`revenue_growth` 等继续作为系统能力与扩展报告项，但不替代上述 5 个 primary families 的覆盖。

### 2.2 Gold Risk Unit

一个 Gold Risk Unit 至少包含：

```text
case_id
risk_family
applicable
required_attributes
accepted_evidence_groups[]
annotation_status
reviewer_provenance
```

- `applicable=true` 的单位进入 Primary Accuracy 分母；
- `applicable=false` 的单位用于 false-positive / precision 统计，但不允许通过大量 true negative 把 Primary Accuracy 刷高；
- 数值字段按 deterministic exact/tolerance rule 判定；
- 枚举/状态字段按 canonical value 判定；
- 条款语义字段按预先写明的 canonical semantic criteria 判定；
- 一个正式“正确抽取”必须同时有正确 risk family、关键属性满足规则，并至少命中一个支撑该 Risk Unit 的 Evidence Group。

### 2.3 Primary metric

```text
Official-aligned Risk Extraction Accuracy
= attribute-correct extracted positive Gold Risk Units
  / all positive Gold Risk Units
```

Official pass line：

```text
>= 0.80
```

Project safety target：

```text
>= 0.85
```

### 2.4 Anti-gaming guardrails

同时必须报告：

```text
Precision
Positive Risk Recall
Macro F1
Per-risk support / Precision / Recall / F1
```

内部 guardrail：

```text
Positive Risk Recall >= 0.82
Macro F1             >= 0.82
```

这两个 0.82 是项目内部质量线，不冒充赛题官方阈值；其作用是防止只靠高频风险或 negative case 获得漂亮 Accuracy。

### 2.5 Benchmark case plan

Development 最终 metric-v1 benchmark 目标：

```text
20 fixed Development cases
5 primary risk families
fixed allowlist before final remediation
```

- 当前 10 个 governed Development cases 可纳入其中，但不足部分需补齐；
- 尽量保证每个 primary family 至少 5 个 positive Gold Units；若真实 Development 数据不足，不人工制造 positive，改为使用全部可得 positive 并明确 support；
- Gold 至少由 2 名 reviewer 完成独立/交叉复核，争议项在 prediction freeze 前解决；
- Development 闭合后，再对固定 2024 Validation subset 做一次性复核；不得用 Validation 作为第二开发集。

## 3. M2 — 关键 Evidence Recall

### 3.1 官方要求不等于 Recall@5

赛题原文件只要求“关键证据片段召回率 >=85%”，没有规定 Top-K，也没有规定 K=5。

因此本项目正式拆成：

```text
Primary official-aligned metric:
Evidence Group Coverage Recall

Secondary diagnostics:
Recall@1 / @3 / @5 / @10 / @20
```

当前 offline `Evidence Recall@5 = 20%` 仅保留为旧 benchmark 的诊断事实：它不是 real-LLM 指标，也不能再被直接解释为“官方 85% 指标的当前值”。

### 3.2 Evidence Group

Human Gold 不把招股书中所有重复出现的句子机械当成独立必命中片段，而按“支撑事实”形成 Evidence Group。

例如一个赎回风险可以有：

```text
Group A: 赎回权存在
Group B: 触发条件
Group C: 权利主体
Group D: 上市前是否终止/失效
```

同一 Group 可以包含多个等价段落、表格或页码锚点。系统命中其中一个被预先认可的等价证据，即覆盖该 Group。

### 3.3 Primary metric

```text
Evidence Group Coverage Recall
= covered Gold Evidence Groups
  / all Gold Evidence Groups
```

Official pass line：

```text
>= 0.85
```

Project safety target：

```text
>= 0.88
```

Primary metric **不设置固定 Top-5 上限**。

### 3.4 Retrieval stage diagnostics

为了知道 85% 卡在哪一层，内部使用分阶段目标：

```text
Candidate Retrieval Recall@20 >= 0.95
Reranked Recall@10           >= 0.90
Final Evidence Group Recall  >= 0.88 project target
```

这些是项目内部诊断/工程目标，不是官方额外阈值。

最终 RiskItem Evidence 不再规定“永远只能 5 条”；可以根据风险复杂度与证据多样性动态保留足够证据。Top-K 指标继续用于评价排序效率，而不是替代官方对齐的 Coverage Recall。

## 4. M3 — Traceability

Official target：

```text
100%
```

一个 relevant TraceEvent 只有在满足以下之一时才算 accounted：

```text
agent/action/tool-or-skill identity recorded
AND
Evidence reference
OR Calculation reference
OR explicit no_evidence_reason
```

涉及远程 LLM 的事件还必须保留：

```text
provider
model
prompt_version
request_id
raw_response_hash
latency_ms
```

最终 Gate：

```text
Development real-LLM benchmark traceability = 1.0
AND
final 3-case matrix traceability = 1.0
```

当前 3-case offline matrix 的 1.0 是已完成工程事实；后续重点是防回归，并在 real-provider run 上继续保持 1.0。

## 5. M4 — Explanation Quality

赛题要求“逻辑解释有效性高”，但没有给出固定数值阈值。本项目采用 5 维、每维 1–5 分的 rubric：

| Dimension | 评价内容 |
|---|---|
| Evidence grounding | 关键结论是否有真实、相关 Evidence/Calculation 支撑 |
| Logical consistency | 推理前后是否自洽，不自相矛盾 |
| Conflict handling | Agent 冲突是否被准确识别、说明 |
| Re-check quality | 为什么复核、复核什么、结果如何影响结论是否清楚 |
| Final conclusion | Final Supervisor 是否从已知事实推出结论且不越权 |

评审规则：

- 至少 2 名人类 reviewer；
- LLM reviewer 只能辅助，不作为唯一评分人；
- 记录 per-case score、reviewer id/role、分歧与 resolution；
- project target：平均分 `>=4.0/5`；任何正式展示案例不得 `<3.0/5`。

这组数值是内部质量 Gate，不声称为命题方官方阈值。

## 6. M5 — 上市后风险预警

### 6.1 必须输出的 horizon

```text
return_1d
return_5d
return_20d
return_60d
```

5D 为 Primary business horizon；1D/20D/60D 是完整性与稳健性 horizon。

### 6.2 `significant_drop_5d` 定义

赛题没有规定“显著下跌”的数值阈值。本协议预先固定 Primary 定义：

```text
significant_drop_5d = (return_5d <= -0.10)
```

同时提供 robustness definition：

```text
Development return_5d bottom 20% cutoff
```

Robustness cutoff 只能从 2020–2023 Development 计算一次并冻结；不得根据 2024 Validation 重新选择。

### 6.3 5D metrics

至少报告：

```text
Precision
Recall
F1
PR-AUC
ROC-AUC
Top-risk-bucket hit rate (Top 10% / Top 20%)
base prevalence
```

赛题没有给 5D 指标的绝对合格线，因此项目**不伪造一个“官方 0.xx 才算 PASS”**。最终 readiness 要求：

- 指标完整、协议固定、可复现；
- 与 no-skill/base-rate 和可用的 document-only / market-only / combined baseline 做透明比较；
- 重点优化 5D，但不能在 2024 Validation 上 post-hoc 选阈值、反转 score 或重新训练 frozen PR-F。

如果融合模型没有稳定提升，也要如实报告“有限 predictive increment”，而不是修改评价口径。

## 7. Optimization order

比赛收口的优化顺序固定为：

```text
P0  B: real-LLM measurement first
    → Retrieval candidate coverage
    → Evidence ranking / group coverage
    → Structured extraction
    → Candidate reconciliation
    → Verifier
    → M1/M2 rerun on Development

P0  D: freeze 5D definition
    → materialize 1D/5D/20D/60D
    → primary 5D evaluation + baselines

P1  E: final real-provider 3-case acceptance
    → explanation-quality rubric
    → traceability remains 100%

P1  C: final-matrix governed Market validation only
    → no new broad market feature scope

P1  A: consume frozen metric-v1 artifacts
    → readiness / Blind / provenance / determinism
    → final metric dashboard / package / release
```

禁止五条 lane 同时为了“提分”修改公共 contract。

## 8. Required final metric artifacts

Role B 至少需要在 `document_benchmark_summary.json` 中提供 metric-v1 字段：

```text
metric_protocol_version = v045_competition_metric_protocol_v1
risk_extraction.official_aligned_accuracy
risk_extraction.precision
risk_extraction.positive_recall
risk_extraction.macro_f1
risk_extraction.per_risk

evidence_coverage.group_coverage_recall
evidence_coverage.gold_group_count
evidence_coverage.covered_group_count
retrieval_diagnostics.recall_at_1/3/5/10/20
```

Role D 的 `evaluation_summary.json` 至少提供：

```text
metric_protocol_version
significant_drop_5d_definition = return_5d <= -0.10
five_day_metrics.precision
five_day_metrics.recall
five_day_metrics.f1
five_day_metrics.pr_auc
five_day_metrics.roc_auc
five_day_metrics.top_10pct_hit_rate
five_day_metrics.top_20pct_hit_rate
blind_2025_y_accessed = false
```

Role E 最终额外提供：

```text
explanation_quality.json
```

至少含：

```text
metric_protocol_version
human_reviewer_count
mean_score
minimum_case_score
per_case_scores
```

A 最终 readiness 只消费这些真实 artifact；missing 字段、legacy-only Recall@5、offline-only B benchmark 均不能被解释成 metric-v1 PASS。

## 9. Current baseline interpretation

截至本协议冻结时：

```text
Role-B 10-case offline:
Risk P/R/F1 = 0/0/0
Evidence Recall@1/@3/@5 = 20/20/20%
Real LLM cases = 0

Final 3-case offline:
Traceability = 1.0 / 1.0 / 1.0
Real-provider Final Supervisor accepted = 0/3

D final 1D/5D/20D/60D submission artifact = not yet closed
```

这些数值保持原始实测含义，不因新协议被重写。新协议只改变**从现在开始怎样定义最终比赛达标**。

## 10. Competition-ready metric condition

```text
M1 Official-aligned Risk Extraction Accuracy >= 0.80
AND project anti-gaming guardrails recorded and passed
AND M2 Evidence Group Coverage Recall >= 0.85
AND M3 Traceability = 1.0
AND M4 Explanation Quality artifact meets internal rubric gate
AND M5 1D/5D/20D/60D + frozen 5D evaluation are complete
AND all split/Blind/provenance rules pass
```

只有以上条件与其他 B/C/D/E/A hard Gate 同时关闭，才允许 `COMPETITION_READY`。
