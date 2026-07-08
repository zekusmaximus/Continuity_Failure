import type { TurnHistory } from "../api/client";
import { DECISION_BADGE, titleCase } from "../domain";

export default function TurnHistoryPanel({ history }: { history: TurnHistory | null }) {
  return (
    <section className="cd-panel">
      <header className="cd-panel-head">
        <h2>Turn History</h2>
        <span className="cd-verified">Engagement Log</span>
      </header>
      {!history || history.turns.length === 0 ? (
        <p className="cd-muted">No turns on record yet.</p>
      ) : (
        <ol className="cd-turn-list">
          {[...history.turns].reverse().map((t) => (
            <li key={t.turn_number} className={`cd-turn-item cd-status-${t.status_after.toLowerCase()}`}>
              <div className="cd-turn-top">
                <span className="cd-turn-num">Turn {t.turn_number}</span>
                <span className={`cd-decision-badge sm ${DECISION_BADGE[t.decision.decision_type] ?? ""}`}>
                  {titleCase(t.decision.decision_type)}
                </span>
                <span className="cd-turn-status">{t.status_after}</span>
              </div>
              <div className="cd-turn-advice">{t.advice_label}</div>
              <div className="cd-turn-summary">{t.aftermath_summary}</div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
