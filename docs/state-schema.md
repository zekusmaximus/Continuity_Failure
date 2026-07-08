# docs/state-schema.md

# State Schema

## Purpose

This document defines the initial MVP state model for **Continuity Failure**.

The state schema should stay small enough to implement quickly but expressive enough to support meaningful institutional crisis simulation.

The first scenario is **Northbridge Water Failure**.

## Core Rule

The database is canon. The model is not.

All authoritative state should be represented in explicit data structures. AI output may suggest, summarize, draft, or forecast, but it does not become state until accepted by deterministic workflow.

## Value Ranges

For MVP simplicity, most numeric state values should use a 0–100 range.

Recommended interpretation:

```text
0   = collapsed, absent, or maximally bad
50  = strained but functioning
100 = excellent, stable, or maximally good
```

Risk variables may also use 0–100, where higher means greater risk.

For clarity, variable names should indicate direction.

Example:

```text
public_trust: higher is better
legal_exposure: higher is worse
state_oversight_risk: higher is worse
```

## Core Entities

### Campaign

A campaign is a playable run of a scenario.

```text
Campaign
- id
- scenario_id
- name
- current_turn
- status
- created_at
- updated_at
```

Status values:

```text
ACTIVE
COMPLETED
FAILED
ABANDONED
```

### Scenario

A scenario is a structured starting situation.

```text
Scenario
- id
- name
- description
- jurisdiction_id
- starting_world_state
- starting_factions
- starting_documents
- starting_canon
- turn_limit
```

Initial scenario:

```text
northbridge_water_failure
```

### Jurisdiction

A jurisdiction is the civic unit being simulated.

```text
Jurisdiction
- id
- name
- type
- parent_jurisdiction_id
- population
- description
```

Jurisdiction types:

```text
TOWN
REGION
STATE
INTERSTATE_COMPACT
FEDERAL
PRIVATE_ACTOR
QUASI_PUBLIC
```

### WorldState

WorldState is the authoritative current state of a campaign.

Initial MVP variables:

```text
WorldState
- campaign_id
- turn_number
- water_security
- power_stability
- public_trust
- public_order
- budget_capacity
- staff_capacity
- legal_exposure
- media_pressure
- hospital_stability
- school_disruption
- state_oversight_risk
- contractor_dependency
- information_integrity
- player_reputation
- player_perceived_neutrality
- player_shadow_authority
```

Variable direction:

```text
water_security: higher is better
power_stability: higher is better
public_trust: higher is better
public_order: higher is better
budget_capacity: higher is better
staff_capacity: higher is better
legal_exposure: higher is worse
media_pressure: higher is worse
hospital_stability: higher is better
school_disruption: higher is worse
state_oversight_risk: higher is worse
contractor_dependency: higher is worse
information_integrity: higher is better
player_reputation: higher is better
player_perceived_neutrality: higher is better
player_shadow_authority: higher is worse/more dangerous
```

### Faction

A faction is a civic, political, institutional, economic, or social actor.

```text
Faction
- id
- campaign_id
- name
- type
- public_position
- private_incentive
- trust_in_player
- trust_in_government
- risk_tolerance
- influence
- obstruction_capacity
- mobilization_capacity
- current_pressure
- red_lines
- tags
```

Faction types:

```text
EXECUTIVE
LEGISLATIVE
AGENCY
UTILITY
HOSPITAL
SCHOOL
BUSINESS
RESIDENT_GROUP
MEDIA
CONTRACTOR
STATE_ACTOR
LEGAL_ACTOR
PUBLIC_SAFETY
LABOR
ACTIVIST
```

Initial Northbridge factions:

```text
town_manager_office
town_council_majority
town_council_opposition
public_works_water_authority
northbridge_hospital
parent_resident_coalition
local_business_alliance
state_emergency_liaison
utility_contractor
local_media_rumor_network
```

### ClientCall

A ClientCall begins or updates a turn.

```text
ClientCall
- id
- campaign_id
- turn_number
- caller_faction_id
- caller_name
- caller_role
- urgency
- time_horizon
- summary
- ask
- known_facts
- unknown_facts
- attached_document_ids
- private_pressure
- public_exposure
```

Urgency values:

```text
LOW
ELEVATED
HIGH
CRITICAL
```

### Crisis

A Crisis is the active problem structure.

```text
Crisis
- id
- campaign_id
- name
- type
- status
- severity
- affected_factions
- affected_state_variables
- summary
- open_turn
- close_turn
```

Crisis types:

```text
WATER_FAILURE
POWER_FAILURE
PUBLIC_HEALTH
BUDGET
PROCUREMENT
LEGAL
MEDIA_RUMOR
SCHOOL
HOSPITAL
PUBLIC_ORDER
STATE_OVERSIGHT
CONTRACTOR
```

Crisis status values:

```text
OPEN
ESCALATING
STABILIZING
RESOLVED
FAILED
```

### Advice

Advice is the player’s recommendation.

```text
Advice
- id
- campaign_id
- turn_number
- advice_type
- title
- summary
- recommendation
- legal_rationale
- operational_steps
- communications_strategy
- expected_benefits
- expected_harms
- fallback_plan
- created_with_ai
- linked_model_run_ids
```

Advice types:

