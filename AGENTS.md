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

## Design Invariants (enforced on this branch)

These are concrete, test-backed guarantees. Do not weaken them without updating
the tests in `tests/`.

1. **All numeric state values stay within 0–100.**
   Enforced by `engine.state.clamp`; every mutation routes through
   `engine.diffs.apply_diffs`. Covered by `tests/test_state_invariants.py`.

2. **Every authoritative state mutation produces an `AppliedDiff`.**
   There is no path that changes `WorldState.variables` without emitting a diff
   with `variable`, `old_value`, `new_value`, `delta`, `reason`, and
   `source_type`. The UI can always show why something changed.

3. **Model output is not canon unless accepted by deterministic workflow.**
   A dormant, validation-gated AI-assist layer exists in `backend/app/ai/`
   (memo drafter + `ModelRun` logging), off by default. It may only *propose*
   advisory artifacts (memo drafts) classified `proposed`/`unverified`/`rumor`;
   only the engine promotes a fact to `canon`, and the AI package is tested
   (`test_ai_layer_cannot_mutate_game_state`, `test_draft_memo_does_not_change_world_state`)
   to never import state-mutation code (`engine.diffs`/`engine.turn`).
   `FactClassification` in `engine/models.py` is the vocabulary.

4. **NPC decisions mediate the player's advice.**
   The player selects an `AdviceOption`; `engine.rules.decide` determines
   `decision_type` and `adherence`, and `engine.turn.advance_turn` scales the
   advice effects accordingly. The player never writes state directly.

5. **A campaign can complete or fail, and never advances past terminal.**
   Failure thresholds live in `engine.rules.FAILURE_THRESHOLDS`; completion is
   reaching turn 10 without failure (`CampaignStatus.COMPLETED`). A terminal
   campaign rejects further turns. Statuses: `ACTIVE`, `COMPLETED`, `FAILED`.

6. **Engine code must remain independent from FastAPI.**
   The `engine/` package imports no web/Pydantic dependency. The backend maps
   engine dataclasses to Pydantic at the API boundary only. Verified by an
   AST scan of `engine/*.py` (`test_engine_does_not_import_fastapi`,
   `test_engine_imports_only_stdlib_and_itself`) so the check is independent
   of test collection order and what other tests import.

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

The deterministic Northbridge MVP is implemented, playable, and tested (156
tests). A dormant, validation-gated AI-assist layer (memo drafter +
`ModelRun` logging) is wired end to end and off by default. Build out the
remaining read-only AI tools and add durable persistence before implementing
autonomous multi-agent behavior.

The first technical milestone (met):

> A user can run a 10-turn deterministic Northbridge water-crisis campaign,
> inspect state changes, and export a basic turn log.

The next milestone:

> The AI-assist layer covers the read-only research/drafting tools behind the
> validation boundary, with in-world tool costs, before durability is added.
