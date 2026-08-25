# 港股 IPO 风险预警赛题强化与提交总计划

> Status snapshot: **2026-08-25**  
> Current formal Gate: **PR-H PARTIAL / BLOCKED**  
> Execution mode: **Competition Final Sprint — five parallel ownership lanes**

## 1. Competition objective

剩余开发不再围绕“探索还有什么可以做”，而围绕赛题硬要求逐项补齐：

```text
长文本 PDF 防幻觉解析
→ 标准财务 + 非标隐性风险
→ Financial / Legal / Market / Decision Agents
→ Retriever / Calculation / IPO Heat / comparable Skills
→ Agent conflict / re-check / verification
→ 基本面 + 市场情绪联合预警
→ 1D / 5D / 20D / 60D 真实表现验证
→ Evidence / page / bbox / trace / Human Review
→ runnable prototype + prediction table + reasoning logs + case reports
```

## 2. Required competition metrics

```text
关键风险要素抽取准确率      >= 80%
关键 Evidence Recall         >= 85%
Agent / Tool / Evidence trace = 100%
```

预测部分不承诺漂亮 AUC，但必须提供上市首日、5D、20D、60D 的真实表现验证，并重点支持 5D 显著下跌风险分析。

## 3. Current baseline

```text
PR-A–PR-G COMPLETE / FROZEN
PR-H       PARTIAL / BLOCKED
438 official cases
438 Production Document-X
438 Market-X Core
424 frozen 5D outcomes
354 Dev + 70 Val canonical
2025 Blind y accessed = NO
```

Frozen PR-F 2024 Full Production:

```text
M   ROC-AUC 0.4246
P   ROC-AUC 0.5000
PM  ROC-AUC 0.4246
```

该结果只作为辅助模型基线。剩余冲刺不投入大规模模型探索。

## 4. Five-person final ownership

### A — Integration / Release / Submission

负责：

```text
public contracts
GitHub / CI / merge
real E2E
3–5 case matrix
reproducibility
release manifest
submission package
```

### B — LLM Document Intelligence

负责：

```text
Legal LLM semantics
Business LLM semantics
redemption / litigation / related-party
core product / commercialization / pipeline
Disclosure Tone bounded analysis
Evidence grounding
Risk/Evidence benchmark
```

### C — Market Intelligence

负责：

```text
PIT-safe MarketContext
IPOHeatSkill
MarketRegimeSkill
optional ComparableIPOSkill
LLM Market interpretation
market provenance
```

### D — Outcome / Model / Evaluation

负责：

```text
frozen PR-F handoff recovery
1D / 5D / 20D / 60D outcome
final prediction table
AI-vs-Offline effect check
evaluation artifacts
```

### E — Supervisor / Multi-Agent / Product

负责：

```text
LLM Final Supervisor
Conflict / RecheckRequest / resolution
Agent Trace
Evidence Viewer
Human Review
final Streamlit
3–5 demo cases
```

## 5. LLM usage policy

LLM 被集中用在真正有增益的位置：

```text
Legal      complex clause semantics
Business   commercialization/core-product semantics
Market     interpretation of governed PIT facts
Supervisor synthesis / conflict / uncertainty / re-check
```

Deterministic code 继续负责：

```text
financial math
exact calculations
PIT guards
identity / schema / hash
feature materialization
model scoring
reproducibility
```

LLM 不得：invent Evidence、invent market facts、replace exact math、change frozen score、bypass Verifier。

## 6. Document Intelligence acceptance

B 必须让真实 case 走通：

```text
Evidence
→ LLM structured extraction
→ schema validation
→ Risk Builder
→ Verifier
```

优先正式风险：

```text
cash_runway
continuous_loss
customer_concentration
supplier_concentration
redemption_rights
material_litigation_compliance
related_party_transaction
precommercial_product
```

同时提供轻量 `Disclosure Tone / Obfuscation` Evidence-backed 输出。

最小 benchmark 至少报告：

```text
Precision / Recall / F1
Evidence Recall / Evidence Precision
```

## 7. Market Intelligence acceptance

C 必须把已治理事实转成可解释 Market Agent：

```text
HSI trend / volatility
HKEX turnover
recent IPO count
recent IPO break rate
recent IPO 1D / 5D performance
```

标准输出：

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

行业 return 在没有 PIT-safe temporal classification 前继续 unavailable。

## 8. Outcome / prediction acceptance

D 必须生成独立 versioned sidecar：

```text
return_1d
return_5d
return_20d
return_60d
```

建议同时：

```text
break_flag_1d
significant_drop_5d
drawdown_20d
drawdown_60d
```

Submission 至少包含：

```text
test_predictions.csv
multi_horizon_results.csv
evaluation_summary.json
ai_vs_offline_report.json
```

## 9. Multi-Agent collaboration acceptance

E 必须实现：

```text
Agent disagreement
→ Conflict
→ targeted re-retrieval
→ Skill / Agent rerun
→ Verifier challenge
→ Final Supervisor resolution
```

最终状态：

```text
resolved
partially_resolved
unresolved
```

不需要无限 autonomous loop；一次可控 targeted re-check 足够体现 Agentic 协作，同时保证可审计。

## 10. Trace / Explainability / Human Review

Agent Trace 必须至少记录：

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

Evidence Viewer：

```text
PDF page + bbox highlight
Risk
Evidence
LLM interpretation
Structured Fact
Calculation
Verifier
```

Human Review：

```text
Accept
Reject
Needs Follow-up
Reviewer Note
```

机器结果与人工结果分开存储。

## 11. Real-case strategy

最终稳定 3–5 个真实 IPO，不追求数量。

案例至少覆盖：

```text
Financial / Calculation case
Legal LLM semantic case
Business LLM semantic case
Market context case
Conflict / re-check case
```

同一 case 可以覆盖多个模式。

## 12. Explicitly deferred

```text
new model families
large hyperparameter search
broad P-Core / feature audit
large Retriever redesign
industry PIT research
broad new market datasets
paper-style ablation
story-only features
```

注意：1D/5D/20D/60D outcome 计算不是 exploratory research，而是赛题硬要求，因此必须完成。

## 13. Submission package

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

## 14. Final Gate

```text
real LLM Document semantics        PASS
Market Agent + Skills              PASS
LLM Final Supervisor               PASS
conflict / re-check                PASS
1D / 5D / 20D / 60D               PASS
Risk benchmark artifact            PASS
Evidence benchmark artifact        PASS
Traceability                       100%
Evidence Viewer                    PASS
Human Review                       PASS
>=3 stable real IPO cases          PASS
prediction table / logs / reports  PASS
full CI / real-case smoke          PASS
submission reproducible            PASS
```

未达标项必须显式记录 blocker，不能用 mock、fake market、fake model 或 UI hardcode 伪装完成。
