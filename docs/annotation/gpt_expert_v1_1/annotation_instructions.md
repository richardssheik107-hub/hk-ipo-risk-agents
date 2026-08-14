# Annotation Instructions

1. Confirm the conversation contains no prior Golden or model output.
2. Read the full prospectus and assess all eight active risks independently.
3. Prefer authoritative formal sources; record all required evidence pages.
4. Distinguish evidence role and requirement; do not create duplicate risks for
   multiple pages.
5. Financial facts must preserve period, currency, unit and sign.
6. Follow resolved policies in Protocol v1.1 and report every open-policy ambiguity.
7. Use `needs_review` where evidence or policy is insufficient. If the risk is
   applicable but its severity/policy is unresolved, set `expected_level` to JSON
   `null`; do not guess a level. A verified applicable risk must use a concrete
   `low`/`medium`/`high`/`critical` level. A non-applicable risk must use
   `rejected + not_applicable`.
8. `null` and `not_applicable` are different: `null` is allowed only for an
   applicable `needs_review` risk; `not_applicable` is allowed only for a
   non-applicable rejected risk.
9. Return one JSON object only, without Markdown fences or commentary.
10. Do not include secrets, local paths, Human Golden, Retriever or Agent output.