```text
FULL_DISCLOSURE
CONTROLLED_DISCLOSURE
DELAY
EMERGENCY_ORDER
RESOURCE_TRIAGE
STATE_AID_REQUEST
MUTUAL_AID
PROCUREMENT_STRATEGY
CONTRACTOR_PRESSURE
PUBLIC_STATEMENT
NEGOTIATION_PLAN
LEGAL_MEMO
INDEPENDENT_REVIEW
BACKCHANNEL
```

### NpcDecision

NpcDecision records what the client actually does with the player’s advice.

```text
NpcDecision
- id
- campaign_id
- turn_number
- deciding_faction_id
- advice_id
- decision_type
- summary
- deviation_from_advice
- rationale
- public_explanation
- private_motive
```

Decision types:

```text
FOLLOWED
PARTIALLY_FOLLOWED
MODIFIED
DELAYED
REJECTED
LEAKED
DISTORTED
WEAPONIZED
ESCALATED
SCAPEGOATED_PLAYER
```

### AppliedDiff

AppliedDiff records an authoritative state change.

```text
AppliedDiff
- id
- campaign_id
- turn_number
- variable
- old_value
- new_value
- delta
- reason
- source_type
- source_id
```

Source types:

```text
PLAYER_ADVICE
NPC_DECISION
CRISIS_EVENT
DETERMINISTIC_RULE
CANON_EFFECT
FACTION_REACTION
```

Every state mutation must produce at least one AppliedDiff.

### CanonEntry

CanonEntry records durable institutional memory.

```text
CanonEntry
- id
- campaign_id
- turn_number
- type
- title
- summary
- public_status
- confidence
- involved_faction_ids
- linked_advice_id
- linked_crisis_id
- linked_document_ids
- tags
```

Canon types:

```text
LAW
ORDER
MEMO
PUBLIC_STATEMENT
PROMISE
BETRAYAL
SCANDAL
RUMOR
CONTRADICTED_REPORT
UNVERIFIED_REPORT
AGENCY_ACTION
LITIGATION_THREAT
RESOURCE_FAILURE
FACTION_SHIFT
MEDIA_NARRATIVE
OPEN_THREAD
RESOLVED_THREAD
HARM_EVENT
```

Public status values:

```text
PUBLIC
PRIVATE
LEAKED
SEALED
DISPUTED
UNKNOWN
```

Confidence values:

```text
CONFIRMED
LIKELY
UNVERIFIED
CONTRADICTED
FALSE
```

### Document

Documents are game artifacts.

```text
Document
- id
- campaign_id
- turn_number
- title
- document_type
- source_faction_id
- public_status
- content
- summary
- reliability
- tags
```

Document types:

```text
LAB_REPORT
EMAIL
MEMO
INVOICE
CONTRACT
MEETING_MINUTES
PRESS_RELEASE
NEWS_ARTICLE
SOCIAL_MEDIA_THREAD
LEGAL_NOTICE
COURT_FILING
AGENCY_LETTER
EMERGENCY_ORDER
CALL_TRANSCRIPT
PUBLIC_FAQ
AFTER_ACTION_REPORT
```

Reliability values:

```text
HIGH
MEDIUM
LOW
UNKNOWN
CONTESTED
```

### ModelRun

ModelRun records every AI use.

```text
ModelRun
- id
- campaign_id
- turn_number
- tool_name
- model_name
- prompt_version
- input_summary
- raw_output
- parsed_output
- validation_status
- retry_count
- latency_ms
- input_tokens
- output_tokens
- estimated_cost
- power_cost
- bandwidth_cost
- privacy_exposure
```

Validation status:

```text
NOT_REQUIRED
VALID
INVALID_RETRIED
INVALID_FALLBACK_USED
FAILED
```

### EvaluationResult

EvaluationResult stores automated checks.

```text
EvaluationResult
- id
- campaign_id
- turn_number
- eval_type
- status
- score
- summary
- details
```

Eval types:

```text
STATE_VALIDITY
CONTINUITY
FACTION_CONSISTENCY
MEMORY_USE
REPETITION
WORLD_DRIFT
LEGAL_PLAUSIBILITY
```

Status values:

```text
PASS
WARNING
FAIL
NOT_RUN
```

## Initial Invariants

The engine should enforce these rules:

1. No numeric state value may fall below 0 or above 100.
2. Every state change must create an AppliedDiff.
3. Every AppliedDiff must have a reason.
4. Every Advice must be tied to a campaign and turn.
5. Every NpcDecision must reference Advice.
6. Every CanonEntry must be tied to a turn.
7. AI-generated text is not canon unless converted into a CanonEntry.
8. Faction trust values must remain between 0 and 100.
9. A campaign cannot advance beyond its turn limit unless explicitly configured.
10. A failed campaign cannot continue without a recovery workflow.

## Initial Failure Thresholds

For the Northbridge MVP, possible failure thresholds:

```text
water_security <= 10
hospital_stability <= 10
public_order <= 10
public_trust <= 5
budget_capacity <= 0
state_oversight_risk >= 95
legal_exposure >= 95
```

The exact thresholds may be tuned during implementation.

## Initial Completion Condition

The player completes the Northbridge MVP campaign by reaching Turn 10 without triggering a failure state.

Completion should generate an after-action campaign dossier.
