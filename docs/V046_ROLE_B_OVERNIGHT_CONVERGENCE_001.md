# V0.4.6 Role-B Overnight Convergence 001

## Status

```text
FINAL_STATUS = OVERNIGHT_IMPROVED
BASE_SHA = fff23aa1db5523683db1d75179033685c9721854
START_HEAD = 8dfd1c6ccf1443de940a6560830cac9bb761eec5
BRANCH = fix/v046-role-b-overnight-convergence-001
Validation opened = false
2025 Blind accessed = false
```

This Development-only sprint improved one official M2 unit in the final fresh
run while preserving M1. It did not reach the strong fixed-10 target. No result
from this sprint is evidence that the all-79 Development target has been met.

## Frozen baseline

The only formal baseline is gated `forensic_012`:

| metric | baseline |
|---|---:|
| M1 | 9/30 (30.00%) |
| M2 | 12/48 (25.00%) |
| Candidate Anchor@20 | 35/48 (72.92%) |
| Agent-consumed Evidence | 30/48 (62.50%) |
| structured-valid | 37/40 (92.50%) |

## Method

The sprint first compared the saved `forensic_012` and `forensic_013` Legal
journals without network access. It then added a zero-network fixed-journal
replay path so code changes could be evaluated against identical LLM responses.
The targeted two-case replay took about 2.69 minutes and the full fixed-10
replay about 13.07 minutes; the final fresh run took about 23.91 minutes in the
current local environment. No parser/retrieval cache was added.

Raw journals, prospectus text, PDFs, credentials and runtime directories are
not part of this commit. The tracked report artifacts contain only counts,
case identifiers, stage labels and hashes/statuses safe for review.

## Stability audit

The `forensic_012` to `forensic_013` Redemption regression is classified as
`LLM_RESPONSE_VARIANCE`, not a proven Financial or shared-runtime regression.
All compared call identities and bounded Evidence inputs matched.

- `ipo_2020_09600`: the structured `restoration_clause` changed from true to
  false. That single semantic field changed the deterministic builder from a
  built candidate to not-applicable.
- `ipo_2023_06682`: the structured response cited a smaller Evidence subset.
  The builder still produced the candidate, but final Evidence binding no
  longer covered the official Evidence unit.

The generic restoration normalization accepts a failed/lapsed/withdrawn listing
clause only when the same bounded evidence also contains a restorative
repurchase/redeem action. A generic on-listing termination does not qualify.
This restores `09600` without issuer, stock, page or Gold-specific logic.

## Accepted changes

1. Preserve the exact deterministic cash-runway value in
   `Calculation.result`; retain `runway_months_rounded` only as display metadata.
2. Canonicalize an explicit failed-listing restoration clause under the bounded
   rule above.
3. Add an immutable, zero-network fixed-journal replay mode.
4. Make Human Review latest-decision resolution use append-only journal order,
   removing a reproducible equal-timestamp UUID-ordering CI flake.

The fixed `forensic_012` journal produced:

```text
M1 = 10/30 (33.33%)
M2 = 14/48 (29.17%)
Redemption M1 = 4/8
Redemption M2 = 5/11
network calls = 0
```

## Rejected or deferred changes

- Automatic expansion of Legal Evidence was not implemented because clause
  identity was not proven and could bind unrelated legal text.
- Broad period-pairing/parser rewrites were not implemented because remaining
  Cash failures span multiple proven roots and no single bounded patch was
  established.
- No implementation changed after the final fresh result.

## Final fresh fixed-10

`overnight_final_001` completed 10/10 cases and 40 real LLM calls:

| metric | baseline | final | delta |
|---|---:|---:|---:|
| M1 | 9/30 | 9/30 | 0 |
| M2 | 12/48 | 13/48 | +1 |
| Candidate Anchor@20 | 35/48 | 35/48 | 0 |
| Agent-consumed Evidence | 30/48 | 34/48 | +4 |
| Candidate-risk Evidence units | 14/48 | 18/48 | +4 |
| structured-valid | 37/40 | 37/40 | 0 |

Transport failures and scope rejections were zero. Three structured validation
failures used the frozen fallback behavior. Monotonicity passed.

| risk | M1 baseline | M1 final | M2 baseline | M2 final | primary remaining root |
|---|---:|---:|---:|---:|---|
| cash_runway | 0/5 | 1/5 | 0/11 | 2/11 | period selection; parser/numeric extraction |
| customer_concentration | 3/8 | 3/8 | 3/13 | 3/13 | period selection; deterministic extraction |
| supplier_concentration | 2/9 | 2/9 | 4/13 | 4/13 | parser preservation; fact conversion |
| redemption_rights | 4/8 | 3/8 | 5/11 | 4/11 | response Evidence variance; verifier/binding |

The fresh Redemption result is below the same-journal result, while Cash gained
one M1 and two M2 units. This is reported as runtime reliability cost; the fresh
response is not replaced or retried until it passes.

## Remaining Cash roots

- `ipo_2020_00368`: wrong compatible period selection.
- `ipo_2020_01961`: parser text missing.
- `ipo_2021_02190`: numeric extraction miss.
- `ipo_2023_01274`: conflicting/wrong period selection.
- `ipo_2023_06682`: exact calculation, status, level and Evidence all match.

## Validation

```text
targeted Cash/Redemption/replay tests = PASS
Human Review tests = 13 passed; latest-decision repeat = 10/10 passed
full pytest = 2162 passed, 2 warnings
compileall = PASS
validate_project = PASS
validate_competition_data = PASS
validate_competition_runtime = PASS
structured smoke = 3/3 PASS
git diff --check = PASS
```

The first `pytest` launcher resolved to a Python 3.13 installation without
LightGBM. The governed validation used Python 3.12, where the declared project
dependencies are installed. One full run then exposed the unrelated Human
Review ordering flake described above; the final full run passed.

## Governance

```text
Existing Gold modified = false
evaluator modified = false
fixed10 identity modified = false
Validation opened = false
2025 Blind used = false
runtime received Gold = false
issuer/stock/page hardcoding = false
frozen Role-D artifacts modified = false
secrets persisted = false
```

The next permitted step is human selection of a new bounded batch. This report
does not authorize another fresh run, Batch 003, Validation or Blind access.
