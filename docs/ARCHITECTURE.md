# HK IPO Risk Agents — Current Architecture

> Status snapshot: **2026-08-23**  
> Document baseline: **v0.3 RELEASED / FROZEN**  
> PR-A / PR-B / PR-C / PR-D: **COMPLETE / FROZEN**  
> Oracle v2: **COMPLETE / FROZEN / EVALUATION-ONLY**  
> Current formal Gate: **PR-E — Baseline + Oracle Diagnostic**

## 1. Architecture form

项目保持模块化单体：一个仓库、一个主要 Python 应用，通过稳定 Pydantic Schema / Protocol 连接模块。

当前不引入与闭环无关的 Kafka、Redis queue、Neo4j、Kubernetes 或微服务拆分。

核心依赖方向：

```text
Streamlit / Report
        ↓
IPOAnalysisService / controlled upper service
        ↓
Document Workflow
        ↓
Parser / Retriever / Domain Agents / Skills / Verifier / Document Supervisor
        ↓
IPOAnalysisResult
        ↓
Document Snapshot / Production Document X
        ↓
Market-X Core (+ optional governed Extended)
        ↓
Outcome / Canonical Modeling Dataset
        ↓
Baseline / Advanced Model / Explainability
        ↓
Market Agent / Final Supervisor
        ↓
Final Report / UI
```

禁止反向依赖：Agent 不操作前端；Schema 不依赖具体实现；Parser 不依赖 Agent；UI 不直接读取内部 raw model/data files。

## 2. Protected interfaces

以下边界视为受保护接口，跨阶段修改必须单独审查：

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

新增 real component 需要 contract test，并通过 ComponentRegistry / controlled wiring 注册；不允许绕过 service boundary 从 UI 直接调用内部模块。

## 3. Production Document runtime

```text
Prospectus PDF
→ DocumentParser
→ DocumentChunk(page / bbox / text / metadata)
→ Stable Retriever
→ Evidence
→ Financial / Legal / Business Agents
→ Deterministic Skills / Calculation
→ Specialized Verifier
→ Document Supervisor
→ IPOAnalysisResult
```

原则：

- 正式风险必须由 Evidence 支持；
- 数值结论由 deterministic code 计算；
- LLM unavailable 必须显式降级，不能伪造成成功；
- Verifier / Supervisor 不创造原始 Evidence；
- failure / pending / needs_review 不得 silent drop。

## 4. Frozen Document modeling boundary

PR-A 已冻结：

```text
IPOAnalysisResult
→ V03DocumentRiskSnapshot
→ v04_document_features_v1
→ Production Document X
```

结果：

```text
438 / 438 authoritative snapshots
438 / 438 Production Document-X
100 dimensions
0 Production failures
0 silent drops
```

Production feature vector 是结构化模型输入，不等于 PDF 全文；Evidence / page provenance 通过 source analysis / risk chain 保留。

## 5. Market architecture

### Market-X Core — frozen

```text
schema  v04_ipo_market_context_features_v1
policy  ipo_market_context_policy_v1
15 raw + 15 missing indicators = 30 positions
```

Core 只消费 listing 前已知且受治理的信息，并通过 PIT validation 防止目标 IPO 的上市后数据进入 X。

### Market-X Extended — optional

HSI、authoritative industry benchmark mapping/history、HK total-market turnover 等 source family 仍可显式 missing。缺失来源不能用不等价 proxy、fake benchmark 或 neutral zero 替代。

## 6. Outcome and canonical dataset

PR-C：

```text
FiveDayOutcomeTarget
424 available / 14 explicit unavailable
Development threshold fitted only on 2020–2023
```

PR-D：

```text
Document X + Market X + Outcome Y
→ v04_canonical_modeling_dataset_v1
→ 424 model-ready
→ 354 Development + 70 Validation
```

Feature groups 显式版本化，identifier / document ID / Evidence ID / Gold page / target-derived value 不得进入 X。

## 7. Production / Oracle separation

Production：最终产品路径。

Oracle：研究旁路。

```text
Reviewed Expert Gold
→ Oracle v2 feature builder
→ expert_oracle_document_features_v2
```

Oracle v2 frozen contract：

```text
98 materialized
96 strict usable
77 Development / 19 Validation
142 features
evaluation_only = true
production_consumable = false
```

Oracle 不 import 到 Production runtime，不替代 Retriever / Agent 结论，不把 Expert Gold 反向泄漏进 Production X。

## 8. PR-E modeling architecture

Full Production cohort：

```text
M   Market only
P   Production Document only
PM  Market + Production
```

Oracle fair intersection：

```text
M   Market only
P   Production Document only
O   Oracle Document only
PM  Market + Production
OM  Market + Oracle
```

Development evaluation：expanding-year forward chaining。Validation：2020–2023 fit → untouched 2024 evaluation。

PR-E output 是研究 / model artifact；在稳定 schema、score semantics、calibration status 冻结前，不直接暴露为产品“概率”。

## 9. PR-F / PR-G / PR-H architecture boundary

PR-F：在 PR-E frozen inputs / cohorts 上增加 LightGBM、SHAP / importance、calibration assessment、ablation、error analysis。

PR-G：

```text
Document Supervisor
+ Market Agent
+ Model prediction / explanation
→ Final Supervisor
```

Final Supervisor 只能引用已有 risk / Evidence / market facts / model drivers，不能创造新 Evidence 或把 model score 当 Evidence。

PR-H：Streamlit 通过受控 service 完成 PDF → Final Report，不在 UI 内复制模型、Retriever 或 Agent 逻辑。

## 10. Reproducibility and runtime artifacts

大型 generated runtime artifacts 默认不提交 Git；Git 保存代码、tests、frozen manifests、small reports 和 hashes。跨机器 handoff 必须验证 source revision / manifest / SHA，而不是把任意本地文件当 source of truth。

## 11. Time and blind governance

```text
2020–2023  Development
2024       Validation
2025       Blind Test
```

2025 Blind y 在正式打开前禁止用于模型、阈值、feature、Retriever、Prompt、LLM 或 Oracle 调优。Competition Hardening 不自动授权读取 Blind y。
