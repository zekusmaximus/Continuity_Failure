# Evals

This directory is reserved for deterministic-engine and (later) model-output
evaluation harnesses.

## Current status

No AI integration exists yet, so there are no model-output evaluations. The
deterministic engine is, however, fully covered by property-style tests in
`tests/` that serve as the first evaluation layer:

* State values are always clamped to `0..100`.
* Every turn produces explainable `AppliedDiff` records.
* Failure thresholds and 10-turn completion are verified.
* Identical advice sequences produce bit-for-bit identical runs (determinism).

## Planned evaluations (post-MVP, once AI systems are introduced)

Per `AGENTS.md`, model output must be **validated before use** and never
directly mutates world state. When AI tools (research console, memo drafter,
scenario simulator, rumor classifier) are added, this directory will hold:

* **Schema-conformance checks** — every model response parsed and validated
  against a Pydantic schema before acceptance.
* **Fact-classification accuracy** — proposed / rejected / canon / rumor /
  unverified / contradicted labels scored against hand-labeled fixtures.
* **Hallucination / leakage probes** — does a tool invent canon or leak data
  that should be offline under degraded power/bandwidth conditions?
* **Determinism regression** — ensure AI suggestions never change authoritative
  state; only the engine produces `AppliedDiff` records.

Model call logging (prompt version, input, output, validation result, retries,
latency, token use, cost estimate) will be captured by the orchestration layer
and consumed by the harnesses here.
