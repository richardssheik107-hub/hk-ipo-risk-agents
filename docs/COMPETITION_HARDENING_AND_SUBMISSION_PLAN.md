# 港股 IPO 风险预警赛题强化与提交总计划

> Status snapshot: **2026-08-25**  
> Current formal Gate: **PR-H — Streamlit Full E2E + 3–5 real 2024 IPO demo**  
> Target sequence: **v0.4.3 Baseline Freeze → Competition Beta → v0.4.5 COMPETITION_READY → Submission**

## 1. 当前基线与问题判断

v0.4 的工程闭环已经基本建立：

```text
Prospectus PDF
→ Document Intelligence
→ Evidence / Calculation / Verifier
→ Production Document-X
→ Market-X
→ Outcome / Canonical Dataset
→ Baseline / LightGBM / Explainability
→ Market Agent / Final Supervisor
→ Streamlit / Final Report
```

PR-A–PR-G 已 COMPLETE / FROZEN；PR-H 仍为 `PARTIAL / BLOCKED`。当前缺口不是重新开发 PR-A–PR-F，而是恢复原 frozen PR-F runtime/handoff、补足 3–5 个真实 2024 招股书并完成全通道 E2E 验收。

当前 5D 预测结果必须诚实保留：

```text
PR-F Full Production 2024
M   ROC-AUC 0.4246
P   ROC-AUC 0.5000
PM  ROC-AUC 0.4246
```

PM 与 M 完全预测等价，Production Document 100 维在 frozen LightGBM 下未获得 split/gain/SHAP 使用；Oracle `OM-M ROC-AUC = -0.0143`，95% paired-bootstrap `[-0.3171, 0.2917]`。这说明当前 **5D target + feature representation + sample + frozen model** 没有验证出稳定 Document 增量，不等于招股书信息本身无价值。

因此比赛强化不以“把 5D AUC 调漂亮”为唯一目标，而同时推进：

```text
Track A  Risk Intelligence / Auditability
Track B  Market Warning / Predictive Validation
Track C  Multi-Agent Collaboration / Product Experience
```

## 2. 五人固定角色

| Role | 固定负责人方向 | 最终责任 |
| --- | --- | --- |
| A — Tech Lead / Integration | 总计划、接口、GitHub、CI、Gate、release | 所有模块最终能合、能跑、能复现、能提交 |
| B — Document Intelligence | Risk / Retriever / Evidence / Calculation / Benchmark | 招股书风险读得准、Evidence 找得准 |
| C — Market Intelligence / Data | Market-X / IPO Heat / PIT / Outcome data | 市场数据真实、PIT-safe、具有金融含义 |
| D — Quant / ML | 1D/5D/20D/60D、模型、SHAP、Ablation、统计评估 | 所有效果结论有严谨实验证据 |
| E — Multi-Agent / Product | Final Supervisor、冲突仲裁、Evidence Viewer、Agent Trace、UI | Agent 真协同，评委能直观看懂结果 |

协作关系：

```text
B Document ───────┐
C Market ─────────┼→ D evaluation/model ─┐
B Evidence ───────┘                      ├→ E Supervisor/Product
C Market interpretation ────────────────┘

A 横跨全部 lane：interface / merge / CI / Gate / release
```

## 3. Phase 0 — v0.4.3 Baseline E2E Freeze（Day 1–3）

比赛强化正式开始前，先把当前 baseline 收干净。

### A

- 确认最新 `main`、PR/branch 和 frozen boundaries；
- 审核 PR-H governed runtime；
- 组织 3–5 case matrix；
- full CI、determinism、provenance、Blind checks；
- PR-H PASS 后生成 v0.4.3 freeze/release evidence。

### B

准备至少 3 个、目标 3–5 个真实 **2024 Validation IPO**：

```text
case_id / stock_code / prospectus
RiskItem / Evidence / Calculation
page / bbox / Verifier status
known limitation
```

### C

对 demo cases 验证：

```text
Market-X Core
HSI / turnover Extended where governed
PIT cutoff / provenance / missing reason
```

Industry return 继续保持 `INDUSTRY_MAPPING_PIT_BLOCKED`，禁止静态分类、proxy 或 neutral zero 强行补齐。

### D

恢复原 frozen PR-F runtime 或已经生成的 hash-bound sanitized handoff：

```text
selected case score
signed top SHAP drivers
run/model identity
SHA256SUMS
```

禁止 retrain / reconstruct / retune / score inversion。

### E

执行真实：

```text
PDF
→ Document
→ Evidence
→ Market
→ Model
→ Rule
→ Final Supervisor
→ 13-section Report
→ Streamlit
```

### Phase 0 PASS

```text
3–5 real 2024 cases
Document / Market / Model / Rule all governed
Evidence refs resolve
model hash matches frozen PR-F
repeat run deterministic
2025 Blind y accessed = false
→ v0.4.3 BASELINE E2E FREEZE
```

## 4. CH-0 — Competition Scope / Metrics Lock（Day 3–4）

