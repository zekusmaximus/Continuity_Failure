import type { CampaignSummary } from "../api/client";

interface Props {
  summary: CampaignSummary | null;
  loading: boolean;
  submitting: boolean;
  onRestart: () => void;
  onOpenDossier: () => void;
}

/**
 * Continuity Desk masthead: brand, engagement name, turn counter, status, and
 * engagement-level actions.
 */
export default function ContinuityHeader({
  summary,
  loading,
  submitting,
  onRestart,
  onOpenDossier,
}: Props) {
  const turn = summary
    ? `${Math.min(summary.turn_number, summary.max_turns)} / ${summary.max_turns}`
    : "— / —";
  const status = summary?.status ?? "INIT";

  return (
    <header className="cd-header">
      <div className="cd-header-brand">
        <div className="cd-brand-mark" aria-hidden>◆</div>
        <div>
          <div className="cd-brand">CONTINUITY DESK</div>
          <div className="cd-brand-sub">Crisis-Governance Consulting Workstation</div>
        </div>
      </div>

      <div className="cd-header-engagement">
        <div className="cd-engagement-name">
          {summary ? summary.name : "Initializing engagement…"}
        </div>
        <div className="cd-engagement-meta">
          <span className="cd-turn">TURN {turn}</span>
          <span className={`cd-status cd-status-${status.toLowerCase()}`}>{status}</span>
        </div>
      </div>

      <div className="cd-header-actions">
        <button
          className="cd-btn cd-btn-ghost"
          onClick={onOpenDossier}
          disabled={!summary}
          title="Compile the campaign dossier"
        >
          Campaign Dossier
        </button>
        <button
          className="cd-btn cd-btn-ghost"
          onClick={onRestart}
          disabled={loading || submitting}
        >
          {loading ? "Starting…" : "New Engagement"}
        </button>
      </div>
    </header>
  );
}
