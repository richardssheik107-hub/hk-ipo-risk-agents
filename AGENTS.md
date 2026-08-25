# Codex 与团队开发规则

## 1. 当前项目目标

本项目构建一个**证据驱动、多智能体协同、可审计**的港股 IPO 招股书解析与上市后风险预警系统。

当前状态：

```text
v0.3 Document Intelligence          COMPLETE / FROZEN
PR-A–PR-G                           COMPLETE / FROZEN
PR-H Full E2E                       PARTIAL / BLOCKED — CURRENT GATE
v0.4.3 Baseline E2E Freeze          NOT CREATED
Competition Hardening               PLANNED
v0.4.5 COMPETITION_READY            TARGET
```

正式路线：

```text
PR-H completion
→ v0.4.3 Baseline E2E Freeze
→ CH-0 Scope / Metrics Lock
→ CH-1 Multi-Horizon
→ CH-2 Document Benchmark / Targeted Hardening
→ CH-3 Market Intelligence
→ CH-4 Multi-Agent Conflict / Trace
→ CH-5 Evidence Viewer / Competition Product
→ CH-6 Formal Evaluation / Freeze
→ v0.4.5 COMPETITION_READY
→ Submission
```

Retriever V3 等研究成果保持历史/冻结状态。只有 CH-2 direct benchmark + error attribution 证明 retrieval/semantic understanding 是瓶颈时，才重启 targeted Retriever/LLM research。

## 2. 开始任务前

代码任务至少阅读：

1. `docs/README.md`；
2. `docs/ROADMAP.md`；
3. `docs/PROJECT_SPEC.md`；
4. `docs/ARCHITECTURE.md`；
5. `docs/DATA_SCHEMA.md`；
6. 本 `AGENTS.md`；
7. 涉及比赛计划/分工时读 `docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md` 与 `docs/V04_FIVE_PERSON_EXECUTION_PLAN.md`；
8. 涉及数据/模型时读 `docs/research/V04_DATA_READINESS.md` 与对应 frozen completion/policy；
9. 检查实现、测试与当前 `main`，说明修改范围和公共接口影响。

历史 handoff / one-off readiness 文档不能覆盖 active docs、completion report 或 frozen manifest。

## 3. 架构规则

1. 保持模块化单体；
2. 不为比赛展示引入无必要微服务/Kafka/Redis/Neo4j/Kubernetes；
3. 业务逻辑不得堆在 `streamlit_app.py`；
4. UI 只能通过 `IPOAnalysisService` / 受控上层 service；
5. Agent 不直接操作前端；Parser 不依赖 Agent；Schema 不依赖具体实现；
6. Mock / unavailable / real implementation 必须可配置替换；
7. Competition UI 是 governed output consumer，不能创造 Risk/Evidence/Market/Model fact。

## 4. 受保护接口

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

跨边界修改必须说明影响、版本化语义并补 contract tests。禁止用临时 hack 绕过 service / registry / provenance。

## 5. Evidence / Agent / Skill 规则

- Parser 返回稳定 `DocumentChunk`；
- Agent 返回 `list[RiskItem]`；
- formal RiskItem 必须有真实 Evidence；
- exact numeric claim 必须有 deterministic Calculation；
- Calculation 记录 inputs / formula / result / unit / evidence IDs；
- 无法核验进入 `pending / needs_review`；
- Verifier / Supervisor 不创造原始 Evidence；
- LLM 做 semantic extraction/interpretation，不做 authoritative exact math；
- 新 Agent / Skill / Provider 必须有测试与受控注册。

## 6. 数据 / PIT / Blind 规则

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

- X 只使用 listing 前可得事实；
- 2025 y 不得用于 feature / threshold / rule / prompt / model / retrieval tuning；
- 2024 不得在看过结果后重新当 tuning set；
- AUC `< 0.5` 不授权事后反转 score direction；
- missing 必须显式，不得 fake proxy / neutral zero；
- provenance / source / feature / model / policy version 必须可追踪；
- 未校准 score 只能称 `uncalibrated_model_score` / score，不得称真实概率。

## 7. Frozen boundary

PR-A–PR-G 的 frozen contracts / manifests 不因比赛优化而原地重写。

