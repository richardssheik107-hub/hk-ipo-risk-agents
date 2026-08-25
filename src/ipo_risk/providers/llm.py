"""Provider-neutral OpenAI-compatible LLM integration."""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from hashlib import sha256
import json
from time import perf_counter
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from ipo_risk.providers.prompt_registry import (
    PromptResolutionError,
    resolve_domain_instruction,
)
from ipo_risk.schemas import Evidence, LLMCallMetadata


StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class LLMFailureKind(StrEnum):
    """Safe failure categories that callers can map to diagnostics."""

    UNAVAILABLE = "unavailable"
    AUTHENTICATION = "authentication"
    REQUEST = "request"
    TRANSPORT = "transport"
    RESPONSE_VALIDATION = "response_validation"


class LLMProviderError(RuntimeError):
    """Structured provider failure whose message contains no remote payload."""

    def __init__(
        self,
        kind: LLMFailureKind,
        message: str,
        *,
        recoverable: bool,
        attempts: int = 0,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.recoverable = recoverable
        self.attempts = attempts


class UnavailableLLMProvider:
    """Deterministic zero-network provider used for honest degradation."""

    name = "unavailable"

    def __init__(self, reason: str = "LLM provider is unavailable") -> None:
        self.reason = reason
        self.last_call_metadata: LLMCallMetadata | None = None

    def _raise(self) -> None:
        raise LLMProviderError(
            LLMFailureKind.UNAVAILABLE,
            self.reason,
            recoverable=False,
            attempts=0,
        )

    def complete(self, prompt: str) -> str:
        self._raise()

    def generate_structured(
        self,
        *,
        task_name: str,
        prompt_version: str,
        evidence: list[Evidence],
        response_model: type[StructuredModel],
    ) -> StructuredModel:
        self._raise()


class OpenAICompatibleLLMProvider:
    """Validate OpenAI-compatible responses against caller-owned models."""

    name = "openai_compatible"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: int = 60,
        max_retries: int = 2,
        temperature: float | None = None,
        client: Any | None = None,
    ) -> None:
        if not api_key or not base_url or not model:
            raise LLMProviderError(
                LLMFailureKind.UNAVAILABLE,
                "OpenAI-compatible LLM configuration is incomplete",
                recoverable=False,
            )
        self.model = model
        self.timeout_seconds = int(timeout_seconds)
        self.max_retries = max(0, int(max_retries))
        self.temperature = temperature
        self.last_call_metadata: LLMCallMetadata | None = None
        if client is not None:
            self._client = client
        else:
            try:
                self._client = self._build_client(
                    api_key=api_key,
                    base_url=base_url,
                    timeout_seconds=self.timeout_seconds,
                )
            except LLMProviderError:
                raise
            except Exception:
                raise LLMProviderError(
                    LLMFailureKind.REQUEST,
                    "LLM client initialization failed",
                    recoverable=False,
                ) from None

    @staticmethod
    def _build_client(*, api_key: str, base_url: str, timeout_seconds: int) -> Any:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMProviderError(
                LLMFailureKind.UNAVAILABLE,
                "The OpenAI-compatible client dependency is unavailable",
                recoverable=False,
            ) from exc
        return OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
            max_retries=0,
        )

    def complete(self, prompt: str) -> str:
        """Run the legacy free-text compatibility method."""

        return self._call(
            messages=[{"role": "user", "content": prompt}],
            prompt_version="legacy_complete",
            parse=lambda raw: raw,
            response_format=None,
        )

    def generate_structured(
        self,
        *,
        task_name: str,
        prompt_version: str,
        evidence: list[Evidence],
        response_model: type[StructuredModel],
    ) -> StructuredModel:
        """Request JSON and return only an exactly validated Pydantic model."""

        try:
            domain_instruction = resolve_domain_instruction(task_name, prompt_version)
        except PromptResolutionError:
            raise LLMProviderError(
                LLMFailureKind.REQUEST,
                "LLM prompt identity is not registered",
                recoverable=False,
                attempts=0,
            ) from None

        request = {
            "task_name": task_name,
            "prompt_version": prompt_version,
            "response_schema": response_model.model_json_schema(),
            "evidence": [self._serialize_evidence(item) for item in evidence],
        }
        system_instruction = "Return exactly one JSON object matching response_schema."
        if domain_instruction is not None:
            system_instruction = (
                f"{system_instruction}\n\nDomain extraction instruction:\n"
                f"{domain_instruction}"
            )
        messages = [
            {
                "role": "system",
                "content": system_instruction,
            },
            {
                "role": "user",
                "content": json.dumps(request, ensure_ascii=False, separators=(",", ":")),
            },
        ]

        def validate(raw: str) -> StructuredModel:
            payload = json.loads(raw)
            return response_model.model_validate(payload)

        return self._call(
            messages=messages,
            prompt_version=prompt_version,
            parse=validate,
            response_format={"type": "json_object"},
        )

    @staticmethod
    def _serialize_evidence(evidence: Evidence) -> dict[str, Any]:
        return {
            "evidence_id": evidence.evidence_id,
            "document_id": evidence.document_id,
            "chunk_id": evidence.chunk_id,
            "page": evidence.page,
            "section": evidence.section,
            "text": evidence.text,
            "source_type": evidence.source_type.value,
            "relevance_score": evidence.relevance_score,
        }

    def _call(
        self,
        *,
        messages: list[dict[str, str]],
        prompt_version: str,
        parse: Callable[[str], StructuredModel | str],
        response_format: dict[str, str] | None,
    ) -> StructuredModel | str:
        total_attempts = 1 + self.max_retries
        for attempt in range(1, total_attempts + 1):
            started = perf_counter()
            try:
                kwargs: dict[str, Any] = {"model": self.model, "messages": messages}
                if self.temperature is not None:
                    kwargs["temperature"] = self.temperature
                if response_format is not None:
                    kwargs["response_format"] = response_format
                response = self._client.chat.completions.create(**kwargs)
                raw = self._response_text(response)
                result = parse(raw)
                self.last_call_metadata = self._metadata(
                    response=response,
                    raw=raw,
                    prompt_version=prompt_version,
                    started=started,
                )
                return result
            except (json.JSONDecodeError, ValidationError, ValueError, TypeError, IndexError, AttributeError):
                if attempt < total_attempts:
                    continue
                raise LLMProviderError(
                    LLMFailureKind.RESPONSE_VALIDATION,
                    "LLM response failed structured validation",
                    recoverable=False,
                    attempts=attempt,
                ) from None
            except LLMProviderError:
                raise
            except Exception as exc:
                kind, recoverable = self._classify_remote_error(exc)
                if recoverable and attempt < total_attempts:
                    continue
                raise LLMProviderError(
                    kind,
                    self._safe_failure_message(kind),
                    recoverable=recoverable,
                    attempts=attempt,
                ) from None
        raise AssertionError("unreachable retry state")

    @staticmethod
    def _response_text(response: Any) -> str:
        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise ValueError("empty model response")
        return content

    def _metadata(
        self,
        *,
        response: Any,
        raw: str,
        prompt_version: str,
        started: float,
    ) -> LLMCallMetadata:
        request_id = str(
            getattr(response, "_request_id", None)
            or getattr(response, "request_id", None)
            or getattr(response, "id", "")
        )
        usage = getattr(response, "usage", None)
        token_usage = {
            key: int(value)
            for key in ("prompt_tokens", "completion_tokens", "total_tokens")
            if (value := getattr(usage, key, None)) is not None
        }
        return LLMCallMetadata(
            provider_name=self.name,
            model_name=self.model,
            prompt_version=prompt_version,
            latency_ms=max(0, int((perf_counter() - started) * 1000)),
            token_usage=token_usage,
            request_id=request_id,
            raw_response_hash=sha256(raw.encode("utf-8")).hexdigest(),
        )

    @staticmethod
    def _classify_remote_error(exc: Exception) -> tuple[LLMFailureKind, bool]:
        status = getattr(exc, "status_code", None)
        name = type(exc).__name__.lower()
        if status in {401, 403} or "authentication" in name or "permission" in name:
            return LLMFailureKind.AUTHENTICATION, False
        if status in {408, 409, 429} or status is not None and status >= 500:
            return LLMFailureKind.TRANSPORT, True
        if any(term in name for term in ("timeout", "connection", "ratelimit")):
            return LLMFailureKind.TRANSPORT, True
        if status is not None and 400 <= status < 500:
            return LLMFailureKind.REQUEST, False
        if any(term in name for term in ("badrequest", "unprocessable", "notfound")):
            return LLMFailureKind.REQUEST, False
        return LLMFailureKind.REQUEST, False

    @staticmethod
    def _safe_failure_message(kind: LLMFailureKind) -> str:
        return {
            LLMFailureKind.AUTHENTICATION: "LLM authentication failed",
            LLMFailureKind.REQUEST: "LLM request was rejected",
            LLMFailureKind.TRANSPORT: "LLM transport request failed",
            LLMFailureKind.UNAVAILABLE: "LLM provider is unavailable",
            LLMFailureKind.RESPONSE_VALIDATION: "LLM response validation failed",
        }[kind]


