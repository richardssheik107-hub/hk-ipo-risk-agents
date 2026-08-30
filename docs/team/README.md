# Competition Execution Index — Final Closeout

> 状态日期：`2026-08-30`  
> 当前阶段：**Release / Submission P0**

五条研发线已经收敛，不再并行扩功能。当前唯一主线是把冻结系统变成可验证、可审计、可展示、可提交的最终材料。

## 当前 owner 状态

| Owner | 主任务 | 状态 | 后续 |
|---|---|---|---|
| **Person 1** | M1 / M2 Document Intelligence | **CLOSED / BELOW G2 TARGET** | 不再调参；只保留 benchmark/provenance |
| **Person 2** | Frontend / Product | **PASS** | 回归保护、现场演示准备 |
| **Person 3** | Dynamic Market-X | **PASS** | 回归保护 |
| **Person 4** | Dynamic Model / SHAP | **PASS** | 回归保护 |
| **Person 5** | Release / Submission | **P0 ACTIVE** | Validation / audits / fresh clone / package / materials |

## Final Development truth

```text
Best offline ALL79:
M1 = 70/102 = 68.63%
M2 = 103/191 = 53.93%

Real LLM gated ALL79:
M1 = 61/102 = 59.80%
M2 = 93/191 = 48.69%
real_llm_cases = 79/79
```

正式 G2 门槛仍为 M1 `>=80%`、M2 `>=85%`，因此 G2 保持 BLOCKED。

## 已关闭稳定产品基线

```text
Final Supervisor E1 = 3/3
M3 = 1.0 x 3
Market final-three = 3/3
Model final-three = 3/3
rechecks = 17/17
seven-stage = 21/21
Evidence screenshots = 17/17 precise
canonical replay = 3 cases / 66 files
G3 Market-X = PASS
G4 Model / SHAP = PASS
G5 Product = PASS
G6 Capabilities = PASS
main CI = PASS
```

## Person 5 当前唯一执行队列

```text
runtime freeze recorded
→ one-shot ALL19 Validation
→ one_shot_validation_receipt.json
→ final G5/G6 rehash
→ final CI
→ fresh clone
→ Blind / provenance / determinism / security / licensing / path audits
→ artifact index
→ secure ZIP + SHA256SUMS
→ PPT / 讲稿 / 演示材料
```

## Shared non-negotiables

```text
Existing Gold immutable
UNJUDGED != negative
Gold never enters runtime
Validation only once after freeze
2025 Blind outcome not used for optimization
PIT-safe Market
missing != zero
no company/stock/case/page/Gold-text hardcoding
no fake Evidence / Market / Model
uncalibrated model score != probability
fallback != real-provider success
no secrets / licensed PDF / raw EOD / raw journal / absolute local path in Git
```

## 当前文档入口

```text
../FINAL_SUBMISSION_STATUS.md
../V0.4_RELEASE_ACCEPTANCE.md
../COMPETITION_CLOSURE_PLAN.md
../SUBMISSION_RUNBOOK.md
01_M1_M2_OWNER.md
05_RELEASE_SUBMISSION_OWNER.md
```

Person 2/3/4 的历史 owner 文档继续作为实现与 provenance 参考，但不再承载开放式研发任务。

## 最终完成定义

“可以向比赛平台提交作品”与仓库自定义 `COMPETITION_READY` 分开判断。

仓库只有在 G2 与 G7 等全部 Gate 真正关闭后才能声明 `COMPETITION_READY`。当前 G2 未达门槛，因此最终材料必须如实披露；不得通过改门槛或换口径制造绿色状态。
