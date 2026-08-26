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

## Competition Metric Protocol v2 — Existing-Gold-Only

当前 Metric Protocol：

```text
v045_competition_metric_protocol_v2_existing_gold_only
```

文档与机器配置：

```text
docs/COMPETITION_METRIC_PROTOCOL.md
configs/v045_competition_metric_protocol.json
```

### M1/M2 Gold policy

项目不再为比赛收尾新增人工标注。M1/M2 唯一 Gold 来源是此前已经存在并冻结的 Expert Annotation / Oracle Gold：

```text
annotation inventory   101
valid annotations      100
official materialized   98
```

注意：98 只是 official materialized annotation 数，不意味着每家公司对所有 risk 都有 Gold。实际 M1/M2 support 由只读 evaluator 统计。

从现在开始明确：

```text
不新增 M1/M2 人工 Gold
不修改旧专家答案
不补低 support risk family
不把未标注项当 negative
不人工重做 Evidence Group
```

系统效果提升只允许来自：

```text
Retriever / ranking code
+ real LLM Prompt / structured extraction
+ normalization / RiskItem reconciliation
+ Verifier
```

并且只在 Development 上调优。

### 当前正式指标解释

| Metric | Official requirement | Project primary definition |
|---|---:|---|
| M1 Risk extraction | >=80% | Existing-Gold positive Risk Unit Accuracy；project target >=85% |
| M2 Evidence recall | >=85% | Existing-Gold Evidence Coverage Recall；project target >=88% |
| M2 Recall@K | 官方未指定 | Recall@1/@3/@5/@10/@20 仅作诊断 |
| M3 Traceability | 100% | accounted Agent/Tool/Evidence-or-reason trace |
| M4 Explanation | “高” | 沿用当前 final product rubric |
| M5 Post-listing | 1D/5D/20D/60D；5D更高权重 | 5D primary，`return_5d <= -10%` 为项目预先定义 |

如果旧 Gold 没有明确判断某个 risk：

```text
UNJUDGED
```

不进入 M1 分母，也不自动算 negative。某 risk 在 Existing Gold 中 support=0 时，最终报告：

```text
NOT_EVALUABLE_FROM_EXISTING_GOLD
```

不补标。

### M2 不再把 Recall@5 当官方85%

历史 offline benchmark：

```text
Evidence Recall@1/@3/@5 = 20% / 20% / 20%
```

继续保留为旧 diagnostic。赛题原文件没有指定 Top-K，因此最终 M2 使用：

```text
covered evaluable Existing-Gold Evidence Units
/
all evaluable Existing-Gold Evidence Units
```

Primary Gate `>=85%`；Recall@K 用来定位 Retriever / ranking 问题。

## 最新实测状态

### 1. 三个真实招股书案例已完成 offline E2E

| Case | Stock | Pages | Status | Conflicts | Re-checks | Traceability |
|---|---|---:|---|---:|---:|---:|
| `ipo_2024_02410` | `2410.HK` | 706 | completed | 6 | 3 | 1.0 |
| `ipo_2024_02460` | `2460.HK` | 579 | completed | 7 | 3 | 1.0 |
| `ipo_2024_01318` | `1318.HK` | 617 | completed | 7 | 3 | 1.0 |

三份 PDF 均通过 SHA-256、字节数和物理页数校验；结构化 workflow error 为 0；未读取 outcome label 或 2025 Blind y。

### 2. Role B 仍是第一质量 blocker

当前正式测得的仍是旧 10-case governed offline diagnostic：

```text
Risk Precision / Recall / F1      0% / 0% / 0%
Evidence Recall@1 / @3 / @5       20% / 20% / 20%
Physical-page correctness         100%
Real LLM cases                    0
```

下一步不再建新 Gold，而是：

```text
Existing Gold read-only coverage audit
→ real-LLM Development run
→ evaluate
→ failure taxonomy
→ code / LLM optimization on Development
→ Full Existing Development Gold benchmark
→ freeze
→ Existing Validation Gold one-shot
```

### 3. Market Intelligence 主体已实现

已实现 governed `MarketContext`、IPOHeatSkill、MarketRegimeSkill、bounded Market LLM、PIT/missingness 与 Trace/Final Supervisor handoff。最终只剩 final 3-case Market state / trace accounting。

### 4. LLM Final Supervisor / Product 已实现，real-provider acceptance 仍 open

三案例 offline traceability 均 1.0；reasoning log、case report、machine Gate-E1 evidence 已实现。最终仍需 3/3 real-provider accepted run。

### 5. Outcome / Model 生成器已实现，最终行情物化仍待完成

D 的 frozen PR-E/PR-F 校验、1D/5D/20D/60D 计算、指标复算、SHAP handoff 和
AI-vs-Offline 汇总已由 `scripts/build_v045_role_d_m5.py` 实现。最终运行仍需本地授权的
`hkshareeodprices.csv` 先生成 governed filtered EOD store，随后输出：

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

5D 为 primary business horizon；项目预定义 `significant_drop_5d = return_5d <= -0.10`。赛题没有给 5D 指标绝对及格线。

### 6. A submission tooling 已实现，但需接 metric-v2

A 已实现 readiness、Blind/provenance/determinism audit、artifact index、Runbook 和 fail-closed packager。最终 readiness 需要消费 Existing-Gold metric-v2 artifacts，并验证 `new_manual_annotations_added=false` / `existing_gold_modified=false`。

## 当前比赛 Gate

| Gate | Status |
|---|---|
| competition runtime contracts | PASS |
| Market Intelligence implementation + AI wiring | PASS |
| 3 real PDF offline E2E | PASS |
| Conflict / re-check / Trace / Human Review | PASS implementation |
| 3-case offline traceability | PASS = 1.0 |
| A readiness / audit / Runbook / packager | PASS implementation |
| Existing Expert Gold inventory | FROZEN |
| Metric Protocol v2 Existing-Gold-Only | **FROZEN** |
| Existing-Gold coverage audit / evaluator | **OPEN / P0** |
| B M1 real-LLM Existing-Gold Risk benchmark | **OPEN / P0** |
| B M2 real-LLM Existing-Gold Evidence Recall | **OPEN / P0** |
| D 1D/5D/20D/60D + 5D evaluation | **OPEN / P0** |
| E real-provider Final Supervisor | **OPEN / P1** |
| C final-matrix Market validation | **OPEN / P1** |
| Evidence bbox upstream grounding | P2 quality gap |
| Final audits / bundle / release freeze | **OPEN** |

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

冻结 completion reports、`reports/frozen/*` 和 research 文档继续保留历史事实，不因本轮比赛策略改写。

## 快速运行

```bash
pip install -e ".[dev,retrieval-research]"
python scripts/validate_competition_runtime.py
```

最终 `COMPETITION_READY` 只能在 metric-v2 与其余 hard Gate 被真实数据关闭之后使用。
