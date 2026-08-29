# Changelog

## Unreleased — demo bundle: a recorded run that replays offline, and says it is a recording

G6 asks for a demonstration script and a static backup for the three cases. The UI
could only run live from an uploaded PDF (`st.file_uploader` was the single entry
point), so demonstrating anything required the licensed prospectus, provider
credentials and a network — three things that can each fail in front of an
audience while proving nothing the recorded run had not already proved.

### Added

- **`ipo_risk.runtime.demo_replay`** — packages a matrix run's artifacts into a
  self-contained bundle with a SHA-256 for every file, loads a recorded case back
  for display, and re-verifies a bundle before it goes on a screen.
- **`scripts/build_v045_demo_bundle.py`** — builds the bundle and generates
  `DEMO_SCRIPT.md` from the bundled artifacts; `--verify` re-hashes an existing
  bundle and exits non-zero when a file was tampered with or lost.
- **Sidebar "Demo replay"** in the Streamlit app: pick a recorded case, load it, and
  every workspace renders it through the same schema a live run uses. The bundle
  directory defaults to `reports/v045_demo_bundle` and honours
  `IPO_RISK_DEMO_BUNDLE`.

### Governance

- **A replay announces itself.** A banner above the workspace carries the recorded
  run's case id, analysis id, config, code base SHA (including whether that tree was
  dirty) and the prospectus SHA-256, and states that nothing is filled in for the
  replay. The runtime label reads `已记录运行回放` rather than a live scenario.
- **Replay state cannot outlive its result**: starting a live analysis or clearing
  the result drops the banner and the replay screenshots together, so no screen ever
  mixes one run's provenance with another run's content.
- **The offline Evidence page is the exported screenshot**, captioned with the
  granularity the manifest recorded and the image's own SHA-256. An Evidence item
  the export refused has no image here either — another item's page would be a false
  claim about where this one came from.
- A case with no recorded analysis result is refused rather than shown as a run that
  found nothing; missing sidecars are listed as missing; the generated walkthrough
  states the unavailable channels, the Gate E1 status and that an unreviewed case is
  not an approved one.

### Measured

Bundled the existing three-case matrix: 3/3 replayable, 62 files, 5.4 MB, verify
PASS. Loaded 2410 in the running app: all seven stages render from the recording,
Market/Model stay honestly unavailable, and the Evidence page shows the exported
screenshot with its hash.


## Unreleased — batch risk report: several companies in one view, with its ordering rule attached

G6 asks for a single-company **and** a batch report. The per-case `case_report.md`
existed; nothing produced a portfolio view (`grep batch` over `runtime/` and `app/`
returned nothing). A batch view is also where a summary is most tempted to say more
than the runs did, because putting companies in an order invites reading the order
as a verdict.

### Added

- **`ipo_risk.runtime.batch_report`** — builds one report over a matrix run: matrix
  identity (code/config/case-list SHA-256, dirty tree), per-case recorded state
  (severity counts, conflicts, Final Supervisor outcome, traceability, Evidence and
  screenshot coverage, channel states, human-review count), cross-case aggregates,
  and a limitations section derived from the data rather than asserted.
- **`scripts/build_v045_batch_report.py`** — reads an existing matrix output
  directory and writes `batch_report.json` + `batch_report.md`. It re-analyses
  nothing and opens no outcome label.

### Governance

- **The ordering carries its rule.** Cases are ordered by the severities the
  document channel recorded, and `TRIAGE_RULE` — printed inside the report — states
  that this orders recorded risk counts and is not a score, not a probability and
  not a prediction of post-listing performance.
- **A declared case that did not execute stays in the report**, with the reason the
  matrix recorded. A batch that silently shrinks to the cases that worked would make
  every aggregate under it wrong.
- A case whose document channel asserted nothing is shown as asserting nothing; an
  unavailable channel contributes no fact and is named with its state; an unreviewed
  case reads as unreviewed; a deterministic fallback is never counted as
  real-provider arbitration.


## Unreleased — Evidence screenshots: unique-match localisation and a hash-bound manifest

