# Comprehensive Engineering & UX Review

**Repository:** Continuity Failure  
**Review date:** 2026-07-09  
**Reviewed revision:** `bfca55a` (`fixes`)  
**Working tree at review start:** clean  
**Review posture:** public-launch readiness, with UX, onboarding, visual design, and player comprehension weighted most heavily

## Review basis

This review is based on the repository implementation, not only its design documents. The engine, backend, AI boundary, frontend components, styles, content, prompts, documentation, and test suite were inspected. The local application was run and walked through from first launch through the first call, brief, evidence, advice, memo draft, NPC decision, consequences, and Case File. Desktop and narrow-screen layouts were inspected.

Verification results:

- `pytest -q`: **146 passed**, with one Starlette/httpx deprecation warning.
- `npm run build`: **passed**; production output was 188.72 kB JS (57.29 kB gzip), 29.21 kB CSS (5.72 kB gzip), and 0.44 kB HTML.
- A dedicated Chrome performance trace was unavailable in this workspace. Core Web Vitals are therefore marked unmeasured rather than estimated.
- A balance diagnostic that repeated each global advice option found that repeating `contractor_pressure` alone completes the campaign while ending at `contractor_dependency = 100`.

Labels used below:

- **Objective:** directly evidenced by code, runtime behavior, tests, or measured output.
- **Design judgment:** a product or aesthetic recommendation whose value depends on the intended experience.

---

## 1. Executive Summary

### Overall quality score: **6.5 / 10**

This is a strong, unusually coherent vertical slice with a credible institutional tone, a clean deterministic core, and a polished visual identity. It is not ready for public launch. It is ready for structured playtesting after a focused correctness and onboarding pass.

### Launch readiness

**Internal prototype / portfolio demo:** ready.  
**Closed playtest:** nearly ready after the quick-win fixes.  
**Public launch:** not ready.

Public-launch blockers:

1. **No durable session or resume path.** Refreshing the frontend loses the active campaign ID; restarting the backend deletes every campaign (`memory/persistence.py`, `frontend/src/App.tsx`).
2. **The turn reveal is temporally incorrect.** Immediately after advice submission, `App.tsx:87-88` refreshes the next turn before showing the prior turn's decision. The header displays Turn 2 and post-turn values while the main screen still says “Client decision · Turn 1.” The Case File also exposes Turn 2 evidence before Turn 1 is archived.
3. **Several headline systems are descriptive rather than mechanical.** Documents, canon, open threads, faction influence, red lines, risk tolerance, trust, and most player-standing variables do not affect resolution. The crisis cascade is principally textual.
4. **Balance permits behavior that contradicts the fiction.** Repeating contractor pressure for all ten turns completes the campaign even at maximum contractor dependency. Completion is binary survival, not quality of stabilization.
5. **Public API security and integrity controls are absent.** There is no authentication, authorization, rate limiting, request idempotency, campaign ownership, or durable transaction boundary. Eight-character campaign IDs are only 32 bits (`engine/seed_data.py:1182-1185`).
6. **Accessibility has material modal, focus, semantics, and motion gaps.** The drawer and document dialog neither move nor trap focus, and background content remains exposed in the accessibility tree (`frontend/src/components/CaseFile.tsx:41`, `DocumentDetail.tsx:31`).

### Biggest strengths

- The central authority boundary is real: model output cannot directly change `WorldState.variables`; turn mutation goes through deterministic engine code.
- Applied variable diffs are legible and useful.
- The player/NPC separation is visible in the decision screen.
- Northbridge's writing is specific, procedural, and tonally disciplined.
- The guided one-task-at-a-time flow is substantially clearer than a dense simulation dashboard.
- The visual system is cohesive, restrained, and appropriate to the fiction.
- The test suite is fast and protects several important invariants.
- The frontend production bundle is already small.

### Biggest weaknesses

- The game currently asks the player to study rich evidence and factions that the rules do not consume.
- The frontend reveals next-turn state too early and offers no back navigation or session recovery.
- The same six global recommendations can answer almost every call, weakening the consulting fantasy.
- The memo drafter produces display-only prose; it is not editable, saved, sent, or referenced by the turn record.
- The repository's own launch-facing documentation contradicts the implementation in several places.
- The backend lacks atomic turn submission and duplicate-request protection.

### Highest-value improvements

1. Freeze the just-resolved turn's header/Case File snapshot until archive, and update `WorldState.turn_number` correctly.
2. Add expected-turn/idempotency validation and a per-campaign transaction lock.
3. Add SQLite persistence plus resume/recent-engagement UI.
4. Make each call mechanically constrain or alter advice, NPC incentives, ambient events, and open-thread consequences.
5. Turn the memo into the artifact actually sent and archived.
6. Add a five-minute first-turn tutorial with indicator direction, failure thresholds, evidence relevance, client adherence, and ambient drift.

### Technical debt assessment

**Moderate to high.** The code volume and dependency footprint are lean, so this is not framework debt. The debt is semantic: duplicated schemas, magic-string dispatch, a 1,211-line content module, global in-memory services, non-atomic mutation, and systems whose data model is richer than their behavior. That debt will compound quickly when adding more scenarios or AI tools unless the scenario/rule contract is formalized first.

---

## 2. Architecture Review

### What works

- **Separation of concerns is strong at the top level.** `engine/` is framework-free; routes are thin; Pydantic mapping is at the API boundary; the frontend does not calculate authoritative outcomes.
- **The deterministic entry point is easy to locate.** `engine/turn.py:43` owns turn advancement.
- **The AI validation boundary is well-shaped.** `backend/app/ai/runner.py` centralizes prompt loading, provider calls, validation, retry, fallback, and logging.
- **The contract test is useful.** `tests/test_contract.py` catches field-name drift across dataclasses, Pydantic, and TypeScript.

