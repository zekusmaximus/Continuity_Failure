import type { AppliedDiff } from "../api/client";
import { VARIABLE_META, SOURCE_LABEL } from "../domain";

function diffColor(delta: number, risk: boolean): string {
  if (delta === 0) return "neutral";
  const good = risk ? delta < 0 : delta > 0;
  return good ? "good" : "bad";
}

export default function AppliedDiffList({ diffs }: { diffs: AppliedDiff[] }) {
  const ordered = [...diffs].sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
  return (
    <div className="cd-diff-block">
      <div className="cd-subhead">Applied State Diffs</div>
      {ordered.length === 0 ? (
        <p className="cd-muted cd-small">No state changes recorded.</p>
      ) : (
        <ul className="cd-diff-list">
          {ordered.map((d, i) => {
            const meta = VARIABLE_META[d.variable];
            const color = diffColor(d.delta, meta?.risk ?? false);
            const sign = d.delta > 0 ? "+" : "";
            return (
              <li key={i} className={`cd-diff-row cd-src-${d.source_type}`}>
                <span className="cd-diff-var">{meta?.label ?? d.variable}</span>
                <span className="cd-diff-move">{d.old_value} → {d.new_value}</span>
                <span className={`cd-diff-delta cd-delta-${color}`}>{sign}{d.delta}</span>
                <span className="cd-diff-source">{SOURCE_LABEL[d.source_type] ?? d.source_type}</span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
