# Competition Hardening and Submission Plan

> Status date: `2026-08-28`

本文件把赛题要求映射到当前系统能力、Metric Protocol 与最终验收产物。当前状态以 `V0.4_RELEASE_ACCEPTANCE.md` 为准；指标定义以 `COMPETITION_METRIC_PROTOCOL.md` 为准；操作顺序以 `V045_CURRENT_EXECUTION_PLAN.md` 为准。

## 1. 官方要求 → Project Metric v2

```text
protocol = v045_competition_metric_protocol_v2_existing_gold_only
```

| Metric | Primary | Threshold / rule |
|---|---|---|
| M1 Risk | Existing-Gold positive Risk Unit Accuracy | official >=0.80；target >=0.85 |
| M2 Evidence | Existing-Gold Evidence Coverage Recall | official >=0.85；target >=0.88 |
| M2 diagnostics | Recall@1/@3/@5/@10/@20 | secondary only |
| M3 Trace | accounted traceability | =1.0 |
| M4 Explanation | final product human-review rubric | two human reviewers per case |
| M5 Outcome | 1D/5D/20D/60D + primary 5D | `return_5d <= -0.10` project definition |

M1/M2 scope 已冻结：Existing Expert Gold only，不补标、不扩样、不改旧 Gold、不把 `UNJUDGED` 当 negative。

## 2. CH-1 — M5 Multi-horizon validation

**Owner：D；Status：PASS RECORDED / CURRENT-MAIN RELEASE REVALIDATION OPEN**

### 已完成实现

```text
M5 governed builder
strict read-only acceptance checker
exact 70-case Validation contract
independent session/return/label/metric recomputation
frozen PR-E / PR-F verification
AI-vs-offline descriptive comparison
label-free PR-F product handoff
complete package checksum validator
A readiness four-file requirement
```

### 已记录正式运行

PR #141 于 2026-08-27 记录：

```text
2024 Validation IPOs = 70
governed filtered EOD = 433,776 rows / 438 IPOs
D1_multi_horizon_evaluation = PASS
blind_2025_y_accessed = false
deterministic --resume = PASS
```

Artifact hashes：

```text
test_predictions.csv
8521dabe3f976e5c532f55fe1571294eb9555ae644a32d524233680af74fa93a

multi_horizon_results.csv
f2d3382f2618e3d328155e9a37e81cd01a156cfc0787c8bc42320237dbb56725

evaluation_summary.json
6d542b025e5a9c52285a80fcdde198282c389ebc55773b40b644ccf0b74f7a63

ai_vs_offline_report.json
3aab6fc39f75f1c350f92ab329df97c97ca48105235d906f5ef213731f180c94
```

五日描述性指标：

```text
Precision 0.3333
Recall 0.0435
F1 0.0769
PR-AUC 0.3364
ROC-AUC 0.4246
Top-10% 0.4286
Top-20% 0.2857
Base prevalence 0.3286
```

### 发布前剩余

Runtime 与授权行情不进入 Git，因此 A 最终打包前必须：

```text
restore immutable frozen PR-E / PR-F runtime
restore governed EOD
current-main rebuild
strict checker PASS
resume byte-identical
fresh-directory byte-identical
materialize final-three label-free product package from configs/v045_demo_cases.json
validate exact package
```

这不是重新优化模型。禁止 broad search、Validation retuning、score inversion、threshold change、calibration 或 substitute market data。

Role-D v2 high-recall output 仍是 research candidate，未经 A 治理决议不得替换 frozen PR-F。

## 3. CH-2 — M1/M2 Document Intelligence benchmark

**Owner：B + A evaluator governance；Status：OPEN / P0**

当前 fixed-10：

```text
10/10 real-LLM
M1 = 23.33%
M2 = 18.75%
dominant failure = semantic_extraction_miss
```

执行顺序：

```text
one dominant-failure Fixer
→ bounded fixed-10 rerun
→ larger Development checkpoint
→ ALL 79 Development
→ freeze
→ one-shot ALL 19 Validation
```

正式 artifact：

```text
existing_gold_evaluable_manifest.json
document_benchmark_summary.json
risk_benchmark.csv
evidence_benchmark.csv
```

必须声明：

```text
new_manual_annotations_added = false
existing_gold_modified = false
blind_2025_outcome_accessed = false
```

## 4. CH-3 — Market Intelligence

**Owner：C；Status：IMPLEMENTATION CLOSED / FINAL-MATRIX VALIDATION OPEN**

最终只确认：

- 3/3 explicit governed Market state；
- unavailable observation 仍有完整 unit / derivation；
- Core-only 不 crash；
- Extended 真实才启用；
- Market LLM 不造数字；
- trace accounting 完整。

无可靠 source 时保持 unavailable，不新增 proxy。

## 5. CH-4 — Multi-Agent / M3 / M4

**Owner：E；Status：IMPLEMENTATION CLOSED / FINAL ACCEPTANCE OPEN**

```text
Agent outputs
→ deterministic conflict detection
→ one bounded targeted re-check
→ retriever / verifier challenge
→ LLM Final Supervisor
→ deterministic fallback
→ TraceEvent
```

当前：

```text
E1 real-provider accepted = 2/3
M3 traceability = 3/3 exactly 1.0
M4 human reviews = 0/6
```

E1 只有 real provider + accepted + complete call trace + scope PASS + severity floor preserved 才成功。Mock/fallback 不算。

## 6. CH-5 — Product / Evidence / Human Review

**Owner：E；Status：CLOSED AS PRODUCT IMPLEMENTATION**

Evidence Viewer、Human Review 与五个比赛工作区继续保留。page grounding 可用；bbox 为 P2，不优先于 M1/M2/C1/E1/M4/D release evidence。

## 7. CH-6 — Formal evaluation / freeze

**Owner：A + B/C/D/E；Status：FINAL EXECUTION OPEN**

最终 handoff：

```text
B: Existing-Gold manifest + ALL79 M1/M2 real-LLM results
C: final-three governed Market trace
D: current-main strict M5 acceptance + deterministic evidence
D→E: final-three label-free frozen ModelSignal package
E: 3-case accepted real-provider + explanation-quality artifact
A: Blind / provenance / determinism / readiness / artifact index / package
```

最终 bundle 至少包括：

```text
existing_gold_evaluable_manifest.json
risk_benchmark.csv/json
evidence_benchmark.csv/json
test_predictions.csv
multi_horizon_results.csv
evaluation_summary.json
ai_vs_offline_report.json
role_d strict acceptance evidence
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
- 提升来自真实 LLM / Retriever / extraction / Verifier 代码；
- Evidence-first、deterministic calculations、PIT Market facts；
- real conflict/re-check、measured traceability、Human Review；
- D 使用冻结 PR-E/PR-F 与 governed EOD 做可复验的 post-listing evaluation；
- D 产品链只接收 label-free frozen score/SHAP projection。

禁止宣称：

- fixed-10 debug 达标等于比赛 PASS；
- uncalibrated score 是 probability；
- 5D -10% 是命题方官方阈值；
- D v2 candidate 已替换 frozen PR-F；
- fallback 是 successful remote arbitration；
- runtime 未复验时 current-main release evidence 已完整；
- 整体已 `COMPETITION_READY`。

## 9. Scope freeze

提交前不做：

- 新的 M1/M2 人工标注或 Gold 扩样；
- broad model search / PR-F replacement training；
- score inversion / Validation tuning；
- full Retriever redesign；
- historical industry PIT research；
- full 438-case LLM；
- presentation-only expansion；
- 无 PIT 证据的 market proxy。
