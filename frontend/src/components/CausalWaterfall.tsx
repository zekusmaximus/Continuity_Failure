import type {
  AdviceMediation,
  TurnResult,
  VariableConsequence,
} from "../api/client";
import {
  CAUSAL_SOURCE_LABEL,
  DECISION_BADGE,
  deltaAssessment,
  signed,
  titleCase,
} from "../domain";

/**
 * The causal waterfall: for every affected variable, the authoritative
 * start → attributed deltas → final reconciliation from the server's
 * ConsequenceReport. Nothing here is recomputed — the component only formats
 * the engine's own record. Direction, source, and outcome are all carried as
 * text (signed values, "improved/worsened", source labels), so the display
 * stays meaningful without color or motion.
 */

function mediationText(med: AdviceMediation): string {
  const pct = Math.round(med.adherence * 100);
  const clampNote = med.clamped ? " — capped at the 0–100 bound" : "";
  switch (med.outcome) {
    case "applied":
      return `You proposed ${signed(med.proposed_delta)}; applied in full.`;
    case "rejected":
      return `You proposed ${signed(med.proposed_delta)}; the client rejected it — no effect applied.`;
    case "delayed":
      return `You proposed ${signed(med.proposed_delta)}; the client deferred it — no effect this turn.`;
    default:
      return (
        `You proposed ${signed(med.proposed_delta)}; the client applied ` +
        `${signed(med.applied_delta)} at ${pct}% adherence${clampNote}.`
      );
  }
}

function VariableBlock({
  entry,
  maxAbsDelta,
}: {
  entry: VariableConsequence;
  maxAbsDelta: number;
}) {
  const risk = entry.direction === "higher_is_worse";
  const unchanged = entry.net_delta === 0;
  const assessment = unchanged ? null : deltaAssessment(entry.net_delta, risk);
  const med = entry.advice;

  return (
    <li className="cd-causal-var">
      <div className="cd-causal-head">
        <span className="cd-causal-label">{entry.label}</span>
        <span className="cd-causal-dir">
          {risk ? "higher is worse" : "higher is better"}
        </span>
        <span className="cd-causal-net">
          <span className="cd-causal-move">
            {entry.start_value} <span aria-hidden>→</span>
            <span className="cd-sr-only"> to </span> {entry.final_value}
          </span>
          {unchanged ? (
            <span className="cd-causal-verdict cd-delta-neutral">no net change</span>
          ) : (
            <span
              className={`cd-causal-verdict ${
                assessment === "improved" ? "cd-delta-good" : "cd-delta-bad"
              }`}
            >
              <span aria-hidden>{entry.net_delta > 0 ? "▲" : "▼"} </span>
              {signed(entry.net_delta)} {assessment}
            </span>
          )}
        </span>
      </div>

      {entry.deltas.length > 0 && (
        <ol className="cd-causal-steps">
          {entry.deltas.map((d, i) => {
            const width =
              maxAbsDelta > 0
                ? Math.max(8, Math.round((Math.abs(d.delta) / maxAbsDelta) * 100))
                : 0;
            const stepGood = deltaAssessment(d.delta, risk) === "improved";
            return (
              <li key={i} className={`cd-causal-step cd-src-${d.source_type}`}>
                <span className="cd-causal-src">
                  {CAUSAL_SOURCE_LABEL[d.source_type] ?? titleCase(d.source_type)}
                </span>
                <span
                  className={`cd-causal-delta ${stepGood ? "cd-delta-good" : "cd-delta-bad"}`}
                >
                  {signed(d.delta)}
                </span>
                <span className="cd-causal-bar" aria-hidden>
                  <span
                    className={`cd-causal-bar-fill ${stepGood ? "fill-good" : "fill-bad"}`}
                    style={{ width: `${width}%` }}
                  />
                </span>
                <span className="cd-causal-running">
                  <span className="cd-sr-only">running value </span>→ {d.value_after}
                </span>
                <span className="cd-causal-reason">{d.reason}</span>
              </li>
            );
          })}
        </ol>
      )}

      {med && med.outcome !== "applied" && (
        <p
          className={`cd-causal-mediation ${
            med.outcome === "reduced" ? "cd-mediation-reduced" : "cd-mediation-blocked"
          }`}
        >
          <span className="cd-causal-mediation-k">
            {med.outcome === "reduced" ? "Reduced" : titleCase(med.outcome)}
          </span>{" "}
          {mediationText(med)}
        </p>
      )}
      {med && med.outcome === "applied" && (
        <p className="cd-causal-mediation cd-mediation-applied">
          <span className="cd-causal-mediation-k">As proposed</span> {mediationText(med)}
        </p>
      )}
    </li>
  );
}

const WORKFLOW_LABEL: Record<string, string> = {
  manual: "drafted manually",
  ai_assisted: "AI-assisted draft",
  deterministic_fallback: "standard advisory template",
};

/** Compact "why the client acted" strip with the sent-memo provenance link. */
function DecisionSummary({ result }: { result: TurnResult }) {
  const d = result.decision;
  const memo = result.sent_memo;
  const reason = d.explanation?.outcome_reason || d.rationale;
  return (
    <div className="cd-causal-decision">
      <p className="cd-causal-decision-line">
        <span className={`cd-decision-badge sm ${DECISION_BADGE[d.decision_type] ?? ""}`}>
          {titleCase(d.decision_type)}
        </span>{" "}
        by {d.decider} · adherence {Math.round(d.adherence * 100)}%
        {d.off_brief && (
          <>
            {" "}
            · <span className="cd-advice-flag cd-flag-off">Off-brief</span>
          </>
        )}
      </p>
      {reason && <p className="cd-causal-decision-why">{reason}</p>}
      {memo && (
        <p className="cd-causal-memo-ref">
          Acting on memo of record: {memo.name}, revision {memo.revision} (
          {WORKFLOW_LABEL[memo.provenance.workflow] ?? memo.provenance.workflow}) ·
          SHA-256 {memo.content_digest.slice(0, 12)}…
        </p>
      )}
    </div>
  );
}

export default function CausalWaterfall({ result }: { result: TurnResult }) {
  const report = result.consequence_report;
  const entries = report?.variables ?? [];
  if (entries.length === 0) return null;

  const changedCount = entries.filter((e) => e.net_delta !== 0).length;
  const maxAbsDelta = Math.max(
    1,
    ...entries.flatMap((e) => e.deltas.map((d) => Math.abs(d.delta))),
  );

  return (
    <div className="cd-causal">
      <h2 className="cd-subhead">How the state moved</h2>
      <DecisionSummary result={result} />
      <p className="cd-context-note">
        Turn {result.turn_number} resolved — {changedCount}{" "}
        {changedCount === 1 ? "variable" : "variables"} changed. Each line
        reconciles exactly: starting value, then every attributed change from
        your advice (as the client applied it), the client's own action, any
        decision cost, and ambient drift, down to the final value on record.
      </p>
      <ul className="cd-causal-list">
        {entries.map((e) => (
          <VariableBlock key={e.variable} entry={e} maxAbsDelta={maxAbsDelta} />
        ))}
      </ul>
    </div>
  );
}
