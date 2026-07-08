# prompts/README.md

# Prompts

## Purpose

This directory contains versioned prompts for AI-assisted gameplay systems in **Continuity Failure**.

Prompts are part of the codebase. They should be reviewed, versioned, tested, and logged.

Do not scatter inline prompts throughout backend code.

## Core Rule

AI output is not authoritative game state.

AI may:

* summarize;
* draft;
* classify;
* forecast;
* narrate;
* critique;
* propose.

AI may not directly mutate canon or world state.

## Prompt Naming

Use this pattern:

```text
task_name.vN.md
```

Examples:

```text
crisis_brief.v1.md
advice_options.v1.md
memo_drafter.v1.md
faction_reactions.v1.md
press_desk.v1.md
historian.v1.md
continuity_critic.v1.md
```

When a prompt’s expected behavior changes materially, create a new version.

Do not silently overwrite prompt behavior without updating the version.

## Initial Prompt Roles

### crisis_brief

Produces a concise situation brief from current state, client call, documents, and canon.

Must distinguish:

* known facts;
* unknown facts;
* rumors;
* contradicted reports;
* immediate risks.

### advice_options

Produces possible advice paths for the player.

Must provide tradeoffs.

Must not present one option as risk-free.

### memo_drafter

Drafts a consultant memo based on selected advice.

Must include:

* recommendation;
* rationale;
* legal/authority considerations;
* operational steps;
* communications strategy;
* likely opposition;
* second-order risks;
* fallback plan.

### faction_reactions

Produces narrative reactions from factions after deterministic consequences are known.

Must not invent state changes.

Must cite supplied faction incentives and prior canon where relevant.

### press_desk

Produces media headlines, rumor framing, and public narrative after a turn.

Must distinguish confirmed news from rumor.

### historian

Creates proposed canon entries after a turn.

Must classify each entry as confirmed, disputed, rumored, private, leaked, or unresolved.

### continuity_critic

Flags contradictions, drift, repetition, or invented facts.

Must identify whether a problem comes from model output, player advice, seed data, or deterministic state.

## Prompt Input Contract

Each prompt should receive a structured input object.

Typical input fields:

```text
campaign_id
turn_number
current_world_state
active_crisis
client_call
factions
documents
prior_canon
player_advice
npc_decision
applied_diffs
model_tool_context
```

Only include fields the prompt needs.

Avoid dumping entire campaign history when targeted canon retrieval will suffice.

## Prompt Output Contract

Every production prompt should return structured output.

Each prompt must define:

* required fields;
* optional fields;
* allowed enum values;
* maximum item counts where appropriate;
* whether freeform prose is allowed;
* whether citations to supplied IDs are required.

## Validation

Every model response should be validated before use.

If validation fails:

1. Retry once with a corrective message if appropriate.
2. If retry fails, use deterministic fallback.
3. Log the failure.

## Tone Requirements

Outputs should be:

* serious;
* procedural;
* civic;
* grounded;
* legally and politically aware;
* specific to supplied facts;
* free of generic apocalypse clichés.

Avoid:

* melodrama;
* cyberpunk slang;
* military-thriller bombast;
* invented lore;
* unsupported certainty;
* fake statutes unless the scenario explicitly contains fictional law;
* direct state mutation.

## Canon Discipline

Generated facts must be classified.

Allowed fact statuses:

```text
CANON
PROPOSED
RUMOR
UNVERIFIED
CONTRADICTED
REJECTED
```

A model may propose canon entries, but backend workflow decides whether to accept them.

## Logging

Every prompt call must log:

```text
prompt_name
prompt_version
model_name
input_summary
raw_output
parsed_output
validation_status
retry_count
latency_ms
token_usage
estimated_cost
```

## Initial Development Approach

For the first AI milestone, implement prompts in this order:

1. `memo_drafter.v1.md`
2. `faction_reactions.v1.md`
3. `press_desk.v1.md`
4. `historian.v1.md`
5. `continuity_critic.v1.md`
6. `crisis_brief.v1.md`
7. `advice_options.v1.md`

The deterministic game loop should work before any of these prompts are required.
