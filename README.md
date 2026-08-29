# HK IPO Risk Agents

面向东吴证券港股 IPO 赛题的多智能体风险分析与上市后预警系统。

> Competition runtime：`v0.4.5`  
> Role-B optimization：`v0.4.6`  
> Metric protocol：`v045_competition_metric_protocol_v2_existing_gold_only`  
> 状态日期：`2026-08-29`  
> 当前结论：**NOT COMPETITION_READY**

## 当前五项主任务

当前 final-three 已经是稳定、可 fresh-clone 的完整演示基线。现在不再围绕“把三个案例跑通”安排工作，而是按五条主线并行冲刺：

| 主任务 | 核心目标 | 优先级 |
|---|---|---|
| **M1 / M2 文档智能优化** | ALL79 Development：M1 `>=80%`、M2 `>=85%` | **P0** |
| **前端 / 产品展示** | 把真实系统做成答辩级最终 UI | **P0/P1** |
| **Market-X 动态泛化** | 任意合法新 IPO 得到真实 Market-X，数据不足时诚实降级 | **P0** |
| **Model / Prediction / SHAP 动态化** | 不再只支持 final-three handoff；满足 feature contract 的案例真实 frozen-model inference + native SHAP | **P0** |
| **最终集成、验收、文档和提交包** | Freeze → one-shot Validation → audits → fresh clone → secure ZIP | **P1 → 最后 P0** |

唯一当前总计划：[`docs/COMPETITION_CLOSURE_PLAN.md`](docs/COMPETITION_CLOSURE_PLAN.md)。五条执行线：[`docs/team/README.md`](docs/team/README.md)。唯一实时 Release Gate：[`docs/V0.4_RELEASE_ACCEPTANCE.md`](docs/V0.4_RELEASE_ACCEPTANCE.md)。

## 当前稳定产品基线

以下能力已经进入 regression-protection 状态：

```text
Final Supervisor E1 = 3/3
real-provider first-attempt accepted = 3/3
M3 = 1.0 x 3
Market final-three = 3/3
Frozen Model final-three = 3/3
recheck = 17/17; budget-skipped = 0
seven-stage = 21/21
Evidence screenshots = 17/17 precise
canonical replay = 3 cases / 66 files
fresh clone / Streamlit smoke / team-ready checks = PASS
```

final-three 是答辩 fallback 和回归基线，不是系统能力上限。

## Role-B 最新正式 checkpoint

PR #189 已把 Batch008/009 的 accepted production fixes 和固定 journal 测量纳入 main：

```text
Batch005 fixed-journal gated  M1 = 12/30   M2 = 18/48
Batch008 fixed-journal gated  M1 = 13/30   M2 = 20/48
Batch009 fixed-journal gated  M1 = 14/30   M2 = 21/48

Batch009 offline              M1 = 9/30    M2 = 15/48
```

Batch009 当前正式 fixed-journal 比例：

```text
M1 = 14/30 = 46.67%
M2 = 21/48 = 43.75%
```

最后一个真实 fresh-provider checkpoint 仍是 Batch005：

```text
fresh gated M1 = 11/30
fresh gated M2 = 17/48
structured valid = 38/40
fallback = 2
transport failures = 0
scope rejections = 0
```

因此 **`14/30, 21/48` 是 zero-network immutable-journal 结果，不是新的 fresh-provider 结果。**

已接受：

- Batch008：legacy Chinese cash statement / explicit Notes-column deterministic compatibility；
- Batch009：generalized Legal redemption/restoration lifecycle recognition，redemption-rights M1 `4/8 → 5/8`。

已拒绝并回滚：direct ranked concentration-table candidate；它未提高 canonical M1/M2，并使 supplier existence F1 `0.875 → 0.80`。后续不得直接恢复该实现。

Role-B 当前优先级：

```text
retrieval candidate generation / ranking
→ exact page / anchor Evidence binding
→ remaining deterministic / numeric extraction
→ genuine conflict fail-closed
→ fixed-vs-fresh LLM / Evidence variance
```

执行模式允许 multi-root wide sprint：同时处理多个已经证明且兼容的 root，子修复独立 commit，bundle 统一评测，出现回归只撤问题子项；有 meaningful gain 后尽快从 fixed10 扩到更大 Development，最终必须 ALL79。

## Dynamic Market-X

PR #191 已把 governed Dynamic Market-X runtime 合入 main；最新严格离线审计覆盖
`562` 个受治理案例，`integrity_violation_count = 0`，Model handoff 为
`bound 550 / not_projectable 12`。因此 Market-X 动态化 Gate 已关闭，合法数据不足的
案例继续按 contract 诚实返回 `PARTIAL / UNAVAILABLE`。

