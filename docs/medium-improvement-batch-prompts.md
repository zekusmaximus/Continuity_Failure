# Medium Improvement Batch Prompts

These prompts turn the medium-priority roadmap from the comprehensive engineering and UX review into eight implementation batches. Run them in order, one prompt per fresh Codex chat.

Before starting Batch 1, make a checkpoint of the current quick-win work if it has not already been committed. Each later batch assumes the earlier batches are present and the repository is green. The prompts still require Codex to inspect the actual worktree rather than trusting a stated test count or stale documentation.

## Recommended order

| Batch | Outcome | Depends on |
| --- | --- | --- |
| 1 | Durable SQLite campaigns, snapshots, model runs, and resume UI | Current quick-win baseline |
| 2 | Atomic and idempotent turn resolution, request IDs, structured logs | Batch 1 |
| 3 | Frontend test harness and critical end-to-end coverage | Batches 1–2 |
| 4 | First-turn onboarding and accessible navigation/overlays | Batch 3 |
| 5 | Versioned scenario content files and strict content validation | Batch 1 |
| 6 | Call-specific advice and faction-aware deterministic decisions | Batch 5 |
| 7 | Persistent memo artifact workflow with exact provenance | Batches 1, 2, and 6 |
| 8 | Causal consequence visualization and integrated regression pass | Batches 3, 6, and 7 |

## Batch 1 — Durable persistence and resume

```text
You are implementing the first medium-priority improvement batch in the Continuity Failure repository at C:\Users\Jeff\Projects\Continuity_Failure. Complete the implementation end to end; do not stop at a design proposal.

# Goal

Replace process-local campaign and model-run storage with durable SQLite persistence. A player must be able to restart the backend, reopen a campaign by ID, and continue from the exact authoritative state. Preserve the existing URL/local-storage resume experience and add a small resume/recent-campaign UI where needed.

# Start here

- Read AGENTS.md completely and preserve every design invariant.
- Inspect git status and existing changes before editing. Do not reset, discard, or rewrite unrelated user work.
- Read the persistence, service, API, AI logging, schemas, tests, and frontend campaign-loading code, plus the medium-priority section of docs/comprehensive-engineering-ux-review-2026-07-09.md.
- Run or otherwise establish the current relevant test/build baseline. Treat documentation test counts as untrusted.
- Confirm that Batch 1 has not already been implemented before adding a competing abstraction.

# Required outcome

- Introduce a narrow repository/storage boundary outside engine/. The deterministic engine must remain standard-library-only and independent of FastAPI, Pydantic, and persistence.
- Use SQLite with schema versioning or a minimal forward migration mechanism. Prefer the Python standard library unless an existing dependency already solves the problem cleanly.
- Persist enough typed data to reconstruct a campaign exactly: campaign identity/status, authoritative WorldState, current phase/turn, resolved turn results, immutable per-turn snapshots, canon entries, open threads, and any other existing campaign-owned state.
- Persist ModelRun records through the same durable boundary without giving AI code any authority to mutate game state.
- Store structured, versioned JSON where practical. Do not use lossy repr/default=str serialization.
- Make turn snapshots append-only/immutable at the storage boundary. Re-saving a campaign must not rewrite historical truth.
- Recover active and terminal campaigns after constructing a new repository/service instance against the same database file.
- Provide an API for listing a small set of recent campaigns with only the metadata needed by the resume UI. Do not expose internal prompts or sensitive model payloads in list responses.
- Update the frontend so a saved campaign ID in the URL or local storage resumes after a backend restart. Handle missing, corrupt, or deleted campaign IDs clearly and allow starting a new campaign.
- Make the database path configurable for development and tests. Tests must use isolated temporary databases and must not contaminate the developer's real data.
- Update architecture and run documentation to describe the real storage behavior and backup/reset location.

# Boundaries

Do not add authentication, accounts, cloud sync, multi-process conflict handling, autonomous agents, a vector database, or statewide content. Do not redesign turn idempotency in this batch beyond safe persistence; that is Batch 2. Do not weaken AppliedDiff, canon-classification, NPC-mediation, or terminal-campaign guarantees.

# Success criteria

- A campaign survives a simulated backend restart and resumes with the same ID, state, history, snapshots, canon, threads, and status.
- Historical snapshots cannot be silently changed by later saves.
- Model runs survive restart and remain advisory records only.
- Existing deterministic outcomes remain unchanged.
- Backend tests and the frontend production build pass; add focused persistence, restart, corruption/missing-ID, and terminal-resume regression tests.

# Final response

Lead with what now works. List the important files changed, schema/migration decisions, validation run and results, and any remaining risk. If a required validation could not run, state the exact reason and the next best check. Do not commit or push unless explicitly asked.
```

