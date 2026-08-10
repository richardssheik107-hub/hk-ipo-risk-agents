# V03 Legal Human Golden Review Packet

## 1. Purpose

This is the self-contained human review packet for the eight Legal A–H
development draft cases. It is human-review infrastructure, not accuracy
evidence, an automated annotation result, or formal Golden truth.

The current case information below is copied from
`tests/fixtures/v03_golden_cases/v03_legal_golden_case_manifest.csv` at
`main@f1e792a85dd4266471509c76e0079ed042c1f175`. Each case section is explicitly
labelled **CURRENT AI/CODEX PRESELECTION DRAFT**. A human reviewer must inspect
the original prospectus PDF and reach an independent conclusion. AI/Codex may
not act as primary reviewer, second reviewer, or adjudicator.

```text
CODEX_IS_HUMAN_REVIEWER = false
HUMAN_PRIMARY_REVIEW_COMPLETE = false
INDEPENDENT_SECOND_REVIEW_COMPLETE = false
FORMAL_LEGAL_GOLDEN_READY = false
GATE_A_05 = FAIL
GATE_A_06 = FAIL
```

This packet does not modify the Legal draft CSV or canonical v0.3 Golden
Manifest.

## 2. Frozen Legal Policy and Allowed Values

The Legal Agent owns only:

- `redemption_rights`
- `material_litigation_compliance`

The frozen v0.3 Legal production candidate severity for both risks is:

```text
level = medium
score = 50
level_is_provisional = true
score_is_rule_based = true
score_is_probability = false
```

The Legal Agent does not self-verify. Legal Verifiers do not upgrade severity
to `high` or `critical`.

Allowed human review values:

- Applicable: `true`, `false`
- Expected Status: `verified`, `needs_review`, `rejected`
- Expected Level: `low`, `medium`, `high`, `critical`, `not_applicable`

The enum may support `high` and `critical`, but reviewers must not create a new
Legal severity policy. Current v0.3 Legal production candidates remain
provisional `medium / 50`.

Human Golden `expected_status` and Agent initial `verification_status` are not
identical concepts. The Agent initially emits only `pending` or `needs_review`.
Golden `verified` means the evidence can ultimately be confirmed under the full
human/Verifier standard; it does not require the Agent to self-verify.

## 3. Human Review Procedure and Independence

```text
Codex preselection
        ↓
Human Primary Review
        ↓
Independent Human Second Review
        ↓
Compare results
        ↓
Record disagreement
        ↓
Human adjudication when required
        ↓
double_reviewed / adjudicated
        ↓
canonical manifest merge by data maintainer
```

Mandatory independence rules:

- Primary reviewer and second reviewer must be different real humans.
- The second reviewer must not see the primary reviewer's `applicable`,
  `expected_status`, `expected_level`, or reasoning before completing the
  independent decision.
- A reviewer must not self-review.
- AI/Codex must not be recorded as reviewer or adjudicator.
- `codex_preselection != human primary reviewer`.
- Every reviewer must inspect the original prospectus PDF, including the stated
  physical page, exact short text, preceding paragraph, and following paragraph.
  Inspect adjacent pages before/after whenever context may change the result.

Only the short evidence already present in the draft manifest is reproduced
below. Reviewers must consult the PDF rather than expanding copyrighted text in
this packet.

---

## CASE A

### Identity

- Case ID: `ipo_2021_09898`
- Stock Code: `9898.HK`
- Company: `微博－ＳＷ`
- Document ID: `ipo_2021_09898`
- Risk Code: `redemption_rights`

### Current AI/Codex Preselection Draft

- Applicable: `true`
- Gold Physical Page: `300`
- Exact Short Evidence: “截至本文件日期，該等權利仍然有效且預計在上市後仍然有效。”
- Draft Expected Status: `verified`
- Draft Expected Level: `high`
- Draft Reviewer: `codex_preselection`
- Draft Second Reviewer: `(empty)`
- Draft Review Status: `draft`
- Draft Notes: `gold_case=A; dataset_split=development; section=關聯方交易; board representation and registration rights remain effective after listing; primary; pending independent human review`

**THIS SECTION IS PRESELECTION ONLY. DO NOT TREAT AS HUMAN GOLD.**

