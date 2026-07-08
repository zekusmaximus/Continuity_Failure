import type { TurnHistory } from "../api/client";

const DECISION_BADGE: Record<string, string> = {
  FOLLOWED: "badge-followed",
  PARTIALLY_FOLLOWED: "badge-partial",
  MODIFIED: "badge-modified",
  DELAYED: "badge-delayed",
  REJECTED: "badge-rejected",
};

export default function TurnHistoryPanel({ history }: { history: TurnHistory | null }) {
  return (
    <section className="panel">
      <header className="panel-head">
        <h2>Turn History</h2>
        <span className="verified">Campaign Dossier</span>
      </header>
      {!history || history.turns.length === 0 ? (
        <p className="muted">No turns on record yet.</p>
      ) : (
        <>
          <ol className="turn-list">
            {[...history.turns].reverse().map((t) => (
              <li key={t.turn_number} className={`turn-item status-${t.status_after.toLowerCase()}`}>
                <div className="turn-top">
                  <span className="turn-num">Turn {t.turn_number}</span>
                  <span className={`decision-badge sm ${DECISION_BADGE[t.decision.decision_type] || ""}`}>
                    {t.decision.decision_type.replace(/_/g, " ")}
                  </span>
                  <span className="turn-status">{t.status_after}</span>
                </div>
                <div className="turn-advice">{t.advice_label}</div>
                <div className="turn-summary">{t.aftermath_summary}</div>
              </li>
            ))}
          </ol>
          <details className="canon">
            <summary>Canon Archive ({history.canon.length})</summary>
            <ul className="canon-list">
              {history.canon.map((c) => (
                <li key={c.id}>
                  <span className="canon-cat">{c.category}</span>
                  <span className="canon-title">{c.title}</span>
                  <span className="canon-source">— {c.source}</span>
                </li>
              ))}
            </ul>
          </details>
        </>
      )}
    </section>
  );
}
