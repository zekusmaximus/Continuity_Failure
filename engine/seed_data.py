"""Northbridge Water Failure seed scenario.

This is the only authoritative starting condition for the MVP campaign. Every
value here is tuned so a thoughtful advice strategy can survive 10 turns while a
negligent one will trip a failure threshold. Nothing here is generated -- it is
hand-authored canon.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List

from engine.models import (
    AdviceOption,
    Campaign,
    CampaignStatus,
    ClientCall,
    Crisis,
    Faction,
    WorldState,
)

SCENARIO_ID = "northbridge_water_failure"
MAX_TURNS = 10


# ---------------------------------------------------------------------------
# Starting world state. Values are 0-100.
# ---------------------------------------------------------------------------

STARTING_VARIABLES: Dict[str, int] = {
    "water_security": 46,
    "power_stability": 72,
    "public_trust": 56,
    "public_order": 66,
    "budget_capacity": 40,
    "staff_capacity": 50,
    "legal_exposure": 34,
    "media_pressure": 28,
    "hospital_stability": 56,
    "school_disruption": 38,
    "state_oversight_risk": 26,
    "contractor_dependency": 52,
    "information_integrity": 62,
    "player_reputation": 50,
    "player_perceived_neutrality": 60,
    "player_shadow_authority": 18,
}


# ---------------------------------------------------------------------------
# Factions.
# ---------------------------------------------------------------------------

def _factions() -> List[Faction]:
    return [
        Faction(
            id="town_managers_office",
            name="Town Manager's Office",
            description="Appointed executive running day-to-day municipal operations.",
            posture="decisive",
            influence=78,
            alignment="authority",
        ),
        Faction(
            id="council_majority",
            name="Town Council Majority",
            description="Governing bloc controlling appropriations and emergency authorities.",
            posture="confident",
            influence=70,
            alignment="authority",
        ),
        Faction(
            id="council_opposition",
            name="Town Council Opposition",
            description="Minority bloc poised to capitalize on any misstep.",
            posture="circumspect",
            influence=45,
            alignment="opposition",
        ),
        Faction(
            id="water_authority",
            name="Public Works / Water Authority",
            description="Operators of the treatment plant, mains, and pressure system.",
            posture="stretched",
            influence=60,
            alignment="service",
        ),
        Faction(
            id="hospital",
            name="Northbridge Hospital",
            description="Regional acute-care facility dependent on municipal water.",
            posture="watchful",
            influence=55,
            alignment="service",
        ),
        Faction(
            id="parent_resident_coalition",
            name="Parent and Resident Coalition",
            description="Organized residents tracking school and household risk.",
            posture="alarmed",
            influence=48,
            alignment="neutral",
        ),
        Faction(
            id="business_alliance",
            name="Local Business Alliance",
            description="Employers and retailers sensitive to disruption and reputation.",
            posture="steady",
            influence=42,
            alignment="neutral",
        ),
        Faction(
            id="state_liaison",
            name="State Emergency Management Liaison",
            description="State agency observer with authority to trigger oversight.",
            posture="advisory",
            influence=50,
            alignment="authority",
        ),
        Faction(
            id="utility_contractor",
            name="Utility Contractor",
            description="Sole qualified firm able to repair the failing system.",
            posture="cooperative",
            influence=58,
            alignment="service",
        ),
        Faction(
            id="media_rumor_network",
            name="Local Media / Rumor Network",
            description="Patchwork of outlets and social channels amplifying uncertainty.",
            posture="circulating",
            influence=40,
            alignment="neutral",
        ),
    ]


def _crisis() -> Crisis:
    return Crisis(
        id="northbridge_water_crisis",
        name="Northbridge Water System Failure",
        description=(
            "Heat stress and deferred maintenance have destabilized the municipal "
            "water system. Preliminary contamination data is ambiguous, hospital "
            "and school pressure is at risk, and the only repair contractor holds "
            "outsized leverage over the town."
        ),
        severity=54,
        active=True,
    )


# ---------------------------------------------------------------------------
# Advice options. ``effects`` are deltas applied when FOLLOWED (adherence 1.0).
# ---------------------------------------------------------------------------

def _advice_options() -> List[AdviceOption]:
    return [
        AdviceOption(
            id="full_disclosure",
            label="Full disclosure and emergency conservation order",
            summary="Publish findings, issue a conservation order, and open the record.",
            rationale="Minimizes legal exposure and protects information integrity.",
            tags=["disclosure"],
            effects={
                "legal_exposure": -10,
                "information_integrity": +10,
                "public_trust": +5,
                "media_pressure": +10,
                "public_order": -8,
                "budget_capacity": -3,
                "player_reputation": +3,
            },
        ),
        AdviceOption(
            id="controlled_disclosure",
            label="Controlled disclosure with hospital and school mitigation",
            summary="Release a measured statement while pre-positioning mitigation.",
            rationale="Balanced: protects trust without triggering panic.",
            tags=["disclosure"],
            effects={
                "information_integrity": +6,
                "public_trust": +2,
                "media_pressure": +5,
                "public_order": -4,
                "hospital_stability": +3,
                "school_disruption": -4,
                "budget_capacity": -3,
            },
        ),
        AdviceOption(
            id="delay_disclosure",
            label="Delay public disclosure pending confirmatory testing",
            summary="Hold the public line while awaiting second-lab confirmation.",
            rationale="Preserves short-term order and contractor bandwidth.",
            tags=["delay"],
            effects={
                "public_order": +4,
                "information_integrity": -10,
                "public_trust": -8,
                "legal_exposure": +8,
                "media_pressure": +5,
            },
        ),
        AdviceOption(
            id="state_support",
            label="Request state emergency support immediately",
            summary="Invoke state emergency assistance for water and logistics.",
            rationale="Fastest path to water security, at a political cost.",
            tags=["state_support"],
            effects={
                "water_security": +12,
                "budget_capacity": +3,
                "state_oversight_risk": +12,
                "public_trust": -3,
                "player_shadow_authority": +3,
            },
        ),
        AdviceOption(
            id="contractor_pressure",
            label="Pressure the contractor privately while preparing a statement",
            summary="Force a faster repair timeline without public confrontation.",
            rationale="Protects budget and water but deepens dependency.",
            tags=["contractor"],
            effects={
                "water_security": +8,
                "budget_capacity": +4,
                "contractor_dependency": +10,
                "legal_exposure": +2,
                "public_trust": -2,
            },
        ),
        AdviceOption(
            id="mutual_aid",
            label="Convene regional mutual aid before public escalation",
            summary="Pull neighboring utilities and regional hospitals into the response.",
            rationale="Strengthens hospital and water resilience collaboratively.",
            tags=["mutual_aid"],
            effects={
                "hospital_stability": +6,
                "water_security": +6,
                "budget_capacity": -5,
                "public_trust": +2,
                "state_oversight_risk": +3,
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Per-turn client calls. The situation evolves across the 10-turn engagement.
# ---------------------------------------------------------------------------

def _client_calls() -> Dict[int, ClientCall]:
    calls = [
        ClientCall(
            id="call_01", turn=1,
            caller="Town Manager's Office", caller_faction_id="town_managers_office",
            summary="Inbound from the Town Manager: ambiguous contamination sample, falling pressure.",
            known_facts=[
                "Preliminary sample shows a possible contaminant above advisory threshold.",
                "System pressure dropped 12% overnight in the south pressure zone.",
                "Confirmatory second-lab result is pending.",
            ],
            ask="How should we handle disclosure and conservation before the second lab returns?",
        ),
        ClientCall(
            id="call_02", turn=2,
            caller="Public Works / Water Authority", caller_faction_id="water_authority",
            summary="Water Authority reports the repair window is shrinking and staff are stretched.",
            known_facts=[
                "The failing main can only be isolated with the sole contractor's crew.",
                "Operator overtime is already at cap for the month.",
                "Pressure is holding but trending down.",
            ],
            ask="Do we commit emergency budget to the contractor now, or seek help first?",
        ),
        ClientCall(
            id="call_03", turn=3,
            caller="Northbridge Hospital", caller_faction_id="hospital",
            summary="Hospital counsel calls: dialysis and sterilization depend on stable water.",
            known_facts=[
                "Two days of degraded pressure would force elective cancellations.",
                "Tanker resupply is available but logistically fragile.",
                "State hospital liaison is asking pointed questions.",
            ],
            ask="How do we protect clinical operations without triggering a state takeover?",
        ),
        ClientCall(
            id="call_04", turn=4,
            caller="Local Media / Rumor Network", caller_faction_id="media_rumor_network",
            summary="A reporter and a council staffer have independently heard about the sample.",
            known_facts=[
                "A press inquiry names the contaminant but gets the threshold wrong.",
                "Social posts claim a 'cover-up' despite no confirmed finding.",
                "Council opposition is drafting a statement.",
            ],
            ask="What do we say publicly before the narrative firms up without us?",
        ),
        ClientCall(
            id="call_05", turn=5,
            caller="Town Council Majority", caller_faction_id="council_majority",
            summary="Council Majority wants to know the fiscal and legal exposure before they vote.",
            known_facts=[
                "Emergency appropriation authority exists but is politically costly.",
                "Legal counsel flags a disclosure-timing liability.",
                "Business alliance is asking about continuity guarantees.",
            ],
            ask="What posture should the council authorize: conservation, state help, or contractor escalation?",
        ),
        ClientCall(
            id="call_06", turn=6,
            caller="Parent and Resident Coalition", caller_faction_id="parent_resident_coalition",
            summary="Parent coalition: schools cannot stay open if pressure drops further.",
            known_facts=[
                "Three schools rely on the south pressure zone.",
                "Parents are organizing carpool to neighboring districts.",
                "Superintendent wants a closure threshold.",
            ],
            ask="How do we keep schools running or close them responsibly and on the record?",
        ),
        ClientCall(
            id="call_07", turn=7,
            caller="Utility Contractor", caller_faction_id="utility_contractor",
            summary="The contractor is requesting a premium-rate emergency change order.",
            known_facts=[
                "Only this firm holds the certifications for the failing valves.",
                "Their proposed timeline slips without the premium.",
                "Procurement has no competitive fallback this quarter.",
            ],
            ask="Do we accept the change order, push back, or try to source alternatives?",
        ),
        ClientCall(
            id="call_08", turn=8,
            caller="State Emergency Management Liaison", caller_faction_id="state_liaison",
            summary="State liaison signals readiness to intervene if metrics keep sliding.",
            known_facts=[
                "State can deploy tankers and operators within 36 hours.",
                "Accepting help raises the odds of a formal oversight designation.",
                "Council opposition favors state help; majority resists it.",
            ],
            ask="Do we invite state support now, or hold out for a local resolution?",
        ),
        ClientCall(
            id="call_09", turn=9,
            caller="Town Council Opposition", caller_faction_id="council_opposition",
            summary="Opposition is threatening a public hearing on the response record.",
            known_facts=[
                "They have compiled a partial timeline of decisions and memos.",
                "Media is primed to amplify a hearing.",
                "A hearing could surface legal-timing questions.",
            ],
            ask="How do we respond to the hearing threat without handing them the narrative?",
        ),
        ClientCall(
            id="call_10", turn=10,
            caller="Town Manager's Office", caller_faction_id="town_managers_office",
            summary="Final stabilization check: can we close the engagement on stable footing?",
            known_facts=[
                "The second lab result is now on the record.",
                "Contractor work is partially complete.",
                "State, hospital, and public all need a credible closeout posture.",
            ],
            ask="What is the final advice to lock in stabilization and protect the institutional record?",
        ),
    ]
    return {call.turn: call for call in calls}


# ---------------------------------------------------------------------------
# Campaign factory.
# ---------------------------------------------------------------------------

def create_northbridge_campaign(campaign_id: str = "", name: str = "") -> Campaign:
    """Construct a fresh Northbridge campaign with deterministic starting state."""
    campaign_id = campaign_id or uuid.uuid4().hex[:8]
    name = name or "Northbridge Water Failure"
    world_state = WorldState(
        turn_number=1,
        variables=dict(STARTING_VARIABLES),
        factions=_factions(),
        active_crisis=_crisis(),
        last_verified=_last_verified(1),
    )
    return Campaign(
        id=campaign_id,
        name=name,
        scenario_id=SCENARIO_ID,
        status=CampaignStatus.ACTIVE,
        turn_number=1,
        max_turns=MAX_TURNS,
        world_state=world_state,
        advice_options=_advice_options(),
        client_calls=_client_calls(),
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def _last_verified(turn: int) -> str:
    return f"Turn {turn} \u00b7 Operational snapshot (deterministic)"

