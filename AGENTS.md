# AGENTS.md

## Project Identity

This repository is for **Continuity Failure**, a near-future civic breakdown simulator.

The player is a crisis-governance consultant advising institutions during cascading societal failure. The game should feel procedural, legal, civic, institutional, morally tense, and systems-driven. Avoid generic apocalypse, zombie, military, superhero, or survival-crafting tropes.

The core fantasy is not “command society.” The core fantasy is “advise failing institutions from inside the collapsing machinery.”

## Non-Negotiable Design Rules

1. **The database is canon. The model is not.**

   * LLM output may propose, summarize, draft, narrate, classify, or evaluate.
   * LLM output must not directly mutate authoritative world state.
   * All state changes must pass through deterministic engine functions.

2. **The player advises. NPCs decide.**

   * The player issues advice, memos, recommendations, emergency orders, public statements, negotiation plans, or research findings.
   * NPC clients may follow, modify, reject, delay, leak, distort, or misuse that advice.

3. **Every state change must be explainable.**

   * State changes require an applied diff.
   * Diffs must be tied to a turn, action, rule, event, or NPC decision.
   * The UI must be able to show why something changed.

4. **Every generated fact must be classified.**

   * Proposed fact.
   * Rejected fact.
   * Canon fact.
   * Rumor.
   * Unverified report.
   * Contradicted report.

5. **No hidden direct model authority.**

   * AI tools may generate suggested actions, memos, scenario forecasts, faction reactions, press narratives, or canon summaries.
   * The deterministic engine decides actual effects.

6. **Collapse should be bureaucratic and institutional.**

   * Prefer legal ambiguity, emergency procurement, public trust collapse, stale data, infrastructure fragility, jurisdiction conflict, bad incentives, and institutional overload.
   * Avoid melodramatic disaster spectacle unless it emerges from civic failure.

## Tone

The tone should be:

* serious;
* procedural;
* civic;
* anxious;
* grounded;
* morally complicated;
* legally and politically aware;
* near-future plausible;
* occasionally eerie, but not supernatural.

Good reference mood:

* emergency operations dashboard;
* legal document review;
* municipal crisis management;
* public utility failure;
* state agency emergency response;
* late-night consulting memo;
* public records exposure;
* institutional systems under stress.

Bad reference mood:

* generic cyberpunk;
* zombie apocalypse;
* military command fantasy;
* cartoon strategy game;
* random AI-agent toy;
* utopian civic-tech demo.

## MVP Focus

The first playable build should focus on one scenario:

**Northbridge Water Failure**

A fictional Connecticut town faces a water-system crisis involving preliminary contamination data, hospital vulnerability, school pressure, contractor dependency, public rumor, fiscal limits, and state oversight risk.

Do not build statewide gameplay before the Northbridge town-level loop works.

## Initial MVP Entities

Start with these core concepts:

* `WorldState`
* `Jurisdiction`
* `Faction`
* `Resource`
* `Crisis`
* `Turn`
* `ClientCall`
* `Advice`
* `AdviceMemo`
* `NpcDecision`
* `AppliedDiff`
* `CanonEntry`
* `OpenThread`
* `ModelRun`
* `EvaluationResult`

## Initial MVP State Variables

Use a small number of legible variables before adding complexity:

* water_security
* power_stability
* public_trust
* public_order
* budget_capacity
* staff_capacity
* legal_exposure
* media_pressure
* state_oversight_risk
* contractor_dependency
* hospital_stability
* school_disruption
* player_reputation
* player_perceived_neutrality
* player_shadow_authority

## AI Systems as Gameplay

AI is not just backend infrastructure. AI exists inside the game world.

The player may have access to:

* local model;
* cloud frontier model;
* municipal archive model;
* legal retrieval system;
* rumor classifier;
* scenario simulator;
* document review assistant.

These tools should have tradeoffs:

* power cost;
* bandwidth requirement;
* privacy exposure;
* data freshness;
* legal risk;
* political risk;
* confidence;
* latency;
* hallucination risk.

Cloud models may be stronger but riskier. Local models may be private but weaker or stale. During power or communications failures, model access should degrade.

## UI Direction

The UI should be diegetic.

The player is using a crisis-consulting workstation, not a generic game menu.

Core UI screens:

1. Engagement Dashboard.
2. Incoming Call.
3. Crisis Brief.
4. Evidence Board.
5. AI Research Console.
6. Advice Workbench.
7. Aftermath / Consequence Stack.
8. Archive / Campaign Dossier.

The interface should begin polished and degrade as systems fail:

* stale data warnings;
* last-verified timestamps;
* missing feeds;
* offline model warnings;
* low-power mode;
* document corruption;
* partial records;
* conflicting reports;
* redactions;
* manual annotations.

## Engineering Rules

* Prefer TypeScript on the frontend.
* Prefer Python with FastAPI and Pydantic on the backend.
* Keep deterministic simulation logic isolated from API routing.
* Keep prompts in versioned files under `prompts/`.
* Keep schemas centralized and reusable.
* Validate every model response before use.
* Log every model call with prompt version, input, output, validation result, retries, latency, token use, and cost estimate where available.
* Write tests for state transitions before expanding content.
* Do not scatter inline prompts throughout the codebase.
* Do not add new frameworks unless they solve an immediate problem.

## Suggested Initial Structure

```text
frontend/
backend/
engine/
memory/
prompts/
evals/
docs/
```

## Output Expectations for Coding Agents

When making changes:

* prefer small, coherent commits;
* update docs when architecture or gameplay assumptions change;
* do not silently change the core premise;
* add tests for deterministic logic;
* preserve replayability;
* avoid placeholder lore when implementing scenario content;
* keep the Northbridge MVP playable before expanding scope.

## Current Priority

Build the deterministic Northbridge MVP before implementing autonomous multi-agent behavior.

The first technical milestone is:

> A user can run a 10-turn deterministic Northbridge water-crisis campaign, inspect state changes, and export a basic turn log.
