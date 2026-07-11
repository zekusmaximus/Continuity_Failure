import { useState } from "react";
import type { TurnResult } from "../api/client";
import { aggregateChanges, DECISION_BADGE, titleCase } from "../domain";
import { useTelemetry } from "../telemetry/TelemetryProvider";
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
 * CONSEQUENCES phase — consequence hierarchy (Wave 3 B2).
 *
 * Reads in this order: the future hook already on the record (when present),
 * the causal headline and decision-receipt context, then a "Show the full
 * record" disclosure holding the complete existing audit — the causal
 * waterfall, consequence stack, faction shifts, and the raw applied-diff
 * record. The full record defaults open on turns 1–2 and closed from turn 3
 * onward; that is presentation state only, and nothing is removed from the
 * audit. Turns persisted before the causal lead existed render the same
 * audit without the lead block.
 */
export default function ConsequencesPhase({ result }: { result: TurnResult }) {
  const [showRaw, setShowRaw] = useState(false);
  // Presentation default only: the player learns the proof on the first two
  // turns, then receives the shortcut. Expanding is one action either way.
  const [showRecord, setShowRecord] = useState(result.turn_number <= 2);
  const { report } = useTelemetry();
  const stack = result.consequence_stack;
  const lead = result.consequence_lead;
  const decision = result.decision;
  const hasReport = (result.consequence_report?.variables?.length ?? 0) > 0;
  const changes = hasReport ? [] : aggregateChanges(result.diffs);

  const toggleRecord = () => {
    const expanded = !showRecord;
    setShowRecord(expanded);
    report({
      event_type: "record_detail_toggled",
      detail_kind: "full_record",
      expanded,
    });
  };

  const toggleRaw = () => {
    const expanded = !showRaw;
    setShowRaw(expanded);
    report({
      event_type: "record_detail_toggled",
      detail_kind: "applied_diff_record",
      expanded,
    });
  };

  return (
    <section className="cd-stage-panel cd-consequences">
      <h1 className="cd-eyebrow">
        <span className="cd-eyebrow-dot" aria-hidden />
        Consequences · Turn {result.turn_number}
      </h1>

      {lead?.future_hook && (
        <div className="cd-callout cd-callout-warn cd-future-hook">
          <span className="cd-callout-k">Now on the record</span>
          <span>{lead.future_hook}</span>
        </div>
      )}

      {lead?.headline && (
        <div className="cd-causal-lead">
          <p className="cd-lead cd-causal-headline">{lead.headline}</p>
          <p className="cd-causal-receipt cd-muted cd-small">
            <span className={`cd-decision-badge ${DECISION_BADGE[decision.decision_type] ?? ""}`}>
              {titleCase(decision.decision_type)}
            </span>{" "}
            {decision.decider} · adherence {Math.round(decision.adherence * 100)}%
          </p>
        </div>
      )}

      <p className="cd-lead">{result.aftermath_summary}</p>

      <div className="cd-expandable cd-full-record">
        <button
          className="cd-expandable-toggle"
          onClick={toggleRecord}
          aria-expanded={showRecord}
        >
          {showRecord ? "▾" : "▸"} Show the full record
        </button>
        {showRecord && (
          <div className="cd-expandable-body">
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
                    onClick={toggleRaw}
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
          </div>
        )}
      </div>
    </section>
  );
}
