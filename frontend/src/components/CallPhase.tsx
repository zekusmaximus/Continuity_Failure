import type { ClientCall } from "../api/client";
import StatusTag from "./StatusTag";
import {
  URGENCY_LABEL,
  URGENCY_CLASS,
  PUBLIC_STATUS_LABEL,
  PUBLIC_STATUS_CLASS,
} from "../domain";

/**
 * CALL phase — only the incoming client call. No state, factions, documents, or
 * dossier. The one question here: will you take the call?
 */
export default function CallPhase({ call }: { call: ClientCall | null }) {
  if (!call) {
    return (
      <section className="cd-stage-panel">
        <h1 className="cd-eyebrow">Engagement closed</h1>
        <p className="cd-lead">No active call. The engagement has closed.</p>
        <p className="cd-muted">Review the campaign dossier for the final record.</p>
      </section>
    );
  }

  return (
    <section className="cd-stage-panel cd-call">
      <h1 className="cd-eyebrow">
        <span className="cd-eyebrow-dot" aria-hidden />
        Incoming call · Turn {call.turn}
      </h1>

      <div className="cd-call-caller">
        <div className="cd-call-name">{call.caller}</div>
        {call.caller_role && <div className="cd-call-role">{call.caller_role}</div>}
      </div>

      <div className="cd-tagrow">
        <StatusTag
          label={`Urgency: ${URGENCY_LABEL[call.urgency] ?? call.urgency}`}
          className={URGENCY_CLASS[call.urgency] ?? "tag-high"}
        />
        {call.time_horizon && (
          <StatusTag label={`Horizon: ${call.time_horizon}`} className="tag-horizon" />
        )}
        {call.public_exposure && (
          <StatusTag
            label={`Exposure: ${PUBLIC_STATUS_LABEL[call.public_exposure] ?? call.public_exposure}`}
            className={PUBLIC_STATUS_CLASS[call.public_exposure] ?? "tag-private"}
          />
        )}
      </div>

      <p className="cd-lead">{call.summary}</p>

      <div className="cd-field">
        <div className="cd-field-k">The ask</div>
        <p className="cd-quote">{call.ask}</p>
      </div>

      {call.immediate_risks.length > 0 && (
        <div className="cd-field">
          <div className="cd-field-k">Primary risk</div>
          <p className="cd-field-v">{call.immediate_risks[0]}</p>
        </div>
      )}

      {call.private_pressure && (
        <div className="cd-callout cd-callout-warn">
          <span className="cd-callout-k">Read on the line</span>
          <span>{call.private_pressure}</span>
        </div>
      )}
    </section>
  );
}
