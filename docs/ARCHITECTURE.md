# Architecture — Current v0.4.5 Competition Runtime

本文件描述当前 v0.4.5 runtime 架构，以及 final competition evaluation 如何在 runtime 之外消费受治理 artifact。业务 runtime 不因 Metric Protocol v2 而被静默改写。

## 1. Runtime overview

```text
IPOAnalysisRequest
      │
      ▼
Prospectus Parser
      │ DocumentChunk(page, text, optional bbox)
      ▼
Retriever
      │ Evidence
      ├───────────────┬────────────────┐
      ▼               ▼                ▼
Financial Agent   Legal Agent     Business Agent
(det-first)       (structured LLM) (hybrid + LLM)
      │               │                │
      └───────────────┴────────────────┘
                      ▼
                   Verifier
                      ▼
              Document Supervisor
                      │
                      ├──────────────► Rule signal
                      │
Governed Market-X ───► MarketContext
                      ▼
                 IPOHeatSkill
                 MarketRegimeSkill
                      ▼
              Market Intelligence
                      │
Optional authentic   │
frozen PR-F signal ──┤
                      ▼
              Competition Supervisor
                      │
              Conflict Detection
                      ▼
          bounded Targeted Re-check
                      ▼
              Verifier Challenge
                      ▼
             LLM Final Supervisor
             (deterministic fallback)
                      ▼
           Trace + Human Review + Report
                      ▼
               Streamlit / exports
```

Final competition evaluation 位于 runtime 之后：

```text
Frozen Existing Expert Gold ──read-only──┐
B Document artifacts                     │
C Market trace                           ├→ Metric Protocol v2 evaluator / A readiness
D Outcome artifacts                      │
E Final artifacts                        ┘
                                         ↓
                              M1 / M2 / M3 / M4 / M5
                                         ↓
                         Blind / provenance / determinism / package
```

`COMPETITION_METRIC_PROTOCOL.md` 定义 evaluator 口径，不允许反向篡改 runtime 或 Existing Expert Gold。

## 2. Document boundary

### Parser

Parser 负责真实 physical page identity。当前 PyMuPDF 路径可以提供 page grounding；2410.HK 已测 706/706 chunks 有 page，但 parser 尚未产生 bbox。

规则：

- UI 不得猜页码/bbox；
- 新增 bbox 必须由 parser/Evidence layer 产生；
- bbox 改变 Evidence content/hash 时必须做 version/provenance review。

### Retriever / Evidence

正式链：

```text
Retriever
→ bounded Evidence candidates
→ structured LLM candidate
→ Evidence ID scope validation
→ Risk Builder
→ Verifier
```

Metric-v2 对这条链分层评价：

```text
Candidate Recall@20              diagnostic target >=0.95
Reranked Recall@10               diagnostic target >=0.90
Existing-Gold Evidence Coverage  official-aligned M2 >=0.85
```

Primary Evidence Gate 不固定 Top-5。Recall@1/@3/@5/@10/@20 用来定位 retrieval/ranking 问题。

M2 Gold 只来自比赛收尾前已经存在的 Expert Annotation / valid audit overlay。允许 deterministic normalization / exact duplicate anchor dedupe；不新增人工 Evidence，不人工重做 semantic Evidence Group。

### Financial

Financial 保持 deterministic-first：表格/文本抽取、Calculation、规则判定由 Python 主导。LLM 不作为精确数学权威。

Competition-priority `customer_concentration`、`supplier_concentration`、`cash_burn_pressure` 只在 Existing Gold 有明确 support 时进入 M1；metric mapping 不修改 frozen internal identity。

### Legal / Business

Legal / Business 使用 provider-neutral structured LLM：prompt identity、Pydantic schema、bounded repair、Evidence scope guard、canonical normalization、semantic conflict fail-closed。

`related_party_transaction` 若用于 runtime，只允许 additive/versioned sidecar；Metric-v2 不为其新增人工 Gold。Existing Gold support=0 时仅 `NOT_EVALUABLE_FROM_EXISTING_GOLD`。

## 3. Market boundary

```text
Pre-listing governed facts
→ MarketContext
→ deterministic Skills
→ optional LLM qualitative interpretation
```

Market LLM 只能解释输入事实，不能 mint numeric market facts。Core-only 合法；Extended 缺失时保持 partial/INSUFFICIENT_DATA；PIT-safe industry mapping 不存在时继续 blocked/missing。

## 4. Model boundary

```text
available authentic frozen handoff
→ uncalibrated_model_score + identity + optional signed SHAP

handoff absent / hash mismatch
→ Model Channel unavailable
```

不允许为 UI 或 M5 临时重训替代模型。

## 5. Competition supervision

Conflict Detection 覆盖 Agent assertion vs Verifier、unresolved bounded claim、Document internal conflict，以及真实可用通道之间的 divergence。

`RecheckRequest.max_attempts=1`，workflow 还有总预算；超预算 conflict 显式 unresolved/not-attempted。

LLM Final Supervisor 输入仅来自结构化 outputs、Evidence/Calculations、Conflict/Recheck result；引用必须 in-scope，severity 不低于 deterministic verified-risk floor，provider failure 保留 deterministic fallback。fallback 不计 E1 successful remote arbitration。

## 6. Trace / M3

`TraceEvent` 覆盖 parser/retriever/agent/skill/llm/verifier/market/model/conflict/recheck/supervisor/human_review。

relevant event 必须有 actor/action/tool identity，并有 Evidence / Calculation reference 或 explicit `no_evidence_reason`。远程 LLM 还保留 provider/model/prompt/request/hash/latency。

Metric-v2 M3：

```text
Development real-LLM traceability =1.0
final 3-case real-provider traceability =1.0
```

当前 3-case offline matrix 已测 1.0 / 1.0 / 1.0。

## 7. Human Review / M4

Human Review 写独立 sidecar，不修改机器事实。M4 沿用当前 final product explanation-quality 方案；本次 Existing-Gold-only M1/M2 scope freeze 不增加新的人工 Gold 任务。

## 8. Runtime modes

- `v045_competition_offline`：真实 PDF + deterministic/offline degradation；
- `v045_competition_ai`：相同治理链 + configured remote provider；
- frozen baseline configs 不被 competition metric 静默替换。

## 9. Evaluation boundary / M1-M5

Metric Protocol v2 是 evaluation contract，不是 runtime schema replacement：

```text
M1 Existing-Gold Risk Accuracy >=0.80
M2 Existing-Gold Evidence Coverage Recall >=0.85
M3 Traceability =1.0
M4 current Explanation rubric
M5 1D/5D/20D/60D, primary significant_drop_5d = return_5d <= -0.10
```

M1/M2 的提升手段只允许是 Development 上的 Retriever / Prompt / structured extraction / normalization / RiskItem reconciliation / Verifier 优化，不允许通过新增 Gold 改变分母。

## 10. Current measured limits

- B 旧 10-case offline：Risk P/R/F1=0%，Evidence Recall@5=20%，Real LLM=0；
- 该 Recall@5 是 legacy diagnostic，不等于 M2 official-aligned current value；
- Existing-Gold evaluable manifest 尚未生成；
- final 3-case remote Final Supervisor 尚未 acceptance；
- D M5 final outputs 尚未闭合；
- parser bbox 尚未生成；
- authentic frozen PR-F per-case handoff 未恢复。

这些限制必须显式呈现，不得由 UI 或 narrative 掩盖。
