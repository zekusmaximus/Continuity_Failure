"""The validation boundary.

Every AI-assisted artifact in the game goes through :func:`run_artifact`, and
this is the *only* place that decides whether model output can be trusted. The
flow is fixed:

    render prompt -> call provider -> validate against a schema
                  -> on failure, retry once
                  -> on second failure (or AI disabled), use deterministic fallback
                  -> log a ModelRun either way

The function never raises into the caller and never touches game state: the
worst case is a validated *fallback* artifact plus a logged failure. Callers get
a uniform, already-validated schema instance and a ``status`` telling them
whether it came from the model or the deterministic fallback (for honest UI
labeling).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Type

from pydantic import BaseModel, ValidationError

from app.ai.logging import ModelRun, ValidationStatus, get_run_store
from app.ai.provider import ModelProvider, ModelRequest, get_provider

# Repo-root prompts directory: backend/app/ai/runner.py -> parents[3] == root.
PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"

MAX_ATTEMPTS = 2  # initial attempt + one retry


class ArtifactStatus:
    OK = "ok"              # validated model output
    FALLBACK = "fallback"  # deterministic fallback used


@dataclass
class AiArtifact:
    """Uniform envelope returned by :func:`run_artifact`.

    ``content`` is always a validated instance of the requested schema, whether
    it came from the model or the fallback; ``status`` records the provenance.
    """

    status: str
    content: BaseModel
    run: ModelRun

    @property
    def from_model(self) -> bool:
        return self.status == ArtifactStatus.OK


def render_prompt(
    prompt_name: str,
    prompt_version: str,
    input_payload: dict,
    prompts_dir: Optional[Path] = None,
) -> tuple[str, str]:
    """Build ``(system, user)`` messages for a prompt.

    The system message is the versioned prompt file
    (``prompts/{name}.{version}.md``) when present; otherwise a generic
    instruction is used so the runner works before any prompt files exist. The
    user message is the structured input payload as JSON.
    """
    prompts_dir = prompts_dir or PROMPTS_DIR
    prompt_file = prompts_dir / f"{prompt_name}.{prompt_version}.md"
    if prompt_file.exists():
        system = prompt_file.read_text(encoding="utf-8")
    else:
        system = (
            f"You are the '{prompt_name}' assistant for a civic-crisis advisory "
            "tool. Respond only with a single JSON object matching the required "
            "schema. Do not invent facts beyond the supplied input."
        )
    # Prompt inputs are part of the logged structured contract. Refuse unknown
    # Python objects instead of silently stringifying them into lossy payloads.
    user = json.dumps(input_payload, ensure_ascii=False, indent=2)
    return system, user


def run_artifact(
    *,
    prompt_name: str,
    prompt_version: str,
    input_payload: dict,
    schema: Type[BaseModel],
    fallback: Callable[[dict], BaseModel],
    input_summary: str = "",
    campaign_id: Optional[str] = None,
    turn_number: Optional[int] = None,
    provider: Optional[ModelProvider] = None,
    settings=None,
    prompts_dir: Optional[Path] = None,
    store=None,
) -> AiArtifact:
    """Produce a validated artifact, falling back deterministically on any failure."""
    from app.config import get_settings

    settings = settings or get_settings()
    store = store if store is not None else get_run_store()

    def _log_and_return(status: str, content: BaseModel, run: ModelRun) -> AiArtifact:
        store.add(run)
        return AiArtifact(status=status, content=content, run=run)

    # --- AI off: straight to deterministic fallback, no provider call. ---
    if not settings.ai_live:
        content = fallback(input_payload)
        run = ModelRun(
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            model_name="disabled",
            validation_status=ValidationStatus.FALLBACK,
            input_summary=input_summary,
            parsed_output=content.model_dump(),
            retry_count=0,
            latency_ms=0,
            campaign_id=campaign_id,
            turn_number=turn_number,
        )
        return _log_and_return(ArtifactStatus.FALLBACK, content, run)

    # --- AI live: call -> validate -> retry once -> fallback. ---
    provider = provider or get_provider(settings)
    system, user = render_prompt(prompt_name, prompt_version, input_payload, prompts_dir)
    request = ModelRequest(
        prompt_name=prompt_name,
        prompt_version=prompt_version,
        system=system,
        rendered_prompt=user,
        schema_name=schema.__name__,
        max_output_tokens=settings.max_output_tokens,
    )

    attempts = 0
    raw = ""
    model_name = settings.model_name
    total_latency = 0
    tokens = {"input": 0, "output": 0}
    saw_transport_error = False

    while attempts < MAX_ATTEMPTS:
        attempts += 1
        start = time.perf_counter()
        result = provider.complete(request)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        total_latency += result.latency_ms if result.latency_ms is not None else elapsed_ms
        if result.model_name:
            model_name = result.model_name
        if result.input_tokens:
            tokens["input"] += result.input_tokens
        if result.output_tokens:
            tokens["output"] += result.output_tokens

        if not result.ok:
            saw_transport_error = True
            continue

        raw = result.raw_output
        try:
            parsed = schema.model_validate_json(raw)
        except ValidationError:
            continue

        run = ModelRun(
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            model_name=model_name,
            validation_status=ValidationStatus.OK,
            input_summary=input_summary,
            raw_output=raw,
            parsed_output=parsed.model_dump(),
            retry_count=attempts - 1,
            latency_ms=total_latency,
            token_usage=tokens,
            campaign_id=campaign_id,
            turn_number=turn_number,
        )
        return _log_and_return(ArtifactStatus.OK, parsed, run)

    # Exhausted attempts -> deterministic fallback. Terminal status reflects the
    # cause: ERROR if the provider never returned usable text, else INVALID.
    terminal = ValidationStatus.ERROR if (saw_transport_error and raw == "") else ValidationStatus.INVALID
    content = fallback(input_payload)
    run = ModelRun(
        prompt_name=prompt_name,
        prompt_version=prompt_version,
        model_name=model_name,
        validation_status=terminal,
        input_summary=input_summary,
        raw_output=raw,
        parsed_output=content.model_dump(),
        retry_count=attempts - 1,
        latency_ms=total_latency,
        token_usage=tokens,
        campaign_id=campaign_id,
        turn_number=turn_number,
    )
    return _log_and_return(ArtifactStatus.FALLBACK, content, run)
