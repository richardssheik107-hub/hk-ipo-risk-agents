---
plan_id: V3-4
title: Add Replaceable Structured LLM Provider
status: APPROVED
revision: 1
base_commit: 4ed73b1561b1b5a517f4856b9b7cef187afd1b84
branch: feat/v03-llm-provider
owner: tech-lead
planner: web-chatgpt
executor: codex
report_path: docs/execution/reports/V3-4_LLM_PROVIDER_EXECUTION_REPORT.md
---

# V3-4 Replaceable Structured LLM Provider

## Goal

在不改变已冻结 `LLMProvider` 公共协议的前提下，实现 v0.3 可替换
LLM Provider 基础设施，包括：

- MockLLMProvider
- OpenAICompatibleLLMProvider
- UnavailableLLMProvider

真实 Provider 仅处理 Retriever 已筛选后的少量 Evidence，并将模型返回结果
通过调用方提供的 Pydantic `response_model` 验证后返回。

本 Plan 不实现 Financial、Legal 或 Business Agent，也不将 LLM 接入工作流。

## Background

当前仓库已经冻结：

- `LLMProvider.complete(prompt) -> str`
- `LLMProvider.generate_structured(...) -> BaseModel`
- `LLMCallMetadata`
- MockLLMProvider
- LLM 环境变量命名
- v0.3 LLM 使用与降级规则

当前缺口：

1. 尚无真实 LLMProvider；
2. 尚无 LLM 专用 Unavailable Provider；
3. ComponentRegistry 只注册 MockLLMProvider；
4. Settings 尚未真正承载：
   - API Key
   - Base URL
   - Model
   - Timeout
   - Max retries
5. `.env.example` 虽已声明这些环境变量，但运行时 Settings 尚未消费其中大部分；
6. 当前 Agent 尚未使用真实 LLM，本棒只建立后续 V3-6/V3-7 可安全依赖的 Provider 层。

真实实现采用 provider-neutral 的 OpenAI-compatible client。

Base URL、API Key、模型名称必须来自运行时配置或环境变量，不得硬编码任何
火山方舟地址、模型 ID 或用户密钥。

## Project Rules

- AGENTS.md
- docs/PROJECT_SPEC.md
- docs/ARCHITECTURE.md
- docs/DATA_SCHEMA.md
- docs/V03_DEVELOPMENT_CONTRACT.md
- docs/V03_LLM_PROVIDER_SPEC.md
- docs/PROJECT_MASTER_CHECKLIST.md
- docs/execution/README.md

## Inputs

- src/ipo_risk/providers/base.py
- src/ipo_risk/providers/mock.py
- src/ipo_risk/providers/unavailable.py
- src/ipo_risk/core/config.py
- src/ipo_risk/core/container.py
- src/ipo_risk/schemas/__init__.py
- tests/contract/test_v03_agent_contract.py
- .env.example
- configs/default.yaml
- configs/mock.yaml
- pyproject.toml

Frozen public contract:

```python
class LLMProvider(Protocol):
    name: str
    last_call_metadata: LLMCallMetadata | None

    def complete(self, prompt: str) -> str: ...

    def generate_structured(
        self,
        *,
        task_name: str,
        prompt_version: str,
        evidence: list[Evidence],
        response_model: type[StructuredModel],
    ) -> StructuredModel: ...
```

Do not change this protocol.

## Allowed Files

- src/ipo_risk/providers/llm.py
- src/ipo_risk/providers/mock.py
- src/ipo_risk/core/config.py
- src/ipo_risk/core/container.py
- pyproject.toml
- tests/contract/test_v03_llm_provider.py
- scripts/check_v03_llm_provider_smoke.py
- docs/execution/reports/V3-4_LLM_PROVIDER_EXECUTION_REPORT.md

## Forbidden Files

- docs/execution/plans/V3-4_LLM_PROVIDER_PLAN.md
- src/ipo_risk/providers/base.py
- src/ipo_risk/schemas/
- src/ipo_risk/agents/
- src/ipo_risk/retrieval/
- src/ipo_risk/skills/
- src/ipo_risk/domain/
- src/ipo_risk/workflows/
- src/ipo_risk/services/
- src/ipo_risk/reporting/
- prompts/
- configs/
- data/
- tests/fixtures/v03_golden_cases/
- .env.example
- .github/workflows/

## Tasks

