"""Shared deterministic condition evaluation.

``ThreadCondition`` is the one legible threshold shape the engine uses for
"is the world in this state?" checks: thread resolution (``engine/threads.py``),
dynamic-thread opening triggers (``engine/consequences.py``), and client-call
variant selection (``engine/calls.py``) all evaluate through this module, so
the semantics can never drift apart. No randomness, no model calls -- a
condition either holds or it does not.

A condition is world-scoped by default (``variable`` names a WorldState
variable). When ``faction_id`` is set it is faction-scoped instead:
``variable`` names one of the numeric faction fields below, evaluated against
that faction. A faction-scoped condition against an unknown faction never
holds -- a missing subject is not silently treated as neutral.
"""

from __future__ import annotations

from typing import Dict, Iterable, Optional

from engine.models import Faction, ThreadCondition

# The faction fields a faction-scoped condition may reference. All 0-100
# integers, and all already moved on the record by engine/factions.py.
FACTION_CONDITION_FIELDS = frozenset(
    {"trust_in_player", "influence", "current_pressure", "risk_tolerance"}
)


def condition_holds(
    condition: ThreadCondition,
    variables: Dict[str, int],
    factions_by_id: Optional[Dict[str, Faction]] = None,
) -> bool:
    """Whether one threshold condition holds.

    World-scoped: missing variables read as 50 (the neutral midpoint),
    matching the long-standing thread-resolution behavior. Faction-scoped:
    an unknown faction or field means the condition does not hold.
    """
    if condition.faction_id:
        faction = (factions_by_id or {}).get(condition.faction_id)
        if faction is None or condition.variable not in FACTION_CONDITION_FIELDS:
            return False
        value = getattr(faction, condition.variable)
    else:
        value = variables.get(condition.variable, 50)
    if condition.op == "<=":
        return value <= condition.threshold
    if condition.op == ">=":
        return value >= condition.threshold
    return False


def all_hold(
    conditions: Iterable[ThreadCondition],
    variables: Dict[str, int],
    factions_by_id: Optional[Dict[str, Faction]] = None,
) -> bool:
    """True when every condition holds (vacuously true for an empty list)."""
    return all(condition_holds(c, variables, factions_by_id) for c in conditions)


def any_holds(
    conditions: Iterable[ThreadCondition],
    variables: Dict[str, int],
    factions_by_id: Optional[Dict[str, Faction]] = None,
) -> bool:
    """True when at least one condition holds. False for an empty list."""
    return any(condition_holds(c, variables, factions_by_id) for c in conditions)
