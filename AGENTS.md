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

7. **A turn resolves atomically, at most once per idempotency key.**
   `POST /advice` carries `expected_turn` (the revision the client composed
   against) and a bounded `idempotency_key`. `campaign_service.submit_advice`
   opens one `SQLiteRepository.transaction()` and inside it checks the
   idempotency record, guards terminal/revision, runs `engine.turn.advance_turn`,
   saves the campaign, appends the immutable snapshot, and records the
   idempotency result. All of it commits or none of it does — there is no
   half-saved turn. Uniqueness of `(campaign_id, idempotency_key)` is a SQLite
   primary key, not merely an application check. Conflicts are typed and stable:
   same key + same payload replays the original response (`Idempotent-Replay:
   true`); same key + different payload is `idempotency_key_conflict`; a
   mismatched revision is `stale_turn`; a terminal campaign is
   `campaign_terminal`. Covered by `tests/test_turn_atomicity.py`.
   Transactionality lives in the application/repository layer; the engine stays
   pure (invariant 6).

8. **Every request is identified and every request logs one structured line.**
   `RequestContextMiddleware` adopts a well-formed inbound `X-Request-ID` or
   mints one, echoes it on the response, and emits a single JSON log record
   with `request_id`, `method`, `route`, `status`, `duration_ms`, `campaign_id`,
   `turn_number`, `expected_turn`, and the `idempotency` outcome. The field set
   is an allow-list (`observability._BINDABLE_FIELDS`): advice memo text,
   prompts, secrets, and model inputs/outputs can never enter a request log.
   Error bodies are always `{"detail": {error, message, request_id, ...}}` with
   player-safe prose and no internals.

9. **A resolved turn remains frozen until the player explicitly moves on.**
   The advice transaction appends an immutable `turn_presentations` record with
   the exact pre-resolution turn package and resolved result. Refresh and
   backend restart restore that record at Client Decision; only the idempotent
   presentation acknowledgement used by **Next Call** (or the terminal dossier
   action) releases the following call. This checkpoint is application workflow
   state outside `engine/` and never mutates `WorldState`.

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
* Keep authored scenario content as versioned JSON under
  `engine/content/scenarios/` (not embedded in engine code); it is validated
  before a campaign starts. Run `python -m engine.content validate` and see
  `docs/content-authoring.md`.
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

The deterministic Northbridge MVP is implemented, playable, and tested (531
Python tests as of this commit — always re-derive the count with `pytest -q`
rather than trusting this number; plus 46 vitest and 24 Playwright tests). A
dormant, validation-gated AI-assist layer (memo drafter + `ModelRun` logging)
is wired end to end and off by default. Durable SQLite persistence and atomic,
idempotent turn resolution are in place. The Wave 2 balance pass (ruleset "3")
made the marquee mechanics truthful in ordinary play: the CRITICAL band and
its one-subsystem auxiliary-power choice are reachable and binding, the turn-4
contractor ultimatum is live, and every completed-campaign verdict has a
pinned witness sequence (`tests/test_ending_reachability.py`). Build out the
remaining read-only AI tools before implementing autonomous multi-agent
behavior.

The first technical milestone (met):

> A user can run a 10-turn deterministic Northbridge water-crisis campaign,
> inspect state changes, and export a basic turn log.

The next milestone:

> The AI-assist layer covers the read-only research/drafting tools behind the
> validation boundary, with in-world tool costs, before durability is added.
