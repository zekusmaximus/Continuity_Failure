"""Model provider abstraction.

A provider is a thin transport: given a rendered prompt, return raw text (or a
failure). Providers do **no** validation, no fallback, and no logging — those
belong to the runner (added in a later commit). This keeps the seam between
"talking to a model" and "deciding whether to trust it" clean and testable.

The default provider is :class:`NullProvider`, which never calls out and never
succeeds, so the surrounding system stays inert and deterministic until a real
provider is explicitly configured.
"""

from __future__ import annotations

import time
from typing import Optional, Protocol, runtime_checkable

from pydantic import BaseModel


class ModelRequest(BaseModel):
    """Everything a provider needs to make one call."""

    prompt_name: str
    prompt_version: str
    system: str = ""
    rendered_prompt: str
    schema_name: str
    max_output_tokens: int = 1024


class ModelResult(BaseModel):
    """Raw outcome of one provider call. No parsing or validation applied."""

    ok: bool
    model_name: str = ""
    raw_output: str = ""
    error: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: Optional[int] = None


@runtime_checkable
class ModelProvider(Protocol):
    """Structural contract for a model transport."""

    name: str

    def complete(self, request: ModelRequest) -> ModelResult: ...


class NullProvider:
    """The default, inert provider.

    Makes no network call and always reports failure, which forces the runner to
    use deterministic fallback output. This is what lets the whole AI layer stay
    dormant (and the test suite stay hermetic and offline) until a real provider
    is configured.
    """

    name = "null"

    def complete(self, request: ModelRequest) -> ModelResult:
        return ModelResult(
            ok=False,
            model_name=self.name,
            error="AI disabled: NullProvider makes no model calls.",
        )


class AnthropicProvider:
    """Live provider backed by the Anthropic SDK (the optional ``ai`` extra).

    Constructed only when AI is live and the ``anthropic`` package is installed;
    otherwise :func:`get_provider` degrades to :class:`NullProvider`. Returns raw
    text — validation, retry, and fallback are the runner's job. A model refusal
    or any transport error is reported as ``ok=False`` so the runner falls back
    deterministically rather than surfacing an exception.
    """

    name = "anthropic"

    def __init__(self, api_key: str, model_name: str):
        import anthropic  # lazy: only imported when a live provider is built

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model_name

    def complete(self, request: ModelRequest) -> ModelResult:
        start = time.perf_counter()
        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=request.max_output_tokens,
                system=request.system,
                messages=[{"role": "user", "content": request.rendered_prompt}],
            )
        except Exception as exc:  # transport/auth/rate-limit — degrade, don't raise
            return ModelResult(
                ok=False,
                model_name=self._model,
                error=str(exc),
                latency_ms=int((time.perf_counter() - start) * 1000),
            )

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        usage = getattr(message, "usage", None)

        if getattr(message, "stop_reason", None) == "refusal":
            return ModelResult(
                ok=False,
                model_name=self._model,
                error="model declined the request (refusal)",
                latency_ms=elapsed_ms,
                input_tokens=getattr(usage, "input_tokens", None),
                output_tokens=getattr(usage, "output_tokens", None),
            )

        text = "".join(
            block.text
            for block in message.content
            if getattr(block, "type", None) == "text"
        )
        return ModelResult(
            ok=True,
            model_name=self._model,
            raw_output=text,
            latency_ms=elapsed_ms,
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
        )


def get_provider(settings=None) -> ModelProvider:
    """Return the active provider for the current configuration.

    When AI is not live (the default), this is always :class:`NullProvider`. When
    it *is* live, an :class:`AnthropicProvider` is built — but if the ``anthropic``
    package isn't installed (the ``ai`` extra was not installed), construction
    fails and we degrade to :class:`NullProvider` rather than crashing. Enabling
    AI without the provider present therefore yields deterministic fallback
    output, never an error.
    """
    from app.config import get_settings

    settings = settings or get_settings()
    if not settings.ai_live:
        return NullProvider()

    try:
        return AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model_name=settings.model_name,
        )
    except Exception:
        return NullProvider()
