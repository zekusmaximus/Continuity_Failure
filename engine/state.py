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


STATE_VARIABLE_LABELS = {
    "water_security": "Water Security",
    "power_stability": "Power Stability",
    "public_trust": "Public Trust",
    "public_order": "Public Order",
    "budget_capacity": "Budget Capacity",
    "staff_capacity": "Staff Capacity",
    "legal_exposure": "Legal Exposure",
    "media_pressure": "Media Pressure",
    "hospital_stability": "Hospital Stability",
    "school_disruption": "School Disruption",
    "state_oversight_risk": "State Oversight Risk",
    "contractor_dependency": "Contractor Dependency",
    "information_integrity": "Information Integrity",
    "player_reputation": "Consultant Reputation",
    "player_perceived_neutrality": "Perceived Neutrality",
    "player_shadow_authority": "Shadow Authority",
}


def humanize_variable(variable: str) -> str:
    """Return a player-facing state-variable label."""
    return STATE_VARIABLE_LABELS.get(
        variable,
        variable.replace("_", " ").title(),
    )


# Variables where a HIGHER value is WORSE for the town/consultant. Everything
# else on the 0-100 scale is higher-is-better. This is the authoritative
# direction vocabulary the API exposes so the UI never has to guess semantics.
HIGHER_IS_WORSE = frozenset(
    {
        "legal_exposure",
        "media_pressure",
        "state_oversight_risk",
        "contractor_dependency",
        "school_disruption",
        "player_shadow_authority",
    }
)

DIRECTION_HIGHER_IS_BETTER = "higher_is_better"
DIRECTION_HIGHER_IS_WORSE = "higher_is_worse"


def variable_direction(variable: str) -> str:
    """Return the direction semantics for a state variable."""
    if variable in HIGHER_IS_WORSE:
        return DIRECTION_HIGHER_IS_WORSE
    return DIRECTION_HIGHER_IS_BETTER


def clamp(value: float) -> int:
    """Clamp a numeric value to the inclusive ``[0, 100]`` integer range."""
    if value <= MIN_VALUE:
        return MIN_VALUE
    if value >= MAX_VALUE:
        return MAX_VALUE
    return int(round(value))


def in_bounds(value: int) -> bool:
    return MIN_VALUE <= value <= MAX_VALUE
