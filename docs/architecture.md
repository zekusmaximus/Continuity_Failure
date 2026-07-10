# docs/architecture.md

# Architecture

> **Implementation status (this branch).** This is a forward-looking design
> spec. The Northbridge deterministic MVP is implemented and runnable today;
> broader AI and deployment layers described below are **planned**. SQLite
> persistence and the first validation-gated AI tool are present. See
> § "Current Architecture (as built)" for what actually
> exists, and § "Intentionally Not Present Yet" for what is deliberately
> deferred.

## Purpose

This document defines the initial technical architecture for **Continuity Failure**.

The first milestone is not a large agent simulation. The first milestone is a deterministic, replayable, inspectable Northbridge town-crisis simulator with optional AI assistance layered on top.

The architecture must preserve one core rule:

> The deterministic engine owns state. AI systems advise, draft, summarize, research, forecast, and narrate.

## Current Architecture (as built)

This is the architecture that exists and runs on the current branch. Everything
in this section is verified by passing tests and a working dev server.

```text
frontend/   React 18 + TypeScript + Vite  (no UI framework, plain CSS)
   |        Vite dev server proxies /api and /health to the backend
   ↓ HTTP (JSON)
backend/    FastAPI + Pydantic v2
   |        app/api/campaigns.py        routes (incl. /memo, /model-runs)
   |        app/services/campaign_service.py  engine <-> memory <-> ai <-> schemas
   |        app/schemas/api.py          Pydantic request/response models
   |        app/repository.py           neutral SQLite repository provider
   |        app/ai/                     dormant, validation-gated AI-assist layer
   |          provider.py               NullProvider (default) / AnthropicProvider
   |          runner.py                 run_artifact: validate -> retry -> fallback
   |          schemas.py                MemoDraft output contract
   |          fallbacks.py              deterministic memo builder
   |          logging.py                durable ModelRun repository adapter
   |        app/config.py               AI + configurable database settings
   ↓ imports
engine/     framework-free deterministic engine (dataclasses, no web deps)
   |        models.py state.py diffs.py rules.py turn.py seed_data.py
   ↓ used by
memory/     versioned SQLite repository (campaigns, immutable snapshots, model runs)
```

**Implemented now**

* Deterministic engine: 16 state variables (0–100, clamped), 10 factions (with
  red lines, public/private incentives, trust, risk tolerance, pressure), 12
  evidence documents, 6 advice options with surfaced tradeoffs (benefits,
  harms, legal/political/operational risk, affected factions), 10 per-turn
  client calls forming a cascade, ambient crisis drift, NPC decision logic with
  visible mediation, applied diffs for every change, deterministic consequence
  stacks, open-thread tracking, failure thresholds, and 10-turn completion.
  The engine also ships a framework-free Markdown dossier builder
  (`engine/dossier.py`).
* FastAPI endpoints: `GET /health`, `POST /api/campaigns`,
  `GET /api/campaigns` (recent resume metadata),
  `GET /api/campaigns/{id}`, `GET /api/campaigns/{id}/current`,
  `POST /api/campaigns/{id}/advice`, `GET /api/campaigns/{id}/turns`,
  `GET /api/campaigns/{id}/dossier`, `POST /api/campaigns/{id}/memo`
  (advisory memo draft), `GET /api/campaigns/{id}/model-runs` (read-only AI
  run log).
* **Durable SQLite boundary** (`memory/persistence.py`): complete versioned
  campaign JSON reconstructs typed engine dataclasses exactly; separate
  append-only end-of-turn snapshots prevent later history rewrites; model runs
  use the same repository without gaining state-mutation authority. The path is
  configurable with `CF_DATABASE_PATH` and schema versions are forward-migrated
  through `schema_migrations` using only Python's standard library (v1 = base
  tables, v2 = `turn_idempotency`).