### Objective architecture issues

1. **Not every authoritative mutation produces an `AppliedDiff`.** `engine/rules.py:459-503` mutates every faction's `posture` and the crisis `severity` directly. These fields are displayed to the user and are authoritative world state, but no diff records why they changed. `world_state.last_verified`, campaign status, and turn count are also mutated outside the diff mechanism. This is narrower than the repository's broad “every state change is explainable” promise.

   **Alternative:** introduce typed domain events/diffs for non-variable state (`FactionPostureChanged`, `CrisisSeverityChanged`, `CampaignStatusChanged`) or explicitly narrow and document the invariant to numeric variables only.

2. **Turn mutation is not atomic.** `advance_turn()` mutates the campaign in place before consequence generation, canon creation, and history append. An exception after `apply_diffs()` can leave state changed without a complete turn record.

   **Alternative:** resolve against a copied snapshot, construct a complete `TurnResult`, validate invariants, then commit the new campaign state in one store transaction.

3. **Store locking is too shallow.** `MemoryStore` locks individual `get`/`set` calls, but `campaign_service.submit_advice()` retrieves a mutable campaign and changes it after the lock is released (`memory/persistence.py`, `backend/app/services/campaign_service.py:162`). Two requests can operate on the same campaign without a transaction.

4. **Unknown variables fail silently.** `engine/diffs.py:29` ignores a delta for an unknown variable. A typo in scenario content therefore removes an effect without failing a test or request.

   **Alternative:** raise `UnknownStateVariable` during scenario validation and turn resolution. Allow explicit optional effects only through a separate API.

5. **Content and mechanics are coupled by magic strings.** Adding an advice type can require synchronized edits in seed data, `_ADVICE_TAG_DISPATCH`, immediate consequence pools, thread rules, and UI labels. `_primary_tag()` falls back to `disclosure` for an unknown tag, which can narrate the wrong outcome.

   **Alternative:** create a validated `AdviceRule` registry keyed by a typed advice kind, containing the decision resolver, consequence renderer, allowed call types, and content contract.

6. **`engine/seed_data.py` is an under-engineered content pipeline.** At 1,211 lines it mixes state tuning, factions, advice, documents, calls, and campaign construction. It is reviewable for one scenario but will not scale safely.

   **Alternative:** move scenario content to versioned YAML/JSON files validated against a schema, while keeping executable rules in Python. Validate unique IDs, referenced IDs, ranges, advice tags, turn availability, and state-variable names at load time.

7. **Replayability is version-fragile.** Turn history stores results, but not a scenario version, ruleset version, starting-state snapshot ID, input document set, or stable rule IDs. Free-text reasons are not durable identifiers. A future rules change prevents faithful replay of an old campaign.

   **Alternative:** persist immutable campaign/turn snapshots with `scenario_version`, `ruleset_version`, `starting_snapshot`, input IDs, selected advice ID, deterministic rule IDs, and ending snapshot.

### Overengineering / underengineering

- **Overengineering:** none material. The project is appropriately small.
- **Underengineering:** transactions, persistence, scenario validation, typed vocabularies, and mechanical integration of evidence/factions/canon.
- **Unnecessary abstraction:** `_risk_label(variable, value)` in `engine/dossier.py` ignores `variable`.
- **Missing abstraction:** a scenario/rules registry and repository interface around persistence.

---

## 3. Backend Review

### API and routing

Routes in `backend/app/api/campaigns.py` are concise and map engine errors to sensible 400/404/409 responses. Response models are explicit.

Problems:

- **No idempotency or expected-turn check.** Repeating a valid advice request advances another turn. Every mutation request should include `expected_turn_number` and an idempotency key; stale or duplicate requests should return 409 without mutation.
- **Check-then-act is duplicated.** Routes call `get_campaign()` and then the service retrieves the campaign again. This neither prevents a race nor improves error handling.
- **Terminal `/current` remains semantically loose.** A terminal campaign has no call but can still expose global advice options through `available_advice()`.
- **No list/resume endpoint.** The frontend cannot recover a campaign after refresh even while it remains in process memory.
- **No pagination.** `/turns` returns the full nested history and `/current` includes a full last turn. Acceptable at ten turns, but the contract does not scale.

### Models and validation

- **Pydantic models mostly describe shape, not validity.** Numeric 0-100 fields have no `ge`/`le`; vocabularies are strings rather than `Literal`/Enum; campaign names and advice IDs have no length constraints (`backend/app/schemas/api.py:125-130`).
- **Extra fields use Pydantic's permissive default.** Unexpected request keys are silently ignored.
- **`WorldState.turn_number` is stale.** `Campaign.turn_number` advances, but `world_state.turn_number` is never updated in `engine/turn.py`. API consumers receive contradictory turn metadata.
- **Final freshness can say Turn 11.** `last_verified` is set to `resolving_turn + 1`, including after the tenth and final turn.
- **Canon faction identity is inconsistent.** `involved_factions` is populated with the decider's display name rather than a faction ID (`engine/turn.py:131`).

### Services, persistence, and race conditions

- Module-level `_STORE` singletons simplify the MVP but prevent horizontal scaling, durable recovery, and clean dependency injection.
- `CampaignStore` is thread-safe only as a map, not as a unit-of-work.
- `save_json()` uses `default=str`, which is not a reversible campaign serialization format, and `load_json()` returns dictionaries rather than reconstructed campaign objects. It should not be presented as a durability seam without a versioned codec.
- No optimistic concurrency, request deduplication, or rollback exists.

