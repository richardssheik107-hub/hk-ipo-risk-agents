# HK IPO Risk Agents — End-to-End Closed Loop Master Plan

> Status snapshot: **2026-08-25**  
> Current Gate: **PR-H PARTIAL / BLOCKED**  
> Program mode: **Competition Final Sprint — five parallel ownership lanes**

## 1. Program objective

项目不再扩展为长期研究计划，而是在现有 v0.4 基础上尽快完成赛题要求的完整 Competition Release。

最终链路：

```text
Prospectus PDF
→ Parser / Retriever / Evidence
→ Financial Agent + deterministic Calculation
→ Legal Agent + LLM semantic extraction
→ Business Agent + LLM semantic extraction
→ Verifier
→ governed Market facts + Skills
→ LLM Market Agent
→ frozen Model signal if available + Rule
→ LLM Final Supervisor
→ Conflict → targeted re-check → resolution / uncertainty
→ Final Report / Evidence Viewer / Agent Trace / Human Review
→ 1D / 5D / 20D / 60D real-performance validation
```

## 2. Frozen foundation

```text
PR-A Document-X                 COMPLETE / FROZEN
PR-B Market-X Core              COMPLETE / FROZEN
PR-C 5D Outcome                 COMPLETE / FROZEN
PR-D Canonical Dataset          COMPLETE / FROZEN
Oracle v2                       COMPLETE / FROZEN / EVALUATION-ONLY
PR-E Baseline + Oracle          COMPLETE / FROZEN
PR-F LightGBM + Explainability  COMPLETE / FROZEN
PR-G Market Agent + Supervisor  COMPLETE / FROZEN
PR-H Full E2E                   PARTIAL / BLOCKED
```

Measured anchors:

```text
Official cases                  438
Production Document-X           438 / 438, 100 dims
Market-X Core                   438 / 438, 30 positions
5D outcome                      424 / 438
Canonical model-ready           424 = 354 Dev + 70 Val
Oracle v2 strict                96 = 77 Dev + 19 Val
2025 Blind y accessed           false
```

## 3. Competition hard requirements

```text
关键风险要素抽取准确率      >= 80%
关键 Evidence Recall         >= 85%
Agent / Tool / Evidence trace = 100%
上市首日 / 5D / 20D / 60D    required
可运行原型 / API / UI         required
prediction table / reasoning logs / Evidence / case reports required
Human Review                   required
```

## 4. Five-person ownership

```text
A  public contracts / integration / CI / release / submission
B  LLM Document Intelligence / Evidence / benchmark
C  Market Intelligence / Skills / LLM interpretation
D  Outcome / PR-F runtime / evaluation
E  LLM Supervisor / conflict / trace / Evidence Viewer / Human Review / UI
```

四条业务 lane 同时向 E 和 A 交付，不再按阶段串行等待。

## 5. LLM architecture policy

LLM 应负责：

```text
Legal complex clause semantics
Business commercialization/core-product semantics
Disclosure Tone bounded interpretation
Market interpretation of governed PIT facts
Final Supervisor synthesis / conflict / uncertainty / re-check
```

Deterministic code 继续负责：

```text
exact financial math
schema / identity
PIT guards
feature materialization
hash / manifest
model scoring
reproducibility
```

Formal RiskItem 仍需要 Evidence；LLM 不能创造 Evidence 或 market facts。

## 6. Document Intelligence workstream

B 负责让真实 case 走通：

```text
Retriever
→ Evidence
→ LLM structured extraction
→ schema validation
→ Risk Builder
→ Verifier
```

重点覆盖：

```text
redemption_rights
material_litigation_compliance
related_party_transaction
precommercial_product
core_product
pipeline_stage
commercialization_status
Disclosure Tone / Obfuscation
```

同时产出 submission-ready Risk/Evidence benchmark。

## 7. Market Intelligence workstream

C 将已有 governed market facts 封装为：

```text
IPOHeatSkill
MarketRegimeSkill
optional ComparableIPOSkill
```

再生成 `MarketContext → LLM Market interpretation`。

任何输出必须保留 value / availability / missing reason / cutoff / provenance。Industry return 在历史分类映射仍不 PIT-safe 时继续 unavailable。

## 8. Outcome / Model / Evaluation workstream

D 必须补齐：

```text
return_1d
return_5d
return_20d
return_60d
```

并尽量恢复 frozen PR-F per-case score + SHAP。若无法恢复，则 Model Channel 显式 unavailable。

D 还负责：

```text
test_predictions.csv
multi_horizon_results.csv
AI-vs-Offline comparison
submission evaluation summary
```

当前 frozen PR-F 弱结果不触发 new model search。

## 9. Multi-Agent / Product workstream

E 负责：

```text
LLM Final Supervisor
Conflict
RecheckRequest
Verifier challenge
resolution / unresolved uncertainty
Agent Trace
Evidence Viewer
Human Review
final Streamlit
```

协同路径：

```text
Agent disagreement
→ Conflict
→ targeted re-retrieval
→ Skill / Agent rerun
→ Verifier challenge
→ Supervisor resolution
```

不做无限 autonomous loop；一次受控 re-check 为主要比赛闭环。

## 10. PR-H / model runtime boundary

PR-H 的 frozen PR-F runtime/handoff 缺失仍是 formal blocker，且不能通过 retrain/reconstruct/retune 解阻。

```text
if recovered:
  ModelSignal = governed frozen score + drivers
else:
  formal PR-H remains blocked
  ModelSignal = unavailable
  rest of competition runtime continues
```

## 11. Explicitly deferred

```text
new model family search
large hyperparameter tuning
broad feature/P-Core research
large Retriever redesign
industry PIT research
broad new market datasets
paper-style ablation
story-only UI work
```

1D/5D/20D/60D outcome 计算不属于 defer 项，因为是赛题明确要求。

## 12. Final release sequence

这里不再按日期排序，而按完成条件推进：

```text
B/C/D/E 各 lane 达到 Done
→ A 完成 all-lane integration
→ >=3 real IPO stable E2E
→ full CI / provenance / Blind / determinism checks
→ submission artifacts complete
→ Competition Release / v0.4.5 COMPETITION_READY
```

详细分工见 [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md)。
