# Major Enhancement Roadmap — Waves 2+

This roadmap sequences the remaining Major Enhancements and Hidden
Opportunities from `docs/comprehensive-engineering-ux-review-2026-07-09.md`
(§16–17), in dependency order, in the same spirit as
`docs/medium-improvement-batch-prompts.md`.

**Wave 1 is complete** (see git history on this branch): thread lifecycle
(ME#1a), institutional debt ledger + client memory (ME#1b, HO#2, HO#7),
evidence citation (ME#1c), living factions + leak rule (ME#2), and the
multi-axis outcome assessment (ME#3, HO#9). The review's headline balance
exploit is closed twice over: contractor spam now fails in-loop on legal
exposure from compounding sole-source precedents, and any high-dependency
completion is graded as a damning ending rather than a win.

Each wave below assumes the previous waves are merged and the repository is
green (`pytest`, `python -m engine.content validate`, `npm run test:ci`).
Every design invariant in `AGENTS.md` still binds: the engine stays
stdlib-only and deterministic, every mutation flows through `apply_diffs`
with a legible reason, AI never mutates state, snapshots stay append-only.

## Dependency overview

| Wave | Outcome | Depends on |
| --- | --- | --- |
| 2a | Versioned-engine completion: branchable/faction-gated calls, seed variants, ruleset_version (ME#4 remainder) | Wave 1 |
| 2b | Diegetic degradation + playable degraded workstation (ME#6, HO#8) | Wave 1 |
| 3a | Identity/security layer for shared deployment (ME#5) | none (schedule when launch is real) |
| 3b | Comprehension-focused playtest telemetry (HO#10) | 3a for shared deployments |
| 4a | The record as a playable object (HO#1) | Wave 1 (memo artifacts, canon) |
| 4b | Counterfactual dossier (HO#3) | 2a (replayable variants) |
| 4c | Consultant ethics profile (HO#4) | Wave 1 endings + ledger |
| 4d | Evidence contradiction graph (HO#5) | Wave 1 citations |
| 4e | Deadline budget (HO#6) | Wave 1 citations |
| 5 | Additional read-only AI tools (ME#7) | everything above (per the review) |

> **Wave 2 is complete** (2026-07-11, batches A1–A4 + B1–B4 merged by PR #4;
> plan: `docs/wave-2-implementation-plan.md`). Shipped: ruleset_version with
> golden-trace pinning, content-authored thread specs, faction-gated call
> variants, seed variants, power_stability drivers (ruleset "2"),
> degradation bands with capability gating, the degraded workstation UI,
> and the CRITICAL-band auxiliary-power choice (HO#8).
>
> **Trimmed from Wave 2, returned here with reasons** (plan §7):
> 1. *Faction-field overrides in seed variants* — variable perturbations
>    deliver the replayability payoff; revisit with 4b, which will exercise
>    variants hard.
> 2. *Numeric world-state costs for unpowered subsystems* — the CRITICAL
>    allocation is capability-gating only; attaching diffs is a balance
>    change (survival headroom is 2 points of budget) that deserves its own
>    instrumented pass after playtesting the bands.
> 3. *Playwright e2e for the degraded path* — needs a long scripted
>    playthrough; covered by vitest band tests + the manual checklist. A
>    seeded low-power scenario variant would make this e2e cheap.
> 4. *Comms degradation affecting adherence/decisions* — belongs with Wave
>    5's AI tools, where model access has in-world costs to degrade.

### Post-Wave-2 gates (fix before adding more systems)

The merge is technically green, but the post-merge adversarial review found
three reachability/choice defects that must precede Wave 3 feature work:

1. Make the turn-4 contractor variant naturally reachable (the exact minimum
   pre-turn trust is 40; its authored gate is 25), or rewrite the trigger around
   a state the first three turns can actually produce.
2. Make CRITICAL play reachable through an authored, balanced route (the lowest
   current path is `hot_summer` at power 28), then add the trimmed Playwright
   journey. Do not merely add a dev-only low-power switch and call the feature
   playable.
3. Bind auxiliary power to a decision window. Today a persistent memo can be
   drafted under provisional `MODEL_ACCESS`, then sent under `LIVE_DATA` with
   citations; `COMMUNICATIONS` also reveals nothing before the player chooses.
   Preserve the one-subsystem fiction in both workflow and record.

Also correct the stale-evidence contradiction (documents authored after
`last_live_turn` currently appear under an earlier “last verified” stamp), keep
call variant/allocation facts visible in the dossier, and align content/API id
validation before expanding authored packages.

## Remaining §16–17 ledger

This is the truthful remainder of the 2026-07-09 review after Waves 1 and 2.
The original ten Quick Wins and ten Medium Improvements are implemented: frozen
turn presentation; synchronized cursors/freshness; corrected copy; directional
state indicators; restart/resume; operational memo fallbacks; strict requests;
focus/reduced motion; humanized variables; **Close Turn**; SQLite; atomic
idempotency; the desk guide; accessible phase/dialog navigation; contextual
advice; memo artifacts; the causal waterfall; split validated content; frontend
E2E; and structured request logs. The only medium-layer coverage debt is the
trimmed natural degraded/CRITICAL Playwright journey, which is blocked by the
reachability defect above rather than by test infrastructure.

| Review item still open | Why it waits |
| --- | --- |
| **3a / ME#5 — identity and security** | Local single-player has no ownership boundary. Implement when a shared playtest/deployment is scheduled, so the account/token model, quotas, CORS/CSP, and audit policy are designed for a real threat model. |
| **3b / HO#10 — comprehension telemetry** | Instrument only after the immediate loop/pacing hypotheses in `player-experience-plan.md` are named. Keep collection local-first and export opt-in; shared aggregation depends on 3a. |
| **4a / HO#1 — record as a playable object** | Needs the Wave-2 record defects fixed first so what the player seals or omits is the same fact the archive preserves. This is the highest-value record-centered feature. |
| **4b / HO#3 — counterfactual dossier** | Ruleset/variant stamping now exists, but old-version execution does not. Define replay compatibility and simulation-not-canon labeling before presenting a road not taken as trustworthy. Faction-field seed overrides return here only if they materially improve comparisons. |
| **4c / HO#4 — consultant ethics profile** | Endings and ledger inputs exist, but verdict/band reachability needs tuning first; otherwise the profile will infer identity from axes players cannot move into all intended ranges. |
| **4d / HO#5 — evidence contradiction graph** | Citation plumbing exists. It waits on a small authored edge vocabulary and UX that makes contradictions actionable rather than adding another library view. |
| **4e / HO#6 — deadline budget** | Add only after measuring first-run reading burden and evidence use. A research budget should create civic pressure, not punish players for learning an already dense interface. |
| **5 / ME#7 — read-only AI tools** | Research, rumor classification, and scenario analysis require evidence provenance, retention rules, 4e costs, and a degradation choice that cannot be bypassed. The model remains advisory and outside authoritative state. |

Wave-2 trims remain open as follows: faction-field variant overrides wait for
4b; numeric allocation costs wait for a reachable choice and balance pass; the
degraded Playwright path follows the reachability fix; communications effects on
NPC adherence wait for Wave 5, while communications *presentation timing* is an
immediate workflow correction rather than a future AI feature.

## Wave 2a — Versioned scenario/rules engine completion (ME#4 remainder)

The content pipeline (versioned JSON packages, schema, validator, loader)
already exists. Remaining:

- **Branchable calls.** Allow a turn to author multiple call variants selected
  by deterministic conditions over world state and faction fields (the same
  `ThreadCondition` shape used by thread resolution). This absorbs the wave-1
  trims: faction-gated call variants (a caller whose trust collapsed opens
  with a different ask) and moving `_DYNAMIC_THREAD_SPECS` from
  `engine/consequences.py` into content.
- **Deterministic seed variants.** A campaign-creation `variant` id that
  selects among authored starting-state perturbations — replayability without
  randomness. Persist the variant id on the campaign for exact replay.
- **`ruleset_version`.** Stamp campaigns with the rules version that resolved
  them; the replay/determinism suite pins old fixtures to old versions so
  balance tuning never silently rewrites history. Snapshot normalization in
  `memory/persistence.py` already handles additive model fields.

## Wave 2b — Diegetic degradation (ME#6 + HO#8)

`power_stability` never changes today, and `SystemStatusModel` already derives
comms/data-freshness for display. Make it real:

- Give `power_stability` deterministic drivers: ambient drift in
  content-authored windows, thread escalations, and advice effects.
- Deterministic degradation bands gate capabilities: below thresholds the desk
  loses live feeds (evidence board shows stale snapshots with their
  `last_verified` stamp), the memo drafter falls back to system drafts
  (`ai_available=false` diegetically), and turn presentation carries a
  degraded visual treatment.
- HO#8's choice moment: under low power the player picks which subsystem to
  keep (model access vs. communications vs. live data), as a per-turn
  constraint, not a twitch mechanic.

## Wave 3a — Identity/security layer (ME#5) — schedule when a shared deployment is actually planned

Deferred by explicit decision (2026-07-11): the app is local/single-player.
When a closed playtest or public deployment is scheduled: opaque 128-bit
campaign ids, ownership (accounts or signed local-first tokens), per-route
authorization, rate limits and quotas, per-user AI budgets, audit trail,
CORS/CSP hardening. The review's §11 checklist is the source of truth.

## Wave 3b — Comprehension telemetry (HO#10)

Track evidence opened, option comparison, time-to-choice, Case File use,
abandon phase, and "why did this change" expansions. Never log memo content.
Local-first storage; export is explicit.

## Wave 4 — Record-centered play

- **HO#1 record as playable object:** players choose what is written, sealed,
  cited, or omitted; later hearings compare the memo of record, the client's
  action, and the actual diffs (all three already exist as typed artifacts).
- **HO#3 counterfactual dossier:** at campaign end, re-run two pivotal turns
  against the deterministic engine with the road-not-taken advice and show the
  divergence, clearly labeled simulation-not-canon. Needs 2a's
  `ruleset_version` pinning.
- **HO#4 ethics profile:** derive a consultant identity (institutionalist,
  disclosure maximalist, dependency broker, state-integration advocate,
  shadow operator) from the wave-1 outcome axes + debt ledger + citation
  record; feed future client dispositions.
- **HO#5 evidence contradiction graph:** author support/contest/derivation
  edges between documents; render the Evidence Board as a reasoning tool;
  citing contradicted evidence interacts with the wave-1 citation costs.
- **HO#6 deadline budget:** a limited number of research/document actions per
  turn so citation choice stays meaningful as the document set grows.

## Wave 5 — Additional read-only AI tools (ME#7)

Last, per the review: research console, rumor classifier, scenario analysis.
Each requires evidence citation, a resource cost (2b's degradation and 4e's
budget give it teeth), a retention policy, and gameplay integration. The
existing `backend/app/ai/` validation boundary (models never mutate state)
is the template.