### AI backend

Strengths:

- AI is off by default.
- Model output is schema-validated and falls back deterministically.
- The model package does not import mutation code.

Weaknesses:

- The “retry” repeats the same request; it does not add a corrective validation message despite documentation saying it may.
- `MemoDraft` requires arrays but does not enforce at least one item or maximum lengths.
- A provider implementation that raises unexpectedly escapes `run_artifact`; only `AnthropicProvider` currently catches its own exceptions.
- Provider construction failures are swallowed without logging the cause.
- Transport error details are discarded by the runner; a logged run records status but not the error.
- Token use is logged, but cost is never calculated.
- `CF_AI_MAX_TOKENS` accepts negative or extreme values.
- Live calls are synchronous and have no explicit application-level timeout or circuit breaker.
- Repeated unauthenticated `/memo` calls can create external model cost when live AI is enabled.

### Logging and error handling

There is no structured application logging, request/correlation ID, audit log, exception reporting, or metrics. Model-run logging is in-memory and its public projection omits raw/parsed output, token use, cost, and errors, so the UI's “inspectable” claim is partial.

### Backend refactoring priorities

1. Add `CampaignRepository` plus transactional `resolve_turn(campaign_id, expected_turn, idempotency_key)`.
2. Persist SQLite snapshots and model runs with schema/rules versions.
3. Introduce strict Pydantic request models and typed enums/ranges.
4. Add structured logs and safe AI timeout/rate-limit/circuit-breaker controls.
5. Split scenario content from rule implementation.

---

## 4. Frontend Review

### Architecture and state management

For this app size, local React state is reasonable. Components are named well, phase boundaries are clear, and authoritative calculation stays on the server.

Objective issues:

- `App.tsx` holds a single volatile session. There is no URL campaign ID, local storage, resume path, or server campaign list.
- The frontend eagerly refreshes next-turn state before displaying the resolved turn (`App.tsx:87-88`), causing the temporal mismatch described above.
- Phase state is not recoverable. Refresh always returns to `INTRO` and creates a new campaign.
- The UI has no back navigation. The stepper is display-only; skipping evidence is effectively one-way except through the dense Case File.
- System status is fetched and typed but never rendered. The promised power/comms/data-freshness/AI workstation state has no visible component.
- Dossier and model-run panels refetch on remount; there is no request cache. Low impact at current scale.

### Component structure

The phase components are sensibly split. `GuidedTurn` is approaching a state-machine responsibility but remains manageable.

Recommended changes:

- Replace the switch plus independent state variables with an explicit reducer/state machine that encodes legal phase transitions and preserves a `resolvedTurnView` snapshot.
- Give every phase a stable heading and focus target.
- Add a compact persistent “decision context” rail on Evidence and Advice: caller, ask, deadline, and top two relevant indicators.
- Make the stepper navigable backward within an unresolved turn.
- Preserve the campaign ID in the URL and resume on load.

### Rendering and performance

No material rendering bottleneck exists. The bundle is small, the DOM is modest, and computations are trivial. The advice page is tall—six cards produced about 1,515 px of stage content at 1280×720—but this is a usability issue, not a CPU issue.

### Responsiveness

At 390×844 the interface remains operable, but the header consumes roughly one-third of the viewport, the turn counter wraps vertically, metadata is 9-11 px, and the content viewport becomes cramped. The repository explicitly calls mobile out of MVP scope, but a public web launch still needs a supported minimum width.

---

## 5. User Experience Review (Highest Priority)

### First-time walkthrough

#### First impression

The intro is focused, atmospheric, and immediately communicates the strongest premise: “You are not the decision-maker.” The palette and restraint feel credible.

The footer then says “No AI systems in this build,” contradicting the shipped memo drafter and Model Runs screen (`frontend/src/components/IntroScreen.tsx:45`). This weakens trust before play begins.

#### Incoming Call

What works:

- Caller, urgency, horizon, exposure, ask, and private pressure are presented clearly.
- The empty space creates focus and urgency.

Likely question: **“What does accepting the call commit me to?”**  
Improvement: explain that Accept Call is only a presentation step and does not spend a turn.

#### Situation Brief

What works:

- Known facts, unknowns, and immediate risks are well separated.
- The active crisis banner provides useful framing.

Confusion:

- “Affected institutions” selects factions by global pressure/influence (`BriefPhase.tsx:33-35`), so Turn 1 shows nine of ten factions. It is not meaningfully affected-by-this-call information.
- The player sees severity 54 but no explanation of its direction, threshold, or consequence.

Likely thought: **“Which of these nine institutions actually matters to this decision?”**  
Improvement: derive 3-4 call-specific stakeholders from attached documents, caller, and advice relevance.

#### Evidence Review

What works:

- Critical/Relevant/Background grouping is a good progressive-disclosure pattern.
- Reliability and public status are visible.

Confusion:

- All first-turn documents are Critical, so prioritization does not help.
- Nothing marks a document read, cited, contradictory, or decision-relevant.
- The player can continue without opening anything, and evidence never changes mechanics.

Likely thought: **“Why should I read this instead of using the risk numbers on the advice cards?”**  
Improvement: let evidence unlock/strengthen advice, reduce uncertainty ranges, or support the record; show “cited by this option” on advice cards.

#### Advice

This is the highest-cognitive-load screen. Six full cards require roughly three viewport heights before selection; a seventh appears on some turns. Every global option remains available even when it does not answer the caller's ask.

Likely thoughts:

- **“Why can I answer a school-closure request with contractor pressure?”**
- **“Are these risk scores predictions, fixed effects, or just editorial labels?”**
- **“What do the current state and faction red lines imply for adherence?”**
- **“Can I compare two options without repeatedly scrolling?”**