`Evidence screenshots` is a required submission deliverable and nothing implemented
it: the repository contained no screenshot code at all, and the only geometry an
Evidence item carried was the parser's page-level text union. This adds the export,
and localises the cited text on the page rather than boxing the whole page.

### Added

- **`ipo_risk.runtime.evidence_screenshots`** — locates each cited Evidence item on
  its physical page and renders one PNG per item. Localisation is matched against
  the page's own text lines (`get_text("dict")`), so "how many times does this text
  appear on this page" is an exact count rather than an inference from geometry: a
  hit that wraps across two visual lines returns two rectangles and would otherwise
  be indistinguishable from two separate occurrences.
- **`scripts/build_v045_evidence_screenshots.py`** — reads case artifacts that
  already exist, re-opens the prospectus the run verified, and writes
  `screenshots/*.png`, a per-case `screenshot_manifest.json` and a matrix-level
  `screenshot_summary.json`. It never re-analyses and never invents an item.
- The manifest binds every image to the source PDF SHA-256, the physical page, the
  geometry drawn, the anchors searched and the image's own SHA-256, as
  `docs/SUBMISSION_RUNBOOK.md` §9 requires.

### Governance

- **Granularity is never overstated.** `snippet_line_match` / `keyword_match` are
  coordinates PyMuPDF found for text that is in the retrieved snippet;
  `page_text_union` is the parser's page-level region and is reported as such;
  `unavailable` renders the page with no box drawn. A page union is never presented
  as a snippet box.
- **Only a unique match is drawn.** Text appearing on more than one line of the page
  cannot say which line the Evidence came from, so the anchor is rejected and
  recorded with its `matched_page_line_count` — the record of what was refused is
  what shows no box was guessed.
- **The source fails closed.** A PDF whose bytes do not match the SHA-256 the run
  verified is refused for the whole case; a missing prospectus, a page beyond the
  document and a failed render are each a recorded status rather than a missing row.
  No local path is written to any artifact.

### Changed

- The Evidence Viewer draws its box through the same localiser, so what a reviewer
  sees on screen is the geometry the submission ships, and its caption always names
  the granularity that was achieved. `evidence_catalog` now carries the Evidence
  metadata the localiser reads; the viewer's own `render_page_png` is removed rather
  than left as a second, page-level renderer.

### Measured, on current main

Three-case matrix over the authorised archive: 13 cited Evidence items, 13 rendered,
13 precisely localised, 0 page-level fallbacks, 0 unrendered.


## Unreleased — concentration extraction: duplicate label block, narrative period counts, receivable scope

Follow-up to the previous concentration work, driven by 0699.HK 均勝電子, whose
five financial risk codes produced no formal risk at all. Every rule was derived
from the 2020–2023 **development** cohort (376 documents); the 2025 blind
documents were used only to locate defects and confirm outcomes.

### Fixed

- **`_CONCENTRATION_LABELS` was defined twice, and the dead copy was the good
  one.** The previous change replaced a block whose end was located with
  `s.index("_LABELS = {")` — a substring of `_CONCENTRATION_LABELS = {` — so the
  rewrite was inserted above the original instead of replacing it. Both copies
  were wrap-tolerant, so every behavioural test passed while the later
  definition shadowed the earlier one and silently dropped the simplified-Chinese
  supplier labels (`最大供应商`, `五大供应商`). A parametrised test now pins
  simplified and traditional coverage for both counterparty kinds.
- **A neighbouring table header outranked the sentence carrying the
  percentages.** `_best_v03_periods` may resolve periods from a context chunk,
  and a track-record table prints a comparative interim column the narrative
  omits. Preferring whichever count was larger flagged correct series as
  mismatched. The sentence that established the series now governs.
- **Balance-sheet concentration was read as revenue concentration.** A
  prospectus also discloses "最大客戶的貿易應收款項……佔貿易應收款項總額的16.61%"
  over the same counterparties. Read as one series with the revenue figures, two
  unrelated metrics looked like contradictory readings of one fact. A segment
  whose denominator is a receivable or payable balance now contributes no values;
  scope is judged per segment, so one page can carry both disclosures.
