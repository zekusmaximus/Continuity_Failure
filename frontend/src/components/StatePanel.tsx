import { useMemo } from "react";
import type { WorldState } from "../api/client";
import {
  VARIABLE_META,
  VARIABLE_ORDER,
  GROUP_ORDER,
  effectiveLevel,
} from "../domain";

function levelClass(level: number): string {
  if (level >= 60) return "lvl-good";
  if (level >= 35) return "lvl-warn";
  return "lvl-crit";
}

export default function StatePanel({ state }: { state: WorldState }) {
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
    <section className="panel">
      <header className="panel-head">
        <h2>State Variables</h2>
        <span className="verified">{state.last_verified}</span>
      </header>
      {state.active_crisis && (
        <div className="crisis-banner">
          <span className="crisis-tag">ACTIVE CRISIS</span>
          <strong>{state.active_crisis.name}</strong>
          <span className="severity">severity {state.active_crisis.severity}</span>
        </div>
      )}
      <div className="state-groups">
        {groups.map(({ group, items }) => (
          <div key={group} className="state-group">
            <div className="state-group-title">{group}</div>
            <ul className="var-list">
              {items.map(({ key, value, meta }) => {
                const level = effectiveLevel(value, meta.risk);
                return (
                  <li key={key} className="var-row">
                    <div className="var-label">
                      <span>{meta.label}</span>
                      <span className={`var-value ${levelClass(level)}`}>{value}</span>
                    </div>
                    <div className="var-bar">
                      <div
                        className={`var-bar-fill ${levelClass(level)}`}
                        style={{ width: `${value}%` }}
                      />
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
      <details className="factions">
        <summary>Faction Postures ({state.factions.length})</summary>
        <ul className="faction-list">
          {state.factions.map((f) => (
            <li key={f.id}>
              <span className="faction-name">{f.name}</span>
              <span className={`posture posture-${f.alignment}`}>{f.posture}</span>
            </li>
          ))}
        </ul>
      </details>
    </section>
  );
}
