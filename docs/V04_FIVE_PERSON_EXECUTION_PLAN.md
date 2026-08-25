# v0.4 → Competition Submission 五人执行计划

> Status snapshot: **2026-08-25**  
> PR-A–PR-G: **COMPLETE / FROZEN**  
> PR-H: **PARTIAL / BLOCKED**  
> Current mode: **Competition Final Sprint**  
> End state: **v0.4.5 COMPETITION_READY + reproducible submission package**

本文件不按日期排任务，只回答：**每个人从现在到提交必须完成什么、依赖谁、交付什么、什么算完成。**

## 1. 协同原则

五个人并行推进，不串行排队：

```text
B  LLM Document Intelligence ─────┐
C  Market Intelligence ───────────┼→ E Final Supervisor / Product
D  Outcome / Model / Evaluation ──┘

A = public contracts + integration + CI + real-case matrix + release + submission
```

所有人从最新 `main` 建短分支；单 PR 单主题；A 高频合流。公共 Schema / workflow / service / container 修改由 A 审核。

## 2. A — Tech Lead / Integration / Release / Submission

### 目标

保证所有模块最终能合、能跑、能复现、能提交。

### A 必须冻结的公共 contracts

```text
RiskItem
Evidence
Calculation
AgentResult
MarketContext
ModelSignal
Conflict
RecheckRequest
SupervisorDecision
TraceEvent
HumanReview
```

所有跨模块对象必须能追踪：

```text
case_id
stock_code
listing_date
run_id
provider / model
prompt / policy / schema version
provenance / hash where applicable
```

### A 负责

- 最新 `main`、branch / PR / merge 策略；
- protected interface review；
- CI / regression / compile / validation；
- 3–5 个真实 IPO case matrix；
- `PDF → Final Report` E2E smoke；
- determinism / provenance / Blind audit；
- final release manifest / tag；
- submission tree、README、RUNBOOK、环境和复现说明。

### A 不负责

- 不替 B 重写 Legal/Business Agent；
- 不替 C 造 Market feature；
- 不替 D 调模型；
- 不替 E 在 UI 层修后端事实。

### A Done

```text
main green
>=3 real IPO stable E2E
all public contracts versioned
no fake unavailable channel
full submission package reproducible
Competition Release identity frozen
```

## 3. B — LLM Document Intelligence / Evidence / Benchmark

### 目标

让 LLM 真正提升复杂招股书语义理解，并保持 Evidence-grounded / verifier-governed。

### Legal Agent

优先完成：

```text
redemption_rights
material_litigation_compliance
related_party_transaction
```

标准链路：

```text
Retriever
→ bounded Evidence
→ LLM structured extraction
→ Evidence-scope validation
→ Risk Builder
→ Verifier
```

需要解析：

```text
right existence / effectiveness
post-listing survival
termination / restoration condition
materiality
actual litigation/compliance issue vs generic disclosure
```

### Business Agent

优先完成：

```text
core_product
pipeline_stage
commercialization_status
precommercial_product
product_revenue_semantics
```

重点解决未盈利生物科技/特专科技中：

```text
核心产品是谁
研发处于什么阶段
是否已商业化
收入是否来自产品销售
是否只是授权/合作收入
```

### Disclosure Tone

增加轻量 Evidence-bounded `Disclosure Tone / Obfuscation` 分析：

```text
tone_risk
hedging_language
obfuscation_signal
missing_quantification
supporting_evidence_ids
```

不做开放式文学评价，不允许无 Evidence 结论。

### B Benchmark

至少生成 submission-ready 最小 benchmark：

```text
Risk Precision / Recall / F1
Evidence Recall
Evidence Precision / page correctness
```

赛题目标：

```text
关键风险要素抽取准确率 >= 80%
关键 Evidence Recall    >= 85%
```

### B → E

交付：

```text
RiskItem
Evidence / page / bbox
LLM structured facts
Calculation refs
Verifier status
AI contribution metadata
```

### B Done

```text
real Legal cases pass
real Business cases pass
LLM citations all in scope
structured output schema-valid
benchmark artifact generated
top errors fixed with regression tests
```

## 4. C — Market Intelligence / Market Agent / Skills

### 目标

把现有 governed Market-X 从“数据字段”变成真正可解释的市场情绪 Agent，同时保持 PIT-safe。

### Governed facts

优先使用：

```text
HSI trend / return
market volatility
HKEX turnover / activity
recent IPO count
recent IPO break rate
recent IPO 1D / 5D performance
```

### Skills

至少实现：

```text
IPOHeatSkill
MarketRegimeSkill
```

如已有可靠数据再实现：

```text
ComparableIPOSkill
```

不能为了“同行估值”临时使用无 PIT / 无 provenance 数据。

### Market Agent

```text
Governed market facts
→ deterministic Skills
→ MarketContext
→ LLM interpretation
```

输出：

```text
market_regime
risk_level
ipo_heat
liquidity_condition
key_drivers
uncertainties
source_feature_ids
provenance
```

LLM 只能解释已有事实，不能生成行情值。

### C → E

交付：

```text
MarketContext
Market Environment
key drivers
source feature ids
PIT cutoff / provenance
missing reason
```

### C Done

```text
3–5 demo cases have governed MarketContext
IPO Heat / Market Regime reproducible
LLM interpretation grounded in feature ids
missing remains explicit
no future leakage / no fake industry proxy
```

## 5. D — Quant / Outcome / Model Runtime / Evaluation

### 目标

