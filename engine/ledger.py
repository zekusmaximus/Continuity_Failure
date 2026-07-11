"""The institutional debt ledger: emergency precedents and their costs.

Every expedient emergency decision leaves a precedent the institution cannot
take back: sole-source procurement terms, informal hospital priority, delayed
public notice. This module records those precedents deterministically and
prices their repetition:

* The first precedent of a kind is recorded free -- it is simply now on the
  ledger (and mirrored into the turn's legal fallout).
* Repeating a kind already on the ledger carries a deterministic cost
  (``REPEAT_COSTS``), applied by the turn resolver as its own diff batch with
  a legible reason.
* A standing precedent also lowers the client's resistance to matching advice
  ("the town has done this before"), expressed as an off-brief discomfort
  relief inside the decision rules.

No randomness, no model calls: same record, same advice, same costs.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from engine.models import (
    AdviceOption,
    Campaign,
    DecisionType,
    NpcDecision,
    PrecedentEntry,
)


class PrecedentKind:
    SOLE_SOURCE_PROCUREMENT = "sole_source_procurement"
    DELAYED_NOTICE = "delayed_notice"
    INFORMAL_HOSPITAL_PRIORITY = "informal_hospital_priority"
    COMPENSATION_FRAMEWORK = "compensation_framework"
    RED_LINE_CROSSED = "red_line_crossed"


PRECEDENT_LABELS: Dict[str, str] = {
    PrecedentKind.SOLE_SOURCE_PROCUREMENT: "Sole-source procurement terms",
    PrecedentKind.DELAYED_NOTICE: "Delayed public notice",
    PrecedentKind.INFORMAL_HOSPITAL_PRIORITY: "Informal hospital priority",
    PrecedentKind.COMPENSATION_FRAMEWORK: "Emergency compensation framework",
    PrecedentKind.RED_LINE_CROSSED: "Advice across a client red line",
}

# The advice decision-tag whose precedent history bears on a proposal of the
# same kind. Used both to price repetition and to lower client resistance.
_KIND_FOR_TAG: Dict[str, str] = {
    "contractor": PrecedentKind.SOLE_SOURCE_PROCUREMENT,
    "delay": PrecedentKind.DELAYED_NOTICE,
    "hospital_priority": PrecedentKind.INFORMAL_HOSPITAL_PRIORITY,
    "business_compensation": PrecedentKind.COMPENSATION_FRAMEWORK,
}

# Deterministic cost of repeating a precedent already on the ledger. Small by
# design: the point is a visible, compounding institutional debt, not a
# punishment spike.
REPEAT_COSTS: Dict[str, Dict[str, int]] = {
    PrecedentKind.SOLE_SOURCE_PROCUREMENT: {
        "contractor_dependency": +2, "legal_exposure": +1,
    },
    PrecedentKind.DELAYED_NOTICE: {
        "legal_exposure": +2, "information_integrity": -1,
    },
    PrecedentKind.INFORMAL_HOSPITAL_PRIORITY: {
        "legal_exposure": +1, "public_trust": -1,
    },
    PrecedentKind.COMPENSATION_FRAMEWORK: {
        "budget_capacity": -1, "legal_exposure": +1,
    },
    PrecedentKind.RED_LINE_CROSSED: {
        "state_oversight_risk": +2,
    },
}

# How much a standing precedent of the matching kind relieves a caller's
# off-brief discomfort: they've signed off on this kind of measure before.
PRECEDENT_FAMILIARITY_RELIEF = 8

# What each recorded precedent notes on the record.
_PRECEDENT_DETAILS: Dict[str, str] = {
    PrecedentKind.SOLE_SOURCE_PROCUREMENT: (
        "Emergency terms were conceded to the sole certified contractor; the "
        "concession is now citable in every future negotiation."
    ),
    PrecedentKind.DELAYED_NOTICE: (
        "Public notice was deliberately held past the point of knowledge; the "
        "timing decision is now part of the record."
    ),
    PrecedentKind.INFORMAL_HOSPITAL_PRIORITY: (
        "Clinical priority was granted informally, off the documented "
        "allocation record."
    ),
    PrecedentKind.COMPENSATION_FRAMEWORK: (
        "An emergency compensation framework was funded; other claimants can "
        "now cite it."
    ),
    PrecedentKind.RED_LINE_CROSSED: (
        "The consultant proposed advice across a stated client red line; the "
        "refusal is on the record."
    ),
}


def kind_for_advice(advice: AdviceOption) -> Optional[str]:
    """The precedent kind this advice's tags bear on, if any."""
    for tag in advice.tags:
        if tag in _KIND_FOR_TAG:
            return _KIND_FOR_TAG[tag]
    return None


