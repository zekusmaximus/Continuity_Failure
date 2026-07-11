# Wave 3 Implementation Plan — Comprehension and Consequence

**Status:** PLAN — implementation must start from the merged, green Wave-2
ruleset-3 balance pass. No Wave-3 feature code is included in this plan.

**Date:** 2026-07-11

**Scope sources:** `docs/major-enhancement-roadmap.md` Wave 3b / HO#10 and
`docs/player-experience-plan.md` ranks 1–3 (causal headline, progressive first
engagement, local comprehension telemetry).

**Binding constraints:** every design invariant in `AGENTS.md`. The engine stays
stdlib-only and deterministic; every authoritative state mutation still flows
through `engine/diffs.apply_diffs`; NPCs mediate advice; model output never
mutates state; terminal campaigns remain terminal; idempotent turn resolution
and frozen presentations remain intact.

---

## 1. Decision: Wave 3 is local comprehension work; deployment security remains deferred

The roadmap names two Wave-3 tracks:

- **3a / ME#5:** identity and security for shared deployment;
- **3b / HO#10:** comprehension-focused playtest telemetry.

There is still no scheduled shared deployment, so 3a remains deliberately
deferred. Building accounts, ownership, quotas, and hardened deployment now
would not answer the current product question: whether a player understands and
feels the simulation strongly enough to finish and replay Northbridge.

Wave 3 therefore delivers **3b plus the smallest player-facing changes needed
to act on it**:

1. local, explicit, privacy-safe measurement of the turn loop;
2. a deterministic causal headline and future hook before the audit detail;
3. progressive teaching attached to real game objects;
4. an optional expedited review cadence after the first two turns;
5. clearer first-run and second-run framing for the existing variants.

This is not Wave 4 in disguise. The player still cannot choose what to seal,
omit, or classify; no counterfactual engine runs; no ethics profile is derived;
no contradiction graph or deadline budget is added. Those remain record-centered
Wave-4 work.

## 2. Hard entry conditions

Wave 3 must not be layered onto half-merged Wave-2 remediation. Before Batch A1:

1. Merge the Wave-2 balance pass documented in
   `docs/wave-2-implementation-plan.md` §9.
2. Resolve every merge conflict and start a fresh `codex/` implementation
   branch from the merged commit.
3. Re-derive the exact baseline counts with:
   - `python -m pytest -q`;
   - `python -m engine.content validate`;
   - `npm run test:ci` from `frontend/`.
4. Run `python tests/support/balance_trace.py` for baseline, `hot_summer`, and
   `strained_finances`; confirm ruleset-3 witnesses and goldens are untouched.
5. Confirm the following Wave-2 properties through the real API before adding
   presentation work:
   - auxiliary allocation binds once and cannot be switched by drafting;
   - hot-summer neglect reaches CRITICAL with turns left;
   - the turn-4 contractor ultimatum has a natural witness;
   - all five completed-campaign verdicts have pinned witnesses;
   - stale documents, ruleset incompatibility, and dossier Wave-2 facts remain
     truthful.

The last clean PR-4 baseline was 485 pytest / 46 Vitest / 24 Playwright. Those
numbers are historical context, not Wave-3 entry counts; record the newly
derived counts in the A1 commit message.

## 3. Wave-3 design guarantees

### 3.1 Telemetry is not canon

Playtest events live in the browser only. They never enter `Campaign`,
`WorldState`, SQLite campaign snapshots, turn fingerprints, model prompts, NPC
decisions, or rule evaluation. Timestamps may be wall-clock values because the
data is observational and explicitly non-authoritative.

### 3.2 Telemetry cannot collect prose

There is no generic `payload: Record<string, unknown>` escape hatch. Events use
a closed TypeScript discriminated union with an allow-list of scalar ids,
turn/phase numbers, booleans, and durations. Memo names/content, document
content/summary, calls, prompts, model input/output, error bodies, and free-form
player text are not valid event fields.

### 3.3 The causal lead is derived, not a new fact