## Batch 2 — Atomic turns, idempotency, and observability

```text
You are implementing the second medium-priority improvement batch in the Continuity Failure repository at C:\Users\Jeff\Projects\Continuity_Failure. Complete and verify the code, not just a plan.

# Goal

Make turn resolution atomic and safe to retry. Each advice submission must carry the campaign state it expects and an idempotency key; duplicate retries return the original resolved result, stale competing submissions fail cleanly, and partial failures leave no authoritative changes. Add request IDs and structured logs that make this behavior diagnosable.

# Start here

- Read AGENTS.md completely.
- Inspect git status and preserve unrelated changes.
- Verify Batch 1's SQLite repository, schema, immutable snapshots, and restart behavior are present. If they are not, stop and report that dependency rather than building a second persistence system.
- Inspect turn API schemas/routes, campaign service, repository transactions, deterministic turn engine, frontend submission flow, and related tests.
- Establish the current test/build baseline from the repository, not a documented count.

# Required outcome

- Add a bounded, strictly validated idempotency key and an expected turn number or equivalent revision to turn-resolution requests.
- Generate one idempotency key per user submission in the frontend and reuse that same key for transport retries. A new deliberate submission gets a new key.
- Enforce uniqueness for a campaign plus idempotency key in SQLite.
- Resolve and persist a turn in one transaction: validate campaign/revision, run deterministic resolution, save authoritative campaign state, append the immutable turn snapshot/history, and save the idempotency result. Commit all or roll back all.
- Ensure two simultaneous submissions cannot both advance the same campaign turn. Use a repository transaction and the smallest necessary process-level coordination if SQLite alone is insufficient in the current architecture.
- Define precise API behavior: same key and same request returns the original response without advancing; same key with different payload is a conflict; stale expected turn is a conflict; terminal campaigns remain rejected.
- Keep engine functions deterministic and free of database/web imports. Transactionality belongs in the application/repository layer.
- Add a request ID to every API request/response, accepting a valid inbound ID or generating one. Include request ID, campaign ID, turn number/revision, route, status, duration, and idempotency outcome in structured logs.
- Do not log raw advice memo text, prompts, secrets, or complete model inputs/outputs in ordinary request logs.
- Return stable, useful error bodies that the frontend can explain without exposing internals.

# Regression tests

Cover successful resolution, exact retry, key reuse with changed payload, stale turn, terminal campaign, two competing submissions, and an injected exception after deterministic resolution but before commit. The rollback test must prove state, snapshots, and turn number are unchanged. Verify request-ID propagation and required structured-log fields.

# Success criteria

- No request can produce a half-saved turn.
- A transport retry never creates a second turn.
- A stale or competing request never overwrites newer state.
- Existing state invariants and deterministic replay behavior still pass.
- Backend tests and frontend build pass.

# Final response

Summarize the observable guarantees, conflict/error contract, transaction boundary, logging fields, and validation results. Name any concurrency limitation that genuinely remains. Do not commit or push unless asked.
```

## Batch 3 — Frontend test foundation and critical journeys

