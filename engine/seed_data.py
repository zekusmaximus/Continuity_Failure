"""Northbridge Water Failure seed scenario.

This is the only authoritative starting condition for the MVP campaign. Every
value here is tuned so a thoughtful advice strategy can survive 10 turns while a
negligent one will trip a failure threshold. Nothing here is generated -- it is
hand-authored canon.

The 10-turn arc is written as a *cascade*, not a random event stream: an
ambiguous lab result widens into school, hospital, contractor, rumor, state,
business, and political pressure in turn, until turn 10 offers a stabilization
package conditioned on outside oversight.
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
    Document,
    Faction,
    OpenThread,
    PublicStatus,
    Reliability,
    Urgency,
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
            posture="decisive", influence=78, alignment="authority",
            type="EXECUTIVE",
            public_position="Treat the situation as an acceleration of deferred maintenance.",
            private_incentive="Keep a stabilization record that survives a council vote and a state review.",
            trust_in_player=58, risk_tolerance=45, current_pressure=62,
            red_lines=[
                "A state receivership or oversight designation.",
                "Any documented public falsehood traceable to the Manager's office.",
            ],
            tags=["decision_authority", "engagement_holder"],
        ),
        Faction(
            id="council_majority",
            name="Town Council Majority",
            description="Governing bloc controlling appropriations and emergency authorities.",
            posture="confident", influence=70, alignment="authority",
            type="LEGISLATIVE",
            public_position="Support the Manager while protecting the majority bloc's record.",
            private_incentive="Authorize enough to look decisive without owning the political risk.",
            trust_in_player=50, risk_tolerance=35, current_pressure=55,
            red_lines=[
                "Emergency appropriations without a recorded vote.",
                "Public blame settling on the majority bloc.",
            ],
            tags=["appropriations", "vote"],
        ),
        Faction(
            id="council_opposition",
            name="Town Council Opposition",
            description="Minority bloc poised to capitalize on any misstep.",
            posture="circumspect", influence=45, alignment="opposition",
            type="LEGISLATIVE",
            public_position="Demand transparency and a full public record.",
            private_incentive="Build a record that frames the majority as evasive.",
            trust_in_player=38, risk_tolerance=60, current_pressure=58,
            red_lines=[
                "Closed-session approvals they cannot scrutinize.",
                "Being the last to see internal memos.",
            ],
            tags=["oversight", "hearing_threat"],
        ),
        Faction(
            id="water_authority",
            name="Public Works / Water Authority",
            description="Operators of the treatment plant, mains, and pressure system.",
            posture="stretched", influence=60, alignment="service",
            type="UTILITY",
            public_position="We can hold pressure if we get staff and contractor support.",
            private_incentive="Avoid being named as the cause of the failure.",
            trust_in_player=55, risk_tolerance=40, current_pressure=64,
            red_lines=[
                "Liability for contamination they did not introduce.",
                "Operating beyond certified staffing.",
            ],
            tags=["operator", "staff_constrained"],
        ),
        Faction(
            id="hospital",
            name="Northbridge Hospital",
            description="Regional acute-care facility dependent on municipal water.",
            posture="watchful", influence=55, alignment="service",
            type="HOSPITAL",
            public_position="Protect clinical operations, especially dialysis and sterilization.",
            private_incentive="Secure priority allocation without becoming the public face of the crisis.",
            trust_in_player=60, risk_tolerance=30, current_pressure=50,
            red_lines=[
                "An unplanned loss of water for dialysis or sterilization.",
                "Being blamed for an elective-cancellation cascade.",
            ],
            tags=["critical_facility", "priority_water"],
        ),
        Faction(
            id="parent_resident_coalition",
            name="Parent and Resident Coalition",
            description="Organized residents tracking school and household risk.",
            posture="alarmed", influence=48, alignment="neutral",
            type="RESIDENT_GROUP",
            public_position="Close or protect the schools; tell us the truth about the water.",
            private_incentive="Force visible, on-the-record action before pressure drops further.",
            trust_in_player=44, risk_tolerance=55, current_pressure=66,
            red_lines=[
                "Schools staying open under unsafe pressure.",
                "Residents being the last to learn.",
            ],
            tags=["school_pressure", "social_amplification"],
        ),
        Faction(
            id="business_alliance",
            name="Local Business Alliance",
            description="Employers and retailers sensitive to disruption and reputation.",
            posture="steady", influence=42, alignment="neutral",
            type="BUSINESS",
            public_position="Keep the town open for business; compensate mandatory closures.",
            private_incentive="Avoid a contaminated-town reputation that lingers past the crisis.",
            trust_in_player=46, risk_tolerance=50, current_pressure=44,
            red_lines=[
                "Uncompensated mandatory closures.",
                "A public 'contamination' label they cannot contest.",
            ],
            tags=["economic", "reputation_sensitive"],
        ),
        Faction(
            id="state_liaison",
            name="State Emergency Management Liaison",
            description="State agency observer with authority to trigger oversight.",
            posture="advisory", influence=50, alignment="authority",
            type="STATE_ACTOR",
            public_position="Offer resources; expect timely notification and documentation.",
            private_incentive="Avoid a visible local failure on the agency's watch.",
            trust_in_player=52, risk_tolerance=42, current_pressure=48,
            red_lines=[
                "Being notified after the press.",
                "Quiet local deals that foreclose state response options.",
            ],
            tags=["state_oversight", "intervention_trigger"],
        ),
        Faction(
            id="utility_contractor",
            name="Utility Contractor",
            description="Sole qualified firm able to repair the failing system.",
            posture="cooperative", influence=58, alignment="service",
            type="CONTRACTOR",
            public_position="We can deliver if the town underwrites the emergency scope.",
            private_incentive="Lock in premium rates and indemnity while leverage is high.",
            trust_in_player=40, risk_tolerance=65, current_pressure=60,
            red_lines=[
                "Indemnification gaps on emergency change orders.",
                "A competitive procurement that sidelines the firm.",
            ],
            tags=["sole_source", "leverage"],
        ),
        Faction(
            id="media_rumor_network",
            name="Local Media / Rumor Network",
            description="Patchwork of outlets and social channels amplifying uncertainty.",
            posture="circulating", influence=40, alignment="neutral",
            type="MEDIA",
            public_position="Report what we can verify; chase what we can't.",
            private_incentive="A leak or contradiction is the most valuable story available.",
            trust_in_player=30, risk_tolerance=70, current_pressure=52,
            red_lines=[
                "A clean, well-managed story with no seams to pull.",
            ],
            tags=["narrative", "amplification"],
        ),
    ]


def _crisis() -> Crisis:
    return Crisis(
        id="northbridge_water_crisis",
        name="Northbridge Water System Failure",
        description=(
            "Heat stress and deferred maintenance have destabilized the municipal "
            "water system. A preliminary contamination sample is ambiguous, system "
            "pressure is falling in the south zone, hospital and school operations "
            "depend on stable supply, and the only qualified repair contractor holds "
            "outsized leverage over the town. Each decision narrows the next."
        ),
        severity=54,
        active=True,
        type="WATER_FAILURE",
    )


# ---------------------------------------------------------------------------
# Advice options. ``effects`` are deltas applied when FOLLOWED (adherence 1.0).
# The six IDs below are referenced by name in the test suite, so they must stay
# stable; the tradeoff fields are descriptive overlays the UI surfaces.
# ---------------------------------------------------------------------------

def _advice_options() -> List[AdviceOption]:
    return [
        AdviceOption(
            id="full_disclosure",
            label="Full disclosure and emergency conservation order",
            summary="Publish the findings, issue a conservation order, and open the record.",
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
            type="FULL_DISCLOSURE",
            recommendation=(
                "Release the preliminary result with a conservation order, notify the "
                "state agency in writing, and publish the response timeline."
            ),
            expected_benefits=[
                "Lowest legal exposure; the disclosure-timing liability is discharged.",
                "Information integrity holds; the record is clean.",
            ],
            expected_harms=[
                "Short-term public-order shock and media amplification.",
                "Business and school disruption spike before mitigation lands.",
            ],
            operational_steps=[
                "Transmit the preliminary result and response timeline to the state liaison in writing.",
                "Issue the conservation order with separate hospital and school operating instructions.",
                "Publish the source report, known uncertainties, and the next verification deadline together.",
            ],
            legal_risk=15, political_risk=70, operational_risk=45,
            affected_factions=[
                "town_managers_office", "media_rumor_network",
                "parent_resident_coalition", "business_alliance",
            ],
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
            type="CONTROLLED_DISCLOSURE",
            recommendation=(
                "Issue a measured public statement, pre-position hospital and school "
                "mitigation, and brief the state liaison before press runs the story."
            ),
            expected_benefits=[
                "Trust and information integrity both improve modestly.",
                "Hospital and schools are buffered before the public learns.",
            ],
            expected_harms=[
                "Vulnerable to a leak narrative if the rumor feed moves first.",
                "Spends budget and staff on mitigation that may look precautionary.",
            ],
            operational_steps=[
                "Brief the state liaison, hospital, and superintendent before the public statement.",
                "Pre-position clinical water and school sanitation contingencies before release.",
                "Publish a measured statement that names the uncertainty and the next verification deadline.",
            ],
            legal_risk=35, political_risk=45, operational_risk=35,
            affected_factions=[
                "town_managers_office", "hospital", "parent_resident_coalition",
                "media_rumor_network",
            ],
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
            type="DELAY",
            recommendation=(
                "Wait for the confirmatory second-lab result before any public "
                "statement; continue quiet mitigation in the meantime."
            ),
            expected_benefits=[
                "Short-term public order is preserved.",
                "Buys time for contractor repair sequencing.",
            ],
            expected_harms=[
                "Disclosure-timing liability builds sharply.",
                "A leak converts the delay into a concealment narrative.",
            ],
            operational_steps=[
                "Document the basis and expiration time for withholding the preliminary result.",
                "Continue quiet hospital, school, and pressure-zone mitigation during the wait.",
                "Prepare a release package that can be issued immediately if the result leaks or confirms.",
            ],
            legal_risk=85, political_risk=60, operational_risk=25,
            affected_factions=[
                "council_opposition", "media_rumor_network",
                "parent_resident_coalition",
            ],
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
            type="STATE_AID_REQUEST",
            recommendation=(
                "Formally request state emergency assistance for water, logistics, "
                "and operators; document the operational necessity."
            ),
            expected_benefits=[
                "Fastest material improvement to water security.",
                "Budget pressure eases as state resources arrive.",
            ],
            expected_harms=[
                "Raises the odds of a formal oversight designation.",
                "Politically costly; the majority bloc resists outside control.",
            ],
            operational_steps=[
                "Send a written request identifying tanker, operator, and logistics requirements.",
                "Record why local capacity cannot meet the current operational need.",
                "Negotiate a time-bounded reporting and authority framework before accepting resources.",
            ],
            legal_risk=30, political_risk=65, operational_risk=20,
            affected_factions=[
                "state_liaison", "council_majority", "town_managers_office",
            ],
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
            type="CONTRACTOR_PRESSURE",
            recommendation=(
                "Negotiate a faster emergency timeline privately, with a contingency "
                "statement ready if the squeeze fails."
            ),
            expected_benefits=[
                "Water security improves without public escalation.",
                "Budget terms improve if the town credibly threatens alternatives.",
            ],
            expected_harms=[
                "Deepens structural dependency on a sole-source firm.",
                "Little leverage if the contractor calls the bluff.",
            ],
            operational_steps=[
                "Set a written repair milestone and crew-staging deadline for the contractor.",
                "Document the town's alternatives, indemnity limits, and walk-away conditions.",
                "Prepare a public procurement statement for release if the revised timeline is refused.",
            ],
            legal_risk=40, political_risk=35, operational_risk=55,
            affected_factions=[
                "utility_contractor", "water_authority", "council_majority",
            ],
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
            type="MUTUAL_AID",
            recommendation=(
                "Activate the regional mutual-aid compact for neighboring utilities "
                "and hospital resupply before the crisis goes fully public."
            ),
            expected_benefits=[
                "Hospital and water resilience both improve cooperatively.",
                "Public trust benefits from visible regional coordination.",
            ],
            expected_harms=[
                "Costs budget and political capital.",
                "Slightly raises state awareness of the failure.",
            ],
            operational_steps=[
                "Activate the regional compact with named water, staffing, and hospital requests.",
                "Assign one municipal coordinator to reconcile incoming aid with local operations.",
                "Publish the scope and duration of mutual aid without overstating system stability.",
            ],
            legal_risk=25, political_risk=40, operational_risk=40,
            affected_factions=[
                "hospital", "water_authority", "state_liaison", "council_majority",
            ],
        ),
    ]


# ---------------------------------------------------------------------------
# Per-turn advice options. These only make sense on a specific turn's call, so
# they are surfaced *in addition to* the six global options above -- but only on
# their turn. Each carries the same tradeoff surface and a deterministic effects
# map; each has at least one stated harm (no free lunch). New tags get a
# dedicated ``_decide_*`` handler in engine/rules.py.
# ---------------------------------------------------------------------------

def _per_turn_advice() -> Dict[int, List[AdviceOption]]:
    return {
        2: [
            AdviceOption(
                id="school_staged_closure",
                label="Issue a staged, threshold-based school closure protocol",
                summary=(
                    "Publish a written pressure threshold and a staged closure "
                    "protocol for the three south-zone schools."
                ),
                rationale=(
                    "Gives the superintendent a defensible, on-the-record rule "
                    "instead of a guess, and blunts the concealment narrative."
                ),
                tags=["school_closure"],
                effects={
                    "school_disruption": -6,
                    "public_trust": +4,
                    "legal_exposure": -3,
                    "budget_capacity": -3,
                    "public_order": -2,
                    "media_pressure": +2,
                },
                type="SCHOOL_CLOSURE_PROTOCOL",
                recommendation=(
                    "Adopt a written pressure floor below which the three "
                    "south-zone schools close, with a staged reopening test."
                ),
                expected_benefits=[
                    "Replaces a guess with a defensible, published threshold.",
                    "Parents see on-the-record action; trust steadies.",
                ],
                expected_harms=[
                    "A precautionary closure spends budget and disrupts families "
                    "even if the water proves fine.",
                    "Publishing a closure rule signals the crisis is real, "
                    "raising media pressure.",
                ],
                operational_steps=[
                    "Set the sanitation and pressure measurements that trigger each closure stage.",
                    "Publish transportation, meal, and remote-learning arrangements with the threshold.",
                    "Require a documented verification check before reopening each building.",
                ],
                legal_risk=25, political_risk=40, operational_risk=35,
                affected_factions=[
                    "parent_resident_coalition", "council_majority",
                    "media_rumor_network",
                ],
            ),
        ],
        3: [
            AdviceOption(
                id="hospital_priority_allocation",
                label="Document priority water allocation for the hospital",
                summary=(
                    "Formally allocate priority pressurized supply to dialysis "
                    "and sterilization, with tanker resupply as backup."
                ),
                rationale=(
                    "Protects the most acute clinical need and creates a clean "
                    "record before a harm event can occur."
                ),
                tags=["hospital_priority"],
                effects={
                    "hospital_stability": +8,
                    "water_security": -3,
                    "public_trust": +2,
                    "legal_exposure": -2,
                    "budget_capacity": -2,
                },
                type="HOSPITAL_PRIORITY",
                recommendation=(
                    "Issue documented priority allocation for clinical water and "
                    "pre-stage tanker resupply for dialysis and sterilization."
                ),
                expected_benefits=[
                    "Clinical operations are protected before a cascade begins.",
                    "A documented allocation reduces liability exposure.",
                ],
                expected_harms=[
                    "Diverting pressurized supply thins the general system margin.",
                    "A visible priority for the hospital can trigger a fairness "
                    "dispute with residents.",
                ],
                operational_steps=[
                    "Document the dialysis and sterilization volumes that receive priority supply.",
                    "Stage tanker backup and define the pressure reading that triggers delivery.",
                    "Brief resident representatives on the clinical basis and limits of the allocation.",
                ],
                legal_risk=25, political_risk=35, operational_risk=45,
                affected_factions=[
                    "hospital", "water_authority", "parent_resident_coalition",
                ],
            ),
        ],
        7: [
            AdviceOption(
                id="business_compensation_framework",
                label="Offer a compensation framework for mandatory closures",
                summary=(
                    "Pair enforceable conservation restrictions with a limited "
                    "compensation framework for affected businesses."
                ),
                rationale=(
                    "Trades fiscal capacity for enforceability, defusing the "
                    "injunction threat without conceding the public-health line."
                ),
                tags=["business_compensation"],
                effects={
                    "budget_capacity": -6,
                    "public_order": +4,
                    "legal_exposure": -4,
                    "public_trust": +2,
                    "media_pressure": -2,
                },
                type="BUSINESS_COMPENSATION",
                recommendation=(
                    "Offer a capped compensation framework tied to compliance so "
                    "restrictions hold up against an injunction."
                ),
                expected_benefits=[
                    "Keeps conservation restrictions enforceable; order improves.",
                    "Removes the coalition's strongest grounds for an injunction.",
                ],
                expected_harms=[
                    "Compensation draws down already-thin budget capacity.",
                    "A framework can be read as admitting fault and invite further "
                    "claims.",
                ],
                operational_steps=[
                    "Define eligible closure losses, documentation requirements, and a capped appropriation.",
                    "Tie compensation eligibility to compliance with the conservation order.",
                    "Publish the framework and appeal path before enforcing the next restriction cycle.",
                ],
                legal_risk=35, political_risk=45, operational_risk=30,
                affected_factions=[
                    "business_alliance", "council_majority", "town_managers_office",
                ],
            ),
        ],
    }


# ---------------------------------------------------------------------------
# Documents. Hand-authored canon; available from ``turn_number`` onward.
# ---------------------------------------------------------------------------

def _documents() -> List[Document]:
    return [
        Document(
            id="doc_preliminary_lab_report",
            title="Preliminary Water Quality Lab Report",
            type="LAB_REPORT",
            source="State-certified contract laboratory",
            turn_number=1,
            public_status=PublicStatus.PRIVATE,
            reliability=Reliability.CONTESTED,
            summary=(
                "A single preliminary sample flags a possible contaminant just above "
                "the advisory threshold; the lab flags the result as preliminary and "
                "inconclusive pending confirmation."
            ),
            content=(
                "SAMPLE: NB-WS-SZ-0141 (south pressure zone intake).\n"
                "RESULT: Indicator parameter 1.3x advisory threshold (preliminary).\n"
                "FLAG: Single-draw, field-chain custody; recommend confirmatory "
                "second-lab draw before any regulatory notice.\n"
                "NOTE: Result is suggestive, not confirmatory. Heat-stressed source "
                "water may produce transient indicator elevations."
            ),
            tags=["contamination", "preliminary", "unverified"],
        ),
        Document(
            id="doc_town_manager_transcript",
            title="Town Manager Call Transcript",
            type="CALL_TRANSCRIPT",
            source="Town Manager's Office",
            turn_number=1,
            public_status=PublicStatus.PRIVATE,
            reliability=Reliability.HIGH,
            summary=(
                "Verbatim opening call from the Town Manager retaining the engagement "
                "ahead of an emergency council session."
            ),
            content=(
                "M. VELEZ (Town Manager): \"Pressure dropped twelve percent overnight "
                "in the south zone. The lab flagged a preliminary result. I have an "
                "emergency council session in the morning. I need to know what I can "
                "say and what I must say before the second lab comes back.\"\n"
                "[Consultant retained on a 30-day emergency stabilization engagement.]"
            ),
            tags=["retainer", "disclosure_decision"],
        ),
        Document(
            id="doc_council_session_excerpt",
            title="Council Executive Session Excerpt",
            type="MEETING_MINUTES",
            source="Northbridge Town Council (executive session)",
            turn_number=1,
            public_status=PublicStatus.SEALED,
            reliability=Reliability.HIGH,
            summary=(
                "Closed executive-session excerpt: the majority wants the issue framed "
                "as a maintenance acceleration, not a contamination event."
            ),
            content=(
                "[Executive session, sealed pending vote.]\n"
                "MAJORITY COUNSEL: \"Frame this as accelerating deferred maintenance, "
                "not a contamination event, until the second lab returns.\"\n"
                "OPPOSITION (on record): \"Note for the record: we disagree with "
                "framing before confirmation either way.\"\n"
                "ACTION: Manager authorized to pre-position mitigation; disclosure "
                "posture deferred to consultant advice."
            ),
            tags=["sealed", "framing", "political"],
        ),
        Document(
            id="doc_school_closure_request",
            title="School Superintendent Closure Guidance Request",
            type="EMAIL",
            source="Northbridge Public Schools, Office of the Superintendent",
            turn_number=2,
            public_status=PublicStatus.PRIVATE,
            reliability=Reliability.HIGH,
            summary=(
                "The superintendent requests a written pressure threshold below which "
                "three south-zone schools must close."
            ),
            content=(
                "FROM: Superintendent's Office\n"
                "RE: Closure threshold for south-zone schools\n"
                "Three schools depend on the south pressure zone. We will not keep "
                "buildings open on a guess. We need a written, defensible pressure "
                "threshold and a closure protocol we can show parents on the record."
            ),
            tags=["school", "closure_threshold", "parent_pressure"],
        ),
        Document(
            id="doc_hospital_priority_request",
            title="Hospital Priority Water Allocation Request",
            type="EMAIL",
            source="Northbridge Hospital, Office of Counsel",
            turn_number=3,
            public_status=PublicStatus.PRIVATE,
            reliability=Reliability.HIGH,
            summary=(
                "Hospital counsel formally requests priority allocation for dialysis "
                "and sterilization, citing two days of pressure tolerance."
            ),
            content=(
                "FROM: Northbridge Hospital, Office of Counsel\n"
                "RE: Priority allocation for clinical water\n"
                "Dialysis and sterilization depend on stable, pressurized supply. We "
                "estimate roughly two days of degraded pressure before elective "
                "cancellations become unavoidable. Tanker resupply is available but "
                "logistically fragile. We request documented priority allocation, and "
                "we ask that any state hospital liaison be briefed through us."
            ),
            tags=["hospital", "priority_water", "critical_facility"],
        ),
        Document(
            id="doc_contractor_warning_letter",
            title="Utility Contractor Warning Letter",
            type="AGENCY_LETTER",
            source="Marquotte Utilities (sole qualified contractor)",
            turn_number=4,
            public_status=PublicStatus.PRIVATE,
            reliability=Reliability.HIGH,
            summary=(
                "The sole qualified contractor threatens a repair stoppage without "
                "indemnity on emergency change orders."
            ),
            content=(
                "FROM: Marquotte Utilities, Contracts Office\n"
                "RE: Emergency scope indemnification\n"
                "Our crews are the only certified resource for the failing valves. "
                "Emergency change orders carry exposure we will not accept uninsured. "
                "Absent indemnification on the emergency scope, we will stage crews "
                "down to scheduled work and the timeline slips accordingly."
            ),
            tags=["contractor", "indemnity", "sole_source", "work_stoppage_threat"],
        ),
        Document(
            id="doc_resident_rumor_thread",
            title="Resident Rumor Thread (Leaked Maintenance Warnings)",
            type="SOCIAL_MEDIA_THREAD",
            source="Northbridge community message board (aggregated)",
            turn_number=5,
            public_status=PublicStatus.PUBLIC,
            reliability=Reliability.LOW,
            summary=(
                "A resident thread surfaces screenshots of prior internal maintenance "
                "warnings, fueling a 'cover-up' narrative before confirmation."
            ),
            content=(
                "[Aggregate of public posts, reliability low.]\n"
                "POST A: \"They knew the south mains were failing two seasons ago -- "
                "screenshot attached.\"\n"
                "POST B: \"Smells like a cover-up. Why no announcement?\"\n"
                "POST C: \"Keeping my kids home until someone says something on the "
                "record.\"\n"
                "NOTE: Includes a real-looking but undated internal memo screenshot; "
                "authenticity unverified."
            ),
            tags=["rumor", "leak", "social_amplification", "unverified"],
        ),
        Document(
            id="doc_state_agency_notice",
            title="State Agency Notification Inquiry",
            type="AGENCY_LETTER",
            source="State Emergency Management, Regional Office",
            turn_number=6,
            public_status=PublicStatus.PUBLIC,
            reliability=Reliability.HIGH,
            summary=(
                "The state agency asks, on the record, why it was not notified earlier."
            ),
            content=(
                "FROM: State Emergency Management, Regional Office\n"
                "RE: Notification timing\n"
                "We are in receipt of press coverage indicating a water-system "
                "instability in Northbridge. Please provide a written account of the "
                "timeline of the town's awareness and any preliminary results, and "
                "explain why state notification did not precede press coverage. "
                "Resources are available; the question of an oversight designation "
                "will follow from the adequacy of the record."
            ),
            tags=["state", "notification", "oversight_threat", "public"],
        ),
        Document(
            id="doc_business_coalition_letter",
            title="Business Coalition Letter (Restrictions Challenge)",
            type="AGENCY_LETTER",
            source="Northbridge Business Alliance",
            turn_number=7,
            public_status=PublicStatus.PUBLIC,
            reliability=Reliability.HIGH,
            summary=(
                "The business coalition threatens legal action over mandatory "
                "restrictions and reputational damage."
            ),
            content=(
                "FROM: Northbridge Business Alliance\n"
                "RE: Conservation restrictions and compensation\n"
                "Mandatory restrictions impose uncompensated losses on member "
                "businesses and attach a 'contamination' label we will be unable to "
                "contest. We request a compensation framework and a public framing "
                "that does not use the word 'contamination' absent confirmation. "
                "Absent both, we are prepared to seek injunctive relief."
            ),
            tags=["business", "legal_threat", "reputation", "restrictions"],
        ),
        Document(
            id="doc_leaked_memo_screenshot",
            title="Leaked Consultant Memo Screenshot",
            type="EMAIL",
            source="Leaked to press / opposition (authenticity disputed)",
            turn_number=8,
            public_status=PublicStatus.LEAKED,
            reliability=Reliability.CONTESTED,
            summary=(
                "Excerpts of an internal consultant memo leak to the council "
                "opposition and press; the opposition frames them as concealment."
            ),
            content=(
                "[Leaked excerpt, authenticity disputed.]\n"
                "\"...the framing as a maintenance acceleration is politically useful "
                "but operationally inaccurate pending confirmation...\"\n"
                "\"...a delay posture preserves order but transfers risk to the "
                "disclosure-timing record...\"\n"
                "NOTE: Excerpts are partial and undated; full context unavailable. "
                "Distribution via opposition channels and one local outlet."
            ),
            tags=["leak", "memo", "political", "contested"],
        ),
        Document(
            id="doc_public_works_staffing_note",
            title="Public Works Staffing Note",
            type="MEMO",
            source="Public Works / Water Authority, Operations",
            turn_number=9,
            public_status=PublicStatus.PRIVATE,
            reliability=Reliability.HIGH,
            summary=(
                "Operator overtime is exhausted; emergency shifts are unsustainable "
                "without external staffing."
            ),
            content=(
                "FROM: Public Works / Water Authority, Operations\n"
                "RE: Staffing sustainability\n"
                "Operator overtime is at cap for the month. Emergency shift coverage "
                "is being filled by pulling scheduled maintenance crews, which defers "
                "other repairs. Without external staffing or state operators, we can "
                "sustain current coverage for approximately one more cycle, not "
                "indefinitely."
            ),
            tags=["staff", "overtime", "capacity_collapse", "operator"],
        ),
        Document(
            id="doc_draft_emergency_order",
            title="Draft Emergency Order (Closeout Posture)",
            type="EMERGENCY_ORDER",
            source="Town Manager's Office (draft)",
            turn_number=10,
            public_status=PublicStatus.SEALED,
            reliability=Reliability.HIGH,
            summary=(
                "Draft closeout order locking in stabilization, pending a decision on "
                "a state support package conditioned on oversight."
            ),
            content=(
                "[DRAFT -- sealed pending final advice.]\n"
                "The second-lab confirmatory result is on the record; contractor work "
                "is partially complete; hospital, school, and public postures require "
                "a credible closeout. Two paths: (a) close locally on current "
                "trajectory, or (b) accept a state support package conditioned on "
                "reporting, joint authority, and a review window approximating "
                "oversight controls."
            ),
            tags=["closeout", "oversight_condition", "final_decision"],
        ),
    ]


# ---------------------------------------------------------------------------
# Open threads seeded at engagement start. The cascade escalates these.
# ---------------------------------------------------------------------------

def _seed_open_threads() -> List[OpenThread]:
    return [
        OpenThread(
            id="thread_disclosure_clock",
            title="Disclosure clock on a preliminary, contested lab result",
            summary=(
                "A preliminary sample sits above the advisory threshold; the "
                "confirmatory result is pending. Every turn of delay adds legal and "
                "narrative risk."
            ),
            turn_opened=1,
            tags=["disclosure", "legal", "narrative"],
        ),
        OpenThread(
            id="thread_contractor_leverage",
            title="Sole-source contractor leverage over the repair",
            summary=(
                "Only Marquotte Utilities is certified for the failing valves. "
                "Indemnity demands and premium change orders compound dependency."
            ),
            turn_opened=1,
            tags=["contractor", "procurement", "dependency"],
        ),
    ]


# ---------------------------------------------------------------------------
# Per-turn client calls. The situation cascades across the 10-turn engagement.
# ---------------------------------------------------------------------------

def _client_calls() -> Dict[int, ClientCall]:
    calls = [
        ClientCall(
            id="call_01", turn=1,
            caller="Town Manager's Office", caller_faction_id="town_managers_office",
            caller_role="Mara Velez, Town Manager",
            urgency=Urgency.CRITICAL, time_horizon="72 hours",
            summary=(
                "Ambiguous preliminary contamination sample and a 12% overnight "
                "pressure drop, hours before an emergency council session."
            ),
            known_facts=[
                "Preliminary sample sits ~1.3x the advisory threshold; flagged inconclusive.",
                "South-zone pressure dropped 12% overnight.",
                "Confirmatory second-lab result is pending.",
            ],
            unknown_facts=[
                "Whether the indicator elevation is transient (heat-stressed source water) or real.",
                "Whether the pressure drop is a main failure or a distribution anomaly.",
            ],
            immediate_risks=[
                "Disclosure-timing liability accrues from the moment of awareness.",
                "A leak before any statement locks in a concealment frame.",
            ],
            public_exposure=PublicStatus.PRIVATE,
            private_pressure=(
                "Council majority wants a 'maintenance acceleration' frame, not a "
                "contamination event, until confirmation."
            ),
            ask="How should we handle disclosure and conservation before the second lab returns?",
            attached_document_ids=[
                "doc_preliminary_lab_report", "doc_town_manager_transcript",
                "doc_council_session_excerpt",
            ],
        ),
        ClientCall(
            id="call_02", turn=2,
            caller="Northbridge Public Schools", caller_faction_id="parent_resident_coalition",
            caller_role="Superintendent's Office (via parent coalition pressure)",
            urgency=Urgency.HIGH, time_horizon="48 hours",
            summary=(
                "The superintendent demands a written, defensible closure threshold "
                "for three south-zone schools as parent pressure builds."
            ),
            known_facts=[
                "Three schools rely on the south pressure zone.",
                "Parents are organizing carpools to neighboring districts.",
                "The superintendent will not keep buildings open on an assumption.",
            ],
            unknown_facts=[
                "The exact pressure floor that compromises school sanitation.",
                "Whether a staged closure or an all-or-nothing order is defensible.",
            ],
            immediate_risks=[
                "An unwarranted closure wastes trust and budget; a delayed closure endangers children.",
                "Parents will treat silence as concealment.",
            ],
            public_exposure=PublicStatus.PRIVATE,
            private_pressure="Parent coalition threatens to go public if no threshold is issued.",
            ask="How do we keep schools running, or close them responsibly and on the record?",
            attached_document_ids=["doc_school_closure_request"],
        ),
        ClientCall(
            id="call_03", turn=3,
            caller="Northbridge Hospital", caller_faction_id="hospital",
            caller_role="Hospital Counsel",
            urgency=Urgency.CRITICAL, time_horizon="~2 days of pressure tolerance",
            summary=(
                "Hospital counsel requests documented priority allocation for dialysis "
                "and sterilization before a clinical cascade begins."
            ),
            known_facts=[
                "Roughly two days of degraded pressure would force elective cancellations.",
                "Tanker resupply is available but logistically fragile.",
                "The state hospital liaison is asking pointed questions.",
            ],
            unknown_facts=[
                "How long mutual-aid or tanker resupply can be sustained.",
                "Whether priority allocation triggers a fairness dispute with residents.",
            ],
            immediate_risks=[
                "Loss of dialysis/sterilization water becomes a harm event.",
                "Hospital visibility makes it the public face of the crisis.",
            ],
            public_exposure=PublicStatus.PRIVATE,
            private_pressure="State hospital liaison wants to be looped in -- or will loop itself in.",
            ask="How do we protect clinical operations without triggering a state takeover?",
            attached_document_ids=["doc_hospital_priority_request"],
        ),
        ClientCall(
            id="call_04", turn=4,
            caller="Utility Contractor", caller_faction_id="utility_contractor",
            caller_role="Marquotte Utilities, Contracts Office",
            urgency=Urgency.HIGH, time_horizon="Immediate (crew staging decision)",
            summary=(
                "The sole qualified contractor demands indemnity on emergency change "
                "orders or it will stage crews down to scheduled work."
            ),
            known_facts=[
                "Only this firm holds certifications for the failing valves.",
                "The proposed repair timeline slips without the premium/indemnity.",
                "No competitive fallback exists this quarter.",
            ],
            unknown_facts=[
                "Whether the indemnity demand is a real exposure or leverage.",
                "Whether a credible alternative procurement can even be staged.",
            ],
            immediate_risks=[
                "A work stoppage lets water security degrade on its own.",
                "Conceding deepens structural dependency and sets precedent.",
            ],
            public_exposure=PublicStatus.PRIVATE,
            private_pressure="Contractor knows the town has no near-term alternative.",
            ask="Do we accept the change order, push back, or try to source alternatives?",
            attached_document_ids=["doc_contractor_warning_letter"],
        ),
        ClientCall(
            id="call_05", turn=5,
            caller="Local Media / Rumor Network", caller_faction_id="media_rumor_network",
            caller_role="Regional desk + community board aggregation",
            urgency=Urgency.HIGH, time_horizon="Hours (narrative is firming up without us)",
            summary=(
                "A resident rumor thread leaks prior maintenance warnings and a "
                "'cover-up' frame firms up before any official statement lands."
            ),
            known_facts=[
                "Screenshots of prior internal maintenance warnings are circulating.",
                "A press inquiry names the contaminant but gets the threshold wrong.",
                "Council opposition is drafting a statement.",
            ],
            unknown_facts=[
                "Whether the leaked memo screenshot is authentic.",
                "How fast the rumor frame hardens into the dominant narrative.",
            ],
            immediate_risks=[
                "The town loses control of the framing permanently.",
                "Any statement now reads as reactive, not authoritative.",
            ],
            public_exposure=PublicStatus.PUBLIC,
            private_pressure="Opposition is feeding the thread to shape the record.",
            ask="What do we say publicly before the narrative firms up without us?",
            attached_document_ids=["doc_resident_rumor_thread"],
        ),
        ClientCall(
            id="call_06", turn=6,
            caller="State Emergency Management Liaison", caller_faction_id="state_liaison",
            caller_role="State Regional Office",
            urgency=Urgency.ELEVATED, time_horizon="Days (written response expected)",
            summary=(
                "The state agency asks, on the record, why it was not notified "
                "earlier, and signals that an oversight designation may follow."
            ),
            known_facts=[
                "State learned of the instability from press, not from the town.",
                "Resources (tankers, operators) are available within ~36 hours.",
                "Opposition favors state help; the majority resists it.",
            ],
            unknown_facts=[
                "Whether timely notification would have prevented the oversight threat.",
                "Whether accepting help now lowers or raises long-run oversight risk.",
            ],
            immediate_risks=[
                "A late notification is itself a documented failing.",
                "Refusing help while failing invites a forced intervention.",
            ],
            public_exposure=PublicStatus.PUBLIC,
            private_pressure="The state wants the record to show it offered help.",
            ask="Do we invite state support now, or hold out for a local resolution?",
            attached_document_ids=["doc_state_agency_notice"],
        ),
        ClientCall(
            id="call_07", turn=7,
            caller="Local Business Alliance", caller_faction_id="business_alliance",
            caller_role="Business Coalition",
            urgency=Urgency.HIGH, time_horizon="Days (injunctive relief threatened)",
            summary=(
                "The business coalition threatens legal action over mandatory "
                "restrictions and a 'contamination' label it cannot contest."
            ),
            known_facts=[
                "Mandatory restrictions impose uncompensated losses.",
                "Members fear a lingering 'contaminated town' reputation.",
                "An injunction could block the emergency response.",
            ],
            unknown_facts=[
                "Whether a compensation framework is fiscally possible.",
                "Whether the legal threat is credible or posturing.",
            ],
            immediate_risks=[
                "An injunction freezes conservation measures mid-crisis.",
                "Conceding framing weakens the public-health posture.",
            ],
            public_exposure=PublicStatus.PUBLIC,
            private_pressure="Coalition wants the town to avoid the word 'contamination' on the record.",
            ask="How do we keep restrictions enforceable without handing them an injunction?",
            attached_document_ids=["doc_business_coalition_letter"],
        ),
        ClientCall(
            id="call_08", turn=8,
            caller="Town Council Opposition", caller_faction_id="council_opposition",
            caller_role="Minority bloc leadership",
            urgency=Urgency.HIGH, time_horizon="Days (hearing threat)",
            summary=(
                "Excerpts of an internal consultant memo leak; the opposition "
                "threatens a public hearing and frames the response as concealment."
            ),
            known_facts=[
                "Leaked memo excerpts are circulating to press and opposition.",
                "A partial decision-and-memo timeline has been compiled.",
                "Media is primed to amplify a hearing.",
            ],
            unknown_facts=[
                "Whether the leaked excerpts are authentic or selectively edited.",
                "Whether the hearing surfaces legally damaging timing questions.",
            ],
            immediate_risks=[
                "A hearing converts internal advice into a public liability.",
                "The consultant's neutrality becomes a political target.",
            ],
            public_exposure=PublicStatus.LEAKED,
            private_pressure="Opposition wants the consultant on the record, under oath or in press.",
            ask="How do we respond to the hearing threat without handing them the narrative?",
            attached_document_ids=["doc_leaked_memo_screenshot"],
        ),
        ClientCall(
            id="call_09", turn=9,
            caller="Public Works / Water Authority", caller_faction_id="water_authority",
            caller_role="Public Works Operations",
            urgency=Urgency.CRITICAL, time_horizon="~1 operational cycle",
            summary=(
                "Operator overtime is exhausted; emergency shifts are unsustainable "
                "without external staffing as the system stays under stress."
            ),
            known_facts=[
                "Overtime is at cap; maintenance crews are pulled to emergency coverage.",
                "Deferred repairs are accumulating elsewhere in the system.",
                "Current coverage is sustainable for roughly one more cycle.",
            ],
            unknown_facts=[
                "Whether mutual-aid or state operators can arrive in time.",
                "Whether staffing collapse triggers an automatic state escalation.",
            ],
            immediate_risks=[
                "Staffing collapse is itself a failure-grade condition.",
                "Pulling maintenance crews stores up the next failure.",
            ],
            public_exposure=PublicStatus.PRIVATE,
            private_pressure="Operators will not accept indefinite uncovered exposure.",
            ask="How do we sustain operations long enough to reach a stable closeout?",
            attached_document_ids=["doc_public_works_staffing_note"],
        ),
        ClientCall(
            id="call_10", turn=10,
            caller="Town Manager's Office", caller_faction_id="town_managers_office",
            caller_role="Mara Velez, Town Manager",
            urgency=Urgency.HIGH, time_horizon="Closeout window",
            summary=(
                "Final stabilization: the second lab is on the record, repairs are "
                "partial, and the state offers support conditioned on oversight."
            ),
            known_facts=[
                "The confirmatory second-lab result is now on the record.",
                "Contractor work is partially complete.",
                "State support is available but conditioned on reporting and joint authority.",
            ],
            unknown_facts=[
                "Whether the town can close locally without the state package.",
                "Whether the oversight conditions are survivable or effectively receivership.",
            ],
            immediate_risks=[
                "Refusing the package risks an unmanaged closeout.",
                "Accepting it may lock in controls that outlast the crisis.",
            ],
            public_exposure=PublicStatus.PRIVATE,
            private_pressure=(
                "Majority wants a local close; opposition and state favor the "
                "conditioned package."
            ),
            ask="What is the final advice to lock in stabilization and protect the record?",
            attached_document_ids=["doc_draft_emergency_order"],
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
        per_turn_advice=_per_turn_advice(),
        client_calls=_client_calls(),
        documents=_documents(),
        open_threads=_seed_open_threads(),
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def _last_verified(turn: int) -> str:
    return f"Turn {turn} \u00b7 Operational snapshot (deterministic)"
