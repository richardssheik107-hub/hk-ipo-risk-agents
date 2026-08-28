# HK IPO Risk Agents

面向港股 IPO 招股书风险识别、市场环境解释与可审计多 Agent 决策的比赛型原型系统。

> 当前 package checkpoint：`v0.4.0`
>
> 当前比赛 runtime：`v0.4.5`
>
> 状态日期：`2026-08-28`
>
> 当前状态：**Competition closure in progress — 尚未标记 `COMPETITION_READY`**

## 系统能力

```text
Prospectus PDF
→ Parser / Retriever / Evidence
→ Financial deterministic analysis
→ Legal / Business structured LLM analysis
→ Verifier / Document Supervisor
→ governed Market-X
→ IPOHeatSkill / MarketRegimeSkill
→ bounded Market LLM interpretation
→ Rule / optional authentic frozen Model signal
→ Conflict detection
→ one bounded targeted re-check
→ LLM Final Supervisor
→ Agent / Tool / Evidence Trace
→ Human Review
→ Streamlit / report / submission artifacts
→ A-owned readiness / Blind / provenance / determinism / package gate
```

核心治理原则：

- LLM 负责语义理解与综合，不负责权威数值计算；
- 精确计算由 Python `Calculation` 完成；
- 正式 `RiskItem` 必须有真实 `Evidence`；
- LLM 只能引用输入作用域内的 Evidence / Risk / Conflict；
- 市场事实必须来自 PIT-governed Market-X，缺失不得补零或造代理；
- 未校准模型分数只能称 `uncalibrated_model_score`；
- 2024 Validation 不做 post-hoc tuning；
- 2025 Blind outcome 未授权前不访问；
- frozen PR-A–PR-G 不因比赛展示需要而重写。

## Competition Metric Protocol v2

当前协议：

```text
v045_competition_metric_protocol_v2_existing_gold_only
```

| Metric | Official requirement | Project definition |
|---|---:|---|
| M1 Risk extraction | >=80% | Existing-Gold positive Risk Unit Accuracy；target >=85% |
| M2 Evidence recall | >=85% | Existing-Gold Evidence Coverage Recall；target >=88% |
| M2 Recall@K | 官方未指定 | Recall@1/@3/@5/@10/@20 仅作诊断 |
| M3 Traceability | 100% | accounted Agent/Tool/Evidence-or-reason trace |
| M4 Explanation | “高” | final product human-review rubric |
| M5 Post-listing | 1D/5D/20D/60D | 5D primary；`return_5d <= -0.10` 为预先冻结的项目定义 |

M1/M2 只使用比赛收尾前已存在并冻结的 Expert Annotation / Oracle Gold：

```text
annotation inventory             101
valid annotations                100
official materialized             98
evaluable Development cases       79
evaluable Validation cases        19
primary positive risk units      128
primary evidence units           217
```

禁止新增 Gold、修改旧专家答案、把 `UNJUDGED` 当 negative，或人工重组 Evidence Group。

## 最新实测状态

### Role B — Development quality closure

2026-08-27 本地 frozen fixed-10 `iter_004`：

```text
completed real-LLM cases = 10/10
M1 = 23.33%
M2 = 18.75%
dominant failure = semantic_extraction_miss
Validation opened = false
2025 Blind accessed = false
```

该结果是 Development debug baseline，不是正式比赛 PASS。B 仍需 bounded Fixer 迭代、ALL 79 Development、冻结后一次性 ALL 19 Validation。

### Role D — M5 已物化，发布复验仍需本地不可变输入

PR #141 在 2026-08-27 记录了一次授权数据上的正式 Role-D 物化：

```text
evaluation split = 2024 Validation
evaluated IPOs = 70
governed filtered EOD = 433,776 rows / 438 target IPOs
D1_multi_horizon_evaluation = PASS
blind_2025_y_accessed = false
deterministic --resume = PASS
```

