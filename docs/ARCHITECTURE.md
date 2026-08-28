# Architecture — Current Runtime and Diagnostic Lanes

## 1. Production analysis path

```text
IPOAnalysisRequest
      ↓
Prospectus Parser
      ↓ DocumentChunk(page, text, optional bbox)
Retriever
      ↓ Evidence
Financial ─┬─ Legal ─┬─ Business
           └─────────┘
                 ↓
              Verifier
                 ↓
        Document Supervisor
                 ↓
Governed MarketContext + Skills
                 ↓
Optional authentic frozen model signal
                 ↓
Conflict Detection
                 ↓
bounded Targeted Re-check
                 ↓
Verifier Challenge
                 ↓
LLM Final Supervisor
+ deterministic fallback
                 ↓
Trace + Human Review + Report / UI
```

Final evaluation 位于 runtime 之后：

```text
Frozen Existing Gold + B artifacts
C market trace + D outcome artifacts + E final artifacts
→ M1 / M2 / M3 / M4 / M5
→ readiness / audits / package
```

## 2. Document boundary

### Parser

Parser 拥有 physical page identity。page、text 与 bbox 必须来自解析/Evidence layer；UI 不得猜测。

当前 page grounding 已可用，但 bbox / screenshot 尚未成为稳定主链。下一阶段需实现：

```text
Evidence ID
→ source PDF hash
→ physical page
→ upstream bbox 或唯一 exact quote match
→ highlighted screenshot
→ screenshot manifest / hash
```

多重匹配或无匹配时 fail closed，不画假框。

### Retriever

正式检索允许 keyword、domain-aware 和 Development-only 可消融的 lexical/hybrid 改造。禁止 Gold、公司、股票、case 或页码进入 runtime scoring。

### Financial

Financial 保持 deterministic-first。数值、期间、单位、比例和 Calculation 由 Python 负责；LLM 不覆盖已确定的权威数值。

### Legal / Business

LLM 只消费 bounded Evidence，输出受 Pydantic Schema 与 Evidence scope guard 约束。provider failure、scope rejection 或表达冲突不得无条件删除正确的 deterministic candidate。

## 3. Role-B v0.4.6 ablation lane

```text
same fixed Development subset
       ├─ offline: zero network baseline
       ├─ shadow: real LLM + journal, final canonical result = offline
       └─ gated: replay journal through agents, no extra network
```

身份绑定：

```text
code fingerprint
subset / Gold hash
provider / model / transport
Prompt / Schema hash
ordered Evidence IDs
runtime config hash
journal hash
```

输出：

- structured smoke；
- LLM call quality；
- retrieval waterfall；
- risk waterfall；
- monotonicity；
- failure focus。

下一步 instrumentation 需补齐 Parser、Builder、Normalization、Reconciliation、Verifier 和 final binding 的真实 lifecycle trace。

## 4. Market boundary

```text
pre-listing governed facts
→ MarketContext
→ deterministic Skills
→ optional bounded LLM interpretation
```

LLM 不能 mint market numbers。Core-only 合法；真实缺失合法；zero fill、未来行和未经证明的 proxy 不合法。

## 5. Model / Outcome boundary

Authentic frozen handoff 存在时，输出 `uncalibrated_model_score`、identity 和 signed drivers；缺失或 hash mismatch 时明确 unavailable。

Outcome evaluator 独立计算 1D / 5D / 20D / 60D，不把真实 outcome 反馈到分析 runtime。

## 6. Supervision

Final Supervisor 只能引用 in-scope Risk、Evidence、Conflict、Recheck 和 governed market/model signals；severity 不低于 deterministic verified-risk floor。

远程失败保留 deterministic fallback，但 fallback 不计 real-provider accepted。

## 7. Trace / M3

每个 relevant event 必须有：

```text
actor / action / tool or skill
Evidence / Calculation reference
或 explicit no_evidence_reason
```

远程 LLM 还需 provider、model、Prompt、request identity、response hash 和 latency。

## 8. Human Review / M4

Human Review 是独立 sidecar，不修改机器事实。每个 final case 至少两名独立真人评审；LLM 只能 advisory。

## 9. Evaluation and submission

```text
M1/M2 → Existing-Gold evaluator
M3 → trace accounting
M4 → human rubric
M5 → governed outcome evaluator
→ readiness / provenance / determinism / security
→ submission package
```

## 10. Current measured gaps

- B fixed-10 M1 `23.33%`、M2 `18.75%`；
- v0.4.6 full measured ablation pending；
- C strict Market contract `1/3`；
- E accepted `2/3`；
- M4 `0/6`；
- Evidence bbox / screenshots open；
- pipeline / text embellishment / related party / comparable valuation demonstrations incomplete；
- D artifact evidence exists but business predictive strength remains weak。
