# HK IPO Risk Agents — Current Architecture

> Status snapshot: **2026-08-25**  
> Baseline PR-A–PR-G: **COMPLETE / FROZEN**  
> Historical PR-H formal Gate: **PARTIAL / BLOCKED**  
> v0.4.5 competition runtime: **IMPLEMENTED / HARDENING**  
> Competition target: **v0.4.5 COMPETITION_READY**

## 1. Architecture form

项目保持模块化单体：一个仓库、一个主要 Python 应用，通过稳定 Pydantic Schema / Protocol 连接模块。当前 competition runtime 的真实执行顺序是：

```text
Streamlit / Report / Human Review
        ↓
IPOAnalysisService
        ↓
Parser / Retriever / Evidence
        ↓
Financial Agent ─ deterministic-first
Legal Agent     ─ bounded LLM semantics
Business Agent  ─ bounded LLM semantics
        ↓
Verifier / Document Supervisor
        ↓
governed Market-X
        ↓
IPOHeatSkill / MarketRegimeSkill
        ↓
MarketIntelligenceAgent ─ bounded LLM interpretation
        ↓
Rule + optional frozen ModelSignal
        ↓
deterministic ConflictDetector
        ↓
bounded TargetedRecheckRunner
        ↓
LLM Final Supervisor synthesis
        ↓
Agent / Tool / Evidence Trace
        ↓
Evidence Viewer / Human Review / Final Report
```

禁止反向依赖：Agent 不操作前端；UI 不直接修补 raw model/data facts；Parser 不依赖 Agent；Schema 不依赖具体实现。

## 2. Protected interfaces

```text
src/ipo_risk/schemas/
src/ipo_risk/agents/base.py
src/ipo_risk/parsers/base.py
src/ipo_risk/retrieval/base.py
src/ipo_risk/predictors/base.py
src/ipo_risk/providers/
src/ipo_risk/workflows/state.py
src/ipo_risk/services/analysis_service.py
src/ipo_risk/core/container.py
src/ipo_risk/domain/risk_codes.py
```

跨阶段修改必须单独审查并补 contract / regression tests。

## 3. Document runtime

```text
Prospectus PDF
→ DocumentParser
→ DocumentChunk(page / bbox / text / metadata)
→ Retriever
→ Evidence
→ Financial / Legal / Business Agents
→ LLM semantics where appropriate
→ deterministic Skills / Calculation
→ Verifier
→ Document Supervisor
```

规则：verified `RiskItem` 必须有 Evidence；精确数值由 deterministic code 计算；LLM unavailable 必须显式降级；failure/pending/needs_review 不 silent drop。

## 4. LLM provider boundary

LLM Provider 只处理 bounded semantic tasks：

```text
Legal clause semantics
Business commercialization/core-product semantics
Disclosure Tone bounded interpretation
MarketContext qualitative interpretation
Final Supervisor bounded synthesis
```

Provider output 必须 schema validate，并记录 model / prompt version / latency / request identity where available。LLM 不创造 Evidence、行情、数值计算、模型分数、case identity 或概率。

## 5. Market architecture

Frozen Core：

```text
schema  v04_ipo_market_context_features_v1
policy  ipo_market_context_policy_v1
15 raw + 15 missing indicators = 30 positions
438 / 438
```

Competition runtime：

```text
governed_pr_b_core
→ optional governed Extended readiness
→ MarketContextView
→ IPOHeatSkill
→ MarketRegimeSkill
→ MarketIntelligenceAgent
→ bounded qualitative LLM interpretation
```

### 5.1 Core-only contract

`market_extended_readiness` 是可选本地产物，默认空。Core-only 情况下，一些 Extended-only source feature 可能**完全不出现在** `MarketContextView.observations` 中。

Skill 缺失语义必须区分：

```text
MarketObservation exists + unavailable → preserve missing_reason
expected source feature absent          → source_unavailable
MarketObservation available             → use governed numeric value
```

缺少 HSI / volatility / turnover 时，`MarketRegimeSkill` 可以返回 `INSUFFICIENT_DATA`；这不是错误，也不能通过 zero-fill 变成可用。真实运行中发现的 `None.missing_reason` 集成缺陷已按这一 contract 修复并增加 regression tests。