- Human primary review: **NOT COMPLETED**
- Independent second review: **NOT COMPLETED**
- Formal Golden status: **NOT READY**

### Frozen Policy Relevant to This Case

The draft `high` is a **PRE-POLICY DRAFT SUGGESTION**, not the authoritative
v0.3 Legal level. Review the level independently against the frozen provisional
`medium / 50` policy. Do not modify production severity policy during review.
Confirm whether the disclosed rights genuinely remain effective after listing
and whether the surrounding context limits their lifecycle or holder.

### PDF Inspection Guidance

Inspect original prospectus physical page 300, the preceding and following
paragraphs, and adjacent pages if they contain the right's holder, termination,
waiver, restoration, or listing-timing conditions.

### Primary Human Review Checklist

- [ ] stock_code / company verified
- [ ] document_id verified
- [ ] physical PDF page verified
- [ ] exact_text matches PDF
- [ ] preceding and following paragraphs reviewed
- [ ] adjacent pages reviewed if necessary
- [ ] evidence is prospectus evidence
- [ ] evidence is not misleading when read in context
- [ ] applicable independently determined
- [ ] expected_status independently determined
- [ ] expected_level reviewed against frozen medium/50 Legal policy
- [ ] ambiguity documented

### Primary Human Review Form

| Field | Human entry |
|---|---|
| Human Primary Reviewer | |
| Review Date | |
| Verified Physical Page | |
| Adjacent Pages Reviewed | |
| Human Applicable | |
| Human Expected Status | |
| Human Expected Level | |
| Evidence Accurate: yes/no | |
| Evidence Complete Enough: yes/no | |
| Reasoning | |
| Disagreement With Preselection | |
| Additional Notes | |

### Independent Second Review Form

> **DO NOT READ PRIMARY REVIEW CONCLUSION BEFORE INDEPENDENT REVIEW.**

| Field | Independent human entry |
|---|---|
| Second Reviewer | |
| Review Date | |
| Verified Physical Page | |
| Adjacent Pages Reviewed | |
| Independent Applicable | |
| Independent Expected Status | |
| Independent Expected Level | |
| Evidence Accurate: yes/no | |
| Evidence Complete Enough: yes/no | |
| Independent Reasoning | |
| Disagreement | |
| Notes | |

### Adjudication

- Required: `only if primary and second review disagree`

| Field | Human adjudication entry |
|---|---|
| Adjudicator | |
| Date | |
| Final Applicable | |
| Final Expected Status | |
| Final Expected Level | |
| Decision Reason | |
| Disagreement Summary | |

---

## CASE B

### Identity

- Case ID: `ipo_2022_09863`
- Stock Code: `9863.HK`
- Company: `零跑汽車`
- Document ID: `ipo_2022_09863`
- Risk Code: `redemption_rights`

### Current AI/Codex Preselection Draft

- Applicable: `false`
- Gold Physical Page: `207`
- Exact Short Evidence: “截至最後實際可行日期，所有特別權利已失效並終止。”
- Draft Expected Status: `rejected`
- Draft Expected Level: `not_applicable`
- Draft Reviewer: `codex_preselection`
- Draft Second Reviewer: `(empty)`
- Draft Review Status: `draft`
- Draft Notes: `gold_case=B; dataset_split=development; section=歷史、發展及公司架構; historical rights expressly terminated before listing; negative control; pending independent human review`

**THIS SECTION IS PRESELECTION ONLY. DO NOT TREAT AS HUMAN GOLD.**

- Human primary review: **NOT COMPLETED**
- Independent second review: **NOT COMPLETED**
- Formal Golden status: **NOT READY**

### Frozen Policy Relevant to This Case

Determine whether “all special rights” truly covers every relevant right,
whether termination occurred before/on listing, and whether any restoration,
revival, waiver, or listing-failure exception survives. A termination sentence
alone is not sufficient if surrounding context qualifies it.

### PDF Inspection Guidance

Inspect original prospectus physical page 207, preceding/following paragraphs,
and adjacent pages for restoration, revival, waiver, listing-failure, or timing
exceptions.

### Primary Human Review Checklist