目标 runtime：

```text
issuer / listing identity
→ validated governed cache / frozen artifact
   or governed dynamic PIT source
→ Market-X builder
→ schema / identity / provenance / hash validation
→ MarketContext
→ Market Skills / Supervisor / UI
```

合法历史不足时允许 `PARTIAL / UNAVAILABLE`，但必须给出真实 reason。禁止 post-listing leakage、missing→0、复制 final-three 数值或无来源 proxy。

## Dynamic Model / Prediction / SHAP

当前 final-three receipt-bound handoff继续保留为稳定 baseline，但最终泛化路径必须是：

```text
governed feature vector
+ final frozen model artifact/hash
→ runtime inference (no retraining)
→ uncalibrated_model_score
→ frozen alert/classification policy
→ native SHAP / signed drivers
→ ModelSignal
→ Final Supervisor / UI
```

`PROMOTE_V2` 已通过 A-owned PR #184 合并正式生效；新的 versioned freeze、strict
receipt、checker 和 final-three label-free handoff 均已保留，历史 PR-F 身份未被覆盖。
当前仍开放的是非 final-three 案例的真实 frozen-model runtime inference + native SHAP，
不能用 per-case handoff 冒充该能力。

## 前端 / 产品

最终 UI 明确支持：

```text
1. Offline Demo Replay
2. Historical Governed IPO
3. Fresh New-IPO Analysis
```

并把 Risk/Evidence、Market、Model/SHAP、Conflict/Recheck、Final Supervisor、Report/Trace 做成评委一眼能理解的研究/风控工作台。

发行人输入已支持 official catalog-backed 快速匹配；所有 `AVAILABLE / PARTIAL / UNAVAILABLE` 必须来自真实 runtime contract，前端不自己补 Market/Model/Evidence。

## 治理边界

任何冲刺都不能改变：

- Existing Gold immutable，`UNJUDGED != negative`；
- Gold 不进入 runtime Retriever / Prompt / Agent；
- 2024 Validation 只允许 freeze 后 one-shot；
- 2025 Blind 不用于优化；
- 不按公司、股票、case、页码、Gold 文本 hardcode；
- LLM 不 invent Evidence / market fact；
- exact numeric claim 由 deterministic Calculation 支撑；
- Market PIT-safe，missing 不等于 zero；
- model score 不称 probability；
- fallback 不冒充 real-provider success；
- Secret、授权 PDF、raw EOD、raw journal、本地绝对路径不进入 Git / submission bundle。

## 快速入口

```bash
pip install -e ".[dev,retrieval-research]"
python -m compileall -q app src scripts
pytest -q
python scripts/validate_project.py
python scripts/validate_competition_data.py
python scripts/validate_competition_runtime.py
python scripts/validate_v045_role_d_receipt.py
python scripts/check_v045_product_runtime.py
python scripts/check_v045_team_clone_ready.py
python scripts/run_final_acceptance.py --ci-status pass --ci-evidence-url <LATEST_MAIN_CI_URL>
```

离线答辩基线：

```bash
python scripts/check_v045_team_clone_ready.py
# Windows
START_DEMO.bat
# macOS / Linux
./start_demo.sh
```

## 文档入口

- [`docs/README.md`](docs/README.md) — 文档索引 / source-of-truth 规则
- [`docs/COMPETITION_CLOSURE_PLAN.md`](docs/COMPETITION_CLOSURE_PLAN.md) — **唯一当前总计划**
- [`docs/team/README.md`](docs/team/README.md) — 五条并行工作线
- [`docs/V0.4_RELEASE_ACCEPTANCE.md`](docs/V0.4_RELEASE_ACCEPTANCE.md) — **唯一实时 Release Gate**
- [`docs/COMPETITION_METRIC_PROTOCOL.md`](docs/COMPETITION_METRIC_PROTOCOL.md) — 冻结指标协议
- [`docs/V046_ROLE_B_EXPERIMENT_LEDGER.md`](docs/V046_ROLE_B_EXPERIMENT_LEDGER.md) — Role-B 历史实验总账，不是当前计划
- [`docs/ROLE_D_MODEL_DECISION.md`](docs/ROLE_D_MODEL_DECISION.md) — D promote/retain 决策入口
- [`docs/SUBMISSION_RUNBOOK.md`](docs/SUBMISSION_RUNBOOK.md) — freeze / Validation / 打包 Runbook

历史单批实验不再作为当前计划入口；需要追溯时使用 machine-readable `reports/` artifacts 和 Git history。
