# Fable 5 — Full Project Review Prompt

> A ready-to-use prompt for asking the **Fable 5** model (`claude-fable-5`) for
> an in-depth review and critique of **Continuity Failure**, with prioritized,
> actionable suggestions for improvement.
>
> **How to use it.** Give Fable 5 access to the repository (paste the tree and
> the files it asks for, attach the repo, or point a code-aware harness at it),
> then paste everything in the `---` fenced block below as your prompt. If you
> can only provide a subset of files, lead with `README.md`, `AGENTS.md`, the
> `engine/` package, `backend/app/ai/`, and the `tests/` directory — those carry
> the design contract the review hinges on.

---

You are a principal-level reviewer conducting a rigorous, in-depth technical and
design review of a software project. You have deep expertise across systems
architecture, Python/FastAPI backends, React/TypeScript frontends, game and
simulation design, and the safe engineering of LLM-assisted features. Your job
is to find what is genuinely wrong, weak, or risky — not to reassure. Assume a
skeptical senior audience who will act on what you write.

## The project under review

**Continuity Failure** is a near-future civic-breakdown simulator. The player
runs a crisis-governance consulting firm and advises failing institutions
(mayors, agency heads, hospital counsel, utility executives) through memos and
recommendations. The player *advises*; NPC clients *decide* (follow, modify,
delay, reject, leak, or weaponize the advice); a deterministic engine resolves
all consequences. LLMs may draft, summarize, classify, and propose, but are
**never** the source of truth for game state.

The current build is a playable 10-turn "Northbridge Water Failure" MVP, plus a
dormant, validation-gated AI-assist layer (a memo drafter) that is off by
default.

### Architecture

```
React + TypeScript + Vite frontend  (guided "Continuity Desk" intake flow)
        ↓  /api
FastAPI backend  (Pydantic at the boundary; in-memory persistence)
        ↓
Deterministic simulation engine  (framework-free; no web/Pydantic imports)
        ↓
Model provider abstraction  (backend/app/ai/ — dormant, validation-gated)
```

Layout: `engine/` (deterministic core), `backend/app/` (API + `ai/` layer),
`frontend/src/` (React components), `tests/` (pytest), `prompts/` (versioned
prompts), `docs/` (design docs), `memory/` (in-memory store), `evals/`
(reserved).

### Non-negotiable design invariants (the review must check these hold)

1. **The database is canon; the model is not.** All state changes route through
   deterministic engine functions; LLM output may only propose.
2. **The player advises; NPCs decide.** Advice is mediated by NPC decisions
   before any effect is applied.
3. **Every state change is explainable** — each mutation emits an `AppliedDiff`
   (variable, old/new value, delta, reason, source) tied to a turn/rule/event.
4. **Every generated fact is classified** (canon / proposed / rumor / unverified
   / contradicted / rejected).
5. **The engine is framework-independent** — `engine/*.py` imports only stdlib
   and itself; the backend maps to Pydantic only at the API boundary.
6. **A campaign can complete or fail and never advances past a terminal state.**

These are asserted by tests in `tests/`. Treat any way to violate them —
including subtle or indirect paths — as a high-severity finding.

## What to review

Cover every dimension below. For each, state what is strong, what is weak, and
what you would change.

1. **Architecture & boundaries.** Is the deterministic-core / AI-assist /
   API / UI separation actually enforced, or only enforced by convention and a
   couple of AST tests? Where could the canon-vs-model boundary erode as the
   codebase grows? Assess the in-memory persistence choice and the migration
   path to durable storage.
2. **Design-invariant integrity.** Audit each of the six invariants for real or
   latent violations, gaps in test coverage, and escape hatches. Be adversarial:
   how would you break the "model is never canon" guarantee?
3. **Engine correctness & simulation design.** Rule resolution, NPC decision
   mediation, advice scaling, consequence stacking, failure thresholds, clamping,
   and diff generation. Look for edge cases, ordering bugs, unreachable content,
   degenerate strategies, and balance problems that undermine replayability.
4. **AI-assist layer.** The validation → retry-once → deterministic-fallback
   boundary, schema design, `ModelRun` logging, provider abstraction, and prompt
   versioning. Is the fallback genuinely safe? Is anything about the boundary
   fragile, under-tested, or easy to misuse when the remaining tools are added?
5. **Backend/API quality.** Endpoint design, Pydantic schema mapping, service
   layer, error handling, validation, and statefulness/concurrency concerns.
6. **Frontend quality & UX.** Component structure, state management, the
   guided-intake flow, the Case File drawer, accessibility, and how well the
   "diegetic crisis workstation" intent (including planned graceful degradation)
   is realized.
7. **Testing.** Coverage relative to the invariants and game loop, test quality
   (are they meaningful or brittle/tautological?), and the most valuable missing
   tests. Note anything asserted in docs but not actually tested.
8. **Content & game design.** Scenario coherence, faction incentives, evidence
   documents, tone discipline (procedural/civic vs. apocalypse cliché), and
   whether the moral/institutional fantasy lands.
9. **Docs & maintainability.** Do `README.md`, `AGENTS.md`, and `docs/` match
   the code? Naming, dead code, TODOs, and onboarding friction.
10. **Roadmap & scaling risk.** Evaluate the stated next steps (more read-only
    AI tools, in-world tool costs, then durable persistence). What is the
    riskiest assumption, and what ordering would you actually recommend?

## How to work

- **Verify before asserting.** Cite specific files, symbols, and (where
  possible) line numbers. If you infer behavior without having read the relevant
  file, say so and mark your confidence. Do not invent APIs or content.
- **Prioritize ruthlessly.** Distinguish correctness/security/invariant risks
  from quality and style. A short list of real problems beats a long list of
  nitpicks.
- **Be concrete.** Every criticism must come with a specific, actionable
  recommendation — ideally a sketch of the fix, the test to add, or the
  refactor to make.
- **No rubber-stamping and no false alarms.** If something is genuinely good,
  say briefly why. If you are unsure a finding is real, label it as a hypothesis
  to check rather than a confirmed defect.

## Output format

1. **Executive summary** — 5–10 sentences: overall health, the single biggest
   strength, and the top 3 risks.
2. **Findings by severity** — grouped **Critical / High / Medium / Low**. For
   each finding: a one-line title, the location (file/symbol), why it matters,
   the concrete failure it enables, and the recommended fix.
3. **Dimension-by-dimension notes** — brief assessment of each of the ten review
   areas above.
4. **Prioritized improvement plan** — a numbered, sequenced list of the highest-
   leverage changes, each tagged with rough effort (S/M/L) and the risk it
   retires.
5. **Open questions** — anything you could not determine from the provided code
   and would need to confirm.

Be direct, specific, and technical. Optimize for what a maintainer can act on
tomorrow.

---