The headline and future hook are deterministic summaries of an already-resolved
`TurnResult`: advice label, NPC decision, applied diffs, thread/precedent events,
and terminal status. They do not invent motive, forecast an outcome, or become a
new `CanonEntry`. Every sentence carries references back to the record it
summarizes.

### 3.4 Faster navigation never changes resolution

Expedited review changes presentation phases only. It uses the same frozen
`CurrentTurnModel`, advice options, evidence, memo workflow, expected turn, and
idempotency submission. It cannot skip advice, auto-cite evidence, auto-create a
memo, acknowledge a presentation, or advance state.

### 3.5 Wave 3 does not change balance

No advice effects, adherence rules, ambient windows, thread schedules, faction
shifts, failure thresholds, seed values, or ending formulas change. Wave 3 does
not bump `CURRENT_RULESET_VERSION`. A test pins that every canonical and
ruleset-3 witness trace remains bit-identical.

## 4. Sequence: measure → sharpen payoff → teach → accelerate → invite replay

Seven independently green batches land in this order:

| Batch | Outcome | Why this order |
| --- | --- | --- |
| A1 | Local telemetry vocabulary and bounded store | Establishes the privacy boundary before any event is emitted. |
| A2 | Turn-loop instrumentation, export, clear, and local summary | Captures the pre-polish baseline and makes the data inspectable. |
| B1 | Deterministic causal lead in the engine/API record | Creates one stable payoff artifact before redesigning presentation. |
| B2 | Consequence hierarchy in the UI and dossier | Makes the causal lead felt while preserving the complete audit. |
| C1 | Progressive first-engagement teaching | Teaches the now-sharper loop through real evidence, threads, and precedents. |
| C2 | Optional expedited review from turn 3 | Removes learned navigation only after the full loop has been taught twice. |
| C3 | Intake and terminal replay framing | Uses the completed loop and telemetry to invite a deliberate second run. |

All seven can ship together as Wave 3. A1–A2 alone are a coherent internal
playtest instrument; B1–B2 alone are a coherent consequence-payoff slice; C1–C3
are presentation-only and may be delayed without weakening engine correctness.

---

## 5. Batch A1 — local telemetry vocabulary and bounded store

### Frontend domain

Add `frontend/src/telemetry/`:

- `events.ts` — `TelemetryEventV1`, a discriminated union;
- `store.ts` — read/append/clear/export primitives;
- `session.ts` — one ephemeral browser-session id and stable schema metadata.

Every event carries only:

- `schema_version: 1`;
- `event_id` and `session_id` generated in the browser;
- `event_type` from the closed vocabulary;
- ISO client timestamp;
- optional `campaign_id`, `turn_number`, and `phase`;
- event-specific allow-listed ids/booleans/numbers.

Initial event vocabulary:

- `campaign_started`, `campaign_resumed`, `campaign_terminal`;
- `phase_entered`, `phase_left` with elapsed milliseconds;
- `evidence_opened` / `evidence_closed` with `document_id` only;
- `advice_selected` and `alternative_section_toggled` with advice id/count;
- `case_file_opened` with tab id;
- `record_detail_toggled` with detail kind;
- `guide_topic_shown` / `guide_topic_opened` with topic id;
- `review_mode_changed` (`guided` / `expedited`);
- `variant_selected` with variant id;
- `desk_session_ended` with last phase and turn (best-effort, never called
  authoritative “abandonment”).

Storage is a bounded local ring of at most **2,000 events** under a versioned
key such as `continuity-failure.telemetry.v1`. On quota/storage failure,
gameplay continues with telemetry disabled for that write. Telemetry never
throws through a player action.

### Privacy tests

Add Vitest coverage that:

- round-trips every event variant;
- rejects unknown event fields during import;
- caps and evicts oldest events deterministically;
- survives malformed/localStorage-unavailable data;
- asserts serialized events contain none of the forbidden keys or sample memo,
  call, document, prompt, and error prose;
- proves telemetry modules are not imported by `engine/` or backend services.

### No contract/persistence ripple