- [ ] stock_code / company verified
- [ ] document_id verified
- [ ] physical PDF page verified
- [ ] exact_text matches PDF
- [ ] preceding and following paragraphs reviewed
- [ ] adjacent pages reviewed if necessary
- [ ] evidence is prospectus evidence
- [ ] evidence is not misleading when read in context
- [ ] applicable independently determined
- [ ] expected_status independently determined
- [ ] expected_level reviewed against frozen medium/50 Legal policy
- [ ] ambiguity documented

### Primary Human Review Form

| Field | Human entry |
|---|---|
| Human Primary Reviewer | |
| Review Date | |
| Verified Physical Page | |
| Adjacent Pages Reviewed | |
| Human Applicable | |
| Human Expected Status | |
| Human Expected Level | |
| Evidence Accurate: yes/no | |
| Evidence Complete Enough: yes/no | |
| Reasoning | |
| Disagreement With Preselection | |
| Additional Notes | |

### Independent Second Review Form

> **DO NOT READ PRIMARY REVIEW CONCLUSION BEFORE INDEPENDENT REVIEW.**

| Field | Independent human entry |
|---|---|
| Second Reviewer | |
| Review Date | |
| Verified Physical Page | |
| Adjacent Pages Reviewed | |
| Independent Applicable | |
| Independent Expected Status | |
| Independent Expected Level | |
| Evidence Accurate: yes/no | |
| Evidence Complete Enough: yes/no | |
| Independent Reasoning | |
| Disagreement | |
| Notes | |

### Adjudication

- Required: `only if primary and second review disagree`

| Field | Human adjudication entry |
|---|---|
| Adjudicator | |
| Date | |
| Final Applicable | |
| Final Expected Status | |
| Final Expected Level | |
| Decision Reason | |
| Disagreement Summary | |

---

## CASE C — LEGAL_GOLDEN_ADJUDICATION_REQUIRED

### Identity

- Case ID: `ipo_2023_02517`
- Stock Code: `2517.HK`
- Company: `鍋圈`
- Document ID: `ipo_2023_02517`
- Risk Code: `redemption_rights`

### Current AI/Codex Preselection Draft

- Applicable: `true`
- Gold Physical Page: `152`
- Exact Short Evidence: “所終止權利在下列若干情況下（包括：(i)上市申請已被撤回或拒絕；或(ii)首次公開發售自有關終止起計24個月內並無進行）將自動恢復。”
- Draft Expected Status: `needs_review`
- Draft Expected Level: `medium`
- Draft Reviewer: `codex_preselection`
- Draft Second Reviewer: `(empty)`
- Draft Review Status: `draft`
- Draft Notes: `gold_case=C; dataset_split=development; section=歷史、發展及公司架構; restoration is conditional on listing failure or delay and must not be labelled mechanically as a continuing right; primary; pending independent human review`

**THIS SECTION IS PRESELECTION ONLY. DO NOT TREAT AS HUMAN GOLD.**

- Human primary review: **NOT COMPLETED**
- Independent second review: **NOT COMPLETED**
- Formal Golden status: **NOT READY**

### Frozen Policy Relevant to This Case

Rights terminate but may automatically restore if the listing application is
withdrawn/rejected or the IPO is not completed within the stated period. Frozen
Builder behavior is:

```text
clear restoration condition
→ BUILT + PENDING
→ enters Verifier
```

The dispute is not a code bug. It concerns how Golden truth should express a
conditional restoration scenario. Do not change the Builder or imply that code
must be changed to pass Golden.

Each reviewer must independently answer:

1. Should Golden represent this as a candidate entering verification, or as
   legal ambiguity requiring `needs_review`?
2. Is the restoration condition sufficiently explicit?
3. Is this a current post-listing continuing right or a listing-failure
   contingency?
4. How should `expected_status` express the frozen system semantics?

### PDF Inspection Guidance

Inspect original prospectus physical page 152, preceding/following paragraphs,
and adjacent pages for the complete termination and restoration lifecycle,
timing, waiver, and listing-outcome conditions.

### Primary Human Review Checklist

