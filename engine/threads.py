"""Deterministic open-thread lifecycle: scheduled escalation and resolution.

Open threads were previously narrative bookkeeping -- created by the
consequence stack and displayed, but mechanically inert. This module gives them
a deterministic lifecycle:

* A thread with a ``due_turn`` escalates when the campaign resolves that turn
  and the thread is still open: its ``escalation_effects`` are applied through
  ``apply_diffs`` (source ``thread``) with a legible reason, so every escalation
  shows up in the causal waterfall like any other move.
* A thread resolves when the player's chosen advice carries one of its
  ``resolve_tags`` and the client actually acted on it (FOLLOWED or
  PARTIALLY_FOLLOWED), or when all of its ``resolve_conditions`` thresholds
  hold against the post-advice world state.
* ``repeat_every`` re-arms the deadline after an escalation, so a standing risk
  (a disclosure clock, a sole-source precedent) keeps costing the town until it
  is actually dealt with.

There is no randomness and no model call: same state, same advice, same threads
-> same escalations, bit for bit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from engine import conditions
from engine.diffs import apply_diffs
from engine.models import (
    AdviceOption,
    AppliedDiff,
    Campaign,
    DecisionType,
    NpcDecision,
    OpenThread,
    SourceType,
    ThreadStatus,
)


# Decision types that count as the client actually acting on the advice for
# thread-resolution purposes. MODIFIED/DELAYED/REJECTED leave the thread live.
_ACTED_ON = (DecisionType.FOLLOWED, DecisionType.PARTIALLY_FOLLOWED)


@dataclass
class ThreadEvent:
    """One legible lifecycle event for the aftermath UI."""
    thread_id: str
    title: str
    kind: str       # "escalated" / "resolved"
    note: str


def _conditions_hold(thread: OpenThread, variables, factions_by_id) -> bool:
    if not thread.resolve_conditions:
        return False
    return conditions.all_hold(thread.resolve_conditions, variables, factions_by_id)


def _resolved_by_advice(
    thread: OpenThread, advice: AdviceOption, decision: NpcDecision
) -> bool:
    if not thread.resolve_tags:
        return False
    if decision.decision_type not in _ACTED_ON:
        return False
    return bool(set(thread.resolve_tags) & set(advice.tags))


def process_threads(
    campaign: Campaign,
    advice: AdviceOption,
    decision: NpcDecision,
    resolving_turn: int,
) -> Tuple[List[AppliedDiff], List[ThreadEvent]]:
    """Advance every open thread one turn: resolve first, then escalate.

    Mutates thread lifecycle fields and (via ``apply_diffs``) the world state.
    Returns the escalation diffs plus the events the aftermath should narrate.
    Threads opened later this same turn are not in ``campaign.open_threads``
    yet, so a new thread never escalates on the turn it opens.
    """
    variables = campaign.world_state.variables
    factions_by_id = {f.id: f for f in campaign.world_state.factions}
    diffs: List[AppliedDiff] = []
    events: List[ThreadEvent] = []

    for thread in campaign.open_threads:
        if thread.status == ThreadStatus.RESOLVED:
            continue

        if _resolved_by_advice(thread, advice, decision) or _conditions_hold(
            thread, variables, factions_by_id
        ):
            thread.status = ThreadStatus.RESOLVED
            thread.turn_resolved = resolving_turn
            thread.due_turn = None
            note = thread.resolution_note or f"{thread.title} was closed out."
            events.append(ThreadEvent(thread.id, thread.title, "resolved", note))
            continue

        if (
            thread.due_turn is not None
            and resolving_turn >= thread.due_turn
            and thread.escalation_effects
        ):
            diffs += apply_diffs(
                variables,
                thread.escalation_effects,
                reason=f"Open thread escalated — {thread.title}",
                source_type=SourceType.THREAD,
            )
            thread.status = ThreadStatus.ESCALATING
            thread.escalation_count += 1
            if thread.repeat_every > 0:
                thread.due_turn = resolving_turn + thread.repeat_every
            else:
                thread.due_turn = None
            note = thread.escalation_note or f"{thread.title} escalated unresolved."
            events.append(ThreadEvent(thread.id, thread.title, "escalated", note))

    return diffs, events
