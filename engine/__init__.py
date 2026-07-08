"""Continuity Failure deterministic simulation engine.

The engine is intentionally independent of any web framework. It owns the
authoritative game-state transitions for the Northbridge Water Failure MVP.

Design rules (see project AGENTS.md):
  * The database is canon. The model is not.
  * The player advises. NPCs decide.
  * Every state change must be explainable (an ``AppliedDiff``).
  * All state mutations pass through deterministic functions in this package.
"""

from engine import models
from engine import state
from engine import diffs
from engine import rules
from engine import seed_data
from engine import turn

__all__ = [
    "models",
    "state",
    "diffs",
    "rules",
    "seed_data",
    "turn",
]
