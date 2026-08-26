# Architecture — Current v0.4.5 Competition Runtime

本文件描述**当前 main 已实现架构**，不是未来愿望清单。

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
              deterministic context
              + bounded LLM interpretation
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

## 2. Document boundary

### Parser

Parser 负责产生真实 physical page identity。当前 PyMuPDF 路径可以提供 page grounding；真实 2410.HK 测量显示 706/706 chunks 有 page，但 parser 尚未产生 bbox。

规则：

- UI 不得自己猜页码/bbox；
- 新增 bbox 必须由 parser/Evidence layer 产生；
- 因 bbox 会进入 Evidence content，改变 hash 时必须做 version/provenance review。

### Retriever / Evidence

Retriever 只负责把有限证据送给下游。LLM 不直接获得整份 700 页 PDF 的无限上下文。

正式语义链：

```text
Retriever
→ bounded Evidence
→ structured LLM candidate
→ Evidence ID scope validation
→ Risk Builder
→ Verifier
```

### Financial

Financial 保持 deterministic-first：表格/文本抽取、Calculation、规则判定由 Python 主导。LLM 不作为精确数学权威。

### Legal / Business

Legal / Business 可以调用 provider-neutral structured LLM：

- prompt identity registered；
- Pydantic response schema authoritative；
- invalid structured result 可以 bounded repair retry；
- out-of-scope Evidence reference fail closed；
- harmless vocabulary variants 可 canonicalize；
- genuine semantic conflict 不被吞掉。

## 3. Market boundary

生产数值来源是 governed Market-X，不是 legacy mock snapshot。

```text
Pre-listing governed facts
→ MarketContext
→ deterministic Skills
→ optional LLM qualitative interpretation
```

Market LLM 只能解释输入事实，不能 mint numeric market facts。

Core-only 情况合法：缺 Extended source 时 `MarketRegimeSkill` 可以 `INSUFFICIENT_DATA`/partial，不得 crash，也不得 zero-fill。

PIT-safe industry classification 不存在时，industry return 继续显式 blocked/missing。

## 4. Model boundary

模型通道只允许消费 authentic frozen PR-F evidence/handoff。

```text
available authentic handoff
→ uncalibrated_model_score + identity + optional signed SHAP

handoff absent / hash mismatch
→ Model Channel unavailable
```

不允许在线重新训练一个替代模型来“补通道”。

## 5. Competition supervision

### Conflict Detection

Competition conflict 是跨 named outputs 的分歧或覆盖缺口，不是一个 Agent 的普通 uncertainty。

当前策略包括：

- Agent assertion vs Verifier；
- unresolved bounded claim；
- Document internal conflict 上抬；
- document vs rule / market / model divergence（只有对应通道真实可用时）。

### Targeted Re-check

`RecheckRequest.max_attempts` schema 层固定为 1；同时 workflow 有总预算。超预算 conflict 显式保留 unresolved/not-attempted，不静默丢弃。

### LLM Final Supervisor

输入仅来自已结构化的 channel outputs、Evidence/Calculations、Conflict/Recheck result。

约束：

- 引用 ID 必须属于输入；
- overall severity 不能低于 deterministic verified-risk floor；
- 不凭空新增数值/概率；
- provider failure 时回退到 deterministic composition，并保留 unavailable reason。

针对 recoverable Responses transport failure，Final Supervisor 有受限 same-model chat JSON fallback；该 fallback 在 trace 中明确标识，不能冒充原 function call 成功。

## 6. Trace

`TraceEvent` 覆盖 parser/retriever/agent/skill/llm/verifier/market/model/conflict/recheck/supervisor/human_review。

每个事件应记录：

- case/run identity；
- actor/action/tool_or_skill；
- provider/model/prompt；
- Evidence/Calculation refs 或明确 no-evidence reason；
- conflict/recheck refs；
- latency/request/hash when available；
- status/details。

traceability 是从真实事件计算的最小覆盖值，不得硬编码 1.0。

当前三案例 offline matrix measured traceability 均为 1.0。

## 7. Human Review / Product boundary

Human Review 写独立 sidecar：

```text
machine result stays immutable
+ reviewer decision / note
→ review sidecar
```

Streamlit 只消费 service/runtime 输出，不在展示层修复后端事实。

当前五工作区：

1. 风险指挥中心；
2. Evidence 与 AI 分析；
3. 市场与模型；
4. Agent 协作轨迹；
5. 人机复核与最终报告。

## 8. Runtime modes

- `v045_competition_offline`：真实 PDF + deterministic/offline degradation，不发远端 LLM；
- `v045_competition_ai`：相同治理链 + configured remote provider；
- frozen `v04_*` baseline configs 不因 competition product 改名或静默替换。

## 9. Current measured limits

架构完整不等于效果达标。当前主要限制：

- B 10-case offline benchmark Risk P/R/F1 = 0%，Evidence Recall@5 = 20%；
- 2460/1318 已有 Evidence 但离线下没有正式风险项；
- final matrix 的 remote Final Supervisor 尚未验收；
- D multi-horizon final outputs 尚未闭合；
- parser bbox 尚未生成；
- authentic frozen PR-F per-case handoff 未恢复。

这些限制必须在产品/报告中显式呈现，不得由 UI 或 narrative 掩盖。
