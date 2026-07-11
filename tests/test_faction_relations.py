"""Living factions: deterministic trust/influence shifts and the leak rule.

Faction fields move on the record: every change is a FactionShift with a
legible reason, trust feeds the decision rules, and a faction whose working
trust has collapsed under high pressure leaks a private record -- at most one
leak per turn, one per faction per campaign, never rewriting prior canon.
"""

from __future__ import annotations

from dataclasses import asdict

from engine import seed_data, turn
from engine.factions import (
    LEAK_PRESSURE_AT_LEAST,
    LEAK_TRUST_AT_MOST,
    TRUST_LOSS_RED_LINE,
)
from engine.models import Campaign, PublicStatus, SourceType


def _fresh_campaign() -> Campaign:
    return seed_data.create_northbridge_campaign(name="test")


def _caller_faction(campaign: Campaign):
    call = campaign.current_call()
    return next(
        f for f in campaign.world_state.factions if f.id == call.caller_faction_id
    )


# ---------------------------------------------------------------------------
# Trust and influence shifts
# ---------------------------------------------------------------------------

def test_followed_advice_that_serves_the_caller_raises_trust():
    campaign = _fresh_campaign()
    caller = _caller_faction(campaign)
    before = caller.trust_in_player
    # Turn 1 caller is the Town Manager's Office; full disclosure is on-brief
    # and (per the decision rules) resolves in its favor.
    result = turn.advance_turn(campaign, "controlled_disclosure")
    trust_shifts = [
        s for s in result.faction_shifts
        if s.faction_id == caller.id and s.field == "trust_in_player"
    ]
    if trust_shifts:  # only when priorities net-improved
        assert trust_shifts[0].new_value > before
        assert trust_shifts[0].reason
        assert caller.trust_in_player == trust_shifts[0].new_value


def test_red_line_crossing_costs_trust_and_raises_pressure():
    campaign = _fresh_campaign()
    campaign.turn_number = 2  # schools call red-lines "delay"
    campaign.world_state.turn_number = 2
    caller = _caller_faction(campaign)
    trust_before = caller.trust_in_player
    pressure_before = caller.current_pressure

    result = turn.advance_turn(campaign, "delay_disclosure")

    assert caller.trust_in_player == max(0, trust_before - TRUST_LOSS_RED_LINE)
    assert caller.current_pressure >= pressure_before
    fields = {(s.faction_id, s.field) for s in result.faction_shifts}
    assert (caller.id, "trust_in_player") in fields
    assert (caller.id, "current_pressure") in fields
    for shift in result.faction_shifts:
        assert shift.reason, "every faction shift must carry a reason"


def test_influence_follows_sustained_pressure():
    campaign = _fresh_campaign()
    high = campaign.world_state.factions[0]
    low = campaign.world_state.factions[1]
    high.current_pressure = 80
    low.current_pressure = 20
    high_before, low_before = high.influence, low.influence

    result = turn.advance_turn(campaign, "controlled_disclosure")

    assert high.influence == min(100, high_before + 2)
    assert low.influence == max(0, low_before - 2)
    shifted = {(s.faction_id, s.field) for s in result.faction_shifts}
    assert (high.id, "influence") in shifted
    assert (low.id, "influence") in shifted


# ---------------------------------------------------------------------------
# Trust feeds the decision rules
# ---------------------------------------------------------------------------

def test_collapsed_trust_makes_off_brief_advice_land_worse():
    def resolve(trust: int):
        c = _fresh_campaign()
        c.turn_number = 4  # contractor call; mutual_aid is on-brief, delay off
        c.world_state.turn_number = 4
        caller = _caller_faction(c)
        caller.trust_in_player = trust
        from engine import rules
        return rules.decide(c, turn.find_advice(c, "delay_disclosure"))

    trusted = resolve(90)
    distrusted = resolve(10)
    assert distrusted.adherence <= trusted.adherence
    labels = {
        (f.label, f.direction)
        for f in distrusted.explanation.adherence_factors
    }
    assert ("Working trust", "decrease") in labels


