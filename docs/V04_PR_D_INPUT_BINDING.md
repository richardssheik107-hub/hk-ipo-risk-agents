# PR-D Frozen Bulk Input Binding

> Contract: `v04_pr_d_input_binding_v1`
> Status: **P0 RESOLVED / PR-D FORMAL MATERIALIZATION NOT STARTED**

PR-D must validate three independent layers before writing any formal output:

1. the committed PR-A / PR-B / PR-C freeze manifests;
2. the additive binding in
   `reports/frozen/v04_pr_d_input_binding_manifest.json`;
3. the actual Production, Market Core, Outcome and historical Oracle artifacts.

## Deterministic identities

Every component is enumerated by JSON artifact, validated under its frozen
schema/feature order, and sorted by internal `case_id`. Each aggregate entry
binds:

```text
case_id
schema_version
policy_version
manifest_hash
feature_order_hash
content_hash
```

`artifact_set_hash` is SHA-256 over the canonical JSON serialization of this
sorted entry list. `case_set_hash` and `identity_set_hash` separately bind the
exact official cohort and the five-way identity:

```text
case_id / stock_code / cohort_year / listing_date / dataset_split
```

The algorithm does not use absolute paths, mtimes, filesystem enumeration
order, or directory names. The binding also records SHA-256 identities of the
three upstream manifests and verifies the PR-C self-freeze identity and the
recomputed PR-C target-set hash.

## Frozen results

| Component | Count | Aggregate hash |
| --- | ---: | --- |
| Production Document-X | 438 | `9197b0f4f90e6d43277586ac40160679d40f91e3b30223578d0853d9dc288bf3` |
| Market-X Core | 438 | `6803424877560945de61a6647863365c4e91b786bc9f12f1451da4a25c3b2eb6` |
| PR-C Outcome | 438 | `1f0ab1f8314a322abcaf4c88feead02e6cd114b478234b36388c27e33dc7ad90` |

Official case-set hash:
`f268fe544fc2607b8cacec7b7b51e9fe668b7fcd0e956202a66b7bef530ad90d`.

Official identity-set hash:
`9b8e1e3e1677d1d613dade66931b00a9793b38636d8f7e7a0e86a76c47e30976`.

PR-C target-set hash recomputes to the frozen
`5e0dedc8d207c8e73ca6439efb72f463c6b6f276c1c6c48e3ad7a989ad1533f4`.

Market Extended remains `not_supplied_governed_optional`. The historical
Oracle v1 aggregate is also bound, but remains evaluation-only and does not
block the 424-row Production cohort when an Oracle identity is ineligible.

Any manifest, case set, identity, schema, feature order, artifact content or
resume provenance mismatch fails closed. The runner does not rebuild or
silently overwrite inputs.
