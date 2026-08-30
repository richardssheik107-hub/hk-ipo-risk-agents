# Architecture — Current Runtime and Open Generalization Paths

> 状态日期：`2026-08-30`

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

最终 ALL79 Development checkpoint：

```text
real-LLM gated M1 = 61/102 = 59.80%
real-LLM gated M2 = 93/191 = 48.69%
offline selected M1 = 70/102 = 68.63%
offline selected M2 = 103/191 = 53.93%
```

real LLM 已覆盖 79/79；316 tasks 中 310 valid、6 fallback、0 transport failure。
单调性失败且删除正确 deterministic candidate，因此不 promote。两种模式均未达到
M1/M2 Gate；当前停止算法迭代并冻结为提交证据。

历史诊断曾采用 multi-root wide sprint；该冲刺已随本次 ALL79 冻结结束，不再作为当前执行指令。

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

`PROMOTE_V2` 决议已通过 A-owned PR #184 生效。晋升模型使用新的 versioned identity，未覆盖历史 frozen PR-F；独立 freeze、四项 artifact、strict receipt 与 product handoff 均已落地，两条身份不互相覆盖。

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
G2 M1/M2 threshold failure（frozen）
one-shot Validation（not executed / blocked under strict policy）
final audits / clean clone / secure package
```

Human Review sidecar/UI/export 可保留为 optional 人机协同能力，不是当前 Release Gate。