- [ ] stock_code / company verified
- [ ] document_id verified
- [ ] physical PDF page verified
- [ ] exact_text matches PDF
- [ ] preceding and following paragraphs reviewed
- [ ] adjacent pages reviewed if necessary
- [ ] evidence is prospectus evidence
- [ ] evidence is not misleading when read in context
- [ ] applicable independently determined
- [ ] expected_status independently determined
- [ ] expected_level reviewed against frozen medium/50 Legal policy
- [ ] ambiguity documented

### Primary Human Review Form

| Field | Human entry |
|---|---|
| Human Primary Reviewer | |
| Review Date | |
| Verified Physical Page | |
| Adjacent Pages Reviewed | |
| Human Applicable | |
| Human Expected Status | |
| Human Expected Level | |
| Evidence Accurate: yes/no | |
| Evidence Complete Enough: yes/no | |
| Reasoning | |
| Disagreement With Preselection | |
| Additional Notes | |

### Independent Second Review Form

> **DO NOT READ PRIMARY REVIEW CONCLUSION BEFORE INDEPENDENT REVIEW.**

| Field | Independent human entry |
|---|---|
| Second Reviewer | |
| Review Date | |
| Verified Physical Page | |
| Adjacent Pages Reviewed | |
| Independent Applicable | |
| Independent Expected Status | |
| Independent Expected Level | |
| Evidence Accurate: yes/no | |
| Evidence Complete Enough: yes/no | |
| Independent Reasoning | |
| Disagreement | |
| Notes | |

### Adjudication

- Required: **YES**
- Final decision: **must remain blank until real human adjudication**

| Field | Human adjudication entry |
|---|---|
| Adjudicator | |
| Date | |
| Final Applicable | |
| Final Expected Status | |
| Final Expected Level | |
| Decision Reason | |
| Disagreement Summary | |

---

## CASE D

### Identity

- Case ID: `ipo_2020_01961`
- Stock Code: `1961.HK`
- Company: `九尊數字互娛`
- Document ID: `ipo_2020_01961`
- Risk Code: `redemption_rights`

### Current AI/Codex Preselection Draft

- Applicable: `true`
- Gold Physical Page: `78`
- Exact Short Evidence: “首次公開發售前投資者享有提早贖回權，可按有關首次公開發售前可換股債券工具所載方式行使。”
- Draft Expected Status: `needs_review`
- Draft Expected Level: `medium`
- Draft Reviewer: `codex_preselection`
- Draft Second Reviewer: `(empty)`
- Draft Review Status: `draft`
- Draft Notes: `gold_case=D; dataset_split=development; section=風險因素; prospectus confirms the right but refers operative terms to another instrument and does not state a complete termination status; primary; pending independent human review`

**THIS SECTION IS PRESELECTION ONLY. DO NOT TREAT AS HUMAN GOLD.**

- Human primary review: **NOT COMPLETED**
- Independent second review: **NOT COMPLETED**
- Formal Golden status: **NOT READY**

### Frozen Policy Relevant to This Case

The prospectus confirms an early redemption right but refers operative terms
to another instrument and does not provide a complete termination lifecycle.
Reviewers must decide whether the available prospectus Evidence is sufficient,
whether adjacent pages disclose more of the referenced instrument, and whether
`needs_review` is genuinely caused by evidence incompleteness.

### PDF Inspection Guidance

Inspect original prospectus physical page 78, preceding/following paragraphs,
and adjacent pages for the referenced convertible instrument, termination,
waiver, restoration, holder, and listing-timing terms.

### Primary Human Review Checklist

- [ ] stock_code / company verified
- [ ] document_id verified
- [ ] physical PDF page verified
- [ ] exact_text matches PDF
- [ ] preceding and following paragraphs reviewed
- [ ] adjacent pages reviewed if necessary
- [ ] evidence is prospectus evidence
- [ ] evidence is not misleading when read in context
- [ ] applicable independently determined
- [ ] expected_status independently determined
- [ ] expected_level reviewed against frozen medium/50 Legal policy
- [ ] ambiguity documented

### Primary Human Review Form

