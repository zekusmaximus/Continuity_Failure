import { useEffect } from "react";
import type { MemoDraft } from "../api/client";

interface Props {
  open: boolean;
  loading: boolean;
  memo: MemoDraft | null;
  error: string | null;
  /** Title of the advice option the memo was drafted for, for the header. */
  optionTitle: string | null;
  onClose: () => void;
}

/** Provenance badge — honest about whether the AI or the deterministic
 *  fallback produced the draft. With AI off this is always "System draft". */
function ProvenanceBadge({ source }: { source: MemoDraft["source"] }) {
  const isAi = source === "ai";
  return (
    <span className={`cd-memo-badge ${isAi ? "cd-memo-badge-ai" : "cd-memo-badge-system"}`}>
      {isAi ? "AI-assisted" : "System draft"}
    </span>
  );
}

/**
 * Advisory memo overlay. Reuses the document-detail modal shell. It renders a
 * draft consultant memo for the selected advice option WITHOUT sending advice
 * or advancing the turn — the endpoint is read-only. The deterministic engine
 * remains the sole authority over game state.
 */
export default function MemoModal({ open, loading, memo, error, optionTitle, onClose }: Props) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const draft = memo?.draft ?? null;

  return (
    <div className="cd-modal-overlay" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="cd-modal cd-modal-doc" onClick={(e) => e.stopPropagation()}>
        <header className="cd-modal-head">
          <div>
            <span className="cd-doc-type">Advisory Memo · draft only</span>
            <h2>{optionTitle ?? "Consultant Memo"}</h2>
            <span className="cd-verified">
              — advisory only · does not send advice or advance the turn
            </span>
          </div>
          <button className="cd-btn cd-btn-ghost cd-modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </header>

        <div className="cd-modal-body">
          {loading && <p className="cd-muted">Drafting memo…</p>}

          {!loading && error && (
            <div className="cd-alert cd-alert-error">
              <strong>Could not draft memo:</strong> {error}
            </div>
          )}

          {!loading && !error && memo && draft && (
            <>
              <div className="cd-tagrow">
                <ProvenanceBadge source={memo.source} />
              </div>

              <div className="cd-field">
                <div className="cd-field-k">Recommendation</div>
                <p className="cd-field-v">{draft.recommendation}</p>
              </div>

              <div className="cd-field">
                <div className="cd-field-k">Rationale</div>
                <p className="cd-field-v">{draft.rationale}</p>
              </div>

              {draft.operational_steps.length > 0 && (
                <div className="cd-field">
                  <div className="cd-field-k">Operational steps</div>
                  <ol className="cd-memo-steps">
                    {draft.operational_steps.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ol>
                </div>
              )}

              <div className="cd-field">
                <div className="cd-field-k">Communications</div>
                <p className="cd-field-v">{draft.communications}</p>
              </div>

              <div className="cd-advice-cols">
                {draft.likely_opposition.length > 0 && (
                  <div className="cd-advice-col">
                    <div className="cd-subhead cd-subhead-bad">Likely opposition</div>
                    <ul className="cd-advice-list cd-bad-list">
                      {draft.likely_opposition.map((o, i) => (
                        <li key={i}>{o}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {draft.second_order_risks.length > 0 && (
                  <div className="cd-advice-col">
                    <div className="cd-subhead cd-subhead-bad">Second-order risks</div>
                    <ul className="cd-advice-list cd-bad-list">
                      {draft.second_order_risks.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              <div className="cd-field">
                <div className="cd-field-k">Fallback plan</div>
                <p className="cd-field-v">{draft.fallback_plan}</p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
