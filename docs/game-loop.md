# docs/game-loop.md

# Game Loop

> **Implementation status (this branch).** This document describes the intended
> full turn loop. Against the working code, the implemented phases are:
> **1 (Incoming Call)**, **2 (Situation Brief — crisis + known facts / unknowns /
> immediate risks / public exposure)**, **3 (Investigation — evidence board +
> factions + open threads)**, **5 (Advice — workbench with surfaced tradeoffs)**,
> **6 (NPC Decision — with visible mediation)**,
> **7 (Deterministic Resolution → applied diffs)**, **8 (Aftermath — deterministic
> consequence stack)**, and **9 (Canon + open-thread update)**, plus
> completion/failure and a Markdown dossier export.
> - **UI shape (as built):** the loop below is presented as a **guided intake
>   flow** — one screen per phase with a single primary action
>   (INTRO → CALL → BRIEF → EVIDENCE → ADVICE → CLIENT_DECISION → CONSEQUENCES →
>   ARCHIVE → next call / DOSSIER), not a single all-at-once dashboard. The
>   backend still resolves the NPC decision and consequences together on advice
>   submission; the frontend stores that one result and reveals it across the
>   client-decision, consequences, and archive phases. Dense views (full state,
>   factions, canon, timeline, raw diffs, model runs, dossier) live in an
>   on-demand Case File.
> - **Memo workflow (as built):** the Advice phase exposes a persistent
>   workbench (`GET/POST /api/campaigns/{id}/memos`, `PATCH /memos/{id}`) for
>   manual or validation-gated assisted drafts and player-authored revisions.
>   AI is off by default (returns a deterministic system draft and logs a
>   fallback `ModelRun`). Drafting and editing never change state. Sending
>   attaches one exact memo revision to the deterministic NPC decision, turn
>   snapshot, canon reference, and dossier; sent records are immutable.
> - **Planned next:** the optional AI-use phase (a validation-gated, read-only
>   Research Console that only proposes classified facts), which would sit
>   between BRIEF/EVIDENCE and ADVICE, plus the remaining read-only tools
>   (faction reactions, press, canon summaries) and in-world tool costs.
> - **Out of scope for this MVP:** autonomous cascade events beyond ambient
>   drift, and long-term town→interstate progression.

## Core Loop

The player is a crisis-governance consultant called into failing institutions.

Each turn is a client engagement or continuation of an engagement.

The player does not directly govern. The player advises. NPCs decide what to do with that advice. The deterministic engine resolves the consequences.

```text
1. Client call arrives.
2. Situation brief is generated.
3. Player reviews facts, risks, factions, resources, and prior canon.
4. Player optionally uses AI tools.
5. Player issues advice.
6. NPC client decides how to use the advice.
7. Deterministic engine applies consequences.
8. Factions, media, agencies, and legal actors react.
9. Canon updates.
10. New risks, calls, and opportunities emerge.
```

## MVP Campaign Structure

The first scenario is **Northbridge Water Failure**.

The campaign lasts 10 turns.

Each turn represents roughly 3 days.

The campaign covers approximately 30 days.

The player is retained by the Northbridge town manager to advise on a worsening water-system crisis.

## Turn Phases

### 1. Incoming Call

A client or stakeholder contacts the player.

The call should establish:

* who is calling;
* why they need help;
* urgency;
* known facts;
* unknown facts;
* immediate ask;
* political pressure;
* legal exposure;
* time horizon.

Example:

```text
Client: Mara Velez, Northbridge Town Manager
Urgency: Critical
Time Horizon: 72 hours
Ask: Recommend whether to disclose preliminary water contamination results before confirmatory testing.
```

### 2. Situation Brief

The situation brief gives the player an organized view of the crisis.

It should include:

* summary;
* known facts;
* unverified reports;
* contradicted facts;
* relevant documents;
* available legal authority;
* affected factions;
* resource pressures;
* immediate risks;
* possible escalation paths.

The brief may be generated partly by AI, but the underlying facts must come from game state, seed data, documents, or canon.

### 3. Investigation

The player reviews the case file.

The player may inspect:

* faction positions;
* prior promises;
* prior memos;
* documents;
* media reports;
* rumor feeds;
* legal authority;
* infrastructure state;
* resource levels;
* outstanding risks;
* state/federal agency posture.

This phase should reward attention to institutional memory.

A fact that looked minor in Turn 2 may become legally or politically decisive in Turn 7.

### 4. Optional AI Use

The player may use AI tools.

Possible tasks:

* summarize documents;
* draft a memo;
* review legal authority;
* classify rumors;
* identify contradictions;
* generate advice options;
* forecast scenario outcomes;
* draft public communications;
* analyze faction reactions.

AI use should carry costs:

* power;
* bandwidth;
* time;
* privacy exposure;
* legal exposure;
* political risk;
* cloud credits;
* confidence limits.

AI output is advisory. It is not canon until accepted into workflow.

### 5. Advice

The player issues advice.

Initial advice forms:

* consultant memo;
* emergency order recommendation;
* public statement;
* legal risk assessment;
* negotiation plan;
* triage protocol;
* procurement strategy;
* state-aid request;
* disclosure strategy;
* delay strategy;
* contractor strategy.

