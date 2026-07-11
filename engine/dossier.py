"""Campaign dossier (Markdown) generation.

The dossier turns a finished (or in-progress) campaign into a coherent
institutional case file: status, final state, the turn-by-turn timeline, canon,
open threads, and a faction summary. It is generated deterministically from
campaign data only -- no model output, no state mutation.

This is intentionally a plain-string builder so the engine stays framework-free;
the backend can return it as text or the frontend can render / download it.
"""

from __future__ import annotations

from typing import List

from engine.models import (
    AdviceEffectOutcome,
    Campaign,
    CampaignStatus,
    TurnResult,
    VariableConsequence,
)
from engine.state import humanize_variable


def _risk_label(variable: str, value: int) -> str:
    return f"{value}/100"


_SOURCE_LABEL = {
    "advice": "advice",
    "npc_modification": "client action",
    "decision": "decision cost",
    "ambient": "ambient drift",
}


def _signed(delta: int) -> str:
    return f"+{delta}" if delta > 0 else str(delta)


def _mediation_note(entry: VariableConsequence) -> str:
    """One clause describing how the advice proposal was mediated."""
    med = entry.advice
    assert med is not None
    adherence_pct = int(round(med.adherence * 100))
    if med.outcome == AdviceEffectOutcome.APPLIED:
        note = f"advice proposed {_signed(med.proposed_delta)}, applied in full"
    elif med.outcome == AdviceEffectOutcome.REJECTED:
        note = f"advice proposed {_signed(med.proposed_delta)}, rejected — not applied"
    elif med.outcome == AdviceEffectOutcome.DELAYED:
        note = f"advice proposed {_signed(med.proposed_delta)}, delayed — not applied this turn"
    else:
        note = (
            f"advice proposed {_signed(med.proposed_delta)}, applied "
            f"{_signed(med.applied_delta)} at {adherence_pct}% adherence"
        )
    if med.clamped:
        note += " (clamped at the 0–100 bound)"
    return note


def _reconciliation_lines(turn: TurnResult) -> List[str]:
    """Render the turn's causal consequence report as compact Markdown lines."""
    report = turn.consequence_report
    if not report.variables:
        return []
    lines = ["- **State reconciliation (start → attributed deltas → final):**"]
    for entry in report.variables:
        steps = "; ".join(
            f"{_signed(d.delta)} {_SOURCE_LABEL.get(d.source_type, d.source_type)} ({d.reason})"
            for d in entry.deltas
        )
        parts = [steps] if steps else ["no applied change"]
        if entry.advice is not None:
            parts.append(_mediation_note(entry))
        lines.append(
            f"  - {entry.label}: {entry.start_value} → {entry.final_value} "
            f"(net {_signed(entry.net_delta)}) — " + " · ".join(parts)
        )
    return lines


