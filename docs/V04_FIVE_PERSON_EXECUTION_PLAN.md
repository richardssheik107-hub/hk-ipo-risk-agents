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
- metric-v1 定义不得由各 lane 私自改写；
- 每个 PR 小而可验证，不允许五个人同时“全仓提分”。

## Competition Metric v1 — 全队共同目标

```text
M1 Risk Extraction
Official-aligned Accuracy >=0.80
Project target >=0.85
Positive Recall >=0.82
Macro F1 >=0.82

M2 Evidence Group Coverage Recall >=0.85
Project target >=0.88
Recall@K = secondary diagnostics

M3 Traceability =1.0

M4 Explanation Quality
>=2 human reviewers
mean >=4.0/5 project target
minimum formal case >=3.0/5

M5 Outcome
1D / 5D / 20D / 60D complete
Primary significant_drop_5d = return_5d <= -0.10
```

赛题没有规定 Top-5 Evidence、5D -10% 或 M4 数值线；这些属于项目在 Validation 重评前冻结的 protocol，不得宣称为官方公式。

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
- Metric Protocol v1 governance + machine-readable config。

### 剩余职责

- review/merge B/C/D/E metric-v1 PR；
- 保护 `metric_protocol_version` 与 shared artifact contract；
- 不允许 legacy-only Recall@5 被标成 M2 PASS；
- final handoff 到齐后 latest-main CI + 3-case AI smoke；
- Blind / provenance / determinism actual PASS；
- final metric dashboard / artifact index / release note / submission bundle；
- 决定 `COMPETITION_READY`。

### A 禁区

A 不替 B 改语义阈值，不替 C 发明市场数据，不替 D 重训/翻转 PR-F，不替 E 造 Supervisor 结果，不在看到 Validation 后改 metric protocol。

## B — LLM Document Intelligence / Metric M1-M2 owner

### Competition primary risk families

B 负责 metric harness / semantic side 的整体闭环，但不改 frozen Financial ownership：

```text
redemption_rights
related_party_transaction        # additive competition sidecar
customer_concentration           # consume existing Financial output
supplier_concentration           # consume existing Financial output
cash_burn_pressure               # consume cash_runway / deterministic cash-burn output
```

现有 `material_litigation_compliance`、`precommercial_product` 等继续作为扩展能力与 error analysis，不替代 primary five。

### 当前实测

旧 10-case Development offline diagnostic：

```text
Risk P/R/F1        0 / 0 / 0
Evidence Recall@5  20%
Real LLM cases     0
```

该 Recall@5 不再等同官方 Evidence `>=85%`。

### 下一交付 — M1

1. 冻结 metric-v1 Development allowlist，target 20 cases；
2. 当前 10 cases 可纳入，补充 family coverage；
3. 2+ reviewer 建立 Gold Risk Units；
4. 先跑 real-LLM，不先修改结果口径；
5. 输出 official-aligned Accuracy / Precision / Positive Recall / Macro F1 / per-risk；
6. 按 retrieval / ranking / semantics / normalization / reconciliation / verifier / Gold ambiguity 分类错误；
7. 只在 Development 做 targeted remediation；
8. 同 protocol rerun。

M1 closure：

```text
Accuracy >=0.80
Positive Recall >=0.82
Macro F1 >=0.82
```

### 下一交付 — M2

Gold 按支撑事实建立 Evidence Groups，不把重复句子机械算多个必命中项。

```text
Candidate Recall@20 target >=0.95
Reranked Recall@10 target >=0.90
Evidence Group Coverage Recall >=0.85 official
Project target >=0.88
```

Recall@1/@3/@5/@10/@20 全部输出，但只作排序诊断。Final Evidence 不强制固定 5 条。

### Handoff → E/A

```text
AgentResultEnvelope
risk/evidence ids
structured diagnostics
provider metadata
document_benchmark_summary.json with metric_protocol_version
risk_benchmark.csv
evidence_benchmark.csv
ai_vs_offline_report.json
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

只做 final-matrix acceptance：

- Core 可读取；
- Core-only 不 crash；
- Extended 只有真实 governed artifact 才启用；
- industry feature 缺失保持 PIT-blocked；
- Market LLM 不生成不存在的数字；
- namespaced Market trace 完整。

### C 禁区

不为提高 M5 临时新增不可证明 PIT 的 market proxy，不做 ComparableIPOSkill，除非所有 P0/P1 已闭合且另行扩 scope。

## D — Outcome / Model / Evaluation / Metric M5 owner

### 已有基础

- 1D/5D/20D/60D foundation；
- chronological split/blind guard；
- frozen PR-C 5D；
- frozen PR-E/PR-F research evidence。

### 下一交付

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

Primary 5D definition 已冻结：

```text
significant_drop_5d = (return_5d <= -0.10)
```

Robustness：Development bottom 20% cutoff，只计算一次并冻结。

`evaluation_summary.json` 至少报告：

```text
metric_protocol_version
precision / recall / f1
PR-AUC / ROC-AUC
Top-10% / Top-20% hit rate
base prevalence
blind_2025_y_accessed=false
```

赛题没有绝对 5D 合格线，因此 D 不为“过 Gate”事后选阈值。主要目标是 5D business value，相比 base-rate / document-only / market-only / combined 透明报告。

如 authentic PR-F handoff 可恢复则 hash-bound 消费；不可恢复就 `ModelSignal.status=unavailable`，不重训替代。

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

### 剩余 E1

- final 3-case real-provider synthesis；
- 3/3 `gate_e1.satisfied=true`；
- provider/model/prompt/request/hash/latency；
- scope fail-closed；
- severity floor preserved。

### 剩余 M3

```text
Development real-LLM traceability =1.0
final 3-case real-provider traceability =1.0
```

### 剩余 M4

生成：

```text
explanation_quality.json
```

5 维 rubric：Evidence grounding / Logical consistency / Conflict handling / Re-check quality / Final conclusion。

至少 2 名人类 reviewer，LLM 只能辅助。内部目标 mean >=4.0/5，minimum formal case >=3.0/5。

### E 禁区

不补写 B 没抽出的 RiskItem，不补 C 缺失 market fact，不生成 D 不存在 model score，不在 UI 猜 bbox。

## Handoff graph

```text
B M1/M2 + AgentResult / Risk / Evidence ┐
C MarketContext / interpretation          ├→ E Final Supervisor / Trace / Product
D M5 Outcome / ModelSignal / evaluation  ┘

E E1/M3/M4 final artifacts ┐
B/C/D metric-v1 handoffs   ├→ A readiness / audits / package / release
A metric/config/CI control ┘
```

## Shared-file ownership

- metric protocol / global configs / shared schema / CI / readiness：A writer，lane reviewer；
- Legal/Business semantics / Document metric evaluator：B；
- Financial existing deterministic risk internals保持既有 ownership，不因 B benchmark 改写；
- Market internals：C；
- Outcome/model/evaluation：D；
- Final Supervisor/trace/product/M4 artifact：E；
- frozen completion reports/manifests 原则上不改原始实测事实。

## Team completion condition

```text
M1 >=80% + guardrails
AND M2 >=85%
AND M3 =100%
AND M4 internal rubric PASS
AND M5 complete/frozen 5D evaluation
AND C final Market validation
AND E real-provider final matrix
AND A final readiness/audits/CI/package
→ COMPETITION_READY
```
