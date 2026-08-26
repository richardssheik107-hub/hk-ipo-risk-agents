# Architecture — Current v0.4.5 Competition Runtime

本文件描述当前 v0.4.5 runtime 架构，以及 final competition evaluation 如何在 runtime 之外消费受治理 artifact。业务 runtime 不因 Metric Protocol v1 而被静默改写。

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

Final competition evaluation 位于上述 runtime 之后：

```text
B Document artifacts ┐
C Market trace       ├→ Metric Protocol v1 evaluator / A readiness
D Outcome artifacts  │
E Final artifacts    ┘
                    ↓
M1 / M2 / M3 / M4 / M5
                    ↓
Blind / provenance / determinism / package
```

`COMPETITION_METRIC_PROTOCOL.md` 定义 evaluator 口径，不允许反向篡改 runtime 的 frozen business truth。

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

Metric-v1 对这条链分层评价：

```text
Candidate Recall@20        diagnostic target >=0.95
Reranked Recall@10         diagnostic target >=0.90
Evidence Group Coverage    official-aligned M2 >=0.85
```

Primary Evidence Gate 不固定 Top-5。Recall@1/@3/@5/@10/@20 用来定位 retrieval/ranking 问题。

### Financial

Financial 保持 deterministic-first：表格/文本抽取、Calculation、规则判定由 Python 主导。LLM 不作为精确数学权威。

Metric-v1 的 `customer_concentration`、`supplier_concentration`、`cash_burn_pressure` 可以消费现有 Financial 输出；metric family mapping 不修改 frozen internal code identity。

### Legal / Business

Legal / Business 使用 provider-neutral structured LLM：prompt identity、Pydantic schema、bounded repair、Evidence scope guard、canonical normalization、semantic conflict fail-closed。

`related_party_transaction` 如用于 competition metric，只允许 additive/versioned sidecar，不静默改 frozen baseline registry。

## 3. Market boundary

```text
Pre-listing governed facts
→ MarketContext
→ deterministic Skills
→ optional LLM qualitative interpretation
```

Market LLM 只能解释输入事实，不能 mint numeric market facts。

Core-only 合法；Extended 缺失时保持 partial/INSUFFICIENT_DATA；PIT-safe industry mapping 不存在时继续 blocked/missing。

## 4. Model boundary

```text
available authentic frozen handoff
→ uncalibrated_model_score + identity + optional signed SHAP

handoff absent / hash mismatch
→ Model Channel unavailable
```

不允许为 UI 或 M5 临时重训替代模型。

## 5. Competition supervision

### Conflict Detection

覆盖 Agent assertion vs Verifier、unresolved bounded claim、Document internal conflict、以及真实可用通道之间的 divergence。

### Targeted Re-check

`RecheckRequest.max_attempts=1`，workflow 还有总预算；超预算 conflict 显式 unresolved/not-attempted。

### LLM Final Supervisor

输入仅来自已结构化 outputs、Evidence/Calculations、Conflict/Recheck result。

约束：

- 引用 ID 必须 in-scope；
- severity 不低于 deterministic verified-risk floor；
- 不凭空新增数值/概率；
- provider failure 保留 deterministic fallback/unavailable reason。

fallback 是正确降级，但不计 E1 successful remote arbitration。

## 6. Trace / M3

`TraceEvent` 覆盖 parser/retriever/agent/skill/llm/verifier/market/model/conflict/recheck/supervisor/human_review。

relevant event 必须有 actor/action/tool identity，并有 Evidence / Calculation reference 或 explicit `no_evidence_reason`。远程 LLM 还保留 provider/model/prompt/request/hash/latency。

traceability 从真实事件计算，不硬编码。

Metric-v1 M3：

```text
Development real-LLM traceability =1.0
final 3-case real-provider traceability =1.0
```

当前 3-case offline matrix 已测 1.0 / 1.0 / 1.0。

## 7. Human Review / M4

Human Review 写独立 sidecar，不修改机器事实。

Metric-v1 最终额外要求 explanation-quality artifact，由至少 2 名人类 reviewer 对：

```text
Evidence grounding
Logical consistency
Conflict handling
Re-check quality
Final conclusion
```

评分。LLM reviewer 只能辅助。

## 8. Runtime modes

- `v045_competition_offline`：真实 PDF + deterministic/offline degradation；
- `v045_competition_ai`：相同治理链 + configured remote provider；
- frozen baseline configs 不被 competition metric 静默替换。

## 9. Evaluation boundary / M1-M5

Metric Protocol v1 是 evaluation contract，不是 runtime schema replacement：

```text
M1 Risk Accuracy >=0.80 + internal anti-gaming guardrails
M2 Evidence Group Coverage Recall >=0.85
M3 Traceability =1.0
M4 Explanation internal rubric
M5 1D/5D/20D/60D, primary significant_drop_5d = return_5d <= -0.10
```

赛题没有规定 Top-5 Evidence 或 5D -10% 为官方公式；这些属于 project predeclared protocol。

## 10. Current measured limits

- B 旧 10-case offline：Risk P/R/F1=0%，Evidence Recall@5=20%，Real LLM=0；
- 该 Recall@5 是 legacy diagnostic，不等于 M2 official-aligned current value；
- 2460/1318 有 Evidence 但 offline 下未形成 formal risk；
- final 3-case remote Final Supervisor 尚未 acceptance；
- M4 explanation-quality artifact 尚未产生；
- D M5 final outputs 尚未闭合；
- parser bbox 尚未生成；
- authentic frozen PR-F per-case handoff 未恢复。

这些限制必须显式呈现，不得由 UI 或 narrative 掩盖。
