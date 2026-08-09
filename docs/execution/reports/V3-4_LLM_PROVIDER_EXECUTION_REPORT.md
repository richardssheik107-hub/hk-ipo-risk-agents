---
plan_id: V3-4
plan_revision: 1
execution_status: COMPLETED
base_commit: 4ed73b1561b1b5a517f4856b9b7cef187afd1b84
start_head: aad7d65530630abe0adeb145a4db89d508183a12
end_head: 33ee35de89c1667c8a303c2f714dea735bc8c22e
branch: feat/v03-llm-provider
executor: codex
---

# Summary

Implemented a provider-neutral, OpenAI-compatible structured LLM layer without
changing the frozen `LLMProvider` protocol or public schemas. The implementation
adds bounded retries, safe failure classification, exact Pydantic validation,
safe call metadata, deterministic unavailable behavior, configuration-driven
assembly, network-free contract tests, and an optional synthetic live-smoke
script. Existing Mock and v0.2 deterministic paths remain stable.

## Review Follow-up

The branch was integrated with `origin/main@f9c74f67756c7ae5bb60aed8b674adbe209d3764`
using merge commit `33ee35de89c1667c8a303c2f714dea735bc8c22e` without
conflicts. The follow-up classifies HTTP 408 and 409 as recoverable transport
failures under the existing bounded retry loop. It also converts unexpected
client-construction failures into non-recoverable, safe `LLMProviderError`
instances without exposing the underlying exception text or runtime settings.
Network-free regressions cover both changes.

# Plan Compliance

COMPLIANT

All changes are confined to the Approved Plan's Allowed Files. No Agent,
Workflow, Service, public schema, frozen Provider protocol, prompt, fixture, or
configuration YAML file was modified.

# Files Created

- `src/ipo_risk/providers/llm.py`
- `tests/contract/test_v03_llm_provider.py`
- `scripts/check_v03_llm_provider_smoke.py`
- `docs/execution/reports/V3-4_LLM_PROVIDER_EXECUTION_REPORT.md`

# Files Modified

- `src/ipo_risk/providers/mock.py`
- `src/ipo_risk/core/config.py`
- `src/ipo_risk/core/container.py`
- `pyproject.toml`

# Files Deleted

None.

# Tasks Completed

- [x] Preserve the frozen LLMProvider public protocol without changing
      `providers/base.py`.
- [x] Add the minimal generic OpenAI-compatible Python SDK runtime dependency
      required for the real Provider. No provider-specific SDK was added.
- [x] Extend Settings with `llm_api_key`, `llm_base_url`, `llm_model`,
      `llm_timeout_seconds`, and `llm_max_retries`.
- [x] Preserve configuration precedence: environment variables > YAML > code
      defaults.
- [x] Convert numeric LLM environment values to integer runtime values.
- [x] Hide the configured API key from Settings repr, exceptions, logs, and
      metadata.
- [x] Implement `OpenAICompatibleLLMProvider` in
      `src/ipo_risk/providers/llm.py`.
- [x] Obtain all real Provider runtime configuration exclusively through
      constructor injection.
- [x] Avoid hard-coded vendor endpoints, model IDs, account data, and
      credentials.
- [x] Implement `complete(prompt)` and safe metadata recording.
- [x] Implement `generate_structured(...)` using only supplied Evidence.
- [x] Include task name, prompt version, response schema, and selected Evidence
      in structured requests.
- [x] Exclude DocumentChunk collections, prospectuses, repository files, local
      paths, and unrelated state from Provider requests.
- [x] Parse JSON and validate it with the exact caller-supplied Pydantic model.
- [x] Prevent arbitrary dictionaries or partially validated payloads from
      crossing the Provider boundary.
- [x] Add safe unavailable, authentication, request, transport, and
      response-validation failure classifications.
- [x] Retry only rate-limit, timeout, connection, server-side, and structured
      validation failures that are recoverable.
- [x] Fail authentication and invalid requests immediately.
- [x] Bound structured validation retries and return a structured failure after
      exhaustion.
- [x] Limit total attempts to `1 + llm_max_retries`.
- [x] Disable SDK-level hidden retries by constructing the client with
      `max_retries=0`.
- [x] Implement `UnavailableLLMProvider`.
- [x] Ensure `UnavailableLLMProvider` performs zero network calls and raises a
      deterministic safe error.
- [x] Register `mock`, `openai_compatible`, and `unavailable` LLM providers.
- [x] Degrade incomplete real-provider configuration to
      `UnavailableLLMProvider` in `DependencyContainer`.
- [x] Preserve default Mock configuration and deterministic workflow behavior.
- [x] Populate provider/model/prompt version/latency/token usage/request ID/raw
      response SHA-256 metadata on successful calls.
- [x] Avoid persistence or printing of raw external responses.
- [x] Update `MockLLMProvider.complete()` to populate legacy-path metadata.
- [x] Add network-free contract tests using injected fake clients.
- [x] Add an optional synthetic-Evidence live-smoke script with safe output.
- [x] Run all required validation and generate this Execution Report.

# Validation Results

- Command: `pytest -q tests/contract/test_v03_agent_contract.py`
  - Result: PASS
  - Details: `9 passed in 0.39s` after integrating the latest main.
- Command: `pytest -q tests/contract/test_v03_llm_provider.py`
  - Result: PASS
  - Details: `22 passed in 0.34s`; all tests are network-free, including the
    HTTP 408/409 and client-initialization review regressions.
- Command: `pytest -q`
  - Result: PASS
  - Details: `625 passed in 13.45s` on the combined latest-main branch.
