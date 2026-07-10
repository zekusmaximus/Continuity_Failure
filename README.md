# Continuity Failure

**Continuity Failure** is a near-future civic breakdown simulator where the player runs a crisis-governance consulting firm called into failing institutions as society loses capacity faster than its legal, political, and infrastructure systems can adapt.

The player does not directly govern. The player advises mayors, town managers, agency heads, hospital counsel, utility executives, regional compacts, and state officials through memos, emergency orders, public statements, negotiation plans, triage frameworks, legal risk assessments, and scenario forecasts.

NPC clients may follow, distort, leak, ignore, or weaponize the player’s advice. The deterministic simulation engine resolves consequences. AI systems generate institutional artifacts, research support, faction reactions, media distortion, legal/policy analysis, and canon summaries — but the model is never the source of truth for game state.

The campaign begins at the town level and expands outward as the player is called into larger failures: municipal crises, regional coordination breakdowns, state emergency governance, and eventually interstate compact formation.

## Core Design Pillars

1. **The database is canon. The model is not.**
   LLMs may propose, narrate, summarize, draft, and analyze. They may not directly mutate authoritative game state.

2. **The player advises. NPCs decide.**
   The player’s power is indirect. Clients may accept, modify, reject, leak, or misuse advice.

3. **Collapse is institutional, not cinematic.**
   The game is about brittle systems, failing procedures, legal ambiguity, public trust, infrastructure scarcity, bad data, procurement pressure, jurisdictional conflict, and moral triage.

4. **Every decision creates a record.**
   Memos, public statements, emergency orders, emails, legal analyses, and AI-generated drafts can become canon, evidence, political liabilities, or future precedent.

5. **AI is part of the world.**
   The player can use local models, cloud frontier models, archive systems, rumor classifiers, legal retrieval tools, and scenario simulators. These systems consume power, bandwidth, money, time, privacy, and institutional legitimacy.

## MVP Scenario

The first playable scenario is **Northbridge Water Failure**.

Northbridge is a mid-sized Connecticut town facing a cascading water-system crisis caused by heat stress, deferred maintenance, contractor dependency, budget exhaustion, ambiguous lab reports, public rumor, school pressure, hospital vulnerability, and delayed state support.

The player is hired by the Northbridge town manager for a 30-day emergency stabilization engagement.

The MVP campaign covers 10 turns. Each turn represents approximately 3 days.

## MVP Success Criteria

The MVP is successful if:

* A player can complete a 10-turn Northbridge campaign.
* The deterministic engine resolves all state changes through explicit rules.
* Every turn produces a replayable log.
* The player can issue advice through at least one memo-style artifact.
* NPCs can react differently based on faction incentives and prior canon.
* The game remembers prior promises, laws, scandals, and unresolved risks.
* AI tools assist with research, drafting, summarization, and scenario analysis without becoming the source of truth.
* The final campaign dossier is exportable as a coherent institutional-collapse case file.

## Initial Gameplay Loop

1. Client call arrives.
2. Player reviews the situation brief.
3. Player inspects documents, factions, risks, authority, and prior commitments.
4. Player uses optional AI tools for research, drafting, document review, or scenario planning.
5. Player issues advice.
6. NPC client accepts, modifies, ignores, leaks, or weaponizes the advice.
7. Deterministic engine applies consequences.
8. Press, factions, lawyers, agencies, and public actors react.
9. Canon archive updates.
10. Reputation and future engagements shift.

## Initial Tech Direction

The intended architecture is:

```text
React UI
  ↓
FastAPI orchestration layer
  ↓
Deterministic simulation engine
  ↓
SQLite/Postgres canon store
  ↓
Model provider abstraction
  ↓
Structured AI role calls
```

The frontend should feel like an in-world crisis-consulting workstation. As
built, it favors a **guided intake flow** — one screen, one task, one obvious
next action — over a wall of simultaneous panels, with the dense operational
material tucked into an on-demand Case File.

## Repository Status

The **deterministic Northbridge MVP** is implemented and playable end to end,
now with a **guided-intake Continuity Desk** — a one-screen-at-a-time consulting
workflow rather than a dense all-at-once dashboard:

* A framework-free `engine/` package resolves every state change through
  explicit, explainable rules.
* A FastAPI `backend/` exposes the campaign endpoints.
* A React + TypeScript + Vite `frontend/` walks the player through each turn as
  a focused sequence — **intro → incoming call → situation brief → evidence
  review → advice → client decision → consequences → archive → next call /
  dossier** — with exactly one primary action per screen. Dense material
  (full state, all factions, canon, full timeline, raw applied diffs) lives in
  a **Case File** drawer, on demand rather than by default.
* A 10-turn Northbridge campaign can be started, played, won, or lost, with
  per-turn documents, a deterministic consequence stack, full turn history,
  and an exportable case-file dossier.

**A dormant, validation-gated AI-assist layer is present and wired end to end,
but off by default.** The deterministic engine remains the sole authority over
world state. The AI layer (`backend/app/ai/`) provides a memo-drafter tool and
`ModelRun` logging behind a strict validation boundary: model output is
validated against a Pydantic schema, retried once on failure, and replaced by a
deterministic fallback if it still fails. With AI off (the default, and the
state in which the test suite runs), the `/memo` endpoint returns a system
draft and logs a `fallback` run — no network call is made. The Advice phase
exposes an optional **Draft memo** affordance, and the Case File has a **Model
Runs** tab so every AI invocation is inspectable. A live Anthropic provider can
be enabled with `CF_AI_ENABLED=true` and `ANTHROPIC_API_KEY`; absent the
optional `anthropic` extra, even a "live" config degrades safely to fallback.
Per `AGENTS.md`, AI may only *propose* classified facts; only the engine
promotes a fact to canon, and the AI package is tested to never import
state-mutation code.

> Pre-merge review of this branch: see `docs/branch-review.md`. Enforced design
> invariants: see `AGENTS.md` § "Design Invariants".

## Repository Layout

```text
frontend/   React + TypeScript + Vite Continuity Desk workstation
backend/    FastAPI orchestration layer (Pydantic, durable SQLite persistence)
            app/ai/ — dormant, validation-gated AI-assist layer (memo drafter)
engine/     Deterministic simulation engine (no web dependencies)
memory/     Versioned SQLite repository for campaigns, snapshots, and model runs
tests/      pytest suite for engine invariants, content, the turn loop,
            the AI boundary, and HTTP routes
evals/      Reserved for future model-output evaluation harnesses
docs/       Design documents
prompts/    Versioned prompts (memo_drafter.v1.md implemented)
```

## Local Development

### Prerequisites

* Python 3.10+
* Node.js 18+ and npm

### Backend

From the repository root (a root-level venv lets you run the server and the
root-level tests from one environment):

```bash
python -m venv .venv
# Windows PowerShell
. .venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -e "backend[dev]"
uvicorn app.main:app --reload
```

The API is served at `http://localhost:8000` (interactive docs at `/docs`).
The `engine/` and `memory/` packages at the repo root are made importable by
the editable install. Campaigns persist by default in
`data/continuity_failure.sqlite3`; set `CF_DATABASE_PATH` to override it. Stop
the backend before copying that file for backup or deleting it for a clean
reset. To enable the live (Anthropic) AI provider, also install
the optional extra and set two environment variables:

```bash
pip install -e "backend[dev,ai]"
export CF_AI_ENABLED=true
export ANTHROPIC_API_KEY=sk-...
```

With AI off (the default) the memo drafter returns a deterministic system draft
and no network call is made. The test suite runs with AI off.

> Alternative (per-`backend` venv, matching the canonical FastAPI workflow):
> ```bash
> cd backend
> python -m venv .venv
> source .venv/bin/activate      # Windows: . .venv\Scripts\Activate.ps1
> pip install -e ".[dev]"
> uvicorn app.main:app --reload
> ```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs at `http://localhost:5173` and proxies `/api` and
`/health` to the backend, so start the backend first.

### Tests

From the repository root (with the venv active):

```bash
pytest
```

The engine tests exercise only the `engine` package and require no web server.

## MVP Scope (this slice)

Implemented:

