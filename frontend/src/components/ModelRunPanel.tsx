import { useEffect, useState } from "react";
import type { ModelRun } from "../api/client";
import { api } from "../api/client";

interface Props {
  campaignId: string | null;
}

const STATUS_LABEL: Record<string, string> = {
  ok: "validated",
  invalid: "invalid → fallback",
  fallback: "fallback",
  error: "error → fallback",
};

const STATUS_CLASS: Record<string, string> = {
  ok: "cd-run-ok",
  invalid: "cd-run-warn",
  fallback: "cd-run-system",
  error: "cd-run-warn",
};

/**
 * Read-only inspector of AI model runs recorded for this campaign. Surfaced in
 * the Case File so the AI layer stays inspectable: every call (success,
 * validation failure, or deterministic fallback) produces exactly one logged
 * run. With AI off (the default) all runs show as "fallback / disabled".
 */
export default function ModelRunPanel({ campaignId }: Props) {
  const [runs, setRuns] = useState<ModelRun[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!campaignId) return;
    let cancelled = false;
    api
      .getModelRuns(campaignId)
      .then((r) => !cancelled && setRuns(r))
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : String(e)));
    return () => {
      cancelled = true;
    };
  }, [campaignId]);

  if (!campaignId) return <p className="cd-muted">No engagement loaded.</p>;
  if (error) return <p className="cd-muted">Could not load model runs: {error}</p>;
  if (!runs) return <p className="cd-muted">Loading model runs…</p>;
  if (runs.length === 0)
    return (
      <p className="cd-muted">
        No AI runs logged yet. The memo drafter is off by default and returns a
        deterministic fallback unless a live provider is configured.
      </p>
    );

  return (
    <div className="cd-runs">
      <table className="cd-table">
        <thead>
          <tr>
            <th>Turn</th>
            <th>Prompt</th>
            <th>Model</th>
            <th>Status</th>
            <th>Retries</th>
            <th>Latency</th>
            <th>Input</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r, i) => (
            <tr key={i}>
              <td>{r.turn_number ?? "—"}</td>
              <td>
                {r.prompt_name}
                <span className="cd-muted"> .{r.prompt_version}</span>
              </td>
              <td>{r.model_name}</td>
              <td>
                <span className={`cd-run-tag ${STATUS_CLASS[r.validation_status] ?? ""}`}>
                  {STATUS_LABEL[r.validation_status] ?? r.validation_status}
                </span>
              </td>
              <td>{r.retry_count}</td>
              <td>{r.latency_ms != null ? `${r.latency_ms}ms` : "—"}</td>
              <td className="cd-muted cd-run-input">{r.input_summary || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
