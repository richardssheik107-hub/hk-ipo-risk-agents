# HK IPO Risk Agents

面向港股 IPO 招股书风险识别、市场环境解释与可审计多 Agent 决策的比赛型原型系统。

> 当前 package checkpoint：`v0.4.0`
>
> 当前比赛 runtime：`v0.4.5`
>
> 当前状态：**Competition closure in progress — 尚未标记 `COMPETITION_READY`**

## 当前能力

```text
Prospectus PDF
→ Parser / Retriever / Evidence
→ Financial deterministic analysis
→ Legal / Business structured LLM analysis
→ Verifier / Document Supervisor
→ governed Market-X
→ IPOHeatSkill / MarketRegimeSkill
→ bounded Market LLM interpretation
→ Rule / optional authentic frozen Model signal
→ Conflict detection
→ one bounded targeted re-check
→ LLM Final Supervisor with deterministic fallback
→ Agent / Tool / Evidence Trace
→ Human Review
→ Streamlit / report / submission artifacts
→ A-owned readiness / Blind / provenance / determinism / package gate
```

核心治理原则：

- LLM 负责语义理解与综合，不负责权威数值计算；
- 精确计算由 Python `Calculation` 完成；
- 正式 `RiskItem` 必须有真实 `Evidence`；
- LLM 只能引用输入作用域内的 Evidence / Risk / Conflict；
- 市场事实必须来自 PIT-governed Market-X，缺失不得补零或造代理；
- 未校准模型分数只能称 `uncalibrated_model_score`；
- 2024 Validation 不做 post-hoc tuning；2025 Blind outcome 未授权前不访问；
- frozen PR-A–PR-G 不因比赛展示需要而重写。

## Competition Metric Protocol v1

赛题原文件给出了几个目标，但没有给出完整 evaluator 公式。项目现已冻结：

```text
docs/COMPETITION_METRIC_PROTOCOL.md
configs/v045_competition_metric_protocol.json
```

Protocol ID：

```text
v045_competition_metric_protocol_v1
```

正式比赛指标解释从现在开始统一采用：

| Metric | Official requirement | Project primary definition |
|---|---:|---|
| M1 Risk extraction | >=80% | attribute-correct positive Gold Risk Unit Accuracy |
| M2 Evidence recall | >=85% | Evidence Group Coverage Recall，**不是 Recall@5** |
| M3 Traceability | 100% | accounted Agent/Tool/Evidence-or-reason trace |
| M4 Explanation | “高” | 5维、2+ human reviewers，内部目标 >=4.0/5 |
| M5 Post-listing | 1D/5D/20D/60D；5D更高权重 | 5D primary，`return_5d <= -10%` 为预先冻结的 significant-drop 定义 |

### M1 primary risk families

为对齐赛题点名的风险范围，metric-v1 的 primary families 固定为：

```text
redemption_rights
related_party_transaction        # additive competition sidecar
customer_concentration
supplier_concentration
cash_burn_pressure               # metric family mapped to existing cash_runway/cash-burn calculation
```

这只是比赛评价映射，不静默改动 frozen formal baseline risk registry。

### M2 不再把 Recall@5 当成官方 85%

当前历史 offline benchmark 的：

```text
Evidence Recall@1/@3/@5 = 20% / 20% / 20%
```

继续保留为**排序/端到端诊断事实**，但赛题原文没有指定 Top-K，因此不能再写成“官方 Evidence Recall 当前为 20%”。最终 official-aligned Evidence Gate 使用：

```text
covered Gold Evidence Groups / all Gold Evidence Groups >= 85%
```

Recall@1/@3/@5/@10/@20 作为 secondary diagnostics。

## 最新实测状态

### 1. 三个真实招股书案例已完成 offline E2E

| Case | Stock | Pages | Status | Conflicts | Re-checks | Traceability |
|---|---|---:|---|---:|---:|---:|
| `ipo_2024_02410` | `2410.HK` | 706 | completed | 6 | 3 | 1.0 |
| `ipo_2024_02460` | `2460.HK` | 579 | completed | 7 | 3 | 1.0 |
| `ipo_2024_01318` | `1318.HK` | 617 | completed | 7 | 3 | 1.0 |

三份 PDF 均通过 SHA-256、字节数和物理页数校验；结构化 workflow error 为 0；未读取任何 outcome label，也没有访问 2025 Blind y。

### 2. Role B 仍是第一质量 blocker

当前正式测得的是旧 10-case governed **offline diagnostic baseline**：

```text
Risk Precision / Recall / F1      0% / 0% / 0%
Evidence Recall@1 / @3 / @5       20% / 20% / 20%
Physical-page correctness         100%
Real LLM cases                    0
```

