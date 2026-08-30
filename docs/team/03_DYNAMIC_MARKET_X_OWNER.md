# Person 3 — Dynamic Market-X Owner — CLOSED

> Release: `v1.0.0`  
> 状态日期：`2026-08-30`  
> Final status: **G3 PASS / REGRESSION PROTECTION**

## Final responsibility

The Market-X track is complete for v1.0.0. The product now uses one governed Market runtime for historical and new IPO paths, with explicit PIT boundaries and honest missingness.

## Final runtime semantics

```text
issuer / stock / listing identity
→ governed frozen Market artifact when available
   or Dynamic PIT Market-X path
→ identity / hash / provenance / cutoff validation
→ MarketContext
→ Market Skills
→ frozen Model handoff / Final Supervisor / UI
```

A case with insufficient governed pre-listing history may return `PARTIAL` or `UNAVAILABLE`. That is a correct product outcome, not a reason to invent a number.

## G3 acceptance

The strict historical audit covers the governed universe with zero integrity violations. Final release documentation uses the committed audit artifacts as the machine source of truth.

Key frozen behavior:

```text
governed cases = 562
integrity violations = 0
runtime errors = 0
frozen path = 438
Dynamic PIT path = 124
Model handoff = bound 550 / not_projectable 12
```

Machine source:

```text
reports/v046_market_runtime/historical_market_runtime_audit.json
```

Technical contract:

```text
docs/V046_ROLE_C_DYNAMIC_MARKET_X.md
```

## Missingness policy

Forbidden:

```text
missing → 0
missing → average
missing → copied final-three value
missing → unsourced web value
```

Required:

```text
value + provenance
or
PARTIAL / UNAVAILABLE + explicit reason
```

## Governance

- no target IPO post-listing outcome in pre-listing Market-X;
- no 2025 Blind outcome use for optimization;
- no case-specific Market hardcoding;
- no raw licensed EOD in the public repository;
- identity mismatch fails closed;
- PIT cutoff is explicit;
- frontend consumes governed MarketContext rather than rebuilding market numbers.

## Post-release rule

No new Market feature engineering is allowed in the v1.0.0 competition line. Only correctness/regression fixes that preserve the frozen feature contract are permitted.
