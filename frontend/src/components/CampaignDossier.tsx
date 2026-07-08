import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Dossier } from "../api/client";

interface Props {
  campaignId: string | null;
  open: boolean;
  onClose: () => void;
}

export default function CampaignDossier({ campaignId, open, onClose }: Props) {
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!open || !campaignId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .getDossier(campaignId)
      .then((d) => {
        if (!cancelled) setDossier(d);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, campaignId]);

  const copy = async () => {
    if (!dossier) return;
    try {
      await navigator.clipboard.writeText(dossier.markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setError("Clipboard unavailable in this browser.");
    }
  };

  const download = () => {
    if (!dossier) return;
    const blob = new Blob([dossier.markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = dossier.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (!open) return null;

  return (
    <div className="cd-modal-overlay" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="cd-modal" onClick={(e) => e.stopPropagation()}>
        <header className="cd-modal-head">
          <div>
            <h2>Campaign Dossier</h2>
            <span className="cd-verified">
              {dossier ? `${dossier.name} · ${dossier.status}` : "Compiling…"}
            </span>
          </div>
          <button className="cd-btn cd-btn-ghost cd-modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </header>

        {error && <div className="cd-alert cd-alert-error">System alert: {error}</div>}

        <div className="cd-modal-actions">
          <button className="cd-btn cd-btn-ghost" onClick={copy} disabled={loading || !dossier}>
            {copied ? "Copied" : "Copy as Markdown"}
          </button>
          <button className="cd-btn cd-btn-ghost" onClick={download} disabled={loading || !dossier}>
            Download .md
          </button>
        </div>

        <div className="cd-modal-body">
          {loading ? (
            <p className="cd-muted">Compiling case file…</p>
          ) : dossier ? (
            <pre className="cd-dossier-md">{dossier.markdown}</pre>
          ) : (
            <p className="cd-muted">No dossier available.</p>
          )}
        </div>
      </div>
    </div>
  );
}
