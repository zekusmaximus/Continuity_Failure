import type { SystemStatus } from "../api/client";
import { levelClass } from "../domain";

interface MeterProps {
  label: string;
  value: number;
  hint?: string;
}

function Meter({ label, value, hint }: MeterProps) {
  return (
    <div className="cd-meter">
      <div className="cd-meter-head">
        <span className="cd-meter-label">{label}</span>
        <span className={`cd-meter-value ${levelClass(value)}`}>{value}</span>
      </div>
      <div className="cd-meter-bar">
        <div className={`cd-meter-fill ${levelClass(value)}`} style={{ width: `${value}%` }} />
      </div>
      {hint && <div className="cd-meter-hint">{hint}</div>}
    </div>
  );
}

/**
 * Diegetic system / infrastructure status. AI is shown as deliberately
 * unavailable in this build (no fake output is generated).
 */
export default function SystemStatusPanel({ status }: { status: SystemStatus }) {
  return (
    <section className="cd-panel">
      <header className="cd-panel-head">
        <h2>System Status</h2>
        <span className="cd-verified">Continuity Desk · Local Node</span>
      </header>
      <Meter label="Power" value={status.power} hint="Grid + standby generation" />
      <Meter label="Comms" value={status.comms} hint="Uplink integrity" />
      <Meter label="Data Freshness" value={status.data_freshness} hint="Feed verification lag" />
      <Meter label="Staff Capacity" value={status.staff_capacity} hint="Operations floor coverage" />
      <div className="cd-ai-status cd-ai-off">
        <span className="cd-ai-dot" aria-hidden />
        <span className="cd-ai-text">{status.model_status}</span>
      </div>
    </section>
  );
}
