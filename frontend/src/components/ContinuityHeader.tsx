import type { CampaignSummary, WorldState } from "../api/client";
import type { Phase } from "../domain";
import { PHASE_LABEL, TURN_STEPS, STEP_SHORT } from "../domain";
import KeyStateIndicators from "./KeyStateIndicators";

interface Props {
  summary: CampaignSummary | null;
  worldState: WorldState | null;
  phase: Phase;
  onOpenCaseFile: () => void;
  onRestart: () => void;
  busy: boolean;
}

/**
 * Guided-mode masthead: engagement identity, turn counter, the current phase in
 * the turn spine, the four key indicators, and access to the Case File. Dense
 * data deliberately does not live here.
 */
export default function ContinuityHeader({
  summary,
  worldState,
  phase,
  onOpenCaseFile,
  onRestart,
  busy,
}: Props) {
  const turn = summary
    ? `${Math.min(summary.turn_number, summary.max_turns)} / ${summary.max_turns}`
    : "— / —";
  const status = summary?.status ?? "INIT";
  const activeIndex = TURN_STEPS.indexOf(phase);

  return (
    <header className="cd-header">
      <div className="cd-header-top">
        <div className="cd-header-brand">
          <span className="cd-brand-mark" aria-hidden>◆</span>
          <span className="cd-brand">CONTINUITY DESK</span>
          <span className="cd-header-engagement">
            {summary ? summary.name : "Northbridge Water Failure"}
          </span>
        </div>

        <div className="cd-header-meta">
          <span className="cd-turn">TURN {turn}</span>
          <span className={`cd-status cd-status-${status.toLowerCase()}`}>{status}</span>
          <span className="cd-phase-now">{PHASE_LABEL[phase]}</span>
          <button
            className="cd-btn cd-btn-ghost cd-btn-sm"
            onClick={onOpenCaseFile}
            disabled={!summary}
            title="Open the full case file (evidence, factions, state, canon, timeline, dossier)"
          >
            Case File
          </button>
          <button
            className="cd-btn cd-btn-ghost cd-btn-sm"
            onClick={onRestart}
            disabled={busy}
            title="Start a new engagement"
          >
            New Engagement
          </button>
        </div>
      </div>

      <div className="cd-header-bottom">
        <ol className="cd-stepper" aria-label="Turn progress">
          {TURN_STEPS.map((step, i) => {
            const state =
              i < activeIndex ? "done" : i === activeIndex ? "active" : "todo";
            return (
              <li key={step} className={`cd-step cd-step-${state}`}>
                <span className="cd-step-dot" aria-hidden />
                <span className="cd-step-label">{STEP_SHORT[step]}</span>
              </li>
            );
          })}
        </ol>
        <KeyStateIndicators state={worldState} />
      </div>
    </header>
  );
}