No backend route, engine dataclass, campaign snapshot, idempotency fingerprint,
or fixture changes in A1.

## 6. Batch A2 — instrumentation, explicit export, and local summary

### Instrumentation boundary

Add one `TelemetryProvider` / hook at the app root. Components report typed
intent events; they do not write storage directly. Phase duration is measured
by paired enter/leave events and flushed on phase change, campaign change, and
best-effort page hide.

Instrument only the decisions named in HO#10:

- time from first seeing Advice to selecting/sending;
- which evidence cards are opened and whether cited evidence was opened first;
- primary-option changes and whether strategic alternatives were expanded;
- Case File opens and selected tab;
- causal-record expansion after the headline;
- guide topics opened;
- phase at the last session event;
- guided versus expedited mode.

Do not infer “understood,” “ignored,” or “abandoned” from one event. The export
reports behavior; playtest notes interpret it.

### Player controls

Add a **Local playtest data** section to the Case File or settings surface:

- explain in plain language that data stays in this browser;
- show event count, first/last timestamp, and approximate storage size;
- **Export JSON** only on explicit click;
- **Clear local data** behind confirmation;
- telemetry collection defaults **on for local development builds and off for
  packaged/public builds** until a product decision says otherwise;
- expose a simple on/off control whose state is itself not sent anywhere.

The JSON export includes a top-level manifest (`schema_version`, app version,
ruleset version, variant id, exported_at) plus events. It contains no campaign
snapshot or prose.

### Local summary

Add a pure `summary.ts` that computes per-turn/phase durations, evidence-open
counts, advice changes, Case File use, record expansions, and final phase from
one export. Render a compact summary before export and unit-test it from fixed
event fixtures. Cross-session aggregation/server upload is trimmed.

### Tests

Vitest covers exact event emission without relying on real time. Playwright
covers one turn, export download, JSON schema/readback, clear confirmation, and
the absence of memo text inserted during the journey.

## 7. Batch B1 — deterministic causal lead and future hook

### Engine model

Add defaulted dataclasses in `engine/models.py`:

```text
ConsequenceReference
  kind        diff | thread | precedent | failure | decision
  id          stable id when one exists; otherwise a deterministic key
  label       short record label, never generated prose

ConsequenceLead
  headline
  future_hook
  references[]
```

Add `TurnResult.consequence_lead: ConsequenceLead = field(default_factory=...)`.
The default permits old snapshots/idempotency responses to load without a
migration; every newly resolved turn populates it.

### Pure builder

Create `engine/experience.py` with
`build_consequence_lead(...) -> ConsequenceLead`. It is stdlib-only, contains no
state mutation, and follows a pinned stable priority:

1. terminal failure/completion fact, if this turn ended the campaign;
2. the client decision and advice label;
3. the largest absolute applied movement, with stable tie-break by humanized
   variable name and diff order;
4. future hook priority: escalated thread → newly opened thread → newly recorded
   precedent → unresolved risk named by the consequence stack → none.

Templates use only typed record text already present on the result. Example
shape, not hardcoded lore:

> You advised **Controlled disclosure**. The Town Manager narrowed the order;
> Public Trust rose 2, while **Contractor warning** is now due on the record.

If advice was delayed/rejected, say so rather than implying its proposed effect
landed. If the largest movement came from ambient/thread/leak pressure, name that
source rather than attributing it to the player. The existing causal report is
the authority for attribution and clamping.

### Integration order

Build the lead after diffs, decision, thread events, canon, and new precedents
exist, but before the `TurnResult` is serialized and saved. The builder receives
those already-produced values; it does not re-run rules or read post-resolution
mutable state to infer causality.

### Contract ripple

Add:

- `ConsequenceReferenceModel` / `ConsequenceLeadModel` in Pydantic;
- TS mirrors in `frontend/src/api/client.ts`;
- contract-matrix entries;
- regenerated fixtures.

No request model or fingerprint field changes. Replaying an older idempotency
response returns the default empty lead; a new resolution returns the populated
lead exactly as stored in its frozen presentation.

### Tests

