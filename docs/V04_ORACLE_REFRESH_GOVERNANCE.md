# v0.4 Oracle Refresh Governance

> Status: **FROZEN GOVERNANCE / ORACLE v2 NOT YET FROZEN**
> Date: 2026-08-23

## 1. Binding decision

The PR-A Oracle snapshot is an immutable historical artifact. It remains
`evaluation_only=true`, is not overwritten, and is not represented as the
current complete annotation universe. Production PR-D materialization is
decoupled from Oracle refresh and therefore is not blocked by Oracle drift.

| Snapshot | State | Materialized | Currently outcome-eligible | Development | Validation |
| --- | --- | ---: | ---: | ---: | ---: |
| Oracle v1 | historical PR-A frozen snapshot / immutable | 60 | 55 | 55 | 0 |
| Oracle v2 | planned refresh / **not frozen** | about 100 buildable | 91 currently strict-usable | 74 | 17 |

The v1 `55 / 0` intersection is historical and must not be used as the current
Oracle ceiling in formal PR-E diagnostics. Before formal PR-E, Oracle v2 must
be materialized under a separately approved, versioned freeze.

## 2. Oracle v2 requirements

The refreshed snapshot must preserve `evaluation_only=true` and publish:

- source annotation inventory hash;
- exact case-set hash and feature-set hash;
- schema and policy identity;
- explicit exclusion records;
- source-to-artifact lineage and reproducible content hashes.

It must not modify Production Document-X, rewrite PR-A historical hashes, use
2025 blind outcomes, or leak expert answers into Production features.

## 3. Current readiness findings

These are audit findings for reconciliation, not an eternal frozen count:

| Case | Current issue |
| --- | --- |
| `ipo_2020_08489` | cohort identity mismatch |
| `ipo_2020_09600` | cohort identity mismatch |
| `ipo_2022_02450` | cohort identity mismatch |
| `ipo_2023_02503` | cohort and split mismatch |
| `ipo_2024_02410` | split mismatch |
| `ipo_2024_00805` | non-official case |
| `ipo_2024_02613` | non-official case |
| `ipo_2020_02599` | outcome unavailable |
| `ipo_2020_06688` | outcome unavailable |

Production identity is authoritative; it must not be changed to accommodate
Oracle annotations.

## 4. Annotation quantity policy

The planned 100-case Expert Annotation target has been substantively reached.
Current priority is annotation QA, identity reconciliation, and Oracle refresh.
No unplanned 150/200-case expansion is authorized. Additional cases require a
separate decision supported by the future PR-E power diagnostic; already
assigned 100-case closeout work may finish normally.
