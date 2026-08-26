# Competition Hardening and Submission Plan

本文件把赛题要求映射到当前系统能力、Metric Protocol 与最终验收产物。当前状态以 `V0.4_RELEASE_ACCEPTANCE.md` 为准；指标定义以 `COMPETITION_METRIC_PROTOCOL.md` 为准。

## 1. 官方要求 → Project Metric v2

赛题原文件明确要求：

```text
关键风险要素抽取准确率 >=80%
关键证据片段召回率 >=85%
Agent / role / tool / evidence traceability =100%
逻辑解释有效性高
1D / 5D / 20D / 60D 上市后验证
5D 显著下跌识别更高权重
```

项目当前协议：

```text
v045_competition_metric_protocol_v2_existing_gold_only
```

v2 的关键 scope freeze：

> **M1/M2 只使用比赛收尾前已经存在并冻结的 Expert Annotation / Oracle Gold。此后不补标、不扩样、不修改旧 Gold、不人工重做 Evidence Group。提升 M1/M2 的唯一手段是 Development 上的代码与真实 LLM 链路优化。**

现有 Gold inventory：

```text
annotation inventory   101
valid annotations      100
official materialized   98
```

最终真正 evaluable support 由只读程序统计。

正式口径：

| Metric | Primary | Threshold / rule |
|---|---|---|
| M1 Risk | Existing-Gold positive Risk Unit Accuracy | official >=0.80，project target >=0.85 |
| M2 Evidence | Existing-Gold Evidence Coverage Recall | official >=0.85，project target >=0.88 |
| M2 diagnostics | Recall@1/@3/@5/@10/@20 | secondary only |
| M3 Trace | accounted traceability | =1.0 |
| M4 Explanation | current final product rubric | no new M1/M2 Gold work |
| M5 Outcome | 1D/5D/20D/60D + primary 5D | `return_5d <= -0.10` project definition |

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

至少报告 5D Precision / Recall / F1 / PR-AUC / ROC-AUC / Top-10% / Top-20% hit rate / base prevalence。赛题没有给绝对 5D 及格线，不为了过 Gate 事后创造阈值。

## 3. CH-2 — M1/M2 Document Intelligence benchmark

**Owner：B + A evaluator governance；Status：OPEN / P0**

### 3.1 Existing-Gold-only

旧 Gold 未明确判断的 `case × risk`：

```text
UNJUDGED
```

`UNJUDGED` 不当 negative、不进入 M1 分母。

Competition-priority risk mapping 仍保留：

```text
redemption_rights
related_party_transaction
customer_concentration
supplier_concentration
cash_burn_pressure
```

但 v2 只评价 Existing Gold 真正有 support 的部分：

```text
support = 0 -> NOT_EVALUABLE_FROM_EXISTING_GOLD
```

不再为了补齐五类新增 annotation。

### 3.2 M1 evaluator

```text
Existing-Gold Official-aligned Accuracy
= correct evaluable positive Existing-Gold Risk Units
  / all evaluable positive Existing-Gold Risk Units
```

PASS：`>=80%`；project target：`>=85%`。

必须披露 per-risk support。Precision / Macro F1 只有旧 Gold 本身提供足够 exhaustive positive/negative judgment 时才正式报告，否则 `NOT_AVAILABLE_FROM_EXISTING_GOLD`。

### 3.3 M2 evaluator

只使用旧 annotation 中已经存在的 Evidence/page/span/table/anchor。

```text
Existing-Gold Evidence Coverage Recall
= covered evaluable existing Evidence Units
  / all evaluable existing Evidence Units
```

PASS：`>=85%`；project target：`>=88%`。

允许 deterministic normalization / identity standardization / exact duplicate dedupe；禁止人工新增 Evidence 或重新做 semantic Evidence Group。

Recall@1/@3/@5/@10/@20 继续报告作为 diagnostics。历史 `Recall@5=20%` 只是旧 offline diagnostic。

### 3.4 Execution order

```text
Existing Gold read-only coverage audit
→ evaluable manifest + source hash
→ fixed small Development debug subset if needed
→ real-LLM run
→ evaluate
→ failure taxonomy
→ Development-only code / Retriever / Prompt / extraction / reconciliation / Verifier optimization
→ Full Existing Development Gold benchmark
→ freeze
→ Existing Validation Gold one-shot
```

不再有新的 20-case annotation target。

## 4. CH-3 — Market Intelligence

**Owner：C；Status：IMPLEMENTATION CLOSED / FINAL-MATRIX VALIDATION REMAINS**

最终只确认 Core/Extended governed behavior、PIT missingness、Market LLM no fabricated numbers、Market trace accounting。无可靠 source 时保持 unavailable，不新增 proxy。

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

M3：final real-provider traceability 必须 1.0。

E1：只有 real provider + accepted + complete call trace + scope passed 才算成功；mock/fallback 不算。

M4：沿用当前 explanation-quality 方案；本次 Existing-Gold-only 决策不增加任何新的 M1/M2 annotation task。

## 6. CH-5 — Product / Evidence / Human Review

**Owner：E；Status：CLOSED AS PRODUCT IMPLEMENTATION**

五个比赛工作区继续保留。page grounding 可用；bbox 为 P2，不优先于 M1/M2/M5/E1。

## 7. CH-6 — Formal evaluation / freeze

**Owner：A + B/C/D/E；Status：FINAL EXECUTION OPEN**

最终 handoff：

```text
B: Existing-Gold evaluable manifest + M1/M2 real-LLM results
C: final matrix market trace
D: 1D/5D/20D/60D + frozen 5D metrics
E: 3-case real-provider + current explanation-quality artifact
A: Blind / provenance / determinism / readiness / artifact index / package
```

B artifact 必须声明：

```text
metric_protocol_version = v045_competition_metric_protocol_v2_existing_gold_only
new_manual_annotations_added = false
existing_gold_modified = false
```

最终产物至少包括：

```text
existing_gold_evaluable_manifest.json
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

允许强调：

- Existing Expert Gold 在比赛收尾前已存在并冻结；
- 评价只读、分母固定；
- 不通过补标改变成绩；
- 提升来自真实 LLM / Retriever / extraction / Verifier 代码优化；
- Evidence-first、deterministic calculations、PIT Market facts、real conflict/re-check、measured traceability、Human Review。

禁止宣称：

- 旧 Recall@5=20% 等于官方 Evidence Recall 当前值；
- 未标注 risk 是 negative；
- 98 个 official materialized annotation 等于 98×全部 risk 都有 Gold；
- 为了比赛补过 Gold；
- uncalibrated score 是 probability；
- 5D -10% 是命题方官方阈值；
- fallback 是 successful remote LLM arbitration。

## 9. Scope freeze

提交前明确不做：

- **任何新的 M1/M2 人工标注、Gold 扩样或 Evidence 人工重组**；
- broad model search；
- full Retriever redesign；
- historical industry mapping research；
- full 438-case LLM；
- presentation-only expansion；
- PR-F 替代训练。

任何新代码都必须直接提高/验证 Existing-Gold M1/M2，或关闭 C/D/E/A final hard Gate。
