# Continuity Failure Codebase Review

> **Status: post-remediation.** This review was first written against `main`
> at commit `b30cf1d` ("phase two and three") and identified a set of Critical /
> High / Medium findings. A remediation pass has since been applied (untracked
> build artifacts, wired the AI seam into the UI, made `_system_status` honest,
> converted the engine-independence test to AST-based, added HTTP route tests,
> and reconciled all docs with the shipped code). This document now records
> both the original findings **and** their resolution, so the history is
> auditable. Open items are marked **OPEN**; resolved items are marked
> **RESOLVED** with evidence.

## Executive Verdict

The repository is **coherent, runnable, and now truthfully documented**. The
deterministic Northbridge MVP is solid: 156 tests pass, the engine is
framework-free (verified by an AST scan, not a fragile `sys.modules` check),
the 10-turn loop completes or fails deterministically, every mutation emits an
`AppliedDiff`, and NPC mediation is real. The frontend builds clean, the
guided-intake UX is a genuine improvement over a dashboard, and the AI-assist
layer — a dormant, validation-gated memo drafter with `ModelRun` logging — is
now wired end to end (backend routes + frontend Advice-phase affordance + Case
File Model Runs tab) and honestly labeled.

The biggest risk identified in the first pass — **documentation broadly denying
the existence of a shipped AI layer** — is **resolved**: README, AGENTS,
architecture, game-loop, state-schema, mvp-roadmap, branch-review,
prompts/README, project-spec, and the FastAPI app description string all now
describe the AI layer accurately (present, dormant by default, validation-gated,
degrades to deterministic fallback, never mutates state). The half-wired AI seam
is resolved (frontend can now reach `/memo` and `/model-runs`). Route coverage
is resolved (21 new `TestClient` tests). Tracked build artifacts are untracked.

**The codebase is now ready for the next layer** (the remaining read-only AI
tools, then durability). The remaining open items are low-severity content and
scaling debts, none of which block forward progress.

- Coherent? Yes.
- Playable/runnable? Yes — `pytest` (156 passed), `npm run build` (clean),
  backend imports and serves, full 10-turn campaign + memo draft smoke-tested
  end to end through the HTTP API.
- Aligned with intended product? Yes, and now documented accurately.
- Biggest remaining risk: **substantially reduced.** The `DECIDER` hardcode is
  **RESOLVED** (the decider is now the current caller), the immediate
  consequence-text repetition is **RESOLVED** (deterministic per-turn
  variation), and the missing schema-contract test is **RESOLVED**
  (`tests/test_contract.py` now enforces engine↔Pydantic↔TS agreement). See the
  Test, Content, and Determinism sections below for evidence.

## Current Implementation Summary

What exists now (verified by reading the code):

- **`engine/`** — framework-free deterministic engine: 16 clamped state
  variables, 10 factions with red lines/incentives/pressure, 6 advice options
  with surfaced tradeoffs, 12 documents, 10 cascading client calls, NPC decision
  logic with visible mediation, ambient drift, deterministic consequence stacks,
  open threads, failure thresholds, 10-turn completion, Markdown dossier.
- **`backend/`** — FastAPI + Pydantic v2. Endpoints: `/health`,
  `POST/GET /api/campaigns[/{id}]`, `/current`, `/advice`, `/turns`, `/dossier`,
  `/memo` (advisory memo draft), `/model-runs` (read-only AI run log).
  In-memory `CampaignStore`. Service layer delegates to engine. **AI-assist
  package `backend/app/ai/{provider,runner,schemas,fallbacks,logging}.py`** with
  a `NullProvider` default, an `AnthropicProvider` (optional `ai` extra), a
  validation boundary (`run_artifact`: call → validate → retry once →
  deterministic fallback), `ModelRun` logging, and `Settings` (AI off by
  default; live only when `CF_AI_ENABLED` + `ANTHROPIC_API_KEY` both set).
- **`frontend/`** — React 18 + TS + Vite, plain CSS. Guided intake flow
  (INTRO → CALL → BRIEF → EVIDENCE → ADVICE → CLIENT_DECISION → CONSEQUENCES →
  ARCHIVE → DOSSIER), one primary action per screen, four-indicator header,
  on-demand Case File drawer. **AI seam wired**: `api/client.ts` has
  `draftMemo`/`getModelRuns` + `MemoDraft`/`ModelRun` types; the Advice phase
  has a "Draft memo" affordance rendering `MemoDraftPanel` with honest
  "AI draft" / "System draft (deterministic fallback)" provenance; the Case File
  has a "Model Runs" tab (`ModelRunPanel`).
