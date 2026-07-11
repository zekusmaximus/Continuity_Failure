# Player Experience Plan — From Correct to Compelling

**Date:** 2026-07-11

**Scope:** Northbridge Water Failure only

**Premise:** preserve every invariant in `AGENTS.md`. The player advises, NPCs
decide, the deterministic record remains authoritative, and drama comes from
institutional consequence rather than spectacle.

## Product judgment

Continuity Failure already has the rare part: a coherent civic simulation whose
changes can be explained. Its retention risk is not lack of systems. It is that
the player can complete ten procedurally identical, reading-heavy turn shells
without feeling when a rule became a promise, a promise became precedent, or a
precedent closed a future option.

The next milestone should therefore be experiential:

> By the end of turn 2, a new player can state what they advised, what the client
> actually did, what changed, and which record may return later. By turn 6, the
> workstation and the institutions should have changed the way the player works,
> not merely changed labels. At the dossier, the player should immediately want
> to test one road not taken.

Do not add a second scenario or more AI tools until Northbridge reliably creates
that arc.

## Evidence from the current build

The post-Wave-2 pass verified 485 backend tests, 46 frontend unit tests, and 24
Playwright journeys against the production frontend build and real
FastAPI/SQLite. The automated terminal journey takes **8.3 seconds**; that is a
throughput check, not a human pacing measure. The UI still asks for roughly
seventy mandatory phase advances across a ten-turn run before optional evidence,
Case File, and memo interactions.

There is no human-session telemetry yet. An interaction/content audit puts a
first run at approximately **45–75 minutes** for a player who reads calls,
compares primary advice, opens relevant evidence, edits at least some memos, and
reads the consequence record. A skimming run can finish in 25–35 minutes; a
record-complete run can exceed 90. Treat these as planning estimates, not
observed-player data. Before large layout work, time five first-time sessions and
record phase arrival/exit locally without memo text.

The current mechanical stress pass also changes the experience diagnosis:

- the turn-4 contractor variant is unreachable in ordinary play;
- CRITICAL and its allocation choice are unreachable (minimum power is 28,
  while CRITICAL begins at 14);
- the allocation seam permits MODEL_ACCESS drafting followed by LIVE_DATA
  submission in the same turn;
- three of five completed-campaign verdicts did not appear in 4,212 systematic
  strategies, and several axis bands were not observed;
- later-turn documents appear after feeds go stale while the desk says they were
  last verified at an earlier turn.

Those are not background engineering details. They remove the very reversals
and uncertainty that should carry the middle and end of the session.

## The first 15 minutes

### Minute 0–2: intake

What works: the desk immediately states “You are not the decision-maker,” names
the Northbridge engagement, and frames the record as precedent/evidence/blame.
That is the correct fantasy.

Bounce risk: three opening-condition choices appear before a new player knows
what budget, legal exposure, or power will mean. The selector reads like a
difficulty menu, but the variants are not labeled by difficulty or recommended
experience.

Change: make **Baseline engagement — recommended first case** the dominant
choice. Collapse the two variants under “Alternate intake conditions” until the
player deliberately opens them. After a terminal run, promote the variants with
one concrete difference each (“less fiscal room”; “earlier grid strain”), never
with hidden numeric spoilers.

### Minute 2–5: operating brief and incoming call

What works: the guide accurately explains authority, adherence, thresholds,
drift, evidence qualities, and frozen turn presentation.

Bounce risk: it is a manual before the player has an object to attach the terms
to. It does not teach citations, open-thread deadlines, the debt ledger, or
degradation through action. Players can acknowledge it, then spend the run
without opening the Case File.

Change: shrink the first modal to three promises:

1. You recommend; the client mediates.
2. Every turn changes state and the record.
3. You will be shown exactly why.

Move definitions into contextual, one-time briefs:

- first advice comparison: on-brief, red line, and adherence;
- first attached document: cite/no-cite consequence preview;
- first opened thread: deadline and deterministic escalation;
- first precedent: why the ledger changes future decisions;
- first STRAINED turn: what “last verified” actually withholds.

### Minute 5–10: brief, evidence, and recommendation

