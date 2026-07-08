import type { ClientCall } from "../api/client";
import StatusTag from "./StatusTag";
import { URGENCY_LABEL, URGENCY_CLASS } from "../domain";

export default function ClientCallPanel({ call }: { call: ClientCall | null }) {
  if (!call) {
    return (
      <section className="cd-panel">
        <header className="cd-panel-head">
          <h2>Client Call</h2>
        </header>
        <p className="cd-muted">No active call for this turn.</p>
      </section>
    );
  }
  return (
    <section className="cd-panel">
      <header className="cd-panel-head">
        <h2>Client Call</h2>
        <span className="cd-verified">Turn {call.turn}</span>
      </header>

      <div className="cd-caller-line">
        <span className="cd-caller-tag">INCOMING</span>
        <StatusTag
          label={URGENCY_LABEL[call.urgency] ?? call.urgency}
          className={URGENCY_CLASS[call.urgency] ?? "tag-high"}
        />
      </div>
      <div className="cd-caller-name">{call.caller}</div>
      {call.caller_role && <div className="cd-caller-role">{call.caller_role}</div>}
      <p className="cd-call-summary">{call.summary}</p>

      {call.time_horizon && (
        <div className="cd-call-meta">
          <span className="cd-meta-k">Time horizon</span>
          <span className="cd-meta-v">{call.time_horizon}</span>
        </div>
      )}

      <div className="cd-subhead">The Ask</div>
      <p className="cd-ask">{call.ask}</p>

      {call.private_pressure && (
        <div className="cd-private-pressure">
          <span className="cd-meta-k">Private pressure</span>
          <span className="cd-meta-v">{call.private_pressure}</span>
        </div>
      )}
    </section>
  );
}
