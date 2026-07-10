import type { Faction } from "../api/client";
import { titleCase } from "../domain";

function influenceClass(value: number): string {
  if (value >= 70) return "mag-high";
  if (value >= 40) return "mag-mid";
  return "mag-low";
}

function pressureClass(value: number): string {
  if (value >= 65) return "lvl-crit";
  if (value >= 40) return "lvl-warn";
  return "lvl-good";
}

export default function FactionCard({ faction }: { faction: Faction }) {
  return (
    <li className={`cd-faction cd-align-${faction.alignment}`}>
      <div className="cd-faction-head">
        <span className="cd-faction-name">{faction.name}</span>
        <span className="cd-faction-posture">{faction.posture}</span>
      </div>
      <div className="cd-faction-bars">
        <div className="cd-faction-bar">
          <span className="cd-faction-bar-k">Influence</span>
          <span className="cd-faction-bar-track">
            <span className={`cd-faction-bar-fill ${influenceClass(faction.influence)}`} style={{ width: `${faction.influence}%` }} />
          </span>
          <span className="cd-faction-bar-v">{faction.influence}</span>
        </div>
        <div className="cd-faction-bar">
          <span className="cd-faction-bar-k">Pressure</span>
          <span className="cd-faction-bar-track">
            <span className={`cd-faction-bar-fill ${pressureClass(faction.current_pressure)}`} style={{ width: `${faction.current_pressure}%` }} />
          </span>
          <span className="cd-faction-bar-v">{faction.current_pressure}</span>
        </div>
      </div>
      {faction.public_position && (
        <div className="cd-faction-line">
          <span className="cd-meta-k">Public</span>
          <span className="cd-meta-v">{faction.public_position}</span>
        </div>
      )}
      {faction.private_incentive && (
        <div className="cd-faction-line cd-private">
          <span className="cd-meta-k">Private</span>
          <span className="cd-meta-v">{faction.private_incentive}</span>
        </div>
      )}
      {faction.red_lines.length > 0 && (
        <div className="cd-faction-redlines">
          {faction.red_lines.map((r) => (
            <span key={r} className="cd-redline" title="Red line">{r}</span>
          ))}
        </div>
      )}
      <div className="cd-faction-foot">
        <span className="cd-chip">{titleCase(faction.alignment)}</span>
        <span className="cd-chip">trust {faction.trust_in_player}</span>
      </div>
    </li>
  );
}
