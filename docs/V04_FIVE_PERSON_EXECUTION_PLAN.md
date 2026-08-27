# v0.4.5 Five-Person Execution Plan

本文件定义 A/B/C/D/E 的稳定 ownership、handoff 和完成标准。当前 Gate 状态以 `V0.4_RELEASE_ACCEPTANCE.md` 为准；比赛指标定义以 `COMPETITION_METRIC_PROTOCOL.md` 为准；当前操作层顺序以 `V045_CURRENT_EXECUTION_PLAN.md` 为准。

## 全队共同约束

- `RiskItem` 必须有真实 Evidence；需要精确计算时必须有 `Calculation`；
- LLM 只做语义与综合，不是权威计算器；
- Market 数值只能来自 PIT-governed 输入；缺失显式 missing；
- 2024 Validation 不作为调参集；2025 Blind y 未授权前不访问；
- frozen PR-A–PR-G 不为比赛展示而回写；
- PR-F authentic handoff 不存在时 Model Channel = unavailable；
- shared contract 只允许兼容式扩展；
- 指标定义不得由各 lane 私自改写；
- 每个 PR 小而可验证，不允许五个人同时“全仓提分”；
- Role-B 当前只采用 Runner/Fixer 分离，不允许 Codex/Lunamax 开放式扫描全仓。

## Competition Metric v2 — Existing-Gold-Only

Protocol：

```text
v045_competition_metric_protocol_v2_existing_gold_only
```

M1/M2 只使用此前已有 Expert Annotation / Oracle Gold：

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
M4 Explanation Quality = current E/A rubric
M5 1D / 5D / 20D / 60D complete
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
- Metric Protocol governance + machine-readable config；
- Existing-Gold coverage audit / evaluator；
- fixed-10 runner 与 current execution documentation governance。

### 当前职责

A 负责尺子、治理和最终集成，不替 B 改语义模型：

```text
Existing-Gold manifest / evaluator governance
metric-v2 artifact contract
failure taxonomy contract
readiness integration
documentation source-of-truth consistency
```

### 最终剩余

- review/merge B/C/D/E final handoff；
- 保护 metric protocol；
- latest-main CI + final 3-case AI smoke；
- Blind / provenance / determinism actual PASS；
- final metric dashboard / artifact index / release note / bundle；
- 决定 `COMPETITION_READY`。

### A 禁区

不替 B 改语义阈值，不替 C 发明市场数据，不替 D 重训/翻转 PR-F，不替 E 造 Supervisor 结果，不新增 M1/M2 Gold，不在看到 Validation 后改 metric protocol。

## B — LLM Document Intelligence / M1-M2 quality owner

### 当前状态

B 是当前 P0 质量主线。操作方式已经收敛为 constrained Lunamax/Codex Runner。

2026-08-27 最近一次本地运行：

```text
EXECUTION_BLOCKED
blocker = IPO_RISK_PROSPECTUS_ROOT is not set
```

这不是代码 blocker；只设置本地授权招股书根目录后继续现有 runner。

### Gold policy

B 不再承担“补 Gold”的任务，只消费既有 Expert Gold 的只读 evaluator 结果。

Competition-priority mapping：

```text
redemption_rights
related_party_transaction
customer_concentration
supplier_concentration
cash_burn_pressure
```

当前 support：

```text
cash_burn_pressure         16
customer_concentration     32
redemption_rights          39
supplier_concentration     41
related_party_transaction   0 -> NOT_EVALUABLE_FROM_EXISTING_GOLD
```

### fixed-10 source of truth

```text
reports/v045_role_b/fixed10_development_subset.json
```

不存在时只运行一次：

```bash
python scripts/run_v045_role_b_iteration.py --subset-only
```

每轮：

```bash
python scripts/run_v045_role_b_iteration.py --iteration auto
```

Runner 完成后只读：

```text
iteration_summary.json
failure_focus.json
```

然后停止。

### 历史 smoke 参考 10 家

```text
1167.HK 加科思─B
1942.HK MOG Holdings
1961.HK 九尊数字互娱
9600.HK 新纽科技
9633.HK 农夫山泉
9898.HK 微博─SW
6698.HK 星空华文
9863.HK 零跑汽车
2451.HK 绿源集团控股
2517.HK 锅圈
```

这组仅用于旧 benchmark / smoke / 人工核对，不覆盖当前自动生成的 Metric-v2 fixed-10。

完整公司表、Runner prompt、blocker 恢复模板：

```text
docs/V045_CURRENT_EXECUTION_PLAN.md
docs/V045_ROLE_B_LUNAMAX_AUTOMATION_RUNBOOK.md
```

### B 的唯一优化循环

```text
Runner
-> score
-> dominant failure
-> STOP
-> one short Fixer
-> one minimal patch + regression test
-> STOP
-> next Runner
```

允许优化：Retriever candidate retrieval、reranking、LLM Prompt、structured extraction、schema normalization、Candidate→RiskItem reconciliation、Verifier。

禁止：新增人工标注、补低 support risk、人工重做 Evidence Group、修改旧专家答案、把未标注项当 negative、反复用 Validation 调 Prompt。

### M1 closure

```text
Existing-Gold official-aligned Accuracy >=0.80
Project target >=0.85
```

### M2 closure

```text
Existing-Gold Evidence Coverage Recall >=0.85
Project target >=0.88
```

同时输出 Recall@1/@3/@5/@10/@20、Candidate Recall@20、Reranked Recall@10 做诊断。

### Benchmark scope / 顺序

```text
fixed-10 baseline
-> max 2-4 targeted rounds
-> larger Development checkpoint
-> ALL 79 Development
-> freeze
-> one-shot ALL 19 Validation
```

fixed-10 M1>=0.80 / M2>=0.85 只代表 debug target，不代表比赛 PASS。

### Handoff → E/A

```text
existing_gold_evaluable_manifest.json
document_benchmark_summary.json
risk_benchmark.csv
evidence_benchmark.csv
ai_vs_offline_report.json
```

所有 artifact 必须记录 source identity/hash，并声明：

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

### 剩余

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

- final 2410 / 2460 / 1318 real-provider synthesis；
- 3/3 `gate_e1.satisfied=true`；
- provider/model/prompt/request/hash/latency；
- scope fail-closed；
- severity floor preserved；
- final real-provider traceability =1.0；
- current explanation quality artifact。

## Handoff graph

```text
Existing Expert Gold ──read-only──> A evaluator/manifest
                                  └> B fixed-10 -> ALL79 real-LLM loop

B M1/M2 + Risk/Evidence ┐
C MarketContext           ├→ E Final Supervisor / Trace / Product
D M5 Outcome/ModelSignal ┘

B/C/D/E final handoffs ─────────────→ A readiness / audits / package / release
```

## Team completion condition

```text
M1 >=80%
AND M2 >=85%
AND M3 =100%
AND M4 current rubric PASS
AND M5 complete/frozen 5D evaluation
AND C final Market validation
AND E real-provider final matrix
AND A final readiness/audits/CI/package
-> COMPETITION_READY
```
