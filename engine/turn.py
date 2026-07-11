"""Turn resolution -- the deterministic one-step advance of a campaign.

``advance_turn`` is the single entry point that turns a chosen piece of advice
into consequences. It is deliberately pure with respect to the campaign object
(it mutates it in place and returns a ``TurnResult``) and depends only on the
engine package, never on FastAPI.
"""

from __future__ import annotations

from typing import List, Optional

from engine import factions, rules
from engine.consequences import build_consequence_report, build_consequence_stack
from engine.diffs import apply_diffs
from engine.ledger import record_precedents
from engine.threads import process_threads
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


class UnknownDocument(Exception):
    """Raised when a cited document id is unknown or not yet available."""


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


def _resolve_citations(campaign: Campaign, cited_document_ids, resolving_turn: int):
    """Resolve cited document ids to Documents available on this turn."""
    if not cited_document_ids:
        return []
    by_id = {doc.id: doc for doc in campaign.documents}
    citations = []
    for doc_id in cited_document_ids:
        doc = by_id.get(doc_id)
        if doc is None or doc.turn_number > resolving_turn:
            raise UnknownDocument(doc_id)
        citations.append(doc)
    return citations


def advance_turn(
    campaign: Campaign,
    advice_id: str,
    cited_document_ids: Optional[List[str]] = None,
) -> TurnResult:
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

    citations = _resolve_citations(campaign, cited_document_ids, resolving_turn)
    decision = rules.decide(campaign, advice, citations)

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
    # Repeating an emergency precedent already on the institutional ledger
    # compounds: the repetition is priced as its own legible diff batch.
    if decision.precedent_adjustments:
        diffs += apply_diffs(
            variables,
            decision.precedent_adjustments,
            reason=decision.precedent_reason or "Precedent repeated",
            source_type=SourceType.DECISION,
        )
    # Staking the memo on contested material costs the consultant credibility.
    if decision.citation_adjustments:
        diffs += apply_diffs(
            variables,
            decision.citation_adjustments,
            reason=decision.citation_reason or "Cited contested evidence",
            source_type=SourceType.DECISION,
        )
    diffs += apply_diffs(
        variables,
        rules.AMBIENT_DRIFT,
        reason="Ambient crisis pressure",
        source_type=SourceType.AMBIENT,
    )

    # Open threads resolve or escalate before the failure check, so an
    # unaddressed standing risk can itself end the engagement.
    thread_diffs, thread_events = process_threads(
        campaign, advice, decision, resolving_turn
    )
    diffs += thread_diffs

    # Faction relationships move on the record: trust follows how the advice
    # served the caller, influence follows sustained pressure, and a faction
    # out of trust and under pressure may leak a private record this turn.
    faction_shifts = factions.update_faction_relations(
        campaign, advice, decision, diffs
    )
    leak_diffs, leak_media_lines, leak_canon = factions.process_leaks(
        campaign, resolving_turn
    )
    diffs += leak_diffs

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
    consequence_stack.escalated_threads = [
        f"{e.title} — {e.note}" for e in thread_events if e.kind == "escalated"
    ]
    consequence_stack.resolved_threads = [
        f"{e.title} — {e.note}" for e in thread_events if e.kind == "resolved"
    ]
    consequence_stack.media_framing.extend(leak_media_lines)

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
        tags=list(advice.tags)
        + [decision.decision_type.lower()]
        + (["evidence_cited"] if decision.cited_document_ids else []),
    )
    consequence_stack.canonized_events = [canon_entry.title]
    campaign.canon.append(canon_entry)
    if leak_canon is not None:
        campaign.canon.append(leak_canon)
        consequence_stack.canonized_events.append(leak_canon.title)

    # Record any emergency precedent this decision set on the debt ledger and
    # surface it in the turn's legal fallout so the cost is visible at once.
    for precedent in record_precedents(
        campaign, advice, decision, resolving_turn, canon_entry.id
    ):
        consequence_stack.legal_fallout.append(
            f"Precedent recorded — {precedent.label}: {precedent.detail}"
        )
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
        faction_shifts=faction_shifts,
    )
    campaign.turn_history.append(turn_result)
    return turn_result