The guided loop moves cleanly, but the player can treat Evidence as a ceremonial
phase: open nothing, advance, and still choose among richly described advice.
The citation mechanic is taught only after the player reaches the workbench, and
threads/ledger live in a separate Case File with no first-turn reason to visit.

Change: on turn 1, ask one grounded question above the evidence cards: “Which
record can bear the sentence you are about to put in writing?” Do not require a
citation. Highlight the attached lab report, then show the selected document’s
source/reliability/public-status triad beside the advice preview. The lesson is
epistemic judgment, not a collectible checkbox.

Keep strategic alternatives collapsed on turn 1. Three primary options are
enough for the first real decision; the full alternative set can appear from
turn 2, after the player understands off-brief cost.

### Minute 10–15: memo, client decision, and first consequence

This is the make-or-break sequence. The player has done meaningful work, but the
payoff arrives as several truthful panels: decision rationale, adherence,
waterfall, aftermath stack, reconciliation, canon, threads, and archive. The
record is excellent for audit and weak as a first dramatic beat.

Change: lead the result with one authored/deterministic causal sentence:

> **You advised a controlled notice. The manager narrowed it to hospital and
> school channels; public trust rose, but the unannounced contractor exposure is
> now on the record.**

Build it from the chosen advice, decision type, largest surprising applied delta,
and newly opened thread/precedent. It is presentation derived from authoritative
records, never new canon. Then offer “Show the record” for the existing panels.
One sharp sentence should orient the emotion; the waterfall should prove it.

End turn 1 by pointing to exactly one future hook: “Contractor warning due in 2
turns,” “State inquiry now open,” or “This procurement precedent will lower
future resistance.” Do not summarize every system equally.

## Session shape and the mid-game sag

The current turn cadence is:

`Call → Brief → Evidence → Advice/Memo → Client Decision → Consequences → Archive`

That is a strong first-turn tutorial and a repetitive ten-turn ritual. Turns 4–7
are the likely sag: the player has learned navigation, the evidence list is
longer, aftermath panels are familiar, and Wave 2’s promised structural changes
do not reliably arrive. The contractor branch and CRITICAL choice are dead; the
turn-6 oversight branch appears mainly on a self-destructive state-support line.

Recommended cadence:

- **Turns 1–2 — learn the desk.** Full guided phases and contextual teaching.
- **Turns 3–4 — accumulate obligations.** First unavoidable return of a thread
  or precedent; allow experienced players to combine Brief and Evidence.
- **Turn 5 — operating reversal.** A reachable power decision or equivalent
  institutional constraint changes how the player prepares advice.
- **Turns 6–8 — consequences talk back.** At least one naturally reachable call
  variant quotes the record and changes the primary ask. Favor fewer, sharper
  documents over a monotonically growing library.
- **Turns 9–10 — closeout under discovery.** Make the player choose what record
  they can defend, not merely preserve threshold headroom.

After turn 2, add an optional **Expedited review** path that combines already-read
Call/Brief/Evidence material into one page while preserving the same API package
and decision. Never auto-skip Client Decision or the causal headline. This can
remove 20–30 empty navigation clicks without weakening the ritual.

Target human pacing after iteration: **8–12 minutes for turn 1, 4–6 minutes for
ordinary middle turns, 6–8 minutes for pivotal turns, and 8–12 minutes for the
terminal dossier**—roughly 50–65 minutes for a thoughtful first run.

## Consequence legibility as drama

The current waterfall is honest. Keep it. Reorder its information hierarchy:

1. **Causal headline:** advice → client mediation → one felt consequence.
2. **Future hook:** one thread, precedent, faction reaction, or lost capability
   that will matter later.
3. **Decision receipt:** decision type, adherence, and the client’s operative
   reason.
4. **State reconciliation:** the existing complete audit, collapsed by default
   after the first two turns.
5. **Archive material:** exact memo, all diffs, canon, and secondary panels.

Prefer concrete institutional sentences over abstract meters: “The hospital now
has a priority commitment the schools can discover” is stronger than three
panels separately saying hospital +4, school pressure +2, and precedent opened.
The sentence must link to those three records so the player can challenge it.

Do not animate every changed number. Reserve motion or focus movement for the
single headline consequence and the new future hook; reduced-motion receives an
instant equivalent.

## Replay pull

