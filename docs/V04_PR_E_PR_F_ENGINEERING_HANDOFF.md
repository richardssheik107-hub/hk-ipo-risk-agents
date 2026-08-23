# v0.4 PR-E / PR-F Engineering Handoff

> Status: **IMPLEMENTATION COMPLETE / FORMAL BULK EXECUTION PENDING**
> Date: 2026-08-23
> Owner: D — Quant / ML

## Delivered implementation

PR-E now provides deterministic Logistic, Linear and Ridge baselines for the
Production M/P/PM and Oracle-v2 M/P/O/PM/OM cohorts. It enforces:

- exact PR-D and Oracle-v2 freeze contracts;
- SHA-256 binding for all sixteen consumed matrices;
- equal cohort, case order, targets and split across every fair comparison;
- 2020–2023 Development-only fitting and 2024 Validation evaluation;
- expanding-year Development diagnostics without random/shuffled CV;
- explicit PM-M, OM-M and OM-PM value diagnostics;
- deterministic resume and 2025 Blind isolation.

The new Oracle-v2 matrix builder verifies the 98 frozen Oracle feature
artifacts, intersects them with the 424 PR-D model-ready rows, and deterministically
produces 77 Development plus 19 Validation rows for each of M/P/O/PM/OM.

PR-F provides fixed-policy, single-threaded deterministic LightGBM classifier
and regressor models for the same eight cohort/group combinations. It records
2024 metrics, per-IPO predictions, native LightGBM SHAP contributions, global
gain/split importance, component importance, signed top drivers and model-text
hashes. PR-F cannot run unless the formal PR-E Gate passed.

## Formal execution boundary

This Git checkout contains the small authoritative freeze manifests, but the
project policy intentionally excludes these governed bulk runtime artifacts:

- six PR-D Production matrices;
- 98 Oracle-v2 feature artifacts;
- generated PR-E metrics;
- generated PR-F models and explanations.

Therefore this checkout can validate the complete implementation and its
fail-closed behavior, but cannot honestly publish measured PR-E or PR-F results.
The formal run must be performed in the governed data workspace that created
the frozen PR-D and Oracle-v2 artifacts. No synthetic data may be presented as
a formal result.

## Public-interface impact

No protected public Schema, Agent, Parser, Retriever, Predictor, Provider,
Workflow, Service or Container interface is changed. All additions are confined
to offline modeling modules, scripts, tests and research documentation.