* **Atomic, idempotent turn resolution**: `POST /api/campaigns/{id}/advice`
  requires `expected_turn` (the revision the client composed against) and a
  bounded `idempotency_key`. `SQLiteRepository.transaction()` yields a
  `RepositoryTransaction` and the campaign service performs the whole unit
  inside it — idempotency lookup, terminal/revision guards, `advance_turn`,
  campaign save, snapshot append, idempotency record — committing all of it or
  rolling all of it back. `BEGIN IMMEDIATE` takes SQLite's write lock before the
  campaign is read, so two competing submissions cannot both advance the same
  turn; the loser sees `stale_turn`. `(campaign_id, idempotency_key)` is a
  primary key, so an exact retry replays the stored response
  (`Idempotent-Replay: true`) and never resolves a second turn.
* **Request identity and structured logs** (`backend/app/observability.py`): a
  pure-ASGI middleware adopts a valid inbound `X-Request-ID` or generates one,
  echoes it, and emits one JSON line per request with `request_id`, `method`,
  `route`, `status`, `duration_ms`, `campaign_id`, `turn_number`,
  `expected_turn`, and the `idempotency` outcome (`resolved` / `replayed` /
  `key_conflict` / `stale_turn` / `terminal` / `rejected` / `not_applicable`).
  Loggable fields are an allow-list, so memo prose, prompts, and model output
  cannot leak into request logs. Errors share one body shape:
  `{"detail": {error, message, request_id, ...}}`.
* **Dormant, validation-gated AI-assist layer** (`backend/app/ai/`): a memo
  drafter is the first implemented tool. `run_artifact` renders the versioned
  prompt, calls a provider (default `NullProvider`, which never succeeds), 
  validates the output against a Pydantic schema, retries once on failure, and
  falls back to a deterministic `MemoDraft` built from the advice record. Every
  call is logged as a `ModelRun` (success / invalid / fallback / error). AI is
  off by default (`Settings.ai_live` requires both `CF_AI_ENABLED` and
  `ANTHROPIC_API_KEY`); a live config without the optional `anthropic` extra
  degrades safely to `NullProvider`. The AI package imports no state-mutation
  code and is tested never to mutate `WorldState`.
* React **Continuity Desk — Guided Intake** UI: an intro/boot screen followed by
  a one-task-per-screen turn flow (incoming call → situation brief → evidence
  review → advice → client decision → consequences → turn archive → next call /
  dossier), each with a single primary action and a persistent four-indicator
  header. Dense material (full 16-variable state, all factions, canon, full
  timeline, raw applied diffs, Markdown dossier) is moved into an on-demand
  **Case File** drawer rather than being rendered all at once. The Advice phase
  exposes an optional **Draft memo** affordance (calls `/memo`, renders the
  draft with honest "AI draft" / "System draft (fallback)" provenance), and the
  Case File has a **Model Runs** tab. The frontend reveals the backend's single
  post-advice `TurnResult` across the separate client-decision / consequences /
  archive phases; no backend shape change was required.
* `pytest` suite: determinism, 0–100 bounds, failure
  thresholds, completion at turn 10, applied diffs, engine/FastAPI-independence
  (AST-based), documents/evidence, advice tradeoffs, consequence stacks, open
  threads, dossier generation, the AI boundary + runner + memo service path,
  HTTP route tests (`TestClient`) covering all endpoints and error paths, plus
  SQLite restart, corruption, terminal recovery, and snapshot-immutability
  regressions.

**Actual current repository structure**

```text
frontend/   src/{main,App,domain}.tsx, api/client.ts, styles/global.css,
            components/* — guided shell (IntroScreen, ContinuityHeader,
            KeyStateIndicators, PrimaryAction, GuidedTurn), one component per
            turn phase (CallPhase, BriefPhase, EvidencePhase, AdvicePhase,
            ClientDecisionPhase, ConsequencesPhase, ArchivePhase), the on-demand
            CaseFile drawer (+ DocumentDetail, ModelRunPanel), MemoDraftPanel,
            and the reused dense views (EvidenceBoard, FactionPanel,
            StateReadout, CanonPanel, TurnHistory, CampaignDossier)
backend/    app/{main,config,repository,api/campaigns,services/campaign_service,schemas/api}.py
            app/ai/{provider,runner,schemas,fallbacks,logging}.py  (dormant by default)
engine/     {models,state,diffs,rules,turn,seed_data,consequences,dossier}.py
memory/     {persistence}.py            (CampaignRepository, SQLiteRepository)
tests/      test_engine_turns.py, test_state_invariants.py, test_content_and_dossier.py,
            test_ai_boundary.py, test_ai_runner.py, test_ai_memo.py, test_api.py,
            test_persistence.py
evals/      README.md                    (reserved)
docs/       *.md
prompts/    README.md, memo_drafter.v1.md
```

