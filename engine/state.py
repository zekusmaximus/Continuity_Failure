"""State value bounds and clamping.

All world-state variables are stored on a 0-100 integer scale. ``budget``
floor and oversight/exposure ceilings are how the deterministic engine reasons
about scarcity and risk.

Directionality (for humans reading diffs):
  * ``*_security`` / ``*_stability`` / ``*_capacity`` / ``public_trust`` /
    ``information_integrity`` / ``player_reputation`` /
    ``player_perceived_neutrality`` / ``power_stability``: HIGHER IS BETTER.
  * ``legal_exposure`` / ``media_pressure`` / ``state_oversight_risk`` /
    ``contractor_dependency`` / ``school_disruption`` /
    ``player_shadow_authority``: HIGHER IS WORSE.
"""

from __future__ import annotations

MIN_VALUE = 0
MAX_VALUE = 100


def clamp(value: float) -> int:
    """Clamp a numeric value to the inclusive ``[0, 100]`` integer range."""
    if value <= MIN_VALUE:
        return MIN_VALUE
    if value >= MAX_VALUE:
        return MAX_VALUE
    return int(round(value))


def in_bounds(value: int) -> bool:
    return MIN_VALUE <= value <= MAX_VALUE
