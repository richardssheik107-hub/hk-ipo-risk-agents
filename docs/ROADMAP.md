# Roadmap — Competition Closure Only

本 Roadmap 只记录尚未完成的工作。当前 Gate 状态以 `V0.4_RELEASE_ACCEPTANCE.md` 为准，指标定义以 `COMPETITION_METRIC_PROTOCOL.md` 为准，当前操作层执行顺序以 `V045_CURRENT_EXECUTION_PLAN.md` 为准。

## 当前立即动作

Role B 已从开放式 Codex 工作流切换为 constrained Lunamax/Codex Runner。2026-08-27 本地最近一次执行能够正确进入 runner，并在 preflight 因本地环境变量缺失返回：

```text
EXECUTION_BLOCKED
blocker = IPO_RISK_PROSPECTUS_ROOT is not set
```

这不是代码 blocker。当前第一动作只有：

```text
设置真实授权招股书根目录 IPO_RISK_PROSPECTUS_ROOT
-> 重新执行 existing fixed-10 runner
-> 生成第一轮 M1/M2 baseline
-> 读取 iteration_summary.json / failure_focus.json
-> 停止
```

完整 Runner prompt、10 家历史 smoke 参考公司与 blocker 恢复模板见：

```text
docs/V045_ROLE_B_LUNAMAX_AUTOMATION_RUNBOOK.md
docs/V045_CURRENT_EXECUTION_PLAN.md
```

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
- `v045_competition_metric_protocol_v2_existing_gold_only` 已定义；
- Existing-Gold read-only coverage audit / evaluator 已实现并实测；
- real `openai_responses` runtime 已由 1167.HK 单案例真实 PDF 全流程验证；
- Role-B fixed-10 Development 自动迭代 runner 已实现；
- constrained Lunamax/Codex Runner 操作规范已文档化并本地验证能够 fail-closed。

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

- 新建 Gold annotation task；
- 为 competition-priority risk family 补样本；
- 新增 negative 标注；
- 人工重新组织 Evidence Groups；
- 看模型错误后修改 Gold；
- 把未标注项当 negative。

现有 inventory / audit：

```text
annotation inventory          101
valid annotations             100
official materialized          98
evaluable Development cases    79
evaluable Validation cases     19
primary positive risk units   128
primary evidence units        217
```

Primary risk support：

```text
cash_burn_pressure         16
customer_concentration     32
redemption_rights          39
supplier_concentration     41
related_party_transaction   0 -> NOT_EVALUABLE_FROM_EXISTING_GOLD
```

Coverage manifest hash：

```text
fcd12d34fcc64853ed778d0026b1e2c943a863549cd1652c6ced7c6145214d1c
```

### M1 — Risk Extraction

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

### M2 — Evidence

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

同时报告：

```text
Recall@1/@3/@5/@10/@20
Candidate Recall@20
Reranked Recall@10
```

这些只用于定位 Retriever/ranking 问题；legacy `Recall@5=20%` 不等于 M2 primary。

### fixed-10 当前执行方式

当前 Metric-v2 正式 debug subset 权威来源：

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

Runner 只做：

```text
preflight
-> fixed 10 sequential real LLM
-> evaluator
-> M1/M2/Recall@K
-> failure taxonomy
-> iteration_summary.json / failure_focus.json
-> STOP
```

Fixer 必须另开短任务，只处理 `dominant_failure_reason`，做一个最小修改 + regression test 后停止。

历史 smoke 参考 10 家：

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

该列表只用于 smoke/人工核对，不覆盖本地自动生成的正式 Metric-v2 fixed-10。

### B closure 顺序

```text
1. 解除本地 prospectus-root blocker
2. fixed-10 baseline
3. 最多 2-4 轮 Runner -> one dominant Fixer -> Runner
4. larger Development checkpoint
5. ALL 79 Development
6. freeze code / Prompt / evaluator / manifest / runtime
7. one-shot ALL 19 Validation
```

fixed-10 内部目标：

```text
M1 >=0.80
M2 >=0.85
```

fixed-10 永远不能声称正式比赛 PASS。

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

1167.HK 单案例真实 runtime 已 PASS，证明 `openai_responses + ark-code-latest` 链路可用；这不是最终 E1 closure。

Final 3-case matrix：

```text
2410.HK / 2460.HK / 1318.HK
```

最终必须：

- real provider；
- `outcome=accepted`；
- `gate_e1.satisfied=true`；
- provider/model/prompt/request/hash/latency 完整；
- scope check PASS；
- severity floor preserved；
- final real-provider traceability = 1.0。

M4 继续使用现有 explanation rubric。

## P1 — C：Final case Market validation

只做 final 3-case governed Market state / trace 验收；不新增 ComparableIPOSkill、不补造 industry/PIT proxy。

## P1 — A：Metric-v2 integration / release freeze

A 剩余：

1. review/merge B/C/D/E final handoff；
2. readiness 读取 metric-v2 artifacts；
3. 验证 `new_manual_annotations_added=false`、`existing_gold_modified=false`；
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
