"""Deterministic workstation degradation, derived from power_stability.

The consulting desk itself runs on the same grid the crisis is stressing.
This module reads the campaign record and answers one question: how degraded
is the workstation right now, and what capability does that cost? It is
computed on demand and NEVER persisted (same contract as ``engine/endings``):
the authoritative record stays the applied diffs; degradation is a pure
function of them.

Bands and gates (each band keeps the gates of the bands above it):

    NOMINAL   power >= 55   everything works
    STRAINED  35..54        live feeds lost -- dashboards and the evidence
                            board show the last verified snapshot with its
                            ``last_live_turn`` stamp
    DEGRADED  15..34        + the memo drafter is offline diegetically
                            (deterministic system drafts only)
    CRITICAL  <= 14         + auxiliary power supports ONE subsystem per turn
                            (the player must allocate it; wave-2b batch B4)

No randomness, no model calls, no mutation: same campaign record, same
degradation, bit for bit.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.models import Campaign


class DegradationBand:
    NOMINAL = "NOMINAL"
    STRAINED = "STRAINED"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


# Band floors, in descending order. Legible constants, like FAILURE_THRESHOLDS.
NOMINAL_FLOOR = 55      # live feeds require at least this much grid margin
DEGRADED_CEILING = 34   # at or below: the model stack drops off the desk
CRITICAL_CEILING = 14   # at or below: one subsystem on auxiliary power


_BAND_REASONS = {
    DegradationBand.NOMINAL: (
        "Grid margin nominal — live feeds, model access, and communications "
        "all on utility power."
    ),
    DegradationBand.STRAINED: (
        "Grid margin strained — live feeds lost; the desk is working from "
        "the last verified snapshot."
    ),
    DegradationBand.DEGRADED: (
        "Grid margin degraded — live feeds lost and model access offline; "
        "drafting falls back to deterministic system templates."
    ),
    DegradationBand.CRITICAL: (
        "Grid margin critical — auxiliary power supports one subsystem per "
        "turn; everything else is dark."
    ),
}


@dataclass
class DegradationStatus:
    """The workstation's current condition. Derived, never persisted."""
    band: str
    power: int
    live_feeds: bool                    # False from STRAINED down
    ai_operational: bool                # False from DEGRADED down
    requires_power_allocation: bool     # True only at CRITICAL
    last_live_turn: int                 # latest resolved turn with live feeds
    reason: str                         # one diegetic sentence for the UI


def band_for_power(power: int) -> str:
    """The degradation band for a power_stability value."""
    if power >= NOMINAL_FLOOR:
        return DegradationBand.NOMINAL
    if power <= CRITICAL_CEILING:
        return DegradationBand.CRITICAL
    if power <= DEGRADED_CEILING:
        return DegradationBand.DEGRADED
    return DegradationBand.STRAINED


def _end_of_turn_power(campaign: Campaign) -> list:
    """(turn_number, end-of-turn power) per resolved turn, from the record.

    Every power move is on the record as an AppliedDiff with old/new values;
    turns where power did not move inherit the previous value. The value
    before any resolved turn is the first recorded diff's old_value, or the
    live value when power has never moved at all.
    """
    value = None
    for result in campaign.turn_history:
        for diff in result.diffs:
            if diff.variable == "power_stability":
                value = diff.old_value
                break
        if value is not None:
            break
    if value is None:
        value = campaign.world_state.variables.get("power_stability", 50)

    trace = []
    for result in campaign.turn_history:
        for diff in result.diffs:
            if diff.variable == "power_stability":
                value = diff.new_value
        trace.append((result.turn_number, value))
    return trace


def assess_degradation(campaign: Campaign) -> DegradationStatus:
    """Assess the workstation from the campaign record. Pure and deterministic."""
    power = campaign.world_state.variables.get("power_stability", 50)
    band = band_for_power(power)
    live = band == DegradationBand.NOMINAL

    if live:
        # Feeds are live: the freshest picture is the current turn's.
        last_live_turn = campaign.turn_number
    else:
        # The latest resolved turn that CLOSED with live feeds; 0 means the
        # last live picture is the engagement intake itself.
        last_live_turn = 0
        for turn_number, value in _end_of_turn_power(campaign):
            if value >= NOMINAL_FLOOR:
                last_live_turn = turn_number

    return DegradationStatus(
        band=band,
        power=power,
        live_feeds=live,
        ai_operational=band in (DegradationBand.NOMINAL, DegradationBand.STRAINED),
        requires_power_allocation=band == DegradationBand.CRITICAL,
        last_live_turn=last_live_turn,
        reason=_BAND_REASONS[band],
    )
