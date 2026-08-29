# Roadmap — 从当前状态到 Competition Ready

> 状态日期：`2026-08-29`
>
> 详细版：`COMPETITION_CLOSURE_PLAN.md`

当前剩余 **4 个实质工作流 + 2 个收尾阶段**。

## 当前数字

```text
B fixed-journal M1 = 12/30 = 40.00%
B fixed-journal M2 = 18/48 = 37.50%
B fresh gated M1 = 11/30 = 36.67%
B fresh gated M2 = 17/48 = 35.42%
B structured valid = 38/40
B current root = deterministic_fact_missing

D frozen PR-F: Recall 4.35%, F1 7.69%, ROC-AUC 0.4246
D v2 candidate: Recall 52.17%, F1 42.11%, PR-AUC 0.3812, ROC-AUC 0.4875
D v2 promotion = pending A review

Market final-three = 3/3
Frozen Model final-three = 3/3
Final Supervisor E1 = 3/3 first-attempt accepted
M3 = 3/3 exactly 1.0
recheck = 17/17; budget-skipped = 0
Evidence screenshot = 17/17 precise
seven-stage = 21/21
canonical replay = 66 files; fresh clone PASS
```

Human Review / M4 已从 Release Gate 移除。Human Review UI 可以继续作为 optional 产品能力，但不要求真人评分。

## 工作流 1 — B 指标与 Full Development（P0）

已排除：

```text
period_candidate_generation as active root
broad Parser preservation as active root
```

当前顺序：

```text
deterministic_fact_missing
→ retrieval_candidate_miss
→ numeric extraction / genuine conflict
→ LLM / Evidence variance
```

每个修复包必须有 proven root cause、测试、前后消融和无 hardcoding 证明。

完成标准：

```text
ALL79 Development
M1 >=0.80
M2 >=0.85
real_llm_cases = 79
Validation=false
Blind not used for optimization
```

## 工作流 2 — Dynamic New-IPO Full Path（P0）

### Phase 1

让 438 个 frozen historical universe 不再依赖 final-three handoff：

```text
Market-X frozen artifact
→ frozen model dynamic inference
→ native SHAP
→ Final Supervisor
```

### Phase 2

打通 arbitrary new IPO：

```text
new PDF
→ issuer / listing identity
→ governed PIT history
→ Dynamic Market-X
→ frozen model inference
→ SHAP
→ Final Supervisor / report
```

无合法市场历史时诚实 partial/unavailable，不造数据。

## 工作流 3 — D 模型正式决议（P0）

A 只做一次 promote/retain：

- promote v2：新 freeze / receipt / handoff / checker；
- retain PR-F：保留弱辅助信号定位并诚实披露限制。

两条路径都要完成 current-main strict revalidation、determinism 和 dynamic inference contract。

## 工作流 4 — Competition Capability（P1）

补齐真实可审计案例：

- core pipeline progress；
- text embellishment；
- related-party transaction；
- comparable IPO valuation；
- Dynamic New-IPO proof；
- Evidence screenshot / report / API/UI。

无 Existing Gold 时标记 `QUALITATIVE DEMONSTRATION`，不混入 M1/M2。

Human Review 可展示，不是必需评测。

## 收尾阶段 1 — Freeze 与一次性 Validation

- freeze B code / Prompt / Retriever / Schema / Verifier / evaluator；
- freeze D model / features / alert policy / inference identity；
- one-shot ALL19 Validation；
- Validation 后不再调参；
- latest-main CI；
- Blind / provenance / determinism / security audit。

## 收尾阶段 2 — Submission

- source / environment / scripts；
- prototype / API / UI；
- prediction table；
- Agent / Tool / Evidence Trace；
- Evidence screenshots；
- canonical case reports；
- Dynamic New-IPO evidence；
- metrics / audits / artifact index；
- secure ZIP + SHA-256 manifest。

不要求 6 份真人 review。

## 稳定基线保护

PR #185 后的 canonical final-three 是当前 `KNOWN_GOOD_TEAM_DEMO_BASELINE`。

后续 B、Dynamic New-IPO、D 改动都必须走 feature branch，并保护：

```text
E1 3/3
M3 1.0 x 3
Market / Model 3/3
17/17 recheck
17/17 precise screenshots
7/7 x 3 stages
canonical replay hash
fresh-clone readiness
```

## Competition Ready

只有：

```text
M1 / M2 / M3
+ D formal model decision
+ Dynamic New-IPO / product coverage
+ capability cases
+ one-shot Validation
+ final audits
+ secure package
```

全部真实完成后，才能标记 `COMPETITION_READY`。