```text
You are implementing the third medium-priority improvement batch in the Continuity Failure repository at C:\Users\Jeff\Projects\Continuity_Failure. Add a maintainable frontend test foundation and use it to protect the game's critical journeys.

# Goal

Make regressions in turn presentation, resume behavior, terminal flow, keyboard operation, responsive layout, and API integration detectable before future UI work lands.

# Start here

- Read AGENTS.md completely.
- Inspect git status and preserve unrelated user work.
- Verify Batches 1 and 2 exist: durable resume plus atomic/idempotent turn submission. Do not mock away the very behavior this batch is meant to protect.
- Inspect frontend tooling, components, API client, backend test fixtures, and existing scripts before choosing libraries.
- Run the current backend tests and frontend build/type checks to establish a baseline.

# Required outcome

- Add the smallest conventional test stack that fits the current frontend: fast component/integration tests plus real-browser end-to-end tests. A DOM testing library and Playwright are appropriate if no equivalent already exists.
- Add clear npm scripts for unit/component tests, end-to-end tests, and any combined CI check. Keep configuration readable and local to the frontend where practical.
- Make tests hermetic. Use an isolated temporary SQLite database or explicit test backend reset, deterministic scenario data, known ports, and reliable process cleanup.
- Prefer queries by accessible role/name and visible behavior. Add test IDs only where semantic selectors cannot express the contract.
- Protect these journeys:
  1. Start a campaign, resolve one call, see the resolved turn snapshot, and confirm next-turn documents/state remain hidden until Next Call.
  2. Click Next Call and confirm the following turn becomes current exactly once.
  3. Refresh and resume the same campaign from the URL/local storage; also resume after restarting the backend process against the same test database.
  4. Retry a submission with the same idempotency key and confirm no duplicate turn.
  5. Reach or load a terminal campaign and verify further advancement is unavailable while the dossier remains usable.
  6. Operate the core turn flow by keyboard, including dialogs/drawers that currently exist.
  7. Exercise representative narrow and wide viewports without clipped primary controls or horizontal page overflow.
- Add targeted component tests for API loading/error/retry states and the restart confirmation behavior.
- Add an accessibility smoke check if it can be integrated without making the suite flaky. Do not treat it as a substitute for the explicit keyboard test.
- Document setup, browser installation, commands, test database behavior, and common local failures.

# Boundaries

Do not redesign the interface in this batch. Do not rely primarily on screenshot snapshots or timing sleeps. Do not make production behavior test-only. New dependencies are justified only for the immediate testing requirement.

# Success criteria

- The suite fails if the temporal snapshot bug returns, if resume loses a campaign, or if a duplicate retry advances twice.
- Tests run from documented commands on a clean checkout.
- Backend tests, frontend unit tests, end-to-end tests, and production build pass.

# Final response

Report the journeys now covered, commands and results, any deliberately deferred browser matrix, and the main testability seams added. Do not commit or push unless asked.
```

## Batch 4 — Onboarding and accessible interaction model

```text
You are implementing the fourth medium-priority improvement batch in the Continuity Failure repository at C:\Users\Jeff\Projects\Continuity_Failure. Improve comprehension and accessibility without changing the deterministic game rules.

# Goal

Add a concise first-turn onboarding experience and overhaul overlays/phase navigation so a new player can understand the civic simulation and a keyboard or screen-reader user can complete the core loop.

# Start here

- Read AGENTS.md completely and inspect the current worktree.
- Preserve unrelated changes.
- Verify Batch 3's frontend test harness and critical-journey tests exist. Extend those tests rather than replacing them.
- Inspect the current intro, turn phases, dialogs/drawers, evidence board, advice workbench, aftermath, dossier, state indicator semantics, and existing reduced-motion/focus styles.
- Establish the current backend/frontend validation baseline.

# Required outcome

- Add progressive first-turn onboarding that explains, in the project's serious diegetic voice: the player advises while NPCs decide; higher is not always better; failure thresholds; ambient drift; adherence/rejection; evidence freshness/reliability; indicator direction labels; and the difference between resolving a turn and loading Next Call.
- Keep the initial explanation concise. Use contextual help or expandable definitions near the relevant control for detail. Do not repeat the tutorial every turn.
- Persist dismissal/completion locally in a versioned key and provide a discoverable way to reopen help. Do not make campaign authority depend on browser storage.
- Give every modal or drawer correct dialog semantics, an accessible name, initial focus, contained focus, Escape behavior where safe, background inertness, and focus restoration to the opener.
- Make phase navigation semantic and stateful: use suitable tabs/steps, expose selected/current/disabled state, support expected arrow-key behavior where applicable, and preserve the rule that future phases cannot reveal future authoritative content.
- Correct heading hierarchy and landmarks, add a skip link, and use restrained live regions for loading, errors, turn resolution, and phase changes.
- Ensure icon-only controls have useful names and all core actions remain visible/focusable at narrow widths.
- Preserve explicit focus-visible styles and reduced-motion CSS. Any new motion must have a no-motion equivalent.
- Maintain the diegetic workstation aesthetic; avoid a generic tutorial carousel or gamey coach marks.

# Tests and verification

- Extend component and E2E coverage for first-run/reopen-help behavior, full keyboard core flow, focus trap/restore, Escape, semantic phase navigation, live announcements, and narrow viewport controls.
- Run an automated accessibility scan on the primary screens and manually inspect the rendered experience in a real browser at representative desktop and mobile sizes.
- Backend tests, frontend tests, end-to-end tests, and production build must pass.

# Boundaries

Do not alter thresholds, effects, NPC decisions, or authoritative state to make onboarding easier. Do not add a large UI framework solely for dialogs or tabs unless the current code cannot meet the requirements safely with a small focused dependency.

# Final response

Lead with what a new or keyboard-only player can now do. Report the interaction semantics, tests, browser/viewports inspected, accessibility findings fixed, and any remaining known limitation. Do not commit or push unless asked.
```

