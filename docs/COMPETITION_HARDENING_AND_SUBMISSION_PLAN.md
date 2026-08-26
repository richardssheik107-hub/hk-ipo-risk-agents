# Competition Hardening and Submission Plan

本文件把赛题要求映射到当前系统能力、Metric Protocol 与最终验收产物。当前状态以 `V0.4_RELEASE_ACCEPTANCE.md` 为准；指标定义以 `COMPETITION_METRIC_PROTOCOL.md` 为准。

## 1. 官方要求 → 项目 Metric v1

赛题原文件明确要求：

```text
关键风险要素抽取准确率 >=80%
关键证据片段召回率 >=85%
Agent / role / tool / evidence traceability =100%
逻辑解释有效性高
1D / 5D / 20D / 60D 上市后验证
5D 显著下跌识别更高权重
```

原文件没有规定 Accuracy 的唯一公式、Evidence 的 Top-K、5D 阈值或 Explanation rubric，因此项目已在 Validation 重评前冻结 `v045_competition_metric_protocol_v1`。

正式口径：

| Metric | Primary | Threshold / rule |
|---|---|---|
| M1 Risk | attribute-correct positive Gold Risk Unit Accuracy | official >=0.80，project target >=0.85 |
| M1 guardrail | Positive Recall / Macro F1 | project >=0.82 / >=0.82 |
| M2 Evidence | Evidence Group Coverage Recall | official >=0.85，project target >=0.88 |
| M2 diagnostics | Recall@1/@3/@5/@10/@20 | secondary only |
| M3 Trace | accounted traceability | =1.0 |
| M4 Explanation | 5-dimension human rubric | project mean >=4.0/5 |
| M5 Outcome | 1D/5D/20D/60D + primary 5D | `return_5d <= -0.10` frozen definition |

## 2. CH-1 — M5 Multi-horizon validation

**Owner：D；Status：OPEN / P0**

最低交付：

```text
return_1d
return_5d
return_20d
return_60d
significant_drop_5d = (return_5d <= -0.10)
```

结果文件：

```text
test_predictions.csv
multi_horizon_results.csv
evaluation_summary.json
ai_vs_offline_report.json
```

`evaluation_summary.json` 至少报告：

```text
metric_protocol_version
five_day_metrics.precision
five_day_metrics.recall
five_day_metrics.f1
five_day_metrics.pr_auc
five_day_metrics.roc_auc
five_day_metrics.top_10pct_hit_rate
five_day_metrics.top_20pct_hit_rate
base_prevalence
blind_2025_y_accessed=false
```

Robustness 额外使用 Development return_5d bottom-20% cutoff，只允许从 2020–2023 Development 计算一次并冻结。

赛题没有给 5D 指标绝对及格线，因此不伪造“官方阈值”。重点看协议固定、完整、可复现，以及 relative to base-rate / document-only / market-only / combined 的业务参考价值。

## 3. CH-2 — M1/M2 Document Intelligence benchmark

**Owner：B；Status：OPEN / P0**

当前旧 10-case governed offline diagnostic baseline：

```text
Risk P/R/F1                   0 / 0 / 0
Evidence Recall@1/@3/@5      20% / 20% / 20%
Physical-page correctness    100%
Real LLM cases               0
```

这些事实保留，但**旧 Recall@5 不再等同于官方 Evidence Recall >=85%**。

### 3.1 M1 primary risk families

```text
redemption_rights
related_party_transaction
customer_concentration
supplier_concentration
cash_burn_pressure
```

其中 related-party 使用 additive competition sidecar；cash-burn family 映射既有 `cash_runway`/deterministic calculation，不改 frozen risk registry。

### 3.2 M1 evaluator

Development Gold 采用 positive Gold Risk Unit：

```text
risk family
required attributes
accepted Evidence Groups
reviewer provenance
```

Primary：

```text
attribute-correct extracted positive Gold Units
/ all positive Gold Units
```

PASS：>=80%；内部目标 >=85%。同时要求 Positive Recall / Macro F1 >=82%，防止 negative-heavy accuracy 或单一风险刷分。

### 3.3 M2 evaluator

Human Gold 按支撑事实建立 Evidence Group，一个 group 可包含多个等价段落/表格/页码。

Primary：

```text
covered Gold Evidence Groups / all Gold Evidence Groups >=85%
```

Primary 不固定 Top-5。

工程诊断：

```text
Candidate Recall@20 >=95%
Reranked Recall@10   >=90%
Recall@1/@3/@5/@10/@20 all reported
```

### 3.4 Execution order

