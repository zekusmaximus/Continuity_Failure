# Continuity Failure — Backend

FastAPI orchestration layer for the **Northbridge Water Failure** MVP.

The backend never mutates world state directly. It receives requests, calls the
deterministic `engine` package, and serializes the result. A validation-gated
AI-assist layer is implemented for advisory memo drafting and is **off by
default**. With AI off, memo requests return a deterministic system draft; no
model call can mutate authoritative state.

## Layout

```
backend/
  pyproject.toml          # installable project; also wires engine/ and memory/
  app/
    main.py               # FastAPI app, CORS, /health
    repository.py         # configurable SQLite repository construction
    api/campaigns.py      # /api/campaigns routes
    services/
      campaign_service.py # engine <-> SQLite repository <-> pydantic bridge
    schemas/api.py        # Pydantic request/response models
    ai/                   # provider, validation runner, memo fallback, run log
    config.py             # offline-first AI settings
```

The `engine/` and `memory/` packages live at the repository root. They are made
importable from this project via the `package-dir` mapping in `pyproject.toml`,
so a single editable install covers all three.

## Setup

From the repository root (a project-level venv is convenient because tests run
from the root):

```bash
python -m venv .venv
# Windows PowerShell
. .venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -e "backend[dev]"
```

> The project README documents a per-`backend` venv alternative
> (`cd backend && python -m venv .venv`). Both work; the only requirement is
> that the editable install of the backend project is active so `app`,
> `engine`, and `memory` resolve.

## Run

```bash
uvicorn app.main:app --reload
```

The API is served at `http://localhost:8000`. Interactive docs:
`http://localhost:8000/docs`.

## Endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET    | `/health` | Service liveness + active scenario id |
| POST   | `/api/campaigns` | Start a new Northbridge campaign |
| GET    | `/api/campaigns?limit=5` | Minimal recent-campaign metadata for resume |
| GET    | `/api/campaigns/{id}` | Campaign summary + current world state |
| GET    | `/api/campaigns/{id}/current` | Current turn package (state, call, advice, last turn) |
| POST   | `/api/campaigns/{id}/advice` | Submit advice, resolve NPC decision, advance one turn |
| GET/POST | `/api/campaigns/{id}/memos` | List or create persistent manual/AI-assisted memo drafts |
| PATCH  | `/api/campaigns/{id}/memos/{memo_id}` | Save a new player-authored draft revision |
| GET    | `/api/campaigns/{id}/turns` | Full turn history + canon archive |
| GET    | `/api/campaigns/{id}/dossier` | Campaign dossier as Markdown |
| POST   | `/api/campaigns/{id}/memo` | Draft an advisory memo without advancing state |
| GET    | `/api/campaigns/{id}/model-runs` | Read-only AI/model run log |

`POST /api/campaigns` accepts an optional `{"name": "..."}` body.
`POST /api/campaigns/{id}/advice` requires `advice_id`, `expected_turn`, a
bounded `idempotency_key`, and the attached `memo_id` / `memo_revision`.
Request bodies reject unknown fields and enforce bounded names and advice IDs.

To enable the optional Anthropic provider, install `backend[ai]` and set both
`CF_AI_ENABLED=true` and `ANTHROPIC_API_KEY`. `CF_AI_MAX_TOKENS` is bounded to
64–8192 output tokens. Without a live provider configuration, the memo endpoint
remains available through its deterministic fallback.

## Persistence

Campaigns (including versioned `AdviceMemo` aggregates), immutable end-of-turn
snapshots, and complete advisory `ModelRun` records are stored in SQLite through
`memory/persistence.py`. A sent memo's exact content, digest, provenance, and
revision are copied into the immutable turn snapshot in the same transaction as
the NPC decision and AppliedDiff record. The default file
is `data/continuity_failure.sqlite3` at the repository root. Override it with
`CF_DATABASE_PATH` (an absolute path is recommended for service deployments):

```bash
export CF_DATABASE_PATH=/path/to/continuity_failure.sqlite3
```

The repository uses Python's standard-library `sqlite3`. Schema changes are
tracked in `schema_migrations`; campaign, snapshot, and model-run JSON envelopes
currently use document version 1. Tests always override the path with isolated
temporary databases.

To back up local play, stop the backend and copy the database file. To reset
local play, stop the backend and delete that file; it is recreated and migrated
on the next request. SQLite files are ignored by git.

## Tests

Run from the repository root:

```bash
pytest
```
