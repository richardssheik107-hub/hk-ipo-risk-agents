# Role-D Model Decision — Frozen PR-F vs v2 Candidate

> 状态日期：`2026-08-29`
>
> 当前决议：**PENDING A-OWNED PROMOTION REVIEW**

本文档把“当前正式 frozen identity”“效果更好的 research candidate”和“Dynamic New-IPO inference”分开。

## 1. 两条模型线

| 项目 | Frozen PR-F | v2 candidate |
|---|---:|---:|
| 状态 | 正式冻结 / 已有 70-case receipt | Research candidate / 未晋升 |
| 选择数据 | 历史 frozen protocol | Development expanding folds |
| 2024 用途 | 正式记录结果 | 候选冻结后一次性评价 |
| ROC-AUC | 0.4246 | 0.4875 |
| PR-AUC | 0.3364 | 0.3812 |
| Precision | 0.3333 | 0.3529 |
| Recall | 0.0435 | 0.5217 |
| F1 | 0.0769 | 0.4211 |
| Alert count | 3 | 34 |
| 2025 Blind y | 未访问 | 未访问 |

## 2. 当前产品事实

PR #185 已证明 final-three 产品路径：

```text
Market = 3/3
Frozen Model = 3/3
Final Supervisor = 3/3
M3 = 1.0 x 3
canonical replay / fresh clone = PASS
```

这说明 frozen PR-F 的**三案例 product handoff 已可稳定消费**，但不等于模型业务价值已经充分，也不等于新 IPO 可以动态推理。

当前 `FrozenModelPredictionProvider` 的正式产品路径仍以 governed per-case handoff / frozen result 为主；下一产品目标是加载受治理的 frozen model identity，对非 final-three feature vector 做真实 dynamic inference + native SHAP。

## 3. 正确解释

v2 候选明显改善高召回 operating point，但：

- ROC-AUC 仍低于 0.5；
- score 未校准；
- 没有正式 promotion record；
- 当前 receipt / handoff 仍绑定 frozen PR-F。

因此最强可支持表述仍是：

> Development-selected v2 candidate substantially improves the high-recall operating point over frozen PR-F, but remains an uncalibrated research candidate pending governance promotion.

不能写成：

- “预测模型已经正式达到优秀水平”；
- “v2 已替换正式模型”；
- “score 是破发概率”；
- “final-three handoff 证明任意新 IPO 都能模型推理”。

## 4. A-owned promotion Gate

A 只进行一次明确、可审计决议，不继续按 2024 调试更多方案。

### 审核项

1. v2 实现/报告身份与仓库代码一致；
2. Development expanding-fold selection 可重放；
3. 2024 仅一次冻结评价；
4. 2025 Blind outcome 未访问；
5. deterministic repeat hash 通过；
6. 与 frozen PR-F 的 case universe / label / metric 一致；
7. score 保持 `uncalibrated_model_score`；
8. 34 alerts 的工作量和命中率可解释。

### Option A — Promote v2

- 创建 hash-bound promotion decision；
- 冻结 v2 code/config/feature list/alert policy；
- current-main 重建 Role-D artifacts；
- strict checker 独立复算；
- 建立新 versioned product/dynamic inference identity；
- 更新 final-three handoff；
- 不再根据 2024 调参数。

### Option B — Retain frozen PR-F

- 保留现有 receipt；
- 将模型定位为弱辅助 signal；
- 不把 M5 当强预测卖点；
- 同样建立 frozen-model dynamic inference contract，使 historical/new cases 不依赖 final-three 预生成结果。

## 5. Dynamic inference requirement

无论 promote 还是 retain，最终产品都应该从：

```text
governed feature vector
+ frozen model artifact / model hash
```

产生：

```text
uncalibrated_model_score
+ native SHAP / top drivers
```

而不是仅查询一个预生成 case prediction。

硬边界：

- feature manifest hash 必须匹配；
- model identity/hash 必须匹配；
- missingness 语义不能改变；
- 不得用 2024/Blind label 参与新 case inference；
- SHAP 必须来自实际 inference；
- score 不得称 probability。

## 6. 推荐决策

仍优先审核 Option A，因为 v2 修复了 frozen PR-F 几乎不报警的问题。但这是治理建议，不是 promotion 结论。

Dynamic New-IPO inference 与 promote/retain 决议可以并行设计 adapter，但正式模型身份必须等 A 决议后冻结。

## 7. 停止规则

不得：

- 根据 2024 调 feature / threshold / alert fraction；
- 反转 score；
- 用 2025 Blind input/outcome 选择模型；
- 直接编辑 frozen D artifact 伪装 v2；
- 复制 final-three per-case signal 冒充 dynamic inference。

下一动作：

```text
A governance review
→ promote or retain
→ freeze formal model identity
→ dynamic inference + strict revalidation
```
