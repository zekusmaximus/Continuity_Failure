"""Backend configuration.

Settings are read from the environment with safe, offline-first defaults. The AI
layer is **disabled by default**: with no configuration, the game runs exactly as
it does today and never attempts a model call. AI only becomes "live" when it is
both explicitly enabled *and* a provider key is present.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Default model. Overridable via CF_AI_MODEL (e.g. "claude-haiku-4-5" for a
# cheaper drafting tier, or a stronger model for harder roles).
DEFAULT_MODEL = "claude-opus-4-8"
DEFAULT_MAX_OUTPUT_TOKENS = 1024
MIN_OUTPUT_TOKENS = 64
MAX_OUTPUT_TOKENS = 8192
DEFAULT_DATABASE_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "continuity_failure.sqlite3"
)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(
    name: str,
    default: int,
    minimum: int = MIN_OUTPUT_TOKENS,
    maximum: int = MAX_OUTPUT_TOKENS,
) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of backend configuration."""

    ai_enabled: bool
    model_name: str
    anthropic_api_key: Optional[str]
    max_output_tokens: int
    database_path: str = str(DEFAULT_DATABASE_PATH)

    def __post_init__(self) -> None:
        if not MIN_OUTPUT_TOKENS <= self.max_output_tokens <= MAX_OUTPUT_TOKENS:
            raise ValueError(
                f"max_output_tokens must be within "
                f"{MIN_OUTPUT_TOKENS}..{MAX_OUTPUT_TOKENS}"
            )

    @property
    def ai_live(self) -> bool:
        """AI actually contacts a provider only when enabled AND a key exists.

        Everything downstream checks this flag; when it is ``False`` the runner
        degrades to deterministic fallback output without any network call.
        """
        return self.ai_enabled and bool(self.anthropic_api_key)


def get_settings() -> Settings:
    """Build a :class:`Settings` snapshot from the current environment."""
    return Settings(
        ai_enabled=_env_bool("CF_AI_ENABLED", default=False),
        model_name=os.environ.get("CF_AI_MODEL", DEFAULT_MODEL) or DEFAULT_MODEL,
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
        max_output_tokens=_env_int("CF_AI_MAX_TOKENS", DEFAULT_MAX_OUTPUT_TOKENS),
        database_path=(
            os.environ.get("CF_DATABASE_PATH") or str(DEFAULT_DATABASE_PATH)
        ),
    )
