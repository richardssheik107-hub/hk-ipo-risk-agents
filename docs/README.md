# Documentation Index and Governance

> 状态日期：`2026-08-30`

仓库当前已经进入 **final submission closeout**。不再维护多套 Roadmap / Current Plan；所有当前事实必须能回到代码、机器 artifact、Release Gate 或 final submission status。

## 1. 当前权威入口

| 文档 | 作用 |
|---|---|
| `../README.md` | 项目入口、最终指标、当前 Gate 状态 |
| `FINAL_SUBMISSION_STATUS.md` | **最终提交状态、已完成/未完成、材料清单与 known limitations** |
| `V0.4_RELEASE_ACCEPTANCE.md` | **唯一实时 Release Gate / blocker 状态源** |
| `COMPETITION_CLOSURE_PLAN.md` | 最终收口执行顺序 |
| `COMPETITION_METRIC_PROTOCOL.md` | 冻结 Metric-v2、Gold、split、M1/M2/M3/M5 口径 |
| `SUBMISSION_RUNBOOK.md` | freeze → one-shot Validation → secure package 操作手册 |
| `TEAM_QUICKSTART.md` | fresh clone / canonical replay |
| `team/README.md` | owner 线最终状态 |
| `ROLE_D_MODEL_DECISION.md` | Role-D frozen model 决策入口 |
| `V045_ROLE_D_FINAL_CLOSURE.md` | Role-D hash-bound closure / receipt 历史证据 |
| `V046_ROLE_C_DYNAMIC_MARKET_X.md` | Dynamic Market-X 泛化合同 / PIT / missingness |
| `V046_ROLE_B_EXPERIMENT_LEDGER.md` | Role-B 历史实验总账，不是 live plan |

## 2. Final Development truth

```text
Best offline ALL79:
M1 = 70/102 = 68.63%
M2 = 103/191 = 53.93%

Real LLM gated ALL79:
M1 = 61/102 = 59.80%
M2 = 93/191 = 48.69%
real_llm_cases = 79/79
```

仓库自定义 G2 门槛仍是 M1 `>=80%`、M2 `>=85%`，因此 G2 保持 **BLOCKED**。Offline 与 real-LLM 必须分开写，不能用较高的 offline 结果替代 provider-backed 结果。

机器事实源：

```text
reports/v045_role_b/document_benchmark_summary.json
reports/v045_role_b/all79_final/README.md
reports/final_status/final_freeze_manifest.json
reports/final_status/product_acceptance.json
reports/final_status/capability_manifest.json
```

## 3. 当前工作状态

| Track | 状态 | 后续动作 |
|---|---|---|
| Document Intelligence | **FROZEN / G2 BELOW TARGET** | 不再 Development 调参；只记录最终事实 |
| Frontend / Product | PASS | 回归保护；只修致命展示/启动问题 |
| Dynamic Market-X | PASS | 回归保护 |
| Dynamic Model / SHAP | PASS | 回归保护 |
| Release / Submission | **P0** | Validation / audits / fresh clone / package |

## 4. Source-of-truth hierarchy

出现冲突时按顺序：

1. 代码 validator / Pydantic / fail-closed guard；
2. hash-bound frozen manifest / receipt / machine benchmark；
3. `COMPETITION_METRIC_PROTOCOL.md`；
4. `V0.4_RELEASE_ACCEPTANCE.md`；
5. `FINAL_SUBMISSION_STATUS.md`；
6. `COMPETITION_CLOSURE_PLAN.md`；
7. owner 文档 / Runbook；
8. experiment ledger / research / Git history。

fixed10 不能冒充 ALL79；offline 不能冒充 real-provider；Replay 不能冒充实时推理；定性 capability proof 不混入 M1/M2。

## 5. 文档生命周期

长期保留文档至少满足一项：

- 当前 Release Gate / Final Status / Runbook；
- 被代码或 CI 消费的合同；
- 不可重建的冻结测量 / provenance / receipt；
- 单一历史总账；
- 有明确消费者的长期 research / annotation 证据。

已过时的多份 Current Plan、单批次实验说明不再作为当前入口；历史可通过 `reports/` 和 Git history 追溯。

## 6. 不可移除的治理边界

Existing Gold immutable、`UNJUDGED != negative`、Validation one-shot、Blind outcome isolation、Evidence scope、Market PIT、missing != zero、deterministic Calculation、uncalibrated-score 语义、fallback truthfulness、Secret/PDF/raw licensed data 安全。

## 7. 当前剩余硬任务

```text
one-shot ALL19 Validation
→ one_shot_validation_receipt.json
→ final G5/G6 rehash
→ final CI / fresh clone
→ Blind / provenance / determinism / security / licensing / path audits
→ artifact index
→ secure submission ZIP + SHA256SUMS
→ PPT / 讲稿 / 演示视频或录屏（若比赛要求）
```