- stable tie-breaking;
- followed/modified/delayed/rejected attribution;
- ambient/thread/leak movement is not called player action;
- terminal failure wins headline priority;
- future-hook priority and references;
- old snapshot/default replay compatibility;
- `asdict` ↔ Pydantic ↔ TS parity;
- canonical state/diffs/decision/faction/ending records remain bit-identical;
- no ruleset bump.

## 8. Batch B2 — consequence hierarchy in the UI and dossier

### Client Decision

Lead with the causal headline above the existing decision receipt. Show:

- advice sent;
- decision type and adherence;
- one operative reason;
- referenced primary movement.

Do not expose the future hook until the Consequences phase; the existing
progressive-disclosure sequence remains meaningful.

### Consequences

Render in this order:

1. future hook, when present;
2. causal headline/decision receipt context;
3. a **Show the full record** disclosure containing the current waterfall,
   consequence stack, faction shifts, and state reconciliation;
4. canon/thread/archive details as today.

The full record defaults open on turns 1–2 and closed from turn 3 onward. This is
presentation state only; keyboard users can expand it with a semantic
`<details>`/button, focus is preserved, and `prefers-reduced-motion` receives an
instant equivalent.

### Dossier

Add each turn's causal headline and future hook to the deterministic Markdown
timeline immediately before state reconciliation. Preserve the exact memo,
decision, applied diffs, call variant, power allocation, and other Wave-2 facts.
The headline supplements the audit; it never replaces it.

### Tests

Vitest covers headline-first ordering, delayed/rejected copy, missing/default
lead, disclosure state by turn, references, and accessibility. Playwright proves
the lead and expanded record survive refresh/backend restart via the frozen
presentation and that reduced-motion/keyboard journeys remain green.

## 9. Batch C1 — progressive first-engagement teaching

### Replace the front-loaded manual

Reduce the first-run Desk Guide to three promises:

1. You recommend; the client decides.
2. Every resolved turn changes state and the record.
3. The desk will show exactly why.

Keep the existing complete guide reachable from Help, but do not require a new
player to read thresholds, citations, threads, ledger, degradation, and archive
semantics before accepting the first call.

### Contextual topics

Add versioned local topic acknowledgements under a separate presentation key
(`continuity-failure.guide.v2`). Trigger each once when its object first matters:

- `adherence` — first advice comparison;
- `evidence_weight` — first attached document;
- `citation` — first citation-capable workbench;
- `thread_deadline` — first newly opened scheduled thread;
- `precedent` — first ledger entry;
- `stale_feed` — first STRAINED package;
- `power_allocation` — first CRITICAL pre-turn allocation;
- `record_detail` — first causal lead before the audit disclosure.

Topics are short inline callouts or non-modal controlled-copy cards whenever
possible. They never cover a primary action, steal focus unexpectedly, or block
resolution. Each links to the full guide and can be dismissed/reopened.

### Turn-1 evidence prompt

Above the attached evidence, ask the authored-neutral question:

> Which record can bear the sentence you are about to put in writing?

Highlight attached documents and explain source/reliability/public status beside
the recommendation without requiring a citation. Strategic alternatives remain
collapsed on turn 1; they are still reachable and become ordinary from turn 2.

### Tests

Vitest covers trigger/dismiss/reopen/version behavior and localStorage failure.
Playwright covers a clean first run, returning player, keyboard/focus, and no
serious accessibility violations. Telemetry records topic ids only.

## 10. Batch C2 — optional expedited review from turn 3

### Presentation mode

After two acknowledged turns, offer **Expedited review** as an explicit player
preference. Default remains the guided loop. The preference is local browser
state, not campaign state, and can be changed at any call.

Guided mode remains:

`Call → Brief → Evidence → Advice → Client Decision → Consequences → Archive`

Expedited mode becomes:

`Review → Advice → Client Decision → Consequences → Archive`

The new `ReviewPhase` composes the same call, brief, caller disposition,
attached evidence, evidence board, degradation banner, and Case File links from
the current package. It does not fetch a smaller payload or mark documents read.

