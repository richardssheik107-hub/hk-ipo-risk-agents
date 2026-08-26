# v0.4.5 Five-Person Execution Plan

本文件定义 A/B/C/D/E 的稳定 ownership、handoff 和完成标准。**不按日期排期**；状态以 `V0.4_RELEASE_ACCEPTANCE.md` 为准。

## 全队共同约束

- `RiskItem` 必须有真实 Evidence；需要精确计算时必须有 `Calculation`；
- LLM 只做语义与综合，不是权威计算器；
- Market 数值只能来自 PIT-governed 输入；缺失显式 missing；
- 2024 Validation 不作为调参集；2025 Blind y 未授权前不访问；
- frozen PR-A–PR-G 不为比赛展示而回写；
- PR-F authentic handoff 不存在时 Model Channel = unavailable；
- 公共 contract 只允许兼容式扩展，shared files 由 A 审核；
- 每个 PR 都应小而可验证，不允许五个人同时“全仓集成”。

## A — Tech Lead / Integration / Release / Submission

### 已完成

- `competition_runtime_v1` 公共 sidecar contract；
- `Conflict / RecheckRequest / TraceEvent / HumanReview` runtime boundary；
- LLM provider observability / Responses metadata；
- network-free competition runtime CI gate；
- C Market Intelligence → v0.4 AI runtime wiring；
- Market missingness / trace / Final Supervisor transport/UI integration hardening；
- 3-case runner 所需的跨 lane 集成已进入 main；
- 本轮 active documentation audit / stale-doc pruning。

### 剩余职责

- B/C/D/E PR 的 contract review、CI、real smoke、merge；
- 保持当前 Gate 文档与 main 同步；
- 最终 artifact completeness / blind / provenance / determinism audit；
- RUNBOOK、release notes、submission archive；
- 决定 `COMPETITION_READY` 是否可使用。

### A 禁区

A 不替 B 改语义阈值，不替 C 发明市场数据，不替 D 重训 PR-F，不替 E 在 UI 造 Supervisor 结果。

## B — LLM Document Intelligence

### Owner 范围

Legal：

- `redemption_rights`；
- `material_litigation_compliance`；
- versioned competition extension（如 related-party）只能做 sidecar/additive，不改 frozen baseline code identity。

Business：

- `precommercial_product`；
- core product / commercialization / pipeline / revenue semantics；
- disclosure tone 等扩展只能 Evidence-grounded、versioned。

Evidence：

- Retriever → Evidence → structured LLM extraction；
- Evidence ID scope validation；
- optional parser bbox grounding。

### 当前实测

10-case Development governed offline benchmark：

```text
Risk P/R/F1        0 / 0 / 0
Evidence Recall@5  20%
Real LLM cases     0
```

因此 B 当前是**第一质量 blocker**。

### 下一交付

- 固定同一 Development benchmark 的 real-LLM run；
- Risk / Evidence benchmark artifacts；
- error taxonomy：retrieval / semantic / reconciliation / verifier / ranking；
- Development-only 最小 remediation；
- Before/After / Offline-vs-AI 证据；
- 若做 bbox：与 A 明确 version/hash 影响后再改 parser。

### Handoff → E/A

`AgentResultEnvelope + risk_ids + evidence_ids + structured diagnostics + provider metadata`。

## C — Market Intelligence

### 已完成主体

- governed MarketContext；
- IPOHeatSkill；
- MarketRegimeSkill；
- bounded Market LLM interpretation；
- explicit PIT/missingness；
- Trace / Final Supervisor compatible handoff；
- 正式 AI runtime wiring；
- 两只真实 IPO 的 real-provider Market LLM validation。

### 剩余交付

- 在 final 3-case environment 验证 Market Core artifact consumption；
- Core-only 与 Extended 两种配置的诚实降级；
- namespaced market evidence/trace 完整；
- 不可用 industry feature 保留 PIT-blocked reason。

### 当前不做

- 没有 frozen PIT-safe 定义时不做 `ComparableIPOSkill`；
- 不用行业静态映射伪装历史 PIT；
- 不用 zero/proxy 填 missing market values。

### Handoff → E/A

`MarketContext + deterministic skill outputs + bounded interpretation + trace provenance`。

## D — Outcome / Model / Evaluation

### 已有基础

- 1D/5D/20D/60D outcome foundation；
- chronological split/blind guard；
- frozen PR-C 5D；
- frozen PR-E/PR-F research evidence。

### 当前缺口

最终比赛结果包尚未关闭，因此 D 是**第一交付 blocker**。

### 下一交付

```text
return_1d
return_5d
return_20d
return_60d

test_predictions.csv
multi_horizon_results.csv
evaluation_summary.json
ai_vs_offline_report.json
```

如 authentic frozen PR-F handoff 可恢复，则额外提供：

- per-case `uncalibrated_model_score`；
- model/run identity；
- checksum；
- top signed SHAP drivers。

不可恢复则明确 `ModelSignal.status=unavailable`，不重训替代。

### Handoff → E/A

`multi-horizon outcomes + evaluation artifacts + optional authentic ModelSignal`。

## E — LLM Final Supervisor / Multi-Agent / Product

### 已完成主体

- LLM Final Supervisor；
- deterministic conflict policy；
- one bounded targeted re-check；
- Verifier challenge / resolution states；
- Agent / Tool / Evidence trace；
- Human Review；
- Evidence Viewer；
- 五个 Streamlit workspaces；
- 3/3 real-PDF offline matrix；
- 三案例 measured traceability = 1.0。

### 剩余交付

- final 3-case matrix 上 real-provider Final Supervisor synthesis；
- 保存 provider/model/prompt/request/hash/latency trace；
- 验证 out-of-scope reference fail closed；
- 接入 B/C/D 最终真实结果后做 UI smoke；
- submission-facing case reports / reasoning logs。

### E 禁区

- 不补写 B 没抽出的 RiskItem；
- 不补 C 缺失的市场事实；
- 不生成 D 不存在的模型分数；
- 不在 UI 伪造 bbox。

## Handoff graph

```text
B → AgentResult / Risk / Evidence / diagnostics ┐
C → MarketContext / market interpretation       ├→ E Final Supervisor / Trace / Product
D → Outcome / ModelSignal / evaluation          ┘

A → contracts / config ownership / CI / integration / release
E → final product artifacts → A final Gate
```

## Shared-file ownership

- schemas / registry / global config / analysis service / CI：A writer，相关 role reviewer；
- Legal/Business semantic internals：B；
- Market skills/agent internals：C；
- outcome/model/evaluation：D；
- final supervisor/trace/product UI：E；
- `streamlit_app`：E writer，A integration reviewer；
- frozen completion reports/manifests：原则上无人修改。

## Team completion condition

```text
B real-LLM benchmark + quality evidence
AND D multi-horizon submission package
AND E real-provider final matrix
AND A final CI/runbook/submission freeze
→ COMPETITION_READY
```