正式四文件及记录哈希：

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
Precision          0.3333
Recall             0.0435
F1                 0.0769
PR-AUC             0.3364
ROC-AUC            0.4246
Top-10% hit rate   0.4286
Top-20% hit rate   0.2857
Base prevalence    0.3286
```

当前 `main` 已具备：

- governed M5 builder；
- 独立只读 strict acceptance checker；
- exact-four-file、70-case、session/return/label/metric/provenance 校验；
- label-free PR-F product handoff 与完整 package validator；
- A readiness 对四个 Role-D 正式文件的 fail-closed 检查。

历史物化现在有一份可在 CI 中验证的哈希绑定机器凭据：

```text
reports/frozen/v045_role_d_m5_materialization_receipt.json
python scripts/validate_v045_role_d_receipt.py
```

该 receipt 会绑定冻结 PR-E/PR-F manifest、Metric Protocol、四个正式 artifact 哈希与治理声明；它是**已记录外部物化证据**，不替代持有授权 EOD 与完整 frozen runtime 时必须执行的 current-main strict rerun。

Runtime、授权 EOD 与完整 PR-E/PR-F research runtime 按规则未提交，因此最终发布前仍需在持有这些不可变输入的环境中进行一次 **current-main strict revalidation**，并物化 `2410/2460/1318` 的 D→E label-free package。当前 v2 high-recall 模型仍是 research candidate，未替换 frozen PR-F。

### Role C / E — final matrix

```text
2410.HK / 2460.HK / 1318.HK offline E2E = 3/3
M3 traceability = 3/3 exactly 1.0
E1 real-provider accepted = 2/3
C1 strict observation contract = 1/3
M4 human reviews = 0/6
```

2460 的 Final Supervisor 两次越界引用均被 scope guard 拒绝并 honest fallback；C 的 2460/1318 仍有 unavailable observation metadata 缺口。

## 当前比赛 Gate

| Gate | Status |
|---|---|
| competition runtime contracts | PASS |
| Existing Expert Gold inventory / Metric-v2 | FROZEN |
| Existing-Gold evaluator | PASS implementation |
| B ALL 79 Development M1/M2 | **OPEN / P0** |
| D M5 builder / strict checker / product handoff | **PASS implementation** |
| D1 70-case formal materialization | **PASS RECORDED；current-main release revalidation pending** |
| D recorded receipt / CI validation | **PASS** |
| D→E final-three label-free package | **PENDING LOCAL FROZEN RUNTIME** |
| C final-matrix Market validation | **BLOCKED: strict C1 1/3** |
| E final 3-case real-provider Supervisor | **BLOCKED: accepted 2/3** |
| M3 final traceability | **PASS: 3/3 = 1.0** |
| M4 explanation-quality human review | **OPEN: 0/6** |
| Final audits / bundle / release freeze | **NOT READY** |

## 文档入口

- 当前 Gate：`docs/V0.4_RELEASE_ACCEPTANCE.md`
- 当前执行总计划：`docs/V045_CURRENT_EXECUTION_PLAN.md`
- Role-D 收口与证据边界：`docs/V045_ROLE_D_FINAL_CLOSURE.md`
- Metric contract：`docs/COMPETITION_METRIC_PROTOCOL.md`
- Role-B Runner：`docs/V045_ROLE_B_LUNAMAX_AUTOMATION_RUNBOOK.md`
- 最终提交 Runbook：`docs/SUBMISSION_RUNBOOK.md`
- 剩余路线：`docs/ROADMAP.md`
- 五人执行：`docs/V04_FIVE_PERSON_EXECUTION_PLAN.md`
- 赛题映射：`docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`

## 快速运行

```bash
pip install -e ".[dev,retrieval-research]"
python scripts/validate_competition_runtime.py
python scripts/validate_v045_role_d_receipt.py

# Role B
python scripts/audit_v045_existing_gold.py --output-dir reports/v045_role_b
python scripts/run_v045_role_b_iteration.py --subset-only
python scripts/run_v045_role_b_iteration.py --iteration auto

# Role D：以下 live build/check 需要本地完整 frozen PR-E/PR-F runtime 与 governed EOD
python scripts/build_v045_role_d_m5.py --output-dir reports/v045_role_d
python scripts/check_v045_role_d_m5.py \
  --role-d-dir reports/v045_role_d \
  --output reports/v045_role_d_acceptance/acceptance.json
python scripts/build_v04_pr_f_product_handoff.py \
  --source-pr-f-dir reports/v04_pr_f \
  --case-list configs/v045_demo_cases.json \
  --output-dir reports/v045_pr_f_product_handoff_final3
```

最终 `COMPETITION_READY` 只能在 B/C/D/E 的 release evidence、latest-main CI、Blind/provenance/determinism、artifact index 与 submission package 全部真实通过后使用。
