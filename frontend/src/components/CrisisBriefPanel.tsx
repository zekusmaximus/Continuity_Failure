import type { ClientCall, WorldState } from "../api/client";
import StatusTag from "./StatusTag";
import {
  URGENCY_LABEL,
  URGENCY_CLASS,
  PUBLIC_STATUS_LABEL,
  PUBLIC_STATUS_CLASS,
} from "../domain";

interface Props {
  call: ClientCall | null;
  state: WorldState;
}

function FactList({ title, items, kind }: { title: string; items: string[]; kind: string }) {
  return (
    <div className="cd-fact-block">
      <div className="cd-subhead">{title}</div>
      {items.length === 0 ? (
        <p className="cd-muted cd-small">No entries on record.</p>
      ) : (
        <ul className={`cd-facts cd-facts-${kind}`}>
          {items.map((f, i) => (
            <li key={i}>{f}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * Crisis Brief / Situation: the active crisis plus the organized situation
 * read (known facts, unknowns, immediate risks, public exposure) drawn from the
 * current client call.
 */
export default function CrisisBriefPanel({ call, state }: Props) {
  const crisis = state.active_crisis;
  return (
    <section className="cd-panel">
      <header className="cd-panel-head">
        <h2>Crisis Brief</h2>
        <span className="cd-verified">{state.last_verified}</span>
      </header>

      {crisis && (
        <div className="cd-crisis-banner">
          <div className="cd-crisis-head">
            <span className="cd-crisis-tag">ACTIVE CRISIS</span>
            <strong>{crisis.name}</strong>
            <span className="cd-severity">severity {crisis.severity}</span>
          </div>
          <p className="cd-crisis-desc">{crisis.description}</p>
        </div>
      )}

      {call ? (
        <>
          <div className="cd-brief-flags">
            <StatusTag
              label={`Urgency: ${URGENCY_LABEL[call.urgency] ?? call.urgency}`}
              className={URGENCY_CLASS[call.urgency] ?? "tag-high"}
            />
            {call.time_horizon && (
              <StatusTag label={`Horizon: ${call.time_horizon}`} className="tag-horizon" />
            )}
            <StatusTag
              label={`Exposure: ${PUBLIC_STATUS_LABEL[call.public_exposure] ?? call.public_exposure}`}
              className={PUBLIC_STATUS_CLASS[call.public_exposure] ?? "tag-private"}
            />
          </div>

          <FactList title="Known Facts" items={call.known_facts} kind="known" />
          <FactList title="Unknowns" items={call.unknown_facts} kind="unknown" />
          <FactList title="Immediate Risks" items={call.immediate_risks} kind="risk" />
        </>
      ) : (
        <p className="cd-muted">No active brief for this turn.</p>
      )}
    </section>
  );
}
