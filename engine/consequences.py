"""Deterministic consequence-stack generation.

The applied diffs are the authoritative record of what changed. This module
translates those diffs (plus the decision and the resulting state) into the
human-readable categories a consultant would actually brief: immediate effects,
second-order fallout, faction / media / legal reactions, and the canon and open
threads the turn leaves behind.

Everything here is deterministic and rule-based. There is no model call and no
randomness: the same campaign state always yields the same consequence text.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from engine.models import (
    AdviceEffectOutcome,
    AdviceMediation,
    AdviceOption,
    AppliedDiff,
    Campaign,
    ConsequenceDelta,
    ConsequenceReport,
    ConsequenceStack,
    DecisionType,
    FactionReaction,
    NpcDecision,
    OpenThread,
    SourceType,
    VariableConsequence,
)
from engine.state import humanize_variable, variable_direction


# ---------------------------------------------------------------------------
# Advice-keyed immediate consequences. Each tag gets a pool of civic, specific
# lines describing what the chosen path produced this turn. The decision type
# modulates the phrasing so a FOLLOWED advice reads differently from a DELAYED
# or MODIFIED one.
# ---------------------------------------------------------------------------

_IMMEDIATE: dict = {
    "disclosure": {
        DecisionType.FOLLOWED: [
            "The findings and response timeline are now on the public record.",
            "State liaison was briefed in writing before the press conference.",
        ],
        DecisionType.PARTIALLY_FOLLOWED: [
            "A controlled statement landed, but with the public-facing scope narrowed.",
            "Mitigation for hospital and schools was pre-positioned before the statement.",
        ],
        DecisionType.MODIFIED: [
            "A partial release was issued under scrutiny rather than the planned controlled rollout.",
        ],
        DecisionType.DELAYED: [
            "The disclosure was postponed; the public record stays incomplete for another cycle.",
        ],
        DecisionType.REJECTED: [
            "No public disclosure was issued; the preliminary result remains internal.",
        ],
    },
    "delay": {
        DecisionType.DELAYED: [
            "Public disclosure held pending confirmatory testing; order preserved for now.",
            "The disclosure-timing clock keeps running against the town.",
        ],
        DecisionType.MODIFIED: [
            "Forced off the delay posture into a partial release under active scrutiny.",
            "The record of the delay itself is now part of the story.",
        ],
        DecisionType.FOLLOWED: [
            "Delay advice adopted; the town waits on the second lab before any statement.",
        ],
        DecisionType.PARTIALLY_FOLLOWED: [
            "A softer delay: minor mitigation proceeds quietly while the public line holds.",
        ],
        DecisionType.REJECTED: [
            "The delay was overridden; officials moved to release despite the advice.",
        ],
    },
    "state_support": {
        DecisionType.FOLLOWED: [
            "State emergency assistance formally requested; tankers and operators inbound.",
            "The operational-necessity record supporting the request is documented.",
        ],
        DecisionType.PARTIALLY_FOLLOWED: [
            "A limited, time-bound state request submitted and downplayed publicly.",
        ],
        DecisionType.MODIFIED: [
            "The state ask was trimmed to limit intrusion, buying capacity at a political cost.",
        ],
        DecisionType.DELAYED: [
            "The state request was postponed; the liaison's offer sits unanswered.",
        ],
        DecisionType.REJECTED: [
            "No state request filed; the town holds out for a local resolution.",
        ],
    },
    "contractor": {
        DecisionType.FOLLOWED: [
            "Private pressure accelerated the repair timeline without public escalation.",
            "A contingency statement was held ready in case the squeeze failed.",
        ],
        DecisionType.PARTIALLY_FOLLOWED: [
            "Light contractor pressure applied; the timeline moved only modestly.",
        ],
        DecisionType.MODIFIED: [
            "Much of the contractor's terms conceded to keep certified crews on site.",
        ],
        DecisionType.DELAYED: [
            "The contractor negotiation was deferred; crews remain on scheduled work.",
        ],
        DecisionType.REJECTED: [
            "Contractor pressure abandoned; the town accepted the original timeline.",
        ],
    },
    "mutual_aid": {
        DecisionType.FOLLOWED: [
            "Regional mutual-aid activated; neighboring utilities and hospital resupply en route.",
            "Cooperative posture visibly demonstrated to the public and the state.",
        ],
        DecisionType.PARTIALLY_FOLLOWED: [
            "A partial mutual-aid package activated within the fiscal limit.",
        ],
        DecisionType.MODIFIED: [
            "Mutual aid shaped to protect hospital operations first.",
        ],
        DecisionType.DELAYED: [
            "Mutual-aid activation postponed; regional partners stand by.",
        ],
        DecisionType.REJECTED: [
            "Mutual aid declined; the town attempts a purely local response.",
        ],
    },
    "school_closure": {
        DecisionType.FOLLOWED: [
            "A written pressure threshold and staged closure protocol are now published for the south-zone schools.",
            "Parents have an on-the-record rule they can hold the town to.",
        ],
        DecisionType.PARTIALLY_FOLLOWED: [
            "Interim school guidance issued, but the exact closure threshold was hedged.",
        ],
        DecisionType.MODIFIED: [
            "The closure protocol was reshaped to fit political and fiscal limits.",
        ],
        DecisionType.DELAYED: [
            "The closure decision was deferred; schools stay open on an assumption.",
        ],
        DecisionType.REJECTED: [
            "No closure protocol issued; the superintendent is left without a defensible rule.",
        ],
    },
    "hospital_priority": {
        DecisionType.FOLLOWED: [
            "Documented priority allocation for dialysis and sterilization is in force.",
            "Tanker resupply is pre-staged against a clinical-pressure drop.",
        ],
        DecisionType.PARTIALLY_FOLLOWED: [
            "Clinical supply was assured informally to avoid spotlighting the shortage.",
        ],
        DecisionType.MODIFIED: [
            "Priority allocation was trimmed to limit the documented diversion of supply.",
        ],
        DecisionType.DELAYED: [
            "The priority-allocation decision was postponed; the hospital waits on a written commitment.",
        ],
        DecisionType.REJECTED: [
            "No priority allocation documented; clinical operations run on the general margin.",
        ],
    },
    "business_compensation": {
        DecisionType.FOLLOWED: [
            "Conservation restrictions now carry a funded, compliance-tied compensation framework.",
            "The strongest grounds for an injunction have been removed.",
        ],
        DecisionType.PARTIALLY_FOLLOWED: [
            "A limited compensation offer was floated alongside the restrictions.",
        ],
        DecisionType.MODIFIED: [
            "The compensation framework was trimmed to what the budget could bear.",
        ],
        DecisionType.DELAYED: [
            "The compensation decision was deferred; the injunction threat stays live.",
        ],
        DecisionType.REJECTED: [
            "No compensation offered; restrictions proceed over business objections.",
        ],
    },
}


def _primary_tag(advice: AdviceOption) -> str:
    for tag in advice.tags:
        if tag in _IMMEDIATE:
            return tag
    return "disclosure"


# The engagement has three legible phases; the same advice tag reads differently
# in the opening, mid-crisis, and closeout stretches. Purely a function of turn.
_PHASE_LABEL = {
    "early": "opening phase",
    "mid": "mid-crisis phase",
    "late": "closeout phase",
}


def _turn_phase(turn: int) -> str:
    if turn <= 3:
        return "early"
    if turn <= 7:
        return "mid"
    return "late"


def _immediate_for(
    campaign: Campaign,
    advice: AdviceOption,
    decision: NpcDecision,
    resolving_turn: int,
) -> List[str]:
    """Immediate-consequence lines for the turn.

    The tag/decision pool supplies the substance; a deterministic contextual
    opener ties the effect to *this* turn's specific call (its caller and
    situation) and the engagement phase, so choosing the same advice tag on a
    later turn no longer produces identical text. Pure function of
    (advice, decision, state, turn) -- no randomness.
    """
    tag = _primary_tag(advice)
    pool = _IMMEDIATE.get(tag, {})
    lines = list(pool.get(decision.decision_type, []))
    if not lines:
        lines.append(
            f"The {decision.decider} responded to the advice ({decision.decision_type})."
        )

    # Fetch by resolving_turn: by the time consequences are built the campaign's
    # turn counter has already advanced, so current_call() would point at the
    # *next* call. The seed guarantees a call for every turn 1..max_turns.
    call = campaign.client_calls.get(resolving_turn)
    if call is not None:
        phase = _PHASE_LABEL[_turn_phase(resolving_turn)]
        lines.insert(
            0,
            f"Turn {resolving_turn} · {phase}: acting on {call.caller}'s call "
            f"— {call.summary}",
        )
    return lines


# ---------------------------------------------------------------------------
# Second-order consequences, read off the *resulting* state.
# ---------------------------------------------------------------------------

def _second_order(variables) -> List[str]:
    out: List[str] = []
    water = variables.get("water_security", 50)
    hospital = variables.get("hospital_stability", 50)
    trust = variables.get("public_trust", 50)
    oversight = variables.get("state_oversight_risk", 0)
    legal = variables.get("legal_exposure", 0)
    media = variables.get("media_pressure", 0)
    dependency = variables.get("contractor_dependency", 0)
    budget = variables.get("budget_capacity", 50)
    staff = variables.get("staff_capacity", 50)

    if water <= 25:
        out.append("Supply margins are thin enough that the next failure could force mandatory curtailment.")
    if hospital <= 30:
        out.append("Hospital clinical operations are within one pressure drop of an elective-cancellation cascade.")
    if oversight >= 60:
        out.append("The state's posture is shifting from advisory toward a formal oversight review.")
    if legal >= 60:
        out.append("Disclosure-timing exposure is high enough to sustain a litigation threat.")
    if media >= 60:
        out.append("The rumor frame is hardening into the dominant public narrative.")
    if dependency >= 65:
        out.append("Structural dependence on the sole contractor is becoming a precedent, not a one-off.")
    if budget <= 20:
        out.append("Fiscal headroom is nearly exhausted; further emergency spend is politically costly.")
    if staff <= 25:
        out.append("Operator capacity is near collapse; emergency shift coverage is unsustainable.")
    if not out:
        out.append("No single variable is at a breaking point, but several are trending the wrong way.")
    return out


# ---------------------------------------------------------------------------
# Faction reactions, keyed off the resulting state per faction.
# ---------------------------------------------------------------------------

def _faction_reactions(campaign: Campaign) -> List[FactionReaction]:
    v = campaign.world_state.variables
    trust = v.get("public_trust", 50)
    media = v.get("media_pressure", 0)
    order = v.get("public_order", 50)
    oversight = v.get("state_oversight_risk", 0)
    hospital = v.get("hospital_stability", 50)
    dependency = v.get("contractor_dependency", 0)
    school = v.get("school_disruption", 0)

    reactions: List[FactionReaction] = []
    by_id = {f.id: f for f in campaign.world_state.factions}

    def add(fid: str, text: str) -> None:
        f = by_id.get(fid)
        if f is not None:
            reactions.append(FactionReaction(faction_id=fid, faction_name=f.name, reaction=text))

    if trust < 55:
        add("council_opposition",
            "Emboldened; compiling the decision timeline into a hearing record.")
    else:
        add("council_opposition",
            "Circumspect; unable to find a clean line of attack yet.")
    if media >= 55:
        add("media_rumor_network",
            "Amplifying; a leak or contradiction is driving the coverage.")
    else:
        add("media_rumor_network",
            "Circulating the official line; no strong seam to pull yet.")
    if oversight >= 60:
        add("state_liaison",
            "Intervening posture; treating late notification as a documented failing.")
    else:
        add("state_liaison",
            "Advisory posture; resources on offer if the record is kept clean.")
    if hospital <= 35:
        add("hospital", "Alarmed; clinical margins are too thin to absorb another drop.")
    else:
        add("hospital", "Watchful; priority mitigation is holding for now.")
    if dependency >= 60:
        add("utility_contractor", "Entrenched; treating emergency scope as leverage.")
    else:
        add("utility_contractor", "Cooperative within current terms.")
    if school >= 55 or trust < 50:
        add("parent_resident_coalition",
            "Pressing for an on-the-record school decision before pressure drops again.")
    if order < 50:
        add("business_alliance", "Restive; weighing an injunction over mandatory restrictions.")
    return reactions


# ---------------------------------------------------------------------------
# Media framing and legal fallout.
# ---------------------------------------------------------------------------

def _media_framing(variables, decision: NpcDecision) -> List[str]:
    media = variables.get("media_pressure", 0)
    out: List[str] = []
    if media >= 65:
        out.append("Headline frame: 'town under a cloud' -- coverage leads with concealment language.")
    elif media >= 45:
        out.append("Headline frame: 'water worries mount' -- reactive, not yet dominant.")
    else:
        out.append("Headline frame: 'town responds' -- coverage follows the official line for now.")
    if decision.decision_type in (DecisionType.DELAYED, DecisionType.MODIFIED):
        out.append("Editorial angle: officials 'struggling to get ahead of the story'.")
    if decision.decision_type == DecisionType.REJECTED:
        out.append("Editorial angle: 'consultant advice set aside' framing begins to circulate.")
    return out


def _legal_fallout(variables, advice: AdviceOption, decision: NpcDecision) -> List[str]:
    legal = variables.get("legal_exposure", 0)
    out: List[str] = []
    tag = _primary_tag(advice)
    if tag == "delay" or decision.decision_type == DecisionType.DELAYED:
        out.append("Disclosure-timing liability: the gap between awareness and notice is now part of the record.")
    if legal >= 65:
        out.append("Litigation posture: plaintiffs' counsel has a colorable timeline argument.")
    elif legal >= 45:
        out.append("Litigation posture: exposure is building but not yet decisive.")
    if "contractor" in advice.tags and decision.decision_type in (DecisionType.MODIFIED,):
        out.append("Procurement posture: conceded emergency terms may be cited as sole-source precedent.")
    if not out:
        out.append("Legal posture: no new cause of action crystallized this turn.")
    return out


# ---------------------------------------------------------------------------
# Open threads opened or escalated by this turn.
# ---------------------------------------------------------------------------

def _threads_for_turn(
    campaign: Campaign, advice: AdviceOption, decision: NpcDecision,
    variables, resolving_turn: int,
) -> List[OpenThread]:
    existing = {t.id for t in campaign.open_threads}
    new: List[OpenThread] = []
    media = variables.get("media_pressure", 0)
    trust = variables.get("public_trust", 50)
    oversight = variables.get("state_oversight_risk", 0)
    dependency = variables.get("contractor_dependency", 0)
    school = variables.get("school_disruption", 0)
    tag = _primary_tag(advice)

    def maybe(tid, title, summary, ttags):
        if tid not in existing:
            new.append(OpenThread(
                id=tid, title=title, summary=summary,
                turn_opened=resolving_turn, tags=ttags,
            ))
            existing.add(tid)

    if (tag == "delay" or decision.decision_type == DecisionType.DELAYED) and media >= 45:
        maybe(
            "thread_concealment_narrative",
            "'Cover-up' concealment narrative",
            "A delay posture under rising media pressure let a concealment frame take hold.",
            ["narrative", "trust", "media"],
        )
    if oversight >= 60:
        maybe(
            "thread_oversight_designation",
            "State oversight designation threat",
            "Late notification and sliding metrics put a formal oversight review in play.",
            ["state", "oversight", "intervention"],
        )
    if (tag == "contractor") and dependency >= 60:
        maybe(
            "thread_contractor_precedent",
            "Sole-source contractor precedent",
            "Conceded emergency terms are hardening into structural dependency.",
            ["contractor", "procurement", "dependency"],
        )
    if school >= 55 or trust < 45:
        maybe(
            "thread_school_standoff",
            "School closure standoff",
            "Parents and the superintendent demand an on-the-record closure threshold.",
            ["school", "parent_pressure"],
        )
    if trust < 40:
        maybe(
            "thread_trust_collapse",
            "Public-trust collapse",
            "Trust has fallen far enough that emergency measures lose public consent.",
            ["trust", "consent"],
        )
    return new


# ---------------------------------------------------------------------------
# Public entry point.
# ---------------------------------------------------------------------------

def build_consequence_stack(
    campaign: Campaign,
    advice: AdviceOption,
    decision: NpcDecision,
    diffs: List,
    resolving_turn: int,
) -> Tuple[ConsequenceStack, List[OpenThread]]:
    """Build a deterministic ConsequenceStack plus any threads opened this turn.

    ``diffs`` are the authoritative applied diffs for the turn; this function
    only *reads* campaign state to narrate them -- it never mutates state.
    """
    variables = campaign.world_state.variables

    new_threads = _threads_for_turn(campaign, advice, decision, variables, resolving_turn)

    stack = ConsequenceStack(
        immediate=_immediate_for(campaign, advice, decision, resolving_turn),
        second_order=_second_order(variables),
        faction_reactions=_faction_reactions(campaign),
        media_framing=_media_framing(variables, decision),
        legal_fallout=_legal_fallout(variables, advice, decision),
        canonized_events=[],  # filled by the turn resolver from the canon entry
        opened_threads=[t.title for t in new_threads],
    )

    # Tag the source of the largest advice/npc move into the immediate list so
    # the cause is legible right away.
    advice_or_npc = [
        d for d in diffs
        if d.source_type in (SourceType.ADVICE, SourceType.NPC_MODIFICATION)
    ]
    if advice_or_npc:
        top = max(advice_or_npc, key=lambda d: abs(d.delta))
        sign = "+" if top.delta > 0 else ""
        stack.immediate.append(
            f"Largest advice/client move: {humanize_variable(top.variable)} "
            f"{top.old_value}\u2192{top.new_value} "
            f"({sign}{top.delta}, {top.source_type})."
        )

    return stack, new_threads


# ---------------------------------------------------------------------------
# Causal consequence report: the per-variable start -> deltas -> final
# reconciliation the aftermath UI and dossier render verbatim.
# ---------------------------------------------------------------------------

def _advice_outcome(
    proposed: int, applied: int, decision: NpcDecision
) -> str:
    """Classify how the caller's mediation left one proposed effect."""
    if applied == proposed:
        return AdviceEffectOutcome.APPLIED
    if decision.decision_type == DecisionType.REJECTED:
        return AdviceEffectOutcome.REJECTED
    if decision.decision_type == DecisionType.DELAYED and applied == 0:
        return AdviceEffectOutcome.DELAYED
    return AdviceEffectOutcome.REDUCED


