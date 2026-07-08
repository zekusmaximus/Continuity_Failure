# docs/architecture.md

# Architecture

> **Implementation status (this branch).** This is a forward-looking design
> spec. The Northbridge deterministic MVP is implemented and runnable today;
> the AI, persistence, and deployment layers described below are **planned**,
> not present. See § "Current Architecture (as built)" for what actually
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
backend/    FastAPI + Pydantic v2, in-memory only
   |        app/api/campaigns.py        routes
   |        app/services/campaign_service.py  engine <-> memory <-> schemas
   |        app/schemas/api.py          Pydantic request/response models
   ↓ imports
engine/     framework-free deterministic engine (dataclasses, no web deps)
   |        models.py state.py diffs.py rules.py turn.py seed_data.py
   ↓ used by
memory/     in-memory CampaignStore (process-local; cleared on restart)
```

**Implemented now**

* Deterministic engine: 16 state variables (0–100, clamped), 10 factions, 6
  advice options, 10 per-turn client calls, ambient crisis drift, NPC decision
  logic, applied diffs for every change, failure thresholds, 10-turn
  completion.
* FastAPI endpoints: `GET /health`, `POST /api/campaigns`,
  `GET /api/campaigns/{id}`, `GET /api/campaigns/{id}/current`,
  `POST /api/campaigns/{id}/advice`, `GET /api/campaigns/{id}/turns`.
* React workstation UI: state panel, client call, advice workbench, aftermath
  with applied diffs, turn history, canon archive.
* `pytest` engine suite (determinism, bounds, failure, completion).

**Actual current repository structure**

```text
frontend/   src/{main,App,domain}.tsx, api/client.ts, components/*, styles/global.css
backend/    app/{main,api/campaigns,services/campaign_service,schemas/api}.py
engine/     {models,state,diffs,rules,turn,seed_data}.py
memory/     {persistence}.py            (CampaignStore, MemoryStore)
tests/      test_engine_turns.py, test_state_invariants.py
evals/      README.md                    (reserved)
docs/       *.md
prompts/    README.md                    (reserved; no prompt files yet)
```

> Note: the "Initial Repository Structure" tree later in this document is the
> **target** layout. Files it lists that do not yet exist (e.g. `engine/events.py`,
> `engine/scoring.py`, `memory/canon.py`, `memory/retrieval.py`,
> `backend/app/config.py`, `backend/app/models/`, frontend `screens/`/`types/`/`utils/`)
> are planned, not current.

**Intentionally Not Present Yet**

* AI / model calls (no provider abstraction, no structured-output validation,
  no `ModelRun` logging).
* Autonomous agents / multi-agent behavior.
* Durable storage: no SQLite, Postgres, SQLAlchemy, or SQLModel. State is
  process-local in-memory only.
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

### Initial Screens

1. Engagement Dashboard.
2. Incoming Call.
3. Crisis Brief.
4. Evidence Board.
5. AI Research Console.
6. Advice Workbench.
7. Aftermath / Consequence Stack.
8. Archive / Campaign Dossier.

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

> **Status:** As built, persistence is **in-memory only** (no SQLite/SQLAlchemy
> yet). The list below is the intended stack for a later durability milestone.

```text
Python
FastAPI
Pydantic
SQLite for MVP
SQLAlchemy or SQLModel
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
engine/events.py
engine/scoring.py
engine/diffs.py
engine/seed_data.py
```

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
