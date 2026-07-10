import AccessibleDialog from "./AccessibleDialog";

export const ONBOARDING_STORAGE_KEY = "continuity-failure.desk-guide.v1";

interface Props {
  open: boolean;
  firstRun: boolean;
  onClose: () => void;
}

/** A compact, diegetic orientation brief with progressive definitions. */
export default function DeskGuide({ open, firstRun, onClose }: Props) {
  return (
    <AccessibleDialog
      open={open}
      onClose={onClose}
      titleId="cd-desk-guide-title"
      overlayClassName="cd-modal-overlay"
      className="cd-modal cd-guide"
    >
      <div className="cd-modal-head">
        <div>
          <span className="cd-doc-type">Consultant orientation · controlled copy</span>
          <h2 id="cd-desk-guide-title">Desk operating brief</h2>
          <span className="cd-verified">Northbridge engagement protocol</span>
        </div>
        <button
          className="cd-btn cd-btn-ghost cd-modal-close"
          onClick={onClose}
          aria-label="Close desk guide"
        >
          ✕
        </button>
      </div>

      <div className="cd-modal-body cd-guide-body">
        {firstRun && (
          <p className="cd-lead">
            You advise from inside the machinery. Northbridge officials decide
            what is actually done—and the record preserves the difference.
          </p>
        )}

        <ol className="cd-guide-summary">
          <li><strong>Read direction, not color alone.</strong> Some high values are capacity; others are risk.</li>
          <li><strong>Read the record before the recommendation.</strong> Turn, source, reliability, and public status qualify every document.</li>
          <li><strong>Send Advice resolves the turn.</strong> Later phases reveal that result; Next Call only loads the next authoritative call.</li>
        </ol>

        <div className="cd-guide-definitions">
          <details>
            <summary>Authority, adherence, and rejection</summary>
            <p>
              Your recommendation is advisory. The client may follow, modify,
              delay, or reject it. Adherence is the share of the advice effects
              the client actually carries into the deterministic resolution;
              client modifications are recorded separately.
            </p>
          </details>
          <details>
            <summary>Indicators, thresholds, and ambient drift</summary>
            <p>
              “↑ better” marks capacity; “↑ risk” or “↑ worse” marks exposure.
              Higher is not always better. The engagement fails if Water
              Security, Hospital Stability, or Public Order reach 10 or below;
              Public Trust reaches 5 or below; Budget Capacity reaches 0; or
              Legal Exposure or State Oversight Risk reaches 95 or above.
            </p>
            <p>
              Ambient crisis pressure is applied every resolved turn whether or
              not your advice addressed it. The consequence record labels that
              movement as Drift so it is not mistaken for your recommendation.
            </p>
          </details>
          <details>
            <summary>Evidence freshness and reliability</summary>
            <p>
              A document’s turn number is its freshness marker. Its source and
              reliability describe how much weight it can bear; public status
              describes who may already know it. Old, contested, leaked, and
              private records remain evidence, but not equivalent evidence.
            </p>
          </details>
          <details>
            <summary>Turn resolution and Next Call</summary>
            <p>
              Send Advice commits one deterministic turn. Client Decision,
              Consequences, and Archive progressively disclose that same stored
              result. Next Call performs no new decision and changes no state;
              it loads the next call package only after the current record closes.
            </p>
          </details>
        </div>

        <div className="cd-guide-actions">
          <button className="cd-btn cd-btn-primary" onClick={onClose}>
            {firstRun ? "Acknowledge briefing" : "Return to desk"}
          </button>
        </div>
      </div>
    </AccessibleDialog>
  );
}
