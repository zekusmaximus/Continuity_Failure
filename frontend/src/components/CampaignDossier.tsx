import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Dossier } from "../api/client";

interface Props {
  campaignId: string | null;
  /** Compact rendering for the Case File tab (skips the eyebrow header). */
  embedded?: boolean;
}

/**
 * Campaign dossier viewer. Fetches the Markdown case file and offers copy /
 * download. Rendered inline both as the DOSSIER phase and inside the Case File
 * → Dossier tab, so it never dominates the normal turn flow.
 */
export default function CampaignDossier({ campaignId, embedded }: Props) {
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!campaignId) return;
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
  }, [campaignId]);

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

  return (
    <div className={embedded ? "cd-dossier-embed" : "cd-stage-panel cd-dossier"}>
      {!embedded && (
        <h1 className="cd-eyebrow">
          <span className="cd-eyebrow-dot" aria-hidden />
          Campaign dossier {dossier ? `· ${dossier.status}` : ""}
        </h1>
      )}

      {error && <div className="cd-alert cd-alert-error" role="alert">System alert: {error}</div>}

      <div className="cd-dossier-actions">
        <button className="cd-btn cd-btn-ghost cd-btn-sm" onClick={copy} disabled={loading || !dossier}>
          {copied ? "Copied" : "Copy as Markdown"}
        </button>
        <button className="cd-btn cd-btn-ghost cd-btn-sm" onClick={download} disabled={loading || !dossier}>
          Download .md
        </button>
      </div>

      {loading ? (
        <p className="cd-muted" role="status">Compiling case file…</p>
      ) : dossier ? (
        <pre className="cd-dossier-md">{dossier.markdown}</pre>
      ) : (
        <p className="cd-muted">No dossier available.</p>
      )}
    </div>
  );
}