> Note: the "Initial Repository Structure" tree later in this document is the
> **target** layout. Files it lists that do not yet exist (e.g. `engine/events.py`,
> `engine/scoring.py`, `memory/canon.py`, `memory/retrieval.py`,
> `backend/app/config.py`, `backend/app/models/`) are planned, not current.

**Intentionally Not Present Yet**

* The broader in-world AI toolset beyond the memo drafter: research console,
  rumor classifier, scenario simulator, document review, faction-reaction /
  press / canon-summary generators, and in-world tool costs (power, bandwidth,
  privacy, latency). The validation boundary and `ModelRun` logging they would
  use *are* present.
* Autonomous agents / multi-agent behavior.
* Multi-process conflict handling, account ownership, and cloud sync. The local
  SQLite boundary intentionally does not solve these yet.
* Vector database / semantic retrieval.
* Authentication and deployment configuration.
* Statewide / regional / interstate progression beyond the town level.

## High-Level Architecture

```text
frontend/
  React + TypeScript UI
  ↓
backend/
  FastAPI orchestration API
  ↓
engine/
  deterministic simulation engine
  ↓
memory/
  canon store, turn history, retrieval
  ↓
prompts/
  versioned prompt files
  ↓
model provider
  structured AI calls
```

## Initial Repository Structure

```text
frontend/
  src/
    components/
    screens/
    api/
    types/
    utils/

backend/
  app/
    main.py
    api/
    services/
    models/
    schemas/
    config.py

engine/
  __init__.py
  state.py
  turn.py
  rules.py
  events.py
  scoring.py
  diffs.py
  seed_data.py

memory/
  __init__.py
  canon.py
  retrieval.py
  persistence.py

prompts/
  README.md
  crisis_brief.v1.md
  advice_options.v1.md
  memo_drafter.v1.md
  faction_reactions.v1.md
  press_desk.v1.md
  historian.v1.md
  continuity_critic.v1.md

evals/
  seeded_campaigns/
  invariants/
  rubrics/

docs/
  architecture.md
  game-loop.md
  state-schema.md
  mvp-roadmap.md
  project-spec.md
```

## Frontend

The frontend should be a diegetic crisis-consulting workstation.

The player is not looking at a generic game UI. The player is using an in-world professional system: part emergency operations console, part legal workbench, part document-review platform, part AI research terminal.

Initial frontend stack:

> **Status:** As built, the frontend is React + TypeScript + Vite with plain CSS
> and no data-fetching library. TanStack Query and Tailwind (below) are options,
> not current dependencies.

```text
React
TypeScript
Vite
TanStack Query
CSS modules or Tailwind
```

Avoid premature UI frameworks that impose too much aesthetic personality. The UI should be custom enough to feel like institutional software under stress.

### Screens (as built: guided intake flow)

Rather than one dashboard showing everything at once, the UI is a guided
sequence — **one screen, one task, one obvious next action**:

1. Intro / boot (orient the player).
2. Incoming Call (`Accept Call`).
3. Situation Brief (`Review Evidence` / `Skip to Advice`).
4. Evidence Review — Critical / Relevant / Background (`Continue to Advice`).
5. Advice — concise tradeoffs, details expand on selection (`Send Advice`).
6. Client Decision — how the NPC used the advice (`Resolve Consequences`).
7. Consequences — human-readable first, raw diffs behind an expander (`Close Turn`).
8. Turn Archive (`Next Call`, or `View Campaign Dossier` when terminal).
9. Case File drawer (on demand): Evidence · Factions · Full State · Canon ·
   Timeline · Dossier.

