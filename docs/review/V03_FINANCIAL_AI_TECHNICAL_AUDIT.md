# V03 Financial Golden AI Technical Preaudit

> **THIS IS AI TECHNICAL PREAUDIT ONLY**
>
> **NOT HUMAN GOLDEN REVIEW**
> **NOT FORMAL GOLDEN TRUTH**

```text
AI_TECHNICAL_PREAUDIT_IS_HUMAN_REVIEW = false
CODEX_IS_PRIMARY_REVIEWER = false
CODEX_IS_SECOND_REVIEWER = false
CODEX_IS_ADJUDICATOR = false
```

## Scope and controls

- Baseline: `main@885afe7b6584886433f5ed584aa85f2a805f270e`
- Canonical source: `tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv`
- Scope: 23 Financial rows with `reviewer=member-3` and `review_status=draft`, across six companies.
- Rules: `v03_contract_v1`, loaded from the frozen YAML configuration.
- This document does not change `reviewer`, `second_reviewer`, `review_status`, or `GATE-A-03`.
- The canonical Manifest remains unchanged. No 2025 blind-set document was accessed.
- Evidence excerpts below are limited to the short text already present in the Manifest. Context findings are paraphrased.

## AI label definitions

Allowed labels are `AI_SUPPORTED_DRAFT`, `AI_DISAGREES_WITH_DRAFT`,
`AI_NEEDS_HUMAN_CONTEXT`, `AI_EVIDENCE_MISMATCH`,
`AI_CALCULATION_MISMATCH`, `AI_PERIOD_OR_UNIT_AMBIGUITY`, and
`AI_UNSUPPORTED_LAYOUT`.

## Company audit results

### 2410.HK 同源康醫藥-B — 4 rows reviewed

PDF identity and layout: the repository's existing 706-page prospectus was used. Physical pages 558, 562, and 563 exist. Page 558 is the audited statement of profit or loss and other comprehensive income; pages 562-563 are consecutive audited cash-flow statement pages. Necessary adjacent-page context was checked. The table headers identify annual periods ending 31 December and three-month periods ending 31 March, with currency/unit `CNY / thousand`.

#### `real_case_001` / `cash_runway` / physical page 562

- Manifest evidence: `經營活動所用淨現金流量 (220,053) (200,944) (56,986) (83,918)`
- Page/text check: matched on physical page 562; it is a company-specific cash-flow statement line, not a risk-factor template.
- Column check: 2024-03-31 three-month value is `-83,918`; `period_months=3`; `CNY / thousand`.
- Cross-page support: page 563 supplies the matching period-end cash balance.
- Decimal recalculation: `77208 / (abs(-83918) / 3) = 2.7601229771...`, displayed `2.76 months` using the frozen Skill rounding.
- Threshold check: `2.76 < 3`, therefore `critical`.
- AI label: `AI_SUPPORTED_DRAFT`.
- Human must confirm: physical page and column alignment; that page 562 and page 563 are treated as a single calculation evidence pair.
- Extra page required: page 563 (already checked); no further page identified by AI.

#### `real_case_001` / `cash_runway` / physical page 563

- Manifest evidence: `現金流量表所述現金及現金等價物 90,762 186,830 111,745 77,208`
- Page/text check: matched on physical page 563; the 2024-03-31 value is `77,208`.
- Period/unit check: same three-month reporting column and `CNY / thousand` basis as page 562.
- Decimal recalculation and threshold: same paired calculation, `2.76 months`, `critical`.
- AI label: `AI_SUPPORTED_DRAFT`.
- Human must confirm: exact physical page, final column, and consistency with the operating cash-flow evidence on page 562.
- Extra page required: page 562 (already checked); no further page identified by AI.

#### `real_case_001` / `continuous_loss` / physical page 558

- Manifest evidence: `年內╱期內虧損 (311,802) (383,171) (83,214) (107,778)`
- Page/text check: matched in the audited income statement. It is net loss for the year/period, not operating loss or cash flow.
- Period/unit check: annual 2022 and 2023 values are `-311,802` and `-383,171`, both `12 months`, `CNY / thousand`. The two interim columns are separately comparable and do not alter the annual two-period classification.
- Decimal/deterministic check: latest selected comparable annual sequence contains `2` losses.
- Threshold check: `2 periods => medium`.
- AI label: `AI_SUPPORTED_DRAFT`.
- Human must confirm: annual rather than interim pair is the intended Golden comparison and that the shortest quoted row remains sufficient.
- Extra page required: adjacent statement header/context was checked; no additional page identified by AI.

#### `real_case_001` / `revenue_growth` / physical page 558