- [ ] Preserve the frozen LLMProvider public protocol without changing
      `providers/base.py`.

- [ ] Add the minimal generic OpenAI-compatible Python SDK runtime dependency
      required for the real Provider. Do not add a provider-specific Volcano,
      Doubao or vendor SDK.

- [ ] Extend Settings with:
      `llm_api_key`,
      `llm_base_url`,
      `llm_model`,
      `llm_timeout_seconds`,
      `llm_max_retries`.

- [ ] Preserve configuration precedence:
      environment variables > YAML > code defaults.

- [ ] Ensure numeric LLM environment values are converted to their intended
      integer types rather than remaining strings.

- [ ] Prevent the configured API key from being exposed through Settings repr,
      exceptions, logs or metadata.

- [ ] Implement `OpenAICompatibleLLMProvider` in
      `src/ipo_risk/providers/llm.py`.

- [ ] The real Provider must obtain API key, base URL, model name, timeout and
      retry configuration exclusively from injected runtime configuration.

- [ ] Do not hard-code any current Volcano Engine Base URL, endpoint ID,
      model ID, account information or credential.

- [ ] Implement the compatibility `complete(prompt)` method and record safe
      `LLMCallMetadata`.

- [ ] Implement `generate_structured(...)` using only the supplied
      `list[Evidence]`.

- [ ] The structured request must include:
      task name,
      prompt version,
      the response model JSON schema,
      and only the supplied Evidence required for extraction.

- [ ] Do not send DocumentChunk collections, complete prospectuses, repository
      files, local paths or unrelated project state to the Provider.

- [ ] Parse the model response as JSON and validate it with the exact
      caller-supplied Pydantic `response_model`.

- [ ] Never return an arbitrary dictionary or partially validated payload from
      `generate_structured()`.

- [ ] Add a safe provider-specific structured exception model/classification
      inside `providers/llm.py` for unavailable, authentication, request,
      transport and response-validation failures.

- [ ] Retry only recoverable failures such as rate limits, timeout, connection
      failures and server-side 5xx failures.

- [ ] Authentication errors and invalid requests must fail immediately.

- [ ] Structured JSON/Pydantic validation failure may be retried within the
      configured total attempt budget but must eventually produce a structured
      Provider failure rather than malformed output.

- [ ] Total attempts must never exceed:

      `1 + llm_max_retries`

      for one Provider call.

- [ ] Avoid SDK-level hidden retries that would exceed the configured total
      attempt budget.

- [ ] Implement `UnavailableLLMProvider`.

- [ ] `UnavailableLLMProvider` must make zero network calls and fail
      deterministically with a safe structured Provider error when invoked.

- [ ] Register:
      `mock`,
      `openai_compatible`,
      and `unavailable`
      LLM providers in ComponentRegistry.

- [ ] If `openai_compatible` is selected but required runtime configuration is
      incomplete, DependencyContainer must honestly degrade to
      `UnavailableLLMProvider` rather than fabricate a response or expose a key.

- [ ] Preserve the existing default/mock configuration and deterministic
      workflow behavior when no real API key is configured.

- [ ] Ensure successful Provider calls populate LLMCallMetadata including:
      provider name,
      model name,
      prompt version,
      latency,
      token usage when available,
      request ID,
      and SHA-256 raw-response hash.

- [ ] Raw external responses must not be persisted or printed by default.

- [ ] Update MockLLMProvider only as required to maintain the same metadata
      contract, including the legacy `complete()` compatibility path.

- [ ] Add network-free contract tests using fakes/mocks for the real Provider.

- [ ] Add an optional local live-smoke script that sends only synthetic Evidence,
      prints no secrets or raw response, and can be skipped when credentials are
      unavailable.

- [ ] Run all required validation and generate the Execution Report.

## Acceptance Criteria

- Existing `LLMProvider` protocol signature is unchanged.

- `providers/base.py` and public schemas are unchanged.

- `MockLLMProvider` remains compatible with existing tests.

- `OpenAICompatibleLLMProvider` implements both frozen Provider methods.

- `UnavailableLLMProvider` implements the same callable contract and performs
  no network access.

- Real Provider output is always validated by the caller-provided Pydantic
  response model before being returned.

- Invalid JSON, wrong field types and schema-invalid responses never cross the
  Provider boundary.

- Only Retriever-selected Evidence is serialized into structured requests.

- No complete prospectus or DocumentChunk collection is accepted or sent.