| Field | Human entry |
|---|---|
| Human Primary Reviewer | |
| Review Date | |
| Verified Physical Page | |
| Adjacent Pages Reviewed | |
| Human Applicable | |
| Human Expected Status | |
| Human Expected Level | |
| Evidence Accurate: yes/no | |
| Evidence Complete Enough: yes/no | |
| Reasoning | |
| Disagreement With Preselection | |
| Additional Notes | |

### Independent Second Review Form

> **DO NOT READ PRIMARY REVIEW CONCLUSION BEFORE INDEPENDENT REVIEW.**

| Field | Independent human entry |
|---|---|
| Second Reviewer | |
| Review Date | |
| Verified Physical Page | |
| Adjacent Pages Reviewed | |
| Independent Applicable | |
| Independent Expected Status | |
| Independent Expected Level | |
| Evidence Accurate: yes/no | |
| Evidence Complete Enough: yes/no | |
| Independent Reasoning | |
| Disagreement | |
| Notes | |

### Adjudication

- Required: `only if primary and second review disagree`

| Field | Human adjudication entry |
|---|---|
| Adjudicator | |
| Date | |
| Final Applicable | |
| Final Expected Status | |
| Final Expected Level | |
| Decision Reason | |
| Disagreement Summary | |

---

## CASE E

### Identity

- Case ID: `ipo_2022_06698`
- Stock Code: `6698.HK`
- Company: `星空華文`
- Document ID: `ipo_2022_06698`
- Risk Code: `material_litigation_compliance`

### Current AI/Codex Preselection Draft

- Applicable: `true`
- Gold Physical Page: `26`
- Exact Short Evidence: “截至最後實際可行日期，我們在兩起重大未決訴訟案件中擔任被告人，總索賠金額為約人民幣140.9百萬元。”
- Draft Expected Status: `verified`
- Draft Expected Level: `high`
- Draft Reviewer: `codex_preselection`
- Draft Second Reviewer: `(empty)`
- Draft Review Status: `draft`
- Draft Notes: `gold_case=E; dataset_split=development; section=概要／合規與訴訟; actual material pending proceedings with defendant role and quantified claims; primary; pending independent human review`

**THIS SECTION IS PRESELECTION ONLY. DO NOT TREAT AS HUMAN GOLD.**

- Human primary review: **NOT COMPLETED**
- Independent second review: **NOT COMPLETED**
- Formal Golden status: **NOT READY**

### Frozen Policy Relevant to This Case

The draft `high` is a **PRE-POLICY DRAFT SUGGESTION**, not the authoritative
v0.3 Legal level. Review independently against frozen provisional `medium / 50`.
Confirm an actual proceeding, materiality, pending status, defendant/subject
identity, claim amount, and whether later resolution, settlement, payment, or
adjacent context changes the current status.

### PDF Inspection Guidance

Inspect original prospectus physical page 26, preceding/following paragraphs,
and adjacent pages for identities, amount, current status, resolution,
settlement, payment, remediation, or other qualifying disclosure.

### Primary Human Review Checklist

- [ ] stock_code / company verified
- [ ] document_id verified
- [ ] physical PDF page verified
- [ ] exact_text matches PDF
- [ ] preceding and following paragraphs reviewed
- [ ] adjacent pages reviewed if necessary
- [ ] evidence is prospectus evidence
- [ ] evidence is not misleading when read in context
- [ ] applicable independently determined
- [ ] expected_status independently determined
- [ ] expected_level reviewed against frozen medium/50 Legal policy
- [ ] ambiguity documented

### Primary Human Review Form

| Field | Human entry |
|---|---|
| Human Primary Reviewer | |
| Review Date | |
| Verified Physical Page | |
| Adjacent Pages Reviewed | |
| Human Applicable | |
| Human Expected Status | |
| Human Expected Level | |
| Evidence Accurate: yes/no | |
| Evidence Complete Enough: yes/no | |
| Reasoning | |
| Disagreement With Preselection | |
| Additional Notes | |

### Independent Second Review Form

> **DO NOT READ PRIMARY REVIEW CONCLUSION BEFORE INDEPENDENT REVIEW.**

| Field | Independent human entry |
|---|---|
| Second Reviewer | |
| Review Date | |
| Verified Physical Page | |
| Adjacent Pages Reviewed | |
| Independent Applicable | |
| Independent Expected Status | |
| Independent Expected Level | |
| Evidence Accurate: yes/no | |
| Evidence Complete Enough: yes/no | |
| Independent Reasoning | |
| Disagreement | |
| Notes | |