- Manifest evidence: `收入 44,242 – – –`
- Page/text check: matched on the formal audited income statement.
- Period/unit check: annual 2022 revenue is `44,242`; annual 2023 is a dash in the formal revenue row; `12 months`, `CNY / thousand`.
- Normalization requiring human attention: the draft treats the formal dash for 2023 annual revenue as zero. The page layout supports that interpretation, but the human reviewer must personally confirm zero-versus-not-disclosed semantics.
- Decimal recalculation: `(0 - 44242) / 44242 * 100 = -100.00%`.
- Threshold check: `-100.00% <= -20%`, therefore `high`.
- AI label: `AI_SUPPORTED_DRAFT`.
- Human must confirm: dash-to-zero normalization and annual column alignment.
- Extra page required: adjacent statement context was checked; no additional page identified by AI.

### 1167.HK 加科思-B — 2 rows reviewed

PDF identity and layout: the streamed 2020 prospectus is 520 physical pages. Physical pages 287 and 416 exist. Page 287 is the company-specific supplier section; page 416 is the audited statement of profit or loss. The necessary adjacent paragraphs/pages were checked. No yearly ZIP or full-document text cache was written to disk.

#### `ipo_2020_01167` / `continuous_loss` / physical page 416

- Manifest evidence: `年內╱期內虧損 (155,935) (425,817) (155,055) (810,904)`
- Page/text check: matched on the formal audited statement. It is net loss for the year/period, not operating loss or cash flow.
- Period/unit check: annual 2018 and 2019 values are `-155,935` and `-425,817`, both `12 months`, `CNY / thousand`; 2019/2020 six-month columns are separately identified.
- Decimal/deterministic check: the selected comparable annual sequence contains `2` losses.
- Threshold check: `2 periods => medium`.
- AI label: `AI_SUPPORTED_DRAFT`.
- Human must confirm: annual column selection and that the interim columns are not mixed with annual periods.
- Extra page required: statement header and adjacent continuation were checked; no further page identified by AI.

#### `ipo_2020_01167` / `supplier_concentration` / physical page 287

- Manifest evidence: the disclosed five-largest supplier percentages are `43.5%, 48.4%, 42.4%`; largest supplier percentages are `11.0%, 19.1%, 20.8%`.
- Page/text check: matched in the dedicated raw-materials and suppliers section and is explicitly based on total purchases.
- Period check: latest period is the six months ended 2020-06-30; `period_months=6`.
- Percentage check: latest largest supplier `20.8%` is not above latest top five `42.4%`; both are in 0-100 percent semantics.
- Threshold check: `20.8 < 30` and `42.4 < 60`, therefore not applicable under the frozen medium thresholds.
- AI label: `AI_SUPPORTED_DRAFT`.
- Human must confirm: the latest-period ordering and use of total-purchase percentages rather than raw purchase amounts.
- Extra page required: surrounding supplier paragraphs were checked; no additional page identified by AI.

### 1541.HK 宜明昂科-B — 4 rows reviewed

PDF identity and layout: the streamed 2023 prospectus is 570 physical pages. Physical pages 329, 331, and 384 exist. Pages 329/331 are the company-specific supplier/customer sections; page 384 is a formal financial-information table. Necessary adjacent pages were checked to confirm table continuation and period labels.

#### `ipo_2023_01541` / `continuous_loss` / physical page 384

- Manifest evidence: `年╱期內虧損 (732,949) (402,894) (149,109) (111,766)`
- Page/text check: matched in the formal selected comprehensive income statement; it is net loss, not operating loss.
- Period/unit check: annual 2021 and 2022 are `-732,949` and `-402,894`, `12 months`, `CNY / thousand`; four-month comparative columns remain separate.
- Deterministic check: `2` comparable annual loss periods.
- Threshold check: `2 periods => medium`.
- AI label: `AI_SUPPORTED_DRAFT`.
- Human must confirm: annual column selection and separation from four-month interim columns.
- Extra page required: adjacent financial-information context checked; no further page identified by AI.

#### `ipo_2023_01541` / `revenue_growth` / physical page 384

- Manifest evidence: `收入 5,067 538 234 73`
- Page/text check: matched in the formal financial-information table.
- Period/unit check: annual 2021/2022 values `5,067` and `538`, both `12 months`, `CNY / thousand`.
- Decimal recalculation: `(538 - 5067) / 5067 * 100 = -89.3822774...%`, displayed `-89.38%`.
- Threshold check: `-89.38% <= -20%`, therefore `high`.
- AI label: `AI_SUPPORTED_DRAFT`.
- Human must confirm: selected annual columns and exact value transcription.
- Extra page required: no additional page identified by AI.

