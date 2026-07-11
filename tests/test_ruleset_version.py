"""Ruleset-version stamping and golden-trace pinning.

Every campaign is stamped with the deterministic-rules version that resolves
it (``engine.rules.CURRENT_RULESET_VERSION``), and the exact terminal state of
the three canonical strategies is pinned per version below. Together they are
the guarantee that balance tuning never silently rewrites history:

* Change any rules constant and the golden-trace test fails until you bump
  ``CURRENT_RULESET_VERSION`` AND add a matching golden entry -- an explicit,
  reviewed act, with the old entry kept as the historical record.
* Old persisted snapshots (written before the field existed) load as
  version "1", because that is the ruleset they were resolved under.
"""

from __future__ import annotations

import json

from engine import seed_data, turn
from engine.models import CampaignStatus
from engine.rules import CURRENT_RULESET_VERSION
from memory.persistence import SQLiteRepository


SURVIVAL_SEQUENCE = [
    "controlled_disclosure",
    "contractor_pressure",
    "mutual_aid",
    "controlled_disclosure",
    "state_support",
    "controlled_disclosure",
    "mutual_aid",
    "contractor_pressure",
    "controlled_disclosure",
    "mutual_aid",
]

CANONICAL_SEQUENCES = {
    "survival": SURVIVAL_SEQUENCE,
    "contractor_spam": ["contractor_pressure"] * 10,
    "delay_spam": ["delay_disclosure"] * 10,
}


# ---------------------------------------------------------------------------
# Golden terminal states, keyed by ruleset version. NEVER edit an existing
# entry: a balance change gets a NEW version key (and a bump of
# CURRENT_RULESET_VERSION in engine/rules.py); superseded entries stay here
# as the on-the-record history of what each ruleset produced.
# ---------------------------------------------------------------------------

