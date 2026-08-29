# Competition Closure Plan — Current Five-Track Sprint

> 状态日期：`2026-08-29`  
> 当前结论：**NOT COMPETITION_READY**  
> 实时 Gate：`V0.4_RELEASE_ACCEPTANCE.md`  
> 冻结指标协议：`COMPETITION_METRIC_PROTOCOL.md`

本文档是当前**唯一总执行计划**。不再维护第二套 Roadmap / Current Plan。

## 0. 当前稳定基线

final-three 已形成可 fresh-clone 的稳定产品基线：

```text
Final Supervisor E1 = 3/3
real-provider first-attempt accepted = 3/3
scope corrections = 0
fallback = 0
M3 = 1.0 x 3
Market / frozen Model = 3/3
recheck = 17/17; budget-skipped = 0
seven-stage = 21/21
Evidence screenshots = 17/17 precise
canonical replay = 3 cases / 66 files
fresh clone / Streamlit smoke / team-ready checks = PASS
```

后续目标是：**指标达标 + 动态泛化 + 最终产品 + 可提交**。

## 1. 五条并行主线

| Track | 核心目标 | 优先级 |
|---|---|---|
| **A — M1 / M2 文档智能优化** | ALL79 Development：M1 `>=80%`、M2 `>=85%` | **P0** |
| **B — 前端 / 产品展示** | 把真实系统做成答辩级最终 UI | **P0/P1** |
| **C — Market-X 动态泛化** | 任意合法新 IPO 进入统一 Market runtime：真实计算或诚实降级 | **P0** |
| **D — Model / Prediction / SHAP 动态化** | 摆脱 final-three per-case handoff，真实加载冻结模型推理 + native SHAP | **P0** |
| **E — 最终集成 / 验收 / 文档 / 提交包** | Freeze → one-shot Validation → audits → fresh clone → secure ZIP | **P1 → 最后 P0** |

详细 owner 文档见 `docs/team/`。

## 2. Track A — M1 / M2 Document Intelligence（P0）

### 正式目标

```text
ALL79 Development
M1 >= 0.80 (target >=0.85)
M2 >= 0.85 (target >=0.88)
real_llm_cases = 79/79
Validation = false during optimization
2025 Blind not used for optimization
```

### 最新正式 checkpoint

PR #189 已合入 Batch008/009 accepted fixes：

```text
Batch005 fixed-journal gated  M1 = 12/30   M2 = 18/48
Batch008 fixed-journal gated  M1 = 13/30   M2 = 20/48
Batch009 fixed-journal gated  M1 = 14/30   M2 = 21/48

Batch009 offline              M1 = 9/30    M2 = 15/48
```

Batch009：

```text
fixed-journal gated M1 = 14/30 = 46.67%
fixed-journal gated M2 = 21/48 = 43.75%
```

最后一个真实 fresh-provider checkpoint 仍是 Batch005：

```text
fresh gated M1 = 11/30
fresh gated M2 = 17/48
structured valid = 38/40
fallback = 2
transport failure = 0
scope rejection = 0
```

Batch008/009 是 immutable-journal、`network_calls=0` 的固定回放，不能冒充 fresh-provider gain。

### 已接受 / 已拒绝

已接受：

- Batch008 legacy Chinese cash statement / explicit Notes-column deterministic compatibility；
- Batch009 generalized Legal redemption/restoration lifecycle recognition，redemption-rights M1 `4/8 → 5/8`。

已拒绝并完整回滚：direct ranked concentration-table extraction candidate；它没有提高 canonical M1/M2，并使 supplier existence F1 `0.875 → 0.80`。**不得直接恢复该实现。**

### 当前 root 优先级

```text
1. retrieval candidate generation / ranking
2. exact page / anchor Evidence binding
3. remaining deterministic / numeric extraction
4. genuine conflict fail-closed
5. fixed-vs-fresh LLM / Evidence variance
```

`forensic_011` 中 retrieval candidate generation 仍是最大 proven first-failure layer：6 M1 / 16 M2 units。一个 redemption Evidence page 位于 rank 18，超出 Legal Agent bounded 10-item consumption；应优先优化 transaction/lifecycle co-occurrence ranking，而不是无界扩大 K。

### 执行模式

允许 autonomous multi-root wide sprint，但只针对 **proven、compatible** roots：

```text
scan all failures
→ complete funnel diagnosis
→ select several proven roots
→ independent subfix commits
→ targeted tests / controls
→ fixed-journal bundle benchmark
→ unit-level regression diff
→ partial revert only bad subfix
→ preserve BEST_KNOWN_GOOD
→ enlarge Development diagnostics
→ fresh checkpoint when justified
→ auto-continue
```

可以在同一轮组合 retrieval/ranking、exact Evidence binding、remaining numeric/deterministic、Legal variants、LLM stability 等已证明问题；不能把被拒绝的 ranked-table patch 原样重新打开。

fixed10 只做 microscope；有 meaningful gain 后尽快扩到 20/40/ALL79 Development。

## 3. Track B — Frontend / Product Experience（P0/P1）

当前已有稳定产品壳、Evidence Viewer、Market / Model 面板、Final Supervisor、Replay、发行人 catalog 快速匹配。

最终 UI 明确支持：

```text
1. Offline Demo Replay
2. Historical Governed IPO
3. Fresh New-IPO Analysis
```

统一展示：

```text
Document Risks / Evidence
Market-X
Model / SHAP
Conflict / Re-check
Final Supervisor
Report / Trace / Provenance
```