Improvements:

- Show 3-4 contextually relevant options first; move “broader strategic alternatives” behind an expander.
- Add a compact comparison mode with legal/political/operational risk, expected state direction, and likely client reaction.
- Keep the caller's ask and current deadline pinned.
- Explain that risk scores are descriptive and that exact results depend on client adherence plus ambient drift.

#### Memo draft

The feature does not fulfill the memo-writing fantasy yet. The deterministic fallback converts benefits into pseudo-actions such as “Pursue: Trust and information integrity improve,” exposes faction IDs like `town_managers_office`, and cannot be edited, accepted, saved, sent, or archived (`backend/app/ai/fallbacks.py:46`). Sending advice ignores the memo.

Likely thought: **“Did drafting this memo change what I am sending?”**  
Improvement: make the memo an editable artifact with explicit `Use this draft`, `Edit`, and `Attach to advice` states; archive exactly what was sent.

#### Client Decision

The separation between advice and client action is excellent in concept and mostly clear in execution.

Critical confusion: the header already says Turn 2 and shows post-turn values while the body says Turn 1. The player sees consequences before clicking “Resolve Consequences.”

Likely thoughts:

- **“Did I accidentally advance twice?”**
- **“Why did Water Security already drop?”**
- **“Am I looking at Turn 1 or Turn 2?”**

Improvement: retain a frozen Turn 1 header snapshot through Decision, Consequences, and Archive; transition to Turn 2 only after Next Call.

#### Consequences

What works:

- The human-readable stack precedes raw diffs.
- The net state-change table is useful.

Confusion:

- The aftermath says `media_pressure 28→32`, while the net state table says Media Pressure 28→35 because ambient drift is applied later. Both are true, but the discrepancy is unexplained.
- “Largest registered move” excludes ambient drift and can disagree with the largest net change.
- Raw snake_case variable names appear in narrative.
- The header leaked the values one screen earlier.

Likely thought: **“Which number is the real final value, 32 or 35?”**  
Improvement: render a causal waterfall per important variable: Advice +4, NPC 0, Ambient +3, Final +7. Label “largest advice/NPC move” precisely.

#### Archive and Next Call

“Archive Turn” performs no backend archive operation; the turn was already committed when advice was sent. It is a narrative pause presented as an action. “Resolve Consequences” is also a reveal-only click. Across ten turns the player performs roughly seventy mandatory phase clicks before optional evidence interactions.

Likely thought after several turns: **“Why am I clicking through the same filing ritual again?”**  
Improvement: after the tutorial turn, combine Decision and Consequences into a staged reveal on one screen and make Archive passive/automatic. Target 4-5 mandatory actions per turn.

#### Campaign Dossier

Copy/download are useful, but the in-app dossier is raw Markdown in a `<pre>`, not a polished case file. It contains the false footer “AI integration is not implemented” (`engine/dossier.py:108`). There is no outcome grade, key turning points, counterfactual, client assessment, or next engagement hook.

### Cross-flow friction

- No save/resume, undo, restart confirmation, or recent engagements.
- Errors are banners without retry actions.
- No keyboard shortcut for the primary action.
- No contextual help or glossary.
- No history of which evidence or memo supported a recommendation.
- The Case File can reveal the next turn's document while the prior turn is still being presented.

---

## 6. Onboarding Review (Highest Priority)

### Current onboarding

The intro explains the role and tone but not the rules. The first turn is not a tutorial; it is the full game with six complex options.

Missing explanations:

- Ten-turn objective and what “completion” means.
- Higher-is-better versus higher-is-worse indicators.
- Failure thresholds.
- Ambient crisis drift.
- Client adherence and modification.
- Difference between reliability, public status, and fact classification.
- Whether risk numbers are authoritative.
- Why the Case File matters.
- What AI/system draft provenance means.
- That New Engagement discards the frontend's current session.

### Recommended first-session flow

1. **Intro:** premise, ten-turn stabilization objective, “your advice is mediated.”
2. **Guided first call:** spotlight caller, deadline, and ask; explain that accepting is non-binding.
3. **Brief tutorial:** annotate Known / Unknown / Risk and show one stakeholder, not nine.
4. **Evidence tutorial:** require opening one contested and one high-reliability document; explain how reliability affects confidence.
5. **Advice tutorial:** initially show three relevant options; explain risk scores and preview “client may modify.”
6. **Commit preview:** summarize the recommendation, evidence cited, known benefit, main risk, and that the action cannot be undone.
7. **Decision reveal:** show adherence in plain language (“used about three-quarters of your plan”).
8. **Consequence waterfall:** distinguish advice, client modification, and ambient pressure.
9. **Archive:** explain canon and one open thread.
10. **Turn 2 onward:** collapse tutorial copy into optional `?` help and reduce mandatory clicks.

Progressive disclosure should preserve the current focused aesthetic while adding a glossary drawer and contextual help links.

---

## 7. Game Design Review

### Gameplay loop

The fiction of advising while others decide is distinctive. The actual loop, however, is currently closer to selecting a global strategy card and reading deterministic prose than preparing institution-specific advice from evidence.

### Objective mechanical gaps

- Faction `influence`, `trust_in_player`, `risk_tolerance`, `current_pressure`, and `red_lines` are seeded and displayed but not used by `decide()`.
- Calls and attached documents do not affect state or decision resolution.
- Canon entries do not influence future turns.
- Open threads accumulate but are never escalated, stabilized, resolved, or consumed by later rules.
- `player_perceived_neutrality` never changes; player standing is mostly inert.
- `DecisionType.REJECTED` has narrative support but no current decision handler returns it.
- `power_stability` never changes, so workstation degradation cannot emerge.
- Only turns 2, 3, and 7 have call-specific advice; global options remain available everywhere.

