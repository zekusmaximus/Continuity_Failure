# Continuity Failure

**Continuity Failure** is a near-future civic breakdown simulator where the player runs a crisis-governance consulting firm called into failing institutions as society loses capacity faster than its legal, political, and infrastructure systems can adapt.

The player does not directly govern. The player advises mayors, town managers, agency heads, hospital counsel, utility executives, regional compacts, and state officials through memos, emergency orders, public statements, negotiation plans, triage frameworks, legal risk assessments, and scenario forecasts.

NPC clients may follow, distort, leak, ignore, or weaponize the player’s advice. The deterministic simulation engine resolves consequences. AI systems generate institutional artifacts, research support, faction reactions, media distortion, legal/policy analysis, and canon summaries — but the model is never the source of truth for game state.

The campaign begins at the town level and expands outward as the player is called into larger failures: municipal crises, regional coordination breakdowns, state emergency governance, and eventually interstate compact formation.

## Core Design Pillars

1. **The database is canon. The model is not.**
   LLMs may propose, narrate, summarize, draft, and analyze. They may not directly mutate authoritative game state.

2. **The player advises. NPCs decide.**
   The player’s power is indirect. Clients may accept, modify, reject, leak, or misuse advice.

3. **Collapse is institutional, not cinematic.**
   The game is about brittle systems, failing procedures, legal ambiguity, public trust, infrastructure scarcity, bad data, procurement pressure, jurisdictional conflict, and moral triage.

4. **Every decision creates a record.**
   Memos, public statements, emergency orders, emails, legal analyses, and AI-generated drafts can become canon, evidence, political liabilities, or future precedent.

5. **AI is part of the world.**
   The player can use local models, cloud frontier models, archive systems, rumor classifiers, legal retrieval tools, and scenario simulators. These systems consume power, bandwidth, money, time, privacy, and institutional legitimacy.

## MVP Scenario

The first playable scenario is **Northbridge Water Failure**.

Northbridge is a mid-sized Connecticut town facing a cascading water-system crisis caused by heat stress, deferred maintenance, contractor dependency, budget exhaustion, ambiguous lab reports, public rumor, school pressure, hospital vulnerability, and delayed state support.

The player is hired by the Northbridge town manager for a 30-day emergency stabilization engagement.

The MVP campaign covers 10 turns. Each turn represents approximately 3 days.

## MVP Success Criteria

The MVP is successful if:

* A player can complete a 10-turn Northbridge campaign.
* The deterministic engine resolves all state changes through explicit rules.
* Every turn produces a replayable log.
* The player can issue advice through at least one memo-style artifact.
* NPCs can react differently based on faction incentives and prior canon.
* The game remembers prior promises, laws, scandals, and unresolved risks.
* AI tools assist with research, drafting, summarization, and scenario analysis without becoming the source of truth.
* The final campaign dossier is exportable as a coherent institutional-collapse case file.

## Initial Gameplay Loop

1. Client call arrives.
2. Player reviews the situation brief.
3. Player inspects documents, factions, risks, authority, and prior commitments.
4. Player uses optional AI tools for research, drafting, document review, or scenario planning.
5. Player issues advice.
6. NPC client accepts, modifies, ignores, leaks, or weaponizes the advice.
7. Deterministic engine applies consequences.
8. Press, factions, lawyers, agencies, and public actors react.
9. Canon archive updates.
10. Reputation and future engagements shift.

## Initial Tech Direction

The intended architecture is:

```text
React UI
  ↓
FastAPI orchestration layer
  ↓
Deterministic simulation engine
  ↓
SQLite/Postgres canon store
  ↓
Model provider abstraction
  ↓
Structured AI role calls
```

The frontend should feel like an in-world crisis-consulting workstation: a degraded civic operations dashboard, legal workbench, emergency management console, document review system, and AI research terminal.

## Repository Status

This repository is at project inception. The first milestone is to build a deterministic Northbridge town-crisis simulator before adding any model-driven turn generation.