The advice should include:

* recommendation;
* rationale;
* expected benefits;
* expected harms;
* legal risk;
* political risk;
* implementation steps;
* fallback plan.

The player should rarely have a clean best option. Every useful option should create tradeoffs.

**As built:** six global advice options are available every turn, plus a small
set of **turn-specific options** surfaced only on the call that motivates them —
a staged school-closure protocol on turn 2, a hospital priority-allocation on
turn 3, and a business-compensation framework on turn 7. These are held in
`Campaign.per_turn_advice` (turn → options) and merged in by
`Campaign.available_advice()`; each carries the full tradeoff surface and at
least one stated harm, and each new advice tag has a dedicated `_decide_*`
handler in `engine/rules.py`.

### 6. NPC Decision

The client decides how to use the advice.

NPC behavior should depend on:

* client traits;
* faction pressure;
* trust in player;
* public exposure;
* legal exposure;
* resource scarcity;
* political incentives;
* prior promises;
* fear of blame;
* media pressure.

Possible NPC responses:

* follow advice exactly;
* follow advice partially;
* delay action;
* reject advice;
* leak advice;
* distort advice publicly;
* use advice as cover for a preexisting decision;
* request a safer revision;
* escalate to another authority;
* blame the consultant later.

This phase is crucial. The player is influential but not sovereign.

**As built:** the NPC that acts on the advice — `NpcDecision.decider` — is the
client on the current call (`campaign.current_call().caller`), so the hospital,
the contractor, the state liaison, and public works each own their own
decisions; the Town Manager's Office is only the fallback when a turn has no
call. The decider is woven into the decision rationale, the aftermath summary,
and the immediate consequence text.

### 7. Deterministic Resolution

The engine applies consequences.

The engine should calculate effects on:

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
* contractor dependency;
* faction trust;
* player reputation;
* player perceived neutrality;
* player shadow authority.

Every change must be represented as an applied diff.

Example:

```text
public_trust: -6
Reason: controlled disclosure was perceived as delayed after resident rumor feed surfaced prior test screenshots.

legal_exposure: -4
Reason: town notified state agency before public press conference and preserved written rationale.

state_oversight_risk: +5
Reason: state agency now has formal notice of water-system instability.
```

### 8. Aftermath

The aftermath screen translates state changes into legible consequences.

It should include:

* immediate consequences;
* second-order consequences;
* faction reactions;
* media framing;
* legal/procedural fallout;
* new open threads;
* canonized events.

**As built:** the immediate-consequence lines vary per turn. The tag/decision
pool supplies the substance, and a deterministic opener ties the effect to
*this* turn's specific call (its caller and situation) and the engagement phase
(opening / mid-crisis / closeout). Choosing the same advice tag on a later turn
therefore no longer reads identically. The variation is a pure function of
`(advice, decision, state, turn)` — no randomness — so the consequence stack
stays bit-for-bit reproducible.

Example:

```text
Immediate:
- Hospital water priority stabilizes dialysis operations.
- Parent coalition demands school closure.
- Council opposition accuses town manager of concealment.

Second-order:
- State agency requests written justification.
- Contractor demands indemnity.
- Local business alliance threatens suit over conservation restrictions.

Canon:
- Emergency Water Disclosure Memo issued on Turn 3.
- "Northbridge Coverup" becomes a persistent media narrative.
```

### 9. Canon Update

The historian/canon layer records durable facts.

Canon should distinguish between:

* confirmed facts;
* disputed claims;
* rumors;
* public narratives;
* private advice;
* leaked materials;
* legal actions;
* unresolved risks.

Canon entries should become retrievable in later turns.

### 10. Progression

New crises should emerge from prior consequences.

Examples:

* A delayed disclosure becomes a public trust crisis.
* An emergency procurement becomes a corruption allegation.
* A hospital prioritization becomes a fairness dispute.
* A school closure becomes a labor conflict.
* A state-aid request becomes a state oversight threat.
* A contractor pressure strategy becomes a work stoppage.

The game should feel like a cascade, not a random event generator.

## Player Success

Success is not “solving collapse.”

In the Northbridge MVP, success means surviving 30 days without triggering catastrophic failure.

Possible success dimensions:

* keep water security above collapse threshold;
* avoid hospital failure;
* preserve enough public order;
* avoid immediate state takeover;
* prevent legal exposure from becoming unmanageable;
* maintain enough public trust to keep emergency measures viable.

The best outcome may still be ugly.

## Campaign Failure

Failure should be institutional, not cartoonish.

Possible failure states:

* water-system collapse;
* hospital emergency failure;
* mass public disorder;
* state receivership or takeover;
* council collapse;
* budget insolvency;
* contractor abandonment;
* court injunction blocking emergency response;
* public trust collapse;
* player fired and scapegoated.

## Long-Term Progression

After Northbridge, successful or notorious performance can unlock larger engagements:

```text
Town crisis
  ↓
neighboring town crisis
  ↓
regional coordination failure
  ↓
state agency emergency
  ↓
governor’s office engagement
  ↓
interstate compact crisis
```

The player’s growing reputation should create both opportunity and danger.

As the player becomes more effective, the player may also become politically toxic, legally exposed, or structurally indispensable.
