import type { MemoDraft } from "../api/client";

interface Props {
  memo: MemoDraft | null;
  loading: boolean;
  error: string | null;
}

/**
 * Renders an AI- or system-drafted consultant memo for the currently selected
 * advice option. The label is honest about provenance: "AI draft" only when the
 * model produced validated output (status "ok"); otherwise "System draft
 * (deterministic fallback)". The memo is advisory — it never advances the turn
 * or changes state.
 */
export default function MemoDraftPanel({ memo, loading, error }: Props) {
  if (loading) {
    return (
      <div className="cd-memo-panel cd-muted" role="status">
        Drafting memo…
      </div>
    );
  }
  if (error) {
    return (
      <div className="cd-memo-panel cd-alert cd-alert-error" role="alert">
        Memo draft failed: {error}
      </div>
    );
  }
  if (!memo) return null;

  const fromModel = memo.status === "ok" && memo.source === "ai";
  const label = fromModel ? "AI draft" : "System draft (deterministic fallback)";
  const labelClass = fromModel ? "cd-memo-src cd-memo-src-ai" : "cd-memo-src cd-memo-src-system";
  const d = memo.draft;

  return (
    <div className="cd-memo-panel">
      <div className="cd-memo-head">
        <span className="cd-eyebrow-dot" aria-hidden />
        <span className="cd-subhead">Drafted memo</span>
        <span className={labelClass}>{label}</span>
        <span className="cd-muted cd-memo-advisory">advisory only — does not change state</span>
      </div>

      <div className="cd-memo-body">
        <div className="cd-field">
          <div className="cd-field-k">Recommendation</div>
          <div>{d.recommendation}</div>
        </div>
        <div className="cd-field">
          <div className="cd-field-k">Rationale</div>
          <div>{d.rationale}</div>
        </div>
        {d.operational_steps.length > 0 && (
          <div className="cd-field">
            <div className="cd-field-k">Operational steps</div>
            <ul className="cd-memo-list">
              {d.operational_steps.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>
        )}
        <div className="cd-field">
          <div className="cd-field-k">Communications</div>
          <div>{d.communications}</div>
        </div>
        {d.likely_opposition.length > 0 && (
          <div className="cd-field">
            <div className="cd-field-k">Likely opposition</div>
            <ul className="cd-memo-list">
              {d.likely_opposition.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>
        )}
        {d.second_order_risks.length > 0 && (
          <div className="cd-field">
            <div className="cd-field-k">Second-order risks</div>
            <ul className="cd-memo-list cd-bad-list">
              {d.second_order_risks.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>
        )}
        <div className="cd-field">
          <div className="cd-field-k">Fallback plan</div>
          <div>{d.fallback_plan}</div>
        </div>
      </div>
    </div>
  );
}