A 主导，全员一次性冻结 Competition Scorecard。后续工作必须能对应一个指标、失败原因或核心 demo 能力。

### Document scorecard

```text
Precision / Recall / F1 by risk
Evidence Recall
Evidence Precision / page correctness
```

硬目标：

```text
关键风险要素抽取准确率 / core quality target >= 80%
关键 Evidence Recall                     >= 85%
```

### Predictive scorecard

```text
1D / 5D / 20D / 60D
M / P / PM / O / OM fair comparisons
ROC-AUC / PR-AUC / Brier
MAE / RMSE where applicable
bootstrap uncertainty
```

不设置“必须事后达到某个 AUC”的人为门槛。

### Multi-Agent / Auditability scorecard

```text
Agent / Tool / Evidence traceability = 100%
real conflict cases                  >= 3
unresolved uncertainty preserved     = 100%
```

## 5. CH-1 — Multi-Horizon Outcome & Predictive Diagnosis（Day 4–8）

**D 主导，C + A 协作，E 消费结果。**

### C：Outcome v2 数据层

在 frozen 5D 之外独立版本化：

```text
raw_return_1d / 20d / 60d
market_adjusted_return_1d / 5d / 20d / 60d
max_drawdown_20d / 60d
volatility_20d / 60d
severe_break_flag
```

session / suspension / missing-price 规则必须版本化并 fail closed；不得回写 PR-C frozen 5D。

### D：核心实验矩阵

```text
        1D    5D    20D    60D
M       ...   ...   ...    ...
P       ...   ...   ...    ...
P-Core  ...   ...   ...    ...
PM      ...   ...   ...    ...
O       ...   ...   ...    ...
OM      ...   ...   ...    ...
```

目的不是挑最好看的 horizon，而是回答：

1. Document 风险是否更适合 20D / 60D；
2. Market / IPO Sentiment 是否更适合 1D / 5D；
3. Production 与 Oracle 的差距究竟来自自动抽取，还是 target 本身信号弱。

### A：治理

```text
2020–2023 Development
2024 Validation
2025 Blind y forbidden
```

不允许针对不同 horizon 反复看 2024 后调参。

## 6. CH-2 — Document Benchmark + Targeted Hardening（Day 4–12）

**B 主导，D + E 协作。**

首先 benchmark，不先重写 Prompt。

### 正式风险集合

```text
cash_runway
continuous_loss
revenue_growth
customer_concentration
supplier_concentration
redemption_rights
material_litigation_compliance
precommercial_product
```

### 每类独立测量

```text
Precision
Recall
F1
Evidence Recall
Evidence Precision / page correctness
```

### 错误归因

每个失败至少归到：

```text
retrieval_miss
parser_or_table_error
semantic_agent_error
calculation_error
risk_rule_error
gold_uncertainty
```

只针对最差 2–3 类做最小增强：

```text
Retriever 问题   → BM25 + dense + section-aware / targeted retrieval
Table 问题       → table parser
语义理解问题     → constrained LLM semantic extraction / reranking
Calculation 问题 → deterministic Skill
规则问题         → versioned rule correction + regression tests
```

D 在每轮后检查 downstream signal 是否变化；E 制作真实 Before/After case。达标类别不无差别重写。

### CH-2 交付

```text
Document Benchmark Report
Risk × Metrics matrix
Error Attribution
Before / After cases
Targeted fix regression tests
```

## 7. CH-3 — Market Intelligence / IPO Context（Day 4–12）

**C 主导，D + E 协作。**

重点不是继续堆 raw features，而是形成四组可解释的 point-in-time 市场信号。

### IPO Heat

```text
recent IPO count
recent IPO break rate
recent IPO 1D / 5D performance
```

### Broad Market

```text
HSI trend / return
market volatility
HKEX turnover / activity
```

### Comparable IPO

只在 PIT-safe source 下构建：

```text
industry / comparable historical IPO context
similar issuance characteristics
prior IPO performance
```

### Liquidity / Activity

```text
market activity
issuance crowding
liquidity context
```

C 同时输出原始 provenance 和结构化解释，例如：

```text
Market Environment = WEAK
Reasons:
- recent IPO break rate elevated
- HSI 20D negative
- recent IPO performance weak
```

D 比较 Core vs Competition Market features；E 将其产品化。行业分类没有 PIT-safe 历史映射前，industry-return feature 继续 unavailable。

## 8. CH-4 — Multi-Agent Conflict Resolution + Trace（Day 10–14）

**E 主导，B + C + A 协作。**

目标从“多 Agent 平行输出”升级为“可观察的协作与复核”。

```text
Agent claim
→ Conflict Detector
→ Evidence re-check / targeted retrieval
→ deterministic Skill if needed
→ Verifier challenge
→ Final Supervisor arbitration
→ resolved / unresolved + uncertainty
```

统一 trace 至少记录：