- **`memory/`** — in-memory `CampaignStore`/`MemoryStore` (thread-safe).
- **`tests/`** — 156 tests: engine turns (incl. AST-based independence), state
  invariants, content/dossier, AI boundary, AI runner, AI memo service path,
  and HTTP route tests (`TestClient`) for all endpoints + error paths.
- **`prompts/`** — `memo_drafter.v1.md` (implemented, wired to `run_artifact`).

## Commands Run (post-remediation)

| Command | Result |
| --- | --- |
| `python -m pytest -q` | **156 passed** in 1.13s |
| `cd frontend && npm run build` (`tsc -b && vite build`) | **Clean** — 59 modules, ~730ms, no type errors |
| `python -c "from app.main import app"` | Backend imports OK; 13 routes incl. `/memo`, `/model-runs` |
| `TestClient` smoke (create → `/current` → `/memo` → `/model-runs`) | `ai_available=False`, `model_status="AI assist present — off by default (returns system drafts)"`, memo `status=fallback source=system`, 1 run logged |
| `git ls-files 'frontend/*.tsbuildinfo'` | **Empty** (artifacts untracked) |

## Major Findings

### Critical

**C1. Documentation broadly claimed "no AI/model calls exist" while a complete
AI layer was implemented. — RESOLVED.**

- Original evidence: `backend/app/ai/*`, `prompts/memo_drafter.v1.md`,
  `tests/test_ai_*`, `/memo`, `/model-runs`, `config.py` all shipped in
  `b30cf1d`, while README, architecture, branch-review, mvp-roadmap,
  project-spec, prompts/README, AGENTS, and `main.py` all denied AI existence.
- Resolution: All ten docs/string updated. README "Repository Status" and
  "Recommended Next Step" now describe the dormant, validation-gated AI layer;
  AGENTS.md Design Invariants #3 and #6 are present-tense and reference the
  AST-based independence test; `docs/architecture.md` "Current Architecture"
  includes `app/ai/`, "Intentionally Not Present Yet" lists only the *remaining*
  tools; `docs/branch-review.md` "What is intentionally still missing" and
  "What is unchanged" corrected; `docs/mvp-roadmap.md` Week 3 task list marked
  with ✅/⏳ status; `docs/game-loop.md`, `docs/state-schema.md`,
  `docs/project-spec.md`, `prompts/README.md`, and the `main.py` description
  string all corrected. A grep for the old denial strings
  (`"no AI/model calls"`, `"AI integration is intentionally not"`,
  `"no prompt files exist"`, `"50 passing"`) now returns no hits outside this
  review document.
- Why it mattered / matters: the project's central design rule ("database is
  canon, model is not") is only credible if docs truthfully locate the AI code.
  Now they do.
- Blocks next merge? No — resolved.

### High

**H1. AI feature was wired backend-only; frontend could not reach `/memo` or
`/model-runs`. — RESOLVED (wired).**

