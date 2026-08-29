# Competition Closure Plan — Current Submission Sprint

> 状态日期：`2026-08-29`
>
> 当前结论：**NOT COMPETITION_READY**
>
> 实时 Gate：`V0.4_RELEASE_ACCEPTANCE.md`
>
> 冻结指标协议：`COMPETITION_METRIC_PROTOCOL.md`

## 0. 当前事实

项目已完成稳定三案例团队基线：

```text
Gate E1 = 3/3
real-provider first-attempt accepted = 3/3
scope corrections = 0
fallback = 0
M3 = 1.0 x 3
Market / frozen Model = 3/3
recheck = 17/17; budget-skipped = 0
seven-stage = 7/7 x 3
Evidence screenshots = 17/17 precise
canonical replay = 66 files
fresh clone / Streamlit smoke / team-ready CI = PASS
```

因此当前主要问题已经从“产品能不能完整展示”转为：

```text
Document Intelligence 定量指标
+ Dynamic New-IPO 泛化
+ D 模型最终治理决议
+ competition capability coverage
+ final freeze / Validation / package
```

Human Review UI / export 继续保留，但 `M4 6 human reviews = REMOVED FROM RELEASE PLAN`，不阻塞 `COMPETITION_READY`。

## 1. 当前 Source-of-truth 数字

### Role-B — Batch009 accepted checkpoint

最新可比 fixed-journal gated：

```text
Batch005  M1 = 12/30   M2 = 18/48
Batch008  M1 = 13/30   M2 = 20/48
Batch009  M1 = 14/30   M2 = 21/48
```

当前 Batch009：

```text
fixed-journal gated M1 = 14/30 = 46.67%
fixed-journal gated M2 = 21/48 = 43.75%
offline M1 = 9/30
offline M2 = 15/48
```

最后一个真实 fresh-provider checkpoint 仍是 Batch005：

```text
fresh gated M1 = 11/30 = 36.67%
fresh gated M2 = 17/48 = 35.42%
structured valid = 38/40
fallback = 2
transport failure = 0
scope rejection = 0
```

Batch008 / 009 使用 immutable local journal、`network_calls = 0`，所以 fixed-journal gain 不能冒充 fresh-provider gain。

已接受：

- Batch008 legacy Chinese cash-statement / explicit Notes-column deterministic exact-fact compatibility；
- Batch009 generalized Legal redemption/restoration lifecycle recognition。

已拒绝：direct ranked concentration-table extraction；它没有提高 canonical M1/M2，并把 supplier existence F1 从 `0.875` 降到 `0.80`，已完整回滚。

已排除 broad `period_candidate_generation` / Parser preservation 作为当前主根因；历史 v0.4.5 GLM-5.3 harness 已归档为 measured failure，不作为当前主路线。

当前 root-cause 顺序：

```text
retrieval candidate generation / ranking
→ exact page / anchor Evidence binding
→ remaining deterministic / numeric extraction
→ genuine conflicts
→ fixed-vs-fresh LLM / Evidence variance
```

`forensic_011` 中 retrieval candidate generation 仍是最大 proven first-failure layer：6 M1 / 16 M2 units。一个 redemption Evidence page 仍位于 rank 18，超出 Legal Agent bounded 10-item consumption，需要优化 transaction/lifecycle co-occurrence ranking，而不是无界提高 K。

### Role-D

```text
Frozen PR-F:
Recall = 4.35%
F1 = 7.69%
PR-AUC = 33.64%
ROC-AUC = 42.46%

v2 candidate:
Recall = 52.17%
F1 = 42.11%
PR-AUC = 38.12%
ROC-AUC = 48.75%
```

v2 未 promote；frozen PR-F 仍是正式 identity。

### Product baseline

```text
recorded run = 3d81e5d0d71aeb5ffc76e3f123e8eecb5c75af8d
runtime-equivalent release = 802bf5095e0db6a604dcb762e1070563f8cb1b34
team-ready merge = 732c5fd7b609b1a6589630b6e6a559c117206747
bundle = reports/v045_demo_bundle
file count = 66
bytes = 7,528,749
verify = PASS
```

## 2. 工作轨 A — Role-B M1/M2（P0）

正式目标：

```text
ALL79 Development
M1 >=0.80（target >=0.85）
M2 >=0.85（target >=0.88）
real_llm_cases = 79
Validation = false
Blind not used for optimization
```

### 2.1 当前策略

不要重新大范围改 Parser 或 period selector，也不要直接恢复 rejected ranked-table candidate。优先：

1. retrieval candidate generation / ranking；
2. exact page / anchor Evidence binding；
3. remaining deterministic / numeric extraction；
4. true conflict fail-closed；
5. fixed-vs-fresh LLM / Evidence stability。

每个修复包必须：

```text
proven root cause
before / after
ablation
regression tests
no company/case/page/Gold-text hardcoding
M1/M2 non-regression
fresh-provider status explicitly reported
```

fixed10 只是诊断。达到稳定提升后尽快扩大 Development checkpoint，最终必须 ALL79。

## 3. 工作轨 B — Dynamic New-IPO Full Path（P0）

