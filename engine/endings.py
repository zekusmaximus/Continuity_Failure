"""Multi-axis outcome assessment: what kind of institution survived.

Completion was previously binary -- reach turn 10 without tripping a failure
threshold and the campaign "succeeded", even at contractor_dependency 100.
This module grades a campaign on seven axes, each a documented arithmetic
blend of final state, the debt ledger, and the thread record, and selects a
deterministic verdict that preserves ambiguity: stabilizing the water while
hollowing out legitimacy or independence is not a win, just a different
ending.

Assessments are computed on demand from the campaign -- never persisted -- so
they stay consistent under recompute and add no storage migration. Everything
here is thresholds and arithmetic; no randomness, no model calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from engine.models import Campaign, CampaignStatus, ThreadStatus
from engine.state import clamp


class OutcomeBand:
    STRONG = "strong"
    HOLDING = "holding"
    COMPROMISED = "compromised"
    FAILED = "failed"


def _band(score: int) -> str:
    if score >= 70:
        return OutcomeBand.STRONG
    if score >= 50:
        return OutcomeBand.HOLDING
    if score >= 30:
        return OutcomeBand.COMPROMISED
    return OutcomeBand.FAILED


@dataclass
class OutcomeFactor:
    """One legible input into an axis score (mirrors AdherenceFactor)."""
    label: str
    detail: str
    direction: str          # "increase" / "decrease" / "neutral"


@dataclass
class OutcomeAxis:
    id: str
    label: str
    score: int              # 0-100
    band: str               # OutcomeBand vocabulary
    factors: List[OutcomeFactor] = field(default_factory=list)


@dataclass
class OutcomeAssessment:
    axes: List[OutcomeAxis]
    verdict_title: str
    verdict_body: List[str]
    campaign_status: str    # COMPLETED / FAILED -- terminal invariant unchanged


def _ledger_count(campaign: Campaign, kind: str) -> int:
    return sum(1 for e in campaign.debt_ledger if e.kind == kind)


def _unresolved_threads(campaign: Campaign) -> int:
    return sum(
        1 for t in campaign.open_threads if t.status != ThreadStatus.RESOLVED
    )


def _axis(axis_id, label, score, factors):
    score = clamp(score)
    return OutcomeAxis(id=axis_id, label=label, score=score,
                       band=_band(score), factors=factors)


def build_outcome_assessment(campaign: Campaign) -> OutcomeAssessment:
    """Grade the campaign. Pure function of campaign state; deterministic."""
    v = campaign.world_state.variables
    g = v.get

    axes: List[OutcomeAxis] = []

    # --- Stabilization: did the essential systems hold? ---
    stabilization = round(
        (g("water_security", 50) + g("hospital_stability", 50)
         + g("public_order", 50)) / 3
    )
    axes.append(_axis(
        "stabilization", "Stabilization", stabilization,
        [
            OutcomeFactor("Water security", f"Final {g('water_security', 50)}/100.",
                          "increase" if g("water_security", 50) >= 50 else "decrease"),
            OutcomeFactor("Hospital stability", f"Final {g('hospital_stability', 50)}/100.",
                          "increase" if g("hospital_stability", 50) >= 50 else "decrease"),
            OutcomeFactor("Public order", f"Final {g('public_order', 50)}/100.",
                          "increase" if g("public_order", 50) >= 50 else "decrease"),
        ],
    ))

    # --- Legitimacy: does the public still consent to be governed? ---
    delayed = _ledger_count(campaign, "delayed_notice")
    leaks = _ledger_count(campaign, "leak")
    legitimacy = round(
        (g("public_trust", 50) + g("information_integrity", 50)) / 2
    ) - 5 * delayed - 4 * leaks
    legitimacy_factors = [
        OutcomeFactor("Public trust", f"Final {g('public_trust', 50)}/100.",
                      "increase" if g("public_trust", 50) >= 50 else "decrease"),
        OutcomeFactor("Information integrity",
                      f"Final {g('information_integrity', 50)}/100.",
                      "increase" if g("information_integrity", 50) >= 50 else "decrease"),
    ]
    if delayed:
        legitimacy_factors.append(OutcomeFactor(
            "Delayed notice", f"{delayed} delayed-notice precedent(s) on the ledger (−{5 * delayed}).",
            "decrease"))
    if leaks:
        legitimacy_factors.append(OutcomeFactor(
            "Leaks", f"{leaks} private record(s) leaked (−{4 * leaks}).", "decrease"))
    axes.append(_axis("legitimacy", "Legitimacy", legitimacy, legitimacy_factors))

    # --- Legal record: what will discovery find? ---
    sole_source = _ledger_count(campaign, "sole_source_procurement")
    legal = 100 - g("legal_exposure", 50) - 5 * delayed - 3 * sole_source
    legal_factors = [
        OutcomeFactor("Legal exposure", f"Final {g('legal_exposure', 50)}/100.",
                      "decrease" if g("legal_exposure", 50) >= 50 else "increase"),
    ]
    if delayed:
        legal_factors.append(OutcomeFactor(
            "Disclosure timing", f"{delayed} delayed-notice precedent(s) (−{5 * delayed}).",
            "decrease"))
    if sole_source:
        legal_factors.append(OutcomeFactor(
            "Procurement record", f"{sole_source} sole-source precedent(s) (−{3 * sole_source}).",
            "decrease"))
    axes.append(_axis("legal_record", "Legal Record", legal, legal_factors))

    # --- Independence: who does the town now answer to? ---
    independence = 100 - round(
        (g("contractor_dependency", 50) + g("state_oversight_risk", 50)) / 2
    )
    axes.append(_axis(
        "independence", "Independence", independence,
        [
            OutcomeFactor("Contractor dependency",
                          f"Final {g('contractor_dependency', 50)}/100.",
                          "decrease" if g("contractor_dependency", 50) >= 50 else "increase"),
            OutcomeFactor("State oversight risk",
                          f"Final {g('state_oversight_risk', 50)}/100.",
                          "decrease" if g("state_oversight_risk", 50) >= 50 else "increase"),
        ],
    ))

    # --- Harm avoided: who absorbed the crisis? ---
    unresolved = _unresolved_threads(campaign)
    harm = round(
        (g("hospital_stability", 50) + (100 - g("school_disruption", 50))) / 2
    ) - 3 * unresolved
    harm_factors = [
        OutcomeFactor("Clinical continuity", f"Hospital stability {g('hospital_stability', 50)}/100.",
                      "increase" if g("hospital_stability", 50) >= 50 else "decrease"),
        OutcomeFactor("School disruption", f"Final {g('school_disruption', 50)}/100.",
                      "decrease" if g("school_disruption", 50) >= 50 else "increase"),
    ]
    if unresolved:
        harm_factors.append(OutcomeFactor(
            "Open threads", f"{unresolved} unresolved thread(s) left running (−{3 * unresolved}).",
            "decrease"))
    axes.append(_axis("harm_avoided", "Harm Avoided", harm, harm_factors))

    # --- Consultant standing: reputation and neutrality of the desk. ---
    red_lines = _ledger_count(campaign, "red_line_crossed")
    standing = round(
        (g("player_reputation", 50) + g("player_perceived_neutrality", 50)) / 2
    ) - 5 * red_lines
    standing_factors = [
        OutcomeFactor("Reputation", f"Final {g('player_reputation', 50)}/100.",
                      "increase" if g("player_reputation", 50) >= 50 else "decrease"),
        OutcomeFactor("Perceived neutrality",
                      f"Final {g('player_perceived_neutrality', 50)}/100.",
                      "increase" if g("player_perceived_neutrality", 50) >= 50 else "decrease"),
    ]
    if red_lines:
        standing_factors.append(OutcomeFactor(
            "Red lines", f"{red_lines} red-line proposal(s) on the record (−{5 * red_lines}).",
            "decrease"))
    axes.append(_axis("consultant_standing", "Consultant Standing", standing,
                      standing_factors))

    # --- Shadow authority: LOWER is better -- how much unelected power the
    # consultant accumulated. Scored so a high score means power stayed where
    # it belongs.
    shadow = g("player_shadow_authority", 0)
    axes.append(_axis(
        "shadow_authority", "Institutional Primacy", 100 - shadow,
        [OutcomeFactor(
            "Shadow authority",
            f"Consultant shadow authority ended at {shadow}/100; decisions "
            + ("increasingly routed through the desk rather than the institutions."
               if shadow >= 50 else "stayed with the institutions."),
            "decrease" if shadow >= 50 else "increase",
        )],
    ))

    title, body = _verdict(campaign, {a.id: a for a in axes})
    return OutcomeAssessment(
        axes=axes,
        verdict_title=title,
        verdict_body=body,
        campaign_status=campaign.status,
    )


def _verdict(campaign: Campaign, axes: Dict[str, OutcomeAxis]):
    """Deterministic verdict from the band combination. Ambiguity preserved."""
    body: List[str] = []

    if campaign.status == CampaignStatus.FAILED:
        title = "The engagement collapsed"
        body.append(campaign.failure_reason or "A failure threshold was crossed.")
        worst = min(axes.values(), key=lambda a: (a.score, a.id))
        body.append(
            f"The record shows where it broke: {worst.label.lower()} "
            f"ended at {worst.score}/100."
        )
        return title, body

    stab = axes["stabilization"]
    indep = axes["independence"]
    legit = axes["legitimacy"]
    legal = axes["legal_record"]

    low = (OutcomeBand.COMPROMISED, OutcomeBand.FAILED)
    if stab.band in low:
        title = "The clock ran out before the water was safe"
        body.append(
            f"Ten turns were survived, but stabilization ended at "
            f"{stab.score}/100 — the essential systems are still failing."
        )
    elif indep.band in low:
        title = "Stabilized — on someone else's terms"
        body.append(
            f"The water kept flowing, but independence ended at "
            f"{indep.score}/100: the town now answers to whoever holds "
            f"its dependencies."
        )
    elif legit.band in low:
        title = "The water flowed; consent drained away"
        body.append(
            f"Operationally a success, civically a loss: legitimacy ended at "
            f"{legit.score}/100."
        )
    elif legal.band in low:
        title = "Stabilized, and discoverable"
        body.append(
            f"The systems held, but the legal record ({legal.score}/100) will "
            f"not survive the first subpoena intact."
        )
    else:
        title = "A defensible stabilization"
        body.append(
            "The systems held, the record is defensible, and the town still "
            "answers to itself. Few engagements end this cleanly."
        )

    # Always name the strongest and weakest axes -- the ambiguity is the point.
    ordered = sorted(axes.values(), key=lambda a: (a.score, a.id))
    weakest, strongest = ordered[0], ordered[-1]
    if weakest.id != strongest.id:
        body.append(
            f"Strongest axis: {strongest.label.lower()} ({strongest.score}/100). "
            f"Weakest: {weakest.label.lower()} ({weakest.score}/100)."
        )
    if campaign.debt_ledger:
        body.append(
            f"The institutional debt ledger carries {len(campaign.debt_ledger)} "
            f"precedent(s) the town cannot take back."
        )
    return title, body