#### `ipo_2023_01541` / `customer_concentration` / physical page 331

- Manifest evidence: latest largest customer `43.6%`; latest top five customers `89.1%`.
- Page/text check: matched in the customer section and supported by the same-page four-month table ending 2023-04-30.
- Period check: latest period `2023-04-30`, `period_months=4`.
- Percentage check: `43.6 <= 89.1`, both use 0-100 percent semantics.
- Threshold check: `89.1 >= 80`, therefore `high`.
- AI label: `AI_SUPPORTED_DRAFT`.
- Human must confirm: latest-period selection and table total.
- Extra page required: adjacent historical customer table checked; no further page identified by AI.

#### `ipo_2023_01541` / `supplier_concentration` / physical page 329

- Manifest evidence: latest top-five suppliers `40.7%`; latest single largest supplier `16.0%`.
- Page/text check: matched in the supplier section; percentages are expressly based on total purchases.
- Period check: latest period `2023-04-30`, `period_months=4`.
- Percentage check: `16.0 <= 40.7`, both within 0-100.
- Threshold check: `16.0 < 30` and `40.7 < 60`, therefore not applicable.
- AI label: `AI_SUPPORTED_DRAFT`.
- Human must confirm: period ordering and that the disclosed denominator is total purchases.
- Extra page required: page 330 supplier table was checked as context; no further page identified by AI.

### 8489.HK 裕程物流 — 4 rows reviewed

PDF identity and layout: the streamed 2020 GEM prospectus is 430 physical pages. Physical pages 142, 152, and 299 exist. Pages 142/152 are company-specific customer/supplier sections; page 299 is the accountant's report. Adjacent tables and continuation pages were checked to confirm chronological order and denominators.

#### `ipo_2020_08489` / `revenue_growth` / physical page 299

- Manifest evidence: `收益 425,414 463,050 353,341 214,318 553,367`
- Page/text check: matched in the formal combined income statement.
- Period/unit check: latest comparable eight-month values are `214,318` and `553,367`, both ending 31 August and using `HKD / thousand`.
- Decimal recalculation: `(553367 - 214318) / 214318 * 100 = 158.20...%`, positive.
- Threshold check: growth is `>= 0%`, therefore not applicable. The earlier annual 2018-to-2019 decline is correctly not substituted for the latest comparable pair.
- AI label: `AI_SUPPORTED_DRAFT`.
- Human must confirm: latest eight-month column alignment rather than stale annual selection.
- Extra page required: adjacent accountant-report context checked; no further page identified by AI.

#### `ipo_2020_08489` / `continuous_loss` / physical page 299

- Manifest evidence: `年╱期內溢利（虧損） 12,614 4,238 (7,439) 194 26,320`
- Page/text check: matched in the formal combined income statement.
- Period/unit check: annual 2017/2018 profits, annual 2019 loss, and comparable eight-month 2019/2020 profits are separately identified; `HKD / thousand`.
- Deterministic check: the latest comparable interim period is profitable, and there is only one annual loss; latest loss streak is zero.
- Threshold check: fewer than 2 latest comparable loss periods, therefore not applicable.
- AI label: `AI_SUPPORTED_DRAFT`.
- Human must confirm: annual/interim separation and use of the latest comparable period.
- Extra page required: no further page identified by AI.

#### `ipo_2020_08489` / `customer_concentration` / physical page 142

- Manifest evidence: latest largest customer `37.5%`; latest five largest customers `68.0%`.
- Page/text check: matched in the customer section; page 141 table and page 142 narrative agree.
- Period check: latest eight-month period in 2020, `period_months=8`.
- Percentage check: `37.5 <= 68.0`, both within 0-100.
- Threshold check: `37.5 >= 30` or `68.0 >= 60`, therefore `medium`.
- AI label: `AI_SUPPORTED_DRAFT`.
- Human must confirm: latest-period identity and agreement between narrative and table.
- Extra page required: page 141 cross-check already inspected; no further page identified by AI.

#### `ipo_2020_08489` / `supplier_concentration` / physical page 152

- Manifest evidence: latest largest supplier `22.6%`; latest top five suppliers `68.0%`.
- Page/text check: matched in the supplier section and based on total service cost; historical supplier tables continue on adjacent pages.
- Period check: latest eight-month period in 2020, `period_months=8`.
- Percentage check: `22.6 <= 68.0`, both within 0-100.
- Threshold check: top five `68.0 >= 60`, therefore `medium`.
- AI label: `AI_SUPPORTED_DRAFT`.
- Human must confirm: denominator is total service cost and the latest eight-month values are correctly selected.
- Extra page required: surrounding supplier table pages checked; no further page identified by AI.

