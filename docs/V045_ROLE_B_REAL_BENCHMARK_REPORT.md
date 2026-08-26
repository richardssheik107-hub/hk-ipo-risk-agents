# ROLE B — OFFLINE GOVERNED DEVELOPMENT BENCHMARK

## FAIL — legacy diagnostic baseline, not metric-v1 final benchmark

> Historical evaluator version: `v045_role_b_real_document_benchmark_v1`
>
> Current competition metric protocol: `v045_competition_metric_protocol_v1`

本报告保留 10-case offline governed benchmark 的原始实测事实。`COMPETITION_METRIC_PROTOCOL.md` 发布后，本报告中的 Risk P/R/F1、Evidence Recall@K 仍保持原始语义，但**不再把 `Evidence Recall@5` 直接解释为赛题官方“关键证据片段召回率 >=85%”的唯一公式**。

赛题没有规定 Top-K；metric-v1 最终 M2 使用 Evidence Group Coverage Recall。当前报告因此是：

```text
input/runtime governance evidence
+ offline extraction/retrieval diagnostic baseline
!= real-LLM metric-v1 competition benchmark
```

## 1. Measured results

```text
PDFs requested:                 10
PDFs located:                   10
SHA verified:                   10
Page counts verified:           10
Cases analyzed:                 10
Cases evaluated:                10
Offline governed cases:         10
Real LLM cases:                  0

Risk Precision:              0.0%
Risk Recall:                 0.0%
Risk F1:                     0.0%

Evidence Recall@1:          20.0%
Evidence Recall@3:          20.0%
Evidence Recall@5:          20.0%
Evidence Precision@5:       NOT AVAILABLE
Physical-page correctness: 100.0%

Evidence out-of-scope:          0
Schema-invalid LLM results:     0
Needs Review:                   0
Verifier rejected:              0
Extraction failed:              0
Provider unavailable/offline:  10

2024 Validation opened:       NO
2025 Blind accessed:          NO
API key accessed:             NO
Network model calls:           0
Evidence egress:                0
```

旧 evaluator 当时输出：

```text
Risk target >=80%:           FAIL
Evidence target >=85%:       FAIL
```

这两个 legacy bool 只能表示“旧 evaluator 按当时 frozen semantics 未达到其 target”。它们**不能单独证明/否定 metric-v1 最终 M1/M2**，因为：

- M1 metric-v1 使用 5 个 competition primary risk families 的 positive Gold Risk Unit Accuracy + anti-gaming guardrails；
- M2 metric-v1 使用 Evidence Group Coverage Recall，而不是固定 Recall@5；
- 当前 run 没有真实 LLM 调用。

无论采用旧还是新协议，本次 offline 结果都不能证明比赛质量达标。

## 2. Governed streaming run

数据来自现有 competition ZIP；runner 一次只流式 staging 当前年度 ZIP 和当前 PDF，不展开完整数据集。每个 PDF identity 均来自 `data/catalog/ipo_prospectus_manifest.csv`，并通过 filename / byte size / SHA-256 / stock/case identity / one-based physical page count 校验。

没有读取 2024/2025 member，也没有访问 Golden 生成 prediction。

## 3. Prediction/Gold isolation

Prediction generation 只读取 allowlist、catalog、frozen configuration、当前 PDF，并强制：

```text
runtime_mode = offline
use_mock = false
parser = pymupdf
retriever = keyword
legal_agent = v03
business_agent = v03
verifier = specialized_v03
llm_provider = unavailable
market_data_provider = unavailable
market_context = none
final_supervisor = none
```

预测先冻结，evaluator 后打开 formal Human Golden。Persisted JSONL 不包含 Evidence/page body、chunk、prompt 或 response。

```text
OFFLINE GOVERNED BENCHMARK != REAL LLM BENCHMARK
```

## 4. Legacy per-risk metrics

| Risk | Golden cases | Risk Precision | Risk Recall | Risk F1 | Evidence Recall@5 |
|---|---:|---:|---:|---:|---:|
| `redemption_rights` | 4 | 0.0% | 0.0% | 0.0% | 0.0% |
| `material_litigation_compliance` | 4 | 0.0% | 0.0% | 0.0% | 0.0% |
| `precommercial_product` | 2 | 0.0% | 0.0% | 0.0% | 50.0% |

Offline provider produced one Role-B RiskItem：`ipo_2020_01167/precommercial_product`，带 9 个 bounded Evidence refs。Frozen Human Golden 期待 `needs_review`，offline Verifier 将其置于 `verified`，因此未计为正确 verified-risk prediction。其余 9 cases 没有形成 Role-B RiskItem。

这个结果暴露的主要问题仍然是：

```text
Evidence candidate may exist
→ structured extraction / candidate formation
→ reconciliation / Verifier
→ no formal RiskItem
```

## 5. Metric-v1 implications

新的 final competition benchmark 不会覆盖/重写本报告，而是新增一套 metric-v1 handoff：

### M1

Primary families：

```text
redemption_rights
related_party_transaction
customer_concentration
supplier_concentration
cash_burn_pressure
```

最终需报告 official-aligned positive Gold Risk Unit Accuracy、Precision、Positive Recall、Macro F1、per-risk support。official pass Accuracy >=0.80；内部 guardrails Positive Recall / Macro F1 >=0.82。

### M2

Human Gold 按支撑事实建立 Evidence Groups：

```text
Evidence Group Coverage Recall >=0.85
```

Recall@1/@3/@5/@10/@20 保留为 ranking diagnostics。旧本报告的 Recall@5=20% 仍可作为优化前 baseline 对照。

### Execution

下一步必须先做真实 LLM measurement，再做 Development-only remediation，禁止看 2024 Validation 后改 metric definition。

## 6. `ipo_2020_01167` governance

该 case 可用 formal Human Golden 评价。Supplementary expert annotation 的现有 receipt 因 unsupported `expected_level` values 保持 invalid/quarantined；本次 benchmark 没有修复、猜测或用它生成 prediction。

## 7. Required answers after metric-v1 clarification

1. 10 PDFs 是否全部找到？**YES**。
2. SHA/page 是否通过？**YES, 10/10**。
3. parsing/analysis failure？**None**。
4. 旧 offline Risk P/R/F1？**0/0/0**。
5. 旧 offline Recall@5？**20%**，仅 legacy ranking/end-to-end diagnostic。
6. 它是不是官方 Evidence Recall 的唯一口径？**NO**。
7. Real LLM cases？**0**。
8. 能否宣称 M1/M2 达标？**NO**。
9. 下一步？**metric-v1 real-LLM Development benchmark → failure taxonomy → Development-only remediation → frozen rerun**。

## 8. Artifacts

- `reports/v045_role_b/offline_development_analysis_results.jsonl`
- `reports/v045_role_b/offline_pdf_run_manifest.json`
- `reports/v045_role_b/document_benchmark_summary.json`
- `reports/v045_role_b/risk_benchmark.csv`
- `reports/v045_role_b/evidence_benchmark.csv`
- `reports/v045_role_b/document_benchmark_protocol.json`

这些是 legacy offline benchmark artifacts；final metric-v1 artifacts 必须额外记录 `metric_protocol_version=v045_competition_metric_protocol_v1`。

## 9. Verification performed at original run

```text
Formal Golden schema/catalog integrity: PASS
Offline/closure benchmark + Legal/Business/Verifier/runtime tests: 204 passed
Python compile check: PASS
git diff --check: PASS
Full pytest: NOT RUN
438-case/PDF-heavy benchmark: NOT RUN
```

原始事实保持不变。