### Adjudication

- Required: `only if primary and second review disagree`

| Field | Human adjudication entry |
|---|---|
| Adjudicator | |
| Date | |
| Final Applicable | |
| Final Expected Status | |
| Final Expected Level | |
| Decision Reason | |
| Disagreement Summary | |

---

## CASE F

### Identity

- Case ID: `ipo_2023_02451`
- Stock Code: `2451.HK`
- Company: `綠源集團控股`
- Document ID: `ipo_2023_02451`
- Risk Code: `material_litigation_compliance`

### Current AI/Codex Preselection Draft

- Applicable: `false`
- Gold Physical Page: `298`
- Exact Short Evidence: “第一及第二案例已結案，判決總額人民幣2.9百萬元（或約為截至2022年12月31日總資產的0.1%）已獲悉數支付。”
- Draft Expected Status: `rejected`
- Draft Expected Level: `not_applicable`
- Draft Reviewer: `codex_preselection`
- Draft Second Reviewer: `(empty)`
- Draft Review Status: `draft`
- Draft Notes: `gold_case=F; dataset_split=development; section=業務; historical cases are closed and paid with no disclosed continuing material impact; negative control; pending independent human review`

**THIS SECTION IS PRESELECTION ONLY. DO NOT TREAT AS HUMAN GOLD.**

- Human primary review: **NOT COMPLETED**
- Independent second review: **NOT COMPLETED**
- Formal Golden status: **NOT READY**

### Frozen Policy Relevant to This Case

Confirm whether all relevant matters are closed, whether payment is sufficient
to treat them as resolved, and whether any continuing litigation, remediation,
licence, operational, or other material impact remains. Independently determine
whether `rejected / not_applicable` is justified.

### PDF Inspection Guidance

Inspect original prospectus physical page 298, preceding/following paragraphs,
and adjacent pages for other proceedings, appeal, continuing impact,
remediation, licence effects, or unpaid obligations.

### Primary Human Review Checklist

- [ ] stock_code / company verified
- [ ] document_id verified
- [ ] physical PDF page verified
- [ ] exact_text matches PDF
- [ ] preceding and following paragraphs reviewed
- [ ] adjacent pages reviewed if necessary
- [ ] evidence is prospectus evidence
- [ ] evidence is not misleading when read in context
- [ ] applicable independently determined
- [ ] expected_status independently determined
- [ ] expected_level reviewed against frozen medium/50 Legal policy
- [ ] ambiguity documented

### Primary Human Review Form

| Field | Human entry |
|---|---|
| Human Primary Reviewer | |
| Review Date | |
| Verified Physical Page | |
| Adjacent Pages Reviewed | |
| Human Applicable | |
| Human Expected Status | |
| Human Expected Level | |
| Evidence Accurate: yes/no | |
| Evidence Complete Enough: yes/no | |
| Reasoning | |
| Disagreement With Preselection | |
| Additional Notes | |

### Independent Second Review Form

> **DO NOT READ PRIMARY REVIEW CONCLUSION BEFORE INDEPENDENT REVIEW.**

| Field | Independent human entry |
|---|---|
| Second Reviewer | |
| Review Date | |
| Verified Physical Page | |
| Adjacent Pages Reviewed | |
| Independent Applicable | |
| Independent Expected Status | |
| Independent Expected Level | |
| Evidence Accurate: yes/no | |
| Evidence Complete Enough: yes/no | |
| Independent Reasoning | |
| Disagreement | |
| Notes | |

### Adjudication

- Required: `only if primary and second review disagree`

| Field | Human adjudication entry |
|---|---|
| Adjudicator | |
| Date | |
| Final Applicable | |
| Final Expected Status | |
| Final Expected Level | |
| Decision Reason | |
| Disagreement Summary | |

---

## CASE G

### Identity

- Case ID: `ipo_2020_09600`
- Stock Code: `9600.HK`
- Company: `新紐科技`
- Document ID: `ipo_2020_09600`
- Risk Code: `material_litigation_compliance`

