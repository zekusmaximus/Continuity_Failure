"""Turn resolution -- the deterministic one-step advance of a campaign.

``advance_turn`` is the single entry point that turns a chosen piece of advice
into consequences. It is deliberately pure with respect to the campaign object
(it mutates it in place and returns a ``TurnResult``) and depends only on the
engine package, never on FastAPI.
"""

from __future__ import annotations

from typing import List

from engine import rules
from engine.consequences import build_consequence_report, build_consequence_stack
from engine.diffs import apply_diffs
from engine.models import (
    AdviceOption,
    AppliedDiff,
    CanonEntry,
    Campaign,
    CampaignStatus,
    DecisionType,
    FactClassification,
    PublicStatus,
    SourceType,
    TurnResult,
)


class UnknownAdviceOption(Exception):
    """Raised when a submitted advice id is not in the campaign's option set."""


def find_advice(campaign: Campaign, advice_id: str) -> AdviceOption:
    # Search current-turn options too, so turn-specific advice is playable on
    # its turn (available_advice() = global options + this turn's options).
    for option in campaign.available_advice():
        if option.id == advice_id:
            return option
    raise UnknownAdviceOption(advice_id)


def _scale_effects(effects, adherence):
    """Scale advice effects by the NPC adherence multiplier."""
    return {var: int(round(delta * adherence)) for var, delta in effects.items()}


def advance_turn(campaign: Campaign, advice_id: str) -> TurnResult:
    """Resolve the current turn against ``advice_id`` and advance the campaign.

    The sequence is:
      1. Resolve the NPC decision (how much of the advice is actually used).
      2. Apply the scaled advice effects.
      3. Apply the NPC's own modifications.
      4. Apply ambient crisis pressure.
      5. Refresh faction postures and crisis severity.
      6. Build an aftermath summary and canon entry.
      7. Check failure / completion.
      8. Increment the turn counter and record history.
    """
    if campaign.is_terminal():
        raise RuntimeError(
            f"Campaign {campaign.id} is terminal ({campaign.status}); "
            "no further turns can be advanced."
        )

    advice = find_advice(campaign, advice_id)
    resolving_turn = campaign.turn_number
    world_state = campaign.world_state
    variables = world_state.variables

    decision = rules.decide(campaign, advice)

    # Snapshot the pre-turn values so the consequence report can reconcile
    # start -> attributed deltas -> final for every touched variable.
    start_values = dict(variables)

    diffs: List[AppliedDiff] = []
    diffs += apply_diffs(
        variables,
        _scale_effects(advice.effects, decision.adherence),
        reason=f"Advice \u2014 {advice.label}",
        source_type=SourceType.ADVICE,
    )
    if decision.modifications:
        diffs += apply_diffs(
            variables,
            decision.modifications,
            reason=f"NPC modification ({decision.decision_type})",
            source_type=SourceType.NPC_MODIFICATION,
        )
    # Off-brief / red-line advice carries a deterministic, legible cost. It is
    # recorded as its own diff batch (source_type "decision") with a concrete
    # reason so the aftermath can always show why the consultant's standing moved.
    if decision.off_brief_adjustments:
        diffs += apply_diffs(
            variables,
            decision.off_brief_adjustments,
            reason=decision.cost_reason or "Off-brief advice",
            source_type=SourceType.DECISION,
        )
    diffs += apply_diffs(
        variables,
        rules.AMBIENT_DRIFT,
        reason="Ambient crisis pressure",
        source_type=SourceType.AMBIENT,
    )

    rules.update_faction_postures(campaign)
    rules.update_crisis_severity(campaign)

    # Failure / completion assessment happens after all diffs for this turn.
    failure_reason = rules.check_failure(variables)
    if failure_reason is not None:
        campaign.status = CampaignStatus.FAILED
        campaign.failure_reason = failure_reason

    campaign.turn_number += 1
    if campaign.status == CampaignStatus.ACTIVE and campaign.turn_number > campaign.max_turns:
        campaign.status = CampaignStatus.COMPLETED

    # Keep the nested world-state cursor aligned with the campaign cursor. A
    # terminal campaign uses max_turns + 1 to mean "all turns resolved", while
    # its freshness label below remains anchored to the final playable turn.
    world_state.turn_number = campaign.turn_number

    aftermath = rules.build_aftermath_summary(
        advice, decision, diffs, campaign.status, failure_reason
    )

    # Build the deterministic consequence stack and any threads it opens.
    consequence_stack, new_threads = build_consequence_stack(
        campaign, advice, decision, diffs, resolving_turn,
    )
    campaign.open_threads.extend(new_threads)

    canon_entry = CanonEntry(
        id=f"canon_turn_{resolving_turn}",
        turn_number=resolving_turn,
        category="decision",
        title=f"Turn {resolving_turn}: {decision.decision_type} on {advice.label}",
        body=aftermath,
        source=decision.decider,
        classification=FactClassification.CANON,
        public_status=PublicStatus.PUBLIC,
        involved_factions=[decision.decider],
        tags=list(advice.tags) + [decision.decision_type.lower()],
    )
    consequence_stack.canonized_events = [canon_entry.title]
    campaign.canon.append(canon_entry)
    if campaign.is_terminal():
        world_state.last_verified = (
            f"Turn {resolving_turn} \u00b7 Final operational snapshot (deterministic)"
        )
    else:
        world_state.last_verified = (
            f"Turn {campaign.turn_number} \u00b7 Operational snapshot (deterministic)"
        )

    turn_result = TurnResult(
        turn_number=resolving_turn,
        advice_id=advice.id,
        advice_label=advice.label,
        decision=decision,
        diffs=diffs,
        aftermath_summary=aftermath,
        canon_entry=canon_entry,
        status_after=campaign.status,
        consequence_stack=consequence_stack,
        failure_reason=failure_reason,
        consequence_report=build_consequence_report(
            start_values, diffs, advice, decision
        ),
    )
    campaign.turn_history.append(turn_result)
    return turn_result