这不能证明 metric-v1 的 M1/M2 达标。B 下一步必须：

```text
real-LLM measurement first
→ build/freeze metric-v1 Development Gold
→ candidate Retrieval Recall@20
→ reranked Recall@10
→ Evidence Group Coverage Recall
→ structured extraction / reconciliation / Verifier
→ M1/M2 rerun
```

当前重点 failure mode 仍是 `Evidence → structured extraction → RiskItem / Verifier`。

### 3. Market Intelligence 主体已实现

已实现 governed `MarketContext`、IPOHeatSkill、MarketRegimeSkill、bounded Market LLM、PIT/missingness 与 Trace/Final Supervisor handoff。最终只剩同一 3-case submission matrix 上的 Market state / trace accounting 验收。

### 4. LLM Final Supervisor / Product 已实现，real-provider acceptance 仍 open

三案例 offline matrix traceability 均为 1.0；reasoning log、case report 和 machine Gate-E1 evidence 已实现。当前 measured offline matrix 仍为 **0/3 successful LLM arbitration**，最终需 real-provider accepted run。

metric-v1 另外要求 E 在最终案例上生成 `explanation_quality.json`，用至少 2 名人类 reviewer 对 Evidence grounding、logical consistency、conflict handling、re-check quality、final conclusion 评分。

### 5. Outcome / Model 最终比赛包仍未闭合

D 仍需生成：

```text
return_1d
return_5d
return_20d
return_60d

test_predictions.csv
multi_horizon_results.csv
evaluation_summary.json
ai_vs_offline_report.json
```

5D 是 primary business horizon。metric-v1 已在 Validation 重评前固定：

```text
significant_drop_5d = (return_5d <= -0.10)
```

并要求报告 Precision / Recall / F1 / PR-AUC / ROC-AUC / Top-10% 与 Top-20% risk-bucket hit rate。赛题没有给这些指标的绝对合格线，因此项目不会伪造一个“官方阈值”。

### 6. A submission tooling 已实现，但需要 metric-v1 handoff 对齐

A 已实现 readiness、Blind/provenance/determinism audit、artifact index、Runbook 与 fail-closed packager。最终 freeze 前，B/D/E 新 handoff 必须按 `COMPETITION_METRIC_PROTOCOL.md` 输出 metric-v1 字段；A readiness 只允许消费真实、可审计 artifact，legacy-only Recall@5 不能作为最终 M2 PASS。

## 当前比赛 Gate

| Gate | Status |
|---|---|
| competition runtime contracts | PASS |
| Market Intelligence implementation + AI wiring | PASS |
| 3 real PDF offline E2E | PASS |
| Conflict / re-check / Trace / Human Review | PASS implementation |
| 3-case offline traceability | PASS = 1.0 |
| A readiness / audit / Runbook / packager | PASS implementation |
| Metric Protocol v1 definition | **FROZEN** |
| B metric-v1 M1 Risk benchmark | **OPEN / P0** |
| B metric-v1 M2 Evidence Group Recall | **OPEN / P0** |
| D 1D/5D/20D/60D + frozen 5D evaluation | **OPEN / P0** |
| E real-provider Final Supervisor | **OPEN / P1** |
| E explanation-quality evaluation | **OPEN / P1** |
| C final-matrix Market validation | **OPEN / P1** |
| Evidence bbox upstream grounding | P2 quality gap |
| Final real audits / bundle / release freeze | **OPEN** |

详细状态见 `docs/V0.4_RELEASE_ACCEPTANCE.md`。

## 文档入口

- Metric contract：`docs/COMPETITION_METRIC_PROTOCOL.md`
- 当前 Gate：`docs/V0.4_RELEASE_ACCEPTANCE.md`
- 最终提交 Runbook：`docs/SUBMISSION_RUNBOOK.md`
- 剩余路线：`docs/ROADMAP.md`
- 五人执行：`docs/V04_FIVE_PERSON_EXECUTION_PLAN.md`
- 赛题映射：`docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`
- 数据与 split：`docs/COMPETITION_DATA_OVERVIEW.md`
- 当前 B 离线历史基线：`docs/V045_ROLE_B_REAL_BENCHMARK_REPORT.md`

冻结 completion reports、`reports/frozen/*` 和 research 文档属于历史/研究证据，不因 metric-v1 改写其原始实测事实。

## 快速运行

```bash
pip install -e ".[dev,retrieval-research]"
python scripts/validate_competition_runtime.py
```

最终 `COMPETITION_READY` 只能在 metric-v1 与其余 hard Gate 被真实数据关闭之后使用。