### Navigation guarantees

- switching modes never calls the backend;
- phase tabs expose the active mode semantically;
- a resolved frozen presentation always reopens at Client Decision regardless
  of mode;
- terminal campaigns still open the dossier;
- Send Advice remains disabled without an attached memo and required bound power
  allocation;
- Next Call remains the only action that acknowledges and releases a resolved
  presentation;
- switching from expedited back to guided returns to the corresponding current
  review phase without losing selection, citations, memo, or allocation.

### Tests

Component tests cover phase maps and state preservation. Playwright covers a
full ten-turn expedited campaign, mid-review refresh, power allocation, variant
call, keyboard phase navigation, terminal dossier, and the invariant that each
submission resolves exactly one turn.

## 11. Batch C3 — intake and terminal replay framing

### First-run intake

Present **Baseline engagement — recommended first case** as the primary path.
Move `hot_summer` and `strained_finances` beneath **Alternate intake
conditions**, with one concrete non-numeric sentence each. Variants remain
available from the start; this is framing, not a locked progression system.

### Terminal replay invitation

After the dossier, show:

- the completed variant/ruleset;
- the verdict and weakest axis already in the assessment;
- one unresolved thread or future hook already on the record;
- **Reopen intake with alternate conditions**.

The action returns to intake with a variant preselected. It does not create a
campaign until the player explicitly chooses **Begin Intake**. Do not implement
the Wave-4 road-not-taken simulation here.

Store only a local `has_completed_engagement` presentation flag so returning
players see alternate conditions more prominently. Campaign completion remains
authoritative in SQLite; the local flag grants no game state and may be absent.

### Tests

Vitest covers baseline emphasis, alternate disclosure, local flag failure, and
preselection without creation. Playwright covers terminal → intake → explicit
variant start and verifies two distinct campaign ids/variant summaries.
Telemetry records the variant id and second start, never dossier/memo prose.

## 12. Contract and persistence summary

| Change | Engine dataclass | Pydantic | TypeScript | Persistence / fixtures |
| --- | --- | --- | --- | --- |
| Telemetry events/store | none | none | A1 discriminated union | versioned bounded browser storage; no campaign fixtures |
| Export manifest/summary | none | none | A2 only | downloaded JSON; no backend record |
| `ConsequenceLead` / references | B1 | B1 full parity | B1 mirror | defaulted on `TurnResult`; campaign/idempotency decode-safe; fixture regen |
| Consequence hierarchy | none | none | B2 components | frozen presentation already stores serialized lead |
| Guide topics | none | none | C1 only | versioned local presentation preferences |
| Expedited review | none | none | C2 phase union/components | local preference; no campaign mutation |
| Replay framing | none | none | C3 only | local completion hint; new campaign remains API-created |

No SQLite schema migration is planned. No request fingerprint changes. No
`Campaign` field changes. The only engine persistence addition is a defaulted
summary field on `TurnResult`.

## 13. Verification discipline

### Every batch

1. Run `python -m pytest -q`.
2. Run `python -m engine.content validate`.
3. From `frontend/`, run `npm run typecheck` and `npm run test`.
4. Run `git diff --check` and inspect the exact batch diff.
5. If any authoritative trace changes, stop: Wave 3 is presentation-only. Do
   not update a golden or bump the ruleset to make the batch green.

### Contract/fixture batches

For B1:

1. regenerate frontend fixtures with the repository fixture command;
2. run contract parity tests;
3. run `npm run test:ci` from `frontend/`;
4. prove ruleset-3 final variables, diffs, decisions, factions, threads, ledger,
   endings, and allocations are unchanged.

### Required new Playwright journeys

- local telemetry export/clear with memo-content absence;
- causal lead → full record → refresh/backend restart;
- progressive clean first run and returning-player run;
- full expedited ten-turn campaign;
- expedited CRITICAL allocation and naturally firing call variant;
- terminal replay invitation into an explicit alternate campaign;
- keyboard, reduced-motion, narrow-phone, wide-desktop, and axe coverage for all
  new surfaces.

