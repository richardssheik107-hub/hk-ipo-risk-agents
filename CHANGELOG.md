# Changelog

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
