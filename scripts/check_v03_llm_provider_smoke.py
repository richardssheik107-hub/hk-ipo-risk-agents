"""Optional live smoke using synthetic evidence and safe metadata output only."""

from dataclasses import replace

from pydantic import BaseModel

from ipo_risk.core.config import load_settings
from ipo_risk.core.container import DependencyContainer, default_registry
from ipo_risk.providers.llm import LLMProviderError, UnavailableLLMProvider
from ipo_risk.schemas import Evidence


class SmokeResult(BaseModel):
    finding: str
    confidence: float


def main() -> int:
    settings = replace(load_settings(), llm_provider="openai_compatible")
    provider = DependencyContainer(settings, default_registry()).create_llm_provider()
    if isinstance(provider, UnavailableLLMProvider):
        print("status=skipped reason=credentials_unavailable")
        return 0

    try:
        provider.generate_structured(
            task_name="synthetic_smoke",
            prompt_version="synthetic_v1",
            evidence=[
                Evidence(
                    evidence_id="synthetic-1",
                    page=1,
                    section="synthetic",
                    text="Synthetic issuer status: pre-commercial.",
                )
            ],
            response_model=SmokeResult,
        )
    except LLMProviderError as exc:
        print(f"status=failed kind={exc.kind} attempts={exc.attempts}")
        return 1

    metadata = provider.last_call_metadata
    print("status=success structured_validation=true")
    print(f"provider={metadata.provider_name} model={metadata.model_name}")
    print(
        f"request_id={metadata.request_id} latency_ms={metadata.latency_ms} "
        f"token_usage={metadata.token_usage} response_hash={metadata.raw_response_hash}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