def kinds_on_ledger(campaign: Campaign) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for entry in campaign.debt_ledger:
        counts[entry.kind] = counts.get(entry.kind, 0) + 1
    return counts


def _kind_recorded_by(advice: AdviceOption, decision: NpcDecision) -> Optional[str]:
    """The precedent kind this turn's resolved decision sets, if any.

    Legible threshold rules over (advice tag, decision type):
    * A red-line rejection is always recorded against the consultant.
    * Conceding contractor terms (MODIFIED) sets sole-source precedent.
    * Acting on delay advice -- or having any advice DELAYED -- sets a
      delayed-notice precedent.
    * The informal (PARTIALLY_FOLLOWED) hospital-priority branch sets an
      informal-priority precedent; the documented branch does not.
    * Funding or trimming the compensation framework sets its precedent.
    """
    if decision.cost_reason.startswith("Red line"):
        return PrecedentKind.RED_LINE_CROSSED
    tags = set(advice.tags)
    if "contractor" in tags and decision.decision_type == DecisionType.MODIFIED:
        return PrecedentKind.SOLE_SOURCE_PROCUREMENT
    if "delay" in tags and decision.decision_type in (
        DecisionType.FOLLOWED, DecisionType.PARTIALLY_FOLLOWED, DecisionType.DELAYED,
    ):
        return PrecedentKind.DELAYED_NOTICE
    if decision.decision_type == DecisionType.DELAYED:
        return PrecedentKind.DELAYED_NOTICE
    if "hospital_priority" in tags and decision.decision_type == DecisionType.PARTIALLY_FOLLOWED:
        return PrecedentKind.INFORMAL_HOSPITAL_PRIORITY
    if "business_compensation" in tags and decision.decision_type in (
        DecisionType.FOLLOWED, DecisionType.MODIFIED,
    ):
        return PrecedentKind.COMPENSATION_FRAMEWORK
    return None


def evaluate_repeat(
    campaign: Campaign, advice: AdviceOption, decision: NpcDecision
) -> Tuple[Dict[str, int], str]:
    """Price this decision's repetition of an existing precedent, if any.

    Returns ``(adjustments, reason)`` -- empty when the decision sets no
    precedent or sets one of a kind not yet on the ledger (the first instance
    is recorded free; only repetition compounds).
    """
    kind = _kind_recorded_by(advice, decision)
    if kind is None or kinds_on_ledger(campaign).get(kind, 0) == 0:
        return {}, ""
    reason = (
        f"Precedent repeated — {PRECEDENT_LABELS[kind]} was already on the "
        f"institutional ledger"
    )
    return dict(REPEAT_COSTS.get(kind, {})), reason


def record_precedents(
    campaign: Campaign,
    advice: AdviceOption,
    decision: NpcDecision,
    resolving_turn: int,
    canon_id: str,
) -> List[PrecedentEntry]:
    """Record any precedent this resolved turn sets. Mutates the ledger."""
    kind = _kind_recorded_by(advice, decision)
    if kind is None:
        return []
    occurrence = kinds_on_ledger(campaign).get(kind, 0) + 1
    entry = PrecedentEntry(
        id=f"precedent_{kind}_t{resolving_turn}",
        kind=kind,
        label=PRECEDENT_LABELS[kind],
        turn_recorded=resolving_turn,
        detail=_PRECEDENT_DETAILS[kind]
        + (f" (instance {occurrence} on the ledger)" if occurrence > 1 else ""),
        canon_id=canon_id,
    )
    campaign.debt_ledger.append(entry)
    return [entry]