- **A span phrase was counted as an enumeration.** "截至2021年12月31日止三個年度
  及2022年首四個月" covers four periods while naming one date and one year.
  Counting the named periods under-counted the series and flagged an 83.3%
  top-five supplier share — a high risk — as a mismatch. Such a sentence now
  yields no count and the resolved periods govern instead.

### Not changed, deliberately

`selected_period` still takes the last entry of `periods`, which arrives in
document order rather than chronological order, so a table caption below the
narrative can date a 2025 reading to 2022. Selecting the chronologically latest
period is correct in isolation and was measured on the development cohort:
clean customer readings 18 → 15, supplier 27 → 18, and 48 additional
`conflicting_values_for_same_period`. Dating facts accurately makes far more of
them collide in the merge's latest-period bucket, and the merge voids a period
the moment any two candidates disagree by any amount. The brittle merge has to
be fixed before this selection can be. The reverted change is documented in a
comment at the call site.

### Development cohort (376 documents, 2020–2023)

| | before | after |
|---|---|---|
| clean `customer_concentration` | 18 | 24 |
| clean `supplier_concentration` | 27 | 33 |
| baseline clean values the fix changes | — | **0** |
| `conflicting_values_for_same_period` (customer) | 141 | 129 |
| `largest_percentage_exceeds_top_five` (customer / supplier) | 39 / 53 | 35 / 52 |
| `value_period_count_mismatch` (customer / supplier) | 152 / 151 | 142 / 140 |

One customer reading regressed: 01490 CHESHI keeps its values (17.7 / 50.4) but
gains `value_period_count_mismatch`. Both figures sit under the 30 / 60 medium
thresholds, so the rule returns `not_applicable` either way and no risk is lost.
The cause is understood: its sentence both enumerates its years *and* carries a
span phrase, and the span guard is blunt enough to fire on either. Separating the
two cases means tuning a new heuristic on two documents, which is not worth a
clean-but-riskless reading.

### Confirmation on 2025 blind (not used to choose any rule)

0699.HK 均勝電子 is a profitable, growing auto-parts maker; all five financial
rules should return no risk, and `cash_runway` already established that from the
cash-flow statement. This change lets `customer_concentration` establish
`largest = 23.2%` where it previously established nothing.
`supplier_concentration` remains blocked on the reverted period selection, and
`customer_concentration`'s top-five figure remains blocked because the document
itself prints 47.2% in the business section and 47.1% in the summary.

## Unreleased — concentration extraction: wrapped labels, segment boundaries, narrative period series

Four independent defects made `customer_concentration` and
`supplier_concentration` almost inert: over the 2020–2023 **development**
cohort (376 documents) only 1 document produced a clean customer reading and 4
produced a clean supplier reading. Every rule below was derived from that
cohort; 0501.HK (2025 blind) was used only to confirm the outcome.

### Fixed

- **A hard line wrap split a label mid-word.** PDF text wraps as `最大客\n戶`,
  so the label went unmatched. That did not merely lose its own percentages:
  the *preceding* label's segment then ran on to the next match and absorbed
  them, so a top-five figure was silently recorded as the largest-customer
  figure. Labels are now matched wrap-tolerantly, with the gap bounded to
  `\s{0,2}` so a label cannot form across unrelated table cells.
- **A segment was bounded only by the next label of the same kind.** An
  intervening supplier paragraph therefore donated its percentages to the
  customer label above it. Both kinds of label now bound a segment, while only
  the requested kind collects values.