- Command: `python scripts/validate_project.py`
  - Result: PASS
  - Details: `status=completed verified=3 pending=1`.
- Command: `python scripts/validate_competition_data.py`
  - Result: PASS
  - Details: `competition_data_validation=passed`.
- Command: `python scripts/validate_v03_golden_manifest.py tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv --integrity`
  - Result: PASS
  - Details: Golden manifest reported valid.
- Command: `python -m compileall -q app src scripts`
  - Result: PASS
  - Details: Completed with exit code 0 and no compile errors.
- Command: `python scripts/check_execution_scope.py docs/execution/plans/V3-4_LLM_PROVIDER_PLAN.md`
  - Result: PASS
  - Details: `execution_scope=valid`.
- Command: `git diff --check`
  - Result: PASS
  - Details: Exit code 0; only informational Git line-ending warnings were
    emitted.

The final validation suite used Python 3.13.7 because the machine's default
Python 3.12 environment lacked the already-declared `openpyxl` dependency. A
complete rerun under the dependency-complete interpreter produced all PASS
results above.

# Acceptance Criteria

- PASS: Existing `LLMProvider` protocol signature is unchanged.
- PASS: `providers/base.py` and public schemas are unchanged.
- PASS: `MockLLMProvider` remains compatible with existing tests.
- PASS: `OpenAICompatibleLLMProvider` implements both frozen methods.
- PASS: `UnavailableLLMProvider` implements the callable contract with zero
  network access.
- PASS: Real Provider output is validated by the exact caller-provided Pydantic
  response model.
- PASS: Invalid JSON, wrong field types, and schema-invalid responses do not
  cross the Provider boundary.
- PASS: Only Retriever-selected Evidence is serialized into structured
  requests.
- PASS: Complete prospectuses and DocumentChunk collections are neither
  accepted nor sent.
- PASS: API key, Base URL, and model are runtime-configured.
- PASS: No API key, token, password, or account credential was added.
- PASS: API keys are absent from Settings repr, exception messages, test output,
  and metadata.
- PASS: `IPO_RISK_LLM_TIMEOUT_SECONDS` and
  `IPO_RISK_LLM_MAX_RETRIES` resolve to integers.
- PASS: Recoverable failures respect the configured retry budget.
- PASS: Authentication and invalid-request failures are not retried.
- PASS: Provider failures have safe structured classifications for later
  diagnostic conversion.
- PASS: Missing real-provider configuration returns honest unavailable
  behavior.
- PASS: Default Mock and deterministic v0.2/v0.3 paths run without an API key.
- PASS: Tests do not access an external API.
- PASS: No Financial, Legal, Business, Verifier, Supervisor, Workflow, or
  Service implementation was added.
- PASS: No prompt-specific business extraction logic was added.
- PASS: Complete repository regression tests pass.

# Manual Validation

- PASS: `python scripts/check_real_v02_e2e.py` completed against the local
  2410.HK fixture.
- PASS: Parsed chunks/pages `706`; parser errors `0`.
- PASS: Evidence pages `563 / 562`; cash runway `2.76` months.
- PASS: Verification `verified`; prediction `90.0 / critical`.
- PASS: Mock Provider works and records metadata, verified by contract tests.
- PASS: Unavailable Provider performs zero network calls, verified by contract
  tests.
- PASS: Missing real configuration degrades to unavailable, verified by
  contract tests and smoke script.
- NOT_TESTED: Live external LLM smoke. No valid credentials were used; the
  script returned `status=skipped reason=credentials_unavailable` without
  exposing sensitive or raw content.

# Deviations

None.

# Known Limitations

- V3-4 intentionally does not integrate the Provider into Agents, Workflows, or
  Services.
- A live OpenAI-compatible endpoint was not called because no runtime
  credentials were supplied.
- The generic SDK dependency is declared in `pyproject.toml`; the current local
  interpreter used for offline tests did not require importing it because tests
  inject a fake client.

# Suggested Follow-ups

- During human review, optionally run the live smoke with newly issued local
  credentials and confirm the endpoint's OpenAI chat-completions compatibility.
- Keep future Agent integration in its separately approved V3-6/V3-7 Plans.
- Do not begin V3-5 until V3-4 review and publication steps are complete.

# Plan Change Requests

None.

# Git Diff Summary

Tracked-file `git diff --stat` before creation of this report:

```text
 pyproject.toml                 |  2 +-
 src/ipo_risk/core/config.py    | 11 +++++++++--
 src/ipo_risk/core/container.py | 27 ++++++++++++++++++++++++++-
 src/ipo_risk/providers/mock.py | 14 +++++++++++++-
 4 files changed, 49 insertions(+), 5 deletions(-)
```

Untracked Allowed Files at that point:

```text
scripts/check_v03_llm_provider_smoke.py
src/ipo_risk/providers/llm.py
tests/contract/test_v03_llm_provider.py
docs/execution/reports/V3-4_LLM_PROVIDER_EXECUTION_REPORT.md
```

Review follow-up `git diff --stat` after integrating the latest main:

```text
 .../reports/V3-4_LLM_PROVIDER_EXECUTION_REPORT.md  | 39 ++++++++++++------
 src/ipo_risk/providers/llm.py                      | 24 ++++++++---
 tests/contract/test_v03_llm_provider.py            | 46 ++++++++++++++++++++++
 3 files changed, 91 insertions(+), 18 deletions(-)
```

# Final Git Status

```text
 M docs/execution/reports/V3-4_LLM_PROVIDER_EXECUTION_REPORT.md
 M src/ipo_risk/providers/llm.py
 M tests/contract/test_v03_llm_provider.py
```

# Next Action

READY_FOR_REVIEW