### Human playtest protocol

Automation cannot measure reading pace. After C3, run at least five observed
first-time Northbridge sessions and record only the local export plus separate
facilitator notes. Report:

- time to first advice and full-run duration;
- phase durations and turns 4–7 abandonment/pauses;
- evidence opened/cited and whether the player can explain its weight;
- advice changes and strategic-alternative use;
- Case File and full-record expansion;
- whether the player can explain advice → NPC action → applied change by turn 2;
- whether the terminal player elects an immediate alternate run.

Do not claim the 50–65 minute target or retention targets are met until observed
sessions support them.

## 14. Manual acceptance checklist

- [ ] A new player sees three promises, not a manual, before the first call.
- [ ] The first attached document teaches evidentiary weight without forcing a
      citation.
- [ ] The first opened thread/precedent/degraded band teaches itself when it
      appears and remains reopenable from Help.
- [ ] Client Decision leads with a truthful one-sentence causal orientation.
- [ ] Consequences names one future hook; the full existing audit is one action
      away and source-linked.
- [ ] Delayed/rejected advice is never described as applied.
- [ ] Ambient, thread, leak, and NPC movements are never attributed to the
      player.
- [ ] Refresh/restart restores the exact lead and frozen record.
- [ ] Expedited review becomes available only after two acknowledged turns and
      never changes backend calls or authoritative state.
- [ ] Local telemetry export contains no memo/call/document/prompt/error prose.
- [ ] Clearing telemetry does not clear campaigns, preferences, or canon.
- [ ] Baseline is the clear first-run recommendation; alternates are available
      without pretending to be locked progression.
- [ ] Terminal replay returns to intake and requires explicit campaign creation.
- [ ] All Wave-2 ruleset-3 balance/reachability witnesses remain green.

## 15. Trimmed from Wave 3

1. **Accounts, ownership, quotas, hosted telemetry, and remote aggregation** —
   remain Wave 3a and require an actual shared-deployment decision and threat
   model.
2. **Record sealing/omission/classification choices** — Wave 4a; telemetry and
   causal hierarchy should show where those choices would matter first.
3. **Counterfactual engine runs / road not taken** — Wave 4b; this wave only
   preselects a real authored variant for a new campaign.
4. **Ethics profile, contradiction graph, and deadline budget** — Waves 4c–4e.
5. **Additional AI research/classification tools** — Wave 5. No new model call
   is justified by comprehension telemetry alone.
6. **Second scenario** — Northbridge must demonstrate comprehension, pacing,
   and replay pull first.
7. **Server-side analytics dashboard or experiment framework** — raw local
   export and pure summary are enough for the next five-to-twenty playtests.
8. **New balance fixes for extreme ending bands or numeric power-allocation
   costs** — separate instrumented rules work with its own ruleset bump; Wave 3
   must not hide it inside presentation commits.

## 16. Open questions (defaults chosen)

1. **localStorage or IndexedDB?** Default: bounded localStorage. The expected
   volume is small, export is explicit, and quota failure is harmless. Move only
   if real exports approach the cap.
2. **Telemetry default on or off?** Default: on in local development/playtest
   builds, off in packaged/public builds, with an obvious local control.
3. **Modal or inline contextual teaching?** Default: inline/non-modal whenever
   the object is already visible; use an accessible dialog only when focus must
   be deliberately paused.
4. **When does expedited review unlock?** Default: after two acknowledged turns,
   not merely after turn number advances, so the complete reveal/archive ritual
   has been experienced twice.
5. **Should the causal lead be generated in the frontend?** No. Build it once in
   the deterministic stdlib engine, record it with references, serialize it, and
   freeze it with the presentation so backend/UI/dossier wording cannot drift.
6. **Should the full consequence record collapse on turn 1?** No. It defaults
   open for turns 1–2, then closed; the player learns the proof before receiving
   the shortcut.
7. **What counts as abandonment?** Nothing automatically. Record the final
   phase/turn seen and let playtest analysis use cautious language; browser close
   is not proof of abandonment.

