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
→ LLM Final Supervisor
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

Existing-Gold coverage audit：

```text
evaluable Development cases = 79
evaluable Validation cases  = 19
primary positive risk units = 128
primary evidence units      = 217
```

Primary support：

```text
cash_burn_pressure         16
customer_concentration     32
redemption_rights          39
supplier_concentration     41
related_party_transaction   0 -> NOT_EVALUABLE_FROM_EXISTING_GOLD
```

从现在开始明确：

```text
不新增 M1/M2 人工 Gold
不修改旧专家答案
不补低 support risk family
不把未标注项当 negative
不人工重做 Evidence Group
```

系统效果提升只允许来自 Development 上的 Retriever/ranking、real LLM Prompt/structured extraction、normalization/reconciliation 与 Verifier。

### 当前正式指标解释

| Metric | Official requirement | Project primary definition |
|---|---:|---|
| M1 Risk extraction | >=80% | Existing-Gold positive Risk Unit Accuracy；project target >=85% |
| M2 Evidence recall | >=85% | Existing-Gold Evidence Coverage Recall；project target >=88% |
| M2 Recall@K | 官方未指定 | Recall@1/@3/@5/@10/@20 仅作诊断 |
| M3 Traceability | 100% | accounted Agent/Tool/Evidence-or-reason trace |
| M4 Explanation | “高” | 当前 final product rubric |
| M5 Post-listing | 1D/5D/20D/60D；5D更高权重 | 5D primary，`return_5d <= -10%` 为项目预先定义 |

`UNJUDGED` 不进入 M1 分母，也不自动算 negative；support=0 的 risk 报 `NOT_EVALUABLE_FROM_EXISTING_GOLD`。

## 最新实测状态

### 1. 三个真实招股书案例已完成 offline E2E

| Case | Stock | Pages | Status | Conflicts | Re-checks | Traceability |
|---|---|---:|---|---:|---:|---:|
| `ipo_2024_02410` | `2410.HK` | 706 | completed | 6 | 3 | 1.0 |
| `ipo_2024_02460` | `2460.HK` | 579 | completed | 7 | 3 | 1.0 |
| `ipo_2024_01318` | `1318.HK` | 617 | completed | 7 | 3 | 1.0 |

### 2. Existing-Gold audit / evaluator 已落地

manifest hash：

```text
fcd12d34fcc64853ed778d0026b1e2c943a863549cd1652c6ced7c6145214d1c
```

```text
new_manual_annotations_added = false
existing_gold_modified = false
blind_2025_outcome_accessed = false
```

### 3. 真实 LLM runtime 单案例已跑通

`ipo_2020_01167` / 1167.HK：

```text
provider = openai_responses
model = ark-code-latest
status = completed
Final Supervisor = available / accepted
deterministic fallback = false
scope guard = PASS
Validation accessed = false
2025 Blind accessed = false
```

当前 AI runtime：

```text
llm_timeout_seconds = 300
llm_max_retries = 0
```

### 4. Role-B fixed-10 自动化已进入实际执行阶段

Role B 现在不再让 Codex 开放式扫描仓库，而是使用 constrained Lunamax/Codex Runner：

```text
fixed-10
→ real-LLM
→ Existing-Gold evaluator
→ M1/M2/Recall@K
→ failure taxonomy
→ STOP
```

当前 Metric-v2 fixed-10 唯一权威来源：

```text
reports/v045_role_b/fixed10_development_subset.json
```

不存在时只生成一次：

```bash
python scripts/run_v045_role_b_iteration.py --subset-only
```

每轮：

```bash
python scripts/run_v045_role_b_iteration.py --iteration auto
```

2026-08-27 最近一次本地 Runner 已正确进入 preflight，并返回：

```text
EXECUTION_BLOCKED
blocker = IPO_RISK_PROSPECTUS_ROOT is not set
```

该 blocker 只需要在本地设置真实授权招股书根目录后继续，不需要改代码。

### 5. 历史 smoke 参考 10 家

以下 10 家用于旧 benchmark / 环境 smoke / 人工核对，**不覆盖**自动生成的 Metric-v2 fixed-10：

