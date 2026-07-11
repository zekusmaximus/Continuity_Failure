# Scenario Content Authoring

Northbridge scenario content is data, not code. It lives as versioned JSON under
`engine/content/scenarios/<scenario_id>/` and is loaded through one factory:

```python
from engine.content import load_campaign
campaign = load_campaign("northbridge_water_failure")
```

The deterministic engine rules (`engine/rules.py`, `engine/turn.py`) decide
outcomes; content only describes the inputs those rules act on. This split keeps
balance/tuning reviewable and lets a typo fail *before* a campaign starts instead
of silently changing or omitting gameplay.

## File layout

One coherent file per authored domain:

| File                   | Contents                                                        |
| ---------------------- | -------------------------------------------------------------- |
| `scenario.json`        | `schema_version`, `scenario_id`, `name`, `max_turns`, `starting_variables`, `crisis`, optional `ambient_windows` (authored ambient episodes over a turn span) |
| `factions.json`        | list of factions                                               |
| `advice.json`          | the global advice options (available every turn)               |
| `per_turn_advice.json` | `{ "<turn>": [advice, ...] }` options that only fit that call  |
| `calls.json`           | one client call per turn (`1..max_turns`), any order; a call may carry `variants` (branchable/faction-gated openings) |
| `documents.json`       | evidence-board documents; `turn_number` is the freshness/available-from turn |
| `threads.json`         | open threads seeded at engagement start                        |
| `thread_specs.json`    | dynamic-thread rules: when the engine opens a consequence thread mid-game, and the schedule it carries |
| `variants.json`        | seed variants: authored starting-state perturbations selectable at campaign creation |

Field names match the engine dataclasses in `engine/models.py`. Any field that
equals its dataclass default may be omitted; required fields (those without a
default) must be present.

## Validator command

Run the validator standalone — use it locally and in CI/pre-commit:

```bash
python -m engine.content validate                       # all shipped scenarios
python -m engine.content validate northbridge_water_failure
```

It exits non-zero and prints every problem anchored to `file:path`, e.g.:

```
FAIL  northbridge_water_failure: 2 error(s)
        advice.json:[0].effects.public_trst: unknown WorldState variable 'public_trst' in effect map
        calls.json:[4].caller_faction_id: references unknown faction 'ministry_of_typos'
```

The same validation runs automatically inside `load_campaign` (and therefore in
`seed_data.create_northbridge_campaign`), and is exercised by
`tests/test_content_validation.py`.

## What is validated

Before a campaign is seeded, the validator checks (collecting *all* failures in
one pass):

- **Unique ids** across factions, advice (global + per-turn share one namespace),
  calls, documents, and threads.
- **API-requestable ids** — advice ids, document ids, and seed-variant ids ride
  on HTTP requests (submissions, citations, campaign creation), so they must
  match the API's identifier shape: lowercase letters, digits, underscores,
  max 64 chars (`engine/content/schema.py::API_IDENTIFIER_PATTERN`). An id
  like `hot-summer` would validate as content yet be unrequestable — that is
  now an authoring error.
- **Known cross-references** — call `caller_faction_id`, call
  `attached_document_ids`, call `crisis_id`, and advice `affected_factions`.
- **Required fields** present; **unknown fields rejected** (a typo'd key that
  would drop an effect is an error, not a silent no-op).
- **Enums** — faction `type`/`alignment`, advice `type`, call `urgency`/
  `public_exposure`, document `type`/`public_status`/`reliability`, crisis `type`.
- **Integer ranges** — 0–100 for `starting_variables`, faction
  influence/trust/risk/pressure, advice risk fields, and crisis severity;
  effect deltas within ±100.
- **Known WorldState variables** — `starting_variables` must be exactly the
  engine's 16-variable set; every effect-map key must be a known variable.
- **Effect maps** — keys are known variables, values are bounded integers.
- **Turn ordering / coverage** — exactly one call per turn `1..max_turns`;
  per-turn advice keys and document/thread turns are in range.
- **Advice routing** — every advice option carries at least one decision tag the
  rules recognize (`engine/rules.py::_ADVICE_TAG_DISPATCH`), so it can't fall
  through to the generic handler.