### Current AI/Codex Preselection Draft

- Applicable: `false`
- Gold Physical Page: `222`
- Exact Short Evidence: “截至最後實際可行日期，我們並無涉及對我們或我們的任何董事提出的可能對我們的業務、財務狀況或經營業績有重大不利影響的尚未解決的或（據我們所知）可能面臨的任何重大訴訟或仲裁程序。”
- Draft Expected Status: `rejected`
- Draft Expected Level: `not_applicable`
- Draft Reviewer: `codex_preselection`
- Draft Second Reviewer: `(empty)`
- Draft Review Status: `draft`
- Draft Notes: `gold_case=G; dataset_split=development; section=業務／法律訴訟及合規; explicit no-material-litigation confirmation; negative control; pending independent human review`

**THIS SECTION IS PRESELECTION ONLY. DO NOT TREAT AS HUMAN GOLD.**

- Human primary review: **NOT COMPLETED**
- Independent second review: **NOT COMPLETED**
- Formal Golden status: **NOT READY**

### Frozen Policy Relevant to This Case

This is an explicit negative case. Confirm that it is issuer-specific rather
than generic boilerplate, is tied to the last practicable date, and is not
qualified by same-page or adjacent-page actual matters. Independently determine
whether `rejected / not_applicable` is justified.

### PDF Inspection Guidance

Inspect original prospectus physical page 222, preceding/following paragraphs,
and adjacent pages for exceptions, actual proceedings, arbitration,
investigation, penalties, or other material matters.

### Primary Human Review Checklist

- [ ] stock_code / company verified
- [ ] document_id verified
- [ ] physical PDF page verified
- [ ] exact_text matches PDF
- [ ] preceding and following paragraphs reviewed
- [ ] adjacent pages reviewed if necessary
- [ ] evidence is prospectus evidence
- [ ] evidence is not misleading when read in context
- [ ] applicable independently determined
- [ ] expected_status independently determined
- [ ] expected_level reviewed against frozen medium/50 Legal policy
- [ ] ambiguity documented

### Primary Human Review Form

| Field | Human entry |
|---|---|
| Human Primary Reviewer | |
| Review Date | |
| Verified Physical Page | |
| Adjacent Pages Reviewed | |
| Human Applicable | |
| Human Expected Status | |
| Human Expected Level | |
| Evidence Accurate: yes/no | |
| Evidence Complete Enough: yes/no | |
| Reasoning | |
| Disagreement With Preselection | |
| Additional Notes | |

### Independent Second Review Form

> **DO NOT READ PRIMARY REVIEW CONCLUSION BEFORE INDEPENDENT REVIEW.**

| Field | Independent human entry |
|---|---|
| Second Reviewer | |
| Review Date | |
| Verified Physical Page | |
| Adjacent Pages Reviewed | |
| Independent Applicable | |
| Independent Expected Status | |
| Independent Expected Level | |
| Evidence Accurate: yes/no | |
| Evidence Complete Enough: yes/no | |
| Independent Reasoning | |
| Disagreement | |
| Notes | |

### Adjudication

- Required: `only if primary and second review disagree`

| Field | Human adjudication entry |
|---|---|
| Adjudicator | |
| Date | |
| Final Applicable | |
| Final Expected Status | |
| Final Expected Level | |
| Decision Reason | |
| Disagreement Summary | |

---

## CASE H

### Identity

- Case ID: `ipo_2020_01942`
- Stock Code: `1942.HK`
- Company: `MOG HOLDINGS`
- Document ID: `ipo_2020_01942`
- Risk Code: `material_litigation_compliance`

### Current AI/Codex Preselection Draft

- Applicable: `false`
- Gold Physical Page: `44`
- Exact Short Evidence: “於一般業務運營過程中，本集團可能面臨產生自勞工糾紛、與客戶及供應商的合約申索、知識產權侵犯申索及其他潛在第三方糾紛的負債。”
- Draft Expected Status: `rejected`
- Draft Expected Level: `not_applicable`
- Draft Reviewer: `codex_preselection`
- Draft Second Reviewer: `(empty)`
- Draft Review Status: `draft`
- Draft Notes: `gold_case=H; dataset_split=development; section=風險因素; generic future litigation exposure without an actual event; template-risk negative control; pending independent human review`