### 5.2 Extended / industry policy

HSI / HKEX turnover 的 governed readiness 可以通过显式 local artifact 接入。Industry return 继续 `PIT_BLOCKED`，禁止静态行业映射、未来信息和 zero-fill。

## 6. Outcome architecture

Frozen 5D：

```text
PR-C FiveDayOutcomeTarget       424 available / 14 unavailable
PR-D canonical dataset          424 = 354 Dev + 70 Val
```

Competition sidecar 必须补：

```text
return_1d
return_20d
return_60d
```

与 frozen 5D 共同形成 1D/5D/20D/60D 验证。新 sidecar 不修改 PR-C frozen artifact。

## 7. Model architecture

Frozen PR-F remains auxiliary. Product 只消费原 frozen runtime/handoff：

```text
model/run identity
uncalibrated_model_score
signed drivers / SHAP
uncertainty metadata
```

若无法恢复：`ModelSignal.status = unavailable`。禁止 retrain/reconstruct 仅为 UI 解阻。

## 8. Multi-Agent / Supervisor architecture

当前已实现的受控协作路径：

```text
Agent / Document / Market / Rule claims
→ deterministic ConflictDetector
→ create bounded RecheckRequest
→ targeted re-retrieval
→ existing Verifier challenge where in scope
→ resolved / partially_resolved / unresolved conflict state
→ LLM Final Supervisor synthesis over governed inputs
```

`RecheckRequest.max_attempts = 1`；整轮还有受控 conflict budget。跨 Market/Model/Rule 且无法通过文档重新检索解决的冲突必须显式 unresolved，不允许叙述性“解决”。

LLM Final Supervisor 不能 mint 新 Risk/Evidence/Conflict id；越界引用会使 LLM synthesis 失效并退回 deterministic composition。

## 9. Trace architecture

Competition trace sidecar记录：

```text
agent_name / action
tool_or_skill
provider / model / prompt_version
evidence_ids / calculation_ids
conflict_id / recheck_id
latency / status
no_evidence_reason when applicable
```

Traceability 是度量值，不是硬编码声明。E-lane real case 已证明该指标会基于实际 Evidence 引用解析计算；最终 submission 仍需在 final case matrix 上重新测量。

## 10. Product architecture

当前 Competition UI 已收敛为五个工作区：

```text
风险指挥中心
Evidence 与 AI 分析
市场与模型
Agent 协作轨迹
人机复核与最终报告
```

Evidence Viewer 只使用 parser 产生的 page / bbox；Human Review 写独立 reviewer sidecar，不修改机器 `RiskItem`、Evidence 或原分析文件。UI 只消费 governed outputs，不通过 presentation layer 修正事实。

## 11. Failure / degradation architecture

Competition runtime 的原则不是“所有通道必须成功”，而是“任何失败都必须可见且不能污染其他通道”：

```text
Market Intelligence failure → retain deterministic governed MarketContext
LLM interpretation failure  → retain deterministic Skill result
LLM Final Supervisor failure → retain deterministic PR-G composition
Model runtime absent         → Model channel explicit unavailable
missing Extended feature     → source_unavailable / insufficient data
```

可恢复失败必须写结构化 diagnostics；安全降级不能被 UI 误标为对应 LLM 模块成功。

## 12. Five-person architecture ownership

```text
A  public contracts / integration / CI / release
B  Document LLM semantics / Evidence / benchmark
C  Market Skills / MarketContext / LLM interpretation
D  Outcomes / frozen ModelSignal / evaluation
E  Supervisor / conflict / trace / product
```

## 13. Reproducibility / artifact policy

Large runtime artifacts、licensed raw data、secrets 不进 Git。跨机器 handoff 必须验证 source revision + manifest + SHA256，并排除 Blind labels。

## 14. Time / Blind governance

```text
2020–2023  Development
2024       Validation
2025       Blind Test
```

2024 不重新作为 tuning set；2025 Blind y 未正式授权前禁止访问。
