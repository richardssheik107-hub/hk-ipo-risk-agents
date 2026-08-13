# v0.3.5 Evidence Intelligence Architecture Plan

本文只记录未来内部设计，不修改当前公共 Schema、Protocol 或 v0.3 生产行为。

## 当前瓶颈

v0.3 采用一次 PDF parse 和统一前置检索：

```text
PDF -> Parser -> static/shared retrieval -> Shared Evidence
    -> Financial / Legal / Business Agents
```

一个固定共享 Top-K 无法同时满足不同章节、语言、证据形态和完整性要求，形成
information bottleneck 与 recall ceiling。

## v0.3.5 目标架构

```text
PDF -> Parser -> Shared Prospectus Index
                   |-> Financial Search Tool -> Financial Agent
                   |-> Legal Search Tool     -> Legal Agent
                   `-> Business Search Tool  -> Business Agent
                                                -> Evidence Completeness
                                                -> Verifier -> Supervisor -> Report
```

核心原则：`Shared document, not shared single retrieval result`。PDF 只解析一次，
三个 Agent 不重复 parse。

## Shared Prospectus Index

未来内部索引应支持 physical page、chunk、section/table metadata、keyword/semantic
search、page/section filtering。具体存储与检索算法尚未冻结。

## Domain-specific retrieval

规划 `FinancialSearchStrategy`、`LegalSearchStrategy` 和
`BusinessSearchStrategy`。每个策略可以独立定义 query families、preferred
sections、source authority、Top-K、table preference 和 semantic mode。

## Bounded iterative retrieval

每个风险最多三轮：

1. broad discovery；
2. missing-fact retrieval；
3. contradiction / confirmation。

禁止无限 autonomous loop。

未来内部建议模型（本轮不进入公共 Schema）：

```text
EvidenceSearchRequest:
  agent, risk_code, round, required_fact, query,
  preferred_sections, preferred_source_authority, top_k, reason

EvidenceSearchResult:
  evidence, coverage_status, missing_facts, conflicts
```

## Evidence Completeness

Completeness 不等于 `has_evidence=true`，而是 required facts 是否齐全。例如：

- cash_runway：cash、operating cash flow、comparable period、currency、unit；
- redemption_rights：right nature、holder/obligor、current status、termination、restoration；
- precommercial_product：core product、stage、product-sales status。

未来 Supervisor 可以请求 targeted retry，但不得创造 Evidence、绕过 Verifier 或
直接修改事实。

## A/B 评测

- Arm A：v0.3 static/shared retrieval；
- Arm B：v0.3.5 domain-specific + bounded iterative retrieval。

保持相同 PDF、LLM、risk policy、Verifier 和 Expert Golden。至少报告 Applicable
Risk Recall、Candidate/Verified Recall、Primary Evidence Hit Rate、Any-valid
Evidence Recall@K、Required Evidence Completion、rounds、calls、tokens、latency。

Keyword/Embedding/Hybrid/Reranker/Table-aware 的算法选择延后到 Phase 0.9；当前先
解决 who searches、what 和 when。