# ---------------------------------------------------------------------------
# The leak rule
# ---------------------------------------------------------------------------

def _prime_leaker(campaign: Campaign):
    leaker = campaign.world_state.factions[2]
    leaker.trust_in_player = LEAK_TRUST_AT_MOST
    leaker.current_pressure = LEAK_PRESSURE_AT_LEAST
    return leaker


def test_collapsed_trust_high_pressure_faction_leaks_once():
    campaign = _fresh_campaign()
    leaker = _prime_leaker(campaign)
    private_before = [
        d for d in campaign.documents
        if d.public_status == PublicStatus.PRIVATE and d.turn_number <= 1
    ]
    assert private_before, "scenario must have a private turn-1 document"

    result = turn.advance_turn(campaign, "controlled_disclosure")

    leak_diffs = [d for d in result.diffs if d.source_type == SourceType.LEAK]
    assert {d.variable for d in leak_diffs} == {
        "media_pressure", "public_trust", "information_integrity",
    }
    assert all(leaker.name in d.reason for d in leak_diffs)

    leaked_doc = private_before[0]
    assert leaked_doc.public_status == PublicStatus.LEAKED

    leak_canon = [c for c in campaign.canon if c.category == "leak"]
    assert len(leak_canon) == 1
    assert leak_canon[0].source == leaker.name
    assert leak_canon[0].public_status == PublicStatus.LEAKED

    ledger_leaks = [e for e in campaign.debt_ledger if e.kind == "leak"]
    assert len(ledger_leaks) == 1
    assert any(
        leaker.name in line for line in result.consequence_stack.media_framing
    )

    # The same faction never leaks twice, even if conditions persist.
    if not campaign.is_terminal():
        second = turn.advance_turn(campaign, "mutual_aid")
        assert [d for d in second.diffs if d.source_type == SourceType.LEAK] == []
        assert len([e for e in campaign.debt_ledger if e.kind == "leak"]) == 1


def test_at_most_one_faction_leaks_per_turn():
    campaign = _fresh_campaign()
    for faction in campaign.world_state.factions[:3]:
        faction.trust_in_player = 10
        faction.current_pressure = 90

    result = turn.advance_turn(campaign, "controlled_disclosure")

    assert len([c for c in campaign.canon if c.category == "leak"]) == 1
    # Deterministic pick: least trust, then id order.
    ledger_leaks = [e for e in campaign.debt_ledger if e.kind == "leak"]
    expected = sorted(
        campaign.world_state.factions[:3], key=lambda f: (f.trust_in_player, f.id)
    )[0]
    assert expected.id in ledger_leaks[0].id


def test_leak_never_mutates_prior_canon():
    campaign = _fresh_campaign()
    turn.advance_turn(campaign, "mutual_aid")
    canon_before = [asdict(c) for c in campaign.canon]

    _prime_leaker(campaign)
    turn.advance_turn(campaign, "mutual_aid")

    # Every pre-existing canon entry is byte-identical; the leak added new ones.
    for old, current in zip(canon_before, campaign.canon):
        assert asdict(current) == old


# ---------------------------------------------------------------------------
# Determinism including faction state
# ---------------------------------------------------------------------------

def test_faction_state_is_bit_for_bit_repeatable():
    def play():
        c = _fresh_campaign()
        _prime_leaker(c)
        seq = ["controlled_disclosure", "mutual_aid", "contractor_pressure",
               "mutual_aid", "state_support"]
        for advice_id in seq:
            if c.is_terminal():
                break
            turn.advance_turn(c, advice_id)
        return c

    a = play()
    b = play()
    assert asdict(a.world_state) == asdict(b.world_state)
    assert [asdict(s) for r in a.turn_history for s in r.faction_shifts] == [
        asdict(s) for r in b.turn_history for s in r.faction_shifts
    ]
    assert [asdict(e) for e in a.debt_ledger] == [asdict(e) for e in b.debt_ledger]