### Balance and challenge

The repeated-strategy diagnostic found:

- Full disclosure fails on public order at turn 8.
- Controlled disclosure fails on budget at turn 9.
- Delay fails on legal exposure at turn 8.
- State support fails on oversight at turn 8.
- Mutual aid fails on budget at turn 6.
- **Contractor pressure completes all ten turns**, ending with `contractor_dependency = 100`.

This is a major thematic and balance problem. Maximum dependence on a sole-source contractor should materially damage completion quality, trigger a thread/failure, or shape the ending. Binary survival currently rewards the behavior the fiction warns against.

### Pacing

The ten calls form a strong authored escalation. Mechanical pressure is less varied because ambient drift is identical each turn and most advice effects are unchanged. The procedural sequence becomes repetitive after the novelty of the first two turns.

### Progression and motivation

There is no score, end-state grade, client trust trajectory, ethics/reputation arc, unlock, save slot, or follow-on call. Completion means only reaching the end without crossing seven thresholds.

### Replayability

Exact determinism is valuable for testing and explanation but produces little replay variation. A single scenario with fixed calls and fixed rules will be solved quickly. Replayability should come from deterministic scenario seeds, hidden-but-auditable institutional constraints, alternate starting records, branching calls, and ending grades—not opaque randomness.

### Recommended game-design changes

1. Give every turn a deterministic event package that changes drift, faction pressure, deadlines, and available authority.
2. Restrict or penalize off-brief advice; let the player deliberately broaden scope at a shadow-authority cost.
3. Use faction incentives and trust in adherence/rejection rules.
4. Make cited evidence change confidence, legality, or adherence.
5. Make open threads schedule later consequences unless addressed.
6. Add a multi-axis ending: stabilization, legitimacy, dependency, legal record, harm avoided, and consultant power.
7. Make `contractor_dependency = 100` produce a qualitatively compromised ending even if water security is high.

---

## 8. Visual Design Review (Highest Priority)

### What works

- The dark navy/black, civic amber, restrained red/green palette is distinctive and appropriate.
- Typography pairing is coherent: humanist system sans for reading, mono for system metadata.
- Alignment and spacing are consistent.
- Call, brief, and document surfaces have clear hierarchy.
- Animation is restrained rather than theatrical.
- The interface reads as an institutional workstation, not generic cyberpunk.

### Objective visual issues

- Many labels are 9-10.5 px (`frontend/src/styles/global.css`, including lines 476, 496, 503, 541, 631, 647, 740, 746, 765, 774, 782). This is too small for sustained reading and magnifies contrast problems.
- `--accent-dim` on the base background measures approximately **3.82:1**, below WCAG AA for normal text; it is used for 10 px state-group headings. `--crit` on the base background is about **4.28:1**, also below 4.5:1 for normal text.
- Faction Pressure and Influence reuse `levelClass()`, where high values become green. High pressure is not “good,” and influence is magnitude rather than health (`FactionCard.tsx:13-24`).
- The mobile header wraps awkwardly and dominates the viewport.
- The dossier is visually raw Markdown rather than an in-world report.
- No `prefers-reduced-motion` rule exists.

### Design judgments

- The interface is sometimes too uniformly flat. Important decisions, deadlines, and breaking thresholds need stronger focal contrast than metadata.
- Advice cards are too tall for comparison. Modern strategy/game UIs often use a comparison row or compact card grid, expanding one option in a detail pane.
- Consequences would benefit from a timeline/waterfall visual that connects advice → client deviation → ambient event → state outcome.
- The degradation fantasy is absent. No stale-feed treatment, disabled channel, low-power palette, corruption, or missing-data state is driven by the current system status.

### High-value visual polish

- Raise body-supporting metadata to 12 px minimum and reserve 10-11 px for rare labels.
- Add explicit `critical in N` threshold markers to key bars.
- Add previous-value ghost marks and short delta pulses after a turn.
- Replace raw Unicode and generic pills with a small consistent icon set where meaning benefits.
- Render dossiers as semantic sections/cards with a printable mode.
- Create three workstation health themes—normal, strained, degraded—driven by power/comms/data freshness.

---

## 9. User Interface Review

| Screen | What works | What should change |
| --- | --- | --- |
| Intro | Strong premise, clear CTA, polished restraint | Correct the AI claim; add objective, duration, save behavior, accessibility/settings link |
| Incoming Call | Excellent caller/ask/horizon hierarchy | Clarify Accept is non-binding; show the one or two state indicators most relevant to this call |
| Situation Brief | Known/unknown/risk grouping is strong | Replace nine “affected” factions with call-specific stakeholders; explain severity |
| Evidence Review | Good prioritization and readable document modal | Track read/cited state; make evidence mechanically relevant; add contradictions; fix modal focus |
| Advice | Rich tradeoffs and honest harms | Reduce default choices, add comparison, pin the ask, explain score semantics, add commit preview |
| Memo Draft | Honest provenance label | Make it editable/attachable/persistent; use faction names and actual operational actions |
| Client Decision | Strong expression of indirect power | Freeze prior-turn header/state; translate adherence; show which memo/evidence the client used |
| Consequences | Best information design in the app | Add causal waterfall; humanize variable names; reconcile intermediate vs final values |
| Archive | Concise record | Make passive or combine with consequence closeout; it is already archived |
| Case File | Good on-demand home for density | Add focus trap, tab semantics, contextual default tab, search/filter, and do not expose next-turn data early |
| Factions | Strong prose and red-line presentation | Stop coloring pressure green; show change over time; connect entries to current advice |
| Full State | Clear grouping | Add direction/threshold legend, deltas, and current-turn causes |
| Canon / Timeline | Useful audit surfaces | Link entries to evidence, advice, diffs, and threads; allow thread status progression |
| Model Runs | Good transparency concept | Include tokens/cost/error/provider outcome and a safe detail view |
| Dossier | Copy/download useful | Render semantic report, add grade/key moments, correct stale AI footer |

