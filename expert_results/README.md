# GPT Expert Result Workspace

This branch stores versioned expert annotation artifacts separately from blind
Case packets and progress tracking. It intentionally starts with no answers.

Each Case has `pass1`, `pass2`, `audit`, and `final` directories. Preserve raw
GPT output, write validation results separately, and never overwrite an existing
artifact. Follow `docs/annotation/gpt_expert_v1_1/RESULT_STORAGE_POLICY.md`.

Do not add PDFs, credentials, local paths, Human Golden, or 2025 blind material.
Do not merge this branch into the collaboration branch while blind work is active.
Remember that a Git branch is not an access-control boundary.