### 2503.HK 中深建業 — 5 rows reviewed

PDF identity and layout: the streamed 2023 prospectus is 522 physical pages. All Manifest pages exist. AI also located the formal audited equivalents on page 395 for income/revenue and pages 181-182 for supplier concentration. This exposed three evidence-selection questions because the Manifest currently points to summary pages despite a formal source being available.

#### `ipo_2023_02503` / `continuous_loss` / physical page 250

- Manifest evidence: `本公司擁有人應佔年╱期內溢利╱（虧損）及全面收益╱（虧損）總額 13,559 28,076 25,325 (4,381) 10,787`
- Page/text check: the text and values match page 250, but that page is explicitly an operating-results summary extracted from the accountant's report.
- Formal cross-check: the same row and values appear on physical page 395 in the accountant's report.
- Period/unit check: three annual profits and comparable six-month loss/profit columns, `CNY / thousand`; latest comparable interim value is positive.
- Deterministic check: latest loss streak is zero; not applicable.
- AI label: `AI_NEEDS_HUMAN_CONTEXT`.
- Objective reason: conclusion and values are supported, but the Annotation Guide says a summary should not replace an available formal primary statement.
- Human must confirm: whether canonical primary evidence should move from page 250 to page 395 while page 250 remains a cross-check.
- Extra page required: page 395, already located and checked by AI.

#### `ipo_2023_02503` / `revenue_growth` / physical page 250

- Manifest evidence: `收益 1,331,204 1,346,219 1,378,055 371,857 495,780`
- Page/text check: values match page 250's operating-results summary.
- Formal cross-check: identical values appear on physical page 395 in the accountant's report.
- Period/unit check: latest comparable six-month values `371,857` and `495,780`, `CNY / thousand`.
- Decimal recalculation: `(495780 - 371857) / 371857 * 100 = 33.3254449...%`, displayed `33.33%`.
- Threshold check: positive growth, therefore not applicable.
- AI label: `AI_NEEDS_HUMAN_CONTEXT`.
- Objective reason: numeric conclusion is consistent, but the current primary page is a summary when a formal statement exists.
- Human must confirm: primary page 395 versus summary cross-check page 250.
- Extra page required: page 395, already checked by AI.

#### `ipo_2023_02503` / `customer_concentration` / physical page 165

- Manifest evidence: latest largest customer contribution is `13.5%`, with historical percentages `20.6%, 20.9%, 14.9%, 13.5%`.
- Page/text check: matched in the company-specific customer section; page 165 continues the period narrative from page 164.
- Period check: latest six months ended 2023-06-30, `period_months=6`.
- Cross-check: page 164's customer table reports top five `45.9%` and largest `13.5%`.
- Threshold check: `13.5 < 30` and `45.9 < 60`, therefore not applicable.
- AI label: `AI_SUPPORTED_DRAFT`.
- Human must confirm: page 164/165 are treated together and the latest-period alignment.
- Extra page required: page 164, already checked.

#### `ipo_2023_02503` / `customer_concentration` / physical page 164

- Manifest evidence: `五大客戶合計 226,909 45.9`
- Page/text check: matched in the latest six-month customer table.
- Percentage check: top five `45.9%`, largest `13.5%`, valid ordering and 0-100 semantics.
- Threshold check: both below medium thresholds; not applicable.
- AI label: `AI_SUPPORTED_DRAFT`.
- Human must confirm: same-risk cross-check role and linkage to the narrative on page 165.
- Extra page required: page 165, already checked.

#### `ipo_2023_02503` / `supplier_concentration` / physical page 12

- Manifest evidence: latest top five suppliers `23.4%`; latest largest supplier `6.1%`.
- Page/text check: exact text and values match physical page 12, but page 12 is the prospectus summary.
- Formal cross-check: the supplier section repeats the disclosure on physical pages 181-182, including latest `23.4%` and `6.1%`.
- Period check: latest six months ended 2023-06-30, `period_months=6`.
- Threshold check: `6.1 < 30` and `23.4 < 60`, therefore not applicable.
- AI label: `AI_NEEDS_HUMAN_CONTEXT`.
- Objective reason: conclusion is numerically consistent, but summary page 12 currently substitutes for available formal business evidence.
- Human must confirm: whether pages 181-182 should become the canonical primary evidence and page 12 only a cross-check.
- Extra page required: pages 181-182, already located and checked by AI.

### Running count after 2503.HK

- Rows technically preaudited: 19 / 23
- `AI_SUPPORTED_DRAFT`: 16
- `AI_NEEDS_HUMAN_CONTEXT`: 3
- Other AI labels: 0
- Technical conclusions contradicted: 0
- Human confirmation points: all 19 rows; three 2503.HK rows require a primary-evidence-page decision.