GOLDEN_TRACES = {
    # Ruleset "3" (Wave 2 balance pass): an ignored grid-stress thread now
    # erodes power every peak cycle (-6, repeat 1) instead of -4 every other
    # turn, and cross-faction trust costs make the turn-4 contractor ultimatum
    # reachable. None of the canonical sequences plays the load-shedding
    # counter, so every "3" entry differs from its "2" entry ONLY in
    # power_stability. The contractor_spam sequence now (correctly) resolves
    # turn 4 against the ultimatum variant -- asserted by
    # test_contractor_spam_reaches_the_ultimatum_variant below -- without
    # changing any final variable other than power_stability.
    "3": {
        "survival": {
            "status": CampaignStatus.COMPLETED,
            "failure_reason": None,
            "turns_resolved": 10,
            "final_variables": {
                "water_security": 62, "power_stability": 24,
                "public_trust": 63, "public_order": 54,
                "budget_capacity": 2, "staff_capacity": 40,
                "legal_exposure": 60, "media_pressure": 73,
                "hospital_stability": 74, "school_disruption": 46,
                "state_oversight_risk": 42, "contractor_dependency": 74,
                "information_integrity": 79, "player_reputation": 45,
                "player_perceived_neutrality": 50, "player_shadow_authority": 20,
            },
        },
        "contractor_spam": {
            "status": CampaignStatus.FAILED,
            "failure_reason": (
                "Legal Exposure reached 98 (failure threshold >= 95)."
            ),
            "turns_resolved": 10,
            "final_variables": {
                "water_security": 87, "power_stability": 24,
                "public_trust": 46, "public_order": 66,
                "budget_capacity": 21, "staff_capacity": 40,
                "legal_exposure": 98, "media_pressure": 70,
                "hospital_stability": 46, "school_disruption": 58,
                "state_oversight_risk": 35, "contractor_dependency": 100,
                "information_integrity": 62, "player_reputation": 42,
                "player_perceived_neutrality": 44, "player_shadow_authority": 18,
            },
        },
        "delay_spam": {
            "status": CampaignStatus.FAILED,
            "failure_reason": (
                "Legal Exposure reached 100 (failure threshold >= 95)."
            ),
            "turns_resolved": 8,
            "final_variables": {
                "water_security": 30, "power_stability": 36,
                "public_trust": 14, "public_order": 63,
                "budget_capacity": 24, "staff_capacity": 42,
                "legal_exposure": 100, "media_pressure": 98,
                "hospital_stability": 48, "school_disruption": 60,
                "state_oversight_risk": 54, "contractor_dependency": 66,
                "information_integrity": 43, "player_reputation": 33,
                "player_perceived_neutrality": 36, "player_shadow_authority": 18,
            },
        },
    },
    # Ruleset "2" (Wave 2b, batch B1): power_stability gained deterministic
    # drivers -- the authored heat-event ambient window (turns 3-6, -6/turn)
    # and the grid-stress thread spec (opens at power <= 55, escalates -4
    # every 2 turns). None of the canonical sequences plays the load-shedding
    # counter, so every "2" entry differs from its "1" entry ONLY in
    # power_stability (asserted by
    # test_ruleset_two_changed_only_power_stability below).
    "2": {
        "survival": {
            "status": CampaignStatus.COMPLETED,
            "failure_reason": None,
            "turns_resolved": 10,
            "final_variables": {
                "water_security": 62, "power_stability": 40,
                "public_trust": 63, "public_order": 54,
                "budget_capacity": 2, "staff_capacity": 40,
                "legal_exposure": 60, "media_pressure": 73,
                "hospital_stability": 74, "school_disruption": 46,
                "state_oversight_risk": 42, "contractor_dependency": 74,
                "information_integrity": 79, "player_reputation": 45,
                "player_perceived_neutrality": 50, "player_shadow_authority": 20,
            },
        },
        "contractor_spam": {
            "status": CampaignStatus.FAILED,
            "failure_reason": (
                "Legal Exposure reached 98 (failure threshold >= 95)."
            ),
            "turns_resolved": 10,
            "final_variables": {
                "water_security": 87, "power_stability": 40,
                "public_trust": 46, "public_order": 66,
                "budget_capacity": 21, "staff_capacity": 40,
                "legal_exposure": 98, "media_pressure": 70,
                "hospital_stability": 46, "school_disruption": 58,
                "state_oversight_risk": 35, "contractor_dependency": 100,
                "information_integrity": 62, "player_reputation": 42,
                "player_perceived_neutrality": 44, "player_shadow_authority": 18,
            },
        },
        "delay_spam": {
            "status": CampaignStatus.FAILED,
            "failure_reason": (
                "Legal Exposure reached 100 (failure threshold >= 95)."
            ),
            "turns_resolved": 8,
            "final_variables": {
                "water_security": 30, "power_stability": 44,
                "public_trust": 14, "public_order": 63,
                "budget_capacity": 24, "staff_capacity": 42,
                "legal_exposure": 100, "media_pressure": 98,
                "hospital_stability": 48, "school_disruption": 60,
                "state_oversight_risk": 54, "contractor_dependency": 66,
                "information_integrity": 43, "player_reputation": 33,
                "player_perceived_neutrality": 36, "player_shadow_authority": 18,
            },
        },
    },
    "1": {
        "survival": {
            "status": CampaignStatus.COMPLETED,
            "failure_reason": None,
            "turns_resolved": 10,
            "final_variables": {
                "water_security": 62, "power_stability": 72,
                "public_trust": 63, "public_order": 54,
                "budget_capacity": 2, "staff_capacity": 40,
                "legal_exposure": 60, "media_pressure": 73,
                "hospital_stability": 74, "school_disruption": 46,
                "state_oversight_risk": 42, "contractor_dependency": 74,
                "information_integrity": 79, "player_reputation": 45,
                "player_perceived_neutrality": 50, "player_shadow_authority": 20,
            },
        },
        "contractor_spam": {
            "status": CampaignStatus.FAILED,
            "failure_reason": (
                "Legal Exposure reached 98 (failure threshold >= 95)."
            ),
            "turns_resolved": 10,
            "final_variables": {
                "water_security": 87, "power_stability": 72,
                "public_trust": 46, "public_order": 66,
                "budget_capacity": 21, "staff_capacity": 40,
                "legal_exposure": 98, "media_pressure": 70,
                "hospital_stability": 46, "school_disruption": 58,
                "state_oversight_risk": 35, "contractor_dependency": 100,
                "information_integrity": 62, "player_reputation": 42,
                "player_perceived_neutrality": 44, "player_shadow_authority": 18,
            },
        },
        "delay_spam": {
            "status": CampaignStatus.FAILED,
            "failure_reason": (
                "Legal Exposure reached 100 (failure threshold >= 95)."
            ),
            "turns_resolved": 8,
            "final_variables": {
                "water_security": 30, "power_stability": 72,
                "public_trust": 14, "public_order": 63,
                "budget_capacity": 24, "staff_capacity": 42,
                "legal_exposure": 100, "media_pressure": 98,
                "hospital_stability": 48, "school_disruption": 60,
                "state_oversight_risk": 54, "contractor_dependency": 66,
                "information_integrity": 43, "player_reputation": 33,
                "player_perceived_neutrality": 36, "player_shadow_authority": 18,
            },
        },
    },
}


def _play(sequence):
    campaign = seed_data.create_northbridge_campaign(name="golden")
    for advice_id in sequence:
        if campaign.is_terminal():
            break
        turn.advance_turn(campaign, advice_id)
    return campaign


# ---------------------------------------------------------------------------
# Stamping
# ---------------------------------------------------------------------------

def test_new_campaigns_are_stamped_with_the_current_ruleset_version():
    campaign = seed_data.create_northbridge_campaign(name="stamped")
    assert campaign.ruleset_version == CURRENT_RULESET_VERSION


def test_current_ruleset_version_has_a_golden_entry():
    """A version bump without a matching golden entry is an incomplete change."""
    assert CURRENT_RULESET_VERSION in GOLDEN_TRACES, (
        f"CURRENT_RULESET_VERSION={CURRENT_RULESET_VERSION!r} has no golden "
        "traces. Add an entry to GOLDEN_TRACES (and keep the old entries)."
    )
    assert set(GOLDEN_TRACES[CURRENT_RULESET_VERSION]) == set(CANONICAL_SEQUENCES)


