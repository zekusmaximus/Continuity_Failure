"""Boundary tests for the dormant AI layer (Week 3, commit 1).

These lock in the two guarantees that make it safe to grow an AI layer on top of
a deterministic engine:

1. AI is **off by default** and degrades to a no-op provider.
2. The AI package is structurally incapable of mutating game state and stays
   independent of the web framework.
"""

from __future__ import annotations

import ast
import os
import sys

# Make the backend `app` package importable without requiring the editable
# install, mirroring conftest.py's handling of engine/memory at the root.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND = os.path.join(_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app.config import get_settings  # noqa: E402
from app.ai.provider import NullProvider, ModelProvider, ModelRequest, get_provider  # noqa: E402
from app.ai.logging import ModelRun, ModelRunStore, ValidationStatus  # noqa: E402


def _clear_ai_env(monkeypatch):
    for var in ("CF_AI_ENABLED", "CF_AI_MODEL", "CF_AI_MAX_TOKENS", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)


# ---------------------------------------------------------------------------
# AI is disabled by default
# ---------------------------------------------------------------------------

def test_ai_disabled_by_default(monkeypatch):
    _clear_ai_env(monkeypatch)
    settings = get_settings()
    assert settings.ai_enabled is False
    assert settings.ai_live is False


def test_ai_live_requires_both_enabled_and_key(monkeypatch):
    _clear_ai_env(monkeypatch)

    # Enabled but no key -> still not live.
    monkeypatch.setenv("CF_AI_ENABLED", "true")
    assert get_settings().ai_live is False

    # Key but not enabled -> still not live.
    monkeypatch.delenv("CF_AI_ENABLED", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert get_settings().ai_live is False

    # Both -> live.
    monkeypatch.setenv("CF_AI_ENABLED", "on")
    assert get_settings().ai_live is True


def test_get_provider_is_null_when_disabled(monkeypatch):
    _clear_ai_env(monkeypatch)
    provider = get_provider()
    assert isinstance(provider, NullProvider)
    assert isinstance(provider, ModelProvider)  # satisfies the structural protocol


def test_null_provider_never_succeeds():
    req = ModelRequest(
        prompt_name="memo_drafter",
        prompt_version="v1",
        rendered_prompt="draft a memo",
        schema_name="MemoDraft",
    )
    result = NullProvider().complete(req)
    assert result.ok is False
    assert result.raw_output == ""
    assert result.error


def test_live_config_still_degrades_safely(monkeypatch):
    # In this commit no real provider is wired, so even a "live" config must
    # degrade to the null provider rather than raise.
    _clear_ai_env(monkeypatch)
    monkeypatch.setenv("CF_AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert get_settings().ai_live is True
    assert isinstance(get_provider(), NullProvider)


# ---------------------------------------------------------------------------
# ModelRun logging shape and store
# ---------------------------------------------------------------------------

def test_model_run_captures_the_logging_contract():
    run = ModelRun(
        prompt_name="memo_drafter",
        prompt_version="v1",
        model_name="null",
        validation_status=ValidationStatus.FALLBACK,
        input_summary="turn 3 / disclosure",
        raw_output="",
        parsed_output={"recommendation": "…"},
        retry_count=1,
        latency_ms=0,
        token_usage={"input": 0, "output": 0},
        estimated_cost=0.0,
        campaign_id="abc",
        turn_number=3,
    )
    dumped = run.model_dump()
    for field in (
        "prompt_name", "prompt_version", "model_name", "input_summary",
        "raw_output", "parsed_output", "validation_status", "retry_count",
        "latency_ms", "token_usage", "estimated_cost",
    ):
        assert field in dumped


def test_model_run_store_is_append_only_and_filterable():
    store = ModelRunStore()

    def _run(cid: str) -> ModelRun:
        return ModelRun(
            prompt_name="memo_drafter",
            prompt_version="v1",
            model_name="null",
            validation_status=ValidationStatus.FALLBACK,
            campaign_id=cid,
        )

    store.add(_run("a"))
    store.add(_run("a"))
    store.add(_run("b"))
    assert len(store.all()) == 3
    assert len(store.for_campaign("a")) == 2
    assert len(store.for_campaign("b")) == 1
    store.clear()
    assert store.all() == []


# ---------------------------------------------------------------------------
# Structural boundary: the AI layer cannot mutate state or import the web stack
# ---------------------------------------------------------------------------

def _ai_imports():
    """Yield ``(filename, imported_module, imported_name)`` for every import in
    the AI package. Uses AST so prose and comments never count — only real
    import statements.
    """
    ai_dir = os.path.join(_BACKEND, "app", "ai")
    assert os.path.isdir(ai_dir), "app/ai package should exist"
    for name in os.listdir(ai_dir):
        if not name.endswith(".py"):
            continue
        with open(os.path.join(ai_dir, name), "r", encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=name)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    yield name, alias.name, None
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    yield name, module, alias.name


def test_ai_layer_cannot_mutate_game_state():
    # The AI package must never *import* the deterministic state-mutation code.
    forbidden_modules = {"engine.diffs", "engine.turn"}
    forbidden_names = {"apply_diffs", "advance_turn"}
    for fname, module, name in _ai_imports():
        assert module not in forbidden_modules, (
            f"app/ai/{fname} must not import {module}"
        )
        # e.g. `from engine import turn` / `from engine import diffs`
        if module == "engine":
            assert name not in {"turn", "diffs"}, (
                f"app/ai/{fname} must not import engine.{name}"
            )
        assert name not in forbidden_names, (
            f"app/ai/{fname} must not import {name}"
        )


def test_ai_layer_does_not_depend_on_fastapi():
    # AI is a transport/validation concern, not a web concern; keep it decoupled
    # from FastAPI so it can be exercised (and tested) without the web stack.
    for fname, module, _name in _ai_imports():
        assert not module.startswith("fastapi"), (
            f"app/ai/{fname} must not import fastapi"
        )
