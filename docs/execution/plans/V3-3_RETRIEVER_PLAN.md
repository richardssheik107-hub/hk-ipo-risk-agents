---
plan_id: V3-3
title: Generalize v0.3 Retriever Query Families
status: APPROVED
revision: 1
base_commit: 6847f67df0e275576e6689c62a50b0269d4cfd84
branch: feat/v03-retriever-query-families
owner: tech-lead
planner: web-chatgpt
executor: codex
report_path: docs/execution/reports/V3-3_RETRIEVER_EXECUTION_REPORT.md
---

# V3-3 Retriever Query Families

## Goal

Extend the deterministic KeywordDocumentRetriever from the existing v0.2 financial retrieval capability into v0.3 multi-domain query families.

Required retrieval families:

- revenue
- continuous_loss
- customer_concentration
- supplier_concentration
- redemption_rights
- material_litigation_compliance
- commercialization_status
- core_product_pipeline

The existing DocumentRetriever public interface must remain unchanged.

## Background

The current retriever already supports deterministic matching, multilingual aliases, ranking, section weighting, stable Evidence IDs and traceable Evidence output.

This task generalizes the mechanism without introducing LLM calls, embeddings, vector databases or external search.

## Project Rules

Follow:

- AGENTS.md
- docs/PROJECT_SPEC.md
- docs/ARCHITECTURE.md
- docs/DATA_SCHEMA.md
- docs/V03_DEVELOPMENT_CONTRACT.md
- docs/PROJECT_MASTER_CHECKLIST.md
- docs/execution/README.md

## Allowed Files

- src/ipo_risk/retrieval/keyword.py
- src/ipo_risk/retrieval/query_families.py
- tests/contract/test_keyword_retriever.py
- tests/contract/test_v03_retriever_query_families.py
- tests/fixtures/v03_retriever/
- docs/execution/reports/V3-3_RETRIEVER_EXECUTION_REPORT.md

## Forbidden Files

- src/ipo_risk/retrieval/base.py
- src/ipo_risk/schemas/
- src/ipo_risk/core/container.py
- src/ipo_risk/agents/
- src/ipo_risk/providers/
- src/ipo_risk/workflows/
- src/ipo_risk/services/
- configs/
- data/
- tests/fixtures/v03_golden_cases/
- .github/workflows/

## Tasks

- [ ] Preserve existing cash, ending cash balance and operating cash flow retrieval behavior.
- [ ] Add maintainable deterministic definitions for the eight v0.3 query families.
- [ ] Add Simplified Chinese, Traditional Chinese and English aliases.
- [ ] Improve domain-aware ranking using deterministic context and section weighting.
- [ ] Preserve stable Evidence IDs and Evidence traceability.
- [ ] Preserve empty-result behavior for unmatched queries.
- [ ] Add contract tests for new query families and decoy contexts.
- [ ] Run validation and create Execution Report.

## Acceptance Criteria

- Retriever public interface unchanged.
- No Schema, Agent, Provider, Workflow, Service or Container interface changes.
- Existing v0.2 retriever behavior remains compatible.
- All eight query families support deterministic multilingual matching.
- Relevant sections rank above unrelated boilerplate.
- No company name, stock code or prospectus page hard-coding.
- No LLM, embedding model, vector database or new dependency.
- No use of 2025 blind-test cases for tuning.

## Required Validation

Run:

- pytest -q tests/contract/test_keyword_retriever.py
- pytest -q tests/contract/test_v03_retriever_query_families.py
- pytest -q
- python scripts/validate_project.py
- python scripts/validate_competition_data.py
- python -m compileall -q app src scripts
- git diff --check

## Stop Conditions

Stop and return PLAN_CHANGE_REQUIRED if implementation requires:

- public interface changes
- schema changes
- workflow/service/container changes
- new dependencies
- LLM/vector search integration
- changes outside Allowed Files

## Expected Deliverables

- Deterministic v0.3 query-family retriever implementation.
- Contract tests.
- docs/execution/reports/V3-3_RETRIEVER_EXECUTION_REPORT.md

This Plan authorizes execution only. It does not authorize commit, push, merge, tag or release.