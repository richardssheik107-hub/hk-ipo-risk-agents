# Roadmap

> Status snapshot: **2026-08-25**  
> Execution strategy: **return to the competition task → five parallel ownership lanes → continuous integration → competition release**

## 1. Current state

```text
v0.3 Document Intelligence          COMPLETE / FROZEN
PR-A–PR-G                           COMPLETE / FROZEN
PR-H Full E2E                       PARTIAL / BLOCKED
Competition Final Sprint            ACTIVE
Target                              v0.4.5 COMPETITION_READY
```

当前不再按日期推进，也不再优先做大规模研究探索。五个人各自拥有固定责任线并行开发，A 持续合流。

## 2. Competition hard requirements

赛题最终必须证明：

```text
1. 数百页招股书解析与非标风险抽取
2. LLM 防幻觉 / Evidence-grounded semantic reasoning
3. Financial / Legal / Market / Decision 多角色 Agent + Skill
4. Agent conflict → re-check → verification → resolution
5. 基本面 + 市场情绪联合预警
6. 上市首日 / 5D / 20D / 60D 真实表现验证
7. 可解释报告 + PDF Evidence + Agent trace + Human Review
8. runnable prototype + prediction table + reasoning logs + case reports
```

指标目标：

```text
关键风险要素抽取准确率      >= 80%
关键 Evidence Recall         >= 85%
Agent / Tool / Evidence trace = 100%
```

## 3. Five parallel lanes

### A — Integration / Release

```text
public contracts
GitHub / PR / CI
E2E integration
3–5 real-case matrix
reproducibility
release / submission
```

### B — LLM Document Intelligence

```text
Legal semantics
Business semantics
related-party / redemption / litigation
core product / commercialization / pipeline
Disclosure Tone bounded analysis
Evidence grounding
minimal Document benchmark
```

### C — Market Intelligence

```text
governed PIT facts
IPO Heat / Market Regime Skills
MarketContext
LLM Market interpretation
optional comparable context
market provenance
```

### D — Quant / Outcome / Evaluation

```text
frozen PR-F runtime recovery
1D / 5D / 20D / 60D outcomes
prediction results
AI-vs-Offline effect check
submission evaluation artifacts
```

### E — Supervisor / Multi-Agent / Product

```text
LLM Final Supervisor
Conflict / RecheckRequest / resolution
Agent Trace
Evidence Viewer
Human Review
final Streamlit
3–5 stable demos
```

## 4. Current frozen foundation

```text
Official universe                  438
Production Document-X             438 / 438, 100 dims
Market-X Core                     438 / 438, 30 positions
5D Outcome                        424 / 438
Canonical                         424 = 354 Dev + 70 Val
Oracle v2 strict                  96 = 77 Dev + 19 Val
HSI Extended                      438 / 438
HKEX turnover 20D                 438 / 438
industry return                     0 / 438, PIT_BLOCKED
2025 Blind y accessed             NO
```

## 5. LLM-first competition path

```text
PDF
→ Retriever / Evidence
→ Financial Agent + deterministic math
→ Legal Agent + LLM semantics
→ Business Agent + LLM semantics
→ Verifier
→ governed Market facts / Skills
→ LLM Market Agent
→ Model if frozen runtime available + Rule
→ LLM Final Supervisor
→ conflict → targeted re-check → resolved / unresolved
→ Report / Evidence Viewer / Trace / Human Review
```

## 6. Model policy

Frozen PR-F remains an auxiliary baseline:

```text
M   0.4246
P   0.5000
PM  0.4246
```

本冲刺不做 broad model search、2024 retuning 或 score inversion。D 只恢复原 frozen runtime/handoff；若无法恢复，Model Channel 诚实显示 unavailable。

## 7. What is explicitly deferred

```text
new model families / hyperparameter search
broad P-Core / feature audit
large Retriever redesign
full multi-horizon modeling research
industry PIT research
broad new data acquisition
paper-style ablation
story-only UI work
```

注意：1D/5D/20D/60D **Outcome 计算本身不是 defer 项**，因为它是赛题明确要求。

## 8. Final Gate

Competition release 只有在以下条件基本满足后才创建：

```text
real LLM provider path active
Legal / Business semantic reasoning grounded
Market Agent grounded in PIT facts
LLM Final Supervisor active
controlled conflict / re-check exists
1D / 5D / 20D / 60D results generated
Risk / Evidence benchmark produced
Agent / Tool / Evidence trace complete
>=3 stable real IPO demos
Evidence Viewer / Human Review usable
prediction table + reasoning logs + reports generated
full CI + real-case smoke pass
submission package reproducible
```

详细 ownership 见 [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md)。