- API key, Base URL and model are runtime-configured.

- No API key, token, password or account credential is committed.

- API key is not exposed by Settings repr, exception text, test output or
  metadata.

- `IPO_RISK_LLM_TIMEOUT_SECONDS` and
  `IPO_RISK_LLM_MAX_RETRIES` resolve to integer runtime values.

- Recoverable failures respect the configured retry budget.

- Authentication and invalid-request failures are not blindly retried.

- Provider failures are distinguishable and safe for later Agent conversion
  into `ComponentDiagnostic` / `AnalysisError`.

- Missing real-provider configuration produces honest unavailable behavior.

- Default Mock and deterministic v0.2/v0.3 paths remain runnable with no API key.

- Tests never access a real external API.

- No Financial, Legal, Business, Verifier, Supervisor, Workflow or Service
  implementation is added in this Plan.

- No prompt-specific business extraction logic is added.

- Complete repository regression tests pass.

## Required Validation

```text
pytest -q tests/contract/test_v03_agent_contract.py
pytest -q tests/contract/test_v03_llm_provider.py
pytest -q
python scripts/validate_project.py
python scripts/validate_competition_data.py
python scripts/validate_v03_golden_manifest.py tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv --integrity
python -m compileall -q app src scripts
python scripts/check_execution_scope.py docs/execution/plans/V3-4_LLM_PROVIDER_PLAN.md
git diff --check
```

## Manual Validation

Run the existing real-document regression if the local fixture is available:

```text
python scripts/check_real_v02_e2e.py
```

Expected stable regression:

- parsed chunks/pages: 706
- parser errors: 0
- Evidence pages: 563 / 562
- cash runway: 2.76 months
- verification: verified
- prediction: 90 / critical

If the real PDF fixture is unavailable, record this check as `NOT_TESTED`.
Do not fabricate a passing result.

Without real LLM credentials:

- confirm `mock` Provider still works;
- confirm `unavailable` Provider performs zero network calls;
- confirm selecting the real Provider with missing configuration degrades
  honestly and does not break deterministic project validation.

If valid local runtime credentials are available, optionally run:

```text
python scripts/check_v03_llm_provider_smoke.py
```

The live smoke must use only synthetic Evidence.

The smoke output may contain:

- provider name
- model name
- structured validation success
- request ID
- token counts
- latency
- response hash

It must not print:

- API key
- Authorization headers
- complete request payload
- Evidence raw text
- complete raw model response

A live external smoke is useful but is not a CI requirement.

## Stop Conditions

Stop with `PLAN_CHANGE_REQUIRED` if:

- the frozen LLMProvider protocol must change;

- a public Schema must change;

- Agent candidate models must change;

- Agent, Workflow or Service integration is required;

- a real Provider cannot be implemented without hard-coding an endpoint,
  model ID or credential;

- implementation requires sending an entire prospectus rather than selected
  Evidence;

- implementation requires a vendor-specific SDK instead of the approved generic
  OpenAI-compatible integration;

- more runtime dependencies than the minimal generic LLM SDK are required;

- passing tests requires weakening, deleting, skipping or xfail-ing existing
  tests;

- a test requires real external network access;

- API keys or other secrets appear in repository files, diffs, logs, reports
  or test fixtures;

- implementation requires touching files outside Allowed Files;

- the worktree contains unrelated uncommitted changes;

- the required work materially expands into V3-5, V3-6, V3-7, V3-8 or V3-9.

Stop with `BLOCKED` if a required local dependency or repository prerequisite is
missing and cannot be resolved inside this Plan.

## Expected Deliverables

- `OpenAICompatibleLLMProvider`

- `UnavailableLLMProvider`

- existing `MockLLMProvider` preserved and contract-compatible

- configuration-driven LLM runtime settings

- ComponentRegistry support for:
  - mock
  - openai_compatible
  - unavailable

- bounded retry and structured failure behavior

- Pydantic-validated structured output

- safe LLMCallMetadata

- network-free Provider contract tests

- optional local LLM smoke script

- `docs/execution/reports/V3-4_LLM_PROVIDER_EXECUTION_REPORT.md`

This Plan does not authorize:

- Financial Agent implementation
- Legal Agent implementation
- Business Agent implementation
- Verifier implementation
- Workflow integration
- Service integration
- commit
- push
- Pull Request creation
- merge
- tag
- release
