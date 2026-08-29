# Architecture — Current Runtime and Open Generalization Paths

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
Governed ModelSignal
                 ↓
Conflict Detection
                 ↓
bounded Targeted Re-check
                 ↓
LLM Final Supervisor
+ deterministic fallback
                 ↓
Trace + Evidence / Screenshot + Report / UI / API
```

Release evaluation 位于 runtime 之后：M1 / M2 / M3 / M5、Dynamic generalization、freeze / Validation / audits / package。

## 2. Document / Role-B boundary

Parser 拥有 physical page identity；page/text/bbox 由解析/Evidence layer 提供，UI 不猜坐标。

Financial 保持 deterministic-first；Legal / Business 只消费 bounded Evidence，受 Pydantic schema 与 Evidence scope guard 约束。

PR #189 后正式 fixed-journal gated checkpoint：

```text
Batch009 M1 = 14/30 = 46.67%
Batch009 M2 = 21/48 = 43.75%
Batch009 offline = 9/30, 15/48
last real fresh checkpoint = Batch005 11/30, 17/48
```

fixed journal 是诊断 microscope，不是 ALL79 Release score，也不能冒充 fresh-provider result。

当前 Role-B root order：

```text
retrieval candidate generation / ranking
→ exact page / anchor Evidence binding
→ remaining deterministic / numeric extraction
→ genuine conflict fail-closed
→ fixed-vs-fresh LLM / Evidence variance
```

执行允许 multi-root wide sprint：多个 proven compatible subfix 独立 commit，targeted controls 后组成 bundle，出现回归只撤问题 subfix，保留 best checkpoint，再扩大 Development。

已拒绝的 direct ranked concentration-table candidate 因无 canonical M1/M2 gain 且 supplier existence F1 回归，不得原样恢复。broad Parser preservation / period candidate generation 只有出现新 proof 才重新打开。

## 3. Market runtime

### Historical governed path

```text
438 governed Market-X Core artifacts
→ GovernedPRBMarketContextProvider
→ schema / identity / hash / PIT provenance validation
→ MarketContext
```

### Target unified resolver

```text
case identity
→ validated cache/artifact exists?
   ├─ yes → load
   └─ no  → governed historical/online source
             → PIT-safe builder
             → validation
             → optional governed cache
→ MarketContext
```

新 IPO 不要求强行生成数字：合法历史不足时 `PARTIAL / UNAVAILABLE` 是正确产品行为。

LLM / Skill 不能 mint market numbers。missing 不得 zero-fill；目标 IPO 上市后数据和 Blind outcome 不得进入 pre-listing runtime。

## 4. Model runtime

### Current stable baseline

```text
receipt-bound final-three handoff
→ Frozen Model 3/3
→ uncalibrated_model_score + drivers
```

该路径用于稳定 Demo / regression，不是最终泛化机制。

### Target dynamic path

```text
governed feature vector
+ final frozen model artifact/hash
+ feature / alert manifests
→ LightGBM inference (no retraining)
→ uncalibrated_model_score
→ native pred_contrib / SHAP
→ ModelSignal
```

必须完成明确的 `PROMOTE_V2 / RETAIN_FROZEN_PR_F` 决议。任何 promoted model 创建新 versioned identity，不覆盖历史 frozen PR-F。

SHAP 必须来自当前 inference；不得复制 final-three drivers。

## 5. Supervision / conflict / trace

Final Supervisor 只能引用 supplied in-scope Risk、Evidence、Conflict、Recheck、MarketContext、ModelSignal；severity 不低于 deterministic verified-risk floor。

当前 regression baseline：

```text
E1 = 3/3
first-attempt accepted = 3/3
fallback = 0
M3 = 1.0 x 3
recheck = 17/17
```

`unresolved + recheck executed` 是合法状态，不等于 workflow failure。

## 6. Evidence and product surfaces

当前 final-three：

```text
Evidence ID
→ source PDF hash
→ physical page
→ unique localisation / truthful fallback
→ screenshot
→ screenshot manifest / hash
```

实测 `17/17` precise。

最终 UI 明确支持：

```text
Offline Demo Replay
Historical Governed IPO
Fresh New-IPO Analysis
```

Frontend 只消费正式 schema/state/provenance，不自己计算 Market/Model，也不把 unavailable 染成 available。

发行人输入已支持 official catalog-backed 快速匹配；正式 downstream join 仍使用 governed identity，而不是 fuzzy company-name join。

## 7. Current stable baseline

进入 regression-protection：

- final-three Market/Model `3/3`；
- Final Supervisor E1 `3/3`；
- M3 `1.0 x 3`；
- recheck `17/17`；
- precise screenshot `17/17`；
- seven-stage `21/21`；
- canonical replay `66` files；
- fresh clone / Streamlit smoke / team-ready checks PASS。

## 8. Open architecture work

```text
ALL79 M1/M2
Dynamic Market-X resolver / fresh-case PIT source
formal D model decision
frozen-model dynamic inference + native SHAP
final answer-ready frontend
capability proofs
freeze / one-shot Validation / audits / secure package
```

Human Review sidecar/UI/export 可保留为 optional 人机协同能力，不是当前 Release Gate。