## Batch 5 — Versioned scenario content and validation

```text
You are implementing the fifth medium-priority improvement batch in the Continuity Failure repository at C:\Users\Jeff\Projects\Continuity_Failure. Separate Northbridge scenario content from engine code and make invalid content fail early with actionable errors.

# Goal

Create a versioned, validated content layer for the Northbridge Water Failure scenario while preserving all current deterministic behavior and public engine interfaces.

# Start here

- Read AGENTS.md completely.
- Inspect git status and preserve unrelated work.
- Inspect all scenario seed data, IDs, turn/call/document/advice/faction definitions, variable references, tests, loaders, and architecture documentation.
- Read the scenario-validator recommendation in docs/comprehensive-engineering-ux-review-2026-07-09.md.
- Capture current deterministic fixtures/outcomes before moving data so accidental balance changes are visible.

# Required outcome

- Move authored Northbridge content out of large executable seed modules into coherent versioned data files grouped by domain, such as scenario metadata, factions, calls/turns, evidence/documents, advice, and operational prose.
- Prefer a data format supported without a new runtime dependency unless the repository already has a suitable parser. Keep a single clear loader/factory API so engine callers do not care where data lives.
- Include an explicit scenario/content schema version and a migration or clear incompatibility error strategy.
- Build a validator that runs both in tests and as a documented developer command. It must report file/path and field context for each error and collect useful errors where safe.
- Validate at minimum: unique IDs; known cross-references; required fields; enum values; integer/range bounds; known WorldState variables; effect-map keys and values; turn ordering/coverage; caller/faction references; advice references; document tags/freshness; operational_steps structure; and any terminal/threshold references present in content.
- Reject unknown fields where silently accepting a typo would change or omit gameplay.
- Validate the complete scenario before a campaign starts. Do not allow malformed content to partially seed authoritative state.
- Preserve deterministic engine dataclasses and the rule that content describes inputs while engine rules decide outcomes.
- Add focused invalid fixtures for duplicate IDs, missing references, unknown variables/tags, invalid ranges/enums, malformed operational steps, and unsupported schema versions.
- Update contributor and architecture documentation with file layout, authoring rules, validator command, and how to add content safely.

# Boundaries

Do not expand beyond the Northbridge town-level scenario. Do not redesign advice mechanics yet; Batch 6 will consume the validated relationships. Do not introduce a database-backed CMS, Pydantic into engine/, or runtime model-generated scenario facts.

# Success criteria

- The Northbridge campaign produces the same starting state, content, choices, and deterministic turn outcomes as before extraction.
- A typo in an ID or state variable fails with a precise content validation error before play begins.
- All backend tests, scenario validation, and frontend build pass.

# Final response

Summarize the content layout, validation contract, behavior-preservation evidence, commands/results, and any schema evolution decision. Do not commit or push unless asked.
```

## Batch 6 — Contextual advice and faction-aware decisions

