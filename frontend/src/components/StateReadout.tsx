import { useMemo } from "react";
import type { WorldState } from "../api/client";
import {
  VARIABLE_META,
  VARIABLE_ORDER,
  GROUP_ORDER,
  effectiveLevel,
  levelClass,
} from "../domain";

/** Compact operational state readout of the 16 world-state variables. */
export default function StateReadout({ state }: { state: WorldState }) {
  const groups = useMemo(() => {
    const byGroup: Record<string, { key: string; value: number; meta: typeof VARIABLE_META[string] }[]> = {};
    for (const key of VARIABLE_ORDER) {
      const meta = VARIABLE_META[key];
      const value = state.variables[key];
      if (value === undefined) continue;
      (byGroup[meta.group] ||= []).push({ key, value, meta });
    }
    return GROUP_ORDER.map((g) => ({ group: g, items: byGroup[g] || [] })).filter(
      (g) => g.items.length > 0,
    );
  }, [state]);

  return (
    <section className="cd-panel cd-state-readout">
      <header className="cd-panel-head">
        <h2>Operational State Readout</h2>
        <span className="cd-verified">{state.last_verified}</span>
      </header>
      <div className="cd-state-grid">
        {groups.map(({ group, items }) => (
          <div key={group} className="cd-state-group">
            <div className="cd-state-group-title">{group}</div>
            <ul className="cd-var-list">
              {items.map(({ key, value, meta }) => {
                const level = effectiveLevel(value, meta.risk);
                return (
                  <li key={key} className="cd-var-row">
                    <span className="cd-var-label">
                      <span>{meta.label}</span>
                      <span className="cd-var-direction">
                        {meta.risk ? "↑ worse" : "↑ better"}
                      </span>
                    </span>
                    <span
                      className="cd-var-bar"
                      role="progressbar"
                      aria-label={meta.label}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-valuenow={value}
                      aria-valuetext={`${value} of 100. ${meta.risk ? "Higher is worse" : "Higher is better"}.`}
                    >
                      <span className={`cd-var-fill ${levelClass(level)}`} style={{ width: `${value}%` }} />
                    </span>
                    <span className={`cd-var-value ${levelClass(level)}`}>{value}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}
