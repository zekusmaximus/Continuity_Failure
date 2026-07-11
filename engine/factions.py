"""Living factions: deterministic trust/influence updates and the leak rule.

Faction fields (``trust_in_player``, ``influence``, ``current_pressure``) live
outside ``WorldState.variables``, so ``apply_diffs`` does not cover them. To
keep the legibility rule intact, every move is recorded as a
:class:`FactionShift` -- old value, new value, and a plain-language reason --
and shipped with the turn result.

The leak rule is the sharp edge: a faction whose working trust in the
consultant has collapsed while its own pressure is high puts a private record
into the rumor feed. Deterministic thresholds, at most one leak per turn, one
leak per faction per campaign, and the leak never rewrites prior canon -- it
flips the document's public status and adds a *new* canon entry.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from engine.diffs import apply_diffs
from engine.ledger import PrecedentKind
from engine.models import (
    AdviceOption,
    AppliedDiff,
    Campaign,
    CanonEntry,
    DecisionType,
    Faction,
    FactClassification,
    FactionShift,
    NpcDecision,
    PrecedentEntry,
    PublicStatus,
    SourceType,
)
from engine.state import clamp, variable_direction

# --- Trust thresholds (read by the decision rules in engine/rules.py) -------

TRUST_LOW = 35          # at or below: the caller second-guesses the consultant
TRUST_HIGH = 70         # at or above: the caller extends benefit of the doubt
TRUST_DISCOMFORT_PENALTY = 10
TRUST_DISCOMFORT_RELIEF = 8

# --- Trust/influence/pressure update rules ----------------------------------

TRUST_GAIN_FOLLOWED = 4        # advice followed and the caller's priorities improved
TRUST_GAIN_PARTIAL = 2
TRUST_LOSS_REJECTED_OFF_BRIEF = 2
TRUST_LOSS_RED_LINE = 8
PRESSURE_GAIN_RED_LINE = 5
INFLUENCE_GAIN_HIGH_PRESSURE = 2   # pressure >= 70: the crisis is theirs to carry
INFLUENCE_DECAY_LOW_PRESSURE = 2   # pressure <= 30: attention moves elsewhere
INFLUENCE_HIGH = 70                # at or above: reactions carry visible weight

# --- Leak thresholds ---------------------------------------------------------

LEAK_TRUST_AT_MOST = 30
LEAK_PRESSURE_AT_LEAST = 65
LEAK_EFFECTS = {"media_pressure": +5, "public_trust": -3, "information_integrity": -2}


def _shift(
    faction: Faction, field_name: str, delta: int, reason: str
) -> Optional[FactionShift]:
    old = getattr(faction, field_name)
    new = clamp(old + delta)
    if new == old:
        return None
    setattr(faction, field_name, new)
    return FactionShift(
        faction_id=faction.id,
        faction_name=faction.name,
        field=field_name,
        old_value=old,
        new_value=new,
        delta=new - old,
        reason=reason,
    )


def _priorities_improved(
    profile_priorities: List[str], diffs: List[AppliedDiff]
) -> bool:
    """Did this turn's advice/client moves net-improve what the caller weighs?

    Direction-aware: on a higher-is-worse variable a negative move counts as
    improvement. Only advice and client-modification diffs are attributed --
    ambient drift is nobody's doing.
    """
    score = 0
    for diff in diffs:
        if diff.source_type not in (SourceType.ADVICE, SourceType.NPC_MODIFICATION):
            continue
        if diff.variable not in profile_priorities:
            continue
        if variable_direction(diff.variable) == "higher_is_worse":
            score -= diff.delta
        else:
            score += diff.delta
    return score > 0


def update_faction_relations(
    campaign: Campaign,
    advice: AdviceOption,
    decision: NpcDecision,
    diffs: List[AppliedDiff],
) -> List[FactionShift]:
    """Update the caller's trust and every faction's influence. Deterministic.

    Wave-1 scope keeps trust moves to the caller only; cross-faction trust
    propagation is roadmap work alongside branchable calls.
    """
    shifts: List[FactionShift] = []
    call = campaign.client_calls.get(decision_turn(campaign, decision))
    caller = None
    if call is not None:
        caller = next(
            (f for f in campaign.world_state.factions
             if f.id == call.caller_faction_id),
            None,
        )

    if caller is not None:
        profile = call.decision_profile
        priorities = list(profile.priorities) if profile is not None else []
        red_line_hit = decision.cost_reason.startswith("Red line")
        if red_line_hit:
            shifts.append(_shift(
                caller, "trust_in_player", -TRUST_LOSS_RED_LINE,
                f"The consultant proposed {advice.label} across a stated red line.",
            ))
            shifts.append(_shift(
                caller, "current_pressure", +PRESSURE_GAIN_RED_LINE,
                "A red-line proposal escalated the standoff instead of easing it.",
            ))
        elif decision.decision_type == DecisionType.FOLLOWED and _priorities_improved(
            priorities, diffs
        ):
            shifts.append(_shift(
                caller, "trust_in_player", +TRUST_GAIN_FOLLOWED,
                f"Followed {advice.label} and what the {caller.name} weighs moved the right way.",
            ))
        elif decision.decision_type == DecisionType.PARTIALLY_FOLLOWED and _priorities_improved(
            priorities, diffs
        ):
            shifts.append(_shift(
                caller, "trust_in_player", +TRUST_GAIN_PARTIAL,
                f"Acted on part of {advice.label}; the {caller.name}'s priorities still improved.",
            ))
        elif decision.decision_type == DecisionType.REJECTED and decision.off_brief:
            shifts.append(_shift(
                caller, "trust_in_player", -TRUST_LOSS_REJECTED_OFF_BRIEF,
                "The call was spent on advice the caller had not asked for.",
            ))

    for faction in campaign.world_state.factions:
        if faction.current_pressure >= 70:
            shifts.append(_shift(
                faction, "influence", +INFLUENCE_GAIN_HIGH_PRESSURE,
                "Sustained pressure keeps this faction at the center of decisions.",
            ))
        elif faction.current_pressure <= 30:
            shifts.append(_shift(
                faction, "influence", -INFLUENCE_DECAY_LOW_PRESSURE,
                "With little pressure to apply, attention moves elsewhere.",
            ))

    return [s for s in shifts if s is not None]


def decision_turn(campaign: Campaign, decision: NpcDecision) -> int:
    """The turn this decision resolved (campaign cursor has not advanced yet)."""
    return campaign.turn_number


def _has_leaked_before(campaign: Campaign, faction: Faction) -> bool:
    marker = f"precedent_leak_{faction.id}_"
    return any(entry.id.startswith(marker) for entry in campaign.debt_ledger)


def process_leaks(
    campaign: Campaign, resolving_turn: int
) -> Tuple[List[AppliedDiff], List[str], Optional[CanonEntry]]:
    """Let at most one collapsed-trust, high-pressure faction leak this turn.

    Returns ``(diffs, media_lines, canon_entry)``. The leak flips one available
    PRIVATE document to LEAKED, applies the leak costs as an authoritative diff
    batch, records the event on the debt ledger (one leak per faction per
    campaign), and writes a NEW canon entry -- prior canon is never mutated.
    """
    candidates = [
        f for f in campaign.world_state.factions
        if f.trust_in_player <= LEAK_TRUST_AT_MOST
        and f.current_pressure >= LEAK_PRESSURE_AT_LEAST
        and not _has_leaked_before(campaign, f)
    ]
    if not candidates:
        return [], [], None
    # Deterministic pick: the faction with the least trust; ties break by id.
    leaker = sorted(candidates, key=lambda f: (f.trust_in_player, f.id))[0]

    private_docs = sorted(
        (
            d for d in campaign.documents
            if d.public_status == PublicStatus.PRIVATE
            and d.turn_number <= resolving_turn
        ),
        key=lambda d: (d.turn_number, d.id),
    )
    if not private_docs:
        return [], [], None
    document = private_docs[0]
    document.public_status = PublicStatus.LEAKED

    reason = (
        f"Leak — {leaker.name} put “{document.title}” into the rumor feed"
    )
    diffs = apply_diffs(
        campaign.world_state.variables,
        LEAK_EFFECTS,
        reason=reason,
        source_type=SourceType.LEAK,
    )
    campaign.debt_ledger.append(PrecedentEntry(
        id=f"precedent_leak_{leaker.id}_t{resolving_turn}",
        kind=PrecedentKind.LEAK,
        label="Private record leaked",
        turn_recorded=resolving_turn,
        detail=(
            f"{leaker.name}, out of trust and under pressure, leaked "
            f"“{document.title}”. Private channels are no longer assumed safe."
        ),
        canon_id=f"canon_leak_{leaker.id}_t{resolving_turn}",
    ))
    canon_entry = CanonEntry(
        id=f"canon_leak_{leaker.id}_t{resolving_turn}",
        turn_number=resolving_turn,
        category="leak",
        title=f"Turn {resolving_turn}: {leaker.name} leaked “{document.title}”",
        body=(
            f"With working trust exhausted and pressure unrelieved, the "
            f"{leaker.name} pushed a private record into public circulation."
        ),
        source=leaker.name,
        classification=FactClassification.CANON,
        public_status=PublicStatus.LEAKED,
        involved_factions=[leaker.name],
        tags=["leak"],
    )
    media_lines = [
        f"{leaker.name} leaked “{document.title}” — the rumor feed is quoting it verbatim."
    ]
    return diffs, media_lines, canon_entry
