# Frontend testing

Two layers protect the Continuity Desk's critical journeys:

- **Component / integration tests** (Vitest + Testing Library, jsdom) — fast,
  in-process, no browser and no backend. They render real components against a
  fake `fetch` that replays payloads captured from the real engine.
- **End-to-end tests** (Playwright + Chromium) — a real browser driving the
  production build, proxied to a real FastAPI process backed by a real, isolated
  SQLite file. Durable resume and at-most-once turn resolution are proven here,
  against the actual backend, not a mock of it.

Both layers query the UI the way a player perceives it — by accessible role and
visible name. Test ids are deliberately absent; if a control stops being
reachable by role and name, that is a real regression.

## One-time setup

From `frontend/`:

```bash
npm install                    # test deps are in devDependencies
npx playwright install chromium   # ~120 MB browser download, once per machine
```

The end-to-end suite starts the backend itself, so the backend's Python
dependencies must be importable. From the repo root, if you have not already:

```bash
pip install -e "backend[dev]"
```

The suite launches the backend with `python -m uvicorn`. If your interpreter is
not named `python` (e.g. you use `py` or a venv path), point the suite at it:

```bash
CF_PYTHON=/path/to/python npm run test:e2e     # macOS / Linux / Git Bash
$env:CF_PYTHON="C:\path\to\python.exe"; npm run test:e2e   # PowerShell
```

## Commands

| Command | What it does |
| --- | --- |
| `npm test` | Component/integration tests once (Vitest). |
| `npm run test:watch` | Same, in watch mode. |
| `npm run test:e2e` | Full end-to-end suite (builds, serves, runs Chromium). |
| `npm run test:e2e:report` | Open the HTML report from the last e2e run. |
| `npm run typecheck` | Type-check the app **and** the test code. |
| `npm run test:ci` | `typecheck` → Vitest → Playwright. The single CI gate. |
| `npm run test:fixtures` | Regenerate the captured API fixtures (see below). |

Backend tests are separate and run from the repo root: `pytest -q`.

## Test database behavior

The end-to-end backend uses its own throwaway database at
`frontend/.e2e/e2e.sqlite3` (via the backend's `CF_DATABASE_PATH` setting). It
is **never** your local `data/continuity_failure.sqlite3` — a playthrough on
your machine is never read, mutated, or deleted by the suite.

Every run wipes that file first, so each run starts from an empty archive. The
`.e2e/` directory (database, backend log, pid file) is git-ignored and safe to
delete.

The backend is owned by `e2e/global-setup.ts` / `global-teardown.ts` rather than
by Playwright's `webServer`, because one journey restarts it mid-run to prove a
campaign survives a backend process restart against the same database. Fixed
ports are used (backend `8100`, preview `4173`) so the proxy target stays stable
across that restart.

## Fixtures (component tests)

`tests/fixtures/*.json` are captured from a real Northbridge campaign resolved
by the real engine and Pydantic schemas — not hand-authored. That way a change
to a backend response shape breaks the component tests instead of silently
passing against a stale object. Regenerate them after an intentional API change:

```bash
npm run test:fixtures
```

The generator uses its own temporary database and never touches real saves.

## What is covered

| Journey | Where |
| --- | --- |
| Resolve a turn; see its snapshot; next-turn data stays hidden until Next Call | `e2e/turn-flow.spec.ts`, `tests/App.test.tsx` |
| Next Call advances exactly once | `e2e/turn-flow.spec.ts`, `tests/App.test.tsx` |
| Resume from URL / local storage; resume after a backend restart | `e2e/resume.spec.ts` |
| Retry with the same idempotency key does not duplicate a turn | `e2e/idempotency.spec.ts`, `tests/apiClient.test.ts` |
| Terminal campaign cannot advance; dossier stays usable | `e2e/terminal.spec.ts` |
| Core turn flow, drawers, and overlays operate by keyboard | `e2e/keyboard.spec.ts` |
| Narrow + wide viewports: no clipped controls, no horizontal overflow | `e2e/responsive.spec.ts` |
| API loading / error / retry states; restart confirmation | `tests/CampaignDossier.test.tsx`, `tests/apiClient.test.ts`, `tests/App.test.tsx` |
| Accessibility smoke (structural WCAG A/AA, serious+critical) | `e2e/accessibility.spec.ts` |

The accessibility scan is a smoke check, not a substitute for the explicit
keyboard test — axe cannot tell you whether the game is playable without a mouse.

## Common local failures

- **`Something is already serving http://127.0.0.1:8100`** — a previous e2e
  backend did not shut down. Delete `frontend/.e2e/backend.pid` (kill that pid
  first if it is still alive), or just re-run: global setup reclaims a stale pid.
- **`Timed out waiting for backend /health`** — the backend could not start.
  Read `frontend/.e2e/backend.log`. Usually the interpreter lacks the backend
  deps; set `CF_PYTHON` (see setup) or `pip install -e "backend[dev]"`.
- **`webServer` timed out** — the production build or `vite preview` failed.
  Run `npm run build` on its own to see the real error.
- **Port 4173 in use** — a leftover `vite preview`. Stop it and re-run;
  `reuseExistingServer` is off so the suite always serves a fresh build.
- **`browserType.launch: Executable doesn't exist`** — run
  `npx playwright install chromium`.
