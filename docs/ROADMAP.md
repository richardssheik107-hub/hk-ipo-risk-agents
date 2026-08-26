# Roadmap — Competition Closure Only

本 Roadmap 只记录尚未完成的工作。当前 Gate 状态以 `V0.4_RELEASE_ACCEPTANCE.md` 为准，指标定义以 `COMPETITION_METRIC_PROTOCOL.md` 为准。

## 已关闭，不再扩展

- competition runtime contracts / CI gate；
- governed MarketContext；
- IPOHeatSkill / MarketRegimeSkill；
- Market AI runtime wiring；
- LLM Final Supervisor implementation；
- deterministic conflict detection；
- one bounded targeted re-check；
- Agent / Tool / Evidence Trace implementation；
- Human Review；
- 五个 Streamlit workspaces；
- 3 real prospectus offline E2E matrix；
- 3-case offline measured traceability = 1.0；
- E reasoning log / case report / Gate-E1 renderer；
- A readiness / Blind / provenance / determinism / artifact index / Runbook / packager；
- Existing Expert Gold / Oracle annotation inventory 已冻结；
- `v045_competition_metric_protocol_v2_existing_gold_only` 已定义。

除非出现回归或直接影响比赛 hard Gate，不再扩架构。

## P0 — B/A：M1/M2 Existing-Gold closure

### Scope freeze

从现在开始，M1/M2 **不再做任何新增人工标注**：

```text
Existing Expert Annotation / Oracle Gold only
+ read-only deterministic normalization
+ real-LLM/code optimization
```

明确停止：

- 新建 20-case Gold annotation task；
- 为五个 competition-priority risk family 补样本；
- 新增 negative 标注以计算更漂亮的 Precision/F1；
- 人工重新组织 Evidence Groups；
- 看模型错误后修改 Gold；
- 把未标注项当作不存在。

现有 inventory：

```text
annotation inventory   101
valid annotations      100
official materialized   98
```

实际 M1/M2 support 由只读 coverage audit 统计，不能预先假设 98 家全部对每个 risk 都可评价。

### M1 — Risk Extraction

Primary：

```text
Existing-Gold Official-aligned Accuracy
= correct evaluable positive Existing-Gold Risk Units
  / all evaluable positive Existing-Gold Risk Units
```

Gate：

```text
Official pass >=0.80
Project target >=0.85
```

必须披露：

```text
evaluable positive support
correct positive count
per-risk support
per-risk correct / recall
```

`Precision` / `Macro F1` 只有旧 Gold 本身提供足够明确的 exhaustive positive/negative judgment 时才报告；否则：

```text
NOT_AVAILABLE_FROM_EXISTING_GOLD
```

不得为了得到这些指标再补标。

### M2 — Evidence

Primary：

```text
Existing-Gold Evidence Coverage Recall
= covered evaluable existing Evidence Units
  / all evaluable existing Evidence Units
```

Gate：

```text
Official pass >=0.85
Project target >=0.88
```

Primary 不固定 Top-5。继续报告：

```text
Recall@1/@3/@5/@10/@20
Candidate Recall@20
Reranked Recall@10
```

这些只用于定位 Retriever/ranking 问题。旧 `Recall@5=20%` 仍只是 legacy offline diagnostic。

### 执行顺序

```text
1. 对既有 Expert Gold 做只读 coverage audit
2. 生成 evaluable-unit manifest + source hash
3. 从既有 Development Gold 选一个固定小 debug subset（仅为迭代速度）
4. 跑 real-provider Document chain
5. 用同一 Existing-Gold evaluator 评分
6. 自动 failure taxonomy
7. 只在 Development 优化：Retriever / ranking / Prompt / extraction / normalization / RiskItem reconciliation / Verifier
8. 重复直到 Full Development Existing-Gold benchmark 达标或时间到
9. 冻结代码 / Prompt / evaluator / manifest
10. 对全部可评价 Existing Validation Gold 做一次性确认
```

正式 Development benchmark 不再是“20家”，而是：

```text
ALL evaluable existing 2020–2023 Expert Gold
```

Validation：

```text
ALL evaluable existing 2024 Expert Gold
```

不得因 Validation 结果继续调优。

## P0 — D：M5 Multi-horizon / 5D package

必须输出：

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

至少报告 Precision / Recall / F1 / PR-AUC / ROC-AUC / Top-10% / Top-20% hit rate / base prevalence。赛题没有给绝对 5D 及格线，不为过 Gate 事后选阈值。

## P1 — E：Real-provider Final Supervisor / M3 / M4

Final 3-case matrix：2410.HK / 2460.HK / 1318.HK。

必须：

- real provider；
- `outcome=accepted`；
- `gate_e1.satisfied=true`；
- provider/model/prompt/request/hash/latency 完整；
- scope check PASS；
- severity floor preserved；
- final real-provider traceability = 1.0。

M4 继续使用现有 explanation rubric；本次 Existing-Gold 变更不增加任何新的 M4 标注工作。

## P1 — C：Final case Market validation

只做最终 3-case governed Market state / trace 验收；不新增 ComparableIPOSkill、不补造 industry/PIT proxy。

## P1 — A：Metric-v2 integration / release freeze

A 剩余：

1. review/merge B/C/D/E final PR；
2. 更新 readiness 读取 `v045_competition_metric_protocol_v2_existing_gold_only`；
3. 验证 B artifact 声明 `new_manual_annotations_added=false`、`existing_gold_modified=false`；
4. legacy Recall@5 不得作为 M2 PASS；
5. latest-main CI；
6. final 3-case AI smoke；
7. Blind / provenance / determinism actual PASS；
8. final metric dashboard / artifact index；
9. submission ZIP security audit；
10. hard Gate 全绿后 `COMPETITION_READY`。

## P2 — Evidence bbox

保持 optional。提交前只有在不影响 P0/P1 时才处理。

## 明确停止的工作

比赛提交前不做：

- **任何新的 M1/M2 人工 Gold 标注**；
- broad model tuning / new model families；
- full Retriever redesign；
- historical industry PIT research；
- broad new market acquisition；
- full 438-case LLM run；
- 大规模 feature search；
- presentation-only expansion；
- PR-F 替代训练；
- proxy/zero fill unavailable market facts。

## Completion condition

```text
M1 Existing-Gold Risk Accuracy >=80%
+ M2 Existing-Gold Evidence Coverage Recall >=85%
+ M3 real final traceability =100%
+ M4 current explanation-quality Gate
+ M5 complete 1D/5D/20D/60D + frozen 5D evaluation
+ C final Market validation
+ E final real-provider acceptance
+ A final readiness/audit/CI/package
= v0.4.5 COMPETITION_READY
```
