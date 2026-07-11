import { useCallback, useMemo, useState } from "react";
import type { CampaignSummary } from "../api/client";
import { useTelemetry } from "../telemetry/TelemetryProvider";
import { TELEMETRY_APP_VERSION } from "../telemetry/session";
import {
  buildTelemetryExport,
  clearTelemetryEvents,
  readTelemetryEvents,
} from "../telemetry/store";
import { summarizeTelemetry } from "../telemetry/summary";
import { PHASE_LABEL } from "../domain";

interface Props {
  summary: CampaignSummary | null;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function formatTimestamp(iso: string | null): string {
  if (!iso) return "—";
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? "—" : parsed.toLocaleString();
}

function formatDuration(ms: number): string {
  const seconds = Math.round(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

/**
 * Local playtest data — the player-facing control surface for telemetry.
 *
 * Everything measured stays in this browser. Export happens only on an
 * explicit click; clearing sits behind a confirmation and touches only the
 * telemetry key, never campaigns, preferences, or canon.
 */
export default function TelemetryPanel({ summary }: Props) {
  const { enabled, setEnabled, storage } = useTelemetry();
  const [confirmingClear, setConfirmingClear] = useState(false);
  // Bumped after clear so the readout below recomputes from storage.
  const [generation, setGeneration] = useState(0);

  const events = useMemo(
    () => readTelemetryEvents(storage),
    [storage, generation],
  );
  const digest = useMemo(() => summarizeTelemetry(events), [events]);
  const approxBytes = useMemo(
    () => (events.length > 0 ? JSON.stringify(events).length : 0),
    [events],
  );

  const handleExport = useCallback(() => {
    const payload = buildTelemetryExport(readTelemetryEvents(storage), {
      app_version: TELEMETRY_APP_VERSION,
      ruleset_version: summary?.ruleset_version ?? null,
      variant_id: summary?.variant_id ?? null,
      exported_at: new Date().toISOString(),
    });
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "continuity-failure-playtest.json";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }, [storage, summary]);

  const handleClear = useCallback(() => {
    clearTelemetryEvents(storage);
    setConfirmingClear(false);
    setGeneration((n) => n + 1);
  }, [storage]);

  return (
    <section className="cd-telemetry" aria-labelledby="cd-telemetry-title">
      <h3 id="cd-telemetry-title" className="cd-subhead">Local playtest data</h3>
      <p className="cd-muted">
        This desk can record how you move through a turn — phases visited,
        documents opened, options compared — to improve the game. The data
        stays in this browser: nothing is uploaded, and no memo text, document
        text, or call content is ever recorded. Export happens only when you
        click the export button below.
      </p>

      <label className="cd-telemetry-toggle">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
        />
        <span>Collect local playtest events in this browser</span>
      </label>
      <p className="cd-muted cd-small">
        This switch is stored only in this browser and is never sent anywhere.
      </p>

      <dl className="cd-telemetry-stats">
        <div>
          <dt>Events on record</dt>
          <dd>{digest.event_count}</dd>
        </div>
        <div>
          <dt>First event</dt>
          <dd>{formatTimestamp(events.length > 0 ? events[0].occurred_at : null)}</dd>
        </div>
        <div>
          <dt>Last event</dt>
          <dd>
            {formatTimestamp(
              events.length > 0 ? events[events.length - 1].occurred_at : null,
            )}
          </dd>
        </div>
        <div>
          <dt>Approximate size</dt>
          <dd>{formatBytes(approxBytes)}</dd>
        </div>
      </dl>

      {digest.event_count > 0 && (
        <div className="cd-telemetry-summary">
          <h4 className="cd-subhead">Session summary</h4>
          <ul className="cd-telemetry-summary-list">
            {digest.phase_durations.map((row) => (
              <li key={row.phase}>
                {PHASE_LABEL[row.phase]}: {formatDuration(row.total_ms)} across{" "}
                {row.visits} {row.visits === 1 ? "visit" : "visits"}
              </li>
            ))}
            <li>
              Evidence opened:{" "}
              {digest.evidence_opens.reduce((total, row) => total + row.count, 0)}{" "}
              (distinct documents: {digest.evidence_opens.length})
            </li>
            <li>
              Advice selections: {digest.advice_selection_count} (changes after the
              first: {digest.advice_change_count})
            </li>
            <li>
              Strategic alternatives expanded: {digest.alternatives_expanded_count}
            </li>
            <li>
              Case File opens:{" "}
              {digest.case_file_opens.reduce((total, row) => total + row.count, 0)}
            </li>
            <li>Record details expanded: {digest.record_detail_expansions}</li>
            <li>
              Last phase on record:{" "}
              {digest.final_phase ? PHASE_LABEL[digest.final_phase] : "—"}
              {digest.final_turn_number != null
                ? ` (turn ${digest.final_turn_number})`
                : ""}
            </li>
          </ul>
        </div>
      )}

      <div className="cd-telemetry-actions">
        <button
          className="cd-btn cd-btn-ghost"
          onClick={handleExport}
          disabled={digest.event_count === 0}
        >
          Export JSON
        </button>
        {confirmingClear ? (
          <span className="cd-telemetry-confirm" role="alertdialog" aria-label="Confirm clearing playtest data">
            <span>
              Delete {digest.event_count} locally stored playtest{" "}
              {digest.event_count === 1 ? "event" : "events"}? Campaigns,
              preferences, and the canon record are untouched.
            </span>
            <button className="cd-btn cd-btn-ghost" onClick={handleClear}>
              Delete playtest data
            </button>
            <button
              className="cd-btn cd-btn-ghost"
              onClick={() => setConfirmingClear(false)}
            >
              Keep data
            </button>
          </span>
        ) : (
          <button
            className="cd-btn cd-btn-ghost"
            onClick={() => setConfirmingClear(true)}
            disabled={digest.event_count === 0}
          >
            Clear local data
          </button>
        )}
      </div>
    </section>
  );
}
