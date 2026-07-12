import { useRef, type KeyboardEvent } from "react";
import type { CampaignSummary, WorldState } from "../api/client";
import type { Phase, ReviewMode } from "../domain";
import { PHASE_LABEL, TURN_STEPS, STEP_SHORT } from "../domain";
import KeyStateIndicators from "./KeyStateIndicators";

interface Props {
  summary: CampaignSummary | null;
  worldState: WorldState | null;
  phase: Phase;
  maxReachedIndex: number;
  // The active turn spine: guided or expedited (Wave 3 C2). Defaults to the
  // guided steps so existing callers/tests are unchanged.
  steps?: Phase[];
  reviewMode?: ReviewMode;
  onGoto: (phase: Phase) => void;
  onOpenCaseFile: () => void;
  onOpenGuide: () => void;
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
  maxReachedIndex,
  steps = TURN_STEPS,
  reviewMode = "guided",
  onGoto,
  onOpenCaseFile,
  onOpenGuide,
  onRestart,
  busy,
}: Props) {
  const turn = summary
    ? `${Math.min(summary.turn_number, summary.max_turns)} / ${summary.max_turns}`
    : "— / —";
  const status = summary?.status ?? "INIT";
  const activeIndex = steps.indexOf(phase);
  const stepRefs = useRef<Array<HTMLButtonElement | null>>([]);

  const moveStep = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const enabled = steps.map((_, i) => i).filter((i) => i <= maxReachedIndex);
    if (enabled.length === 0) return;
    const position = enabled.indexOf(index);
    let nextPosition = position;
    if (event.key === "ArrowRight") nextPosition = (position + 1) % enabled.length;
    else if (event.key === "ArrowLeft") nextPosition = (position - 1 + enabled.length) % enabled.length;
    else if (event.key === "Home") nextPosition = 0;
    else if (event.key === "End") nextPosition = enabled.length - 1;
    else return;
    event.preventDefault();
    const next = enabled[nextPosition];
    onGoto(steps[next]);
    stepRefs.current[next]?.focus();
  };

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
            onClick={onOpenGuide}
            title="Reopen the desk operating brief"
          >
            Desk Guide
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
        <div
          className="cd-stepper"
          role="tablist"
          aria-label={`Turn phases · ${reviewMode} review`}
        >
          {steps.map((step, i) => {
            const state =
              i < maxReachedIndex ? "done" : i === activeIndex ? "active" : "todo";
            const disabled = i > maxReachedIndex;
            return (
              <button
                key={step}
                ref={(node) => { stepRefs.current[i] = node; }}
                id={`cd-phase-tab-${step.toLowerCase()}`}
                className={`cd-step cd-step-${state}`}
                role="tab"
                aria-selected={i === activeIndex}
                aria-current={i === activeIndex ? "step" : undefined}
                aria-controls="main-content"
                aria-disabled={disabled}
                disabled={disabled}
                tabIndex={i === activeIndex || (activeIndex < 0 && i === maxReachedIndex) ? 0 : -1}
                onClick={() => onGoto(step)}
                onKeyDown={(event) => moveStep(event, i)}
              >
                  <span className="cd-step-dot" aria-hidden />
                  <span className="cd-step-label">{STEP_SHORT[step]}</span>
                  <span className="cd-sr-only">
                    {disabled ? ", unavailable" : i === activeIndex ? ", current phase" : ", available"}
                  </span>
              </button>
            );
          })}
        </div>
        <KeyStateIndicators state={worldState} />
      </div>
    </header>
  );
}
