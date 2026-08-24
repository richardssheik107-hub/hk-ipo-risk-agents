# HK IPO Risk Agents — End-to-End Closed Loop Master Plan

> Status snapshot: **2026-08-24**  
> Strategy: **End-to-End Closed Loop First, Competition Hardening Second**  
> Current formal Gate: **PR-G — A review passed; local freeze manifest pending**  
> PR-H preparation: **UNBLOCKED**

## 1. Program objective

v0.4 的目标不是继续无限优化单个 Agent，也不是用 2024 Validation 反复追逐一个更好看的 AUC，而是先完成一条真实、可重建、可解释、可审计的端到端链路：

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
PR-E Baseline + Oracle          COMPLETE / FROZEN
PR-F LightGBM + Explainability  COMPLETE / FROZEN
PR-G implementation             MERGED / A REVIEW PASS
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

Market-X Extended 已接入 governed CSMAR HSI daily close，438/438 官方 case 的 HSI 5D、20D return 与 20-session volatility 已通过 PIT readiness；authoritative industry benchmark 与 HK total-market turnover 仍显式缺失。

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

## 5. Frozen PR-E / PR-F interpretation

PR-E 在 2024 Validation 上没有验证出稳定 Document 增量。PR-F 的 frozen LightGBM 得到：

```text
Full Production 2024
M   ROC-AUC 0.4246
P   ROC-AUC 0.5000
PM  ROC-AUC 0.4246
```

PM 与 M 在该 frozen tree policy 下预测完全等价，Production Document 100 维特征没有获得 split / gain / SHAP 使用。Oracle `OM-M ROC-AUC = -0.0143`，95% paired-bootstrap interval `[-0.3171, 0.2917]`，样本仅 19 个 Validation case。

正式解释边界：

- 这是当前 5D target、样本规模、feature representation 与 frozen model policy 下的失败/不稳定结果；
- 不是“招股书原始信息没有价值”的证明；
- 也不是“Oracle 已证明存在很强专家上限”的证据；
- 不允许因为 AUC `< 0.5` 在看过 2024 后反转分数方向并把它包装成正式提升；
- 不允许继续用 2024 做模型、特征、Prompt、Retriever 或 LLM 调参后仍称其为 untouched Validation。

因此 PR-F 的意义是冻结一个诚实基线，并把后续研发从“盲目调模型”转向“直接测风险识别能力 + 多 horizon + Market Sentiment + 产品级可追溯闭环”。

## 6. PR-G review and transition to PR-H

PR #104 已将 frozen model evidence adapter、Market Context、Final Supervisor、opt-in workflow、v0.4 13-section report 和 UI surface 合入 main。A 已完成 protected-interface / provenance / gate 审阅，结论见 [`V04_PR_G_A_GATE_REVIEW.md`](V04_PR_G_A_GATE_REVIEW.md)：

```text
PR-G implementation / contract review     PASS
PR-G local freeze manifest materialization REQUIRED_LOCAL_ACTION
PR-H preparation                           UNBLOCKED
```

PR-G 不能在纯远程审阅中直接标记 COMPLETE/FROZEN，因为最终 manifest 需要真实本地 prospectus/runtime 生成 prospectus hash 与 Final Supervisor content hash。不得猜测这些值。

A 已冻结两个 PR-H runtime 方向：

```text
Governed Market runtime
→ consume PreListingMarketFeatureSnapshot or a lossless governed projection
→ do not promote legacy MarketSnapshot to PR-B source-of-truth

Frozen model runtime
→ keep full PR-F runtime outside Git
→ consume a checksum + model_result_hash bound local handoff via pr_f_run_dir
```

## 7. Gate sequence

| Gate | Deliverable | State |
| --- | --- | --- |
| PR-A | Document materialization + coverage | COMPLETE / FROZEN |
| PR-B | Market-X Core + governed EOD | COMPLETE / FROZEN |
| PR-C | Frozen 5D target | COMPLETE / FROZEN |
| PR-D | Canonical model-ready dataset | COMPLETE / FROZEN |
| PR-E | Linear/Ridge/Logistic + Oracle diagnostic | COMPLETE / FROZEN |
| PR-F | LightGBM + SHAP / importance / calibration / ablation | COMPLETE / FROZEN |
| PR-G | Market Agent + Final Supervisor | **A REVIEW PASS / LOCAL FREEZE PENDING** |
| PR-H | Streamlit Full E2E + real-case demo | **PREPARATION UNBLOCKED** |
| CH-0..CH-6 | Competition hardening | AFTER PR-H |

