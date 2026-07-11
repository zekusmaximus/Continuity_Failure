"""Deterministic causal lead and future hook -- Wave 3 Batch B1.

``build_consequence_lead`` composes a one-glance orientation for a resolved
turn from values resolution has ALREADY produced: the advice option, the NPC
decision, the applied diffs, thread and precedent events, the consequence
stack, and the terminal status. It is stdlib-only, mutates nothing, re-runs no
rules, and reads no post-resolution mutable state. The applied diffs and the
consequence report remain the authority for attribution and clamping; every
sentence here carries references back to the record it summarizes.

Priority is pinned and stable:

  headline  1. terminal failure/completion fact, if this turn ended the campaign;
            2. the client decision and advice label;
            3. the largest absolute applied movement, tie-broken by humanized
               variable name and then diff order.
  hook      escalated thread -> newly opened thread -> newly recorded
            precedent -> unresolved risk named by the consequence stack -> none.

Truthfulness rules: delayed/rejected advice is said to have not landed rather
than implying its proposed effect applied, and movement whose dominant source
is ambient/thread/leak pressure names that source instead of the player.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from engine.models import (
    AdviceOption,
    AppliedDiff,
    CampaignStatus,
    ConsequenceLead,
    ConsequenceReference,
    ConsequenceStack,
    DecisionType,
    NpcDecision,
    OpenThread,
    PrecedentEntry,
    SourceType,
)
from engine.state import humanize_variable
from engine.threads import ThreadEvent

# How the client's mediation reads in one clause, keyed by decision type.
# Phrasing never implies a delayed/rejected recommendation took effect.
_DECISION_CLAUSE = {
    DecisionType.FOLLOWED: "the {decider} carried it out as advised",
    DecisionType.PARTIALLY_FOLLOWED: "the {decider} adopted part of it",
    DecisionType.MODIFIED: "the {decider} acted, but changed the terms",
    DecisionType.DELAYED: (
        "the {decider} put it on hold — none of its proposed effects landed this turn"
    ),
    DecisionType.REJECTED: (
        "the {decider} refused it — none of its proposed effects landed this turn"
    ),
}

# Movement whose dominant source is the decision pipeline is attributed to the
# recorded decision; anything else names its own source, never the player.
_MOVEMENT_BY_SOURCE = {
    SourceType.ADVICE: "{label} {verb} {size} under the recorded decision",
    SourceType.NPC_MODIFICATION: "the {decider}'s own action moved {label} {signed}",
    SourceType.DECISION: "the decision's recorded cost moved {label} {signed}",
    SourceType.AMBIENT: "ambient crisis pressure — not the decision — moved {label} {signed}",
    SourceType.THREAD: "an open thread's escalation moved {label} {signed}",
    SourceType.LEAK: "a faction leak moved {label} {signed}",
}


def _signed(delta: int) -> str:
    return f"+{delta}" if delta > 0 else str(delta)


def _largest_movement(diffs: Sequence[AppliedDiff]) -> Optional[str]:
    """The variable with the largest absolute net movement this turn.

    Net movement is summed over the turn's diffs per variable. Ties break by
    humanized variable name, then by first appearance in diff order -- pinned
    so the same record always leads with the same variable.
    """
    order: List[str] = []
    net: Dict[str, int] = {}
    for diff in diffs:
        if diff.variable not in net:
            net[diff.variable] = 0
            order.append(diff.variable)
        net[diff.variable] += diff.delta
    moved = [variable for variable in order if net[variable] != 0]
    if not moved:
        return None
    return min(
        moved,
        key=lambda variable: (
            -abs(net[variable]),
            humanize_variable(variable),
            order.index(variable),
        ),
    )


def _dominant_source(diffs: Sequence[AppliedDiff], variable: str) -> str:
    """The source type contributing the most absolute movement to ``variable``.

    Ties break by first appearance in diff order, so attribution is stable.
    """
    totals: Dict[str, int] = {}
    first_seen: Dict[str, int] = {}
    for index, diff in enumerate(diffs):
        if diff.variable != variable:
            continue
        totals[diff.source_type] = totals.get(diff.source_type, 0) + abs(diff.delta)
        first_seen.setdefault(diff.source_type, index)
    return min(totals, key=lambda source: (-totals[source], first_seen[source]))


def _movement_clause(
    diffs: Sequence[AppliedDiff], variable: str, decider: str
) -> str:
    net = sum(diff.delta for diff in diffs if diff.variable == variable)
    source = _dominant_source(diffs, variable)
    template = _MOVEMENT_BY_SOURCE.get(source, _MOVEMENT_BY_SOURCE[SourceType.AMBIENT])
    return template.format(
        label=humanize_variable(variable),
        verb="rose" if net > 0 else "fell",
        size=abs(net),
        signed=_signed(net),
        decider=decider,
    )


def _future_hook(
    thread_events: Sequence[ThreadEvent],
    new_threads: Sequence[OpenThread],
    new_precedents: Sequence[PrecedentEntry],
    consequence_stack: ConsequenceStack,
    resolving_turn: int,
) -> tuple[str, List[ConsequenceReference]]:
    """One forward-looking fact already on the record, by pinned priority."""
    for event in thread_events:
        if event.kind == "escalated":
            return (
                f"{event.title} escalated this turn and remains unresolved on the record.",
                [ConsequenceReference(kind="thread", id=event.thread_id, label=event.title)],
            )
    if new_threads:
        thread = new_threads[0]
        due = f" It is due on turn {thread.due_turn}." if thread.due_turn is not None else ""
        return (
            f"{thread.title} is now open on the record.{due}",
            [ConsequenceReference(kind="thread", id=thread.id, label=thread.title)],
        )
    if new_precedents:
        precedent = new_precedents[0]
        return (
            f"{precedent.label} is now a recorded precedent on the institutional ledger.",
            [
                ConsequenceReference(
                    kind="precedent", id=precedent.id, label=precedent.label
                )
            ],
        )
    if consequence_stack.second_order:
        return (
            consequence_stack.second_order[0],
            [
                ConsequenceReference(
                    kind="decision",
                    id=f"turn_{resolving_turn}_second_order_0",
                    label="Second-order consequence",
                )
            ],
        )
    return "", []


def build_consequence_lead(
    *,
    resolving_turn: int,
    advice: AdviceOption,
    decision: NpcDecision,
    diffs: Sequence[AppliedDiff],
    thread_events: Sequence[ThreadEvent],
    new_threads: Sequence[OpenThread],
    new_precedents: Sequence[PrecedentEntry],
    consequence_stack: ConsequenceStack,
    status_after: str,
    failure_reason: Optional[str],
) -> ConsequenceLead:
    """Compose the turn's causal headline and future hook. Pure; mutates nothing."""
    references: List[ConsequenceReference] = []

    advice_label = advice.title or advice.label
    decision_clause = _DECISION_CLAUSE.get(
        decision.decision_type, _DECISION_CLAUSE[DecisionType.MODIFIED]
    ).format(decider=decision.decider)
    decision_sentence = f"You advised {advice_label}; {decision_clause}."
    decision_reference = ConsequenceReference(
        kind="decision", id=advice.id, label=advice_label
    )

    if status_after == CampaignStatus.FAILED:
        # Priority 1: the terminal fact leads. ``failure_reason`` is the
        # engine's own recorded reason, not new prose.
        headline = f"The engagement ended this turn: {failure_reason} {decision_sentence}"
        references.append(
            ConsequenceReference(
                kind="failure",
                id=f"turn_{resolving_turn}_failed",
                label="Engagement failed",
            )
        )
        references.append(decision_reference)
    elif status_after == CampaignStatus.COMPLETED:
        headline = (
            f"The engagement reached its final turn and closed. {decision_sentence}"
        )
        references.append(
            ConsequenceReference(
                kind="failure",
                id=f"turn_{resolving_turn}_completed",
                label="Engagement completed",
            )
        )
        references.append(decision_reference)
    else:
        variable = _largest_movement(diffs)
        references.append(decision_reference)
        if variable is None:
            headline = f"{decision_sentence} No tracked variable moved this turn."
        else:
            movement = _movement_clause(diffs, variable, decision.decider)
            headline = f"{decision_sentence} This turn's largest recorded move: {movement}."
            references.append(
                ConsequenceReference(
                    kind="diff", id=variable, label=humanize_variable(variable)
                )
            )

    future_hook, hook_references = _future_hook(
        thread_events, new_threads, new_precedents, consequence_stack, resolving_turn
    )
    references.extend(hook_references)

    return ConsequenceLead(
        headline=headline, future_hook=future_hook, references=references
    )
