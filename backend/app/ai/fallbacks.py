"""Deterministic fallbacks.

Every AI role has a deterministic builder that produces a valid artifact from the
same structured input the model would have received. This is what guarantees the
game keeps working with AI disabled, or when a model call fails validation — the
fallback is not an error message, it is a usable (if plainer) artifact assembled
from the deterministic advice record.

These builders take plain dicts and import no engine code, keeping the AI layer
powerless over game state.
"""

from __future__ import annotations

from app.ai.schemas import MemoDraft


def build_memo_input(option, call) -> dict:
    """Flatten a selected advice option (+ current call) into a prompt payload.

    Duck-typed on purpose: reads attributes off the engine's advice/call objects
    without importing them, so this module stays free of engine dependencies.
    """
    return {
        "advice_title": getattr(option, "title", "") or getattr(option, "label", ""),
        "recommendation": getattr(option, "recommendation", "") or getattr(option, "summary", ""),
        "rationale": getattr(option, "rationale", ""),
        "expected_benefits": list(getattr(option, "expected_benefits", []) or []),
        "expected_harms": list(getattr(option, "expected_harms", []) or []),
        "legal_risk": getattr(option, "legal_risk", 0),
        "political_risk": getattr(option, "political_risk", 0),
        "operational_risk": getattr(option, "operational_risk", 0),
        "affected_factions": list(getattr(option, "affected_factions", []) or []),
        "situation": (getattr(call, "summary", "") if call else ""),
        "ask": (getattr(call, "ask", "") if call else ""),
    }


def memo_fallback(payload: dict) -> MemoDraft:
    """Assemble a deterministic memo from the advice payload (no model call)."""
    title = payload.get("advice_title") or "the selected recommendation"
    benefits = payload.get("expected_benefits") or []
    harms = payload.get("expected_harms") or []
    factions = payload.get("affected_factions") or []

    steps = [f"Pursue: {b}" for b in benefits] or [
        "Proceed per the selected advisory option and document the rationale of record.",
    ]

    opposition = (
        [f"Parties with a stake in this decision: {', '.join(factions)}."]
        if factions
        else ["No specific opposition identified in the current record."]
    )

    return MemoDraft(
        recommendation=payload.get("recommendation") or "(no recommendation on file)",
        rationale=payload.get("rationale")
        or "Assembled from the deterministic advice record; no model narration was used.",
        operational_steps=steps,
        communications=f"Frame public communications around {title}. State only what the record supports.",
        likely_opposition=opposition,
        second_order_risks=harms or ["No second-order harms recorded for this option."],
        fallback_plan=(
            "If the client deviates from this advice, preserve the written advice of "
            "record and revisit at the next call."
        ),
    )
