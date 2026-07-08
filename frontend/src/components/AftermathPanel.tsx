import type { TurnResult } from "../api/client";
import { VARIABLE_META } from "../domain";

function diffColor(delta: number, risk: boolean): string {
  if (delta === 0) return "neutral";
  const good = risk ? delta < 0 : delta > 0;
  return good ? "good" : "bad";
}

const DECISION_BADGE: Record<string, string> = {
  FOLLOWED: "badge-followed",
  PARTIALLY_FOLLOWED: "badge-partial",
  MODIFIED: "badge-modified",
  DELAYED: "badge-delayed",
  REJECTED: "badge-rejected",
};

export default function AftermathPanel({ result }: { result: TurnResult | null }) {
  if (!result) {
    return (
      <section className="panel">
        <header className="panel-head">
          <h2>Aftermath</h2>
        </header>
        <p className="muted">No turn resolved yet. Submit advice to advance the engagement.</p>
      </section>
    );
  }

  const ordered = [...result.diffs].sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));

  return (
    <section className="panel">
      <header className="panel-head">
        <h2>Aftermath</h2>
        <span className="verified">Resolved Turn {result.turn_number}</span>
      </header>

      <div className="decision-block">
        <span className={`decision-badge ${DECISION_BADGE[result.decision.decision_type] || ""}`}>
          {result.decision.decision_type.replace(/_/g, " ")}
        </span>
        <span className="decider">{result.decision.decider}</span>
        <span className="adherence">adherence {Math.round(result.decision.adherence * 100)}%</span>
      </div>
      <p className="decision-rationale">{result.decision.rationale}</p>

      <div className="subhead">Applied Diffs</div>
      <ul className="diff-list">
        {ordered.map((d, i) => {
          const meta = VARIABLE_META[d.variable];
          const color = diffColor(d.delta, meta?.risk ?? false);
          const sign = d.delta > 0 ? "+" : "";
          return (
            <li key={i} className={`diff-row diff-${d.source_type}`}>
              <span className="diff-var">{meta?.label ?? d.variable}</span>
              <span className="diff-move">
                {d.old_value} → {d.new_value}
              </span>
              <span className={`diff-delta delta-${color}`}>
                {sign}
                {d.delta}
              </span>
              <span className="diff-source">{d.source_type}</span>
            </li>
          );
        })}
      </ul>

      <div className="subhead">Summary</div>
      <p className="aftermath-text">{result.aftermath_summary}</p>
    </section>
  );
}