A future AI Research Console would slot in as an optional step between Brief and
Advice; it is not present in this build. The memo drafter is present as an
optional, advisory affordance *within* the Advice phase (it drafts a memo for
the selected option without sending advice or changing state).

### Frontend Principles

* Show state changes clearly.
* Show uncertainty.
* Show last-verified timestamps.
* Show which facts are canon, proposed, rumored, contradicted, or unverified.
* Show why consequences occurred.
* Treat documents, calls, memos, and AI outputs as first-class visual objects.
* Let the interface degrade as power, bandwidth, trust, and institutional capacity degrade.

## Backend

The backend coordinates game state, persistence, model calls, turn resolution, and replay.

Initial backend stack:

> **Status:** As built, persistence uses standard-library SQLite with versioned
> JSON documents and append-only turn snapshots. SQLAlchemy/SQLModel are not
> needed for the current narrow repository. The AI-assist layer (`app/ai/`) is
> present and dormant by default; see "AI Layer" below.

```text
Python
FastAPI
Pydantic
SQLite for MVP
Standard-library sqlite3 repository
```

SQLite is sufficient for the first milestone. Postgres can be introduced later if the project needs richer querying, concurrency, deployment scale, or full-text search beyond MVP needs.

### Backend Responsibilities

The backend should:

* load scenarios;
* create campaigns;
* store world state snapshots;
* resolve turns;
* call deterministic engine functions;
* validate player advice;
* coordinate model calls;
* validate structured AI outputs;
* persist model runs;
* write turn logs;
* expose replay data;
* export campaign dossiers.

The backend should not bury game rules in route handlers. API endpoints should call services, and services should call the engine.

## Deterministic Engine

The deterministic engine is the source of truth for simulation state.

It should be isolated from HTTP, UI, and model-provider logic.

Core files:

```text
engine/state.py
engine/turn.py
engine/rules.py
engine/consequences.py
engine/dossier.py
engine/diffs.py
engine/seed_data.py        (compatibility facade over engine/content)
engine/content/            (versioned, validated scenario content layer)
```

> **Status:** `events.py` and `scoring.py` above are the original target list;
> they are not present. Deterministic consequence-stack generation lives in
> `engine/consequences.py`, and the framework-free Markdown campaign dossier is
> built in `engine/dossier.py`.

### Scenario Content Layer

Authored scenario content is separated from executable engine rules. Content
describes *inputs* (starting state, factions, advice options, per-turn calls,
evidence documents, seed threads, crisis); the engine rules decide *outcomes*.

```text
engine/content/
  __init__.py            single factory API: load_campaign(scenario_id, ...)
  schema.py              schema version + controlled vocabularies + field specs
  validator.py           collecting validator (file/field-anchored errors)
  loader.py              JSON reader, schema-version gate/migration, dataclass build
  __main__.py            developer command: python -m engine.content validate
  scenarios/
    northbridge_water_failure/
      scenario.json      schema_version, id, name, max_turns, starting_variables, crisis
      factions.json      the ten Northbridge factions
      advice.json        the six global advice options
      per_turn_advice.json   turn -> options that only make sense on that call
      calls.json         one client call per turn (1..max_turns)
      documents.json     evidence-board documents (freshness = turn_number)
      threads.json       open threads seeded at engagement start
```

Rules of the layer:

* **JSON only** — the format is parsed with the standard library, so the engine
  keeps its "stdlib + engine only" import boundary
  (`tests/test_engine_turns.py::test_engine_imports_only_stdlib_and_itself`).
  No YAML/Pydantic/CMS is introduced into `engine/`.
* **Validate before seeding.** `load_campaign` validates the *complete* scenario
  before constructing any authoritative state, so malformed content never
  partially seeds a campaign. `seed_data.create_northbridge_campaign` is now a
  thin facade over `engine.content.load_campaign` and keeps its old signature.
