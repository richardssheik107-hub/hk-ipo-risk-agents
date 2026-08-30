# V0.4.6 Role-B Source-Edition Unlock Audit

Status: `SOURCE_UNLOCK_PARTIAL`

This Development-only shadow audit evaluates whether official HKEX English
prospectus editions remove the apparent M1 ceiling created by the current
Traditional-Chinese catalog. It does not modify the production catalog, Gold,
Validation, Blind, Track A outputs, or runtime scoring contracts. No real LLM
call was made.

## Policy decision

The original competition document describes the supplied dataset as three to
five years of prospectus PDFs and asks the prototype to accept a company name,
stock code, or prospectus file. It neither requires a specific language
edition nor expressly authorizes replacing supplied files with an internet
edition. The correct classification is therefore `SOURCE_POLICY_AMBIGUOUS`.

Official HKEX counterparts may be used for shadow research and provenance
testing. They must not silently overwrite the production catalog or be treated
as a passed competition gate without an integration-owner policy decision.

## Gold-independent discovery

The resolver uses only stock code, disclosure date, the official HKEX active
stock index, and official HKEX title-search metadata. It requires the official
Listing Documents category and generic prospectus titles, queries English and
Traditional Chinese independently, falls back to the official delisted-security
index when needed, and binds editions by stock code, release date, and filing
class. Gold text, Gold pages, risk labels, company-specific
rules, and case-specific URL maps are not inputs to discovery.

For all 14 audited source-mismatch cases:

- official English prospectus found: `14/14`;
- official Traditional-Chinese prospectus found: `14/14`;
- high-confidence bilingual filing relation: `14/14`;
- current catalog byte-identical to official Chinese PDF: `11/14`;
- non-identical current bytes requiring separate provenance treatment:
  `ipo_2022_00314`, `ipo_2022_01204`, `ipo_2022_02372`.

The safe per-document URL/hash inventory is in
`docs/research/v046_source_unlock_provenance.json`.

## M1 fact recoverability versus M2 exact-anchor mismatch

The earlier phrase “21 M1 units are impossible from Chinese” is too broad.
Evaluator-only post-run checks show:

- affected positive M1 units: `21`;
- facts already surfaced by the current Chinese pipeline: `11/21`;
- additional facts deterministically present in the official Chinese PDF:
  `10/21`;
- underlying facts recoverable from Chinese: `21/21`;
- affected exact English M2 anchors: `27`;
- those exact English anchors absent from the current Chinese edition: `27/27`.

Thus the underlying risk facts are not English-only. The hard edition mismatch
is exact English evidence provenance. M1 can still score as incorrect under the
frozen protocol when required evidence does not match, so fact availability
must not be confused with achieved M1.

## Targeted offline benchmark

The isolated English shadow catalog was run through the current deterministic
offline parser/retriever/evaluator for the 14 cases.

| Cohort | Edition | M1 | M2 | Real LLM calls |
| --- | --- | ---: | ---: | ---: |
| 14 source-mismatch cases, current batch076 baseline | current Chinese | 0/21 | 0/27 | 0 |
| same 14 cases, source-unlock shadow | official English | 2/21 | 9/27 | 0 |
| 3 non-mismatch controls, current batch076 baseline | current Chinese | 4/10 | 11/19 | 0 |
| same 3 controls, substitution shadow | official English | 0/10 | 0/19 | 0 |

The targeted English run proves genuine candidate/evidence gain, but does not
unlock the M1 ceiling by itself. It also proves that global English substitution
is unsafe. Adding the observed targeted gains to the current ALL79 checkpoint
would produce at most `35/102` M1 and `71/191` M2 if every gain transferred
without conflict, still far below the release thresholds. An ALL79 rerun was
therefore not justified.

## Integration contract

The safe strategy is
`language_neutral_all_official_prospectus_editions`, not English-primary
replacement.

An integration implementation must:

1. retain the supplied/current document and add official counterparts as
   versioned documents;
2. assign a stable retrieval `document_id` containing case, authority,
   language, and content-hash identity;
3. keep filing identity separate from document identity so bilingual editions
   are related but never conflated;
4. deduplicate evidence within a document by document/page/span identity and
   across translations only after semantic-equivalence verification;
5. preserve source URL, language, release time, hash, page geometry, and parser
   origin on every candidate and Evidence record;
6. keep missing editions explicit and never proxy-fill or translate evidence;
7. require integration-owner approval before any production catalog or metric
   protocol change.

Do not merge an English-only manifest, do not replace the 14 current PDFs, and
do not claim `SOURCE_UNLOCK_READY` from metadata discovery alone.

## Reproduction

Use `scripts/build_v046_source_unlock_shadow_catalog.py` to build an isolated
catalog and `scripts/audit_v046_source_fact_recoverability.py` for the
evaluator-only fact audit. The focused unit suite is:

```text
python -m pytest tests/unit/test_hkex_official_editions.py tests/unit/test_source_edition_audit.py -q
```

Expected result: `10 passed`.
