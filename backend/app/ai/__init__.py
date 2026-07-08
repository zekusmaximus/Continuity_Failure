"""AI-assist layer for Continuity Failure.

This package is the **only** place model calls may live, and it is deliberately
powerless over game state:

* It imports no state-mutation code (``engine.diffs`` / ``engine.turn``); the
  deterministic engine remains the sole authority over ``WorldState``.
* It is inert by default. With AI disabled (the default), every entry point
  degrades to deterministic fallback output and makes no network call.
* Everything it produces is advisory — proposed drafts, never canon.

See ``prompts/README.md`` for the prompt/validation/logging discipline this
layer implements, and ``AGENTS.md`` § "Design Invariants" for the boundary it
must never cross.
"""
