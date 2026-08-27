# Documentation Index and Governance

本文档是仓库文档治理入口。当前状态只能由代码 validator、冻结 manifest、当前 Gate、Competition Metric Protocol 与最新实测报告共同确定，不能从历史 completion report 的“next step”或旧 metric 口径推断。

## 当前权威文档

| 文档 | 作用 |
|---|---|
| `../README.md` | 项目入口与当前摘要 |
| `COMPETITION_METRIC_PROTOCOL.md` | **比赛指标唯一评价口径：M1–M5、Existing Gold、Top-K、5D、split** |
| `V0.4_RELEASE_ACCEPTANCE.md` | **唯一当前 Gate / blocker 状态源** |
| `V045_CURRENT_EXECUTION_PLAN.md` | **当前操作层总计划：fixed-10、10 家公司、Lunamax/Codex prompt、blocker 恢复、ALL79/Validation 顺序** |
| `V045_ROLE_B_FIXED10_ITERATION_WORKFLOW.md` | Role-B fixed-10 runner / evaluator / Runner-Fixer workflow |
| `V045_ROLE_B_LUNAMAX_AUTOMATION_RUNBOOK.md` | **可直接复制给 Lunamax/Codex 的 constrained Runner prompt 与 blocker recovery prompt** |
| `ROADMAP.md` | 只记录尚未关闭的执行路线 |
| `V04_FIVE_PERSON_EXECUTION_PLAN.md` | A/B/C/D/E ownership、handoff、merge boundary |
| `COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md` | 赛题要求 → 系统能力 → metric / artifact 验收映射 |
| `SUBMISSION_RUNBOOK.md` | 最终安装、benchmark、3-case、readiness、打包与 freeze 操作手册 |
| `PROJECT_SPEC.md` | 产品边界与不可破坏原则 |
| `ARCHITECTURE.md` | 当前 runtime 架构 |
| `DATA_SCHEMA.md` | 当前公共/比赛 sidecar schema |
| `COMPETITION_DATA_OVERVIEW.md` | 数据范围、split、Gold/Validation/Blind 边界 |
| `research/V04_DATA_READINESS.md` | 数据就绪技术事实 |
| `V045_ROLE_B_REAL_BENCHMARK_REPORT.md` | B 历史 governed benchmark 证据 |
| `V04_ROLE_E_COMPLETION_REPORT.md` | E 实现、3-case matrix 与 submission artifact 实测证据 |

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
3. 已冻结 completion report 中的原始实测事实；
4. `COMPETITION_METRIC_PROTOCOL.md` 对最终比赛 metric 的定义；
5. `V0.4_RELEASE_ACCEPTANCE.md` 当前 Gate 状态；
6. `V045_CURRENT_EXECUTION_PLAN.md` 当前操作顺序；
7. 其他 active docs；
8. research、历史 completion report、Git history。

历史报告里的 Recall@5、旧 risk set 或旧 target 字段保留原始语义，不因新协议追溯改写。

## Metric-v2 解释规则

```text
M1 Existing-Gold Risk Accuracy >=80%
   project target >=85%

M2 Existing-Gold Evidence Coverage Recall >=85%
   project target >=88%
   Recall@1/@3/@5/@10/@20 仅 diagnostics

M3 Traceability =100%
M4 Explanation Quality = current final product rubric
M5 1D/5D/20D/60D
   primary 5D significant drop = return_5d <= -10%（项目定义）
```

M1/M2 Gold policy：

```text
Existing Expert Annotation / Oracle Gold only
no new manual annotation
no existing Gold modification
UNJUDGED != negative
no manual semantic Evidence regrouping
```

现有 inventory：101 annotations / 100 valid / 98 official materialized。

## 当前状态快照

- 3 个真实 2024 招股书 offline E2E 3/3 completed，PDF 完整性 3/3；
- final AI matrix 三案例均实际进入 `openai_responses`；2410/1318 accepted，2460 两次被 scope guard 拒绝并 honest fallback，E1 accepted 2/3、fallback 1/3；
- 三案例 final measured traceability 均为 1.0，M3 PASS；
- Market Intelligence、LLM Final Supervisor、conflict/re-check/Human Review/五工作区均已实现；
- A 已实现 submission readiness、Blind/provenance/determinism audit、artifact index 与 fail-closed packager；
- Existing-Gold coverage audit：79 Development / 19 Validation；128 primary Risk Units / 217 Evidence Units；
- 1167.HK 已跑通真实 `openai_responses + ark-code-latest` 全流程；
- Role-B fixed-10 runner 已实现；
- Role-B 已切换为 constrained Lunamax/Codex Runner/Fixer 分离；
- 2026-08-27 本地 `iter_004` 已完成 frozen fixed-10 10/10 real-LLM，M1=23.33%、M2=18.75%；该结果仅为 Development debug baseline，未达到目标；
- 招股书根目录与 governed `case_id` serialization blocker 已解除；
- C final matrix explicit state 与 trace 3/3，但 2460/1318 的 unavailable industry observations 缺 `unit`/`derivation`，严格 C1 仅 1/3；
- D 尚未交付 final 1D/5D/20D/60D、frozen 5D 与 AI-vs-offline 正式 artifacts；
- M4 review form 已建立但 human reviews 为 0/6；
- 2025 Blind y 仍未访问。

精确 Gate 以 `V0.4_RELEASE_ACCEPTANCE.md` 为准。

## Role-B fixed-10 当前文档口径

正式 Metric-v2 subset：

```text
reports/v045_role_b/fixed10_development_subset.json
```

首次不存在时由：

```bash
python scripts/run_v045_role_b_iteration.py --subset-only
```

确定性生成；之后不重新选公司。

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

该列表不覆盖自动生成的正式 Metric-v2 subset。完整公司表/行业/日期及 canonical prompt 见 `V045_CURRENT_EXECUTION_PLAN.md`。

## 文档生命周期规则

新文档只有在满足至少一个条件时长期保留：

- 定义当前唯一 contract / Gate / metric / ownership；
- 记录不可重建的冻结实测结果；
- 记录稳定技术设计且仍有当前消费者；
- 作为 governed research / annotation evidence；
- 记录当前可重复执行的比赛 closure 操作流程。

`COMPETITION_METRIC_PROTOCOL.md`、`V0.4_RELEASE_ACCEPTANCE.md`、`V045_CURRENT_EXECUTION_PLAN.md` 与 `SUBMISSION_RUNBOOK.md` 属于当前正式比赛 contract/operation 文档。

## 更新责任

- **A**：README、Metric Protocol governance、Existing-Gold evaluator/manifest contract、Gate、Roadmap、current execution plan、release/submission；
- **B**：real-LLM Document optimization、Risk/Evidence benchmark、fixed-10 execution artifacts；
- **C**：Market technical evidence；
- **D**：Outcome/model/evaluation artifacts；
- **E**：Supervisor/Trace/Product / explanation-quality evidence；
- Existing Expert Gold 在比赛收尾阶段由任何 lane 都不得修改；
- shared architecture/schema/metric contract 变更必须由 A 做 cross-lane review。