---

## 10. Performance Review

### Measured baseline

| Metric | Result | Assessment |
| --- | ---: | --- |
| Production JS | 188.72 kB / 57.29 kB gzip | Excellent for this scope |
| Production CSS | 29.21 kB / 5.72 kB gzip | Excellent |
| HTML | 0.44 kB / 0.30 kB gzip | Excellent |
| Build | 1.30 s Vite build after typecheck | Healthy |
| LCP / CLS / INP / TBT | Not measured; trace tool unavailable | Do not infer |

### Ranked performance findings

1. **Low impact now: repeated full-history serialization.** After every advice, the frontend fetches `/current` and `/turns`; `/turns` grows with every nested turn result. At ten turns this is trivial. For longer campaigns, return an incremental turn result and cache normalized history.
2. **Low impact now: eager single bundle.** Every Case File and dossier component ships initially. At 57.29 kB gzip, code splitting would add complexity for negligible benefit.
3. **Low impact now: dossier/model-run refetches.** Cache by campaign ID and invalidate after mutation.
4. **Potential backend latency risk when AI is live.** Synchronous model calls can occupy request workers; add timeouts and a job/status flow if drafts become slower.
5. **Deployment-dependent:** no production hosting/caching/compression configuration exists. Verify Brotli/gzip, immutable hashed-asset caching, and no-cache HTML at deployment time.

### Recommendation

Do not spend a sprint on frontend micro-optimization. Preserve the small bundle, add real browser performance tracing in CI or pre-release testing, and focus engineering time on durability, correctness, and UX.

---

## 11. Security Review

### Current trust boundaries

The deterministic/model boundary is strong. The network/user boundary is not launch-ready.

### High concerns

1. **No authentication or campaign authorization.** Anyone who knows a campaign ID can read its private/sealed evidence, submit advice, read history, generate memos, and download the dossier.
2. **Campaign IDs are short.** Eight hex characters provide only 32 bits of space and are unsuitable as access control.
3. **No rate limits or quotas.** Attackers can create unbounded campaigns in memory and, when AI is enabled, incur provider cost through `/memo`.
4. **No idempotency/concurrency control.** Duplicate requests can advance multiple turns.
5. **No durable audit/security logging.** There is no record of who read or changed a campaign.

### Medium concerns

- Request fields have no length limits; campaign names can consume memory and expand dossiers.
- CORS is appropriate only for local development (`backend/app/main.py:35-38`) and has no environment-specific production policy.
- No CSP, HSTS, secure-cookie, or proxy-trust configuration exists because deployment is not defined.
- Model-run storage will eventually contain sensitive prompts/outputs; retention, redaction, and access policy are unspecified.
- Provider errors may contain sensitive operational details; decide what is logged and what is returned.
- Dependencies are broad minimum ranges in `pyproject.toml` with no backend lock file or vulnerability scanning.

### Positive findings

- React renders user-provided campaign names as text, avoiding direct HTML injection.
- Dossier content is shown in a `<pre>`, not executed as Markdown/HTML.
- Secrets come from environment variables and are not committed.
- AI input is currently curated scenario data, limiting prompt-injection exposure.

### Public-launch minimum

Use opaque 128-bit IDs, account/session ownership, authorization on every route, CSRF strategy if cookie-authenticated, strict request limits, rate limits, idempotency keys, per-user AI budgets, structured audit logs, production CORS/security headers, locked dependencies, and automated security scanning.

---

## 12. Code Quality Review

### Strengths

- Names are clear and modules have useful docstrings.
- Functions are generally short.
- State-effect code is easy to inspect.
- Frontend components have focused responsibilities.
- Comments explain design intent rather than syntax in most places.

### Code smells and concrete refactors

- **Magic-string vocabularies:** replace string constant classes and tags with typed enums/literals at boundaries.
- **Silent default behavior:** unknown advice tags become generic partial decisions and disclosure consequences. Fail scenario validation instead.
- **Decorative model fields:** either use faction pressure/trust/red lines in rules or remove them until implemented; dormant fields mislead designers.
- **Large content file:** split authored content from executable rules.
- **Duplicated schema definitions:** current tests help, but generate TypeScript types from OpenAPI or a shared schema to reduce maintenance.
- **Contract test limitation:** the TypeScript parser checks field names, not cross-language types; `tsc` only verifies internal TypeScript consistency.
- **Dead/unreachable behavior:** rejected decision branches are currently unreachable.
- **Stale comments/docs:** several “resolved” documentation claims are already false again.
- **Non-standard package field:** remove `allowScripts` from `frontend/package.json` if npm is canonical.
- **No lint/type tooling for Python:** add Ruff and mypy/pyright selectively; frontend has typecheck via build but no ESLint.

---

## 13. Testing Review

### Current quality

The 146-test suite is fast and meaningfully protects bounds, deterministic turn flow, failure/completion, API happy/error paths, AI fallback behavior, and schema field parity. This is a strong foundation.

### Missing or fragile coverage

