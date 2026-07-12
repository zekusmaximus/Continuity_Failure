import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { CampaignSummary, OutcomeAssessment, TurnHistory } from "../api/client";

interface Props {
  campaignId: string | null;
  summary: CampaignSummary | null;
  history: TurnHistory | null;
  onReopenIntake: () => void;
}

/**
 * Terminal replay invitation — Wave 3 C3.
 *
 * Shown after the dossier on a terminal campaign: the completed
 * variant/ruleset, the verdict and its weakest axis (already computed in the
 * assessment), and one unresolved thread or future hook already on the
 * record. The action returns to intake with an alternate variant preselected
 * — it creates nothing; only an explicit Begin Intake starts a new campaign.
 * This is framing for a deliberate second run, not a locked progression
 * system and not a counterfactual simulation.
 */
export default function ReplayInvitation({
  campaignId,
  summary,
  history,
  onReopenIntake,
}: Props) {
  const [assessment, setAssessment] = useState<OutcomeAssessment | null>(null);

  const terminal =
    summary?.status === "COMPLETED" || summary?.status === "FAILED";

  useEffect(() => {
    if (!campaignId || !terminal) return;
    let cancelled = false;
    void api
      .getDossier(campaignId)
      .then((dossier) => {
        if (!cancelled) setAssessment(dossier.assessment);
      })
      .catch(() => {
        // The invitation renders without the verdict rather than blocking.
      });
    return () => {
      cancelled = true;
    };
  }, [campaignId, terminal]);

  if (!summary || !terminal) return null;

  const weakest =
    assessment && assessment.axes.length > 0
      ? assessment.axes.reduce((low, axis) => (axis.score < low.score ? axis : low))
      : null;

  // One forward-looking fact already on the record: the first unresolved
  // thread, else the final turn's recorded future hook.
  const unresolvedThread = (history?.open_threads ?? []).find(
    (thread) => thread.status !== "resolved",
  );
  const lastTurn = history?.turns[history.turns.length - 1];
  const openQuestion = unresolvedThread
    ? `Still open on the record: ${unresolvedThread.title}.`
    : lastTurn?.consequence_lead.future_hook || "";

  return (
    <section className="cd-replay-invitation" aria-labelledby="cd-replay-title">
      <h2 id="cd-replay-title" className="cd-subhead">
        The record is closed. The conditions are not the only ones.
      </h2>
      <dl className="cd-replay-facts">
        <div>
          <dt>Completed under</dt>
          <dd>
            {summary.variant_id ? summary.variant_id : "baseline"} · ruleset{" "}
            {summary.ruleset_version}
          </dd>
        </div>
        {assessment && (
          <div>
            <dt>Verdict</dt>
            <dd>{assessment.verdict_title}</dd>
          </div>
        )}
        {weakest && (
          <div>
            <dt>Weakest axis</dt>
            <dd>
              {weakest.label} — {weakest.score}/100 ({weakest.band})
            </dd>
          </div>
        )}
      </dl>
      {openQuestion && <p className="cd-muted">{openQuestion}</p>}
      <button className="cd-btn cd-btn-ghost" onClick={onReopenIntake}>
        Reopen intake with alternate conditions
      </button>
      <p className="cd-muted cd-small">
        Returns to intake with an alternate opening preselected. No campaign is
        created until you choose Begin Intake.
      </p>
    </section>
  );
}
