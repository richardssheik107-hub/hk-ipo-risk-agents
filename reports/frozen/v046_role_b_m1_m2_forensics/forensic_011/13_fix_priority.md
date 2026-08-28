# Role-B Forensic Fix Priority

Only the first proven root cause is recommended for the next Fixer.

| Priority | Root cause | M1 units | M2 units | Recommended module |
|---:|---|---:|---:|---|
| 1 | `retrieval_candidate_miss` | 6 | 16 | src/ipo_risk/retrieval/role_b_financial_v046.py |
| 2 | `parser_text_missing` | 5 | 10 | defer |
| 3 | `risk_absent_caused_evidence_miss` | 0 | 7 | defer |
| 4 | `deterministic_extraction_miss` | 4 | 0 | defer |
| 5 | `retrieval_ranking_or_topk_miss` | 1 | 1 | defer |
| 6 | `wrong_period_selection` | 2 | 0 | defer |
| 7 | `builder_not_applicable_misclassification` | 1 | 0 | defer |
| 8 | `final_evidence_not_retained` | 1 | 0 | defer |
| 9 | `final_evidence_page_mismatch` | 0 | 1 | defer |
| 10 | `level_mismatch` | 1 | 0 | defer |
| 11 | `llm_abstention_with_sufficient_evidence` | 1 | 0 | defer |
| 12 | `retrieved_page_anchor_truncated` | 0 | 1 | defer |
| 13 | `risk_rejected_caused_evidence_miss` | 0 | 1 | defer |
