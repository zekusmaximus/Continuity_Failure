import type { RecentCampaign, ScenarioVariant } from "../api/client";

interface Props {
  onBegin: () => void;
  onResume: (campaignId: string) => void;
  recentCampaigns: RecentCampaign[];
  loading: boolean;
  variants?: ScenarioVariant[];
  selectedVariant?: string;
  onVariantChange?: (variantId: string) => void;
  /** Local presentation hint (Wave 3 C3): a completed engagement makes the
   * alternate conditions more prominent. Grants nothing; may be absent. */
  completedBefore?: boolean;
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
  variants = [],
  selectedVariant = "",
  onVariantChange,
  completedBefore = false,
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
          <p>
            Reaching the end is not winning. The final dossier grades what
            kind of institution survived — and what the consultant became in
            the process.
          </p>
        </div>

        <div className="cd-intro-engagement">
          <span className="cd-intro-engagement-k">Current Engagement</span>
          <span className="cd-intro-engagement-v">Northbridge Water Failure</span>
        </div>

        {variants.length > 0 && (
          // Wave 3 C3: baseline is the clear first-run recommendation; the
          // authored variants sit beneath it as alternate intake conditions.
          // Framing only — every variant remains available from the start.
          <fieldset className="cd-intro-variant">
            <legend className="cd-intro-variant-label">Opening conditions</legend>
            <label className="cd-intro-baseline">
              <input
                type="radio"
                name="intro-variant"
                value=""
                checked={selectedVariant === ""}
                onChange={() => onVariantChange?.("")}
                disabled={loading}
              />
              <span>
                <strong>Baseline engagement</strong> — recommended first case
                <small>
                  The Northbridge water crisis as authored: the town as the
                  record first describes it.
                </small>
              </span>
            </label>
            <details className="cd-intro-alternates" open={completedBefore || selectedVariant !== ""}>
              <summary>Alternate intake conditions</summary>
              {variants.map((variant) => (
                <label key={variant.id} className="cd-intro-alternate">
                  <input
                    type="radio"
                    name="intro-variant"
                    value={variant.id}
                    checked={selectedVariant === variant.id}
                    onChange={() => onVariantChange?.(variant.id)}
                    disabled={loading}
                  />
                  <span>
                    <strong>{variant.name}</strong>
                    <small>{variant.description}</small>
                  </span>
                </label>
              ))}
            </details>
          </fieldset>
        )}

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