```text
same/fixed Development allowlist
→ real-LLM measurement first
→ freeze prediction
→ evaluate
→ classify failure:
   retrieval candidate miss
   ranking miss
   semantic extraction miss
   normalization/reconciliation miss
   verifier reject
   Gold ambiguity
→ Development-only targeted remediation
→ rerun same protocol
```

20 fixed Development cases 为 metric-v1 target；当前 10 cases 可纳入，补充 coverage 前先冻结 allowlist。Gold 至少 2 人交叉复核。

## 4. CH-3 — Market Intelligence

**Owner：C；Status：IMPLEMENTATION CLOSED / FINAL-MATRIX VALIDATION REMAINS**

最终只确认：

- final 3-case Core materialization 可读；
- Core-only 不 crash；
- Extended 只有真实 governed artifact 才启用；
- industry mapping 缺失继续 PIT-blocked；
- Market LLM 不产生输入里不存在的数字；
- Market trace 每个 event 有 namespaced governed input / Calculation / explicit no-Evidence reason。

不新增 ComparableIPOSkill，不为 M5 临时发明不可证明 PIT 的 feature。

## 5. CH-4 — Multi-Agent / M3 / M4

**Owner：E；Status：IMPLEMENTATION CLOSED / FINAL ACCEPTANCE OPEN**

现有链：

```text
Agent outputs
→ deterministic conflict detection
→ one bounded targeted re-check
→ retriever / verifier challenge
→ LLM Final Supervisor
→ deterministic fallback
→ TraceEvent
```

### M3 Traceability

当前 3-case offline = 1.0 / 1.0 / 1.0。最终还要求：

```text
Development real-LLM benchmark traceability = 1.0
final 3-case real-provider traceability = 1.0
```

LLM event 必须保留 provider/model/prompt/request/hash/latency。

### E1 Real-provider arbitration

只有 real provider + accepted + complete call trace + scope passed 才算 Gate E1；mock/fallback/failure 不算。

### M4 Explanation Quality

最终生成：

```text
explanation_quality.json
```

五维：Evidence grounding / Logical consistency / Conflict handling / Re-check quality / Final conclusion。

至少 2 名人类 reviewer；LLM 只能辅助。内部目标 mean >=4.0/5，正式案例 minimum >=3.0/5。

## 6. CH-5 — Product / Evidence / Human Review

**Owner：E；Status：CLOSED AS PRODUCT IMPLEMENTATION**

五个比赛工作区继续保留。Evidence Viewer page grounding 可用；bbox 为 P2，不允许 UI 自己生成坐标。

## 7. CH-6 — Formal evaluation / freeze

**Owner：A + B/C/D/E；Status：FINAL EXECUTION OPEN**

最终 handoff 必须使用 metric protocol v1：

```text
B: metric-v1 risk/evidence summary + CSV + ai_vs_offline
C: final matrix market trace
D: 1D/5D/20D/60D + frozen 5D metrics
E: 3-case real-provider + explanation_quality.json
A: Blind / provenance / determinism / readiness / artifact index / package
```

当前 A tooling 已实现，但 final freeze 不允许把 legacy-only B bool 或 Recall@5 解释成 metric-v1 PASS。最终 A integration 必须确认 handoff 中有 `metric_protocol_version=v045_competition_metric_protocol_v1`。

最终产物：

```text
risk_benchmark.csv/json
evidence_benchmark.csv/json
ai_vs_offline_report.json
test_predictions.csv
multi_horizon_results.csv
evaluation_summary.json
explanation_quality.json
agent_reasoning_logs
Evidence / Human Review exports
3 case reports
blind_audit.json
provenance_audit.json
determinism_audit.json
submission_readiness.json
artifact_index.json
submission bundle + manifest + SHA-256
```

## 8. Submission story

允许强调：Evidence-first、structured LLM、deterministic calculations、PIT Market facts、real conflict/re-check、measured traceability、Human Review、graceful degradation、predeclared metric protocol。

禁止宣称：

- 旧 Recall@5=20% 等于官方 Evidence Recall 当前值；
- 80% 指标可以靠大量 true negative 计算；
- uncalibrated score 是 probability；
- 5D -10% 是命题方官方阈值；
- 5D 指标有命题方未给出的绝对及格线；
- fallback 是 successful remote LLM arbitration；
- 3-case E2E = 预测准确。

## 9. Scope freeze

提交前不做 broad model search、大规模 Retriever 重写、历史行业 mapping 研究、full 438-case LLM、presentation-only expansion、PR-F 替代训练。

任何新代码必须直接关闭 M1/M2/M3/M4/M5 或 B/C/D/E/A final hard Gate。