def build_consequence_report(
    start_values: Dict[str, int],
    diffs: List[AppliedDiff],
    advice: AdviceOption,
    decision: NpcDecision,
) -> ConsequenceReport:
    """Build the authoritative per-variable causal decomposition of a turn.

    ``start_values`` is the world-state snapshot captured *before* any of this
    turn's diffs were applied; ``diffs`` are the ordered authoritative applied
    diffs. The report is pure bookkeeping over those records -- it never
    recomputes effects -- plus the proposed-versus-applied advice mediation,
    which is the one fact the diff list cannot express (a fully rejected
    proposal leaves no diff at all).

    Invariant: for every entry, ``start_value + sum(d.delta) == final_value``.
    """
    by_variable: Dict[str, List[AppliedDiff]] = {}
    for diff in diffs:
        by_variable.setdefault(diff.variable, []).append(diff)

    variables = list(by_variable.keys())
    # Advice-targeted variables that never moved (rejected/delayed/rounded-out
    # proposals) still get an entry so the mediation is visible, not implied.
    for variable, proposed in advice.effects.items():
        if proposed != 0 and variable in start_values and variable not in by_variable:
            variables.append(variable)

    entries: List[VariableConsequence] = []
    for variable in variables:
        var_diffs = by_variable.get(variable, [])
        start = var_diffs[0].old_value if var_diffs else start_values[variable]
        final = var_diffs[-1].new_value if var_diffs else start

        mediation = None
        proposed = advice.effects.get(variable, 0)
        if proposed != 0:
            applied = sum(
                d.delta for d in var_diffs if d.source_type == SourceType.ADVICE
            )
            expected = int(round(proposed * decision.adherence))
            mediation = AdviceMediation(
                proposed_delta=proposed,
                adherence=decision.adherence,
                expected_delta=expected,
                applied_delta=applied,
                outcome=_advice_outcome(proposed, applied, decision),
                clamped=applied != expected,
            )

        entries.append(
            VariableConsequence(
                variable=variable,
                label=humanize_variable(variable),
                direction=variable_direction(variable),
                start_value=start,
                final_value=final,
                net_delta=final - start,
                deltas=[
                    ConsequenceDelta(
                        source_type=d.source_type,
                        delta=d.delta,
                        reason=d.reason,
                        value_before=d.old_value,
                        value_after=d.new_value,
                    )
                    for d in var_diffs
                ],
                advice=mediation,
            )
        )

    entries.sort(key=lambda e: (-abs(e.net_delta), e.variable))
    return ConsequenceReport(variables=entries)
