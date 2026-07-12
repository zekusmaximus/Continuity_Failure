import type { CurrentTurn, PowerAllocation } from "../api/client";
import CallPhase from "./CallPhase";
import BriefPhase from "./BriefPhase";
import EvidencePhase from "./EvidencePhase";

interface Props {
  current: CurrentTurn;
  onOpenCaseFile: () => void;
  /** Absent when the turn is already resolved (read-only review). */
  onCommitPower?: (allocation: PowerAllocation) => void;
  busy?: boolean;
}

/**
 * REVIEW phase — expedited review (Wave 3 C2).
 *
 * One screen composing the exact same current-turn package the guided loop
 * spreads across Call, Brief, and Evidence: the incoming call with its
 * auxiliary-power commitment panel, the caller's disposition, the situation
 * brief, and the full prioritized evidence board with Case File access. It
 * renders the same components against the same payload — nothing smaller is
 * fetched, no document is marked read, and no resolution behavior changes.
 */
export default function ReviewPhase({
  current,
  onOpenCaseFile,
  onCommitPower,
  busy = false,
}: Props) {
  const call = current.client_call;
  return (
    <div className="cd-review-phase">
      <p className="cd-muted cd-review-note">
        Expedited review · the complete call package on one screen. Advice,
        decision, and consequences proceed exactly as in the guided loop.
      </p>
      <CallPhase
        call={call}
        disposition={current.caller_disposition}
        systemStatus={current.system_status}
        onCommitPower={onCommitPower}
        busy={busy}
      />
      {call && <BriefPhase call={call} state={current.world_state} />}
      {call && (
        <EvidencePhase
          documents={current.documents}
          call={call}
          onOpenCaseFile={onOpenCaseFile}
          turnNumber={current.summary.turn_number}
        />
      )}
    </div>
  );
}
