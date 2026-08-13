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
8. after validation passes, run `scripts/import_expert_annotation.py` to store the
   result under ignored `reports/gpt_expert_annotation_pilot/expert_results/`.

Do not commit annotation answers or PDFs.

## Independent second pass

The audit uses a new ChatGPT conversation with the PDF and Protocol. Its task is to
find errors, not rubber-stamp the first pass. Future audit output states are:

- `PASS`
- `REVISION_REQUIRED`
- `POLICY_AMBIGUITY`
- `HUMAN_ADJUDICATION_REQUIRED`

The detailed audit schema is not implemented in Phase 0.6B.

## Assignment discipline

Claim work only in `team_case_assignment.csv`. Initial annotator/status fields are
blank. Never put credentials, local PDF paths or annotation answers in assignment
notes.

## Pilot sequence

Phase 0.6C begins with 2410.HK (Financial), 2517.HK (Legal), and 1167.HK
(Business). The first historical 2410 attempt remains diagnostic only and is not
reused as the new blind answer.
