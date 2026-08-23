# v0.4 Oracle Refresh Governance

> Status: **FROZEN GOVERNANCE / ORACLE v2 FREEZE CANDIDATE READY FOR A FINAL SIGN-OFF**
> Date: 2026-08-23

## 1. Binding decision

The PR-A Oracle snapshot is an immutable historical artifact. It remains
`evaluation_only=true`, is not overwritten, and is not represented as the
current complete annotation universe. Production PR-D materialization is
decoupled from Oracle refresh and therefore is not blocked by Oracle drift.

| Snapshot | State | Materialized | Currently outcome-eligible | Development | Validation |
| --- | --- | ---: | ---: | ---: | ---: |
| Oracle v1 | historical PR-A frozen snapshot / immutable | 60 | 55 | 55 | 0 |
| Oracle v2 | materialized / reproducible / **freeze candidate** | 98 | 96 | 77 | 19 |

The v1 `55 / 0` intersection is historical and must not be used as the current
Oracle ceiling in formal PR-E diagnostics. Oracle v2 has now been materialized
under a separate versioned contract and is ready for Role A final sign-off; it
is not frozen on `main` until that review and merge complete.

## 2. Oracle v2 requirements

The refreshed snapshot must preserve `evaluation_only=true` and publish:

- source annotation inventory hash;
- exact case-set hash and feature-set hash;
- schema and policy identity;
- explicit exclusion records;
- source-to-artifact lineage and reproducible content hashes.

It must not modify Production Document-X, rewrite PR-A historical hashes, use
2025 blind outcomes, or leak expert answers into Production features.

## 3. Oracle v2 materialization findings

Production identity is authoritative. The refresh reconciled all 98 official
materialized cases with zero unresolved identity records. Current explicit
exceptions are:

| Case | Current issue |
| --- | --- |
| `ipo_2024_00805` | non-official case |
| `ipo_2024_02613` | non-official case |
| historical `real_case_001` | non-canonical legacy path; canonical `ipo_2024_02410` is retained separately |
| `ipo_2020_02599` | outcome unavailable: `missing_base_price` |
| `ipo_2020_06688` | outcome unavailable: `no_eligible_session` |

Production identity is authoritative; it must not be changed to accommodate
Oracle annotations.

The current inventory contains 101 entries: 100 valid annotations and one
invalid legacy entry. Of 87 audit overlays, 17 are stale relative to their
current pass-1 source hash after cross-platform newline normalization. Stale overlays remain auditable but are explicitly
`stale_not_applied`; v2 never silently applies them.

The candidate contract is `expert_oracle_document_features_v2` /
`oracle_gold_policy_v2`, with 142 features, `evaluation_only=true` and
`production_consumable=false`. See `V04_ORACLE_V2_COMPLETION_REPORT.md` and
`reports/frozen/v04_oracle_v2_manifest.json` for the full counts and hashes.

## 4. Annotation quantity policy

The planned 100-case Expert Annotation target has been substantively reached.
Current priority is annotation QA, identity reconciliation, and Oracle refresh.
No unplanned 150/200-case expansion is authorized. Additional cases require a
separate decision supported by the future PR-E power diagnostic; already
assigned 100-case closeout work may finish normally.
