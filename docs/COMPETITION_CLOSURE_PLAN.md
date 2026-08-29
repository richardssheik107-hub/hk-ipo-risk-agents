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

### Human Review policy

Human Review UI / export 继续保留，但：

```text
M4 6 human reviews = REMOVED FROM RELEASE PLAN
```

不新增真人标注，不要求 3 案 × 2 reviewer，不阻塞 `COMPETITION_READY`。历史 rubric 只作为 optional 解释质量诊断。

## 1. 当前 Source-of-truth 数字

### Role-B

```text
fixed-journal M1 = 12/30 = 40.00%
fixed-journal M2 = 18/48 = 37.50%
fresh gated M1 = 11/30 = 36.67%
fresh gated M2 = 17/48 = 35.42%
structured valid = 38/40
fallback = 2
transport failure = 0
scope rejection = 0
```

当前 root-cause 顺序：

```text
deterministic_fact_missing
→ retrieval_candidate_miss
→ numeric extraction / genuine conflicts
→ LLM / Evidence variance
```

Batch006/007 已排除 `period_candidate_generation` 和广泛 Parser preservation 作为当前主根因。

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

不要重新大范围改 Parser 或 period selector。优先：

1. deterministic fact formation；
2. 明确隔离的 retrieval candidate miss；
3. numeric extraction；
4. true conflict fail-closed；
5. LLM / Evidence stability。

每个修复包必须：

```text
proven root cause
before / after
ablation
regression tests
no company/case/page/Gold-text hardcoding
M1/M2 non-regression
```

fixed10 只是诊断。达到稳定提升后尽快扩大 Development checkpoint，最终必须 ALL79。

## 3. 工作轨 B — Dynamic New-IPO Full Path（P0）

这是当前最重要的产品泛化任务。目标不是再增加几个预置案例，而是消除“只有 final-three 才全通道”的观感。

### Phase 1 — 438 historical frozen universe

当前 438 个 Market-X Core artifacts 已提交。下一步补：

```text
existing frozen Market-X artifact
→ frozen feature schema validation
→ frozen LightGBM dynamic inference
→ native pred_contrib / SHAP
→ ModelPredictionView
→ Final Supervisor / report
```

验收：从非 final-three 的 frozen historical cases 中抽取一组 holdout，不能增加 case-specific code，也不能依赖预生成 per-case handoff。

### Phase 2 — arbitrary new IPO

已有通用 PIT builder：

```text
listing_date + industry + prior IPO history
→ Dynamic Market-X
```

需要接入受治理的历史输入，再进入同一 frozen model inference path：

```text
new PDF
→ Document Agents
→ issuer/listing identity
→ Dynamic PIT Market-X
→ frozen model inference
→ SHAP
→ Final Supervisor
→ report
```

如果合法市场历史不足，状态必须明确 partial/unavailable；不能 fake-fill。

## 4. 工作轨 C — Role-D Model Decision（P0）

只允许一次治理决议：

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

Human Review 可以展示，但 optional，不需要人工评分。

无 Existing Gold 的能力统一标记：

```text
QUALITATIVE DEMONSTRATION
```

不混入 M1/M2。

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
- provenance-preserving runtime equivalence audit。

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

## 9. 并行策略

建议三线立即并行：

```text
B M1/M2 autonomous optimization
Dynamic New-IPO runtime
D model governance decision
```

Capability case 和 final package 准备可穿插推进。

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