* Northbridge seed scenario: 16 state variables, 10 factions (with red lines,
  public/private incentives, pressure), 6 advice options with surfaced
  tradeoffs (benefits, harms, legal/political/operational risk, affected
  factions), 12 evidence documents, and 10 per-turn client calls that cascade
  across the engagement.
* Deterministic turn resolution: NPC decision (followed / partially followed /
  modified / delayed / rejected) with visible mediation (deviation, public
  explanation, private motive, resulting risk), scaled advice effects, ambient
  crisis pressure, and an `AppliedDiff` for every change.
* Deterministic **consequence stack** per turn (immediate, second-order, faction
  reactions, media/rumor framing, legal/procedural fallout, canonized events,
  opened threads) plus accumulating **open threads**.
* Failure thresholds (`water_security`, `hospital_stability`, `public_order`,
  `public_trust`, `budget_capacity`, `state_oversight_risk`, `legal_exposure`)
  and successful 10-turn completion.
* Full turn history, canon archive, and open-thread tracking.
* Durable SQLite storage for complete typed campaigns, append-only end-of-turn
  snapshots, and advisory model-run logs. URL/local-storage campaign IDs resume
  after backend restart, and the intro screen lists recent engagements.
* **Continuity Desk — Guided Intake** web UI: a boot/intro screen, then a
  phased turn flow (incoming call → situation brief → evidence review → advice →
  client decision → consequences → turn archive → next call), each screen with a
  single primary action and a persistent four-indicator header
  (Water Security · Public Trust · Legal Exposure · Hospital Stability). Dense
  material — full 16-variable state, all factions, canon, full timeline, raw
  applied diffs, and the Markdown **campaign dossier** (view / copy / download) —
  lives in an on-demand **Case File** drawer, not the default view.
* Consequences are shown human-readable first (immediate / second-order /
  faction / media / legal / canon / threads), then as a compact
  changed-variables table (old → new), with the raw applied diffs behind an
  expandable "Why did this change?".
* **Dormant, validation-gated AI-assist layer.** A memo drafter
  (`POST /api/campaigns/{id}/memo`) drafts an advisory memo for a selected
  advice option, surfaced in the Advice phase as an optional "Draft memo"
  affordance with honest "AI draft" / "System draft (fallback)" provenance
  labeling. Model output is validated against a Pydantic schema, retried once
  on failure, and replaced by a deterministic fallback otherwise. Every call
  (success, invalid, or fallback) is logged as a `ModelRun` and inspectable via
  a read-only **Model Runs** tab in the Case File. AI is off by default; the
  diegetic system-status indicator reflects whether a live provider is
  configured. The AI package is tested to never import state-mutation code.

Intentionally **not** implemented yet:

* The broader in-world AI toolset beyond the memo drafter (local/cloud/archive
  models, research console, rumor classifier, scenario simulator, document
  review) and their resource costs (power, bandwidth, privacy, latency).
* Autonomous agents and multi-agent behavior.
* Vector database / semantic memory.
* Statewide or regional gameplay beyond the town level.
* Authentication and deployment tooling.

The memo drafter *is* implemented (off by default): it drafts an advisory memo
for a selected advice option, validates model output against a schema, falls
back to a deterministic system draft on any failure, and logs every call as a
`ModelRun`. It never advances the turn or changes world state.

## Recommended Next Step

The deterministic loop is document-rich, the Continuity Desk is playable end to
end, and the first AI-assist tool (memo drafter + `ModelRun` logging) is wired
through the UI behind the validation boundary, and campaign/model-run records
now survive backend restarts in SQLite. The next step is to **extend the
AI-assist layer with the remaining read-only tools and in-world costs**:

1. Add a validated Research Console that only *proposes* classified facts
   (proposed / unverified / rumor), never canon — the engine remains the sole
   authority over world state.
2. Layer additional model-assisted artifacts (faction-reaction text, press
   framing, canon summaries) behind structured-output validation, reusing the
   `run_artifact` boundary and deterministic fallbacks already in place.
3. Add in-world AI tool costs (power, bandwidth, privacy, latency, confidence)
   so the memo drafter and later tools carry gameplay tradeoffs.
4. Add retention/export policy for durable advisory model payloads before live
   model use expands.

See `docs/branch-review.md` for the full branch review.

