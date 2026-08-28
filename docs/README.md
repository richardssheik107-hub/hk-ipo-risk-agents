# Documentation Index and Governance

> Status date: `2026-08-28`

本文档是仓库文档治理入口。当前状态只能由代码 validator、冻结 manifest、当前 Gate、Competition Metric Protocol 与最新实测证据共同确定，不能从历史 completion report 的旧 “next step” 推断。

## 当前权威文档

| 文档 | 作用 |
|---|---|
| `../README.md` | 项目入口与当前摘要 |
| `COMPETITION_METRIC_PROTOCOL.md` | M1–M5、Existing Gold、Top-K、5D、split 的唯一指标口径 |
| `V0.4_RELEASE_ACCEPTANCE.md` | **唯一当前 Gate / blocker 状态源** |
| `V045_CURRENT_EXECUTION_PLAN.md` | 当前操作顺序：B Runner/Fixer、D release revalidation、C/E closure、A package |
| `V045_ROLE_B_FIXED10_ITERATION_WORKFLOW.md` | Role-B fixed-10 runner / evaluator workflow |
| `V045_ROLE_B_LUNAMAX_AUTOMATION_RUNBOOK.md` | constrained Runner / blocker recovery prompt |
| `ROADMAP.md` | 尚未关闭的执行路线 |
| `V04_FIVE_PERSON_EXECUTION_PLAN.md` | A/B/C/D/E ownership、handoff、merge boundary |
| `COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md` | 赛题要求 → 系统能力 → metric/artifact 验收 |
| `SUBMISSION_RUNBOOK.md` | 安装、benchmark、3-case、readiness、打包与 freeze |
| `PROJECT_SPEC.md` | 产品边界与不可破坏原则 |
| `ARCHITECTURE.md` | 当前 runtime 架构 |
| `DATA_SCHEMA.md` | 公共/比赛 sidecar schema |
| `COMPETITION_DATA_OVERVIEW.md` | 数据范围、split、Gold/Validation/Blind 边界 |
| `research/V04_DATA_READINESS.md` | 数据就绪技术事实 |
| `V045_ROLE_B_REAL_BENCHMARK_REPORT.md` | B 历史 governed benchmark 证据 |
| `V04_ROLE_E_COMPLETION_REPORT.md` | E 实现与 3-case artifact 实测证据 |

Machine-readable metric freeze：

```text
configs/v045_competition_metric_protocol.json
protocol_version = v045_competition_metric_protocol_v2_existing_gold_only
```

`AGENTS.md` 是跨版本工程治理规则，优先级高于叙述性文档。

## Source-of-truth hierarchy

出现冲突时按以下顺序裁定：

1. 代码中的 validator / Pydantic / Protocol / fail-closed guard；
2. `reports/frozen/*.json` 与 hash-bound frozen manifest；
3. 已冻结报告或 PR 中不可重建的原始实测事实；
4. `COMPETITION_METRIC_PROTOCOL.md`；
5. `V0.4_RELEASE_ACCEPTANCE.md`；
6. `V045_CURRENT_EXECUTION_PLAN.md`；
7. 其他 active docs；
8. research、历史 completion report、Git history。

历史报告中的旧 Recall@K、旧 risk set 或旧 target 保留原始语义，不因新协议追溯改写。

## Metric-v2 解释规则

```text
M1 Existing-Gold Risk Accuracy >=80%; target >=85%
M2 Existing-Gold Evidence Coverage Recall >=85%; target >=88%
Recall@1/@3/@5/@10/@20 = diagnostics only
M3 Traceability =100%
M4 Explanation Quality = current human-review rubric
M5 1D/5D/20D/60D
primary significant drop = return_5d <= -0.10（项目定义）
```

M1/M2 Gold policy：

```text
Existing Expert Annotation / Oracle Gold only
no new manual annotation
no existing Gold modification
UNJUDGED != negative
no manual semantic Evidence regrouping
```

## 当前状态快照

- 3 个真实 2024 招股书 offline E2E 3/3 completed，PDF integrity 3/3；
- E final AI matrix：2410/1318 accepted，2460 scope-blocked honest fallback，E1=2/3；
- M3 measured traceability = 3/3 exactly 1.0；
- C strict observation contract = 1/3；
- M4 human reviews = 0/6；
- Existing-Gold audit = 79 Development / 19 Validation / 128 Risk Units / 217 Evidence Units；
- B fixed-10 `iter_004` = 10/10 real-LLM，M1=23.33%、M2=18.75%；
- D governed M5 builder、strict checker、label-free product handoff 与 A four-file readiness contract 已实现；
- PR #141 已记录 D 的 70-case 2024 Validation M5 PASS、四文件 hashes 与 deterministic resume PASS；
- D runtime、授权 EOD 与完整 PR-E/PR-F research runtime 未提交，发布前仍需 current-main strict revalidation；
- D→E final-three package 仍需在持有 frozen runtime 的本地环境物化；
- D v2 high-recall output 仍为 research candidate，未替换 frozen PR-F；
- 2025 Blind y 仍未访问；
- 整体仍未 `COMPETITION_READY`。

精确 Gate 以 `V0.4_RELEASE_ACCEPTANCE.md` 为准。

## Role D 当前可重复操作

```bash
python scripts/build_v045_role_d_m5.py --output-dir reports/v045_role_d
python scripts/check_v045_role_d_m5.py \
  --role-d-dir reports/v045_role_d \
  --output reports/v045_role_d_acceptance/acceptance.json
python scripts/build_v04_pr_f_product_handoff.py \
  --source-pr-f-dir reports/v04_pr_f \
  --case-list configs/v045_demo_cases.json \
  --output-dir reports/v045_pr_f_product_handoff_final3
```

这些命令要求本地存在 SHA 完全匹配的 frozen PR-E/PR-F runtime 与合法 governed EOD。缺失时不得训练或下载替代输入。

## 文档生命周期规则

新文档只有在满足至少一个条件时长期保留：

- 定义当前唯一 contract / Gate / metric / ownership；
- 记录不可重建的冻结实测结果；
- 记录稳定技术设计且仍有当前消费者；
- 作为 governed research / annotation evidence；
- 记录当前可重复执行的比赛 closure 流程。

## 更新责任

- **A**：README、Metric Protocol governance、Gate、Roadmap、execution plan、release/submission；
- **B**：real-LLM Document optimization、Risk/Evidence benchmark、fixed-10 artifacts；
- **C**：Market technical evidence；
- **D**：Outcome/model/evaluation artifacts 与 release revalidation evidence；
- **E**：Supervisor/Trace/Product/explanation-quality evidence；
- Existing Expert Gold 在收尾阶段不得由任何 lane 修改；
- shared architecture/schema/metric contract 变更必须由 A 做 cross-lane review。