- **A narrative period series was counted by resolved dates alone.** A track
  record names its periods once ("於2022年、2023年、2024年以及截至2025年6月30日
  止六個月") and a later sentence refers back to it; only the interim stub
  resolves to a date, so a correct four-value series looked like a count
  mismatch against one period. `_enumerated_period_count` now reads the count
  from the sentence that established the series. It counts only — bare years
  are still never resolved to a calendar year end, so
  `test_bare_years_are_not_guessed_as_calendar_year_ends` is unchanged.
- **A page that read nothing could veto a page that read cleanly.** The merge
  unioned issues across every candidate for the selected period, so a customer
  table with no percentages, or a risk-factor paragraph quoting only the
  top-five figure, blocked a complete clean reading — and the rule builder
  rejects any fact carrying issues. A complete clean reading now governs;
  contradicting candidates still raise `conflicting_values_for_same_period`.

### Development cohort (376 documents, 2020–2023)

| | before | after |
|---|---|---|
| clean `customer_concentration` | 1 | 18 |
| clean `supplier_concentration` | 4 | 27 |
| clean readings regressed | — | **0** |
| baseline clean values the fix changes | — | **0** |
| `value_period_count_mismatch` (customer / supplier) | 221 / 224 | 152 / 151 |
| `largest_percentage_exceeds_top_five` (customer) | 54 | 39 |

No issue category increased except supplier `missing_period` (66 → 67).

Values churn inside the `needs_review` pool: 56 readings gained a value, 30
lost one, 34 changed. **None of the 30 losses was a clean reading**, so no risk
decision regressed. Some losses are improvements — 01597 納泉能源 reported
`top_five = 70` taken from a run ending `5%, 30%, 70%`, and the fix now
separates the series well enough for two candidates to disagree, turning a
garbage value into an honest conflict. One is a genuine quality loss: on 01645
海納智能 the wrap-tolerant label matches an incidental mention carrying a lone
`5%`, which conflicts with a plausible `38.3` and voids both. Both documents
stay `needs_review` either way, so neither changes a decision.

### Confirmation on 2025 blind (not used to choose any rule)

0501.HK 豪威集成電路, table path: `customer_concentration` extracts
L=25.8% / T5=50.3% and the rule returns `not_applicable` (both under the
30 / 60 medium thresholds); `supplier_concentration` extracts L=24.9% /
T5=62.4% and generates a medium risk (top-five ≥ 60). All five financial risk
codes now report a clean diagnosis; `cash_runway` remains blocked upstream in
retrieval and is untouched here.

## Unreleased — v0.4 table scenarios reachable from the UI

The v0.4 table configs shipped without a scenario entry, so the table document
path was unreachable for anyone driving the product through Streamlit. Selecting
"v0.4 AI 模式 + Final Supervisor" kept `parser: pymupdf` + `financial_extractor:
regex`, and the whole table path stayed invisible to the v0.4 workflow. Confirmed
on 0501.HK (豪威集成電路): the flat-text path produced **zero** financial risks —
`revenue_growth` failed `metric_label_not_found`, `continuous_loss` failed
`unsupported_layout` — while the same document on the table path extracts
`revenue_growth` (+15.13%, 9M2024 → 9M2025, CNY thousand) and generates a
`continuous_loss` pending risk.

### Fixed

- **`configs/v04_offline_table.yaml` and `configs/v04_ai_table.yaml` had no UI
  scenario.** Both are now wired into `SCENARIOS` next to their flat-text
  counterparts. No config file, workflow, agent or extractor changed; the two
  legacy v0.4 scenarios keep their exact wiring, and the default scenario is
  still `v0.4 离线模式 + Final Supervisor`.

### Added

- `tests/contract/test_ui_exposes_every_runtime_config.py` — a shipped runtime
  config with no scenario entry now fails the build. The test parses
  `SCENARIOS` with `ast` rather than importing `streamlit_app.py`, which renders
  at import time, and pins each v0.4 label to the document path it promises.

## Unreleased — v0.3 opt-in table path: column geometry and mixed annual/interim statements

Scoped strictly to the opt-in table path (`parser: pymupdf_table` +
`financial_extractor: table`, i.e. the `*_table.yaml` configs). The default
`pymupdf` parser, the `regex` financial extractor and the frozen 2410.HK
cash-runway regression (2.76 months, evidence pages 563/562) are unchanged.

Every rule and threshold below was derived from the 2020–2023 **development**
cohort — the period-header work on 24 documents / 3,695 reconstructed blocks, the
column-geometry work on all 320 development documents that reconstruct a grid at
all (28,382 anchored pages). The 2025 blind cohort was used only to confirm the
outcome, never to choose a feature or a parameter.

### Fixed

- **Blocks lost their period header.** A statement is split into several vertical
  blocks whenever a subtotal rule opens a gap, but only the topmost block sits
  under the caption — the rest scanned the *previous block's data rows* as their
  header. Blocks now inherit the nearest preceding header (all blocks on a page
  share one set of `value_anchors`, hence one column geometry) and the header
  scan is floored at the previous block's last row. Development cohort: blocks
  with no year header 1,457 → 381; blocks yielding no period at all 67.1% → 53.7%.
- **Mixed annual/interim tables collapsed into one period series.** A track-record
  table prints three full years beside two nine-month stubs, so `2024年` appears
  twice and the column count never matched a uniform three-period series — the
  real meaning of `value_period_count_mismatch` / `conflicting_values`. The parser
  now emits `period_columns`, pairing each value column with its own year label
  *and* the caption governing it, so the two `2024年` columns resolve to
  `2024-12-31` (12 months) and `2024-09-30` (9 months). Columns are split by the
  repeated-year cue where it fires and by caption geometry otherwise; on the
  development cohort the two agree on 270/285 headers and geometry additionally
  resolves 56/60 headers the repeat cue cannot split.
- **Scale-before-currency units resolved to nothing.** `千美元` / `千港元` /
  `百萬港元` put the scale in front of the currency, which the base grammar (a
  trailing `元`) cannot read, stalling every fact on `missing_unit`. These forms
  are 1,186 of the unit captions in the development cohort. Overridden in
  `TableAwareV03FinancialFactExtractor` only.
- **Right-aligned short cells were silently dropped.** `_assemble_row` snapped a
  value token to a year anchor by comparing x-*centres* within a 16pt tolerance,
  but statement columns are right-*aligned*: the offset between a token's centre
  and the year label centred above it is a function of the token's length, so a
  bare `–` overshoots its anchor while a seven-digit figure undershoots it. On the
  2020–2023 development cohort (320 documents, 28,382 anchored pages) 22.2% of the
  cells whose column is unambiguous — 553,488 cells on rows carrying exactly one
  value per anchor — sat further than 16pt from their own anchor, and the ones
  that overshot were dropped, leaving `""` in `cells` and surfacing downstream as
  `invalid_numeric_value`. Tokens are now assigned to the column whose x-interval
  contains them, the interval being the midpoints between adjacent anchors with
  the two outer bounds mirrored, which removes the tolerance rather than retuning
  it. Development cohort, forced-pairing rows reconstructed exactly: 68.8% → 93.3%
  (right-edge snapping at the same tolerance reached only 79.2%, so the intervals,
  not the anchor definition, are what buys the win); value tokens captured 64.1% →
  78.4%; of 204,390 rows accepted before, 204,124 are still accepted and 50,150
  new rows join them. The note-reference column stays out: of 14,768 tokens under
  an explicit 附註/Note header, 80 fall inside the widened first column, fewer than
  the 84 that already sat right of the label margin. `COL_SNAP` is renamed
  `HEADER_SNAP`, its only remaining use being the year-header-to-column match in
  `_period_columns` where both sides are year labels and the bias does not arise.

- **Dot leaders hid table revenue rows.** The frozen revenue patterns anchor on
  `(?:\s|$)` after the metric name, so a reconstructed label
  (`收入.................`) never matched and every revenue row fell through to
  the lower-confidence flattened-text path. Leader runs are now collapsed for
  matching only.

### Fixed (second pass: labels, units, duplicate readings)

- **Wrapped row labels lost everything but their tail.** A statement prints a long
  caption over several lines and the figures on the last one, so reading a single
  visual row hands the extractor the caption's tail — and a tail can name a
  different metric than the whole: 「年內利潤及全面」/「收入總額」 is *profit and total
  comprehensive income*, but the value line reads as 收入總額, so the row's net
  profit was extracted as the company's revenue. Lines directly above a data row
  that carry no value and sit entirely left of the first value column are now
  rejoined in reading order. Development cohort: 2,718 of 17,501 data rows wrap;
  rejoining changes which metric 46 rows match and every change is a correction
  (「出售物業、廠房及設備的收益」 — a disposal gain — stops reading as revenue, and 31
  total-comprehensive-income rows start reading as the net result).
- **The money unit was read from the whole page instead of the grid's caption.**
  A summary page prints its table in 千元 while the prose beside it quotes 百萬元;
  a whole-page scan sees two scales, resolves neither, and the page then disagrees
  with the statement page about the unit of an identical figure, so the series is
  discarded for conflicting values. The cash-runway table path already resolved
  the caption first; the period-series path now does too.
- **The flattened-text fallback could invent rows the grid does not have.** With
  no coordinates it matches the metric name wherever it appears — in prose, in a
  segment note, under 非香港財務報告準則計量, or as the tail of a wrapped caption
  (「…金融資產的公允價值收益」 read as 收益). On a page the parser reconstructed, the
  grid is now the authority: no matching grid row means the row is absent. On the
  development cohort, text-only readings of a page that already has a grid
  disagree with that grid's column count 79 times out of 126, and the ones that
  agree are no more likely to be the metric.
- **The same figure cited by three pages counted as three observations.** A
  prospectus prints one figure in the summary, in MD&A and in the audited
  statements. Left un-merged, the growth rule sorted by period end, took the
  latest fact as "current" and its own duplicate as "previous", and the skill
  rejected the pair as `period_order_invalid`. Exact agreement on period, value,
  currency and unit now merges into one observation that keeps every citation;
  any genuine disagreement still reports `conflicting_values_for_same_period`.
- **One unreadable page discarded an otherwise clean series.** Retrieval returns
  five pages and one is regularly a statement of changes in equity, whose columns
  are share capital / premium / accumulated losses rather than periods. Its
  readings arrive already marked defective, but a single issue anywhere forced
  the whole series to review. A defective reading is evidence that a page could
  not be read, not evidence about the value, so it no longer outvotes a clean
  one; only observations carrying their own issues are dropped, conflicts are
  recomputed over the survivors, and disagreement among clean readings still
  blocks. Dropped pages are recorded in `unreadable_pages`.

### Added

- `configs/v04_offline_table.yaml` and `configs/v04_ai_table.yaml`. v0.4 shipped
  on `parser: pymupdf` + `financial_extractor: regex`, so none of the table work
  was reachable from the current workflow. These are the v0.4 workflow with the
  two document-intelligence components swapped and nothing else changed; the
  frozen `v04_offline.yaml` / `v04_ai.yaml` keep their behaviour, and a contract
  test pins that the pairs differ in exactly those two fields.

### Verified (second pass)

- 1,570 tests pass, including the frozen 2410.HK E2E regression.
- 經發物業 01354 (2024): per-risk diagnostics identical to the pre-change
  baseline, and `revenue_growth` reproduces `21.99030582216588192683810214`
  over 2022-12-31 → 2023-12-31 exactly.
- MiniMax 00100 (2025, blind — confirmation only): first clean financial
  extraction. `continuous_loss` now generates a pending risk (two consecutive
  nine-month losses, 9M2024 −304,342 and 9M2025 −512,013 千美元) and
  `revenue_growth` resolves to `not_applicable` at +174.68%, correctly pairing
  9M2025 against 9M2024 rather than against FY2024.

### Added

- `period_columns`, `period_header_source`, `period_group_lines`,
  `period_basis_mixed` and `local_header_lines` on reconstructed tables;
- `period_axis`, `period_basis` (`annual` / `interim`) and `period_group_line` on
  every fact produced by the table path, so a downstream rule can see whether it
  holds a full year or a nine-month stub;
- `period_column_unresolved`, recorded when a column carries a value the column
  map cannot date (an empty spare column stays silent).

### Verified

- 1,558 tests pass, including the frozen 2410.HK E2E regression (2.76 months,
  evidence pages 563/562).
- 經發物業 01354 (2024): byte-identical per-risk diagnostics through the
  mixed-period work above. The right-alignment fix **does** move this case, and
  the move is a downstream consequence rather than a parser defect: physical
  pages 26–27 (概要) now reconstruct their whole summary income statement instead
  of a single row, the retriever's `structured_table_row` signal (+0.30) lifts
  them into the top five, and `revenue_growth` turns from `not_applicable`
  (growth 21.99%) into `conflicting_values`. Both causes are separate known
  weaknesses, not new ones: page 27 prints 「年內利潤及全面／收入總額」 across two
  lines, so the row label reconstructs as the tail `收入總額` and matches the
  revenue metric, and the 概要 page carries no unit caption of its own
  (`missing_unit`). The 593,660 / 706,816 / 862,247 revenue series itself is
  unchanged and agrees across pages 26, 340 and 447.
- Development cohort outcome (32 documents, 2020–2023, `v03_offline_table`):
  543 → 538 diagnostic issue instances; `invalid_numeric_value` 12 → 5, while
  `ambiguous_empty_value_symbol` rises 22 → 26 because a recovered dash is now
  reported as the empty-value symbol it is instead of vanishing into a hole.
- MiniMax 00100 (2025, blind — confirmation only): on physical page 542 the two
  dashes and the `(3)` that the 16pt tolerance dropped are captured, and
  `invalid_numeric_value` is eliminated from `revenue_growth` with the retrieved
  evidence pages unchanged. `continuous_loss` keeps an `invalid_numeric_value`
  from physical page 589, a statement of changes in equity whose columns are not
  fiscal years — a different defect, untouched here.
- MiniMax 00100 (2025, blind — confirmation only): `unit_missing_or_ambiguous`
  and `missing_unit` eliminated on all five risk codes; `missing_period`
  eliminated on `continuous_loss`; `value_period_count_mismatch` eliminated on
  `revenue_growth`. The consolidated income statement now yields a clean
  five-period mixed series and the growth rule pairs 9M2025 against 9M2024
  rather than against FY2024.

## v0.3.0-multi-agent-risk-analysis — 2026-08-12

Released as the frozen multi-Agent document-risk analysis product. Formal
Golden metrics are published as measured and remain below planned research
targets; no post-evaluation tuning was performed.

### Final technical completion (owner-waived human certification)

- integrated real Financial, Legal and Business Agents into the shared registry and container;
- added deterministic `SpecializedVerifierRouter`, `V03Supervisor` and `enhanced_v2`;
- exposed offline and optional AI-enhanced runtime modes through `IPOAnalysisService`;
- added Streamlit domain views and Markdown/JSON downloads;
- added structured v0.3 reporting and explicit evaluation provenance;
- preserved `mvp_v1`, Mock mode and the released v0.2 regression;
- deferred Financial 23-row and Business 3-row independent human second review by explicit owner waiver;
- did not claim formal Financial/Business or combined cross-domain Golden metrics;
- did not access the 2025 blind set or start v0.4 market prediction work.

### Final product completion

- completed the product-first Streamlit experience with IPO Profile, overall rule-score
  dashboard, domain status, risk cards, Supervisor and runtime diagnostics;
- expanded Markdown/JSON downloads to preserve Evidence, Calculation, Verifier and
  structured section metadata;
- froze the deterministic v0.3 report at ten auditable sections;
- added explicit cross-domain supervisory synthesis and rule-score components without
  inventing a new verified risk or probability;
- kept Golden governance `PARTIAL` while classifying it as a research-validation
  limitation rather than a software release blocker;
- preserved public Schema/Protocol boundaries, `mvp_v1`, Mock and v0.2 behavior.

### Human Golden final closeout

- froze `single_named_human_review_v1`, permanently removing independent second
  review as a Financial/Business release requirement;
- promoted 23 Financial and 3 Business named-human primary reviews as
  `first_reviewed`, without populating `second_reviewer`;
- preserved all eight Legal double-reviewed/adjudicated judgments unchanged;
- completed provenance-filtered Financial, Legal, Business and cross-domain evaluation;
- superseded the active Owner waiver while preserving it as historical audit provenance;
- closed all Gate A items without using 2025 blind data or tuning production behavior.

### Merged

- PR #20：新增`CatalogIPODataProvider`、特殊证券治理、批量运行、断点续跑、2025盲测保护和黄金案例评测基础设施；
- PR #21：新增Planner → Executor基础设施，包括`execute-approved-plan` Skill、Plan Validator、Scope Guard和Execution Report工作区；
- PR #23：完成八类v0.3 Retriever查询族、简繁英别名、确定性章节权重和稳定Evidence追溯；
- PR #22：合并Financial v0.3核心链路，包括财务事实抽取、Decimal Skills、`V03FinancialAgent`和`V03FinancialVerifier`；
- PR #24：合并OpenAI-compatible、Mock和Unavailable LLMProvider，配置驱动装配、有限重试、安全异常分类及Pydantic结构化校验。

### Current validation

- 本次技术收口基线：`main@b60570ef0854b198c6e4827336cb4a3b529fe462`；
- 完整自动化测试：893 passed；
- 项目校验、赛事数据校验、Golden manifest integrity、compileall与diff check通过；
- Streamlit Mock与v0.3 offline真实PDF浏览器smoke通过；
- 2410.HK回归：706页、0解析错误、Evidence第563/562页、现金跑道2.76个月、verified、90/critical。

### Remaining limitations

- 正式Golden采用一次具名人工复核政策，不应误称为独立双审评测；
- 真实外部LLM endpoint smoke未执行；
- 1167.HK、9633.HK和Legal真实demo fixture在本次本地执行中不可用；
- PDF报告导出未加入，本版支持Markdown和结构化JSON；
- v0.4 Market Agent、标签、概率模型尚未开始。

本节是开发中状态，不代表已创建v0.3 Release。

## v0.2.0-real-document-slice - 2026-08-06

Release: https://github.com/richardssheik107-hub/hk-ipo-risk-agents/releases/tag/v0.2.0-real-document-slice

### Added

- PyMuPDF真实PDF解析与关键词Evidence检索；
- 现金和经营现金流确定性提取；
- 现金跑道Calculation、RiskItem及专用Verifier；
- 真实CashRunwayFinancialAgent；
- unavailable专业Agent、市场数据Provider及request IPO Provider；
- Service metadata、持久化往返验证和真实Service级E2E；
- Streamlit安全PDF上传、组件模式及完整证据链展示。

### Validation

- 自动化测试：284 passed；
- PR #17 GitHub Actions：pytest与compileall通过；
- 2410.HK：现金第563页、经营现金流第562页；
- 现金跑道：2.76个月，verified，critical / 90；
- 无真实市场数据时保持90分并明确进入degraded模式；
- 规则评分不输出概率。
- 赛事数据校验、项目校验与编译检查通过；
- 565份招股书manifest、555/10行情覆盖与562/3官方IPO主数据桥接完成。
- 远程main全新克隆、Python 3.12.10虚拟环境安装和完整验收通过；
- 2410.HK第562/563页已完成第二次独立证据复核；
- Streamlit真实场景与Predictor故障降级场景人工验收通过。

### Fixed

- Extractor或Risk Builder异常时刷新Financial Agent结构化失败诊断；
- Streamlit PDF上传增加200 MB显式大小上限。

### Known Limitations

- 真实链路只覆盖现金跑道，Legal、Business和Market Agent仍不可用；
- LLMProvider未进入生产链路，ReportGenerator仍为Mock格式化实现；
- 规则分不是上市后下跌概率；扫描型PDF/OCR和统计预测模型尚未实现。

## v0.1.0-architecture-mvp

### Added

- Pydantic 公共 Schema 与结构化 AnalysisError；
- 配置驱动的组件装配；
- LangGraph mvp_v1 工作流；
- RuleVerifier、RuleSupervisor 与 RuleBasedPredictor；
- 确定性金融 Skill；
- JSON Repository 与 Streamlit 页面；
- 节点故障降级、契约与端到端测试。

### Validation

- pytest -q：24 passed；
- Mock 健康检查：completed，3 条已核验风险、1 条待核验风险；
- Predictor 故障可降级为 partial。

### Mock Components

- DocumentParser、DocumentRetriever；
- 四类专业 Agent；
- LLM、市场和 IPO 数据 Provider；
- ReportGenerator。