Two seed variants and two call variants are enough infrastructure, not enough
felt variation. The cheapest convincing second run is:

1. fix both existing call-variant gates and make at least one fire on a competent
   but ethically different line, not only on collapse play;
2. make each seed variant change one early call emphasis, one document’s
   reliability/freshness context, and one late dilemma while retaining the same
   ten-turn skeleton;
3. add an end-screen **Road not taken** comparison for one pivotal turn, clearly
   labeled simulation-not-canon and pinned to the campaign’s ruleset;
4. let the dossier name one unresolved question and offer a one-click restart
   into the relevant variant.

Do not build a second full scenario yet. A thin second-scenario skeleton may be
used privately to test content portability, but public content work should first
make baseline, hot summer, and strained finances produce recognizably different
stories.

## Recommended Wave 3+ ordering

Effort uses **S** (2–5 days), **M** (1–2 weeks), and **L** (3–5 weeks), including
tests, content, accessibility, and documentation.

| Rank | Work | Effort / dependency | Player and retention value |
| --- | --- | --- | --- |
| 0 | **Wave-2 integrity patch:** reachable contractor/CRITICAL paths; bind one allocation window; truthful stale evidence; preserve call/allocation facts in dossier; align validators; tune ending reachability | M; before all new features | Restores trust. Players can finally encounter the features Wave 2 advertises, and the power choice becomes real rather than bypassable. |
| 1 | **Causal headline + future hook** | S; uses existing `TurnResult`, threads, ledger | Highest value per effort. Converts audit data into a memorable beat without changing canon. |
| 2 | **Progressive first engagement** | M; contextual help plus turn-1 content pass | Lowers first-15-minute bounce and teaches the distinctive mechanics by use. |
| 3 | **Local comprehension telemetry (3b/HO#10)** | S–M; define privacy-safe events first | Replaces pacing guesses with phase time, evidence use, comparison, expansion, and abandonment data. Never log memo text. |
| 4 | **Record as playable object (4a/HO#1)** | L; needs integrity patch and clear archive UX | Deepens the core fantasy: what is written, cited, sealed, or omitted becomes a choice with later institutional consequences. Strongest long-term identity. |
| 5 | **Counterfactual dossier (4b/HO#3)** | L; needs ruleset execution policy, not just stamping | Strongest direct replay prompt. Shows one road not taken while protecting canon/simulation boundaries. |
| 6 | **Consultant ethics profile (4c/HO#4)** | M; needs reachable/tuned outcome bands | Gives the run a personal residue and a language for comparing play styles. Feed future dispositions only through deterministic rules. |
| 7 | **Evidence contradiction graph (4d/HO#5)** | L; authored edge vocabulary and citation UI | Makes evidence reasoning distinctive. Defer until it changes decisions, not merely visualization. |
| 8 | **Deadline budget (4e/HO#6)** | M; depends on telemetry and contradiction value | Adds pressure and replay variation, but can worsen reading fatigue if introduced before the evidence loop is compelling. |
| 9 | **Identity/security (3a/ME#5)** | M–L; schedule only for shared deployment | Necessary for launch safety, neutral for local-player retention. Do when the deployment decision is real. |
| 10 | **Additional AI tools (Wave 5/ME#7)** | L per useful tool; needs 4d/4e and honest degradation costs | Valuable only when research/classification creates a constrained choice. More prose without cost or provenance will worsen the session. |

## Acceptance signals

Before calling the experience compelling, observe these in playtests:

- 80% of first-time players can explain advice vs. client action vs. applied
  change after turn 2 without opening help.
- Most players cite or deliberately decline evidence for a stated reason by
  turn 2; checkbox use alone is not success.
- At least one thread/precedent is recalled before the UI reminds the player.
- No abandonment spike occurs in turns 4–7.
- Every authored call variant, completed-campaign verdict, and intended outcome
  band has a documented reachable sequence; no test-only narrative remains.
- A complete first run centers near 50–65 minutes, with experienced runs under
  40 minutes through expedited review.
- At least half of terminal playtesters choose a variant or road-not-taken action
  for an immediate second run.

The aim is not to make the desk faster at all costs. It is to make every minute
feel like the player is leaving a record inside an institution that will remember
what they did.
