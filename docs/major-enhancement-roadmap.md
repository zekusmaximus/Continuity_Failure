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

> **Wave 2 is complete** (2026-07-11, batches A1–A4 + B1–B4 on this branch;
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
