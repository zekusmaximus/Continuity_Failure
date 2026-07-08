interface Props {
  onBegin: () => void;
  loading: boolean;
}

/**
 * Boot / intake screen. Orients the player before any state, factions, or raw
 * game data appear. One task: begin the engagement.
 */
export default function IntroScreen({ onBegin, loading }: Props) {
  return (
    <div className="cd-intro">
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

        <p className="cd-intro-foot">
          Deterministic engine · No AI systems in this build
        </p>
      </div>
    </div>
  );
}
