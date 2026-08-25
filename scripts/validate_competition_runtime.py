"""Fail-fast competition runtime contract validation.

This gate is intentionally network-free. It validates the cross-lane contracts and
configuration wiring that A owns; it does not claim that external credentials,
real PDFs, frozen PR-F handoff, B/C/D/E business outputs, or competition metrics
are already available.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from ipo_risk.core.config import load_settings
from ipo_risk.core.container import DependencyContainer, default_registry
from ipo_risk.schemas.competition_runtime import (
    CompetitionConflict,
    CompetitionRuntimeIdentity,
    RecheckRequest,
    TraceEvent,
    TraceEventType,
)


AI_CONFIGS = (
    Path("configs/v04_ai.yaml"),
    Path("configs/v04_ai_table.yaml"),
)


def _pass(label: str) -> None:
    print(f"PASS  {label}")


def validate_contracts() -> None:
    identity = CompetitionRuntimeIdentity(case_id="gate-case", run_id="gate-run")
    conflict = CompetitionConflict(
        case_id=identity.case_id,
        run_id=identity.run_id,
        involved_agents=["financial", "business"],
        summary="gate conflict",
    )
    RecheckRequest(
        conflict_id=conflict.conflict_id,
        case_id=identity.case_id,
        run_id=identity.run_id,
        requested_by="final_supervisor",
        targets=["cash_runway"],
        reason="gate re-check",
    )
    TraceEvent(
        case_id=identity.case_id,
        run_id=identity.run_id,
        event_type=TraceEventType.SUPERVISOR,
        status="success",
    )
    try:
        RecheckRequest(
            conflict_id=conflict.conflict_id,
            case_id=identity.case_id,
            run_id=identity.run_id,
            requested_by="final_supervisor",
            targets=["cash_runway"],
            reason="invalid second-loop allowance",
            max_attempts=2,
        )
    except ValidationError:
        pass
    else:
        raise RuntimeError("competition re-check contract no longer fails closed")
    _pass("competition runtime sidecar contracts")


def validate_ai_configs() -> None:
    for path in AI_CONFIGS:
        if not path.exists():
            raise FileNotFoundError(f"required AI runtime config is missing: {path}")
        settings = load_settings(str(path))
        if settings.llm_provider not in {"openai_compatible", "openai_responses"}:
            raise RuntimeError(
                f"{path} must select a registered remote LLM provider, got "
                f"{settings.llm_provider!r}"
            )
        provider = DependencyContainer(settings, default_registry()).create_llm_provider()
        provider_name = getattr(provider, "name", type(provider).__name__)
        if provider_name not in {
            "unavailable",
            "openai_compatible",
            "openai_responses",
        }:
            raise RuntimeError(f"unexpected LLM provider resolution: {provider_name}")
        _pass(f"{path} provider wiring -> {provider_name}")


def main() -> int:
    validate_contracts()
    validate_ai_configs()
    print(
        "INFO  external secrets, real-case PDFs, PR-F handoff, competition metrics, "
        "and B/C/D/E lane outputs are intentionally outside this network-free A gate"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
