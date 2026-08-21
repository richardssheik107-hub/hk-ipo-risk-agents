# v0.4 Role A → Codex Handoff

> Status: **WEB/GITHUB-SIDE IMPLEMENTATION PREP COMPLETE / LOCAL EXECUTION EVIDENCE REQUIRED**  
> Date: **2026-08-21**  
> State: **PR-A COMPLETE / FROZEN; PR-B Core code prepared on this existing branch, Gate not yet passed**

## 1. Read first

Before changing code, read:

1. `AGENTS.md`
2. `docs/README.md`
3. `docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`
4. `docs/research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`
5. `docs/research/V04_DATA_READINESS.md`
6. `docs/V04_ROLE_A_CROSS_TEAM_PREP.md`

The web/GitHub-side preparation has already implemented the unblocked PR-B Core work. Do not rebuild the same orchestration or reopen frozen Document Intelligence.

## 2. What is already done on this branch

Implemented or hardened:

```text
scripts/build_v04_ipo_eod_store.py
scripts/run_v04_pr_b.py
src/ipo_risk/market/eod_store.py
src/ipo_risk/market/ipo_market_context_features.py
```

Tests added/expanded:

```text
tests/unit/test_v04_ipo_eod_store.py
tests/unit/test_v04_pr_b_orchestration.py
tests/unit/test_ipo_market_context_features.py
tests/unit/test_v04_data_readiness.py
```

Governance and wiring corrections already made:

- governed EOD cohort uses authoritative `official_listed_date.year`, not document `source_year`;
- EOD data/business logic lives in `ipo_risk.market.eod_store`; CLI remains a thin wrapper;
- `run_v04_pr_b.py` imports the governed EOD implementation directly from `ipo_risk.market.eod_store`;
- EOD store retains `OBJECT_ID` provenance;
- `S_DQ_AMOUNT` is explicitly per-security only, never total-market turnover;
- PR-B Core uses strictly pre-listing prior-IPO context;
- prior 1D/5D outcomes enter X only after their target session occurred strictly before the target listing date;
- the formal runner derives the prior-IPO history left boundary from the earliest official listing date in the governed 2020–2024 universe;
- 30D/60D/180D lookbacks extending before that declared source boundary become explicit missing values rather than misleading zeros/partial-history values;
- the history boundary is recorded in execution provenance and each Core feature artifact;
- 2025 blind outcomes remain inaccessible;
- resume conflicts fail closed;
- semantic coverage is stable across `created`/`reused` lifecycle changes;
- the committed source manifest now reflects PR-A 438/438 Document materialization rather than the old 0/438 readiness state;
- HSI / industry benchmark / turnover remain Market-X Extended gaps and are not silently proxied.

The remaining PR-B uncertainty is no longer design/wiring work; it is **real local execution evidence and any defects revealed by that execution**.

## 3. Immediate Codex task: run, verify, fix only real failures

### Step 1 — sync this existing branch

Continue on the current branch. **Do not create another branch unless the user explicitly asks.**

Confirm the files above are present before editing.

### Step 2 — install and run targeted tests

```bash
python -m pip install -e '.[dev,retrieval-research]'
pytest -q \
  tests/unit/test_v04_ipo_eod_store.py \
  tests/unit/test_ipo_market_context_features.py \
  tests/unit/test_v04_pr_b_orchestration.py \
  tests/unit/test_v04_data_readiness.py \
  tests/unit/test_market_provider_and_labels.py \
  tests/unit/test_market_governance_validation.py
```

If tests fail, fix the actual implementation defect. Do not weaken assertions or change the frozen PIT/no-leakage rules to make tests pass.

### Step 3 — run full tests

```bash
pytest -q
```

Record the exact pass/fail count. Do not claim green CI/tests unless they actually ran.

### Step 4 — run PR-B pilot with the local governed market root

```bash
python scripts/run_v04_pr_b.py \
  --catalog-dir data/catalog \
  --data-root <LOCAL_MARKET_ROOT> \
  --output-dir reports/v04_pr_b_pilot \
  --limit 5
```

Inspect:

```text
execution_context.json
governed_eod/v04_ipo_eod.manifest.json
governed_eod/v04_ipo_eod.csv
core_features/*.json
coverage.json
coverage.csv
failure_report.csv
run_manifest.json
```

Also verify that `execution_context.json` and per-case Core artifacts contain the declared prior-IPO history start date and that early-2020 incomplete lookbacks use explicit missing indicators.

The pilot is engineering validation only. Do not tune feature rules from those five cases.

### Step 5 — full 438-case PR-B Core run

```bash
python scripts/run_v04_pr_b.py \
  --catalog-dir data/catalog \
  --data-root <LOCAL_MARKET_ROOT> \
  --output-dir reports/v04_pr_b
```

Expected governance preflight:

```text
official target cohort = 438
2025 blind outcomes     = not accessed
```

Do not assume actual Core materialization count before the run reports it.

### Step 6 — resume + determinism audit

```bash
python scripts/run_v04_pr_b.py \
  --catalog-dir data/catalog \
  --data-root <LOCAL_MARKET_ROOT> \
  --output-dir reports/v04_pr_b \
  --resume \
  --verify-determinism
```

Required result for Gate acceptance:

```text
mismatch_count = 0
coverage semantic hash unchanged
```

### Step 7 — freeze measured PR-B results only if Gate passes

Only after targeted tests, full tests, full materialization and determinism all succeed:

- update `docs/research/V04_DATA_READINESS.md` with measured numbers;
- update `docs/ROADMAP.md` and `docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md` to PR-B COMPLETE / FROZEN;
- add a concise PR-B completion report / small frozen manifest;
- report actual failures/missingness rather than hiding them.

Stop at the PR-B Gate. Do not formally start PR-C before acceptance.

## 4. Core vs Extended: do not reopen this decision

Current working interpretation for PR-B is:

```text
PR-B Core
= governed IPO EOD + prior-IPO context already available today

Market-X Extended
= HSI + industry benchmark mapping/history + HKEX total-market turnover
```

The Extended sources are still absent in the committed source manifest. Their absence must remain explicit and **never justifies fabricating a proxy**. If the formal owner decides Extended sources are required for the PR-B Gate rather than a later extension, that is a scope/Gate decision and must be documented explicitly; code must not guess.

Do not:

- create fake HSI observations;
- use Hang Seng Bank as HSI;
- infer industry benchmark IDs from company/industry text;
- use `S_DQ_AMOUNT` as total-market turnover;
- fill missing Extended features with neutral zero.

If the user/team later supplies or approves authoritative Extended sources, integrate them through the existing versioned contracts with provenance and tests.

## 5. Remaining work after PR-B

```text
PR-C — 5D weak-performance target policy freeze
PR-D — canonical model-ready dataset
PR-E — M/P/O/PM/OM baseline + Oracle diagnostic
PR-F — LightGBM + explainability
PR-G — Market Agent + Final Supervisor
PR-H — Streamlit Full E2E + 3–5 real IPO demo
```

PR-C threshold selection may use only 2020–2023 Development. 2024 is formal validation; 2025 y remains blind.

## 6. Remaining ownership

| Role | Remaining work |
|---|---|
| A | PR-B local run/Gate review; then cross-module contracts, reproducibility and integration support for later PRs |
| B | frozen Document downstream QA / evidence-to-driver traceability |
| C | PR-B market-domain QA; authoritative Extended-source acquisition/approval if required |
| D | PR-C target policy, PR-D dataset, PR-E/F modeling |
| E | Oracle isolation QA, PR-G supervisor, PR-H product integration |

## 7. Suggested Codex instruction

> Continue on the existing branch. Read `AGENTS.md`, `docs/V04_ROLE_A_CODEX_HANDOFF.md` and `docs/research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`. The web/GitHub-side PR-B Core code, EOD refactor, history-boundary wiring and tests are already prepared. Run targeted tests, full pytest, a 5-case pilot, the full 438-case run, then `--resume --verify-determinism`. Fix only real failures without weakening PIT/no-leakage rules. If and only if all PR-B Gate evidence passes, freeze measured results in the readiness/roadmap/master-plan docs, then stop before PR-C.