```text
You are implementing the sixth medium-priority improvement batch in the Continuity Failure repository at C:\Users\Jeff\Projects\Continuity_Failure. Make advice choices mechanically specific to each call while preserving deterministic, explainable authority.

# Goal

Replace the feel of a reusable global advice menu with a call-specific decision space. Caller and faction incentives must materially influence adherence, modification, delay, or rejection, and off-brief advice must carry a visible deterministic tradeoff.

# Start here

- Read AGENTS.md completely and inspect git status.
- Preserve unrelated changes.
- Verify Batch 5's validated scenario-content layer is present. Extend it instead of reintroducing hard-coded seed relationships.
- Inspect ClientCall, AdviceOption, Faction, NpcDecision, rules.decide, turn resolution, content data, API mappings, advice UI, and balance/evaluation tests.
- Capture baseline campaign trajectories and identify whether every NPC decision branch is currently reachable.

# Required outcome

- Extend validated scenario content so each client call declares a small set of primary/relevant advice options and enough structured incentive context to explain why they fit.
- Present roughly 3–4 primary options for a call. If the UI permits other known options, place them behind a clearly labeled strategic-alternatives path and show their off-brief cost or risk before submission.
- Define the off-brief consequence deterministically. It may affect adherence, client trust/pressure, reputation, time/resource pressure, or another existing authoritative variable, but every numeric mutation must still flow through AppliedDiff with a concrete reason/source.
- Make faction/caller attributes such as risk tolerance, current pressure/influence, institutional mandate, incentives, and red lines feed deterministic NPC decision logic in a legible way.
- Ensure FOLLOWED, MODIFIED, DELAYED, and REJECTED outcomes are genuinely reachable under plausible tested conditions. Avoid randomness unless the project already has a replay-safe seeded mechanism.
- Add an explanation payload suitable for the aftermath: relevant incentives, conflicts, adherence calculation factors, and why the NPC selected the outcome. Do not expose opaque internal scoring without human labels.
- Keep the player in an advisory role. The selected option may propose effects; the NPC decision and deterministic engine mediate actual effects.
- Update content validation for all new call/advice/faction references and ranges.
- Update the advice workbench so relevance, institutional fit, tradeoffs, and off-brief status are understandable before submission without overwhelming the first screen.
- Add balance/regression tests showing advice relevance matters, each decision branch is reachable, replay is deterministic, values remain clamped, and every mutation emits an AppliedDiff.

# Boundaries

Do not add free-form model authority, hidden random state changes, autonomous agents, or statewide systems. Do not implement the full memo lifecycle in this batch; that is Batch 7. Avoid a single universal penalty that makes every off-brief choice obviously wrong.

# Success criteria

- Different calls produce meaningfully different primary choices.
- The same advice can be received differently by factions for explicit deterministic reasons.
- Rejection is reachable and tested without violating state invariants.
- Backend tests, content validation, frontend tests/E2E relevant to advice, and production build pass.

# Final response

Explain the new player-facing choice model, deterministic decision inputs, reachable outcome evidence, balance tests, and validation results. Mention material tuning assumptions. Do not commit or push unless asked.
```

## Batch 7 — Persistent memo artifact workflow

```text
You are implementing the seventh medium-priority improvement batch in the Continuity Failure repository at C:\Users\Jeff\Projects\Continuity_Failure. Turn memo drafting into a persistent, auditable advisory artifact without granting the model authority over canon or state.

# Goal

Implement the workflow Draft → Edit → Attach/Send → Client decision → Canon/archive. The exact memo the player sends must be preserved with provenance and linked to the resolved turn.

# Start here

- Read AGENTS.md completely and inspect the worktree.
- Preserve unrelated changes.
- Verify durable persistence, atomic/idempotent turn resolution, and contextual advice from Batches 1, 2, and 6 exist. If a dependency is absent, report it rather than building a parallel shortcut.
- Inspect AdviceMemo/ModelRun models, AI drafter validation, memo fallback, campaign repository, API schemas/routes, advice workbench, turn history/canon, export/dossier, and tests.

# Required outcome

- Add a persistent AdviceMemo aggregate with stable ID, campaign ID, optional turn/call/advice linkage, status, content, revision/version, created/updated timestamps, authorship/source, fact classification, and provenance.
- Support the workflow through strict API endpoints and UI: create a manual or AI-assisted draft, edit it, save revisions as appropriate, attach/select one memo for a submission, and clearly confirm what will be sent.
- AI-generated text remains proposed advisory material. Record the relevant ModelRun ID, prompt version, model/provider, validation result, and fallback status without storing secrets in ordinary API responses.
- Player edits must be distinguishable from generated source text. Preserve an immutable snapshot or cryptographic digest of the exact sent memo so later edits cannot rewrite history.
- Include memo ID/revision or sent snapshot provenance in the idempotent turn request. Retrying the same request must reference the same sent artifact; changing the memo requires a new deliberate submission/key.
- When the turn resolves, link the sent memo to the NpcDecision, turn result, archive/dossier, and any canon entry that records the institutional action. Canon must reflect the deterministic workflow outcome, not merely the memo's claims.
- Prevent editing/deleting the historical sent representation. Drafts may be edited; sent/archived artifacts are immutable or superseded through an explicit new revision.
- Keep and improve the deterministic fallback path using display faction names and validated operational_steps content.
- Add useful empty, loading, validation, conflict, and AI-disabled states to the workbench.
- Enforce strict request bounds and ownership checks for memo names/content/revisions. Unknown fields must be rejected.

# Regression tests

Cover manual draft/edit, AI draft with ModelRun provenance, AI-disabled fallback, strict validation, attach/send, idempotent retry, stale memo revision conflict, persistence across restart, exact sent-content preservation, post-send immutability, archive/dossier linkage, and proof that drafting/editing never changes WorldState.

# Boundaries

Do not allow memo prose or model output to directly set effects, decision type, canon classification, or authoritative variables. Do not build collaboration, document uploads, rich-text complexity, or autonomous sending.

# Success criteria

- The dossier can show exactly what was sent, when, by what workflow, and which client decision followed.
- Later edits cannot alter a prior turn's record.
- All state changes remain deterministic and explainable through AppliedDiff.
- Backend tests, frontend tests/E2E, and production build pass.

# Final response

Lead with the completed workflow. Report the data/provenance model, immutability guarantees, tests/results, and any intentionally deferred document features. Do not commit or push unless asked.
```

