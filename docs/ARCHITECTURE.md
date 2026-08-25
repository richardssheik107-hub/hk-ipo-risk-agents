# HK IPO Risk Agents — Current Architecture

> Status snapshot: **2026-08-25**  
> Baseline PR-A–PR-G: **COMPLETE / FROZEN**  
> Current Gate: **PR-H PARTIAL / BLOCKED**  
> Competition target: **v0.4.5 COMPETITION_READY**

## 1. Architecture form

项目保持模块化单体，一个仓库、一个主要 Python 应用，通过稳定 Pydantic Schema / Protocol 连接模块。最终比赛版结构：

```text
Streamlit / Report / Human Review
        ↓
IPOAnalysisService / controlled upper service
        ↓
Parser / Retriever / Evidence
        ↓
Financial Agent ─ deterministic math
Legal Agent     ─ LLM semantics
Business Agent  ─ LLM semantics
        ↓
Verifier
        ↓
Market Skills / MarketContext ─ LLM interpretation
        ↓
ModelSignal if frozen runtime available + Rule
        ↓
LLM Final Supervisor
        ↓
Conflict / targeted re-check / resolution / uncertainty
        ↓
Evidence Viewer / Agent Trace / Final Report
```

禁止反向依赖：Agent 不操作前端；UI 不直接读取任意 raw model/data files；Parser 不依赖 Agent；Schema 不依赖具体实现。

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

跨阶段修改必须单独审查并补 contract tests。

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
→ IPOAnalysisResult
```

规则：verified RiskItem 必须有 Evidence；精确数值由 deterministic code 计算；LLM unavailable 必须显式降级；failure/pending/needs_review 不 silent drop。

## 4. LLM provider boundary

LLM Provider 只处理 bounded semantic tasks：

```text
Legal clause semantics
Business commercialization/core-product semantics
Disclosure Tone bounded interpretation
MarketContext interpretation
Final Supervisor synthesis/conflict/re-check
```

Provider output 必须 schema validate，并记录 model / prompt version / latency / request identity where available。LLM 不创造 Evidence、行情、数值计算或模型分数。

## 5. Market architecture

Frozen Core：

```text
schema  v04_ipo_market_context_features_v1
policy  ipo_market_context_policy_v1
15 raw + 15 missing indicators = 30 positions
438 / 438
```

Competition runtime 增加：

```text
IPOHeatSkill
MarketRegimeSkill
optional ComparableIPOSkill
MarketContext
LLM Market interpretation
```

现有 HSI / HKEX turnover 可使用；industry return 继续 PIT-blocked，禁止静态映射和 zero-fill。

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

目标协作路径：

```text
Agent claim
→ Conflict
→ targeted re-retrieval
→ Skill / Agent rerun
→ Verifier challenge
→ Final Supervisor arbitration
→ resolved / partially_resolved / unresolved
```

不实现无限 autonomous loop；一次受控 re-check 为主，保证可审计和稳定。

## 9. Trace architecture

每次运行需能记录：

```text
agent_name
task
input_evidence_ids
tool_or_skill
llm_provider / model
structured_output
calculation_ids
verifier_status
conflict_id
recheck_action
final_status
latency
```

目标：Agent / Tool / Evidence traceability = 100%。

## 10. Product architecture

最终 Competition UI 只保留高价值工作区：

```text
Risk Command Center
Evidence + AI Analysis
Market & Model
Agent Trace
Human Review / Final Report
```

UI 只消费 governed outputs，不通过 presentation layer 修正事实。

## 11. Five-person architecture ownership

```text
A  public contracts / integration / CI / release
B  Document LLM semantics / Evidence / benchmark
C  Market Skills / MarketContext / LLM interpretation
D  Outcomes / frozen ModelSignal / evaluation
E  Supervisor / conflict / trace / product
```

## 12. Reproducibility / artifact policy

Large runtime artifacts、licensed raw data、secrets 不进 Git。跨机器 handoff 必须验证 source revision + manifest + SHA256，并排除 Blind labels。

## 13. Time / Blind governance

```text
2020–2023  Development
2024       Validation
2025       Blind Test
```

2024 不重新作为 tuning set；2025 Blind y 未正式授权前禁止访问。
