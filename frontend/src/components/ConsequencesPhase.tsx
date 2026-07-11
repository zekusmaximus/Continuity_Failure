import { useState } from "react";
import type { TurnResult } from "../api/client";
import { aggregateChanges } from "../domain";
import AppliedDiffList from "./AppliedDiffList";
import CausalWaterfall from "./CausalWaterfall";

function StackSection({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone: string;
}) {
  if (items.length === 0) return null;
  return (
    <div className={`cd-stack-sec cd-stack-${tone}`}>
      <h2 className="cd-subhead">{title}</h2>
      <ul className="cd-stack-list">
        {items.map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </ul>
    </div>
  );
}

/**
 * CONSEQUENCES phase — human-readable fallout first, then the causal
 * waterfall: the server's authoritative per-variable reconciliation of how
 * the starting snapshot became the resolved snapshot (start → your advice as
 * the client applied it → client action → decision cost → ambient drift →
 * final). The raw applied diffs stay available behind an expandable
 * "Authoritative applied-diff record". Turns persisted before the report
 * existed fall back to the flat net-change table.
 */
export default function ConsequencesPhase({ result }: { result: TurnResult }) {
  const [showRaw, setShowRaw] = useState(false);
  const stack = result.consequence_stack;
  const hasReport = (result.consequence_report?.variables?.length ?? 0) > 0;
  const changes = hasReport ? [] : aggregateChanges(result.diffs);

  return (
    <section className="cd-stage-panel cd-consequences">
      <h1 className="cd-eyebrow">
        <span className="cd-eyebrow-dot" aria-hidden />
        Consequences · Turn {result.turn_number}
      </h1>

      <p className="cd-lead">{result.aftermath_summary}</p>

      <div className="cd-stack-grid">
        <StackSection title="Immediate consequences" items={stack.immediate} tone="immediate" />
        <StackSection title="Second-order consequences" items={stack.second_order} tone="second" />
        <StackSection
          title="Faction reactions"
          items={stack.faction_reactions.map((r) => `${r.faction_name}: ${r.reaction}`)}
          tone="faction"
        />
        <StackSection title="Media / rumor framing" items={stack.media_framing} tone="media" />
        <StackSection title="Legal / procedural fallout" items={stack.legal_fallout} tone="legal" />
        <StackSection title="Canonized events" items={stack.canonized_events} tone="canon" />
        <StackSection title="Open threads" items={stack.opened_threads} tone="thread" />
        <StackSection
          title="Threads escalated"
          items={stack.escalated_threads ?? []}
          tone="thread-escalated"
        />
        <StackSection
          title="Threads resolved"
          items={stack.resolved_threads ?? []}
          tone="thread-resolved"
        />
        <StackSection
          title="Faction standing shifts"
          items={(result.faction_shifts ?? []).map((s) => {
            const label =
              s.field === "trust_in_player"
                ? "trust"
                : s.field === "current_pressure"
                  ? "pressure"
                  : "influence";
            return `${s.faction_name}: ${label} ${s.old_value}→${s.new_value} — ${s.reason}`;
          })}
          tone="faction-shift"
        />
      </div>

      <div className="cd-changes">
        {hasReport ? (
          <CausalWaterfall result={result} />
        ) : (
          <>
            <h2 className="cd-subhead">State changes</h2>
            <p className="cd-context-note">
              Reasons distinguish advice, client modification, and ambient
              Drift—the crisis pressure applied independently each turn.
            </p>
            {changes.length === 0 ? (
              <p className="cd-muted cd-small">No tracked variable moved this turn.</p>
            ) : (
              <ul className="cd-change-list">
                {changes.map((c) => {
                  const good = c.risk ? c.delta < 0 : c.delta > 0;
                  const sign = c.delta > 0 ? "+" : "";
                  return (
                    <li key={c.variable} className="cd-change-row">
                      <span className="cd-change-label">{c.label}</span>
                      <span className="cd-change-move">
                        {c.oldValue} <span className="cd-change-arrow">→</span> {c.newValue}
                      </span>
                      <span className={`cd-change-delta ${good ? "cd-delta-good" : "cd-delta-bad"}`}>
                        {sign}
                        {c.delta}
                      </span>
                      {c.reasons.length > 0 && (
                        <span className="cd-change-reason">{c.reasons.join(" · ")}</span>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </>
        )}

        {result.diffs.length > 0 && (
          <div className="cd-expandable">
            <button
              className="cd-expandable-toggle"
              onClick={() => setShowRaw((s) => !s)}
              aria-expanded={showRaw}
            >
              {showRaw ? "▾" : "▸"} Authoritative applied-diff record
            </button>
            {showRaw && (
              <div className="cd-expandable-body">
                <AppliedDiffList diffs={result.diffs} />
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
