# Project Spec: Continuity Failure

> **Implementation status (this branch).** This spec describes the intended
> product. Against the working code:
> - **Implemented now:** the deterministic Northbridge 10-turn loop — client
>   calls (with caller role, urgency, horizon, known/unknown facts, immediate
>   risks, public exposure), an Evidence Board with 12 documents, advice
>   selection with surfaced tradeoffs, NPC decisions with visible mediation,
>   deterministic consequence stacks, applied diffs, canon entries, open threads,
>   campaign completion/failure, the Continuity Desk web UI, and a Markdown
>   campaign dossier export.
> - **Planned next:** the remaining read-only AI-assist tools (research console,
>   faction-reaction / press / canon-summary generators) behind the validation
>   boundary already in place, plus in-world tool costs and durable persistence.
> - **Out of scope for this MVP:** the in-world AI tools beyond the memo
>   drafter (local/cloud/archive/legal/rumor/scenario models), AI resource
>   costs, power/comms degradation beyond the derived system-status indicator,
>   and town→state→interstate progression. The memo drafter itself is
>   implemented (off by default, validation-gated, deterministic fallback).

## One-Sentence Pitch

**Continuity Failure** is a near-future civic breakdown simulator where the player runs a crisis-governance consulting firm called into failing institutions as towns, agencies, utilities, hospitals, and regional governments lose the capacity to manage cascading emergencies.

## Player Role

The player is a consultant, not a ruler.

The player advises institutions through:

* legal risk memos;
* emergency authority analysis;
* public communications;
* resource triage;
* procurement strategy;
* negotiation plans;
* faction management;
* scenario forecasting;
* after-action analysis;
* continuity planning.

The player’s influence is powerful but indirect. Clients may accept, modify, reject, leak, ignore, or weaponize the advice.

## Core Theme

The game is about the collapse of institutional capacity under conditions of legal ambiguity, resource scarcity, technological dependency, public distrust, and compounding infrastructure failure.

The central moral tension:

> The more society fails, the more valuable the player becomes.

The player may preserve institutions, profit from collapse, become indispensable, create dependency, or quietly become an unelected operating layer beneath formal government.

## MVP Scenario: Northbridge Water Failure

### Setting

Northbridge is a fictional mid-sized Connecticut town in the early 2030s.

It is prosperous enough to have expectations, old enough to have deferred infrastructure, and politically divided enough that every emergency decision becomes contested.

### Initial Situation

Northbridge faces a water-system crisis involving:

* preliminary contamination data;
* aging water infrastructure;
* repeated heat waves;
* contractor disputes;
* school closure pressure;
* hospital vulnerability;
* public rumor;
* budget exhaustion;
* council factionalism;
* state agency delay;
* possible emergency procurement issues.

### Initial Client

The Northbridge town manager calls the player before an emergency council meeting.

The immediate question:

> Should the town disclose preliminary contamination risk, delay until confirmation, request state intervention, impose conservation measures, prioritize critical facilities, or attempt quiet mitigation?

### MVP Campaign Length

The MVP scenario lasts 10 turns.

Each turn represents roughly 3 days.

The full MVP campaign covers approximately 30 days.

## Primary Gameplay Loop

1. **Incoming Call**

   * A client presents an urgent situation.

2. **Situation Brief**

   * The player receives known facts, unknown facts, time pressure, legal context, faction pressure, and available documents.

3. **Investigation**

   * The player reviews documents, prior commitments, faction positions, resource levels, public sentiment, and relevant authority.

4. **Optional AI Use**

   * The player may use AI tools for legal research, document review, rumor analysis, memo drafting, or scenario forecasting.
   * AI tools consume limited resources and may create privacy, cost, power, or political risks.

5. **Advice**

   * The player issues a recommendation, memo, statement, order, negotiation plan, or triage framework.

6. **NPC Decision**

   * The client decides how to use the advice.

7. **Resolution**

   * The deterministic engine applies consequences to world state.

8. **Aftermath**

   * Factions, press, agencies, lawyers, residents, contractors, and other actors respond.

9. **Canon Update**

   * Durable facts, promises, scandals, laws, and unresolved risks are stored.

10. **Next Turn**

* New crises emerge from prior consequences.

## MVP Resources

Northbridge should begin with a small number of core state variables:

* water security;
* power stability;
* public trust;
* public order;
* budget capacity;
* staff capacity;
* legal exposure;
* media pressure;
* hospital stability;
* school disruption;
* state oversight risk;
* contractor dependency.

## MVP Factions

Initial factions:

1. Town Manager’s Office.
2. Town Council Majority.
3. Town Council Opposition.
4. Public Works / Water Authority.
5. Northbridge Hospital.
6. Parent and Resident Coalition.
7. Local Business Alliance.
8. State Emergency Management Liaison.
9. Utility Contractor.
10. Local Media / Rumor Network.

Each faction should have:

* public position;
* private incentives;
* trust in player;
* trust in town government;
* risk tolerance;
* resources;
* red lines;
* memory of promises or betrayals.

## Advice Types

Initial advice categories:

* full disclosure;
* controlled disclosure;
* delay pending confirmation;
* emergency conservation order;
* hospital/school prioritization;
* request state support;
* regional mutual aid;
* contractor pressure strategy;
* public communications plan;
* legal-risk-minimized emergency order;
* independent review;
* quiet backchannel negotiation.

Every advice option should have tradeoffs. No option should be purely correct.

## AI Tooling as In-World Mechanic

The player’s consulting firm has access to several AI systems.

### Local Model

Private and resilient, but weaker and possibly stale.

### Cloud Frontier Model

Strongest research and synthesis, but requires power, bandwidth, money, and creates confidentiality/political exposure.

### Municipal Archive Model

Useful for local records, minutes, ordinances, and prior commitments, but limited by incomplete or badly maintained records.

### Legal Retrieval System

Finds authority, procedures, emergency powers, procurement rules, notice obligations, and litigation risks.

### Rumor Classifier

Tracks public narratives and misinformation but can be poisoned by partial or manipulated feeds.

### Scenario Simulator

Projects consequences of possible advice, but its projections are only forecasts, not truth.

## Compute and Power Constraints

AI use should cost in-world resources:

* power;
* bandwidth;
* cloud credits;
* time;
* privacy exposure;
* data freshness;
* political risk.

During infrastructure failures, AI access may degrade. The player may need to choose between live maps, cloud research, local inference, document processing, and communications.

## Canon Rules

Canon is stored in the database.

Canon may include:

* issued advice;
* client decisions;
* public statements;
* emergency orders;
* laws;
* lawsuits;
* scandals;
* promises;
* betrayals;
* faction shifts;
* unresolved risks;
* deaths or harms;
* media narratives;
* state/federal interventions.

Model-generated content is not canon until accepted by deterministic workflow.

## Desired UI Feel

The interface should feel like a professional crisis-consulting workstation used inside a failing society.

It should combine:

* emergency operations dashboard;
* municipal GIS;
* legal document review;
* public-sector case management;
* AI research console;
* institutional archive;
* consequence simulator;
* memo drafting system.

The UI should visually degrade as society and infrastructure degrade.

## MVP Deliverable

A successful MVP allows the player to:

* start the Northbridge Water Failure scenario;
* receive client calls;
* inspect crisis briefs and documents;
* use limited AI tools;
* issue advice;
* see client decisions;
* watch deterministic consequences unfold;
* review faction and media reactions;
* inspect state diffs;
* view canon history;
* complete a 10-turn campaign;
* export a basic campaign dossier.