## Batch 8 — Causal aftermath visualization and final regression

```text
You are implementing the eighth medium-priority improvement batch in the Continuity Failure repository at C:\Users\Jeff\Projects\Continuity_Failure. Make turn consequences causally legible and finish with an integrated regression pass across all medium improvements.

# Goal

In the aftermath, show how the starting snapshot became the resolved snapshot through the player's advice, the NPC's response, and ambient/system effects. The visualization must use authoritative server/engine provenance, remain accessible, and never reveal the next turn before Next Call.

# Start here

- Read AGENTS.md completely and inspect git status.
- Preserve unrelated changes.
- Verify the frontend test foundation and Batches 6–7 are present.
- Inspect AppliedDiff, TurnResult, NpcDecision explanations, ambient drift, API mappings, aftermath/consequence UI, indicator metadata, reduced-motion CSS, dossier/export, and critical E2E tests.
- Establish the complete validation baseline before editing.

# Required outcome

- Expose or normalize authoritative consequence groups at the API boundary so each displayed change can be attributed to a source such as starting value, advice proposal as mediated by adherence, NPC modification/delay/rejection, ambient drift/rule, and final value.
- Do not recalculate authoritative outcomes in the browser. The frontend may format/group server-provided AppliedDiff data but must not invent missing deltas.
- Build a compact causal waterfall or equivalent per affected variable: start → attributed deltas → final. Use humanized variable labels, direction semantics, signed values, reasons, and source labels.
- Clearly distinguish proposed advice effects from effects actually applied after NPC mediation. If an advice effect was rejected or reduced, show that explicitly rather than implying it changed state.
- Add a readable summary of why the NPC acted as they did using the deterministic explanation data from Batch 6 and link the sent memo provenance from Batch 7.
- Animate changed values only when it improves comprehension. Respect prefers-reduced-motion and avoid relying on animation or color to communicate meaning.
- Provide an accessible table/text equivalent with correct reading order and announced resolution status. Pressure/influence and positive/negative direction colors must remain semantically correct and include text/icon cues.
- Preserve the resolved turn snapshot and its documents throughout aftermath. Only the explicit Next Call action may load the next turn's state/documents.
- Ensure the visualization works at narrow and wide viewports without nested-card clutter, clipped labels, or horizontal page overflow.
- Include the same causal data in dossier/export where appropriate, using stable provenance rather than duplicated prose generation.

# Integrated regression pass

Extend tests for exact diff grouping/math, rejected/reduced advice, ambient drift, no-change variables, clamp boundaries, human labels, accessible fallback, reduced motion, responsive layout, and temporal snapshot preservation. Then run the full backend suite, scenario validator, frontend unit suite, critical E2E suite, accessibility checks, and production build. Inspect the rendered aftermath in a real browser at representative desktop and mobile sizes.

Fix regressions caused by this batch when they are in scope. Do not silently broaden into unrelated redesigns; document any separate issue with evidence.

# Success criteria

- A player can answer: what changed, by how much, because of whom/what, and from which authoritative record.
- The numbers reconcile exactly from start through deltas to final.
- The display remains understandable without color or motion.
- No future-turn state leaks before Next Call.
- All validation is green.

# Final response

Lead with the causal story the UI can now show. List provenance/API changes, accessibility and responsive behavior, full validation commands/results, and any remaining risk. Do not commit or push unless asked.
```

## Suggested fresh-chat handoff rhythm

At the end of each batch, keep the implementation on a coherent branch or commit before opening the next fresh chat. Give the next chat the corresponding prompt above; it already tells Codex to verify dependencies and the actual worktree. If a batch uncovers a prerequisite defect, fix it only when it is necessary for that batch's success criteria and call it out in the handoff.
