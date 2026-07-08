# docs/mvp-roadmap.md

# MVP Roadmap

## Objective

Build a playable 10-turn deterministic version of **Northbridge Water Failure** before adding complex AI orchestration.

The first MVP should prove the core loop:

> client call → situation brief → player advice → NPC decision → deterministic consequences → aftermath → canon update.

## MVP Definition

The MVP is complete when a user can:

* start the Northbridge scenario;
* receive a client call each turn;
* review the current crisis state;
* choose or draft advice;
* see how the NPC client uses the advice;
* see deterministic consequences;
* inspect state diffs;
* review faction/media reactions;
* complete or fail a 10-turn campaign;
* export a basic campaign dossier.

## Week 1: Deterministic Simulation Skeleton

### Goal

Create the basic playable engine without AI.

### Tasks

1. Set up repository structure.
2. Create backend project.
3. Create frontend project.
4. Define core Pydantic schemas.
5. Implement initial Northbridge seed data.
6. Implement `WorldState`.
7. Implement `Faction`.
8. Implement `ClientCall`.
9. Implement `Advice`.
10. Implement `NpcDecision`.
11. Implement `AppliedDiff`.
12. Implement deterministic `advance_turn()`.
13. Implement basic advice options.
14. Implement deterministic consequence rules.
15. Implement state invariant checks.
16. Implement turn logging.
17. Expose backend endpoints:

    * create campaign;
    * get campaign;
    * get current turn;
    * submit advice;
    * advance turn;
    * get turn history.
18. Build minimal UI:

    * dashboard;
    * current call;
    * state variables;
    * advice choices;
    * aftermath;
    * turn history.

### Week 1 Deliverable

A user can run through a crude but complete 10-turn campaign with no AI.

## Week 2: Advice Workbench and Case File

### Goal

Make the deterministic game feel like crisis consulting.

### Tasks

1. Build case file screen.
2. Add document entities.
3. Add initial documents:

   * preliminary lab report;
   * town manager call transcript;
   * council meeting excerpt;
   * contractor warning letter;
   * hospital water-priority request;
   * resident rumor thread.
4. Add advice workbench.
5. Add memo-style advice form.
6. Add structured advice templates.
7. Add NPC decision logic based on faction incentives.
8. Add consequence stack UI.
9. Add faction reaction summaries.
10. Add media reaction summaries.
11. Add basic canon entries.
12. Add campaign archive screen.
13. Add export-to-markdown dossier.

### Week 2 Deliverable

A user can play the Northbridge scenario as a consultant issuing advice, not merely selecting strategy-game buttons.

## Week 3: AI-Assisted Artifacts

### Goal

Add AI support without letting AI control state.

### Tasks

1. Create model provider abstraction.
2. Add prompt versioning.
3. Add model run logging.
4. Add structured output validation.
5. Add AI tool definitions:

   * document summarizer;
   * advice option generator;
   * memo drafter;
   * faction reaction writer;
   * press desk;
   * historian.
6. Add AI Research Console UI.
7. Add in-world AI tool costs:

   * power;
   * bandwidth;
   * privacy exposure;
   * latency;
   * confidence.
8. Add local/cloud model distinction in the UI, even if both initially call the same backend provider.
9. Add fallback behavior when model output fails.
10. Add AI-generated draft memo that the player can accept/edit.
11. Add AI-generated press/faction aftermath text.
12. Ensure deterministic engine still owns all state changes.

### Week 3 Deliverable

AI can help draft, summarize, and narrate, but the game remains deterministic and replayable.

## Week 4: Polish, Evaluation, and Demo Loop

### Goal

Make the Northbridge MVP demo-ready.

### Tasks

1. Improve visual design of the crisis workstation.
2. Add last-verified timestamps.
3. Add fact status labels:

   * canon;
   * proposed;
   * rumor;
   * unverified;
   * contradicted.
4. Add basic power/model status panel.
5. Add low-power/degraded-system UI state.
6. Add replay screen.
7. Add evaluation checks:

   * state validity;
   * continuity;
   * faction consistency;
   * memory use;
   * repetition;
   * world drift.
8. Add seeded campaign test.
9. Add README run instructions.
10. Add demo script.
11. Add final after-action report.
12. Add transition hook:

* after Northbridge, a state agency or neighboring town calls.

### Week 4 Deliverable

A demo-ready 10-turn Northbridge campaign with deterministic replay, AI-assisted artifacts, and exportable dossier.

## Explicitly Out of Scope for MVP

Do not build these before the Northbridge MVP works:

* autonomous multi-agent society simulation;
* statewide campaign;
* interstate compact gameplay;
* user accounts;
* multiplayer;
* complex vector database;
* real-time map simulation;
* animated NPC portraits;
* full legal research engine;
* procedural scenario generator;
* deployment optimization;
* mobile layout;
* save-slot management beyond basic persistence.

## First Playable Milestone

The first playable milestone is intentionally modest:

> Start campaign. Read call. Choose advice. Advance turn. See consequences. Repeat for 10 turns.

Everything else exists to make that loop richer.

## MVP Quality Bar

The MVP should feel:

* procedural;
* civic;
* tense;
* document-rich;
* legally aware;
* morally uncomfortable;
* systemically legible.

It should not feel:

* random;
* generic;
* apocalyptic for spectacle;
* like a chatbot;
* like a shallow resource clicker;
* like a dashboard with no game.