```text
agent_name
input_task
plan_step
tool_or_skill_call
input_evidence_ids
calculation_ids
claim
verifier_status
conflict_id
resolution_action
final_status
```

必须准备 3–5 个真实 conflict cases，不以 mock 作为比赛主证据。

B 提供 Document Evidence；C 提供 Market Evidence；A 冻结 conflict/trace contract；E 完成 orchestration 与展示。

## 9. CH-5 — Competition Product / Evidence Viewer（Day 10–16）

**E 主导，全员提供受控数据。**

这一阶段才重新启动大规模 UI 打磨。最终产品优先固定五个工作区：

1. **Risk Command Center** — Overall Risk / Top Risks / Evidence Coverage / Market Environment / Model Signal；
2. **Risk Map** — Financial / Legal / Business / Market 的结构化风险视图；
3. **Evidence Viewer** — 左侧 PDF page + bbox highlight，右侧 Risk / Evidence / Calculation / Verifier / Agent；
4. **Market & Model** — IPO Heat / Broad Market / Comparable / score semantics / SHAP / multi-horizon；
5. **Agent Trace** — Parser → Retriever → Agent → Skill → Verifier → Market Agent → Conflict → Final Supervisor。

输入责任：

```text
B → Risk / Evidence / page / bbox / Calculation
C → Market interpretation / provenance
D → model score / SHAP / horizon result / uncertainty
A → runtime / provenance / trace contracts
E → product integration
```

## 10. Competition Beta Gate（Day 15–18）

A 组织一次完整 Beta Gate：

- full repository tests；
- Document benchmark v1；
- multi-horizon experiment v1；
- Market Intelligence v1；
- 3+ real conflict traces；
- 3–5 stable demo cases；
- Evidence Viewer / Agent Trace 可运行；
- no Blind leak / no fake market / no probability overclaim。

Beta 后原则上只允许修明确 bug、失败 benchmark、关键 demo usability，不再无边界增加功能。

## 11. CH-6 — Formal Competition Evaluation & Freeze（Day 18–21）

**A + D 主导，全员冻结各自 lane。**

### B freeze

```text
Document Benchmark
per-risk metrics
Evidence metrics
error attribution
```

### C freeze

```text
Competition Market feature set
PIT / missingness / provenance audit
```

### D freeze

```text
1D / 5D / 20D / 60D result matrix
ablation
SHAP
bootstrap uncertainty
error analysis
limitations
```

### E freeze

```text
Final Supervisor
real conflict cases
Evidence Viewer
Agent Trace
Competition UI
```

### A final Gate

```text
full tests
integration / golden / real-case regression
determinism / provenance
secret / path / raw-data leakage scan
reproducibility runbook
release manifest
```

PASS 后标记：

```text
v0.4.5 COMPETITION_READY
```

## 12. Final Submission Package

A 是 Submission Owner，提交目录目标：

```text
submission/
├── README
├── source
├── configs
├── demo
├── evaluation
├── reports
├── screenshots
└── runbook
```

### A

- 最终目录、安装与运行说明；
- source revision / release / reproducibility；
- 保证 `clone → install → run` 可复现。

### B

- Document benchmark；
- Risk / Evidence examples；
- targeted enhancement Before/After。

### C

- Market methodology；
- PIT 说明；
- Market feature / case examples。

### D

- model / multi-horizon tables；
- ablation / SHAP / error analysis / limitations。

### E

- final Streamlit；
- screenshots；
- 3–5 star demo cases；
- demo flow / presentation script。

## 13. Three Star Demo Patterns

最终至少选三类，不随机展示十几个 IPO：

### Case A — Document / Evidence

突出 `Risk → Evidence → Calculation → PDF page/bbox`，B + E 负责。

### Case B — Multi-Agent Conflict

突出 `conflict → re-check → Skill/Verifier → Supervisor`，E 主负责。

### Case C — Market / Prediction

突出 `Market Environment → model drivers / SHAP → multi-horizon`，C + D 负责。

A 保证三套 demo 均可重复运行。

## 14. Presentation Ownership

```text
A  architecture / governance / E2E / reproducibility
B  Document Intelligence / Evidence / benchmark
C  Market Intelligence / PIT / IPO Heat
D  model / multi-horizon / experiments / limitations
E  Multi-Agent / conflict / Supervisor / live demo
```

## 15. Non-goals / Stop Rules

禁止：

- 打开 2025 Blind y；
- 回写 PR-A–PR-F frozen contract；
- 看过 2024 后反转 score 或事后挑 direction；
- fake market / proxy / neutral-zero missing fill；
- 把 `uncalibrated_model_score` 称为真实概率；
- 无 benchmark 地整体重写 Retriever / LLM / Prompt / Agent；
- 为了比赛展示伪造 conflict、Evidence、Market 或模型结果；
- 只挑最漂亮 horizon / metric 代表系统整体能力。

每个优化方向最多进行有限轮、有明确假设的实验：

```text
hypothesis
→ governed experiment
→ accept result
→ route decision
```

不进入无限调参循环。
