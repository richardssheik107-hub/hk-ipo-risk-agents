# Documentation Index — v1.0.0

> Release: `v1.0.0`  
> 状态日期：`2026-08-30`  
> 文档状态：**FINAL / CLOSED FOR COMPETITION RELEASE**  
> Final product-surface freeze: `006c7f302be5c278680d136371f6ef0db45fecc0`

v1.0.0 之后不再维护第二套 Roadmap、并行冲刺计划或“当前 Batch”状态页。所有开发型 owner 文档均已收口为最终状态/历史职责说明。

## 1. v1.0.0 当前权威入口

| 文档 | 作用 |
|---|---|
| `../README.md` | 项目首页、v1.0.0 能力、最终指标与启动方式 |
| `RELEASE_NOTES_V1.0.0.md` | **v1.0.0 正式 Release Notes** |
| `V1_RELEASE_ACCEPTANCE.md` | **v1.0.0 Release / Gate 真相源** |
| `FINAL_SUBMISSION_STATUS.md` | 最终比赛提交状态、材料与剩余本地动作 |
| `COMPETITION_CLOSURE_PLAN.md` | 冻结后的最终收口状态，不再是研发 Roadmap |
| `COMPETITION_METRIC_PROTOCOL.md` | 冻结 Metric-v2 / Gold / split / M1/M2/M3/M5 口径 |
| `SUBMISSION_RUNBOOK.md` | one-shot Validation、fresh clone、安全审计、封包操作手册 |
| `AUTHORIZED_SOURCE_HANDOFF.md` | 赛题来源哈希、授权数据复用方式与不可上传边界 |
| `TEAM_QUICKSTART.md` | fresh clone / canonical replay /统一产品入口 |
| `FRONTEND_JUDGE_FACING_HANDOFF.md` | 最终评审入口与 canonical UI 信息架构 |
| `ROLE_D_MODEL_DECISION.md` | Role-D V2 最终模型决议与边界 |
| `V046_ROLE_C_DYNAMIC_MARKET_X.md` | Dynamic Market-X 冻结技术合同 |

## 2. Machine-readable final truth

```text
reports/v045_role_b/document_benchmark_summary.json
reports/final_status/final_freeze_manifest.json
reports/final_status/submission_closeout_status.json
reports/final_status/product_acceptance.json
reports/final_status/capability_manifest.json
reports/v046_dynamic_model_runtime/dynamic_model_runtime_audit.json
```

`one_shot_validation_receipt.json` 只有在授权环境真实执行一次 Validation 后才能加入。

文档与 artifact 冲突时，以代码 validator / frozen manifest / machine-readable receipt 为优先事实源。

## 3. Final Development measurements

| Mode | Cases | M1 | M2 |
|---|---:|---:|---:|
| Best offline | 79/79 | 70/102 = 68.63% | 103/191 = 53.93% |
| Real LLM gated | 79/79 | 61/102 = 59.80% | 93/191 = 48.69% |

G2 内部门槛仍是 M1 >=80%、M2 >=85%、real LLM 79/79，因此 G2 为 **BLOCKED**。v1.0.0 是正式比赛产品发布版，不等于 `COMPETITION_READY=true`。

## 4. Final product surface

Latest approved product-surface commit:

```text
006c7f302be5c278680d136371f6ef0db45fecc0
```

All launch paths converge on the same canonical app:

```text
START_DEMO.bat       ─┐
start_demo.sh         ├─→ app/streamlit_app.py
START_JUDGE_DEMO.bat  ┤
start_judge_demo.sh  ─┘
```

The judge commands are compatibility aliases. On `006c7f3...`, `tests`, `Role D runtime` and `Team demo runtime` all passed.

## 5. Team owner 文档

`team/` 不再表示活跃开发队列，而是最终职责归档：

```text
01_M1_M2_OWNER.md              CLOSED / FROZEN / G2 BLOCKED
02_FRONTEND_OWNER.md           CLOSED / G5 PASS / CANONICAL UI
03_DYNAMIC_MARKET_X_OWNER.md   CLOSED / G3 PASS
04_DYNAMIC_MODEL_OWNER.md      CLOSED / G4 PASS
05_RELEASE_SUBMISSION_OWNER.md RELEASE OPERATIONS ONLY
```

`team/README.md` 给出最终状态摘要。

## 6. 长期规范 / 冻结技术文档

以下文档继续保留，不因 v1.0.0 改名或重写内部 protocol identity：

- `PROJECT_SPEC.md`
- `ARCHITECTURE.md`
- `DATA_SCHEMA.md`
- `COMPETITION_DATA_OVERVIEW.md`
- `COMPETITION_METRIC_PROTOCOL.md`
- `V046_ROLE_C_DYNAMIC_MARKET_X.md`
- `V046_ROLE_B_EXPERIMENT_LEDGER.md`
- `research/*`
- `annotation/*`

这些是技术合同、研究证据或历史 provenance，不是当前研发计划。

## 7. Historical / superseded docs

`V0.4_RELEASE_ACCEPTANCE.md` 仅保留为 v0.4 阶段历史入口，已由 `V1_RELEASE_ACCEPTANCE.md` 取代。

Batch / Bundle / fixed-journal / forensic 等历史结果只能用于追溯，不能覆盖 v1.0.0 Final Truth。

## 8. Source-of-truth hierarchy

出现冲突时按顺序：

1. runtime validator / Pydantic / fail-closed guard；
2. frozen / final-status machine-readable artifacts；
3. `COMPETITION_METRIC_PROTOCOL.md`；
4. `V1_RELEASE_ACCEPTANCE.md`；
5. `FINAL_SUBMISSION_STATUS.md`；
6. `SUBMISSION_RUNBOOK.md`；
7. frozen technical contracts；
8. historical experiment/research docs and Git history。

## 9. Release governance

不可移除的边界：

```text
Existing Gold immutable
UNJUDGED != negative
Gold never enters runtime
Validation one-shot after freeze
2025 Blind outcome not used for optimization
PIT-safe Market
missing != zero
no issuer/case/page/Gold hardcoding
no fabricated Evidence
uncalibrated model score != probability
fallback != real-provider success
no secrets / licensed PDF / raw EOD / raw provider journal in release package
```
