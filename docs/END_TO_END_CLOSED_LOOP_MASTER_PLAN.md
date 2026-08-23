# HK IPO Risk Agents — End-to-End Closed Loop Master Plan

> Status snapshot: **2026-08-23**  
> Strategy: **End-to-End Closed Loop First, Competition Hardening Second**  
> Current formal Gate: **PR-G — Market Agent + Final Supervisor**

## 1. Program objective

v0.4 的目标不是继续无限优化单个 Agent，而是先完成一条真实、可重建、可解释、可审计的端到端链路：

```text
Prospectus PDF
→ Document Intelligence
→ Production Document X
→ Pre-IPO Market X
→ 5D Outcome Y
→ Canonical Model-ready Dataset
→ Baseline + Oracle Diagnostic
→ LightGBM + Explainability
→ Market Agent
→ Final Supervisor
→ Streamlit Full E2E
→ Baseline E2E Freeze
```

baseline E2E 冻结后，再进入赛题专项强化：

```text
CH-0 Scope Lock
→ CH-1 Multi-horizon Outcome
→ CH-2 Document Risk Hardening
→ CH-3 Market Sentiment + Skills
→ CH-4 Conflict Resolution + Traceability
→ CH-5 Evidence Screenshot + Human Review
→ CH-6 Evaluation + Submission Freeze
```

## 2. Current frozen foundation

```text
PR-A Document X                 COMPLETE / FROZEN
PR-B Market-X Core              COMPLETE / FROZEN
PR-C 5D Outcome                 COMPLETE / FROZEN
PR-D Canonical Dataset          COMPLETE / FROZEN
Oracle v2                       COMPLETE / FROZEN / EVALUATION-ONLY
PR-E Baseline + Oracle         COMPLETE / FROZEN
```

Measured anchors：

```text
Official cases                  438
Production Document-X           438 / 438 / 100 dims
Market-X Core                   438 / 438 / 30 positions
5D outcome available            424
Explicit exclusions              14
Canonical model-ready           424 = 354 Dev + 70 Val
Oracle v2                       98 materialized / 96 strict usable
Oracle v2 split                 77 Dev / 19 Val
2025 Blind y accessed           false
```

## 3. Production and Oracle remain permanently separate

### Production path

```text
Prospectus
→ Parser
→ Retriever
→ Financial / Legal / Business Agents
→ Deterministic Skills
→ Verifier
→ Document Supervisor
→ Snapshot
→ Production Document X
```

Production 必须从真实招股书重新生成，不依赖 Expert Gold，并可以进入最终产品。

### Oracle path

```text
Reviewed Expert Gold
→ versioned Oracle feature builder
→ Oracle Document X
```

Oracle 只用于 evaluation ceiling / error attribution：

```text
evaluation_only = true
production_consumable = false
```

Oracle 不进入 Production runtime，不得把 Gold page / Evidence ID / manual answer 泄漏进 Production X，也不得读取 2025 Blind y。

## 4. Formal modeling design

固定时间治理：

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

PR-E 正式比较：

```text
M   Market only
P   Production Document only
O   Oracle Document only
PM  Market + Production
OM  Market + Oracle
```

必须 same cohort / split / target / preprocessing / model family。

核心诊断：

```text
Production Increment     = PM - M
Document Signal Ceiling  = OM - M
Pipeline Gap              = OM - PM
```

Development 使用严格 forward chaining；2024 只作为正式 Validation，不参与 feature / threshold / preprocessing / coefficient 的拟合。

## 5. Gate sequence

| Gate | Deliverable | State |
| --- | --- | --- |
| PR-A | Document materialization + coverage | COMPLETE / FROZEN |
| PR-B | Market-X Core + governed EOD | COMPLETE / FROZEN |
| PR-C | Frozen 5D target | COMPLETE / FROZEN |
| PR-D | Canonical model-ready dataset | COMPLETE / FROZEN |
| PR-E | Linear/Ridge/Logistic + Oracle diagnostic | COMPLETE / FROZEN |
| PR-F | LightGBM + SHAP / importance / calibration / ablation | COMPLETE / FROZEN |
| PR-G | Market Agent + Final Supervisor | **CURRENT** |
| PR-H | Streamlit Full E2E + real-case demo | WAITING |
| CH-0..CH-6 | Competition hardening | AFTER PR-H |

正式 Gate 必须严格串行；准备性工作可并行，但不改变冻结状态、不读取后续不允许的数据、不越级进入 `main`。

## 6. Evidence and calculation governance

- 无真实 Evidence 的风险不得成为 verified formal conclusion；
- 数值结论由 deterministic Skill / Calculation 完成；
- Verifier / Supervisor 不创造原始 Evidence；
- missing 不等于 zero / safe；
- 失败必须结构化记录，不能 silent drop；
- score 未经 calibration 不得表述为真实概率。

## 7. Market governance

Market-X Core 已冻结。Market-X Extended 的 HSI / authoritative industry benchmark / HK total-market turnover source 仍可显式缺失；不得使用不等价 proxy、fake benchmark 或 neutral zero 为了“补齐”特征。

## 8. Frozen PR-E completion basis

PR-E 已在以下条件全部满足后标记 COMPLETE / FROZEN：

1. 输入与 frozen PR-D / Oracle v2 manifest 严格绑定；
2. M/P/PM full-production cohort 可复现；
3. M/P/O/PM/OM Oracle fair intersection 可复现；
4. Development forward-chaining 无未来信息；
5. 2024 Validation 未参与拟合或调参；
6. 正式分类与回归 metrics 真实产生并保存；
7. PM-M、OM-M、OM-PM 被明确报告；
8. non-significance 不被解释为“没有效果”，小 Oracle Validation 样本必须带 uncertainty / power caveat；
9. 2025 Blind y accessed = false；
10. tests / validation / reproducibility / A final review PASS。

## 9. Current PR-G and later gates

PR-F 已冻结更复杂模型比较；PR-G 当前把 frozen model score、SHAP drivers 与 uncertainty 接入 Market Agent / Final Supervisor。PR-H 才完成 PDF → Final Report 的稳定 E2E。只有 PR-H 跑通并冻结后，CH-0..CH-6 才成为正式主线。

Competition 细节见 [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md)。五人角色见 [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md)。
