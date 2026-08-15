# V04-2 Document-to-Market Feature Contract

Status: **MERGED**

## 1. Why this boundary exists

V04-2 separates document intelligence from later statistical modeling:

```text
final IPOAnalysisResult
        -> V03DocumentRiskSnapshot
        -> v04_document_features_v1
        -> V04ModelingRecord / V04ModelingDataset
        <- V04-1 MarketOutcomeLabel
```

Models will consume a frozen numeric contract, not Retriever results, Agent
candidates, raw Evidence search output, or an LLM response. This keeps future
document-pipeline improvements from rewriting the Market Foundation or model API.

## 2. Source boundary

`DocumentRiskSnapshotBuilder` consumes the persisted public
`IPOAnalysisResult`. Its `verified_risks` are the final supervised output;
pending and rejected items remain explicit public result buckets. A required
`DocumentRiskSnapshotBuildContext` supplies stable case/document identity,
cohort, split, and document-pipeline version/commit that the legacy result does
not always carry directly. It also retains V04-1 security type and eligibility
as non-feature governance provenance.

The builder has no Retriever, Agent, LLM, network, random, or clock dependency.
`RiskItem.created_at`, result timestamps, Evidence text, and LLM output never
become feature values.

## 3. Eight canonical risks

The contract imports `V03_ENABLED_RISK_CODES` and `V03_RISK_OWNERS`; it does not
copy a second risk registry. V1 uses the following deterministic alphabetical
order:

1. `cash_runway`
2. `continuous_loss`
3. `customer_concentration`
4. `material_litigation_compliance`
5. `precommercial_product`
6. `redemption_rights`
7. `revenue_growth`
8. `supplier_concentration`

Unknown future codes are retained in `unknown_risk_codes` diagnostics but never
change V1 order or feature count.

## 4. Risk-state semantics

Each canonical position is a `DocumentRiskFeature` with one of:

- `verified`: a trusted final supervised risk exists;
- `pending`: verification has not completed;
- `needs_review`: deterministic verification requires review;
- `rejected`: the final verifier rejected the item;
- `not_emitted`: the responsible pipeline completed but emitted no final item;
- `unavailable`: a relevant component failed or was unavailable.

The snapshot retains score, level, confidence, evidence count, calculation
presence/success, source risk ID, and an explicit missing/degradation reason.
Final duplicate canonical positions fail with a structured
`DuplicateAuthoritativeRiskError`; the builder never selects first/max/average.

## 5. Missingness semantics

Absence of a verified risk is never encoded as a safe score of zero. In the
numeric vector, score and level are `null` unless state is `verified`. Every
risk has six state indicators and a separate `missing` flag. Evidence count zero
means no attached Evidence and does not mean the security is safe.

## 6. Feature manifest and versioning

`DocumentFeatureManifest` version `v04_document_features_v1` freezes 100 ordered
numeric positions:

- 11 positions per risk: six state indicators, score, level ordinal, evidence
  count, calculation success, and missingness (88 total);
- 12 aggregates: state counts, verified high/critical counts, max/mean verified
  score, authoritative conflict count when available, and missing-risk count.

The level map is explicit: low=0, medium=1, high=2, critical=3. Each definition
contains index, name, dtype, source, and missing semantics. The manifest has a
deterministic SHA-256 content hash, and vectors carry both version and hash.

`PredictionResult.risk_score` is intentionally excluded because
`RuleBasedPredictor` is a comparison baseline. Only its model version may appear
in snapshot audit metadata.

## 7. Snapshot provenance

`V03DocumentRiskSnapshot` preserves:

- case, document, stock, cohort, listing date, and split;
- workflow and public result schema version;
- document pipeline version and commit;
- feature schema version;
- source analysis ID and final status;
- generated-from result version.

Canonical JSON and content hashes are deterministic. Two otherwise identical
snapshots from pipeline commits A and B have identical feature values but
different provenance and snapshot hashes, supporting controlled Retriever A/B.

## 8. Modeling dataset join

`V04ModelingDatasetBuilder` joins a snapshot to one `MarketOutcomeLabel` only
after exact checks of case ID, stock code, cohort/listing year, listing date, and
dataset split. Records preserve document pipeline, workflow/schema, feature
manifest, market label policy, chronological split policy, and dataset versions.
The builder also requires V04-1 modeling eligibility under
`v04_market_security_eligibility_v2`. Eligibility comes from explicit
authoritative official-IPO membership, not security type. An official case with
unknown type may enter; an arbitrary case cannot enter merely by declaring an
ordinary-equity type.

Rows are deterministically ordered by case ID and label horizon. The dataset
version is `v04_modeling_dataset_v1`.

## 9. Chronological split and blind protection

V04-1 governance remains authoritative:

```text
2020-2023 -> development
2024      -> validation
2025      -> blind
```

Development and validation have separate builder entry points. A blind label
cannot form `V04ModelingRecord` or `V04ModelingDataset`. There is no override,
force, or allow-blind parameter.

`V04BlindFeatureExporter` accepts 2025 document snapshots and emits
`V04BlindFeatureDataset`. Its record schema deliberately has no outcome-label or
target field, and it enforces explicit governed-case membership. A 2025 ticker
is not automatically a member of the frozen 2020-2024 universe; an explicitly
governed blind case can still produce `X_blind` while `y_blind` stays outside
training, feature selection, model selection, and threshold tuning.

## 10. Retriever upgrade behavior

Retriever improvements regenerate snapshots/datasets; they do not change Market
Foundation or model APIs. A new document pipeline commit produces new snapshot
provenance and a new dataset artifact while the market label policy may remain
unchanged.

## 11. Feature-schema version bumps

A new feature schema version is required when feature names, order, dtype,
state/missing semantics, level mapping, aggregate formulas, canonical risk set,
or trusted source boundary changes. New input data under the same frozen rules
does not require a schema bump; it produces a new snapshot/dataset artifact.

## 12. Out of scope

V04-2 does not implement a Market Agent, HSI/industry/sentiment features,
Logistic Regression, LightGBM, SHAP, calibration, tuning, production prediction,
or 2025 outcome evaluation. It does not modify Retriever, Parser, professional
Agent rules, Verifier semantics, Supervisor scoring, Expert Golden, or the V04-1
label policy.
