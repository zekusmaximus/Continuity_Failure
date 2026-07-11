import type { CanonEntry, OpenThread } from "../api/client";
import StatusTag from "./StatusTag";
import {
  PUBLIC_STATUS_LABEL,
  PUBLIC_STATUS_CLASS,
  threadDeadlineLabel,
  titleCase,
} from "../domain";

export default function CanonPanel({
  canon,
  threads,
}: {
  canon: CanonEntry[];
  threads: OpenThread[];
}) {
  const ordered = [...canon].sort((a, b) => a.turn_number - b.turn_number);
  const openThreads = threads.filter((t) => t.status !== "resolved");
  const resolvedThreads = threads.filter((t) => t.status === "resolved");
  return (
    <section className="cd-panel">
      <header className="cd-panel-head">
        <h2>Archive · Canon & Open Threads</h2>
        <span className="cd-verified">{canon.length} entries</span>
      </header>

      <div className="cd-subhead">Canon Archive</div>
      {ordered.length === 0 ? (
        <p className="cd-muted cd-small">No canon entries yet.</p>
      ) : (
        <ul className="cd-canon-list">
          {ordered.map((c) => (
            <li key={c.id} className="cd-canon-item">
              <div className="cd-canon-top">
                <span className="cd-canon-cat">{c.category}</span>
                <span className="cd-canon-title">{c.title}</span>
                <StatusTag
                  label={PUBLIC_STATUS_LABEL[c.public_status] ?? c.public_status}
                  className={PUBLIC_STATUS_CLASS[c.public_status] ?? "tag-private"}
                />
              </div>
              <p className="cd-canon-body">{c.body}</p>
              <div className="cd-canon-foot">
                <span className="cd-canon-src">— {c.source}</span>
                <span className="cd-canon-turn">Turn {c.turn_number}</span>
              </div>
            </li>
          ))}
        </ul>
      )}

      <div className="cd-subhead">Open Threads ({openThreads.length})</div>
      {openThreads.length === 0 ? (
        <p className="cd-muted cd-small">No open threads.</p>
      ) : (
        <ul className="cd-thread-list">
          {openThreads.map((t) => {
            const deadline = threadDeadlineLabel(t);
            return (
              <li key={t.id} className="cd-thread-item">
                <div className="cd-thread-top">
                  <span className="cd-thread-title">{t.title}</span>
                  <span className={`cd-thread-status cd-ts-${t.status}`}>
                    {titleCase(t.status)}
                  </span>
                  {deadline && (
                    <span className="cd-thread-deadline">{deadline}</span>
                  )}
                </div>
                <p className="cd-thread-summary">{t.summary}</p>
                {t.escalation_count > 0 && t.escalation_note && (
                  <p className="cd-thread-summary cd-thread-esc-note">
                    Last escalation: {t.escalation_note}
                  </p>
                )}
                <span className="cd-canon-turn">Opened turn {t.turn_opened}</span>
              </li>
            );
          })}
        </ul>
      )}

      {resolvedThreads.length > 0 && (
        <>
          <div className="cd-subhead">Resolved Threads ({resolvedThreads.length})</div>
          <ul className="cd-thread-list">
            {resolvedThreads.map((t) => (
              <li key={t.id} className="cd-thread-item cd-thread-resolved">
                <div className="cd-thread-top">
                  <span className="cd-thread-title">{t.title}</span>
                  <span className={`cd-thread-status cd-ts-${t.status}`}>
                    {titleCase(t.status)}
                  </span>
                  <span className="cd-thread-deadline">
                    {threadDeadlineLabel(t)}
                  </span>
                </div>
                {t.resolution_note && (
                  <p className="cd-thread-summary">{t.resolution_note}</p>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
