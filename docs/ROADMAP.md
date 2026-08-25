# Roadmap

> Status snapshot: **2026-08-25**  
> Execution strategy: **stop expanding scope → validate real cases → close metrics → package submission**

## 1. Current state

```text
v0.3 Document Intelligence          COMPLETE / FROZEN
PR-A–PR-G                           COMPLETE / FROZEN
v0.4.5 competition runtime          IMPLEMENTED / HARDENING
Historical PR-H formal freeze       PARTIAL / BLOCKED
Competition Final Sprint            ACTIVE
Target                              v0.4.5 COMPETITION_READY
```

开发重心已经从“继续加大模块”切换为 competition closure。Market Intelligence 正式 runtime wiring、LLM Final Supervisor、conflict detection、bounded targeted re-check、Agent Trace、Evidence Viewer 与 Human Review 都已经进入 `main`，不再列为待开发功能。

## 2. Competition hard requirements

赛题最终必须证明：

```text
1. 数百页招股书解析与非标风险抽取
2. LLM 防幻觉 / Evidence-grounded semantic reasoning
3. Financial / Legal / Market / Decision 多角色 Agent + Skill
4. Agent conflict → re-check → verification → resolution / explicit unresolved
5. 基本面 + 市场情绪联合预警
6. 上市首日 / 5D / 20D / 60D 真实表现验证
7. 可解释报告 + PDF Evidence + Agent trace + Human Review
8. runnable prototype + prediction table + reasoning logs + case reports
```

指标目标：

```text
关键风险要素抽取准确率       >= 80%
关键 Evidence Recall          >= 85%
Agent / Tool / Evidence trace = 100%
```

## 3. What is already closed

```text
[done] real remote LLM provider integration boundary
[done] Legal / Business LLM runtime path
[done] governed Market-X Core projection
[done] IPOHeatSkill / MarketRegimeSkill implementation
[done] MarketIntelligenceAgent formal AI runtime wiring
[done] bounded qualitative Market LLM interpretation path
[done] conflict detection
[done] targeted re-check budget and one-attempt contract
[done] LLM Final Supervisor implementation
[done] Agent / Tool / Evidence trace sidecar
[done] Evidence Viewer
[done] Human Review
[done] v0.4.5 competition Streamlit scenarios
```

PR #128 已证明 E-lane 真实受控路径可以产生 conflict / re-check / trace；其历史完成报告保持在 `V04_ROLE_E_COMPLETION_REPORT.md`。

## 4. Current hardening fix

2410.HK 的 v0.4.5 AI smoke 暴露：Core-only Market-X 在 Extended-only feature 完全缺席时，`MarketRegimeSkill` 会访问 `None.missing_reason`。

当前修复策略：

```text
feature object exists + unavailable → preserve governed missing_reason
feature object absent               → source_unavailable
feature available                   → consume governed numeric value
```

同类逻辑在 `IPOHeatSkill` 一并修复，并有 core-only regression tests。修复只改变缺失值处理，不改变 Market threshold、不填零、不构造 HSI/turnover/industry 值。

真实 2410.HK 仍需在更新后的 `main` 上重跑，才能把该案例从 partial acceptance 升为 pass。

## 5. Remaining closure lanes

### A — Integration / Release

```text
rerun 2410.HK after current fix
close >=3 stable real-case matrix
verify component diagnostics are clean or explicitly degraded
keep main CI green
freeze final runbook / release / submission package
```

### B — LLM Document Intelligence

```text
finish minimal real-case Legal / Business benchmark
measure Risk extraction and Evidence Recall
keep true semantic conflicts fail-closed
```

### C — Market Intelligence

```text
confirm Core-only graceful degradation
optionally materialize governed Extended readiness in local final runtime
validate Market LLM on final real-case matrix
keep industry return PIT_BLOCKED unless legitimate mapping exists
```

### D — Quant / Outcome / Evaluation

```text
return_1d
return_5d
return_20d
return_60d
prediction outputs
AI-vs-Offline effect check
submission evaluation artifacts
```

### E — Supervisor / Product hardening

```text
confirm real-provider LLM Final Supervisor on final case matrix
verify conflict / re-check UI and trace on >=3 cases
polish product presentation without changing backend truth
```

## 6. Frozen foundation

```text
Official universe                  438
Production Document-X             438 / 438, 100 dims
Market-X Core                     438 / 438, 30 positions
5D Outcome                        424 / 438
Canonical                         424 = 354 Dev + 70 Val
Oracle v2 strict                  96 = 77 Dev + 19 Val
HSI Extended readiness            438 / 438
HKEX turnover 20D readiness       438 / 438
industry return                     0 / 438, PIT_BLOCKED
2025 Blind y accessed             NO
```

## 7. Model policy

Frozen PR-F remains an auxiliary baseline:

```text
M   0.4246
P   0.5000
PM  0.4246
```

不做 broad model search、2024 retuning、score inversion，也不为了 UI 可用而重建一个“像 PR-F”的新模型。若原 frozen runtime/handoff 无法恢复，Model Channel 明确显示 unavailable。

## 8. Explicitly deferred

```text
new model families / hyperparameter search
large Retriever redesign
industry PIT research
broad new data acquisition
paper-style ablation
full 438-case LLM execution
story-only UI work without backend truth
```

1D/5D/20D/60D Outcome 计算本身不是 defer 项，因为它是赛题硬要求。

## 9. Final Gate

只有以下条件基本闭合后才允许标记 `COMPETITION_READY`：

```text
[ ] >=3 stable real IPO E2E demos
[ ] 2410.HK post-fix AI smoke passes or all remaining degradations are explained
[ ] real-provider Final Supervisor validated on final case matrix
[ ] 1D / 5D / 20D / 60D results generated
[ ] Risk extraction benchmark >= target or gap explicitly documented
[ ] Evidence Recall benchmark >= target or gap explicitly documented
[ ] Agent / Tool / Evidence trace measured at required level
[ ] prediction table + reasoning logs + case reports generated
[ ] Evidence Viewer / Human Review usable
[ ] full CI + determinism + provenance + blind audit pass
[ ] reproducible runbook + submission package complete
```

详细验收状态见 [`V0.4_RELEASE_ACCEPTANCE.md`](V0.4_RELEASE_ACCEPTANCE.md)。
