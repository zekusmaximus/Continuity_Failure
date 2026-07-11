import { useState } from "react";
import type { ClientCall, PowerAllocation, SystemStatus } from "../api/client";
import StatusTag from "./StatusTag";
import {
  POWER_ALLOCATIONS,
  URGENCY_LABEL,
  URGENCY_CLASS,
  PUBLIC_STATUS_LABEL,
  PUBLIC_STATUS_CLASS,
} from "../domain";

/**
 * CALL phase — only the incoming client call. No state, factions, documents, or
 * dossier. The one question here: will you take the call?
 *
 * At CRITICAL, this is also where the turn's auxiliary power can be committed
 * — the pre-decision choice: routing it to COMMUNICATIONS opens the caller's
 * disposition (and lets their history reach the desk) while the advice is
 * still being composed. Committing is binding for the whole turn.
 */
export default function CallPhase({
  call,
  disposition = "",
  systemStatus = null,
  onCommitPower,
  busy = false,
}: {
  call: ClientCall | null;
  disposition?: string;
  systemStatus?: SystemStatus | null;
  // Absent when the turn is already resolved (read-only review).
  onCommitPower?: (allocation: PowerAllocation) => void;
  busy?: boolean;
}) {
  const [pending, setPending] = useState<PowerAllocation | null>(null);
  const allocationRequired = !!systemStatus?.requires_power_allocation;
  const committed = systemStatus?.power_commitment ?? null;
  const committedLabel =
    POWER_ALLOCATIONS.find((a) => a.id === committed)?.label ?? committed;

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

      {allocationRequired && (
        <fieldset className="cd-power-allocation cd-call-power">
          <legend className="cd-field-k">
            Auxiliary power · one subsystem this turn
          </legend>
          {committed ? (
            <p className="cd-muted cd-small" role="status">
              ⚡ Auxiliary power is committed to <strong>{committedLabel}</strong>{" "}
              this turn. One subsystem per turn; everything else stays dark.
            </p>
          ) : (
            <>
              <p className="cd-muted cd-small">
                The workstation is critical: the auxiliary feed carries exactly
                one subsystem per turn. Route it now to work the call with that
                subsystem live — Communications opens the caller's disposition
                before you compose advice. Routing is <strong>binding</strong>{" "}
                for the turn; you can also leave it and commit later, through
                drafting or with the advice itself.
              </p>
              {POWER_ALLOCATIONS.map((allocation) => (
                <label key={allocation.id} className="cd-power-option">
                  <input
                    type="radio"
                    name="call-power-allocation"
                    value={allocation.id}
                    checked={pending === allocation.id}
                    disabled={busy || !onCommitPower}
                    onChange={() => setPending(allocation.id)}
                  />
                  <span className="cd-power-label">{allocation.label}</span>
                  <span className="cd-muted cd-small">{allocation.detail}</span>
                </label>
              ))}
              <button
                className="cd-btn"
                disabled={!pending || busy || !onCommitPower}
                onClick={() => pending && onCommitPower?.(pending)}
              >
                {pending
                  ? `Route auxiliary power → ${
                      POWER_ALLOCATIONS.find((a) => a.id === pending)?.label
                    }`
                  : "Route auxiliary power"}
              </button>
            </>
          )}
        </fieldset>
      )}

      <div className="cd-call-caller">
        <div className="cd-call-name">{call.caller}</div>
        {call.caller_role && <div className="cd-call-role">{call.caller_role}</div>}
        {disposition && <p className="cd-muted cd-call-disposition">{disposition}</p>}
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
