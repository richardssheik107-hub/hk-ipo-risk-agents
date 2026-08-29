# Five-Person Competition Execution Index

> 状态日期：2026-08-29  
> 目的：把当前剩余比赛任务拆成 5 条互不覆盖、可以并行推进的工作流。

## 当前总体状态

当前稳定产品基线已经具备：

```text
Final Supervisor E1 = 3/3
M3 = 1.0 x 3
Market final-three = 3/3
Model final-three = 3/3
rechecks = 17/17
budget skipped = 0
seven-stage = 21/21
Evidence screenshots = 17/17 precise
canonical replay = 3 cases / 66 files
fresh clone = PASS
```

当前真正剩余的核心竞争任务：

```text
1. ALL79 M1 / M2
2. Dynamic Market-X
3. Dynamic Model / SHAP + formal D decision
4. Final competition frontend
5. Freeze / Validation / audits / final submission
```

Human Review / M4 已从 Release Gate 中移除，只保留 optional 产品能力。

## 五人分工

### Person 1 — M1 / M2 Document Intelligence

文档：[`01_M1_M2_OWNER.md`](01_M1_M2_OWNER.md)

一句话目标：

> 让系统“识别得准”。

正式完成条件：

```text
ALL79 Development
M1 >= 0.80
M2 >= 0.85
real LLM = 79/79
```

建议分支：

```text
codex/role-b-m1-m2
```

---

### Person 2 — Frontend / Product Experience

文档：[`02_FRONTEND_OWNER.md`](02_FRONTEND_OWNER.md)

一句话目标：

> 让系统“展示得像成熟产品”。

负责 Demo / Historical / Fresh 三种模式、七阶段、Risk、Evidence、Market、Model、SHAP、Conflict、Supervisor、Report 的最终前端体验。

建议分支：

```text
codex/final-product-ui
```

---

### Person 3 — Dynamic Market-X

文档：[`03_DYNAMIC_MARKET_X_OWNER.md`](03_DYNAMIC_MARKET_X_OWNER.md)

一句话目标：

> 让任意合法 IPO case 都有正确的 Market runtime，而不是只支持三个 Demo。

路线：

```text
438 historical universe
→ arbitrary new IPO Dynamic PIT Market-X
```

建议分支：

```text
codex/dynamic-market-x
```

---

### Person 4 — Dynamic Model / Prediction / SHAP

文档：[`04_DYNAMIC_MODEL_OWNER.md`](04_DYNAMIC_MODEL_OWNER.md)

一句话目标：

> 让任意满足 feature contract 的案例都能真实加载冻结模型推理，并动态生成 SHAP。

同时负责：

```text
frozen PR-F vs v2 candidate formal decision
model freeze / receipt / manifest
historical dynamic inference
fresh-case model path
competition capability coverage coordination
```

建议分支：

```text
codex/dynamic-model-runtime
```

---

### Person 5 — Release / Submission

文档：[`05_RELEASE_SUBMISSION_OWNER.md`](05_RELEASE_SUBMISSION_OWNER.md)

一句话目标：

> 让前四个人的成果“真的能提交”。

负责：

```text
integration
freeze
one-shot Validation
CI
audits
artifact index
fresh clone
submission ZIP / manifest / SHA-256
```

建议分支：

```text
codex/release-submission
```

## 依赖关系

```text
Person 1 Document Intelligence ─────┐
                                    │
Person 3 Dynamic Market-X ──────────┼──→ Person 4 Dynamic Model / SHAP
                                    │            │
existing governed runtime ──────────┘            │
                                                 ▼
                                      Final Supervisor / Report
                                                 │
                                                 ▼
                                      Person 2 Frontend / UX
                                                 │
                                                 ▼
                                      Person 5 Release / Submit
```

Person 5 从项目开始就持续做 integration watch，但只有在 Person 1 / 3 / 4 的核心能力 freeze 后，才执行最终 one-shot Validation。

## 代码边界

### Person 1 不应该顺手做

```text
Market / Model / UI / package
```

### Person 2 不应该顺手做

```text
Risk algorithm / Market calculation / model tuning
```

### Person 3 不应该顺手做

```text
M1/M2 tuning / model training / frontend fake values
```

### Person 4 不应该顺手做

```text
Retriever / Gold evaluator / frontend visual redesign
```

### Person 5 不应该顺手做

```text
为了让 Gate 变绿而修改算法指标或安全标准
```

## Shared non-negotiables

五个人都必须遵守：

```text
Existing Gold immutable
Validation only once after freeze
2025 Blind untouched for optimization
PIT-safe Market
missing != zero
no company/page hardcoding
no fake Evidence / bbox
uncalibrated model score != probability
fallback != real-provider success
no secrets / licensed PDF / raw EOD in Git
```

## Merge 原则

每个人独立分支工作，通过：

```text
targeted tests
integration tests
git diff --check
relevant CI
```

再 PR → main。

稳定 `main` 始终作为可回退的答辩基线；任何新功能不得以破坏 canonical 3-case Demo 为代价。

## 最终完成条件

全队只有在以下全部成立时才可声明 `COMPETITION_READY`：

```text
ALL79 M1 >= 0.80
ALL79 M2 >= 0.85
M3 = 1.0
formal D model decision complete
Dynamic Market-X complete / boundary documented
Dynamic Model / SHAP complete
competition capability cases complete
final frontend complete
one-shot Validation complete under freeze
latest-main CI PASS
Blind / provenance / determinism / security PASS
fresh clone PASS
secure submission package PASS
```

详细执行要求以五份 owner 文档和 `docs/V0.4_RELEASE_ACCEPTANCE.md` 为准。