# Expert Result Storage Policy

## Separation model

The collaboration branch contains protocols, blank Case packets, assignments, and
progress only. Annotation answers belong on the dedicated
`annotation/gpt-expert-results` branch and use one directory per Case:

```text
expert_results/<case_id>/
├─ pass1/expert_annotation_v1.json
├─ pass1/validation_result.json
├─ pass2/expert_annotation_v2.json
├─ pass2/validation_result.json
├─ audit/audit.json
└─ final/expert_annotation_final.json
```

The initial results branch contains only an empty scaffold. PDFs, credentials,
local paths, Human Golden, and 2025 blind material are forbidden.

## Immutability and provenance

- Never overwrite a pass, audit, or final artifact.
- Preserve GPT output verbatim; validation writes a separate result file.
- A validation failure changes progress to `validation_failed` or `needs_review`;
  it does not justify editing the original JSON.
- A revised output is a new pass, not a replacement for pass1.
- Audit and final stages must retain references to their source passes when their
  schemas are introduced.

The importer refuses an existing stage filename. If another revision is required
after pass2, stop and establish a reviewed naming/schema extension rather than
inventing filenames ad hoc.

## Branch and access boundary

`docs/gpt-expert-golden-v1-1-sync` is the collaboration branch.
`annotation/gpt-expert-results` is the answer branch. Do not merge the result branch
into the collaboration branch while blind annotation is active.

Git branches are organization boundaries, not authorization boundaries. Anyone
with repository read permission can inspect both branches. Strict blindness
therefore requires either a team access rule (annotators do not inspect the result
branch before completing their own pass) or a private store with separate access
control.

## Progress status vocabulary

Only these values are used in `team_case_assignment.csv`:

```text
not_started
in_progress
completed
validation_failed
needs_review
audit_completed
adjudication_required
finalized
```

Blank means unassigned/not yet reported. Notes may describe workflow blockers but
must not disclose judgments, evidence pages, calculations, or answers.