1. **No frontend unit, integration, accessibility, or end-to-end tests.** The temporal Turn 1/Turn 2 bug is exactly the kind an E2E test should catch.
2. **No concurrency/idempotency tests.** Submit the same turn twice concurrently and sequentially.
3. **No atomic rollback test.** Inject an exception after diffs and assert the campaign is unchanged.
4. **No persistence/restart tests.** None exists yet.
5. **No test that `WorldState.turn_number` matches campaign state.**
6. **No test for non-variable authoritative diffs.** Faction posture and crisis severity change silently.
7. **No reachability test for every advertised NPC decision type.** `REJECTED` would fail.
8. **No balance/property suite over simple strategies and end-state quality.** The contractor-pressure exploit passes current completion tests.
9. **Incomplete content validation.** Per-turn advice effects are not included in `test_advice_effects_only_reference_known_variables`; duplicate IDs, unknown tags, invalid faction references, and turn/document consistency need full validation.
10. **No real-provider contract test or timeout/error-budget test.** Keep it opt-in and mocked at transport boundaries.
11. **No coverage report or mutation testing.** A coverage target is less important than critical-path tests, but the current blind spots are not visible.
12. **A deprecation warning exists.** The test stack should migrate from the deprecated Starlette/httpx integration before it becomes a failure.

### Recommended test layers

- Vitest + Testing Library for phase behavior and accessibility semantics.
- Playwright E2E for first launch, one complete turn, refresh/resume, terminal flow, mobile minimum width, keyboard-only flow, and duplicate submit.
- axe-core checks on every phase and overlay.
- Engine scenario validator tests and strategy/balance fixtures.
- Repository transaction and restart integration tests against SQLite.

---

## 14. Accessibility Review

### What works

- Most interactions use native buttons and radio inputs.
- Radio options are associated with visible labels.
- Escape closes overlays.
- Close buttons have accessible names.
- Major page regions use header/main landmarks.

### Launch-blocking accessibility issues

1. **Modal/drawer focus management:** opening a document or Case File leaves focus on the background trigger. Focus is not trapped, restored, or moved to the dialog. Background content remains in the accessibility tree despite `aria-modal`.
2. **Phase focus management:** after a primary action changes the screen, focus is not moved to the new phase heading and the change is not announced.
3. **Weak heading structure:** most phase titles are styled `<div>` elements rather than headings, so the main content has little semantic outline.
4. **No live regions:** async errors, memo completion, copied state, and turn changes are not announced.
5. **Bars lack semantics:** key indicators and risks are spans without `role="progressbar"`, values, direction, or text equivalents.
6. **Drawer tabs lack tab semantics:** no `tablist`, `tab`, `aria-selected`, or keyboard arrow behavior.
7. **Motion preference ignored:** no reduced-motion mode.
8. **Small text and contrast:** numerous 9-10.5 px labels; accent-dim and critical text combinations fail 4.5:1 on the base background.
9. **Color semantics:** beneficial/harmful state changes rely heavily on green/red; faction pressure is also semantically miscolored.
10. **Raw Markdown dossier:** poor heading/table navigation for screen readers.

### Recommended remediation

Use an accessible dialog primitive or implement focus trap/inert/restoration; make phase titles headings with `tabIndex=-1`; focus them on transition; add `aria-live` for async status; add semantic meters with text direction; implement real tabs; provide reduced motion; raise minimum text size; and run axe plus keyboard-only E2E tests.

---

## 15. Documentation Review

### Accurate/useful documentation

- Root `README.md` explains the premise, architecture direction, setup, and current scope well.
- `AGENTS.md` is unusually effective at protecting product identity and deterministic authority.
- `docs/architecture.md`, `docs/game-loop.md`, and `docs/state-schema.md` contain valuable forward-looking context.
- Prompt discipline is documented clearly.

### Inaccuracies

- `backend/README.md:6` says AI integration is not implemented and omits `/memo`, `/model-runs`, and `/dossier` from the endpoint table.
- `evals/README.md:8` says no AI integration exists.
- `frontend/src/components/IntroScreen.tsx:45` says no AI systems exist.
- `engine/dossier.py:108` says AI integration is not implemented.
- `docs/architecture.md:88` and `docs/branch-review.md:67,121` say 96 tests; the suite has 146.
- `docs/codebase-review.md` claims documentation drift and major open debts are resolved, but several contradictions remain and important UX/mechanical issues are absent from that review.
- `docs/mvp-roadmap.md` marks “AI-generated draft memo that the player can accept/edit” as complete while immediately noting accept/edit is not implemented.

### Missing public-launch documentation

- No license, contributing guide, security policy, deployment guide, production configuration, data/privacy policy, support path, release checklist, migration strategy, or save-data compatibility policy.
- No player-facing manual or glossary.
- No architecture decision records for persistence, auth, model retention, or replay versioning.
- No automated docs truth checks for test counts/endpoints/status claims.

### Recommendation

Separate documents into `as-built`, `roadmap`, and `historical review`; generate the endpoint reference from OpenAPI; stop embedding exact test counts in prose unless automated; and add a single release-readiness document with owners and verification commands.

---

## 16. Prioritized Improvement Roadmap

### Quick Wins (1-2 days), ranked by ROI

1. **Fix temporal turn presentation.** Preserve the resolved turn snapshot until Next Call; do not show next-turn documents/state early.
2. **Synchronize `WorldState.turn_number` and final freshness labels.** Add regression tests.
3. **Correct false AI/test-count documentation and UI copy.** Update backend README, evals README, intro, dossier footer, architecture, and branch review.
4. **Fix faction pressure/influence colors and add indicator direction labels.**
5. **Add restart confirmation and persist campaign ID in the URL/local storage.** Even before SQLite, this can resume while the backend process lives.
6. **Improve memo fallback prose.** Use display faction names and concrete operational steps from a dedicated `operational_steps` content field.
7. **Add strict request constraints.** Name/advice length, extra-field rejection, enum/range validation, max-token bounds.
8. **Add reduced-motion CSS and explicit focus-visible styles.**
9. **Humanize all variable names in aftermath/consequence prose.**
10. **Rename “Archive Turn” to “Close Turn” or make archive automatic.**

