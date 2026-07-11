"""Shared deterministic condition evaluation.

``ThreadCondition`` is the one legible threshold shape the engine uses for
"is the world in this state?" checks: thread resolution (``engine/threads.py``)
and dynamic-thread opening triggers (``engine/consequences.py``) both evaluate
through this module, so the semantics can never drift apart. No randomness,
no model calls -- a condition either holds against the variables or it does not.
"""

from __future__ import annotations

from typing import Dict, Iterable

from engine.models import ThreadCondition


def condition_holds(condition: ThreadCondition, variables: Dict[str, int]) -> bool:
    """Whether one threshold condition holds against the world state.

    Missing variables read as 50 (the neutral midpoint), matching the
    long-standing thread-resolution behavior.
    """
    value = variables.get(condition.variable, 50)
    if condition.op == "<=":
        return value <= condition.threshold
    if condition.op == ">=":
        return value >= condition.threshold
    return False


def all_hold(conditions: Iterable[ThreadCondition], variables: Dict[str, int]) -> bool:
    """True when every condition holds (vacuously true for an empty list)."""
    return all(condition_holds(c, variables) for c in conditions)


def any_holds(conditions: Iterable[ThreadCondition], variables: Dict[str, int]) -> bool:
    """True when at least one condition holds. False for an empty list."""
    return any(condition_holds(c, variables) for c in conditions)
