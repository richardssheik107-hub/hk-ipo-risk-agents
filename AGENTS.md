# Codex 与团队开发规则

## 1. 当前执行模式

本项目当前进入 **Competition Final Sprint**。不再按日期拆分，也不继续大规模探索；五个人各自拥有固定工作流并行推进，A 负责公共接口、持续集成、CI、release 和 submission。

```text
PR-A–PR-G                    COMPLETE / FROZEN
PR-H                         PARTIAL / BLOCKED
Competition Final Sprint     ACTIVE
Target                       v0.4.5 COMPETITION_READY
```

最终目标必须直接对应赛题：

```text
PDF 招股书解析
→ 非标风险抽取
→ 多角色 Agent + Skill
→ 基本面 + 市场情绪
→ conflict / re-check / verification
→ 1D / 5D / 20D / 60D 验证
→ Evidence / Trace / Human Review
→ runnable prototype + submission package
```

## 2. 开始任务前

至少阅读：

1. `docs/README.md`
2. `docs/ROADMAP.md`
3. `docs/PROJECT_SPEC.md`
4. `docs/ARCHITECTURE.md`
5. `docs/DATA_SCHEMA.md`
6. 本 `AGENTS.md`
7. `docs/V04_FIVE_PERSON_EXECUTION_PLAN.md`
8. `docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`

涉及 frozen data/model 时再读对应 completion / manifest / research contract。

## 3. Five-person ownership

### A — Tech Lead / Integration

Owns:

```text
public contracts
GitHub / branch / PR / CI
E2E integration
real-case matrix
release / submission
```

A 不替 B/C/D/E 重做领域算法。公共 schema / workflow / container / service 变更必须经 A 审核。

### B — LLM Document Intelligence

Owns:

```text
Legal semantic extraction
Business semantic extraction
redemption / litigation / related-party risk
core product / pipeline / commercialization
Disclosure Tone bounded analysis
Evidence grounding
minimal Document benchmark
```

### C — Market Intelligence

Owns:

```text
governed PIT market facts
IPOHeatSkill
MarketRegimeSkill
optional ComparableIPOSkill
MarketContext
LLM market interpretation
PIT provenance
```

### D — Quant / Outcome / Evaluation

Owns:

```text
frozen PR-F runtime recovery
1D / 5D / 20D / 60D outcomes
prediction table
Offline-vs-AI minimal effect check
submission evaluation artifacts
```

禁止 broad model search / 2024 retuning / score inversion。

### E — LLM Final Supervisor / Product

Owns:

```text
LLM Final Supervisor
Conflict / RecheckRequest / resolution
Agent Trace
Evidence Viewer
Human Review
final Streamlit
3–5 stable demo cases
```

## 4. Sprint priority rule

任何任务必须直接满足至少一项：

```text
赛题硬要求
real E2E blocker
LLM semantic quality
Market Agent functionality
Final Supervisor collaboration
1D/5D/20D/60D verification
Risk/Evidence metric requirement
Traceability requirement
Human Review requirement
submission reproducibility
```

默认 defer：

```text
new model families
large hyperparameter search
broad P-Core / feature audit
large Retriever redesign
industry PIT research
broad new data acquisition
paper-style ablation
story-only / cosmetic work
```

## 5. Architecture rules

- 保持模块化单体；
- UI 只能消费 governed service 输出；
- Parser 不依赖 Agent；Schema 不依赖具体实现；
- mock / unavailable / real implementation 必须显式区分；
- 不为比赛临时引入 Kafka/Redis/Neo4j/Kubernetes 等无必要基础设施。

Protected interfaces:

```text
src/ipo_risk/schemas/
src/ipo_risk/agents/base.py
src/ipo_risk/parsers/base.py
src/ipo_risk/retrieval/base.py
src/ipo_risk/predictors/base.py
src/ipo_risk/providers/
src/ipo_risk/workflows/state.py
src/ipo_risk/services/analysis_service.py
src/ipo_risk/core/container.py
src/ipo_risk/domain/risk_codes.py
```

跨边界修改必须补 contract/regression tests。

## 6. LLM usage contract

### LLM should do

```text
Legal complex clause semantics
Business commercialization/core-product semantics
Disclosure tone bounded interpretation
Market interpretation of governed facts
Final Supervisor synthesis / conflict / uncertainty / re-check request
```

### LLM must not do

```text
invent Evidence
invent market facts
cite out-of-scope Evidence IDs
replace exact financial calculations
change frozen model score
call uncalibrated score a probability
bypass Verifier
```

LLM structured output 必须 schema validate；provider failure 必须 honest degradation。

## 7. Evidence / Calculation / Verifier

- formal RiskItem 必须有真实 Evidence；
- exact numeric claim 必须有 deterministic Calculation；
- Calculation 记录 inputs / formula / result / unit / evidence IDs；
- 无法核验进入 `pending / needs_review`；
- Verifier / Supervisor 不创造原始 Evidence；
- page / bbox / Evidence identity 不得由 UI 修补。

## 8. Market / PIT / Blind

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

- target IPO X 只能使用 listing 前可得事实；
- 2025 y 禁止访问；
- 2024 不得重新当 tuning set；
- missing 不得 fake-fill；
- provenance / source / policy / model version 必须可追踪；
- industry return 继续 PIT-blocked，除非有历史有效映射。

## 9. Frozen boundary

PR-A–PR-G frozen contracts / manifests 不因冲刺而原地重写。PR-H 的 frozen PR-F runtime/handoff 缺失仍是 formal blocker。

若无法恢复：

```text
formal PR-H stays BLOCKED
Model Channel = unavailable
Document + Market + Rule + LLM Supervisor continue
```

禁止 retrain/reconstruct 仅为 UI 解阻。

## 10. Competition product contract

```text
PDF
→ Evidence
→ Financial / Legal / Business
→ LLM semantics where needed
→ Calculation / Verifier
→ governed Market facts / Skills
→ LLM Market interpretation
→ Model if frozen runtime available + Rule
→ LLM Final Supervisor
→ conflict → targeted re-check
→ resolved / partially_resolved / unresolved
→ Report / Agent Trace / Human Review
```

不实现无限 autonomous loop；可控 targeted re-check 足够。

## 11. Required evaluation artifacts

必须产出：

```text
risk benchmark
Evidence benchmark
1D / 5D / 20D / 60D outcome table
prediction_results.csv
AI_vs_offline comparison
agent_reasoning_logs
3–5 case reports
```

目标：

```text
关键风险要素抽取准确率      >= 80%
关键 Evidence Recall         >= 85%
Agent / Tool / Evidence trace = 100%
```

## 12. Git / Codex collaboration

- 每个人从最新 `main` 建短分支；
- 单 PR 单主题；
- A 高频合流，main 始终可运行；
- Codex 任务必须写清目标、允许修改范围、禁止修改范围、输入/输出 contract、tests 和 acceptance；
- 不保留长寿命实验分支；
- 不提交 PDF bulk、licensed raw data、model bulk、cache、credential、absolute path；
- 不新增长篇探索性 handoff 文档。

## 13. Final ownership summary

```text
A  integration / CI / release / submission
B  LLM Document Intelligence / Evidence / benchmark
C  Market Intelligence / Skills / LLM interpretation
D  Outcome / PR-F / evaluation / prediction table
E  LLM Supervisor / conflict / trace / Evidence Viewer / Human Review / UI
```

完整计划以 `docs/V04_FIVE_PERSON_EXECUTION_PLAN.md` 为准。
