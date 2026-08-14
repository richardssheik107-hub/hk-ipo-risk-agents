# Team Annotation Workflow

## Primary pass

For each assigned Case:

1. open a completely new web ChatGPT conversation;
2. upload only the original prospectus PDF, Protocol v1.1, common instructions,
   and that Case's blank JSON;
3. do not upload Human Golden, old evaluation, Retriever or Agent output;
4. use one conversation for one Case only;
5. do not copy answers across Cases;
6. save JSON only;
7. run `scripts/validate_expert_annotation.py` locally with the manifest page count;
8. run `scripts/import_expert_annotation.py --stage pass1`; the importer preserves
   the raw GPT JSON and writes a separate `validation_result.json` under the ignored
   local results workspace. Its default inventory is the portable tracked
   `source_manifest.csv`, so no local PDF path is required;
9. never edit or replace the preserved pass output when validation fails;
10. update `team_case_assignment.csv` with progress only, never answers;
11. publish answers only to `annotation/gpt-expert-results` after the applicable
    team blind-boundary rule permits it.

Do not commit annotation answers or PDFs to the collaboration/docs branch.

## Independent second pass

The audit uses a new ChatGPT conversation with the PDF and Protocol. Its task is to
find errors, not rubber-stamp the first pass. Future audit output states are:

- `PASS`
- `REVISION_REQUIRED`
- `POLICY_AMBIGUITY`
- `HUMAN_ADJUDICATION_REQUIRED`

The detailed audit schema is not implemented in Phase 0.6B. Preserve later
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

## Pilot sequence

Phase 0.6C begins with 2410.HK (Financial), 2517.HK (Legal), and 1167.HK
(Business). The first historical 2410 attempt remains diagnostic only and is not
reused as the new blind answer.
