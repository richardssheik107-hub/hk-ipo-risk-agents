# Role-D Model Decision — Frozen PR-F vs v2 Candidate

> 状态日期：`2026-08-28`
>
> 当前决议：**PROMOTE V2 — EFFECTIVE ON A-OWNED MERGE OF THE PROMOTION PR**

本文档把“正式可复现模型”和“效果更好的研究候选”分开，避免两种常见误判：一是把四文件物化完成等同于业务效果已经足够；二是把尚未治理晋升的候选直接写成正式系统结果。

## 1. 两条模型线

| 项目 | Frozen PR-F | v2 candidate |
|---|---:|---:|
| 状态 | 保留的旧正式冻结 / 已有 70-case receipt | 新版本化 freeze/receipt；由 A 合并本 PR 后生效 |
| 选择数据 | 历史 frozen protocol | 2020→2021、2020–21→2022、2020–22→2023 expanding Development folds |
| 2024 用途 | 正式记录结果 | 冻结候选后一次性评价 |
| ROC-AUC | 0.4246 | 0.4875 |
| PR-AUC | 0.3364 | 0.3812 |
| Precision | 0.3333 | 0.3529 |
| Recall | 0.0435 | 0.5217 |
| F1 | 0.0769 | 0.4211 |
| Alert count | 3 | 34 |
| 2025 Blind y | 未访问 | 未访问 |

v2 使用七个 Market Core regime features，并保留原 LightGBM 参数。候选选择与 alert fraction 只使用 expanding Development folds；仓库报告声明 2024 label 未用于 feature/model/alert selection。

## 2. 正确解释

v2 候选显著改善：

- 高风险样本召回；
- F1；
- PR-AUC；
- Brier；
- 实际可用的 alert 覆盖。

它晋升后的产品定位仍是 triage signal：

- ROC-AUC 仍略低于 0.5；
- score 未校准；
- promotion record、严格 receipt 和 D→E handoff 已版本化生成；
- A 对本 promotion PR 的合并记录是决议生效证据。

因此当前最强可支持表述是：

> Development-selected V2 substantially improves the governed high-recall operating point over frozen PR-F. It remains an uncalibrated triage signal, and promotion becomes effective only through A-owned merge of the versioned freeze/receipt PR.

不能写成：

- “预测模型已经正式达到优秀水平”；
- “v2 已替换正式模型”；
- “ROC-AUC 已显著超过随机”；
- “score 是破发概率”。

## 3. A-owned promotion Gate

A 应进行一次明确、可审计的晋升决策，而不是继续在 2024 上试更多方案。

### A 合并前审核项

1. v2 实现和报告身份与仓库代码一致；
2. expanding Development selection 可从原始 artifact 重放；
3. 2024 只执行一次冻结评价；
4. 2025 Blind outcome 未访问；
5. deterministic repeat hash 通过；
6. 与 frozen PR-F 的比较公式、case universe 和 label 定义一致；
7. score 继续标为 `uncalibrated_model_score`；
8. 对 34 个 alerts 的业务工作量与命中率给出解释。

### 晋升选项

#### Option A — Promote v2

- 创建 hash-bound promotion decision；
- 冻结 v2 code/config/feature list/alert policy；
- current-main 重建四个 Role-D artifact；
- strict checker 独立复算；
- 生成新的 final-three label-free handoff；
- 更新 A readiness、案例报告和答辩指标；
- 不再根据 2024 结果调整任何参数。

#### Option B — Retain frozen PR-F

- 保留现有 receipt；
- 将模型定位为弱辅助信号；
- 强调 Document + Market + Agent 归因价值，不把 M5 作为强预测卖点；
- 同样完成 current-main strict revalidation 和 final-three handoff。

## 4. 晋升决议载体

本 PR 实现 Option A，并把审批动作收敛为 A-owned GitHub merge：A 合并即确认完成身份、复现、determinism、leakage、工作量和局限审核。未合并前，本分支只是一份完整晋升候选；合并进入 `main` 后，版本化 promotion record 生效。

旧 PR-F manifest、receipt、四项结果和 handoff 均保留，不覆盖、可回滚。

## 5. 停止规则

从现在起不得：

- 继续根据 2024 调 feature、threshold 或 alert fraction；
- 反转 score；
- 用 2025 Blind 输入或 outcome 选择模型；
- 直接编辑 D artifact 使其显示 v2；
- 在没有新 freeze/receipt 的情况下让 E 消费 v2 signal。

下一动作只有：

```text
A 审核本 promotion PR
→ 合并：V2 晋升生效，前端消费 V2 handoff
→ 不合并：main 继续保留旧 PR-F
```
