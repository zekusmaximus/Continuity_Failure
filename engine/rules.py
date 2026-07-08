"""Deterministic rules: failure thresholds, ambient pressure, NPC decisions.

This module contains the legible, rule-based logic that turns a chosen piece of
advice into consequences. There is no randomness and no model call anywhere in
this file -- every branch is an explicit threshold so a turn is fully replayable
and every diff is explainable.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from engine.models import (
    AdviceOption,
    Campaign,
    DecisionType,
    NpcDecision,
    SourceType,
)
from engine.state import clamp


# An internal working draft of an NPC decision, before the public NpcDecision
# is assembled. The first three fields (decision_type, adherence, modifications)
# are authoritative and determinism-tested; the descriptive fields only surface
# *why* the client deviated, so the player can read the mediation.
class _DecisionDraft:
    __slots__ = (
        "decision_type", "adherence", "modifications",
        "deviation", "public_explanation", "private_motive", "resulting_risk",
    )

    def __init__(self, decision_type: str, adherence: float,
                 modifications, deviation="", public_explanation="",
                 private_motive="", resulting_risk=""):
        self.decision_type = decision_type
        self.adherence = adherence
        self.modifications = modifications
        self.deviation = deviation
        self.public_explanation = public_explanation
        self.private_motive = private_motive
        self.resulting_risk = resulting_risk


# ---------------------------------------------------------------------------
# Failure conditions. Each tuple is (variable, operator, threshold).
#   "<=" means "fails at or below threshold" (a capacity has collapsed).
#   ">=" means "fails at or above threshold" (a risk has become unmanageable).
# ---------------------------------------------------------------------------

FAILURE_THRESHOLDS: List[Tuple[str, str, int]] = [
    ("water_security", "<=", 10),
    ("hospital_stability", "<=", 10),
    ("public_order", "<=", 10),
    ("public_trust", "<=", 5),
    ("budget_capacity", "<=", 0),
    ("state_oversight_risk", ">=", 95),
    ("legal_exposure", ">=", 95),
]


def check_failure(variables: Dict[str, int]) -> Optional[str]:
    """Return a human-readable failure reason, or ``None`` if the state holds."""
    for variable, op, threshold in FAILURE_THRESHOLDS:
        value = variables.get(variable, 50)
        if op == "<=" and value <= threshold:
            return (
                f"{variable} collapsed to {value} "
                f"(failure threshold {op} {threshold})."
            )
        if op == ">=" and value >= threshold:
            return (
                f"{variable} reached {value} "
                f"(failure threshold {op} {threshold})."
            )
    return None


# ---------------------------------------------------------------------------
# Ambient pressure -- the crisis worsens on its own each turn if unmanaged.
# These are gentle by design; good advice offsets them, bad advice compounds.
# ---------------------------------------------------------------------------

AMBIENT_DRIFT: Dict[str, int] = {
    "water_security": -2,        # the underlying failure keeps degrading
    "hospital_stability": -1,
    "budget_capacity": -2,       # emergency spend accumulates
    "media_pressure": 3,         # rumor pressure builds
    "contractor_dependency": 1,
    "legal_exposure": 2,
    "school_disruption": 2,
    "staff_capacity": -1,
}


# ---------------------------------------------------------------------------
# NPC decision logic. The player selects advice; the Town Manager's Office
# decides how much of it to actually use, modulated by faction pressure.
# ---------------------------------------------------------------------------

DECIDER = "Town Manager's Office"


def _decide_disclosure(campaign: Campaign) -> _DecisionDraft:
    v = campaign.world_state.variables
    media = v.get("media_pressure", 0)
    legal = v.get("legal_exposure", 0)
    trust = v.get("public_trust", 50)

    if legal >= 60 or media >= 60:
        # Scrutinity is too high; officials must come clean.
        return _DecisionDraft(
            DecisionType.FOLLOWED, 1.0, {},
            deviation="None \u2014 the advice was adopted as written once scrutiny forced it.",
            public_explanation=(
                "Given the level of public attention, the Manager is releasing the "
                "findings and the response timeline in full."
            ),
            private_motive="Legal and media pressure made a partial posture indefensible.",
            resulting_risk="Short-term panic and a difficult news cycle.",
        )
    if media <= 25 and trust >= 60 and campaign.turn_number <= 4:
        # Early, quiet, trusted window -- the manager is tempted to soft-pedal.
        return _DecisionDraft(
            DecisionType.PARTIALLY_FOLLOWED, 0.6,
            {"media_pressure": 2, "information_integrity": -3},
            deviation="Trimmed the public-facing scope; held back detail while trust held.",
            public_explanation=(
                "A measured update has been issued; fuller detail will follow with "
                "the confirmatory result."
            ),
            private_motive="The early window looked survivable without a full release.",
            resulting_risk="A leak during the trimmed window becomes a concealment story.",
        )
    return _DecisionDraft(
        DecisionType.PARTIALLY_FOLLOWED, 0.75, {},
        deviation="Adopted the spirit of the disclosure but narrowed its public scope.",
        public_explanation="A controlled statement has been issued with mitigation pre-positioned.",
        private_motive="Wanted the credit for openness without the cost of full exposure.",
        resulting_risk="Controlled framing is brittle if the rumor feed moves first.",
    )


def _decide_delay(campaign: Campaign) -> _DecisionDraft:
    v = campaign.world_state.variables
    media = v.get("media_pressure", 0)
    legal = v.get("legal_exposure", 0)

    if media >= 55 or legal >= 55:
        # Can no longer delay under active scrutiny -- officials are forced to
        # pivot toward a partial release, but the pivot itself is costly: trust
        # and legal exposure still worsen as the record of the delay surfaces.
        return _DecisionDraft(
            DecisionType.MODIFIED, 0.3,
            {"information_integrity": +2, "public_trust": -2,
             "legal_exposure": +4, "media_pressure": +4},
            deviation="Pivoted from delay to a forced partial release under scrutiny.",
            public_explanation=(
                "The Manager is releasing what can be confirmed now, ahead of the "
                "full confirmatory result."
            ),
            private_motive="Could no longer hold the line; salvaging the appearance of initiative.",
            resulting_risk="The record of the delay itself becomes the liability.",
        )
    return _DecisionDraft(
        DecisionType.DELAYED, 0.35,
        {"information_integrity": -5, "public_trust": -4,
         "legal_exposure": +3, "media_pressure": +4},
        deviation="Held the public line and let the disclosure clock keep running.",
        public_explanation="The Manager will await confirmatory testing before any public statement.",
        private_motive="Bought time for the contractor and for political cover.",
        resulting_risk="Disclosure-timing liability compounds; a leak converts delay to cover-up.",
    )


def _decide_state_support(campaign: Campaign) -> _DecisionDraft:
    v = campaign.world_state.variables
    oversight = v.get("state_oversight_risk", 0)
    water = v.get("water_security", 50)

    if oversight >= 60:
        # Council majority resists further state intrusion; trims the ask.
        return _DecisionDraft(
            DecisionType.MODIFIED, 0.45,
            {"state_oversight_risk": +6, "public_trust": -2, "water_security": +4},
            deviation="Trimmed the state request to limit intrusion while accepting partial help.",
            public_explanation="A limited state assistance request has been submitted.",
            private_motive="The majority bloc refused a full request to avoid an oversight trajectory.",
            resulting_risk="A partial ask may still draw oversight without buying enough capacity.",
        )
    if water <= 20:
        # Crisis is acute enough that even wary officials accept the help.
        return _DecisionDraft(
            DecisionType.FOLLOWED, 0.9, {},
            deviation="None \u2014 the crisis was acute enough to accept the full request.",
            public_explanation="The Manager has formally requested state emergency assistance.",
            private_motive="Local capacity had failed; refusing was no longer credible.",
            resulting_risk="The support package may carry conditions approaching oversight.",
        )
    return _DecisionDraft(
        DecisionType.PARTIALLY_FOLLOWED, 0.7, {},
        deviation="Accepted state resources but downplayed the request publicly.",
        public_explanation="State resources are being brought in on a limited, time-bound basis.",
        private_motive="Wanted the capacity without owning a public admission of failure.",
        resulting_risk="Half-measures invite a later, less favorable intervention.",
    )


def _decide_contractor(campaign: Campaign) -> _DecisionDraft:
    v = campaign.world_state.variables
    dependency = v.get("contractor_dependency", 0)
    budget = v.get("budget_capacity", 50)

    if dependency >= 70:
        # The contractor holds the leverage; the squeeze mostly fails.
        return _DecisionDraft(
            DecisionType.MODIFIED, 0.5,
            {"contractor_dependency": +6, "water_security": +3, "budget_capacity": -3},
            deviation="Conceded much of the contractor's terms to keep crews on site.",
            public_explanation="Emergency repair scope has been expanded to protect supply.",
            private_motive="With no alternative, the town could not credibly hold the line.",
            resulting_risk="Structural dependency deepens; premium terms become precedent.",
        )
    if budget <= 20:
        # No fiscal room to apply real pressure.
        return _DecisionDraft(
            DecisionType.PARTIALLY_FOLLOWED, 0.55, {},
            deviation="Pressed the contractor lightly; budget left no room for a real squeeze.",
            public_explanation="Repair timelines are being renegotiated within current authority.",
            private_motive="Could not fund a credible alternative or premium concession.",
            resulting_risk="Light pressure yields little leverage over a sole-source firm.",
        )
    return _DecisionDraft(
        DecisionType.FOLLOWED, 0.85, {},
        deviation="None \u2014 the private pressure strategy held together.",
        public_explanation="Repair sequencing has been accelerated without public escalation.",
        private_motive="The threat of alternatives was just credible enough.",
        resulting_risk="Dependency still grows even when the immediate squeeze works.",
    )


def _decide_mutual_aid(campaign: Campaign) -> _DecisionDraft:
    v = campaign.world_state.variables
    budget = v.get("budget_capacity", 50)
    hospital = v.get("hospital_stability", 50)

    if budget <= 25:
        # Can only afford a partial aid activation.
        return _DecisionDraft(
            DecisionType.PARTIALLY_FOLLOWED, 0.6,
            {"budget_capacity": -3, "hospital_stability": +3, "water_security": +3},
            deviation="Activated only a partial mutual-aid package given the fiscal limit.",
            public_explanation="Regional partners are supporting hospital and supply resilience.",
            private_motive="Budget constrained the activation to what could be afforded.",
            resulting_risk="Partial aid may not cover the next pressure drop.",
        )
    if hospital <= 25:
        return _DecisionDraft(
            DecisionType.FOLLOWED, 0.9, {},
            deviation="None \u2014 the hospital threshold made full activation defensible.",
            public_explanation="The regional mutual-aid compact has been fully activated.",
            private_motive="Hospital vulnerability made full aid politically unassailable.",
            resulting_risk="Aid visibility nudges state awareness of the failure.",
        )
    return _DecisionDraft(
        DecisionType.FOLLOWED, 0.8, {},
        deviation="None \u2014 mutual aid was convened on the planned scope.",
        public_explanation="Regional coordination is underway for hospital and supply support.",
        private_motive="Cooperative posture protected trust at manageable cost.",
        resulting_risk="Spends budget and some political capital for a cooperative gain.",
        )


_ADVICE_TAG_DISPATCH = {
    "disclosure": _decide_disclosure,
    "delay": _decide_delay,
    "state_support": _decide_state_support,
    "contractor": _decide_contractor,
    "mutual_aid": _decide_mutual_aid,
}


def decide(campaign: Campaign, advice: AdviceOption) -> NpcDecision:
    """Resolve how the NPC client uses the player's chosen advice.

    Returns a fully deterministic ``NpcDecision``. ``adherence`` scales the
    advice's base effects; ``modifications`` are extra deltas the NPC imposed.
    The ``deviation`` / ``public_explanation`` / ``private_motive`` /
    ``resulting_risk`` fields are descriptive overlays so the player can read
    the mediation; they do not change state.
    """
    draft: _DecisionDraft
    handler = None
    for tag in advice.tags:
        if tag in _ADVICE_TAG_DISPATCH:
            handler = _ADVICE_TAG_DISPATCH[tag]
            break

    if handler is not None:
        draft = handler(campaign)
    else:
        draft = _DecisionDraft(
            DecisionType.PARTIALLY_FOLLOWED, 0.7, {},
            deviation="Adopted a general, partial version of the advice.",
            public_explanation="The Manager acted on the recommendation in part.",
            private_motive="No specific guidance applied cleanly; hedged the decision.",
            resulting_risk="Unfocused action leaves the underlying failure unaddressed.",
        )

    v = campaign.world_state.variables
    media = v.get("media_pressure", 0)
    trust = v.get("public_trust", 50)

    rationale = _build_rationale(advice, draft.decision_type, media, trust, campaign.turn_number)
    return NpcDecision(
        advice_id=advice.id,
        decision_type=draft.decision_type,
        decider=DECIDER,
        rationale=rationale,
        adherence=draft.adherence,
        modifications=draft.modifications,
        deviation=draft.deviation,
        public_explanation=draft.public_explanation,
        private_motive=draft.private_motive,
        resulting_risk=draft.resulting_risk,
    )


def _build_rationale(
    advice: AdviceOption,
    decision_type: str,
    media: int,
    trust: int,
    turn: int,
) -> str:
    label = advice.label
    if decision_type == DecisionType.FOLLOWED:
        return (
            f"The Town Manager adopted {label} in full. "
            f"Media pressure {media}, public trust {trust}, turn {turn}."
        )
    if decision_type == DecisionType.PARTIALLY_FOLLOWED:
        return (
            f"The Town Manager adopted the spirit of {label} but trimmed the "
            f"public-facing scope. Media pressure {media}, public trust {trust}."
        )
    if decision_type == DecisionType.MODIFIED:
        return (
            f"The Town Manager reworked {label} to fit political constraints "
            f"before acting. Media pressure {media}, turn {turn}."
        )
    if decision_type == DecisionType.DELAYED:
        return (
            f"The Town Manager postponed {label}, buying time but letting "
            f"rumors accumulate. Public trust {trust}, turn {turn}."
        )
    return f"The Town Manager declined {label}."


# ---------------------------------------------------------------------------
# Posture updates -- shift faction posture labels from resulting state, so the
# dashboard reads coherently without any state being silently changed.
# ---------------------------------------------------------------------------

def update_faction_postures(campaign: Campaign) -> None:
    v = campaign.world_state.variables
    trust = v.get("public_trust", 50)
    media = v.get("media_pressure", 0)
    order = v.get("public_order", 50)

    for faction in campaign.world_state.factions:
        if faction.id == "town_managers_office":
            faction.posture = "decisive" if order >= 50 else "defensive"
        elif faction.id == "council_majority":
            faction.posture = "confident" if trust >= 50 else "nervous"
        elif faction.id == "council_opposition":
            faction.posture = "circumspect" if trust >= 55 else "emboldened"
        elif faction.id == "water_authority":
            faction.posture = "stretched" if v.get("water_security", 50) < 50 else "stable"
        elif faction.id == "hospital":
            faction.posture = (
                "critical" if v.get("hospital_stability", 50) <= 30 else "watchful"
            )
        elif faction.id == "parent_resident_coalition":
            faction.posture = "reassured" if trust >= 50 else "alarmed"
        elif faction.id == "business_alliance":
            faction.posture = "steady" if order >= 50 else "restive"
        elif faction.id == "state_liaison":
            faction.posture = (
                "intervening"
                if v.get("state_oversight_risk", 0) >= 60
                else "advisory"
            )
        elif faction.id == "utility_contractor":
            faction.posture = (
                "entrenched"
                if v.get("contractor_dependency", 0) >= 60
                else "cooperative"
            )
        elif faction.id == "media_rumor_network":
            faction.posture = "amplifying" if media >= 55 else "circulating"


def update_crisis_severity(campaign: Campaign) -> None:
    crisis = campaign.world_state.active_crisis
    if crisis is None:
        return
    water = campaign.world_state.variables.get("water_security", 50)
    crisis.severity = clamp(100 - water)


# ---------------------------------------------------------------------------
# Aftermath text generation.
# ---------------------------------------------------------------------------

_DECISION_PHRASING = {
    DecisionType.FOLLOWED: "acted on your advice in full",
    DecisionType.PARTIALLY_FOLLOWED: "adopted part of your advice",
    DecisionType.MODIFIED: "reworked your advice to fit local politics",
    DecisionType.DELAYED: "delayed your advice to buy time",
    DecisionType.REJECTED: "set your advice aside",
}


def build_aftermath_summary(
    advice: AdviceOption,
    decision: NpcDecision,
    diffs: List,
    status_after: str,
    failure_reason: Optional[str],
) -> str:
    phrasing = _DECISION_PHRASING.get(decision.decision_type, "responded to your advice")
    leading = f"The {decision.decider} {phrasing} ({decision.decision_type})."

    top = sorted(
        [d for d in diffs if d.source_type in (SourceType.ADVICE, SourceType.NPC_MODIFICATION)],
        key=lambda d: abs(d.delta),
        reverse=True,
    )[:3]
    if top:
        moves = "; ".join(f"{d.variable} {d.old_value}\u2192{d.new_value}" for d in top)
        moves = f" Notable shifts: {moves}."
    else:
        moves = ""

    if status_after == "FAILED":
        return f"{leading}{moves} The engagement collapsed: {failure_reason}"
    return f"{leading}{moves}"
