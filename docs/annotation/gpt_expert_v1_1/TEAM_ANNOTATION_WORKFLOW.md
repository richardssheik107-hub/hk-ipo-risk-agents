# Team Annotation Workflow

## Primary pass

For each assigned Case:

1. open a completely new web ChatGPT conversation;
2. upload only the original prospectus PDF, Prompt Contract v1.1.1, common instructions,
   and that Case's blank JSON;
3. paste the frozen `PRIMARY_BLIND_ANNOTATION_PROMPT.md`;
4. do not upload Human Golden, human review, old GPT answers, audit results,
   Retriever/Agent output, market outcome labels, or post-listing returns;
5. use one conversation for one Case only;
6. do not copy answers across Cases;
7. save JSON only and do not manually repair the raw output;
8. run `scripts/validate_expert_annotation.py` locally with the manifest page count;
9. run `scripts/import_expert_annotation.py --stage pass1`; the importer preserves
   the raw GPT JSON and writes a separate `validation_result.json` under the ignored
   local results workspace. Its default inventory is the portable tracked
   `source_manifest.csv`, so no local PDF path is required;
10. never edit or replace the preserved pass output when validation fails;
11. update `team_case_assignment.csv` with progress only, never answers;
12. publish answers only to `annotation/gpt-expert-results` after the applicable
    team blind-boundary rule permits it.

Do not commit annotation answers or PDFs to the collaboration/docs branch.

## Independent second pass

The audit uses a new ChatGPT conversation with the PDF, Protocol, instructions,
Primary JSON, and `SECOND_PASS_AUDIT_PROMPT.md`. Its task is to find errors, not
rubber-stamp the first pass. Primary and second pass should not be handled by the
same person for the same Case. Audit output states are:

- `PASS`
- `REVISION_REQUIRED`
- `POLICY_AMBIGUITY`
- `HUMAN_ADJUDICATION_REQUIRED`

The detailed audit schema is not implemented in Phase 0.6B.1. Preserve later
artifacts as `pass2/expert_annotation_v2.json`, `audit/audit.json`, and
`final/expert_annotation_final.json`; never overwrite a previous stage.

## Assignment discipline

Claim work only in `team_case_assignment.csv`. Initial annotator/status fields are
blank. Never put credentials, local PDF paths or annotation answers in assignment
notes. Status values are restricted to `not_started`, `in_progress`, `completed`,
`validation_failed`, `needs_review`, `audit_completed`,
`adjudication_required`, and `finalized`.

The assignment CSV is a progress index, not an answer store. Result publication and
access boundaries are defined in [RESULT_STORAGE_POLICY.md](RESULT_STORAGE_POLICY.md).

Use interleaved/round-robin assignment by `task_index`, not whole-year blocks. For
five annotators, allocate indices `1,6,11...`, `2,7,12...`, through `5,10,15...`.
This keeps annotator effects from being confounded with year effects. The tracked
CSV intentionally contains no person names.

## Pilot sequence

Phase 0.6C remains not started. The first historical 2410 attempt remains
`PILOT_DIAGNOSTIC_ONLY` and is not reused as the new blind answer. Formal 2410
annotation must use the catalog Case `ipo_2024_02410`, a new conversation, Prompt
Contract v1.1.1, and preferably an annotator who has not seen the pilot result.