### 9633.HK 農夫山泉 — 4 rows reviewed

PDF identity and layout: the streamed 2020 prospectus is 549 physical pages. Physical pages 116, 141, and 313 exist. Pages 116/141 are company-specific customer/supplier disclosures; page 313 is the accountant's report and formal consolidated income statement. Physical renderings and adjacent pages 115-117, 140-142, and 312-314 were checked.

#### `ipo_2020_09633` / `continuous_loss` / physical page 313

- Manifest evidence: `年╱期內溢利 3,385,949 3,611,712 4,954,244 2,359,953 1,930,887`
- Page/text check: matched in the formal consolidated income statement; the row is profit for the year/period, not operating profit or cash flow.
- Period/unit check: 2017-2019 annual columns and comparable five-month 2019/2020 columns are clearly separated; `CNY / thousand`.
- Deterministic check: all annual and comparable interim values are positive; latest loss streak is zero.
- Threshold check: fewer than two latest comparable loss periods, therefore not applicable.
- AI label: `AI_SUPPORTED_DRAFT`.
- Human must confirm: annual/interim separation and positive-value transcription.
- Extra page required: adjacent accountant-report pages were checked; no further page identified by AI.

#### `ipo_2020_09633` / `revenue_growth` / physical page 313

- Manifest evidence: `收益 17,491,214 20,475,045 24,021,041 9,917,234 8,663,655`
- Page/text check: matched in the formal consolidated income statement.
- Period/unit check: latest comparable periods are the five months ended 2019-05-31 and 2020-05-31, values `9,917,234` and `8,663,655`; `CNY / thousand`.
- Decimal recalculation: `(8663655 - 9917234) / 9917234 * 100 = -12.6404096...%`, displayed `-12.64%`.
- Threshold check: `< 0%` and `> -20%`, therefore `medium`.
- AI label: `AI_SUPPORTED_DRAFT`.
- Human must confirm: latest five-month column alignment and value transcription.
- Extra page required: no additional page identified by AI.

#### `ipo_2020_09633` / `customer_concentration` / physical page 116

- Manifest evidence: latest top-five customers `5.1%`; latest single largest customer `2.4%`.
- Page/text check: matched in the customer section and supported by the same-page channel table; the denominator is total revenue.
- Period check: latest five months ended 2020-05-31, `period_months=5`.
- Percentage check: `2.4 <= 5.1`, both within 0-100.
- Threshold check: `2.4 < 30` and `5.1 < 60`, therefore not applicable.
- AI label: `AI_SUPPORTED_DRAFT`.
- Human must confirm: latest-period ordering and total-revenue denominator.
- Extra page required: pages 115 and 117 were checked; no further page identified by AI.

#### `ipo_2020_09633` / `supplier_concentration` / physical page 141

- Manifest evidence: latest top-five suppliers `31.8%`; latest single largest supplier `11.2%`.
- Page/text check: matched in the dedicated supplier section; percentages are expressly based on total purchases.
- Period check: latest five months ended 2020-05-31, `period_months=5`.
- Percentage check: `11.2 <= 31.8`, both within 0-100.
- Threshold check: `11.2 < 30` and `31.8 < 60`, therefore not applicable.
- AI label: `AI_SUPPORTED_DRAFT`.
- Human must confirm: supplier identity, latest-period ordering, and total-purchase denominator.
- Extra page required: pages 140 and 142 were checked; no further page identified by AI.

## Final technical-preaudit summary

| Category | Rows |
|---|---:|
| No obvious technical issue; still requires human confirmation | 20 |
| Calculation or threshold mismatch | 0 |
| Requires a primary-evidence/context decision | 3 |
| AI disagrees with the current draft conclusion | 0 |
| AI unable to determine | 0 |
| **Total** | **23** |

AI label totals:

- `AI_SUPPORTED_DRAFT`: 20
- `AI_NEEDS_HUMAN_CONTEXT`: 3
- `AI_DISAGREES_WITH_DRAFT`: 0
- All other allowed labels: 0

The three context decisions are `ipo_2023_02503 / continuous_loss / page 250`, `ipo_2023_02503 / revenue_growth / page 250`, and `ipo_2023_02503 / supplier_concentration / page 12`. Their numeric conclusions are reproducible, but a real human must decide whether the available formal pages 395 and 181-182 should replace the current summary pages as canonical primary evidence.

All 23 rows still require individual human primary review. This audit has not changed the canonical Manifest and cannot close `GATE-A-03`.
