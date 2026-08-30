# Person 1 — M1 / M2 Document Intelligence Owner — CLOSED

> Release: `v1.0.0`  
> 状态日期：`2026-08-30`  
> Runtime freeze main：`ab3390cc548f3d4ec7f08d5d39350a3c1baf1f0a`  
> Benchmark SHA：`dcc36abd30ec42cd1d6b83bc6d70b2d1aa74f61b`  
> Final status：**DEVELOPMENT CLOSED / G2 BLOCKED**

## Final ALL79 truth

| Mode | Cases | M1 | M2 |
|---|---:|---:|---:|
| Best offline | 79/79 | **70/102 = 68.63%** | **103/191 = 53.93%** |
| Real LLM gated | 79/79 | **61/102 = 59.80%** | **93/191 = 48.69%** |

Internal G2 target:

```text
M1 >= 80%
M2 >= 85%
real_llm_cases = 79/79
```

Result:

```text
real LLM coverage = PASS
M1 threshold = BLOCKED
M2 threshold = BLOCKED
G2 = BLOCKED
```

Machine source:

```text
reports/v045_role_b/document_benchmark_summary.json
```

## Final engineering state

The accepted Role-B work is merged into the frozen release line. Development optimization stops at v1.0.0.

```text
AUTO_CONTINUE = FALSE
DEVELOPMENT_TUNING = STOP
VALIDATION_DRIVEN_TUNING = FORBIDDEN
```

The higher offline measurement is retained as an engineering reference only and is never substituted for the provider-backed result.

## Retained generic improvements

The final runtime contains the accepted cross-case/generalized repairs accumulated during the competition work, including Financial extraction hardening, concentration lifecycle/binding improvements, Legal shareholder-right lifecycle handling, Evidence/provenance controls, and full-Development/smoke/evaluator hardening.

Historical rejected experiments remain historical and are not silently reintroduced.

## Final quality observation

The real LLM path did not outperform the best offline path on the final ALL79 measurement. Under the strict schema/Evidence-scope contract, some provider-generated candidates were rejected or caused negative monotonicity. v1.0.0 therefore preserves the real measurement as-is rather than relaxing Evidence guards to improve the score.

## Governance

- Existing Gold immutable;
- Gold does not enter runtime;
- `UNJUDGED != negative`;
- no issuer/case/page/Gold-text hardcoding;
- no fabricated Evidence;
- no retry-to-improve benchmark;
- no post-freeze Development tuning;
- no Validation-driven tuning;
- 2025 Blind outcomes not used for optimization.

## Post-release rule

Person 1 has no active competition-development task after v1.0.0. Any future Document Intelligence experimentation belongs to a later version and must not rewrite the v1.0.0 benchmark truth.
