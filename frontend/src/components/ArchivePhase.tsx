import type { TurnHistory, TurnResult } from "../api/client";
import { DECISION_BADGE, titleCase } from "../domain";

interface Props {
  result: TurnResult;
  history: TurnHistory | null;
}

/**
 * ARCHIVE phase — a concise record of the turn just resolved. The full log lives
 * in the Case File → Timeline tab; this is the one-screen summary before the
 * next call.
 */
export default function ArchivePhase({ result, history }: Props) {
  const d = result.decision;
  const stack = result.consequence_stack;

  // Threads opened or updated this turn, matched from the live thread list.
  const openThreads = (history?.open_threads ?? []).filter(
    (t) => t.turn_opened === result.turn_number,
  );

  return (
    <section className="cd-stage-panel cd-archive">
      <div className="cd-eyebrow">
        <span className="cd-eyebrow-dot" aria-hidden />
        Turn archive · Turn {result.turn_number} filed
      </div>

      <div className="cd-field">
        <div className="cd-field-k">Advice issued</div>
        <p className="cd-field-v">{result.advice_label}</p>
      </div>

      <div className="cd-field">
        <div className="cd-field-k">Client decision</div>
        <p className="cd-field-v">
          <span className={`cd-decision-badge sm ${DECISION_BADGE[d.decision_type] ?? ""}`}>
            {titleCase(d.decision_type)}
          </span>{" "}
          {d.decider} · adherence {Math.round(d.adherence * 100)}%
        </p>
      </div>

      {stack.immediate.length > 0 && (
        <div className="cd-field">
          <div className="cd-field-k">Major consequences</div>
          <ul className="cd-facts cd-facts-known">
            {stack.immediate.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      {result.canon_entry && (
        <div className="cd-field">
          <div className="cd-field-k">Canon entry</div>
          <p className="cd-field-v">
            <strong>{result.canon_entry.title}</strong> — {result.canon_entry.body}
          </p>
        </div>
      )}

      {openThreads.length > 0 && (
        <div className="cd-field">
          <div className="cd-field-k">New / updated open threads</div>
          <ul className="cd-facts cd-facts-risk">
            {openThreads.map((t) => (
              <li key={t.id}>
                {t.title} — {t.summary}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
