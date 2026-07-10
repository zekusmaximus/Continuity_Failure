# Evals

This directory is reserved for deterministic-engine and (later) model-output
evaluation harnesses.

## Current status

The first AI-assist tool (memo drafting) is implemented behind structured
validation, deterministic fallback, and `ModelRun` logging, but a dedicated
model-output evaluation harness is not implemented yet. The deterministic
engine and AI boundary are covered by tests in `tests/` that serve as the first
evaluation layer:

* State values are always clamped to `0..100`.
* Every turn produces explainable `AppliedDiff` records.
* Failure thresholds and 10-turn completion are verified.
* Identical advice sequences produce bit-for-bit identical runs (determinism).

## Planned evaluations

Per `AGENTS.md`, model output must be **validated before use** and never
directly mutates world state. As the research console, scenario simulator,
rumor classifier, and additional artifact roles are added, this directory will
hold:

* **Schema-conformance checks** — every model response parsed and validated
  against a Pydantic schema before acceptance.
* **Fact-classification accuracy** — proposed / rejected / canon / rumor /
  unverified / contradicted labels scored against hand-labeled fixtures.
* **Hallucination / leakage probes** — does a tool invent canon or leak data
  that should be offline under degraded power/bandwidth conditions?
* **Determinism regression** — ensure AI suggestions never change authoritative
  state; only the engine produces `AppliedDiff` records.

Model call logging (prompt version, input, output, validation result, retries,
latency, and token use) is already captured by the orchestration layer. Future
evaluation harnesses will consume those records and add cost and quality
scoring.