- **Call-specific advice space** — each call declares
  `primary_advice_ids` (3–5 on-brief options), each of which must be an advice id
  available on that turn (global ∪ that turn's per-turn options) and must **not**
  carry one of the call's `red_line_tags`. Each call also declares a
  `decision_profile` (`mandate`, `priorities` = known WorldState variables,
  `red_line_tags` = recognized decision tags, `off_brief_tolerance` 0–100). The
  caller's faction risk tolerance / pressure plus this profile feed the
  deterministic NPC decision; any option *not* in `primary_advice_ids` resolves
  off-brief (lower adherence + a recorded standing cost), and a red-line tag is
  rejected outright. See `engine/rules.py::_modulate`.
- **operational_steps / expected_benefits / expected_harms** — non-empty lists of
  non-empty strings (no free-lunch advice, and a defensible step list).
- **Faction advice trust costs** — a faction may declare `advice_trust_costs`:
  a list of `{advice_tag, delta, reason}` reactions applied to its
  `trust_in_player` when advice carrying that tag is actually acted on
  (FOLLOWED / PARTIALLY_FOLLOWED / MODIFIED) while **someone else** is on the
  line (the caller's seat keeps its own trust rules). `advice_tag` must be a
  recognized decision tag, `delta` is a bounded nudge (±20, non-zero), and
  `reason` is required — it becomes the recorded `FactionShift` reason. This
  is how a faction targeted by a strategy reacts off-call (e.g. the contractor
  squeezed three turns running stops negotiating through the consultant,
  which is what arms the turn-4 ultimatum call variant).
- **Document tags** — non-empty; **freshness** (`turn_number`) in range.
- **Threshold coverage** — every variable the failure thresholds and ambient
  drift reference has a starting value.
- **Ambient windows** — each `scenario.json` `ambient_windows` entry needs
  `id` (unique), `from_turn <= to_turn` within `1..max_turns`, a non-empty
  `effects` map of known variables with bounded deltas, and a non-empty
  `reason` (it becomes the AppliedDiff reason, so the causal waterfall names
  the episode). Effects apply as their own `ambient` diff batch on every turn
  in the span.
- **Seed variants** — each `variants.json` entry needs `id`, `name`,
  `description`, and a non-empty `variable_overrides` map of known WorldState
  variables within 0–100; ids are unique; no other fields. A variant is a
  deterministic perturbation of `starting_variables` selected by id at
  campaign creation (`POST /api/campaigns` `{"variant": "hot_summer"}`); the
  campaign persists `variant_id` so exact replay is scenario + variant +
  advice sequence. Balance obligation: before shipping a variant, run
  `python tests/support/balance_trace.py <variant_id>` — some documented
  advice sequence must complete it, and both spam strategies must still fail
  (see `tests/test_seed_variants.py`, which pins both facts per variant).
- **Call variants** — a call's `variants` list holds authored alternate
  openings: `{id, conditions, call}`. Each variant `call` is a complete call
  body validated by every base-call rule (same `turn` as its slot, `id` equal
  to the variant id, 3–5 valid `primary_advice_ids`, a `decision_profile`, no
  nested `variants`); `conditions` must be non-empty (an unconditioned variant
  would always shadow the base call) and use the `ThreadCondition` shape —
  world-scoped by default, or faction-scoped with `faction_id` set, where
  `variable` must be one of `trust_in_player` / `influence` /
  `current_pressure` / `risk_tolerance`. Call and variant ids share one
  namespace. Selection is deterministic: first variant in authored order whose
  conditions ALL hold, evaluated once per turn before the decision seam
  (`engine/calls.py`); the resolved turn records `call_variant_id`.
- **Thread specs** — every spec has a non-empty opening trigger (at least one
  of `open_conditions_all`, `open_conditions_any`, `open_advice_tags`,
  `open_decision_types`); conditions reference known variables with `<=`/`>=`
  ops and 0–100 thresholds; `open_advice_tags`/`resolve_tags` are recognized
  decision tags; `open_decision_types` are known decision types; `due_in >= 1`;
  `repeat_every >= 0`; `escalation_effects` require an `escalation_note`; a
  spec that carries `escalation_effects` (or a `repeat_every` cadence) must
  also carry `due_in` — without a first deadline the thread would open with
  `due_turn = None` and the schedule would never fire; spec
  ids are unique and must not collide with seeded `threads.json` ids (a spec
  never re-opens an id already on the record). Trigger semantics: all
  `open_conditions_all` AND (any `open_conditions_any`, when present) AND — when
  either tag/type list is present — the advice's primary tag is in
  `open_advice_tags` OR the decision type is in `open_decision_types`. See the
  `ThreadSpec` dataclass in `engine/models.py`.

## Schema version and migrations

`scenario.json` declares `schema_version` (currently `1`).

- The loader reads `SUPPORTED_SCHEMA_VERSIONS` (see `engine/content/schema.py`).
- To evolve the shape, bump `CURRENT_SCHEMA_VERSION` and register a forward
  migration `N -> N+1` in `MIGRATIONS` (`engine/content/loader.py`). Migrations
  are applied in order until the bundle reaches a supported version.
- Content declaring an unsupported version with no migration path raises
  `IncompatibleSchemaVersion` with an actionable message.

## How to add or change content safely

1. Edit the relevant JSON file(s) under the scenario directory.
2. Run `python -m engine.content validate` and fix every reported error.
3. Run `pytest -q` — `tests/test_content_validation.py` re-validates the shipped
   content, and the engine/determinism tests confirm outcomes are unchanged.
4. If you add a **new advice tag**, also add its decision resolver in
   `engine/rules.py` (`_ADVICE_TAG_DISPATCH`) and its immediate-consequence pool
   in `engine/consequences.py`; the validator will reject an option whose tags
   the rules don't recognize.
5. If you add a **new WorldState variable**, add it to
   `engine/state.py::STATE_VARIABLE_LABELS` (the canonical known-variable set)
   and give it a `starting_variables` value.

## Boundaries

- Content stays JSON parsed by the standard library — do not add YAML, a runtime
  parser dependency, Pydantic in `engine/`, or a database-backed CMS.
- Keep content to the Northbridge town-level scenario for now.
- Content proposes inputs; only the deterministic engine promotes anything to
  canon (see `AGENTS.md` § Design Invariants).