# ---------------------------------------------------------------------------
# Golden traces: the terminal state of every canonical strategy is pinned,
# bit for bit, per ruleset version.
# ---------------------------------------------------------------------------

def test_canonical_sequences_match_the_golden_traces():
    golden = GOLDEN_TRACES[CURRENT_RULESET_VERSION]
    for name, sequence in CANONICAL_SEQUENCES.items():
        campaign = _play(sequence)
        expected = golden[name]
        assert campaign.status == expected["status"], name
        assert campaign.failure_reason == expected["failure_reason"], name
        assert len(campaign.turn_history) == expected["turns_resolved"], name
        assert campaign.world_state.variables == expected["final_variables"], (
            f"{name}: the deterministic rules no longer reproduce the golden "
            f"trace for ruleset {CURRENT_RULESET_VERSION!r}. If this change is "
            "intentional, bump CURRENT_RULESET_VERSION in engine/rules.py and "
            "add a new golden entry -- do not edit the existing one."
        )


def test_ruleset_three_changed_only_power_stability():
    """The ruleset-3 balance pass touches no failure-threshold variable:
    every canonical outcome, turn count, and non-power variable is
    bit-identical to ruleset "2". The contractor_spam sequence resolves turn 4
    against the ultimatum variant under "3", but the variant's decision space
    (contractor_pressure on-brief, same tag handler) leaves the authoritative
    variables unchanged."""
    for name in CANONICAL_SEQUENCES:
        v2 = GOLDEN_TRACES["2"][name]
        v3 = GOLDEN_TRACES["3"][name]
        assert v2["status"] == v3["status"], name
        assert v2["failure_reason"] == v3["failure_reason"], name
        assert v2["turns_resolved"] == v3["turns_resolved"], name
        changed = {
            var for var, value in v3["final_variables"].items()
            if v2["final_variables"][var] != value
        }
        assert changed == {"power_stability"}, (
            f"{name}: ruleset 3 changed {sorted(changed)}; only "
            "power_stability may differ from ruleset 2"
        )


def test_contractor_spam_reaches_the_ultimatum_variant():
    """Under ruleset 3, three acted-on squeezes collapse the contractor's
    working trust (40 -> 22, at or below the authored threshold 25), so the
    turn-4 call resolves against the ultimatum variant -- previously dead
    content (trust could never move before turn 4)."""
    campaign = _play(CANONICAL_SEQUENCES["contractor_spam"])
    variants = [t.call_variant_id for t in campaign.turn_history]
    assert variants[3] == "call_04_terms_ultimatum"
    assert all(v is None for i, v in enumerate(variants) if i != 3)


def test_ruleset_two_changed_only_power_stability():
    """The B1 drivers touch no failure-threshold variable: every canonical
    outcome, turn count, and non-power variable is bit-identical to ruleset
    "1". This is the pinned statement that the 2b drift is capability
    pressure, not balance pressure."""
    for name in CANONICAL_SEQUENCES:
        v1 = GOLDEN_TRACES["1"][name]
        v2 = GOLDEN_TRACES["2"][name]
        assert v1["status"] == v2["status"], name
        assert v1["failure_reason"] == v2["failure_reason"], name
        assert v1["turns_resolved"] == v2["turns_resolved"], name
        changed = {
            var for var, value in v2["final_variables"].items()
            if v1["final_variables"][var] != value
        }
        assert changed == {"power_stability"}, (
            f"{name}: ruleset 2 changed {sorted(changed)}; only "
            "power_stability may differ from ruleset 1"
        )


# ---------------------------------------------------------------------------
# Persistence: snapshots written before the field existed load as "1".
# ---------------------------------------------------------------------------

def test_campaign_persisted_without_the_field_loads_as_version_one(tmp_path):
    repository = SQLiteRepository(tmp_path / "pre-version.sqlite3")
    campaign = seed_data.create_northbridge_campaign(name="old build")
    repository.put(campaign)

    # Simulate a pre-upgrade database: strip the field from the stored payload
    # exactly as an older build would have written it.
    with repository._connect() as connection:  # noqa: SLF001 - test hook
        row = connection.execute(
            "SELECT payload_json FROM campaigns WHERE id = ?", (campaign.id,)
        ).fetchone()
        payload = json.loads(row["payload_json"])
        assert payload["data"].pop("ruleset_version") == CURRENT_RULESET_VERSION
        connection.execute(
            "UPDATE campaigns SET payload_json = ? WHERE id = ?",
            (json.dumps(payload), campaign.id),
        )
        connection.commit()

    reopened = SQLiteRepository(repository.path).get(campaign.id)
    assert reopened.ruleset_version == "1"


def test_ruleset_version_roundtrips_through_persistence(tmp_path):
    repository = SQLiteRepository(tmp_path / "roundtrip.sqlite3")
    campaign = seed_data.create_northbridge_campaign(name="roundtrip")
    repository.put(campaign)
    restored = SQLiteRepository(repository.path).get(campaign.id)
    assert restored.ruleset_version == CURRENT_RULESET_VERSION