Formal PR-H starts after the final PR-G frozen manifest is committed. PR-H then proves the full governed runtime across 3–5 real IPO cases.

## 8. Post-PR-F two-track strategy

后半程采用两个互补目标，而不是把所有项目价值押在 5D AUC 上。

### Track A — Risk Intelligence / Auditability

```text
Document risk extraction
→ Evidence / Calculation / page / bbox
→ Verifier
→ Agent conflict / re-check / arbitration
→ human review
→ auditable Final Supervisor output
```

Competition 直接硬目标：

```text
关键风险要素抽取准确率           >= 80%
关键 Evidence recall            >= 85%
Agent / Tool / Evidence trace   = 100%
```

### Track B — Market Warning / Predictive Validation

```text
Market context / sentiment
+ governed model score
+ SHAP / bootstrap uncertainty
+ 1D / 5D / 20D / 60D outcomes
→ uncertainty-aware warning
```

5D 继续作为 frozen primary target，但不假设结构性 Document 风险必须在 5D 最强；CH-1 将验证 20D / 60D 是否更符合结构性风险的经济含义。短期 1D / 5D 的新增研发优先从 point-in-time IPO heat、近期破发/5D 表现、同行业历史 IPO context、liquidity/activity 和 authoritative market benchmark 补充中寻找增量。

## 9. Evidence and calculation governance

- 无真实 Evidence 的风险不得成为 verified formal conclusion；
- 数值结论由 deterministic Skill / Calculation 完成；
- Verifier / Supervisor 不创造原始 Evidence；
- missing 不等于 zero / safe；
- 失败必须结构化记录，不能 silent drop；
- score 未经 calibration 不得表述为真实概率。

## 10. Market governance

Market-X Core 已冻结。HSI Extended 已有 governed source；industry benchmark / HK total-market turnover 仍可显式缺失。不得使用不等价 proxy、fake benchmark 或 neutral zero 为了“补齐”特征。

PR-H runtime 必须保留 `PreListingMarketFeatureSnapshot` 的 case identity、strictly-pre-listing cutoff、feature schema/policy、per-feature provenance 和 missing semantics。legacy `MarketSnapshot` 只保留 v0.3 compatibility。

## 11. Competition enhancement decision rules

Competition Hardening 不进行无目标重构：

- CH-1：独立版本化 1D / 20D / 60D outcome，5D frozen policy 不回写；
- CH-2：按风险类别直接测 Precision / Recall / F1 / Evidence Recall；达标类别不重写，不达标类别做最小增强；
- 若 CH-2 error attribution 显示主要损失来自 retrieval，则优先 Hybrid Retrieval；若来自复杂语义/条件理解，再引入 LLM semantic extraction / reranking；
- LLM 不替代 deterministic financial calculation、schema validation、feature vectorization、hash 或 provenance；
- CH-3：短期市场预测重点补 Market Sentiment / IPO heat / liquidity / comparable context；
- CH-4 / CH-5：冲突仲裁、全链 trace、Evidence screenshot 与 human audit trail 作为比赛产品能力；
- CH-6：统一报告抽取指标、Evidence 指标、traceability、multi-horizon 预测结果和 3–5 个真实案例，不挑选单一最漂亮指标代替全套证据。

## 12. Current PR-H objective

PR-H 必须完成：

```text
3–5 real IPOs
PDF
→ Document Evidence / Calculation
→ governed Market-X runtime
→ frozen per-case model score + SHAP drivers
→ Final Supervisor
→ Streamlit / 13-section Final Report
```

每个 demo case 均需验证 Evidence references resolve、market provenance 合法、model runtime 与 frozen hash 一致、score 不被表述为 probability、2025 Blind y 未访问。只有 PR-H 跑通并冻结后，CH-0..CH-6 才成为正式主线。

Competition 细节见 [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md)。五人角色见 [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md)。
