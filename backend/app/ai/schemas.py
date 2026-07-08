"""Output contracts for AI-assisted artifacts.

Each artifact role has a Pydantic schema that the runner validates model output
against. Validation failure triggers a retry and then a deterministic fallback,
so these schemas are the enforcement point for "the model may draft, but only in
the shape we accept."
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel


class MemoDraft(BaseModel):
    """A consultant memo drafted from a selected advice option.

    Mirrors the ``memo_drafter`` output contract in ``prompts/README.md``. This
    is advisory prose only — it proposes nothing to canon and mutates no state.
    """

    recommendation: str
    rationale: str
    operational_steps: List[str]
    communications: str
    likely_opposition: List[str]
    second_order_risks: List[str]
    fallback_plan: str