class OpenAIResponsesLLMProvider:
    """Responses API adapter preserving the existing structured Provider protocol."""

    name = "openai_responses"
    tool_name = "submit_structured_result"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: int = 60,
        max_retries: int = 2,
        client: Any | None = None,
    ) -> None:
        if not api_key or not base_url or not model:
            raise LLMProviderError(
                LLMFailureKind.UNAVAILABLE,
                "Responses API configuration is incomplete",
                recoverable=False,
            )
        self.model = model
        self.max_retries = max(0, int(max_retries))
        self.last_call_metadata: LLMCallMetadata | None = None
        self._client = client or self._build_client(api_key, base_url, timeout_seconds)

    @staticmethod
    def _build_client(api_key: str, base_url: str, timeout_seconds: int) -> Any:
        try:
            from openai import OpenAI
            return OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout_seconds,
                max_retries=0,
            )
        except Exception:
            raise LLMProviderError(
                LLMFailureKind.UNAVAILABLE,
                "Responses API client initialization failed",
                recoverable=False,
            ) from None

    def complete(self, prompt: str) -> str:
        response = self._request(
            input=prompt,
            instructions="Respond directly.",
            prompt_version="legacy_complete",
        )
        text = getattr(response, "output_text", None)
        if not isinstance(text, str) or not text.strip():
            raise LLMProviderError(
                LLMFailureKind.RESPONSE_VALIDATION,
                "Responses API text output is missing",
                recoverable=False,
                attempts=1,
            )
        return text

    def generate_structured(
        self,
        *,
        task_name: str,
        prompt_version: str,
        evidence: list[Evidence],
        response_model: type[StructuredModel],
    ) -> StructuredModel:
        try:
            domain_instruction = resolve_domain_instruction(task_name, prompt_version)
        except PromptResolutionError:
            raise LLMProviderError(
                LLMFailureKind.REQUEST,
                "LLM prompt identity is not registered",
                recoverable=False,
            ) from None
        request = {
            "task_name": task_name,
            "prompt_version": prompt_version,
            "evidence": [
                OpenAICompatibleLLMProvider._serialize_evidence(item)
                for item in evidence
            ],
        }
        base_instructions = (
            "Judge only supplied Evidence and submit exactly one structured result "
            "through the required function. Do not add facts to satisfy the schema."
        )
        if domain_instruction:
            base_instructions += "\n\n" + domain_instruction

        tools = [
            {
                "type": "function",
                "name": self.tool_name,
                "description": "Submit the complete structured judgment.",
                "parameters": response_model.model_json_schema(),
                "strict": True,
            }
        ]
        validation_feedback = ""
        total_validation_attempts = 1 + min(self.max_retries, 2)
        for structured_attempt in range(1, total_validation_attempts + 1):
            instructions = base_instructions
            if validation_feedback:
                instructions += "\n\n" + validation_feedback
            response = self._request(
                input=json.dumps(request, ensure_ascii=False, separators=(",", ":")),
                instructions=instructions,
                tools=tools,
                tool_choice={"type": "function", "name": self.tool_name},
                parallel_tool_calls=False,
                prompt_version=prompt_version,
            )
            arguments = self._function_arguments(response)
            if not isinstance(arguments, str):
                validation_feedback = (
                    "The previous response did not provide string JSON arguments through "
                    "the required function. Call the required function exactly once with "
                    "arguments matching its schema."
                )
                if structured_attempt < total_validation_attempts:
                    continue
                raise LLMProviderError(
                    LLMFailureKind.RESPONSE_VALIDATION,
                    "Responses API structured output is missing",
                    recoverable=False,
                    attempts=structured_attempt,
                )
            try:
                payload = json.loads(arguments)
                return response_model.model_validate(payload)
            except json.JSONDecodeError:
                validation_feedback = (
                    "The previous function arguments were not valid JSON. Submit valid JSON "
                    "through the required function without changing the Evidence-grounded facts."
                )
            except ValidationError as exc:
                validation_feedback = self._validation_feedback(exc)
            if structured_attempt >= total_validation_attempts:
                raise LLMProviderError(
                    LLMFailureKind.RESPONSE_VALIDATION,
                    "Responses API structured output failed validation",
                    recoverable=False,
                    attempts=structured_attempt,
                ) from None
        raise AssertionError("unreachable structured validation state")

    @classmethod
    def _function_arguments(cls, response: Any) -> str | None:
        for item in getattr(response, "output", None) or []:
            kind = item.get("type") if isinstance(item, dict) else getattr(item, "type", None)
            name = item.get("name") if isinstance(item, dict) else getattr(item, "name", None)
            if kind == "function_call" and name == cls.tool_name:
                arguments = (
                    item.get("arguments")
                    if isinstance(item, dict)
                    else getattr(item, "arguments", None)
                )
                return arguments if isinstance(arguments, str) else None
        return None

    @staticmethod
    def _validation_feedback(exc: ValidationError) -> str:
        safe_errors = []
        for error in exc.errors(include_input=False)[:8]:
            path = ".".join(str(part) for part in error.get("loc", ())) or "<root>"
            safe_errors.append(
                {
                    "path": path,
                    "type": str(error.get("type", "validation_error")),
                    "message": str(error.get("msg", "invalid value")),
                }
            )
        return (
            "The previous structured result failed local schema validation. Submit a "
            "corrected function call using only the same supplied Evidence; do not invent "
            "facts just to satisfy the schema. Validation errors: "
            + json.dumps(safe_errors, ensure_ascii=False, separators=(",", ":"))
        )

    @staticmethod
    def _response_raw(response: Any) -> str:
        if hasattr(response, "model_dump_json"):
            return str(response.model_dump_json())
        if hasattr(response, "model_dump"):
            return json.dumps(
                response.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        return str(response)

    def _responses_metadata(
        self,
        *,
        response: Any,
        prompt_version: str,
        started: float,
    ) -> LLMCallMetadata:
        request_id = str(
            getattr(response, "_request_id", None)
            or getattr(response, "request_id", None)
            or getattr(response, "id", "")
        )
        usage = getattr(response, "usage", None)

        def _usage_value(name: str) -> Any:
            if isinstance(usage, dict):
                return usage.get(name)
            return getattr(usage, name, None)

        token_usage: dict[str, int] = {}
        for response_key, canonical_key in (
            ("input_tokens", "prompt_tokens"),
            ("output_tokens", "completion_tokens"),
            ("total_tokens", "total_tokens"),
        ):
            value = _usage_value(response_key)
            if value is not None:
                token_usage[canonical_key] = int(value)
        raw = self._response_raw(response)
        return LLMCallMetadata(
            provider_name=self.name,
            model_name=self.model,
            prompt_version=prompt_version,
            latency_ms=max(0, int((perf_counter() - started) * 1000)),
            token_usage=token_usage,
            request_id=request_id,
            raw_response_hash=sha256(raw.encode("utf-8")).hexdigest(),
        )

    def _request(self, *, prompt_version: str, **kwargs: Any) -> Any:
        for attempt in range(1, self.max_retries + 2):
            started = perf_counter()
            try:
                response = self._client.responses.create(model=self.model, **kwargs)
                self.last_call_metadata = self._responses_metadata(
                    response=response,
                    prompt_version=prompt_version,
                    started=started,
                )
                return response
            except Exception as exc:
                kind, recoverable = OpenAICompatibleLLMProvider._classify_remote_error(exc)
                if recoverable and attempt <= self.max_retries:
                    continue
                raise LLMProviderError(
                    kind,
                    OpenAICompatibleLLMProvider._safe_failure_message(kind),
                    recoverable=recoverable,
                    attempts=attempt,
                ) from None
        raise AssertionError("unreachable")
