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
- `v045_competition_metric_protocol_v1` definition + machine-readable config。

除非出现回归或直接影响比赛 Gate，不再对这些模块做架构探索。

## P0 — B：M1 Risk Extraction closure

当前旧 10-case offline diagnostic baseline：

```text
Risk P/R/F1 = 0 / 0 / 0
Real LLM cases = 0
```

metric-v1 primary families：

```text
redemption_rights
related_party_transaction
customer_concentration
supplier_concentration
cash_burn_pressure
```

执行顺序：

```text
1. 固定 20-case Development target allowlist
2. 当前 10 cases 可纳入；补齐 family coverage 前先冻结新 allowlist
3. 2+ reviewer 建立 Gold Risk Units
4. real-provider run first，禁止先看结果改 metric
5. freeze prediction
6. evaluate official-aligned Accuracy / Precision / Positive Recall / Macro F1 / per-risk
7. error taxonomy
8. Development-only targeted remediation
9. rerun same evaluator
```

Primary Gate：

```text
Official-aligned Risk Extraction Accuracy >=0.80
Project target >=0.85
Positive Recall >=0.82
Macro F1 >=0.82
```

Accuracy 分母使用 positive Gold Risk Units，不允许 negative-heavy true-negative accuracy 刷分。

## P0 — B：M2 Evidence Group Coverage closure

旧 `Evidence Recall@5=20%` 只保留为 legacy diagnostic，不再当官方 `>=85%` 的直接口径。

正式优化链：

```text
Gold Evidence Groups
→ Candidate retrieval
→ Reranking
→ Final Evidence selection
→ RiskItem / Verifier
```

工程目标：

```text
Candidate Retrieval Recall@20 >=0.95
Reranked Recall@10           >=0.90
Evidence Group Coverage Recall >=0.85 official pass
Project target >=0.88
```

Recall@1/@3/@5/@10/@20 全部报告，但只作为排序诊断。

最终 Evidence 不固定只能 5 条；按风险复杂度和多样性动态保留足够证据。

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

metric-v1 Primary 5D：

```text
significant_drop_5d = (return_5d <= -0.10)
```

Robustness：Development return_5d bottom 20%，只在 Development 计算一次并冻结。

至少报告：

```text
Precision
Recall
F1
PR-AUC
ROC-AUC
Top-10% risk hit rate
Top-20% risk hit rate
base prevalence
```

赛题没有规定绝对 5D 及格线，所以 D 不允许为“过 Gate”事后创造阈值。目标是协议固定、完整、可复现，并透明比较 no-skill/base-rate、document-only、market-only、combined（可用时）。

## P1 — E：Real-provider Final Supervisor acceptance

同一 final 3-case matrix：

```text
2410.HK
2460.HK
1318.HK
```

必须：

- real provider；
- `outcome=accepted`；
- per-case 与 matrix `gate_e1.satisfied=true`；
- provider/model/prompt/request/hash/latency 完整；
- in-scope reference check PASS；
- severity floor 不降低；
- fallback 仍是正确降级，但不能计 successful arbitration。

## P1 — E：M4 Explanation Quality

新增最终 artifact：

```text
explanation_quality.json
```

5 维评分：

```text
Evidence grounding
Logical consistency
Conflict handling
Re-check quality
Final conclusion
```

至少 2 名人类 reviewer，LLM 仅辅助。内部目标：

```text
mean >=4.0/5
formal case minimum >=3.0/5
```

## P1 — C：Final case Market validation

C 主体代码已完成，只需确认：

- Core materialization 可解析；
- Core-only 不 crash；
- Extended 只有真实 governed artifact 才启用；
- industry return 不可用时保留 PIT missing reason；
- Market LLM 不生成不存在的数字；
- Market trace namespaced evidence/calculation/no-evidence accounting 完整。

不新增 ComparableIPOSkill，不为 M5 临时发明不可证明 PIT 的 feature。

## P1 — A：Metric-v1 integration / release freeze

A 基础收口工具开发已完成。剩余是对 metric-v1 handoff 的 final integration：

1. review/merge B/C/D/E small PR；
2. 确认 B/D/E artifact 均记录 `metric_protocol_version=v045_competition_metric_protocol_v1`；
3. legacy-only Recall@5 或旧 bool target 不得作为 M1/M2 final PASS；
4. latest-main CI；
5. final 3-case AI smoke；
6. Blind / provenance / determinism actual PASS；
7. final metric dashboard / artifact completeness；
8. artifact index；
9. submission ZIP security audit；
10. release note；
11. hard Gate 全绿后 `COMPETITION_READY`。

## P2 — Evidence bbox grounding

page grounding 已可用，bbox 仍 optional quality gap。若最终 demo 需要精确高亮：B 负责 parser/Evidence，A 审 schema/version/hash；UI 不得猜坐标。

## 明确停止的工作

比赛提交前不做：

- broad model tuning / new model families；
- full Retriever redesign；
- historical industry PIT research；
- broad new market acquisition；
- full 438-case LLM run；
- 大规模 feature search；
- 纯装饰 UI；
- proxy/zero fill unavailable market facts。

## Completion condition

```text
M1 Risk official-aligned Accuracy >=80% + guardrails
+ M2 Evidence Group Coverage Recall >=85%
+ M3 real final traceability =100%
+ M4 explanation-quality internal Gate
+ M5 complete 1D/5D/20D/60D + frozen 5D evaluation
+ C final Market validation
+ E final real-provider acceptance
+ A final readiness/audit/CI/package
= v0.4.5 COMPETITION_READY
```
