"""Runner tests (Week 3, commit 2).

Exercise the validation boundary end-to-end with fake providers: success,
retry-then-success, invalid-output fallback, transport-error fallback, and the
AI-off short-circuit. No network, no real model, fully deterministic.
"""

from __future__ import annotations

import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND = os.path.join(_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from pydantic import BaseModel  # noqa: E402

from app.config import Settings  # noqa: E402
from app.ai.logging import ModelRunStore, ValidationStatus  # noqa: E402
from app.ai.provider import ModelRequest, ModelResult  # noqa: E402
from app.ai.runner import ArtifactStatus, run_artifact, render_prompt  # noqa: E402


# --- Reference schema + fallback used only by these tests ------------------

class ReferenceArtifact(BaseModel):
    headline: str
    points: list[str]


def _fallback(payload: dict) -> ReferenceArtifact:
    return ReferenceArtifact(headline="(system fallback)", points=[])


_VALID_JSON = json.dumps({"headline": "Contamination confirmed", "points": ["a", "b"]})


# --- Settings helpers ------------------------------------------------------

def _live() -> Settings:
    return Settings(
        ai_enabled=True,
        model_name="test-model",
        anthropic_api_key="sk-test",
        max_output_tokens=256,
    )


def _off() -> Settings:
    return Settings(
        ai_enabled=False,
        model_name="test-model",
        anthropic_api_key=None,
        max_output_tokens=256,
    )


# --- Fake providers --------------------------------------------------------

class _ScriptedProvider:
    """Returns a scripted sequence of ModelResults, one per call."""

    name = "scripted"

    def __init__(self, results):
        self._results = list(results)
        self.calls = 0

    def complete(self, request: ModelRequest) -> ModelResult:
        self.calls += 1
        return self._results.pop(0)


def _ok(raw: str) -> ModelResult:
    return ModelResult(ok=True, model_name="test-model", raw_output=raw, output_tokens=12)


def _err() -> ModelResult:
    return ModelResult(ok=False, model_name="test-model", error="network down")


class _ExplodingProvider:
    name = "boom"

    def complete(self, request: ModelRequest) -> ModelResult:  # pragma: no cover
        raise AssertionError("provider must not be called when AI is off")


def _run(**kwargs):
    """run_artifact with the reference schema/fallback and an isolated store."""
    store = ModelRunStore()
    art = run_artifact(
        prompt_name="reference",
        prompt_version="v1",
        input_payload={"turn": 1},
        schema=ReferenceArtifact,
        fallback=_fallback,
        input_summary="turn 1",
        store=store,
        **kwargs,
    )
    return art, store


# ---------------------------------------------------------------------------
# AI off
# ---------------------------------------------------------------------------

def test_ai_off_uses_fallback_and_never_calls_provider():
    art, store = _run(settings=_off(), provider=_ExplodingProvider())
    assert art.status == ArtifactStatus.FALLBACK
    assert art.from_model is False
    assert art.content.headline == "(system fallback)"
    assert art.run.validation_status == ValidationStatus.FALLBACK
    assert art.run.model_name == "disabled"
    assert art.run.retry_count == 0
    assert len(store.all()) == 1


# ---------------------------------------------------------------------------
# Live success
# ---------------------------------------------------------------------------

def test_success_path_returns_model_output():
    provider = _ScriptedProvider([_ok(_VALID_JSON)])
    art, store = _run(settings=_live(), provider=provider)
    assert art.status == ArtifactStatus.OK
    assert art.from_model is True
    assert art.content.headline == "Contamination confirmed"
    assert art.content.points == ["a", "b"]
    assert art.run.validation_status == ValidationStatus.OK
    assert art.run.retry_count == 0
    assert art.run.parsed_output == {"headline": "Contamination confirmed", "points": ["a", "b"]}
    assert provider.calls == 1
    assert len(store.all()) == 1


def test_retry_then_success():
    provider = _ScriptedProvider([_ok("not json at all"), _ok(_VALID_JSON)])
    art, _ = _run(settings=_live(), provider=provider)
    assert art.status == ArtifactStatus.OK
    assert art.run.validation_status == ValidationStatus.OK
    assert art.run.retry_count == 1
    assert provider.calls == 2


# ---------------------------------------------------------------------------
# Live failure -> fallback
# ---------------------------------------------------------------------------

def test_invalid_output_twice_falls_back():
    provider = _ScriptedProvider([_ok("garbage"), _ok('{"wrong": true}')])
    art, _ = _run(settings=_live(), provider=provider)
    assert art.status == ArtifactStatus.FALLBACK
    assert art.content.headline == "(system fallback)"
    assert art.run.validation_status == ValidationStatus.INVALID
    assert art.run.retry_count == 1
    assert provider.calls == 2


def test_transport_error_falls_back():
    provider = _ScriptedProvider([_err(), _err()])
    art, _ = _run(settings=_live(), provider=provider)
    assert art.status == ArtifactStatus.FALLBACK
    assert art.run.validation_status == ValidationStatus.ERROR
    assert art.run.retry_count == 1
    assert provider.calls == 2


def test_every_call_logs_exactly_one_run():
    store = ModelRunStore()
    for _ in range(3):
        run_artifact(
            prompt_name="reference",
            prompt_version="v1",
            input_payload={},
            schema=ReferenceArtifact,
            fallback=_fallback,
            settings=_off(),
            store=store,
        )
    assert len(store.all()) == 3


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------

def test_render_prompt_generic_when_file_absent(tmp_path):
    system, user = render_prompt("nonexistent", "v9", {"x": 1}, prompts_dir=tmp_path)
    assert "nonexistent" in system
    assert json.loads(user) == {"x": 1}


def test_render_prompt_uses_file_when_present(tmp_path):
    (tmp_path / "memo_drafter.v1.md").write_text("SYSTEM PROMPT BODY", encoding="utf-8")
    system, user = render_prompt("memo_drafter", "v1", {"turn": 2}, prompts_dir=tmp_path)
    assert system == "SYSTEM PROMPT BODY"
    assert json.loads(user) == {"turn": 2}