def render_dossier_markdown(campaign: Campaign) -> str:
    """Render the campaign as a Markdown case-file dossier."""
    lines: List[str] = []
    v = campaign.world_state.variables
    status = campaign.status

    lines.append(f"# Campaign Dossier \u2014 {campaign.name}")
    lines.append("")
    lines.append(f"- **Campaign ID:** `{campaign.id}`")
    lines.append(f"- **Scenario:** `{campaign.scenario_id}`")
    lines.append(f"- **Status:** {status}")
    lines.append(f"- **Turns resolved:** {len(campaign.turn_history)} / {campaign.max_turns}")
    if campaign.failure_reason:
        lines.append(f"- **Failure reason:** {campaign.failure_reason}")
    lines.append(f"- **Created:** {campaign.created_at or 'unknown'}")
    lines.append("")

    lines.append("## Final World State")
    lines.append("")
    lines.append("| Variable | Value |")
    lines.append("| --- | --- |")
    for key in sorted(v.keys()):
        lines.append(f"| {humanize_variable(key)} | {_risk_label(key, v[key])} |")
    lines.append("")

    # Faction summary
    lines.append("## Faction Summary")
    lines.append("")
    lines.append("| Faction | Alignment | Posture | Influence | Pressure |")
    lines.append("| --- | --- | --- | --- | --- |")
    for f in campaign.world_state.factions:
        lines.append(
            f"| {f.name} | {f.alignment} | {f.posture} | "
            f"{f.influence} | {f.current_pressure} |"
        )
    lines.append("")

    # Turn-by-turn timeline
    lines.append("## Turn-by-Turn Timeline")
    lines.append("")
    if not campaign.turn_history:
        lines.append("_No turns resolved yet._")
        lines.append("")
    else:
        for t in campaign.turn_history:
            lines.append(f"### Turn {t.turn_number} \u2014 {t.advice_label}")
            lines.append("")
            lines.append(f"- **NPC decision:** {t.decision.decision_type} "
                         f"(adherence {int(round(t.decision.adherence * 100))}%)")
            lines.append(f"- **Status after:** {t.status_after}")
            lines.append(f"- **Client:** {t.decision.decider}")
            lines.append(f"- **Aftermath:** {t.aftermath_summary}")
            if t.sent_memo is not None:
                lines.append(
                    f"- **Memo of record:** `{t.sent_memo.memo_id}` revision "
                    f"{t.sent_memo.revision} (`{t.sent_memo.content_digest}`)"
                )
            lines.extend(_reconciliation_lines(t))
            if t.consequence_stack.opened_threads:
                lines.append("- **Threads opened:** "
                             + "; ".join(t.consequence_stack.opened_threads))
            lines.append("")

    lines.append("## Advice Memos of Record")
    lines.append("")
    sent = [t for t in campaign.turn_history if t.sent_memo is not None]
    if not sent:
        lines.append("_No advice memos have been sent._")
        lines.append("")
    else:
        for turn in sent:
            memo = turn.sent_memo
            assert memo is not None
            lines.append(f"### Turn {turn.turn_number} — {memo.name}")
            lines.append("")
            lines.append(f"- **Memo ID / revision:** `{memo.memo_id}` / {memo.revision}")
            lines.append(f"- **Sent:** {memo.sent_at}")
            lines.append(f"- **Authorship/source:** {memo.author} / {memo.source}")
            lines.append(f"- **Classification:** {memo.classification}")
            workflow_label = {
                "manual": "manual player draft",
                "deterministic_template": "deterministic desk template",
                "ai_assisted": "AI-assisted and validated",
                "deterministic_fallback": "deterministic system fallback",
            }.get(memo.provenance.workflow, memo.provenance.workflow)
            lines.append(f"- **Workflow:** {workflow_label}")
            if memo.provenance.model_run_id:
                lines.append(f"- **Model run:** `{memo.provenance.model_run_id}`")
            lines.append(f"- **SHA-256:** `{memo.content_digest}`")
            lines.append(
                f"- **Client decision:** {turn.decision.decision_type} by "
                f"{turn.decision.decider}"
            )
            lines.append("")
            lines.append("**Exact sent content**")
            lines.append("")
            lines.append("```text")
            # Keep the exact sent string contiguous in the export. The digest
            # above remains the authority if prose itself contains a fence.
            lines.append(memo.content)
            lines.append("```")
            lines.append("")

    # Canon
    lines.append("## Canon Archive")
    lines.append("")
    if not campaign.canon:
        lines.append("_No canon entries._")
        lines.append("")
    else:
        for c in campaign.canon:
            lines.append(f"- **[T{c.turn_number}] {c.title}** \u2014 _{c.category}_ "
                         f"({c.public_status})")
            lines.append(f"  - {c.body}")
        lines.append("")

    # Open threads
    open_only = [t for t in campaign.open_threads if t.status != "resolved"]
    lines.append("## Open Threads")
    lines.append("")
    if not open_only:
        lines.append("_No open threads._")
        lines.append("")
    else:
        for t in open_only:
            lines.append(f"- **{t.title}** (opened turn {t.turn_opened}, {t.status})")
            lines.append(f"  - {t.summary}")
        lines.append("")

    lines.append("---")
    lines.append("_Generated from authoritative deterministic campaign state. "
                 "AI-assisted drafts, when used, remain advisory and cannot mutate state._")
    lines.append("")
    return "\n".join(lines)


def dossier_filename(campaign: Campaign) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in campaign.name.strip())
    safe = safe.strip("-") or "campaign"
    suffix = {
        CampaignStatus.ACTIVE: "active",
        CampaignStatus.COMPLETED: "completed",
        CampaignStatus.FAILED: "failed",
    }.get(campaign.status, "campaign")
    return f"{safe}-{suffix}.md"