补齐赛题要求的真实表现验证，并生成最终可提交的效果证据；不再展开模型探索。

### Frozen PR-F runtime

优先恢复原 frozen runtime 或合法 hash-bound handoff：

```text
per-case score
score semantics
signed top SHAP
model/run identity
checksum
```

禁止：

```text
retrain
reconstruct
2024 retune
score inversion
```

若恢复失败：

```text
ModelSignal.status = unavailable
```

不阻断 Document / Market / Rule / Supervisor 主链。

### 1D / 5D / 20D / 60D Outcome

必须补齐：

```text
return_1d
return_5d
return_20d
return_60d
```

建议同时生成：

```text
break_flag_1d
significant_drop_5d
drawdown_20d
drawdown_60d
```

所有 horizon 必须统一 session / suspension / missing-price policy，并独立版本化，不改写 frozen PR-C 5D。

### Offline vs AI minimal effect check

在相同 selected real cases 上比较：

```text
Offline deterministic
vs
AI enhanced
```

至少记录：

```text
risk decisions resolved
semantic fields resolved
Extraction Failed
Needs Review
Evidence grounding validity
Legal semantic accuracy
Business semantic accuracy
useful conflict / re-check count
```

### Final evaluation artifacts

必须生成：

```text
test_predictions.csv
evaluation_summary.json
multi_horizon_results.csv
ai_vs_offline_report.json
```

`test_predictions.csv` 至少：

```text
case_id
stock_code
risk_score
risk_level
model_status
return_1d
return_5d
return_20d
return_60d
```

### D → E

交付：

```text
ModelSignal
SHAP if available
score semantics
outcome validation
uncertainty / limitations
```

### D Done

```text
1D/5D/20D/60D outcome reproducible
PR-F state resolved as available or explicit unavailable
AI-vs-Offline artifact exists
final prediction table exists
no Blind leakage
```

## 6. E — LLM Final Supervisor / Multi-Agent / Trace / Product

### 目标

让 Multi-Agent 真正发生可观察协作，并把所有能力变成投研人员可使用的产品。

### LLM Final Supervisor

输入只允许 governed：

```text
Financial Agent result
Legal Agent result
Business Agent result
MarketContext / Market Agent result
ModelSignal
Rule signal
Evidence / Calculation refs
Verifier status
```

输出：

```text
overall_risk
key_findings
conflicts
uncertainties
recheck_required
recheck_targets
final_explanation
```

### Conflict / Re-check

标准路径：

```text
Agent disagreement
→ Conflict
→ targeted re-retrieval
→ Skill / Agent rerun
→ Verifier challenge
→ Final Supervisor resolution
```

状态必须区分：

```text
resolved
partially_resolved
unresolved
```

不做无限 autonomous loop；一次可控 targeted re-check 为主。

### Agent Trace

每步至少记录：

```text
agent_name
task
input_evidence_ids
tool_or_skill
llm_provider / model
structured_output
calculation_ids
verifier_status
conflict_id
recheck_action
final_status
latency
```

赛题目标：`Agent / Tool / Evidence traceability = 100%`。

### Evidence Viewer

核心视图：

```text
左侧  PDF page + bbox highlight
右侧  Risk / Evidence / LLM interpretation / Structured Fact / Calculation / Verifier
```

### Human Review

最小可用：

```text
Accept
Reject
Needs Follow-up
Reviewer Note
```

机器结果和人工结果必须分开存储。

### Final product workspaces

只保留高价值工作区：

```text
Risk Command Center
Evidence + AI Analysis
Market & Model
Agent Trace
Human Review / Final Report
```

### E Done

```text
LLM Final Supervisor runs on real case
>=1 real controlled conflict/re-check trace
Agent trace complete
Evidence Viewer usable
Human Review usable
3–5 stable demo cases
final Streamlit uses governed outputs only
```

## 7. Cross-owner handoff contracts

```text
B → E  Risk + Evidence + LLM facts + Verifier
C → E  MarketContext + interpretation + provenance
D → E  ModelSignal + outcomes + evaluation
E → A  Supervisor + Trace + Product
A → all public contract / CI / release decisions
```

任何跨 owner 数据都必须通过正式 schema/sidecar，不通过临时 dict 或 UI hack。

## 8. Final submission package

A 统一最终结构：

```text
submission/
├── README.md
├── RUNBOOK.md
├── source/
├── configs/
├── demo/
├── evaluation/
│   ├── test_predictions.csv
│   ├── risk_benchmark.*
│   ├── evidence_benchmark.*
│   ├── multi_horizon_results.csv
│   └── ai_vs_offline_report.*
├── traces/
├── evidence/
├── reports/
└── screenshots/
```

## 9. Final acceptance matrix

```text
PDF long-document parsing                       PASS
standard + non-standard risk extraction         PASS
real LLM Legal / Business semantics             PASS
Market Agent + Skills                           PASS
LLM Final Supervisor                            PASS
conflict / re-check                             PASS
1D / 5D / 20D / 60D                            PASS
Risk benchmark artifact                         PASS
Evidence benchmark artifact                     PASS
Agent / Tool / Evidence trace                   100%
Evidence Viewer                                 PASS
Human Review                                    PASS
>=3 stable real IPO cases                       PASS
prediction table / reasoning logs / case report PASS
full CI / real-case smoke                       PASS
submission reproducible                         PASS
```

未达标项必须显式记录 blocker，不允许通过 mock / fake data / score rewrite 伪装 PASS。
