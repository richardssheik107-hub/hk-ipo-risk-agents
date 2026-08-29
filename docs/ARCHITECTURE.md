# Architecture — Current Runtime and Diagnostic Lanes

> 状态日期：`2026-08-29`

## 1. Production analysis path

```text
IPOAnalysisRequest
      ↓
Prospectus Parser
      ↓ DocumentChunk(page, text, bbox)
Retriever
      ↓ Evidence
Financial ─┬─ Legal ─┬─ Business
           └─────────┘
                 ↓
              Verifier
                 ↓
        Document Supervisor
                 ↓
Governed MarketContext + Skills
                 ↓
Governed model signal
                 ↓
Conflict Detection
                 ↓
bounded Targeted Re-check
                 ↓
Verifier Challenge
                 ↓
LLM Final Supervisor
+ deterministic fallback
                 ↓
Trace + Evidence / Screenshot + Report / UI / API
                 ↓
optional Human Review
```

Final release evaluation 位于 runtime 之后：

```text
Frozen Existing Gold + B artifacts
C market trace + D outcome artifacts + E final artifacts
→ M1 / M2 / M3 / M5
→ product-generalization / capability gates
→ Validation / readiness / audits / package
```

Human Review 不修改机器事实，并且不再是 mandatory Release Gate。

## 2. Document boundary

### Parser / Evidence geometry

Parser 拥有 physical page identity。page、text 与 bbox 必须来自解析/Evidence layer；UI 不得猜测。

当前 final-three 已完成：

```text
Evidence ID
→ source PDF hash
→ physical page
→ upstream bbox / unique exact quote match
→ screenshot
→ screenshot manifest / hash
```

实测 `17/17` precise。多重匹配或无匹配继续 fail closed。

### Retriever

正式检索允许 keyword、domain-aware 和 Development-only 可消融的 lexical/hybrid 改造。禁止 Gold、公司、股票、case 或页码进入 runtime scoring。

### Financial

Financial 保持 deterministic-first。数值、期间、单位、比例和 Calculation 由 Python 负责；LLM 不覆盖已确定的权威数值。

当前 B 根因重点是 deterministic fact formation，而不是 broad Parser/period-selector rewrite。

### Legal / Business

LLM 只消费 bounded Evidence，输出受 Pydantic Schema 与 Evidence scope guard 约束。provider failure、scope rejection 或表达冲突不得无条件删除正确 deterministic candidate。

## 3. Role-B v0.4.6 diagnostic lane

```text
same fixed Development subset
       ├─ offline: zero network baseline
       ├─ shadow: real LLM + journal, canonical result = offline
       └─ gated: replay journal through agents, no extra network
```

当前 checkpoint：

```text
fixed-journal M1 = 12/30
fixed-journal M2 = 18/48
fresh gated M1 = 11/30
fresh gated M2 = 17/48
structured valid = 38/40
```

当前 root sequence：

```text
deterministic_fact_missing
→ retrieval_candidate_miss
→ numeric extraction / genuine conflicts
→ LLM / Evidence variance
```

## 4. Market boundary

历史 frozen path：

```text
438 governed Market-X Core artifacts
→ GovernedPRBMarketContextProvider
```

Dynamic New-IPO target：

```text
listing_date + industry + governed prior-IPO history
→ PIT Market-X feature builder
→ MarketContext
```

LLM 不能 mint market numbers。真实缺失合法；zero fill、未来信息和未经证明 proxy 不合法。

## 5. Model / Outcome boundary

当前 final-three：

```text
receipt-bound frozen PR-F handoff
→ uncalibrated_model_score
→ signed/native drivers
```

下一步 dynamic inference：

```text
governed feature vector
+ frozen model artifact/hash
→ LightGBM inference
→ pred_contrib / native SHAP
→ ModelPredictionView
```

不得复制 final-three per-case signal 冒充新 case inference。

Frozen PR-F 有正式 receipt；v2 candidate 使用 Development selection 并在 2024 一次评价，但尚未晋升。任何 promote 必须创建新的 versioned freeze / receipt / artifact / handoff。

Outcome evaluator 独立计算 1D / 5D / 20D / 60D，不把真实 outcome 反馈到分析 runtime。

## 6. Supervision

Final Supervisor v3 只能引用 in-scope Risk、Evidence、Conflict、Recheck 和 governed market/model signals；severity 不低于 deterministic verified-risk floor。

当前实测：

```text
Gate E1 = 3/3
first-attempt accepted = 3/3
corrections = 0
fallback = 0
scope violation = 0
```

远程失败仍保留 deterministic fallback，但 fallback 不计 remote acceptance。

## 7. Trace / M3

Relevant event 必须有 actor/action/tool，并绑定 Evidence、Calculation 或 explicit `no_evidence_reason`。远程 LLM 额外记录 provider、model、Prompt、request identity、response hash 和 latency。

当前 final-three：`M3 = 1.0 × 3`。

## 8. Conflict / Re-check

re-check v2 对 document-actionable conflict 使用 bounded budget；cross-channel non-document conflict 不消耗 document budget。

当前 final-three：

```text
17/17 actionable attempted
budget-skipped = 0
```

`unresolved` + `recheck executed` 是合法事实状态，不等于 workflow failure。

## 9. Human Review

`HumanReview` sidecar / UI / export 保留，作为 optional 人机协同能力。

当前 Release policy：

```text
human-review count is not a release requirement
M4 6-review gate = removed
```

空 review 只能解释为 `unreviewed`，不能解释为“已批准”。

## 10. Replay / product delivery

Canonical replay：

```text
reports/v045_demo_bundle
3 cases
66 files
hash verify PASS
fresh clone PASS
Streamlit smoke PASS
```

Replay immutable：不会用新代码给旧运行补结果；provenance 保留 recorded run SHA。

## 11. Current measured gaps

已关闭：

- C/E final-three 3/3；
- M3 1.0 ×3；
- Evidence screenshot 17/17；
- seven-stage 21/21；
- team-ready replay；
- Final Supervisor vocabulary/scope blocker。

仍开放：

- ALL79 B M1/M2；
- D promote/retain；
- historical-universe frozen-model dynamic inference；
- arbitrary new-IPO PIT Market path；
- pipeline / text embellishment / related-party / comparable valuation demonstrations；
- one-shot Validation；
- final audits / secure package。
