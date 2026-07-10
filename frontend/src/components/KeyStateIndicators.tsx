import type { WorldState } from "../api/client";
import {
  KEY_INDICATORS,
  VARIABLE_META,
  effectiveLevel,
  levelClass,
} from "../domain";

/**
 * The four headline indicators shown in the masthead. Everything else lives in
 * the Case File — this is the at-a-glance read the player carries through every
 * phase.
 */
export default function KeyStateIndicators({ state }: { state: WorldState | null }) {
  return (
    <div className="cd-keystate" role="group" aria-label="Key state indicators">
      {KEY_INDICATORS.map((key) => {
        const meta = VARIABLE_META[key];
        const value = state?.variables?.[key];
        const has = typeof value === "number";
        const level = has ? effectiveLevel(value, meta.risk) : 0;
        const cls = has ? levelClass(level) : "";
        const direction = meta.risk ? "Higher is worse" : "Higher is better";
        return (
          <div
            key={key}
            className="cd-keystate-item"
            aria-label={`${meta.label}: ${has ? value : "unavailable"} of 100. ${direction}.`}
          >
            <span className="cd-keystate-label-wrap">
              <span className="cd-keystate-label">{meta.label}</span>
              <span className="cd-keystate-direction">
                {meta.risk ? "↑ risk" : "↑ better"}
              </span>
            </span>
            <span
              className="cd-keystate-track"
              role="progressbar"
              aria-label={meta.label}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={has ? value : undefined}
              aria-valuetext={has ? `${value} of 100. ${direction}.` : "Unavailable"}
            >
              <span
                className={`cd-keystate-fill ${cls}`}
                style={{ width: has ? `${value}%` : "0%" }}
              />
            </span>
            <span className={`cd-keystate-value ${cls}`}>{has ? value : "—"}</span>
          </div>
        );
      })}
    </div>
  );
}