- Resolution: `frontend/src/api/client.ts` gained `MemoDraft`/`ModelRun`
  interfaces and `draftMemo`/`getModelRuns` methods. New
  `MemoDraftPanel` renders the draft with honest provenance labeling
  (`status === "ok" && source === "ai"` → "AI draft", else "System draft
  (deterministic fallback)"). New `ModelRunPanel` renders the read-only run log.
  `AdvicePhase` gained an optional "Draft memo" affordance (shown when an option
  is selected); `App.tsx` holds memo state and a `handleDraftMemo` callback that
  clears on option-change and new-turn; `CaseFile` gained a "Model Runs" tab.
  CSS added for both panels. `npm run build` clean.
- Note: the memo is advisory-display only (no accept/edit yet — that is a
  deliberate future task, tracked in `mvp-roadmap.md` Week 3 task 10).
- Blocks next merge? No — resolved.

**H2. No HTTP/route-level tests existed despite `httpx` being a dev dep.
— RESOLVED.**

- Resolution: `tests/test_api.py` added with 21 `TestClient` tests covering:
  `/health`; create (default + named); get campaign + 404; `/current` + 404;
  `/advice` (advances turn, 400 unknown advice, 404 unknown campaign, 409
  terminal); full campaign completion + `/turns`; `/dossier` + 404; `/turns`
  404; `/memo` (fallback, no-state-change, logs a run, 400 unknown advice, 404
  unknown campaign, works on terminal campaign); `/model-runs` (404, empty for
  new campaign). Store-isolation fixture clears `CampaignStore` and
  `ModelRunStore` per test.
- Blocks next merge? No — resolved.

**H3. Tracked build artifacts that should be gitignored. — RESOLVED.**

- Resolution: `git rm --cached` removed `frontend/tsconfig.tsbuildinfo`,
  `frontend/tsconfig.node.tsbuildinfo`, `frontend/vite.config.d.ts`,
  `frontend/vite.config.js`. `frontend/.gitignore` extended with
  `*.tsbuildinfo`, `vite.config.d.ts`, `vite.config.js`. Working-tree files
  preserved (now ignored, not deleted). `git ls-files` confirms none tracked.
- Blocks next merge? No — resolved.

### Medium

**M1. `_system_status` lied about AI availability. — RESOLVED.**

- Resolution: `campaign_service._system_status` now reads `settings.ai_live`
  and `get_provider(settings)`, returning `ai_available=True` with a
  "Live AI assist active (<provider> provider)" message only when a live
  provider is configured; otherwise `ai_available=False` with "AI assist present
  — off by default (returns system drafts)". `SystemStatusModel` docstring and
  default `model_status` updated to match. Smoke test confirms the honest
  off-by-default message.
- Blocks next merge? No — resolved.

**M2. Tests claimed "50 passing"; actual was 72, now 96. — RESOLVED.**

- Resolution: All "50 passing" references in `docs/architecture.md` and
  `docs/branch-review.md` updated to "96 passing" with accurate coverage
  descriptions.

**M3. The AI boundary test is structurally sound but narrow. — OPEN (low).**

- The AST import-boundary test (`test_ai_layer_cannot_mutate_game_state`) plus
  the runtime `test_draft_memo_does_not_change_world_state` together enforce
  the invariant. The runtime test is the real guarantee. A dynamic-import
  (`importlib`) path would still evade the AST check, but this is a low-likelihood
  future risk, not a current defect. No change made.

**M4. `test_engine_does_not_import_fastapi` was fragile and overspecified.
— RESOLVED.**

- Resolution: Replaced the `sys.modules`-based assertion with two AST-based
  tests: `test_engine_does_not_import_fastapi` (scans `engine/*.py` for
  `fastapi`/`uvicorn`/`starlette`/`pydantic` imports) and
  `test_engine_imports_only_stdlib_and_itself` (asserts every top-level import
  is stdlib or `engine`). These are order-independent and unaffected by what
  other tests import — which is what unblocked adding the `TestClient` route
  tests (H2) in the same suite. AGENTS.md Design Invariant #6 updated to
  reference the AST form.
- Blocks next merge? No — resolved.

**M5. Two venvs at root (`.venv/`, `.venv-1/`). — OPEN (low, environmental).**

- Both are gitignored (not tracked). Cosmetic / local-hygiene only. The README
  documents a root venv; `docs/branch-review.md` documents a per-`backend`
  venv. Pick one canonical workflow in a future docs pass. No code impact.

### Low

**L1. Typo "Scrutinity" → "Scrutiny"** (`engine/rules.py:111`). — OPEN.
Comment-only. Trivial fix when next touching that file.

**L2. `_risk_label` in `engine/dossier.py` is vestigial.** — OPEN. Ignores its
`variable` arg. Inline or give it a real risk-direction label in a future pass.

**L3. `frontend/package.json` has a non-standard `allowScripts` field** (pnpm
artifact). — OPEN. Inert under npm. Remove if npm is canonical.

**L4. `Crisis` entity is near-vestigial** (severity updated, no status lifecycle).
— OPEN. Either implement `OPEN/ESCALATING/STABILIZING/RESOLVED/FAILED` or drop
the pretense in `state-schema.md`. Not blocking.

## Architecture Review

- **Engine purity: strong.** `engine/` imports only stdlib + itself, now
  verified by AST scan (not `sys.modules`). No Pydantic, no HTTP, no IO.
- **Backend thickness: good.** Routes are thin — parse, call service, map
  exceptions to HTTP codes, return. All game logic delegates to
  `turn_engine.advance_turn`. The service is the only place engine + memory +
  AI meet.
- **AI boundary: well-designed, tested, and now wired.** `run_artifact`
  (render → call → validate → retry once → deterministic fallback → log) is the
  right shape. `NullProvider` keeps the layer dormant by default. AST + runtime
  tests enforce "AI cannot write state." The frontend now reaches it honestly.
- **Persistence: clearly separated.** `memory/persistence.py` is the only
  mutable campaign container; `ModelRunStore` mirrors it. Both in-memory.
- **Frontend authority: correct.** The frontend computes no game outcomes —
  only display aggregation (`aggregateChanges`) and label derivation.
- **API ↔ frontend contract: now complete.** The AI types (`MemoDraft`,
  `ModelRun`) are duplicated faithfully across Pydantic → TS, matching the
  deterministic types. **No contract test enforces this duplication** — see
  Open Items.
- **Boundary violation: none.**

## Gameplay / Product Review

Unchanged from the first pass — the remediation did not touch game logic. The
build supports the intended consulting simulator well: player advises / NPCs
decide (real, visible mediation); consequences are legible (human-readable
stack first, raw diffs behind an expander); advice choices are meaningful and
non-obviously-optimal; Northbridge feels civic, not apocalyptic; failure is
reachable and meaningful; completion generates a dossier; canon/open-threads
support play.

**New:** the Advice phase now has an optional memo-drafting affordance, which
adds a sliver of the "consultant writing a memo" fantasy that was previously
thinnest. The memo is advisory display only (no accept/edit) — a deliberate
future task.

## UX Review

Unchanged structure; the AI wiring adds two affordances without crowding the
guided flow:

- The "Draft memo" button appears only when an advice option is selected, below
  the option list. It renders a `MemoDraftPanel` with honest provenance. It does
  not interrupt the one-primary-action-per-screen discipline (Send Advice
  remains the primary action; Draft memo is a secondary, optional affordance).
- The Case File gains a "Model Runs" tab alongside Evidence/Factions/Full
  State/Canon/Timeline/Dossier — correctly optional, dense, inspectable.

Remaining UX suggestions from the first pass still apply (collapsing advice
cards by default, an `adherence` plain-gloss, contextual Case File hints, header
indicator delta flashes) — none blocking, none addressed by this remediation.

## Scenario Content Review

Northbridge content remains specific, plausible, well-structured, and
internally consistent. The two content weaknesses identified originally are now
**RESOLVED**:

- **Immediate-consequence text repeats** across same-tag turns
  (`controlled_disclosure` appeared 4× in the survival sequence with identical
  immediate lines). — **RESOLVED.** `engine/consequences.py` `_immediate_for`
  now prepends a deterministic per-turn opener that names the turn's specific
  caller and engagement phase (opening/mid-crisis/closeout), so the four
  `controlled_disclosure` turns (1, 4, 6, 9 — Town Manager, Contractor, State
  Liaison, Public Works) each read differently. The variation is a pure
  function of `(advice, decision, state, turn)`; determinism is preserved and
  covered by `test_immediate_consequence_text_varies_per_turn` and
  `test_immediate_consequence_variation_is_deterministic`.
- **Advice options are global, not per-turn** — turn 2's school-closure call
  had no school-specific advice option. — **RESOLVED.**
  `Campaign.per_turn_advice` (turn → options) now adds a staged school-closure
  protocol (turn 2), a hospital priority allocation (turn 3), and a
  business-compensation framework (turn 7), merged in by
  `Campaign.available_advice()`. Each has full tradeoff fields, at least one
  stated harm, a deterministic `effects` map, and a dedicated `_decide_*`
  handler in `engine/rules.py`. Covered by
  `test_per_turn_advice_is_available_on_its_turn_only` and the extended
  `test_no_advice_option_is_purely_optimal`.

## State Model and Determinism Review

Bounds enforced, invariants strong, failure thresholds correct, completion
logic correct, NPC logic deterministic, determinism bit-for-bit tested.

- **`rules.DECIDER` hardcoded to "Town Manager's Office"** — hospital/contractor/
  state turns were all attributed to the Town Manager. — **RESOLVED.**
  `engine.rules._resolve_decider` now derives `NpcDecision.decider` from
  `campaign.current_call().caller` (falling back to the Town Manager's Office
  only when no call is present), and `_build_rationale` uses the resolved
  decider. `build_aftermath_summary` already embedded `decision.decider`, so
  the aftermath text now names the correct client while remaining bit-for-bit
  reproducible (same caller ⇒ same text). Covered by
  `test_decider_is_the_current_caller_not_hardcoded`; the determinism tests
  still pass.

Remaining fragile assumptions (still **OPEN**, lower priority):

- `update_faction_postures` keyed on hardcoded faction ids.
- `_ADVICE_TAG_DISPATCH` now handles 8 tags (the original 5 plus
  `school_closure`, `hospital_priority`, `business_compensation`); a silent
  generic fallback still applies to any future untagged advice.
- `player_shadow_authority` barely simulated (only `state_support` +3 moves it).

## Test Review

- **Count: 156 tests, all passing** (the 146-test content/correctness baseline
  plus regression coverage for synchronized turn snapshots, humanized outcome
  prose, strict request payloads, memo operational steps, and AI token bounds).
  The earlier content pass added 46 parametrized schema-contract checks in
  `tests/test_contract.py` plus decider, per-turn-advice, and consequence-
  variation tests. The earlier
  96 came from +24 over the original 72 (2 AST-based engine-independence tests
  replacing 1 fragile one, plus 21 `TestClient` route tests).
- **Coverage by area:** state invariants, turn flow/failure/completion/
  determinism, engine AST-independence, content/dossier, AI boundary (AST +
  runtime), AI runner (success/retry/fallback/transport-error/off), AI memo
  service path, and HTTP routes (all endpoints + 400/404/409 error paths +
  memo/model-runs + terminal-campaign memo).
- **Core invariants protected: yes** — bounds, diffs, failure thresholds,
  completion, NPC mediation, consequence stack, engine independence (AST), AI
  state-mutation boundary (AST + runtime).
- **Previously-lacking tests, now added:**
  - **Schema-contract test** between the engine dataclasses, the Pydantic
    models, and the TS interfaces. — **RESOLVED.** `tests/test_contract.py`
    introspects `Model.model_fields` vs `dataclasses.fields` for every entity
    that crosses the boundary (Faction/Crisis/AdviceOption/ClientCall/Document/
    OpenThread/WorldState/AppliedDiff/NpcDecision/CanonEntry/FactionReaction/
    ConsequenceStack/TurnResult, plus Campaign→summary), asserting field-set
    parity **and** structural type compatibility on the dangerous `asdict` leg,
    and field-name parity against the `client.ts` interfaces (parsed with a
    dependency-free regex). A rename or type change in any exposed engine
    dataclass now breaks a test (verified by a temporary rename during
    development).
  - **`DECIDER` test.** — **RESOLVED.**
    `test_decider_is_the_current_caller_not_hardcoded` asserts the decider
    equals the caller for the hospital (3), contractor (4), and state-liaison
    (6) turns.
- **Brittle tests: none remaining.** The fragile `sys.modules` test was
  replaced (M4).

## Documentation Drift Review

All rows below are **RESOLVED** unless marked OPEN.

| Document | Original Accuracy | Resolution |
| --- | --- | --- |
| `README.md` | Wrong on AI. | RESOLVED — Repository Status, MVP Scope, Layout, Local Dev (optional `ai` extra), and Recommended Next Step rewritten to describe the wired, dormant AI layer. |
| `AGENTS.md` | Silent on AI existence; invariants future-tense. | RESOLVED — Invariant #3 present-tense with test references; #6 references AST form; Current Priority updated. |
| `docs/architecture.md` | Wrong on AI; "50 passing." | RESOLVED — Current Architecture includes `app/ai/`; Not Present lists only remaining tools; structure tree updated; Frontend/Backend status notes updated; "96 passing." |
| `docs/game-loop.md` | AI phase claim stale. | RESOLVED — "AI assist (as built)" block added describing the memo affordance; Planned next narrowed to remaining tools. |
| `docs/state-schema.md` | "ModelRun not implemented." | RESOLVED — Notes partial (logging-only) implementation with endpoint and field-set caveat. |
| `docs/mvp-roadmap.md` | Week 3 "Planned next"; "50 passing." | RESOLVED — Week 3 task list marked ✅/⏳; status header updated. |
| `docs/branch-review.md` | "No AI/model calls"; "50 passing." | RESOLVED — "What is intentionally still missing" and "What is unchanged" corrected; New API surface includes `/memo`+`/model-runs`; test count + how-to-test updated. |
| `prompts/README.md` | "No prompt files exist yet." | RESOLVED — States `memo_drafter.v1.md` is implemented and wired. |
| `backend/app/main.py` description | Wrong string. | RESOLVED — Description now describes the dormant, validation-gated AI layer. |
| `docs/project-spec.md` | "Out of scope: all in-world AI tools." | RESOLVED — Narrowed to tools beyond the memo drafter. |
| `docs/codebase-review.md` | (this document) | RESOLVED — Rewritten post-remediation (this revision). |

## Technical Debt

Resolved by the earlier remediation: docs drift (1), half-wired AI surface (2),
no route tests + fragile independence test (3, coupled — fixed together),
tracked build artifacts (7), `_system_status` dishonesty (6).

Resolved by this content/correctness pass:

1. ~~**Duplicated schema contract with no enforcement.**~~ — **RESOLVED.**
   `tests/test_contract.py` enforces engine↔Pydantic↔TS agreement; a rename or
   type change on the boundary now fails a test.
2. ~~**`DECIDER` hardcoded to Town Manager.**~~ — **RESOLVED.** The decider is
   derived from the current caller (`engine.rules._resolve_decider`).
3. ~~**Static immediate-consequence text repeats** across same-tag turns.~~ —
   **RESOLVED.** Deterministic per-turn variation in `_immediate_for`.
4. ~~**Advice options are global, not per-turn.**~~ — **RESOLVED.**
   `Campaign.per_turn_advice` adds turn-specific options for turns 2, 3, 7.

**Remaining open debts (priority order):**

1. **`Crisis` lifecycle unimplemented** despite schema defining statuses.
2. Two venv workflows documented (cosmetic).
3. Low: "Scrutinity" typo, vestigial `_risk_label`, `allowScripts` field.

None of this is overengineering — the codebase is lean. The remaining debts are
low-severity cosmetics and one unimplemented entity lifecycle, not excessive
abstraction.

## Recommended Next Steps

### Immediate cleanup before further feature work
1. ~~Reconcile docs with shipped AI layer (C1).~~ **Done.**
2. ~~Untrack build artifacts (H3).~~ **Done.**
3. ~~Decide AI-seam fate (H1) + fix `_system_status` (M1).~~ **Done — wired.**

### Next implementation branch/pass
1. ~~**Add a schema-contract test.**~~ **Done** — `tests/test_contract.py`.
2. ~~**Fix `DECIDER` to use the current caller** and add a test.~~ **Done** —
   `engine.rules._resolve_decider` + `test_decider_is_the_current_caller_not_hardcoded`.
3. ~~**Add per-turn variation to immediate consequence text** and 2–3
   turn-specific advice options.~~ **Done** — `_immediate_for` opener +
   `Campaign.per_turn_advice` (turns 2, 3, 7).

### Later, not now
1. Durable persistence (SQLite canon store) — only after the AI read/write
   boundary is proven (it now is, with tests) and the contract test exists.
2. The full AI Research Console (in-world tool costs, local/cloud distinction,
   scenario simulator) — the memo drafter is a good first step; do not build the
   rest until the memo's accept/edit path and tool costs are designed.
3. `Crisis` lifecycle, `EvaluationResult`, `AdviceMemo` entities.
4. Statewide/regional progression.

## Final Recommendation

**The next pass should be scenario/content improvement + the contract test,
not architecture cleanup** — because the architecture cleanup is done.

Concretely, in order: **(1) schema-contract test, (2) fix `DECIDER`, (3)
consequence-text variation + per-turn advice options.** After that, resume AI
Research Console work (accept/edit for memos, then the remaining read-only
tools) or persistence.

Not architecture cleanup first (that is complete). Not UX simplification first
(the guided flow is sound; the AI affordances fit without crowding). Not AI
integration first (the first AI tool is wired and tested; expand it after the
contract test and content variety land). Not persistence first.

## Final Note

The deterministic foundation remains genuinely good work, and the
remediation has closed the gap between what the docs said and what the code
does. The AI layer is now honestly described, wired end to end, tested at both
the service and HTTP levels, and correctly bounded. The remaining work is
content variety, one semantic hardcode, and a contract test — not architecture.
