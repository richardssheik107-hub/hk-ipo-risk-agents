# v0.4.5 Five-Person Execution Plan

> Status date: `2026-08-28`

本文件定义 A/B/C/D/E 的稳定 ownership、handoff 与完成标准。当前 Gate 以 `V0.4_RELEASE_ACCEPTANCE.md` 为准；指标定义以 `COMPETITION_METRIC_PROTOCOL.md` 为准；操作顺序以 `V045_CURRENT_EXECUTION_PLAN.md` 为准。

## 全队共同约束

- `RiskItem` 必须有真实 Evidence；精确计算必须有 `Calculation`；
- LLM 只做语义与综合，不是权威计算器；
- Market 数值只能来自 PIT-governed 输入，missing 不补零；
- 2024 Validation 不作为调参集；2025 Blind y 未授权前不访问；
- frozen PR-A–PR-G 不为展示而回写；
- authentic PR-F handoff 不存在时 Model Channel = unavailable；
- shared contract 只允许兼容式扩展；
- 指标定义不得由各 lane 私自改写；
- 每个 PR 小而可验证；
- 不提交 licensed data、PDF bulk、model/cache、credential 或 absolute path。

## Competition Metric v2 — Existing-Gold-Only

```text
protocol = v045_competition_metric_protocol_v2_existing_gold_only
M1 official >=0.80; target >=0.85
M2 official >=0.85; target >=0.88
M3 =1.0
M4 current human-review rubric
M5 horizons =1D/5D/20D/60D
primary significant_drop_5d = return_5d <= -0.10
```

M1/M2 只使用此前已有的 Expert Annotation / Oracle Gold；不新增人工 Gold、不修改 Existing Gold、不把 `UNJUDGED` 当 negative。

## A — Tech Lead / Integration / Release

### Owns

```text
public contracts
GitHub / branch / PR / CI
readiness / Blind / provenance / determinism
artifact index / security audit / submission package
final COMPETITION_READY decision
```

### 当前剩余

- review B/C/D/E final handoff；
- latest-main CI；
- final-three AI smoke；
- consume D strict current-main revalidation evidence；
- run final audits and package only after every hard Gate passes。

### 禁区

A 不替 B 调语义模型，不替 C 发明市场数据，不替 D 重训/翻转 PR-F，不替 E 造 Supervisor 结果。

## B — LLM Document Intelligence / M1-M2

### 当前状态

```text
fixed-10 iter_004 = 10/10 real-LLM
M1 = 23.33%
M2 = 18.75%
dominant failure = semantic_extraction_miss
```

### 唯一优化循环

```text
Runner → score → dominant failure → STOP
one short Fixer → one minimal patch + regression test → STOP
next Runner
```

### Closure

```text
bounded fixed-10 iterations
→ larger Development checkpoint
→ ALL 79 Development
→ freeze
→ one-shot ALL 19 Validation
```

不得新增/修改 Gold、打开 Validation 调 Prompt、做 broad Retriever rewrite。

## C — Market Intelligence

### 已完成主体

- governed MarketContext；
- IPOHeatSkill / MarketRegimeSkill；
- bounded Market LLM；
- PIT / missingness；
- trace / Final Supervisor handoff。

### 剩余

只做 final-three strict acceptance：Core 可读、Core-only 不 crash、Extended 真实才启用、unavailable observation 仍含完整 unit/derivation、Market LLM 不造数字、trace accounting 完整。

### 禁区

不为提高 M5 临时新增不可证明 PIT 的 proxy，不做 ComparableIPOSkill。

## D — Outcome / Model / Evaluation / M5

### 已完成实现

```text
frozen PR-E / PR-F runtime verification
1D / 5D / 20D / 60D outcome builder
70-case prediction and horizon tables
frozen AI-vs-offline descriptive comparison
strict read-only M5 acceptance checker
label-free PR-F product handoff
complete product-package validator
A readiness four-file contract
```

### 已记录正式物化

PR #141 于 2026-08-27 记录：

```text
2024 Validation IPOs = 70
D1_multi_horizon_evaluation = PASS
blind_2025_y_accessed = false
deterministic --resume = PASS
```

正式四文件：

```text
test_predictions.csv
multi_horizon_results.csv
evaluation_summary.json
ai_vs_offline_report.json
```

赛题没有绝对 5D 模型合格线。记录指标较弱不构成重训、反转 score、改 threshold 或 calibration 的许可。

### 当前唯一剩余

在持有完整 frozen PR-E/PR-F runtime 与授权 governed EOD 的本地环境：

```text
current-main rebuild
→ strict checker PASS
→ same-directory resume byte-identical
→ fresh-directory byte-identical
→ read configs/v045_demo_cases.json
→ materialize 2410/2460/1318 label-free product package
→ validate complete package
→ handoff evidence to A/E
```

若不可变输入不可恢复，状态必须是 `BLOCKED_EXTERNAL_IMMUTABLE_INPUTS`，不得训练替代品。

### v2 candidate

Role-D v2 high-recall output 仍是 research candidate / A review required，未替换 frozen PR-F。

### 禁区

```text
broad model search
2024 Validation retuning
score inversion
threshold change
calibration
substitute market data
2025 Blind outcome access
```

## E — Final Supervisor / Product / M3-M4

### 已完成主体

- LLM Final Supervisor；
- conflict policy；
- bounded re-check；
- Verifier challenge；
- Trace / Human Review；
- Evidence Viewer / Streamlit；
- 3/3 offline matrix；
- M3 traceability 3/3 = 1.0。

### 剩余

```text
2410 / 2460 / 1318 real-provider accepted 3/3
complete provider/model/prompt/request/hash/latency
scope fail-closed
severity floor preserved
M4 two independent human reviewers per case
```

2460 当前 honest fallback 不算 successful arbitration。

## Handoff graph

```text
Existing Expert Gold ─read-only─> A evaluator / B benchmark

B Risk/Evidence ┐
C MarketContext ├→ E Final Supervisor / Trace / Product
D ModelSignal   ┘

D full research runtime ─D-only evaluation─> M5 artifacts
D label-free projection ────────────────> E Model Channel

B/C/D/E final evidence ────────────────> A readiness / audits / package
```

## Team completion condition

```text
M1 >=80%
AND M2 >=85%
AND M3 =100%
AND M4 PASS
AND D current-main M5 strict revalidation PASS
AND D→E final-three label-free package PASS
AND C final Market validation PASS
AND E real-provider final matrix PASS
AND A final readiness/audits/CI/package PASS
→ COMPETITION_READY
```
