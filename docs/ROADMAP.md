# Roadmap

> Status snapshot: **2026-08-23**  
> Current formal Gate: **PR-E — Baseline + Oracle Diagnostic**  
> Strategy: **End-to-End Closed Loop First, Competition Hardening Second**

## 1. Current state

| Phase | Status | Frozen / active result |
| --- | --- | --- |
| v0.3 Document Intelligence | COMPLETE / FROZEN | real PDF → Evidence → Agents → Verifier → Supervisor |
| PR-A Document materialization | COMPLETE / FROZEN | 438/438 Production Document-X, 100 dims |
| PR-B Market-X Core | COMPLETE / FROZEN | 438/438, 30 positions, PIT audited |
| PR-C 5D Outcome | COMPLETE / FROZEN | 424 available / 14 explicit unavailable |
| PR-D Canonical Dataset | COMPLETE / FROZEN | 424 = 354 Development + 70 Validation |
| Oracle v2 | COMPLETE / FROZEN | 98 materialized / 96 strict usable = 77 Dev + 19 Val |
| PR-E Baseline + Oracle Diagnostic | **CURRENT FORMAL GATE** | formal measured run not frozen yet |
| PR-F LightGBM + Explainability | WAITING | starts after PR-E |
| PR-G Market Agent + Final Supervisor | WAITING | starts after PR-F |
| PR-H Streamlit Full E2E | WAITING | starts after PR-G |
| CH-0..CH-6 Competition Hardening | PLANNED | starts after PR-H baseline E2E |

## 2. Current measured data anchors

```text
Official 2020–2024 universe           438
Production Document-X                 438 / 438
Production feature width              100
Market-X Core                         438 / 438
Market Core width                      30
5D outcome available                  424 / 438
5D outcome unavailable                 14
  missing_base_price                   12
  no_eligible_session                   2
Canonical model-ready                 424
Development / Validation              354 / 70
Oracle v1                             historical immutable: 60 materialized
Oracle v2                             98 materialized / 96 strict usable
Oracle v2 Development / Validation     77 / 19
2025 Blind y accessed                 NO
```

Market-X Extended 仍缺 governed HSI、authoritative industry benchmark mapping/history、HK total-market turnover；这些是 Extended limitations，不重开 PR-B，也不阻塞当前 Core baseline。

## 3. Current PR-E objective

PR-E 正式比较：

```text
M   Market only
P   Production Document only
O   Oracle Document only
PM  Market + Production
OM  Market + Oracle
```

必须保证 Production / Oracle 比较使用相同 cohort、split、target、preprocessing、model family。

核心解释量：

```text
Production Increment     = PM - M
Document Signal Ceiling  = OM - M
Pipeline Gap              = OM - PM
```

Development evaluation 必须 time-aware：

```text
train 2020       → evaluate 2021
train 2020–2021  → evaluate 2022
train 2020–2022  → evaluate 2023
```

正式 Validation：

```text
fit 2020–2023 Development
→ evaluate untouched 2024 Validation
```

不得使用 random/shuffled time-mixing CV，不得访问 2025 Blind y。

## 4. Strict formal sequence

```text
PR-A  COMPLETE / FROZEN
→ PR-B COMPLETE / FROZEN
→ PR-C COMPLETE / FROZEN
→ PR-D COMPLETE / FROZEN
→ PR-E CURRENT
→ PR-F LightGBM + Explainability
→ PR-G Market Agent + Final Supervisor
→ PR-H Streamlit Full E2E + 3–5 real IPO demo
→ v0.4.3 Baseline E2E Freeze
→ CH-0 Competition Scope Lock
→ CH-1 Multi-horizon outcomes
→ CH-2 Competition Document Risk Hardening
→ CH-3 Market Sentiment + Competition Skills
→ CH-4 Conflict Resolution + Traceability
→ CH-5 Evidence Screenshot + Human Review
→ CH-6 Competition Evaluation + Submission Freeze
→ v0.4.5 COMPETITION_READY
```

## 5. What is intentionally not reopened now

在 PR-E diagnostic / frozen competition metrics 证明存在真实瓶颈前，不把以下工作重新设为主线：

- Retriever tuning；
- LLM Reranker；
- Fine-tuning / LoRA；
- 大规模 Prompt 重写；
- 新专业 Agent；
- 深度模型市场预测；
- 无边界 UI 重构。

如果 `OM >> PM`，才有证据表明 Document Pipeline 存在明显信息缺口；如果 `OM ≈ PM`，优先推进 model / productization，而不是无目标地重做 Retriever / Agent。

## 6. Version targets

```text
v0.4.3  Baseline E2E Freeze
v0.4.5  Competition Submission Freeze
v0.5.0  Retriever / LLM / Agent research only if Oracle gap or metrics justify it
```

当前详细数据事实见 [`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md)，当前任务分工见 [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md)。
