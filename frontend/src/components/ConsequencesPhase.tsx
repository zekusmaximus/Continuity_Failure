import { useState } from "react";
import type { TurnResult } from "../api/client";
import { aggregateChanges } from "../domain";
import AppliedDiffList from "./AppliedDiffList";

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
      <div className="cd-subhead">{title}</div>
      <ul className="cd-stack-list">
        {items.map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </ul>
    </div>
  );
}

/**
 * CONSEQUENCES phase — human-readable fallout first, then a compact "what
 * changed" table (only moved variables, old → new, reason). The raw applied
 * diffs stay hidden behind an expandable "Why did this change?".
 */
export default function ConsequencesPhase({ result }: { result: TurnResult }) {
  const [showRaw, setShowRaw] = useState(false);
  const stack = result.consequence_stack;
  const changes = aggregateChanges(result.diffs);

  return (
    <section className="cd-stage-panel cd-consequences">
      <div className="cd-eyebrow">
        <span className="cd-eyebrow-dot" aria-hidden />
        Consequences · Turn {result.turn_number}
      </div>

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
      </div>

      <div className="cd-changes">
        <div className="cd-subhead">State changes</div>
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

        {result.diffs.length > 0 && (
          <div className="cd-expandable">
            <button
              className="cd-expandable-toggle"
              onClick={() => setShowRaw((s) => !s)}
              aria-expanded={showRaw}
            >
              {showRaw ? "▾" : "▸"} Why did this change?
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
