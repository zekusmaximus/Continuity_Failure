import { useEffect, useRef, type ReactNode } from "react";
import AccessibleDialog from "./AccessibleDialog";
import { useTelemetry } from "../telemetry/TelemetryProvider";

export const ONBOARDING_STORAGE_KEY = "continuity-failure.desk-guide.v1";

interface Props {
  open: boolean;
  firstRun: boolean;
  onClose: () => void;
}

/** A compact, diegetic orientation brief with progressive definitions. */
export default function DeskGuide({ open, firstRun, onClose }: Props) {
  const { report } = useTelemetry();

  // One event per guide opening. The ref survives StrictMode's double
  // effect run, so re-running with the guide still open emits nothing.
  const reportedShown = useRef(false);
  useEffect(() => {
    if (!open) {
      reportedShown.current = false;
      return;
    }
    if (reportedShown.current) return;
    reportedShown.current = true;
    report({ event_type: "guide_topic_shown", topic_id: "desk_operating_brief" });
  }, [open, report]);

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
        {firstRun ? (
          // Wave 3 C1: a new player gets three promises, not a manual. Every
          // threshold, citation, thread, ledger, and degradation rule teaches
          // itself beside its object when it first matters; the complete
          // operating brief stays one click away under Help.
          <>
            <p className="cd-lead">
              You advise from inside the machinery. Northbridge officials decide
              what is actually done—and the record preserves the difference.
            </p>
            <ol className="cd-guide-summary cd-guide-promises">
              <li><strong>You recommend; the client decides.</strong></li>
              <li><strong>Every resolved turn changes state and the record.</strong></li>
              <li><strong>The desk will show exactly why.</strong></li>
            </ol>
            <p className="cd-muted">
              The desk explains everything else — evidence weight, adherence,
              threads, precedents, degraded feeds — beside the real thing, the
              first time it matters. The complete operating brief stays
              available from Help at any point.
            </p>
          </>
        ) : (
          <FullGuideBody />
        )}

        <div className="cd-guide-actions">
          <button className="cd-btn cd-btn-primary" onClick={onClose}>
            {firstRun ? "Acknowledge briefing" : "Return to desk"}
          </button>
        </div>
      </div>
    </AccessibleDialog>
  );
}

/** The complete operating brief, reachable from Help after the first run. */
function FullGuideBody() {
  const { report } = useTelemetry();

  const topic = (topicId: string, summary: string, body: ReactNode) => (
    <details
      onToggle={(event) => {
        if (event.currentTarget.open) {
          report({ event_type: "guide_topic_opened", topic_id: topicId });
        }
      }}
    >
      <summary>{summary}</summary>
      {body}
    </details>
  );

  return (
    <>
        <ol className="cd-guide-summary">
          <li><strong>Read direction, not color alone.</strong> Some high values are capacity; others are risk.</li>
          <li><strong>Read the record before the recommendation.</strong> Turn, source, reliability, and public status qualify every document.</li>
          <li><strong>Send Advice resolves the turn.</strong> Later phases reveal that result; Next Call only loads the next authoritative call.</li>
        </ol>

        <div className="cd-guide-definitions">
          {topic(
            "adherence",
            "Authority, adherence, and rejection",
            <p>
              Your recommendation is advisory. The client may follow, modify,
              delay, or reject it. Adherence is the share of the advice effects
              the client actually carries into the deterministic resolution;
              client modifications are recorded separately.
            </p>,
          )}
          {topic(
            "thresholds_drift",
            "Indicators, thresholds, and ambient drift",
            <>
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
            </>,
          )}
          {topic(
            "evidence_freshness",
            "Evidence freshness and reliability",
            <p>
              A document’s turn number is its freshness marker. Its source and
              reliability describe how much weight it can bear; public status
              describes who may already know it. Old, contested, leaked, and
              private records remain evidence, but not equivalent evidence.
            </p>,
          )}
          {topic(
            "turn_resolution",
            "Turn resolution and Next Call",
            <p>
              Send Advice commits one deterministic turn. Client Decision,
              Consequences, and Archive progressively disclose that same stored
              result. Next Call performs no new decision and changes no state;
              it loads the next call package only after the current record closes.
            </p>,
          )}
        </div>
    </>
  );
}