### Medium Improvements (1-2 weeks), ranked by ROI

1. **SQLite persistence and resume UI.** Store campaigns, immutable turn snapshots, canon, threads, and model runs.
2. **Atomic/idempotent turn resolution.** Expected turn, idempotency key, transaction lock, rollback test.
3. **First-turn onboarding plus contextual help.** Include failure thresholds, drift, adherence, and indicator direction.
4. **Accessible overlay and phase navigation overhaul.** Dialog focus, inert background, semantic tabs, headings, live regions, keyboard E2E.
5. **Mechanically contextual advice.** Limit primary options per call, price off-brief advice, and use caller/faction incentives in decisions.
6. **Memo artifact workflow.** Draft → edit → attach/send → canon/archive, with exact provenance.
7. **Causal consequence visualization.** Advice/NPC/ambient waterfall and state delta animation.
8. **Scenario content validator and split content files.** Catch unknown IDs/tags/variables before runtime.
9. **Frontend tests.** One-turn E2E, refresh/resume, terminal flow, keyboard, responsive, accessibility.
10. **Basic structured logging and request IDs.** Include turn/campaign/idempotency provenance.

### Major Enhancements

1. **Make evidence, canon, and open threads part of the rules.** Evidence should change confidence/authority; threads should schedule deterministic consequences; prior canon should constrain future decisions.
2. **Faction simulation that uses the existing data.** Trust, influence, red lines, risk tolerance, and pressure should drive adherence, rejection, leaks, and future calls.
3. **Outcome-quality and ending system.** Grade stabilization, legitimacy, legal record, dependency, harm, neutrality, and shadow authority.
4. **Versioned scenario/rules engine.** Data-driven scenario packages, branchable calls, deterministic seed variants, migration/replay compatibility.
5. **Public-launch identity/security layer.** Accounts or secure local-first ownership, authorization, quotas, AI budgets, audit trail, and hardened deployment.
6. **Diegetic degradation system.** Make power/comms/data freshness affect available screens, model choices, latency, confidence, and visual treatment.
7. **Additional read-only AI tools only after the above foundations.** Research, classification, and scenario analysis need evidence citation, resource cost, retention policy, and gameplay integration.

---

## 17. Hidden Opportunities

1. **The record as a playable object.** Let players choose what is written, sealed, cited, or omitted. Later hearings can compare the memo, client action, and actual diff.
2. **Institutional “debt ledger.”** Track emergency precedents—sole-source procurement, informal hospital priority, delayed notice—and make each reduce future options.
3. **Counterfactual dossier.** At campaign end, reveal one deterministic “what likely would have happened” comparison for two pivotal turns, clearly labeled as simulation rather than canon.
4. **Consultant ethics profile.** Derive an identity from behavior: institutionalist, disclosure maximalist, dependency broker, state-integration advocate, or shadow operator. Use it to shape future clients and endings.
5. **Evidence contradiction graph.** Show which documents support, contest, or derive from each other. This would make the Evidence Board a reasoning tool rather than a library.
6. **Deadline budget.** Give the player a limited number of research/document actions per turn. Time pressure would make evidence selection meaningful without adding twitch mechanics.
7. **Client memory.** NPCs should quote prior advice, promises, and deviations. This is a high-immersion use of deterministic canon before adding more generative text.
8. **Playable degraded workstation.** Lose live feeds, fall back to stale archive snapshots, or choose between model access and communications under low power.
9. **Endings that preserve ambiguity.** A completed campaign could stabilize water while hollowing out legitimacy or creating contractor/state dependence. This matches the premise better than pass/fail.
10. **Playtest telemetry designed around comprehension.** Track evidence opened, option comparison, time-to-choice, Case File use, abandon phase, and “why did this change” expansion—without logging sensitive memo content.

---

## 18. Overall Verdict

### What would impress me

- A senior engineer or indie studio has clearly protected the premise in the architecture rather than merely describing it.
- The deterministic boundary, explainable variable diffs, and NPC mediation are real.
- The Northbridge writing is focused, civic, and unusually free of genre clichés.
- The guided redesign and visual language show strong product taste.
- The repository is small, readable, fast to test, and not burdened with unnecessary frameworks.

### What would concern me

- The richest data—evidence, faction incentives, canon, threads—is mostly decorative.
- The UI's temporal state mismatch damages the core promise that consequences are explainable.
- The game can be completed through thematically disastrous contractor dependence.
- The product has no durable session, resume flow, or public API ownership model.
- Accessibility and first-session teaching have not received the same rigor as the deterministic engine.
- Existing internal review documents declare several areas resolved too early.

### What prevents launch

Durability/resume, atomic/idempotent turns, temporal UI correctness, basic auth/ownership and rate limits, accessible dialogs/navigation, truthful documentation, and a game-design pass that makes client calls/evidence/factions mechanically consequential.

### What elevates it from good to excellent

Make the institutional record—not the resource bars—the center of the game. Advice should cite evidence; clients should deviate because of explicit incentives; those deviations should create precedents and open threads; future calls should remember them; the final dossier should judge not only whether water kept flowing, but what kind of institution survived and what the consultant became in the process.

The current repository is a convincing foundation for that game. It is not yet that game.
