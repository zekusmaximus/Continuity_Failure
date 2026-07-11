import type { SystemStatus } from "../api/client";
import { levelClass } from "../domain";

/**
 * The workstation's own condition — the first consumer of the deterministic
 * degradation assessment (engine/degradation.py via system_status).
 *
 * Two surfaces share this file because they share the vocabulary:
 * - DegradationBanner: a thin always-visible strip under the header whenever
 *   the desk is not NOMINAL. The player should never have to open a panel to
 *   learn their feeds are stale.
 * - SystemStatusPanel: the full meter readout (power / comms / data
 *   freshness / staff) with the band and the diegetic model-status line,
 *   rendered in the Case File's state tab.
 */

export const BAND_LABEL: Record<SystemStatus["degradation_band"], string> = {
  NOMINAL: "Workstation nominal",
  STRAINED: "Workstation strained",
  DEGRADED: "Workstation degraded",
  CRITICAL: "Workstation critical",
};

function staleLine(status: SystemStatus): string {
  const anchor =
    status.last_live_turn > 0
      ? `turn ${status.last_live_turn} close-out`
      : "engagement intake";
  return `Live feeds lost — working from the ${anchor} snapshot.`;
}

export function DegradationBanner({ status }: { status: SystemStatus | null }) {
  if (!status || status.degradation_band === "NOMINAL") return null;
  const detail =
    status.degradation_band === "CRITICAL"
      ? "Auxiliary power supports one subsystem per turn."
      : status.degradation_band === "DEGRADED"
        ? `${staleLine(status)} Model access offline.`
        : staleLine(status);
  return (
    <div
      className={`cd-degradation-strip cd-degradation-${status.degradation_band.toLowerCase()}`}
      role="status"
    >
      <strong>{BAND_LABEL[status.degradation_band]}</strong> — {detail}
    </div>
  );
}

function Meter({ label, value }: { label: string; value: number }) {
  return (
    <li className="cd-var-row">
      <span className="cd-var-label">
        <span>{label}</span>
      </span>
      <span
        className="cd-var-bar"
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value}
        aria-valuetext={`${value} of 100`}
      >
        <span
          className={`cd-var-fill ${levelClass(value)}`}
          style={{ width: `${value}%` }}
        />
      </span>
      <span className={`cd-var-value ${levelClass(value)}`}>{value}</span>
    </li>
  );
}

export default function SystemStatusPanel({ status }: { status: SystemStatus }) {
  const band = status.degradation_band;
  return (
    <section className={`cd-panel cd-system-status cd-system-${band.toLowerCase()}`}>
      <header className="cd-panel-head">
        <h2>Workstation Status</h2>
        <span
          className={`cd-band-tag cd-band-${band.toLowerCase()}`}
          aria-label={`Degradation band: ${band}`}
        >
          {BAND_LABEL[band]}
        </span>
      </header>
      <ul className="cd-var-list">
        <Meter label="Grid power" value={status.power} />
        <Meter label="Communications" value={status.comms} />
        <Meter label="Data freshness" value={status.data_freshness} />
        <Meter label="Operations staff" value={status.staff_capacity} />
      </ul>
      <p className="cd-system-model">
        <span className={status.ai_available ? "cd-system-ok" : "cd-system-off"}>
          {status.model_status}
        </span>
      </p>
      {!status.live_feeds && (
        <p className="cd-system-stale" role="status">
          {staleLine(status)}
        </p>
      )}
    </section>
  );
}