Competition additions 使用新 version / sidecar：

```text
CH-1 new outcome horizons
CH-2 benchmark / optional P-Core
CH-3 Competition Market features
CH-4 trace / conflict
CH-5 human-review / presentation sidecars
```

需要改变 frozen boundary 时必须显式提出新 Gate，而不是 silently overwrite。

## 8. 当前 PR-H 规则

PR-H 当前 formal blockers：

```text
original frozen PR-F runtime or pre-existing hash-bound handoff missing
formal governed real 2024 prospectus count < 3
3–5 all-channel case matrix not executed
```

禁止为了 PR-H：

- retrain/reconstruct PR-F；
- 根据 2024 重调模型；
- 提交 target labels / Blind y / raw licensed data 到 product handoff；
- 用 mock Market/Model 伪装正式 available。

PR-H PASS 才能创建 v0.4.3 baseline freeze。

## 9. Competition Experiment 规则

每个实验必须写清：

```text
hypothesis
input/version
Development protocol
Validation protocol
metrics
result
route decision
```

不允许无限调参。CH-1/2/3 的目的先是定位 signal loss：

```text
Document extraction quality
Document representation
horizon alignment
Market/IPO context
model family
```

只有 evidence 指向具体瓶颈时才做 targeted enhancement。

## 10. CH-2 Document Benchmark 规则

核心 formal risks 至少逐类报告：

```text
Precision
Recall
F1
Evidence Recall
Evidence Precision / page correctness
```

Error attribution 统一为：

```text
retrieval_miss
parser_or_table_error
semantic_agent_error
calculation_error
risk_rule_error
gold_uncertainty
```

只优先修最差 2–3 类；达标类别不无差别重写。

## 11. CH-3 Market 规则

Competition Market 优先 PIT-safe：

```text
recent IPO count
recent IPO break rate
recent IPO 1D/5D performance
HSI
HKEX turnover/activity
PIT-safe comparable context
```

Current industry return remains PIT-blocked until historical company classification mapping is valid. HSCI price history alone does not solve classification PIT.

## 12. CH-4 / CH-5 产品规则

Conflict path：

```text
Agent claim
→ Conflict Detector
→ Evidence re-check / targeted retrieval
→ Skill
→ Verifier challenge
→ Final Supervisor arbitration
```

Unresolved conflict must remain unresolved + uncertainty.

Competition UI target workspaces：

```text
Risk Command Center
Risk Map
Evidence Viewer
Market & Model
Agent Trace
```

Evidence Viewer / Agent Trace 不改变 source identity，不通过 UI 修正后端事实。

## 13. 代码质量与测试

- 类型标注；
- 公共函数简短 docstring；
- 明确异常处理，不宽泛吞错；
- 不在 import 时执行耗时逻辑；
- 不删除有效测试、不弱化断言迁就错误；
- 新功能必须补 regression / contract tests。

完整环境：

```bash
pip install -e '.[dev,retrieval-research]'
pytest -q
python scripts/validate_project.py
```

CI 绿不等于用户本地资产存在；runtime asset availability 必须单独验证。

## 14. Git / 协作规则

1. 不直接把未经测试的开发提交推到 `main`；
2. 从最新 `main` 建短分支，单 PR 单主题；
3. PR body 写 scope、tests、governance、remaining blockers；
4. A / integration owner 每 2–3 天做一次合流 checkpoint；
5. 不提交大型 PDF、licensed raw data、model bulk、cache、credential、local absolute path；
6. push / PR / merge 仅在明确授权时执行；
7. 临时 handoff 优先放 PR/issue/comment，不再新增长期 `HANDOFF_FINAL` / `PREP_V2` 文档。

## 15. 当前五人优先级

```text
A  PR-H integration / Gate / v0.4.3 / later release & submission
B  real-case Evidence QA → CH-2 Document Benchmark
C  PR-H Market QA → CH-1 outcome data + CH-3 Market Intelligence
D  frozen PR-F handoff → feature/multi-horizon/model diagnosis
E  PR-H E2E → CH-4 conflict + CH-5 Evidence Viewer / Competition UI
```

完整排期以 `docs/V04_FIVE_PERSON_EXECUTION_PLAN.md` 为准。