**THIS SECTION IS PRESELECTION ONLY. DO NOT TREAT AS HUMAN GOLD.**

- Human primary review: **NOT COMPLETED**
- Independent second review: **NOT COMPLETED**
- Formal Golden status: **NOT READY**

### Frozen Policy Relevant to This Case

Determine whether the disclosure is only generic future exposure without an
actual proceeding and whether it is merely risk-factor template language.
Check same-page and adjacent-page context for an actual matter that the short
evidence alone could omit. Independently determine whether
`rejected / not_applicable` is justified.

### PDF Inspection Guidance

Inspect original prospectus physical page 44, preceding/following paragraphs,
and adjacent pages for issuer-specific actual litigation, arbitration,
investigation, penalties, or other present matters.

### Primary Human Review Checklist

- [ ] stock_code / company verified
- [ ] document_id verified
- [ ] physical PDF page verified
- [ ] exact_text matches PDF
- [ ] preceding and following paragraphs reviewed
- [ ] adjacent pages reviewed if necessary
- [ ] evidence is prospectus evidence
- [ ] evidence is not misleading when read in context
- [ ] applicable independently determined
- [ ] expected_status independently determined
- [ ] expected_level reviewed against frozen medium/50 Legal policy
- [ ] ambiguity documented

### Primary Human Review Form

| Field | Human entry |
|---|---|
| Human Primary Reviewer | |
| Review Date | |
| Verified Physical Page | |
| Adjacent Pages Reviewed | |
| Human Applicable | |
| Human Expected Status | |
| Human Expected Level | |
| Evidence Accurate: yes/no | |
| Evidence Complete Enough: yes/no | |
| Reasoning | |
| Disagreement With Preselection | |
| Additional Notes | |

### Independent Second Review Form

> **DO NOT READ PRIMARY REVIEW CONCLUSION BEFORE INDEPENDENT REVIEW.**

| Field | Independent human entry |
|---|---|
| Second Reviewer | |
| Review Date | |
| Verified Physical Page | |
| Adjacent Pages Reviewed | |
| Independent Applicable | |
| Independent Expected Status | |
| Independent Expected Level | |
| Evidence Accurate: yes/no | |
| Evidence Complete Enough: yes/no | |
| Independent Reasoning | |
| Disagreement | |
| Notes | |

### Adjudication

- Required: `only if primary and second review disagree`

| Field | Human adjudication entry |
|---|---|
| Adjudicator | |
| Date | |
| Final Applicable | |
| Final Expected Status | |
| Final Expected Level | |
| Decision Reason | |
| Disagreement Summary | |

## 4. Canonical Merge Ownership

Reviewed Legal rows may be sent to the data maintainer for canonical v0.3
Golden Manifest merge only after all of the following are complete:

1. real human primary review for A–H;
2. independent human second review for A–H;
3. all disagreements documented and adjudicated;
4. mandatory Case C adjudication completed;
5. reviewer identities and provenance validated.

This packet does not directly modify either the Legal draft manifest or the
canonical manifest.

# Legal Human Review Completion Checklist

## Primary review

- [ ] Case A primary reviewed
- [ ] Case B primary reviewed
- [ ] Case C primary reviewed
- [ ] Case D primary reviewed
- [ ] Case E primary reviewed
- [ ] Case F primary reviewed
- [ ] Case G primary reviewed
- [ ] Case H primary reviewed

## Independent second review

- [ ] Case A second reviewed
- [ ] Case B second reviewed
- [ ] Case C second reviewed
- [ ] Case D second reviewed
- [ ] Case E second reviewed
- [ ] Case F second reviewed
- [ ] Case G second reviewed
- [ ] Case H second reviewed

## Governance completion

- [ ] Case C adjudicated
- [ ] all disagreements resolved
- [ ] reviewer identities are real humans
- [ ] primary and second reviewers are different humans
- [ ] no reviewer self-review
- [ ] AI/Codex is not recorded as reviewer or adjudicator
- [ ] 2025 blind data untouched
- [ ] reviewed rows ready for canonical merge
