# Codex 与团队开发规则

## 1. 当前项目目标

本项目构建一个**证据驱动、多智能体协同、可审计**的港股 IPO 招股书解析与上市后风险预警系统。

当前进入 **5-day competition submission sprint**：

```text
PR-A–PR-G                           COMPLETE / FROZEN
PR-H                               PARTIAL / BLOCKED
Competition submission sprint       ACTIVE
Target                               v0.4.5 COMPETITION_READY
```

当前路线不再按 3 周探索计划推进，而是：

```text
Day 1  real LLM Document Intelligence
Day 2  LLM Market interpretation + LLM Final Supervisor + one re-check
Day 3  3–5 real cases + targeted fixes + minimal Offline-vs-AI check
Day 4  Evidence / AI Analysis / Agent Trace product integration
Day 5  regression + freeze + submission
```

## 2. 开始任务前

代码任务至少阅读：

1. `docs/README.md`；
2. `docs/ROADMAP.md`；
3. `docs/PROJECT_SPEC.md`；
4. `docs/ARCHITECTURE.md`；
5. `docs/DATA_SCHEMA.md`；
6. 本 `AGENTS.md`；
7. `docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`；
8. `docs/V04_FIVE_PERSON_EXECUTION_PLAN.md`。

如涉及 frozen data/model，再读对应 completion / manifest / research contract。

## 3. Sprint 优先级

任何新任务必须直接满足至少一项：

```text
competition requirement
real E2E blocker
Legal/Business LLM semantic quality
Market LLM interpretation
Final Supervisor / conflict / re-check
Evidence / Agent trace visibility
selected real-case stability
submission reproducibility
```

以下工作默认 defer：

```text
full multi-horizon research
broad feature audit / P-Core
new model family / tuning
large Retriever redesign
industry PIT research
new broad market data acquisition
full benchmark construction
story-only / presentation-only features
```

## 4. 架构规则

- 保持模块化单体；
- UI 只能消费受控 service 输出，不能创造事实；
- Parser 不依赖 Agent；Schema 不依赖实现；
- Mock / unavailable / real implementation 必须显式可区分；
- 不为比赛临时引入无必要微服务/Kafka/Redis/Neo4j/Kubernetes。

Protected interfaces：

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

跨边界修改必须补 contract/regression test。

## 5. LLM 规则

### LLM 应做

```text
Legal complex clause semantics
Business commercialization/core-product semantics
Market fact interpretation
Final Supervisor synthesis/conflict/uncertainty/re-check request
```

### LLM 不得做

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

## 6. Evidence / Calculation / Verifier

- formal RiskItem 必须有真实 Evidence；
- exact numeric claim 必须有 deterministic Calculation；
- Calculation 记录 inputs / formula / result / unit / evidence IDs；
- 无法核验进入 `pending / needs_review`；
- Verifier / Supervisor 不创造原始 Evidence；
- Evidence page / bbox / identity 不得由 UI 修补。

## 7. Data / PIT / Blind

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

- X 只使用 listing 前可得事实；
- 2025 y 禁止访问；
- 2024 不得重新当 tuning set；
- missing 不得 fake-fill；
- provenance / source / policy / model version 必须可追踪；
- weak AUC 不授权 score inversion。

## 8. Frozen boundary

PR-A–PR-G frozen contracts / manifests 不因五天冲刺而原地重写。新增功能应作为受控 runtime/sidecar 增量。

PR-H 当前 formal blocker 仍包括 frozen PR-F per-case handoff 与 all-channel real-case matrix。D 优先恢复，但不得 retrain/reconstruct 仅为 UI 解阻。

若 handoff 仍不可得：

```text
formal PR-H stays BLOCKED
Model Channel = unavailable
Document + Market + Rule + LLM Supervisor continue
```

## 9. Five-day product contract

最终真实路径目标：

```text
PDF
→ Evidence
→ Financial / Legal / Business
→ LLM semantic extraction where needed
→ Verifier
→ governed Market facts
→ LLM Market interpretation
→ Model if frozen runtime available + Rule
→ LLM Final Supervisor
→ one controlled re-check if needed
→ Report / Streamlit / Agent Trace
```

不实现 open-ended autonomous loop；一轮可控 re-check 足够。

## 10. Minimal effect check

只在 selected 3–5 cases 上比较：

```text
Offline deterministic
vs
AI enhanced
```

记录：

```text
semantic fields resolved
risk decisions resolved
needs_review / extraction_failed
Evidence grounding validity
structured-output validity
useful conflict/re-check count
```

不要扩展成新的大规模研究项目。

## 11. 测试与质量

完整环境：

```bash
pip install -e '.[dev,retrieval-research]'
pytest -q
python scripts/validate_project.py
```

提交前还需 selected real-case smoke。不得删除有效测试、弱化断言、伪造通过结果。

## 12. Git / 协作

五天内改为高频小 PR：

```text
morning   confirm one deliverable per owner
afternoon short branch / small PR
evening   A integration + CI + real-case smoke
```

- main 每晚保持可运行；
- 单 PR 单主题；
- 不保留长寿命实验分支；
- 不提交大型 PDF、licensed raw data、model bulk、cache、credential、absolute path；
- 不新增长篇 exploration / handoff 文档；
- 失败方向当天止损。

## 13. 当前五人优先级

```text
A  integration / CI / release / submission
B  Legal + Business real LLM semantics / Evidence / Verifier
C  governed Market facts + LLM Market interpretation
D  frozen PR-F handoff + minimal Offline-vs-AI effect check
E  LLM Final Supervisor + conflict/re-check + Evidence/AI Trace + UI
```

完整排期以 `docs/V04_FIVE_PERSON_EXECUTION_PLAN.md` 为准。
