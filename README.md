# HK IPO Risk Agents

面向东吴证券港股 IPO 赛题的多智能体风险分析与上市后预警原型。

> Package checkpoint：`v0.4.0`
>
> Competition runtime：`v0.4.5`
>
> Role-B diagnostic track：`v0.4.6`
>
> 状态日期：`2026-08-28`
>
> 当前结论：**NOT COMPETITION_READY**

## 赛题目标

项目需要同时完成三件事：

1. 对数百页港股招股书进行防幻觉解析，抽取财务、法务和业务隐性风险；
2. 让 Financial、Legal、Business、Market 与 Final Supervisor 协作、冲突查证并保留完整 Trace；
3. 输出带原 PDF 页码、段落和证据截图的风险报告，并用上市后 1D / 5D / 20D / 60D 表现验证业务参考价值。

## 当前状态

| 维度 | 当前事实 | 赛题关闭标准 |
|---|---|---|
| M1 风险抽取 | fixed-10 `23.33%` | ALL 79 Development `>=80%` |
| M2 证据召回 | fixed-10 `18.75%` | ALL 79 Development `>=85%` |
| B 线诊断 | v0.4.6 三路对照、journal、waterfall + read-only Evidence audit 已实现 | 完整 fixed-10 实测与逐单元根因矩阵 |
| M3 Traceability | 三案例 `3/3 = 1.0` | 保持 100% 并进入 final bundle |
| Final Supervisor | real-provider accepted `2/3` | `3/3` accepted，fallback 不计成功 |
| Market strict contract | `1/3` | `3/3`，无伪造数值、缺失元数据完整 |
| M4 | `0/6` 真人评审 | 每案两名独立评审并通过 rubric |
| M5 formal | 70-case 四文件物化与 receipt 已记录 | current-main strict revalidation |
| M5 v2 candidate | Recall `52.17%`、F1 `42.11%`、PR-AUC `38.12%`，未晋升 | A governance decision + 新 freeze/handoff |
| 产品 | UI、Report、Trace、Human Review 已存在 | Evidence 高亮截图、典型案例、预测表和安全封包齐全 |

Frozen PR-F 的五日 Recall 仅 `4.35%`、ROC-AUC `0.4246`，不能据此宣称强业务效果。仓库已有一个完全按 expanding Development folds 选择、在 2024 一次评估的 v2 候选，将 Recall 提升到 `52.17%`、F1 提升到 `42.11%`，但 ROC-AUC 仍为 `0.4875`，且尚未完成 A-owned 晋升决议。正式产品仍不能直接消费它。

## 距离比赛还剩 6 个阶段

1. **B 全链路取证**：把 Parser、Retrieval、LLM、Builder、Reconciliation、Verifier、Evidence binding 分开测量；
2. **B 指标闭环**：通用修复 → fixed-10 → ALL 79 Development → freeze；
3. **D/C/E 并行闭环**：D 模型晋升决策与复验，Market strict 3/3，Final Supervisor accepted 3/3，M4 6 份评审；
4. **赛题能力补齐**：核心管线、文本粉饰度、关联交易、同行估值、Evidence 截图；
5. **冻结与一次性 Validation**：D final artifacts、B one-shot ALL 19 Validation、CI/audits；
6. **最终交付**：源码、运行脚本、预测表、Trace、Evidence、案例报告、API/UI、submission ZIP。

完整计划：[`docs/COMPETITION_CLOSURE_PLAN.md`](docs/COMPETITION_CLOSURE_PLAN.md)。

## 系统架构

```text
Prospectus PDF
→ Parser / Retriever / Evidence
→ Financial deterministic analysis
→ Legal / Business structured LLM
→ Verifier / Document Supervisor
→ governed Market Context + Skills
→ optional frozen model signal
→ Conflict / bounded re-check
→ LLM Final Supervisor + deterministic fallback
→ Agent / Tool / Evidence Trace
→ Human Review / Report / UI
→ M1–M5 evaluation / readiness / package
```

Role-B v0.4.6 提供：

```text
offline baseline
+ real-LLM shadow probe
+ journal-replayed gated result
+ read-only persisted-result Evidence audit
→ monotonicity / retrieval waterfall / LLM quality / provenance diagnostics
```

## 指标与治理

```text
M1 Existing-Gold Risk Accuracy >=0.80
M2 Existing-Gold Evidence Coverage Recall >=0.85
M3 Traceability =1.0
M4 Explanation Quality = human-review rubric
M5 = 1D / 5D / 20D / 60D，5D 重点
```

继续保留的硬边界：

- Existing Gold 不新增、不修改，`UNJUDGED` 不当 negative；
- Gold 不进入 runtime Retriever、Prompt 或 Agent；
- Validation 冻结后一次性运行，不用于调参；
- 未来优化不再使用 2025 Blind 输入或 outcome；
- LLM 不得创造越界 Evidence；
- 精确财务数值由 deterministic `Calculation` 负责；
- Market 必须 PIT-safe，缺失不补零、不造 proxy；
- 不提交 Secret、授权 PDF、raw EOD、本地绝对路径或未授权模型。

流程上的旧限制已经移除：不再固定最多 2–4 轮，不再 Runner-only，也不再绝对禁止 Development-only 的 Retriever 或模型/transport 对照。

## 快速入口

```bash
pip install -e ".[dev,retrieval-research]"
python -m compileall -q app src scripts
pytest -q
python scripts/validate_project.py
python scripts/validate_competition_data.py
python scripts/validate_competition_runtime.py
python scripts/validate_v045_role_d_receipt.py
```

Role-B：

```bash
python scripts/audit_v045_existing_gold.py --output-dir reports/v045_role_b
python scripts/run_v046_role_b_ablation.py --subset-only
python scripts/check_v046_role_b_structured_smoke.py
python scripts/run_v046_role_b_ablation.py --run-id <RUN_ID> --modes all --execute
```

真实运行需要本地授权招股书目录与 provider 凭证；不得使用 mock 冒充 real-LLM。

## 文档入口

- 当前统一计划：[`docs/COMPETITION_CLOSURE_PLAN.md`](docs/COMPETITION_CLOSURE_PLAN.md)
- 当前 Gate：[`docs/V0.4_RELEASE_ACCEPTANCE.md`](docs/V0.4_RELEASE_ACCEPTANCE.md)
- B 线计划：[`docs/ROLE_B_M1_M2_PLAN.md`](docs/ROLE_B_M1_M2_PLAN.md)
- D 模型决议：[`docs/ROLE_D_MODEL_DECISION.md`](docs/ROLE_D_MODEL_DECISION.md)
- 指标协议：[`docs/COMPETITION_METRIC_PROTOCOL.md`](docs/COMPETITION_METRIC_PROTOCOL.md)
- 最终提交：[`docs/SUBMISSION_RUNBOOK.md`](docs/SUBMISSION_RUNBOOK.md)
- 文档审计：[`docs/DOCUMENT_AUDIT_20260828.md`](docs/DOCUMENT_AUDIT_20260828.md)

`COMPETITION_READY` 只能在全部真实 Gate、one-shot Validation、CI、Blind/provenance/determinism、安全审计和最终封包通过后使用。