所有 channel 必须真实显示 `AVAILABLE / PARTIAL / UNAVAILABLE` 与 reason。Track B 可以先完成信息架构和状态语义，不必等待 C/D，但不能伪造尚未完成的动态值。

## 4. Track C — Dynamic Market-X（PASS / regression protection）

已有：438 个 governed frozen Market-X Core artifacts、final-three Market `3/3`、PIT-safe builder/schema/provenance contracts。

最终 resolver：

```text
issuer / stock / listing identity
→ validated governed cache / frozen artifact exists?
   ├─ yes → load
   └─ no  → governed historical/online source
             → PIT-safe Market-X builder
             → schema / identity / provenance / hash validation
             → optional governed cache
→ MarketContext
→ Market Skills
→ Final Supervisor / UI
```

“online”不绑定某一家数据商；要求是合法、受治理、PIT-safe、可追溯。合法历史不足时必须明确 `PARTIAL / UNAVAILABLE` 和 external-data boundary。

禁止目标 IPO post-listing data、Blind outcome、missing→0、final-three 值复制、unsourced proxy。

验收已通过：PR #191 合入后 strict audit 覆盖 562 governed cases，0 integrity
violation；438 frozen + 124 dynamic PIT，Model handoff `bound 550 / not_projectable 12`。
后续只做 regression protection 和授权 Extended 数据的可选本地物化。

## 5. Track D — Dynamic Model / Prediction / SHAP（P0）

当前 final-three Frozen Model `3/3 available` 已稳定，但主要依赖 receipt-bound per-case handoff。

最终产品必须：

```text
governed feature vector
+ final frozen model artifact/hash
+ feature manifest / alert policy
→ runtime inference (no retraining)
→ uncalibrated_model_score
→ frozen alert/classification policy
→ native pred_contrib / SHAP
→ ModelSignal
→ Final Supervisor / UI
```

治理决议已关闭、runtime 泛化仍开放：

1. A-owned `PROMOTE_V2` 正式决议：**PASS（PR #184 merged）**；
2. Dynamic inference runtime：满足 feature contract 就能推理，不再按 case_id 查询预生成结果。

若 promote v2，必须新建 versioned model/hash/feature manifest/alert policy/receipt/handoff；不覆盖旧 PR-F，也不再根据 2024 Validation 调参。SHAP 必须来自当前 inference。

V2 promotion package 已实现并通过 PR #184 正式生效：versioned freeze、strict receipt、checker 与 final-three label-free handoff 均已生成，current-main strict revalidation 通过，resume / fresh-directory byte-identical 已验证，34-alert 工作量与 ROC-AUC 仍低于 0.5 的局限已披露。旧 frozen PR-F 完整保留、可回滚。当前只剩真实 dynamic inference + native SHAP。

## 6. Track E — Final Integration / Release / Submission（P1 → 最后 P0）

从现在开始持续做 integration watch，只有 A/C/D 核心行为稳定后进入 final freeze。

Freeze 后：

```text
freeze code / config / prompt / schema / retriever / verifier / evaluator
freeze Market provider/schema identity
freeze model / feature / alert identity
record hashes
→ one-shot ALL19 Validation
→ no Validation-driven retuning
→ latest-main CI
→ Blind / PIT / provenance / determinism / security / licensing / path audits
→ artifact index
→ fresh clone
→ secure submission ZIP + SHA-256 manifest
```

Human Review UI/export 可以保留，但不是 Release Gate，不需要补 6 份人工 review。

## 7. Competition capability coverage

不再单独维护第六条开放式研发计划。以下作为 A/B/C/D 的横向验收：

- core pipeline progress；
- text embellishment；
- related-party transaction；
- comparable IPO valuation；
- Evidence screenshot；
- single/batch report；
- API/UI；
- Dynamic New-IPO proof。

无 Existing Gold 的能力标记 `QUALITATIVE DEMONSTRATION`，不混入 M1/M2。

## 8. 并行依赖

```text
Track A Document Intelligence ───────┐
                                     │
Track C Dynamic Market-X ────────────┼──→ Track D Dynamic Model / SHAP
                                     │              │
existing governed runtime ───────────┘              │
                                                    ▼
                                         Final Supervisor / Report
                                                    │
                                                    ▼
                                         Track B Final Frontend
                                                    │
                                                    ▼
                                         Track E Release / Submit
```

Track E 持续做 integration watch；Track B 不必等待 C/D 才优化结构，但不能通过 UI fake-fill 未完成能力。

## 9. Regression-protection 基线

任何分支都必须保护：

```text
E1 3/3
M3 1.0 x 3
Market final-three 3/3
Model final-three 3/3
17/17 recheck
17/17 precise screenshots
7/7 x 3 stages
canonical replay hash
fresh-clone readiness
```

## 10. Competition Ready

只有以下全部真实完成才允许声明：

```text
ALL79 M1 >=80%
+ ALL79 M2 >=85%
+ M3 =100%
+ Dynamic Market-X acceptable
+ formal D decision + Dynamic Model / SHAP acceptable
+ final frontend complete
+ capability demonstrations complete
+ one-shot Validation complete under freeze
+ latest-main CI / Blind / provenance / determinism / security / licensing PASS
+ fresh clone PASS
+ secure final package PASS
= COMPETITION_READY
```

任何 fixed10 提升、final-three UI green 或 replay PASS 都不能替代 Release Gate。
