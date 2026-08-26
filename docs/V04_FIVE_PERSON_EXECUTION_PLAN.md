# v0.4.5 Five-Person Execution Plan

本文件定义 A/B/C/D/E 的稳定 ownership、handoff 和完成标准。当前 Gate 状态以 `V0.4_RELEASE_ACCEPTANCE.md` 为准；比赛指标定义以 `COMPETITION_METRIC_PROTOCOL.md` 为准。

## 全队共同约束

- `RiskItem` 必须有真实 Evidence；需要精确计算时必须有 `Calculation`；
- LLM 只做语义与综合，不是权威计算器；
- Market 数值只能来自 PIT-governed 输入；缺失显式 missing；
- 2024 Validation 不作为调参集；2025 Blind y 未授权前不访问；
- frozen PR-A–PR-G 不为比赛展示而回写；
- PR-F authentic handoff 不存在时 Model Channel = unavailable；
- shared contract 只允许兼容式扩展；
- 指标定义不得由各 lane 私自改写；
- 每个 PR 小而可验证，不允许五个人同时“全仓提分”。

## Competition Metric v2 — Existing-Gold-Only

Protocol：

```text
v045_competition_metric_protocol_v2_existing_gold_only
```

M1/M2 从现在开始只使用项目此前已有的 Expert Annotation / Oracle Gold：

```text
annotation inventory   101
valid annotations      100
official materialized   98
```

**不新增人工 Gold，不补 risk family，不把 UNJUDGED 当 negative，不人工重做 Evidence Group。**

共同目标：

```text
M1 Existing-Gold Risk Extraction Accuracy
official >=0.80
project target >=0.85

M2 Existing-Gold Evidence Coverage Recall
 official >=0.85
 project target >=0.88
 Recall@K = diagnostics only

M3 Traceability =1.0

M4 Explanation Quality
保持现有 E/A rubric，不因 M1/M2 变化增加 Gold 标注工作

M5 Outcome
1D / 5D / 20D / 60D complete
Primary significant_drop_5d = return_5d <= -0.10
```

## A — Tech Lead / Integration / Release / Submission

### 已完成

- competition runtime contracts；
- conflict/recheck/trace/human-review boundary；
- provider observability；
- network-free CI gate；
- Market / Final Supervisor integration；
- 3-case runner；
- documentation governance；
- readiness / Blind / provenance / determinism audit；
- SHA-256 artifact index；
- Submission Runbook；
- fail-closed packager；
- Metric Protocol governance + machine-readable config。

### 当前与 B 并行负责 M1/M2 evaluator infrastructure

A 负责“尺子和治理”，不是替 B 改语义模型：

```text
1. 只读 Existing-Gold coverage audit
2. evaluable-unit manifest + source hash
3. UNJUDGED / NOT_EVALUABLE 语义
4. M1/M2 evaluator
5. failure taxonomy output
6. metric-v2 artifact contract
7. final readiness integration
```

A 不新增人工 Gold，也不要求 B 新标 20 家。

### 最终剩余职责

- review/merge B/C/D/E final PR；
- 保护 `metric_protocol_version=v045_competition_metric_protocol_v2_existing_gold_only`；
- final handoff 到齐后 latest-main CI + 3-case AI smoke；
- Blind / provenance / determinism actual PASS；
- final metric dashboard / artifact index / release note / submission bundle；
- 决定 `COMPETITION_READY`。

### A 禁区

A 不替 B 改语义阈值，不替 C 发明市场数据，不替 D 重训/翻转 PR-F，不替 E 造 Supervisor 结果，不新增 M1/M2 Gold，不在看到 Validation 后改 metric protocol。

## B — LLM Document Intelligence / M1-M2 quality owner

### Gold policy

B 不再承担“补 Gold”的任务。B 只能消费既有 Expert Gold 的只读 evaluator 结果。

Competition-priority risk mapping 仍保留：

```text
redemption_rights
related_party_transaction
customer_concentration
supplier_concentration
cash_burn_pressure
```

但只有既有 Gold 真正有 support 时才评价：

```text
support > 0 -> evaluable
support = 0 -> NOT_EVALUABLE_FROM_EXISTING_GOLD
未明确标注 -> UNJUDGED
```

`material_litigation_compliance`、`precommercial_product` 等旧 Gold 已覆盖的风险可继续作为 diagnostics，不为了“五类”删除。

### 当前旧实测

```text
Risk P/R/F1        0 / 0 / 0
Evidence Recall@5  20%
Real LLM cases     0
```

旧 Recall@5 是 offline diagnostic，不等同官方 Evidence `>=85%`。

### B 的唯一优化任务

```text
real-provider Development run
→ evaluator score
→ failure taxonomy
→ targeted remediation
→ rerun
```

允许优化：

- Retriever candidate retrieval；
- reranking；
- LLM Prompt；
- structured extraction；
- schema normalization；
- Candidate → RiskItem reconciliation；
- Verifier。

