import type { ClientCall, Faction, WorldState } from "../api/client";
import StatusTag from "./StatusTag";
import { PUBLIC_STATUS_LABEL, PUBLIC_STATUS_CLASS } from "../domain";

interface Props {
  call: ClientCall | null;
  state: WorldState;
}

function FactList({ title, items, kind }: { title: string; items: string[]; kind: string }) {
  if (items.length === 0) return null;
  return (
    <div className="cd-field">
      <div className="cd-field-k">{title}</div>
      <ul className={`cd-facts cd-facts-${kind}`}>
        {items.map((f, i) => (
          <li key={i}>{f}</li>
        ))}
      </ul>
    </div>
  );
}

/**
 * BRIEF phase — the organized situation read. Enough to decide with, not the
 * whole system. Affected institutions are named, not fully detailed (that lives
 * in the Case File → Factions tab).
 */
export default function BriefPhase({ call, state }: Props) {
  const crisis = state.active_crisis;

  // Which factions the caller's ask touches, kept to names only here.
  const affected: Faction[] = state.factions.filter(
    (f) => f.current_pressure >= 45 || f.influence >= 60,
  );

  if (!call) {
    return (
      <section className="cd-stage-panel">
        <h1 className="cd-eyebrow">Situation brief unavailable</h1>
        <p className="cd-lead">No active brief for this turn.</p>
      </section>
    );
  }

  return (
    <section className="cd-stage-panel cd-brief">
      <h1 className="cd-eyebrow">
        <span className="cd-eyebrow-dot" aria-hidden />
        Situation brief · Turn {call.turn}
      </h1>

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

      <div className="cd-field">
        <div className="cd-field-k">Summary</div>
        <p className="cd-lead">{call.summary}</p>
      </div>

      <FactList title="Known facts" items={call.known_facts} kind="known" />
      <FactList title="Unknowns" items={call.unknown_facts} kind="unknown" />
      <FactList title="Immediate risks" items={call.immediate_risks} kind="risk" />

      {affected.length > 0 && (
        <div className="cd-field">
          <div className="cd-field-k">Affected institutions</div>
          <div className="cd-tagrow">
            {affected.map((f) => (
              <span key={f.id} className="cd-chip">{f.name}</span>
            ))}
          </div>
        </div>
      )}

      <div className="cd-field">
        <div className="cd-field-k">Public exposure</div>
        <StatusTag
          label={PUBLIC_STATUS_LABEL[call.public_exposure] ?? call.public_exposure}
          className={PUBLIC_STATUS_CLASS[call.public_exposure] ?? "tag-private"}
        />
      </div>
    </section>
  );
}