这是当前最重要的产品泛化任务。目标不是再增加几个预置案例，而是消除“只有 final-three 才全通道”的观感。

### Phase 1 — 438 historical frozen universe

```text
existing frozen Market-X artifact
→ frozen feature schema validation
→ frozen LightGBM dynamic inference
→ native pred_contrib / SHAP
→ ModelPredictionView
→ Final Supervisor / report
```

验收：从非 final-three frozen historical cases 抽取 holdout，不增加 case-specific code，不依赖预生成 per-case handoff。

### Phase 2 — arbitrary new IPO

```text
new PDF
→ Document Agents
→ issuer/listing identity
→ governed PIT history
→ Dynamic Market-X
→ frozen model inference
→ SHAP
→ Final Supervisor
→ report
```

如果合法市场历史不足，状态必须明确 partial/unavailable；不能 fake-fill。

## 4. 工作轨 C — Role-D Model Decision（P0）

只允许一次治理决议。

### Promote v2

- 审核 expanding Development selection；
- 审核 2024 one-shot identity；
- 审核 Blind / leakage；
- 冻结 code/config/features/alert policy；
- 新建 versioned receipt / checker / handoff；
- current-main strict revalidation；
- 不再按 2024 调参数。

### Retain frozen PR-F

- 保留现有 receipt；
- 定位为弱辅助 triage signal；
- 不夸大预测能力；
- 仍完成 dynamic inference/product contract 与最终审计。

## 5. 工作轨 D — Competition Capability（P1）

必须有真实、可审计演示：

- core pipeline progress；
- text embellishment；
- related-party transaction；
- comparable IPO valuation；
- Evidence screenshot；
- single/batch report；
- API/UI；
- Dynamic New-IPO proof。

Human Review 可以展示，但 optional，不需要人工评分。无 Existing Gold 的能力统一标记 `QUALITATIVE DEMONSTRATION`，不混入 M1/M2。

## 6. 已完成、原则上只做回归保护的部分

- final-three Market 3/3；
- final-three frozen Model 3/3；
- Final Supervisor v3 E1 3/3；
- M3 1.0 ×3；
- recheck v2 17/17；
- Evidence screenshot 17/17 precise；
- 7-stage 21/21；
- batch report / case report；
- canonical replay / hash manifest；
- fresh-clone launchers；
- team clone checker；
- Role-D runtime CI；
- provenance-preserving runtime equivalence audit；
- Batch008 accepted cash deterministic compatibility；
- Batch009 accepted Legal lifecycle recognition。

这些组件后续只在必要时做回归修复，不再作为开放式优化主线。

## 7. Freeze 与 one-shot Validation（P1）

只有 B ALL79 Development 达标且 D 正式身份冻结后：

1. freeze B code / Prompt / Retriever / Schema / normalization / reconciliation / Verifier / evaluator；
2. freeze D model / feature / alert policy / runtime inference contract；
3. 记录 hashes；
4. 执行 one-shot ALL19 Validation；
5. 不再根据 Validation 回头调参。

## 8. Final audits / package（P1）

必须通过：

```text
latest-main CI
Gold immutability
Blind isolation
PIT audit
Evidence scope
provenance
runtime/model determinism
secret scan
licensed-data scan
absolute-path scan
bundle hash verification
fresh-clone verification
```

最终 package：

```text
source / environment / scripts
prototype / API / UI
prediction table
Agent / Tool / Evidence Trace
Evidence screenshots
canonical case reports
Dynamic New-IPO proof
metrics / audits
artifact index
release note
secure ZIP + SHA-256 manifest
```

不要求 M4 真人 review 文件。

## 9. 五人并行策略

当前正式 owner 见 `docs/team/README.md`：

```text
Person 1 — M1/M2 Document Intelligence
Person 2 — Frontend / Product UX
Person 3 — Dynamic Market-X
Person 4 — Dynamic Model / SHAP + D decision
Person 5 — Release / Submission
```

Person 5 持续做 integration watch，但 only after freeze 执行 one-shot Validation。

## 10. 仍不可放松的边界

- Existing Gold immutable；
- `UNJUDGED != negative`；
- Gold 不进入 runtime；
- Validation one-shot；
- Blind 不用于优化；
- 无公司/股票/case/page/Gold-text 特判；
- LLM 不 invent Evidence / market fact；
- exact numeric claim 由 deterministic Calculation 支撑；
- Market PIT-safe；
- frozen score 不称 probability；
- fallback 不冒充 remote success；
- Secret/PDF/raw EOD/absolute path 不进 Git/bundle。

## 11. Competition Ready

只有以下全部真实满足才可宣称：

```text
M1 >=80%
+ M2 >=85%
+ M3 =100%
+ D formal decision / strict release identity
+ final-three stable baseline preserved
+ Dynamic New-IPO / product coverage acceptable
+ capability cases complete
+ one-shot Validation complete under freeze
+ CI / Blind / provenance / determinism / security audits PASS
+ secure final package PASS
= COMPETITION_READY
```

**不包含 M4 / 人工 review 数量要求。**
