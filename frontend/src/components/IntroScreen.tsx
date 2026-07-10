import type { RecentCampaign } from "../api/client";

interface Props {
  onBegin: () => void;
  onResume: (campaignId: string) => void;
  recentCampaigns: RecentCampaign[];
  loading: boolean;
}

/**
 * Boot / intake screen. Orients the player before any state, factions, or raw
 * game data appear. One task: begin the engagement.
 */
export default function IntroScreen({
  onBegin,
  onResume,
  recentCampaigns,
  loading,
}: Props) {
  return (
    <main id="main-content" className="cd-intro" tabIndex={-1}>
      <div className="cd-intro-card">
        <div className="cd-intro-mark" aria-hidden>◆</div>
        <h1 className="cd-intro-title">CONTINUITY DESK</h1>
        <p className="cd-intro-sub">Emergency Governance Advisory Platform</p>

        <div className="cd-intro-premise">
          <p>
            <strong>You are not the decision-maker.</strong>
            <br />
            You advise the decision-makers.
          </p>
          <p>
            Clients may follow, alter, delay, leak, or ignore your advice.
            Every recommendation creates a record. Every record can become
            precedent, evidence, or blame.
          </p>
        </div>

        <div className="cd-intro-engagement">
          <span className="cd-intro-engagement-k">Current Engagement</span>
          <span className="cd-intro-engagement-v">Northbridge Water Failure</span>
        </div>

        <button
          className="cd-btn cd-btn-primary cd-intro-begin"
          onClick={onBegin}
          disabled={loading}
        >
          {loading ? "Opening desk…" : "Begin Intake"}
        </button>

        {recentCampaigns.length > 0 && (
          <section className="cd-intro-recent" aria-labelledby="recent-engagements">
            <h2 id="recent-engagements">Recent engagements</h2>
            <div className="cd-intro-recent-list">
              {recentCampaigns.map((campaign) => (
                <button
                  key={campaign.id}
                  className="cd-intro-resume"
                  onClick={() => onResume(campaign.id)}
                  disabled={loading}
                >
                  <span>
                    <strong>{campaign.name}</strong>
                    <small>
                      Turn {Math.min(campaign.turn_number, campaign.max_turns)} of{" "}
                      {campaign.max_turns} · {campaign.status.toLowerCase()}
                    </small>
                  </span>
                  <span className="cd-intro-resume-action">Reopen</span>
                </button>
              ))}
            </div>
          </section>
        )}

        <p className="cd-intro-foot">
          Deterministic engine · Optional AI assist is validation-gated and off by default
        </p>
      </div>
    </main>
  );
}