* **Schema version.** `scenario.json` declares `schema_version`. The loader reads
  `SUPPORTED_SCHEMA_VERSIONS`, applies any registered forward migration, and
  raises `IncompatibleSchemaVersion` otherwise.
* **Fail loudly.** A typo in an id, cross-reference, WorldState variable, effect
  key, enum, range, turn, document tag, or operational step raises
  `ContentValidationError` — listing every problem with its file and field path —
  before play begins.

Authoring rules, the validator command, and the full check list live in
[`docs/content-authoring.md`](content-authoring.md).

### Engine Responsibilities

The engine should:

* advance turns;
* apply player advice;
* apply NPC decisions;
* update resources;
* update faction positions;
* update risk variables;
* generate applied diffs;
* enforce invariants;
* prevent invalid state;
* produce replayable turn results.

### Engine Non-Responsibilities

The engine should not:

* call LLMs;
* generate prose;
* perform legal research;
* create UI text except mechanical labels;
* rely on hidden model assumptions;
* mutate state without producing an applied diff.

## Memory and Canon

Canon is persistent game truth.

Model-generated text is not canon unless accepted by the game workflow.

Initial memory can be implemented with database tables and simple retrieval. Do not add a vector database until the project has enough content to justify it.

### Canon Types

Initial canon entry types:

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

### Canon Rules

Every canon entry should include:

* id;
* turn number;
* title;
* type;
* summary;
* involved factions;
* linked documents or advice;
* whether it is public, private, leaked, sealed, or disputed;
* downstream relevance tags.

## AI Layer

AI is both infrastructure and gameplay.

The player may use in-world AI tools:

* local model;
* cloud frontier model;
* municipal archive model;
* legal retrieval system;
* rumor classifier;
* scenario simulator;
* document review assistant.

Each AI tool should have gameplay costs and risks:

* power cost;
* bandwidth requirement;
* cloud credit cost;
* privacy exposure;
* confidence;
* data freshness;
* political risk;
* latency;
* hallucination risk.

### AI Responsibilities

AI systems may:

* summarize documents;
* generate crisis briefs;
* draft memos;
* suggest advice options;
* forecast possible consequences;
* produce faction reactions;
* generate press coverage;
* identify contradictions;
* create canon summaries;
* flag continuity issues.

### AI Prohibitions

AI systems may not:

* directly mutate world state;
* invent canon without workflow approval;
* silently create new factions, laws, resources, or prior events;
* override deterministic outcomes;
* conceal uncertainty;
* create advice that lacks traceable input context.

## Structured Outputs

All model calls must return validated structured outputs.

Each model call should have:

* prompt version;
* input payload;
* expected schema;
* raw output;
* parsed output;
* validation result;
* retry count;
* latency;
* token usage if available;
* estimated cost if available.

Invalid model outputs should be rejected, retried once if appropriate, and then replaced by deterministic fallback text.

## Turn Logging

Every turn should produce a replayable log.

A turn log should include:

```text
turn_id
campaign_id
scenario_id
starting_state_snapshot_id
client_call
documents_available
player_advice
ai_tools_used
model_runs
npc_decision
applied_diffs
ending_state_snapshot_id
faction_reactions
press_reactions
canon_entries
evaluation_results
```

## Replayability

The system should allow a developer to inspect how a state was reached.

Minimum replay requirements:

* every turn has a starting snapshot;
* every turn has applied diffs;
* every diff has a reason;
* every reason links to advice, event, NPC decision, or deterministic rule;
* every model output is inspectable but not authoritative.

## Deployment Direction

Do not optimize deployment before the MVP loop works.

Likely eventual deployment:

```text
Frontend: Vercel / Netlify / static hosting
Backend: Render / Railway / Fly.io
Database: SQLite for local MVP, Postgres later
```

Local development should remain simple.

## First Technical Milestone

The first technical milestone is:

> A user can run a deterministic 10-turn Northbridge Water Failure campaign, inspect state changes, view turn history, and export a basic campaign dossier.

No autonomous multi-agent architecture should be added before this milestone is working.