| case_id | stock | company |
|---|---|---|
| `ipo_2020_01167` | `1167.HK` | 加科思─B |
| `ipo_2020_01942` | `1942.HK` | MOG Holdings |
| `ipo_2020_01961` | `1961.HK` | 九尊数字互娱 |
| `ipo_2020_09600` | `9600.HK` | 新纽科技 |
| `ipo_2020_09633` | `9633.HK` | 农夫山泉 |
| `ipo_2021_09898` | `9898.HK` | 微博─SW |
| `ipo_2022_06698` | `6698.HK` | 星空华文 |
| `ipo_2022_09863` | `9863.HK` | 零跑汽车 |
| `ipo_2023_02451` | `2451.HK` | 绿源集团控股 |
| `ipo_2023_02517` | `2517.HK` | 锅圈 |

完整公司行业/上市日期、canonical Runner prompt、`IPO_RISK_PROSPECTUS_ROOT` blocker 恢复 prompt 已统一写入：

```text
docs/V045_CURRENT_EXECUTION_PLAN.md
docs/V045_ROLE_B_LUNAMAX_AUTOMATION_RUNBOOK.md
```

### 6. fixed-10 后续节奏

```text
current local env unblock
-> fixed-10 baseline
-> max 2-4 targeted Runner/Fixer rounds
-> larger Development checkpoint
-> ALL 79 Development
-> freeze
-> one-shot ALL 19 Validation
```

fixed-10 内部目标：

```text
M1 >=0.80
M2 >=0.85
```

它不是比赛正式 PASS。正式项目目标仍是 M1>=0.80（target 0.85）、M2>=0.85（target 0.88）。

### 7. 其余 hard Gate

- D：final 1D/5D/20D/60D + frozen 5D metrics；
- E：2410 / 2460 / 1318 final real-provider 3/3 accepted + M3/M4；
- C：final governed Market state / trace；
- A：latest-main CI、Blind/provenance/determinism、artifact index、security audit、submission bundle、release freeze。

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
| Existing-Gold coverage audit / evaluator | **PASS** |
| real-LLM single-case runtime smoke | **PASS** |
| fixed-10 Development iteration tooling | **PASS implementation** |
| constrained Lunamax/Codex operating procedure | **PASS operating procedure** |
| B fixed-10 baseline | **EXECUTION ACTIVE; local env unblock required** |
| B M1 real-LLM Existing-Gold benchmark | **OPEN / P0** |
| B M2 real-LLM Existing-Gold Evidence Recall | **OPEN / P0** |
| D 1D/5D/20D/60D + 5D evaluation | **OPEN / P0** |
| E final 3-case real-provider Final Supervisor | **OPEN / P1** |
| C final-matrix Market validation | **OPEN / P1** |
| Evidence bbox upstream grounding | P2 quality gap |
| Final audits / bundle / release freeze | **OPEN** |

详细状态见 `docs/V0.4_RELEASE_ACCEPTANCE.md`。

## 文档入口

- Metric contract：`docs/COMPETITION_METRIC_PROTOCOL.md`
- 当前 Gate：`docs/V0.4_RELEASE_ACCEPTANCE.md`
- **当前执行总计划**：`docs/V045_CURRENT_EXECUTION_PLAN.md`
- **Lunamax/Codex fixed-10 prompt**：`docs/V045_ROLE_B_LUNAMAX_AUTOMATION_RUNBOOK.md`
- fixed-10 workflow：`docs/V045_ROLE_B_FIXED10_ITERATION_WORKFLOW.md`
- 最终提交 Runbook：`docs/SUBMISSION_RUNBOOK.md`
- 剩余路线：`docs/ROADMAP.md`
- 五人执行：`docs/V04_FIVE_PERSON_EXECUTION_PLAN.md`
- 赛题映射：`docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`
- 数据与 split：`docs/COMPETITION_DATA_OVERVIEW.md`

## 快速运行

```bash
pip install -e ".[dev,retrieval-research]"
python scripts/validate_competition_runtime.py
python scripts/audit_v045_existing_gold.py --output-dir reports/v045_role_b
python scripts/run_v045_role_b_iteration.py --subset-only
python scripts/run_v045_role_b_iteration.py --iteration auto
```

最终 `COMPETITION_READY` 只能在 metric-v2 与其余 hard Gate 被真实数据关闭之后使用。
