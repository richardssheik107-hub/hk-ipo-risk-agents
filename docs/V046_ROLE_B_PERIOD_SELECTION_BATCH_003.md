# V0.4.6 Role-B Batch 003 — Deterministic Period Selection Closure

## Status

```text
FINAL_STATUS = BATCH003_REJECTED
BASE_SHA = 0a52db344eb765150b25bc2b4fa6d10f258ac504
BRANCH = fix/v046-role-b-period-selection-batch-003
REPORT_COMMIT_SHA = enclosing Git commit (avoids a self-referential hash)
production runtime changed = false
fresh LLM run executed = false
Validation opened = false
2025 Blind accessed = false
```

The rejection is a bounded finding, not an execution failure. The fixed-journal
audit found no unit that satisfies the strict selector-bug contract. Changing
the production period selector would therefore be speculative and would cross
the approved scope into parser preservation, period parsing, numeric extraction
or deterministic fact conversion.

## Integration floor

Batch 003 starts from `main@0a52db344eb765150b25bc2b4fa6d10f258ac504`,
which contains Overnight Convergence 001 through merged PR #165. Its required
GitHub Actions run `33221091017` completed successfully.

The zero-network fixed-journal replay `batch003_integration_floor` preserved the
frozen floor:

| risk | M1 | M2 |
|---|---:|---:|
| Cash | 1/5 | 2/11 |
| Customer | 3/8 | 3/13 |
| Supplier | 2/9 | 4/13 |
| Redemption | 4/8 | 5/11 |
| **Total** | **10/30 (33.33%)** | **14/48 (29.17%)** |

The replay used 40 immutable journal records and made zero network calls. The
fixed-10 identity is `5758b9f0...b6a`, the Gold manifest identity is
`fcd12d34...d1c`, and the journal identity is `8d5cb474...e5e2`.

The runner reports formal monotonicity as `NOT_PROVEN` because this integration
replay intentionally contains only `offline,gated`, not the required
`offline,shadow,gated` triplet. The observed metrics are non-regressive, but the
missing shadow mode is not relabeled as a formal monotonicity PASS.

## Period-selection audit

The evaluation-only audit joined persisted gated runtime diagnostics to
Existing Gold after execution. Gold was not passed into runtime. It inspected
22 positive Financial units and emitted only bounded fields, hashes and stage
labels.

| classification | units |
|---|---:|
| correct | 6 |
| deterministic fact missing | 8 |
| parser text missing | 4 |
| period candidate missing | 2 |
| numeric extraction miss | 1 |
| real conflict, fail closed | 1 |
| **proven period-selection bug** | **0** |

A selector bug requires the correct bounded Evidence, parsed value and parsed
period to exist, with compatible currency/unit and no real conflict, followed
by selection of a different period. No audited unit met all conditions.

### Primary diagnosis set

- `ipo_2020_00368 / cash_runway`: parser/target fact missing.
- `ipo_2020_00368 / customer_concentration`: values exist but no correct period
  candidate; this is period parsing, not period selection.
- `ipo_2020_01961 / supplier_concentration`: no period candidate and the
  expected deterministic value is absent; this is extraction/conversion.
- `ipo_2021_01024 / customer_concentration` and `supplier_concentration`: the
  audited canonical calculation inputs are explicitly unavailable. Stale
  pass-1 facts were not revived.
- `ipo_2023_01274 / cash_runway`: correct period/value candidates exist, but
  same-period operating-cash-flow values genuinely conflict. Existing
  fail-closed behavior is correct and was preserved.

The earlier broad `wrong_period_selection` labels are therefore superseded by
the strict classifications above for Batch 003 decision-making.

## Implementation decision

No production selector patch was made. The only implementation added is an
evaluation-only classifier, a read-only audit command and synthetic tests. The
runtime Financial extractor, Parser, Retriever, prompts, provider/model,
Legal/Business paths, evaluator definitions and frozen Role-D artifacts are
unchanged.

Because no safe generic selector fix was proven, the acceptance threshold of
M1 `>=12/30` and M2 `>=17/48` cannot be pursued inside this batch. The final
fixed-journal result therefore equals the baseline: M1 `10/30`, M2 `14/48`.
No fresh LLM run was authorized or executed.

## Controls

- `ipo_2023_06682`: Cash remains fully correct.
- `ipo_2021_02190`: Cash remains a numeric extraction miss; Customer remains
  correct; Supplier was not falsely converted by period logic.
- `ipo_2022_06610`: Customer and Supplier remain parser-text missing.
- Redemption remains M1 `4/8`, M2 `5/11`; no Legal file changed.

## Governance

```text
Existing Gold modified = false
evaluator metric modified = false
fixed10 identity modified = false
Validation opened = false
2025 Blind used = false
runtime received Gold = false
issuer/stock/company/page/year hardcoding = false
Retriever modified = false
Parser modified = false
Prompt/model/provider modified = false
frozen Role-D artifacts modified = false
raw prospectus or Gold text persisted = false
secrets persisted = false
```

## Validation

```text
period/Financial/Cash/Concentration/replay/Human Review targeted = 294 passed
full pytest = 2194 passed, 3 warnings
compileall = PASS
validate_project = PASS (completed; verified=3; pending=1)
validate_competition_data = PASS
validate_competition_runtime = PASS
validate_v045_role_d_receipt = PASS
structured smoke = 3/3 PASS in integration preflight
git diff --check = PASS
sensitive-output scan = PASS
```

The structured smoke is the recorded integration preflight for the same base,
provider/model and prompt/schema contracts. It was not rerun after the audit
because Batch 003 changes no provider, prompt, schema or runtime path.

## Accepted work

1. A strict, reusable evaluation-only period-selection classifier.
2. Safe parsing of persisted legacy component diagnostics with
   `ast.literal_eval` rather than executable evaluation.
3. A zero-network audit producing hashed values and bounded metadata.
4. Regression tests that distinguish missing period/value, real conflict,
   incompatible facts and a true selector failure.

## Rejected or deferred work

- Production period-selector changes: rejected because zero selector bugs were
  proven.
- Parser preservation and period parsing: deferred as out of Batch 003 scope.
- Numeric extraction and concentration fact conversion: deferred.
- Ignoring the `ipo_2023_01274` conflict: rejected because it would weaken the
  fail-closed financial safety boundary.
- Fresh fixed-10 LLM execution: not authorized because the fixed-journal Gate
  was not met.

## Remaining root-cause order

The next bounded work should address concentration deterministic extraction and
fact conversion, especially absent period/value candidates. Parser preservation
should remain a separate later batch unless a new audit proves it is the single
largest safe root.

```text
NEXT_RECOMMENDED_STAGE =
BATCH_004_CONCENTRATION_DETERMINISTIC_EXTRACTION_AND_FACT_CONVERSION
```