禁止：

- 新增人工标注；
- 为低 support risk 补样本；
- 人工重做 Evidence Group；
- 修改旧专家答案；
- 把未标注项当 negative；
- 用 Validation 反复调 Prompt。

### M1 closure

```text
Existing-Gold official-aligned Accuracy >=0.80
Project target >=0.85
```

必须报告 per-risk support。Precision/Macro F1 只有 Existing Gold 本身足够 exhaustive 时才报告，否则明确 `NOT_AVAILABLE_FROM_EXISTING_GOLD`。

### M2 closure

```text
Existing-Gold Evidence Coverage Recall >=0.85
Project target >=0.88
```

同时输出 Recall@1/@3/@5/@10/@20、Candidate Recall@20、Reranked Recall@10 做诊断；Primary 不固定 Top-5。

### Benchmark scope

为迭代速度可从 Existing Development Gold 固定一个小 debug subset，但正式 Development benchmark 使用：

```text
ALL evaluable existing Development Expert Gold
```

系统冻结后，Validation 使用：

```text
ALL evaluable existing Validation Expert Gold
```

一次性确认，不再调优。

### Handoff → E/A

```text
document_benchmark_summary.json
risk_benchmark.csv
evidence_benchmark.csv
ai_vs_offline_report.json
existing_gold_evaluable_manifest.json
```

所有 artifact 必须记录 Existing-Gold source identity/hash，并声明：

```text
new_manual_annotations_added=false
existing_gold_modified=false
blind_2025_outcome_accessed=false
```

## C — Market Intelligence

### 已完成主体

- governed MarketContext；
- IPOHeatSkill；
- MarketRegimeSkill；
- bounded Market LLM；
- PIT/missingness；
- trace/final-supervisor handoff；
- AI runtime wiring；
- real-provider Market path validation。

### 剩余交付

只做 final-matrix acceptance：Core 可读、Core-only 不 crash、Extended 真实才启用、industry 缺失继续 PIT-blocked、Market LLM 不造数字、trace accounting 完整。

### C 禁区

不为提高 M5 临时新增不可证明 PIT 的 market proxy，不做 ComparableIPOSkill。

## D — Outcome / Model / Evaluation / Metric M5 owner

D 继续产出：

```text
return_1d
return_5d
return_20d
return_60d

test_predictions.csv
multi_horizon_results.csv
evaluation_summary.json
ai_vs_offline_report.json
```

Primary：

```text
significant_drop_5d = (return_5d <= -0.10)
```

报告 Precision / Recall / F1 / PR-AUC / ROC-AUC / Top-10% / Top-20% hit rate / base prevalence。赛题没有绝对 5D 合格线，不为过 Gate 事后改阈值。

如 authentic PR-F handoff 不可恢复，ModelSignal 明确 unavailable，不重训替代。

## E — LLM Final Supervisor / Multi-Agent / Product / M3-M4 owner

### 已完成主体

- Final Supervisor；
- conflict policy；
- bounded re-check；
- Verifier challenge；
- Trace / Human Review；
- Evidence Viewer / Streamlit；
- 3/3 offline matrix；
- offline traceability 1.0；
- reasoning log / case report / Gate-E1 evidence。

### 剩余

- final 3-case real-provider synthesis；
- 3/3 `gate_e1.satisfied=true`；
- provider/model/prompt/request/hash/latency；
- scope fail-closed；
- severity floor preserved；
- final real-provider traceability =1.0；
- 按现有方案完成 explanation quality artifact。

M1/M2 Existing-Gold 政策不要求 E 新增人工 Gold。

## Handoff graph

```text
Existing Expert Gold ──read-only──> A evaluator/manifest
                                  └> B real-LLM optimization loop

B M1/M2 + AgentResult / Risk / Evidence ┐
C MarketContext / interpretation          ├→ E Final Supervisor / Trace / Product
D M5 Outcome / ModelSignal / evaluation  ┘

B/C/D/E final handoffs ────────────────→ A readiness / audits / package / release
```

## Shared-file ownership

- metric protocol / global configs / shared schema / CI / readiness：A writer；
- Existing Gold 不允许在比赛收尾阶段由任何 lane 修改；
- Legal/Business semantics / Document optimization：B；
- Financial deterministic internals 保持既有 ownership；
- Market：C；
- Outcome/model/evaluation：D；
- Final Supervisor/trace/product：E；
- frozen completion reports/manifests 不改原始实测事实。

## Team completion condition

```text
M1 Existing-Gold Accuracy >=80%
AND M2 Existing-Gold Evidence Coverage Recall >=85%
AND M3 =100%
AND M4 current rubric PASS
AND M5 complete/frozen 5D evaluation
AND C final Market validation
AND E real-provider final matrix
AND A final readiness/audits/CI/package
→ COMPETITION_READY
```
