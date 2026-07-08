// Human-readable metadata for the 16 world-state variables.
// ``risk: true`` means HIGHER IS WORSE (drives bar color and label wording).

export interface VariableMeta {
  label: string;
  risk: boolean; // true => higher value is worse
  group: "Civic & Trust" | "Capacity" | "Risk & Exposure" | "Player Standing";
}

export const VARIABLE_META: Record<string, VariableMeta> = {
  water_security: { label: "Water Security", risk: false, group: "Capacity" },
  power_stability: { label: "Power Stability", risk: false, group: "Capacity" },
  hospital_stability: { label: "Hospital Stability", risk: false, group: "Capacity" },
  budget_capacity: { label: "Budget Capacity", risk: false, group: "Capacity" },
  staff_capacity: { label: "Staff Capacity", risk: false, group: "Capacity" },

  public_trust: { label: "Public Trust", risk: false, group: "Civic & Trust" },
  public_order: { label: "Public Order", risk: false, group: "Civic & Trust" },
  information_integrity: { label: "Information Integrity", risk: false, group: "Civic & Trust" },
  school_disruption: { label: "School Disruption", risk: true, group: "Civic & Trust" },

  media_pressure: { label: "Media Pressure", risk: true, group: "Risk & Exposure" },
  legal_exposure: { label: "Legal Exposure", risk: true, group: "Risk & Exposure" },
  state_oversight_risk: { label: "State Oversight Risk", risk: true, group: "Risk & Exposure" },
  contractor_dependency: { label: "Contractor Dependency", risk: true, group: "Risk & Exposure" },

  player_reputation: { label: "Player Reputation", risk: false, group: "Player Standing" },
  player_perceived_neutrality: { label: "Perceived Neutrality", risk: false, group: "Player Standing" },
  player_shadow_authority: { label: "Shadow Authority", risk: true, group: "Player Standing" },
};

export const VARIABLE_ORDER = Object.keys(VARIABLE_META);

export const GROUP_ORDER: VariableMeta["group"][] = [
  "Capacity",
  "Civic & Trust",
  "Risk & Exposure",
  "Player Standing",
];

// A value is "effective" (green) for the player's goals when the good-side is
// high or the risk-side is low.
export function effectiveLevel(value: number, risk: boolean): number {
  return risk ? 100 - value : value;
}

export function levelClass(level: number): string {
  if (level >= 60) return "lvl-good";
  if (level >= 35) return "lvl-warn";
  return "lvl-crit";
}

// --- Diegetic label maps (deterministic, presentation only) ---

export const URGENCY_LABEL: Record<string, string> = {
  low: "Low",
  elevated: "Elevated",
  high: "High",
  critical: "Critical",
};

export const URGENCY_CLASS: Record<string, string> = {
  low: "tag-low",
  elevated: "tag-elevated",
  high: "tag-high",
  critical: "tag-critical",
};

export const PUBLIC_STATUS_LABEL: Record<string, string> = {
  public: "Public",
  private: "Private",
  leaked: "Leaked",
  sealed: "Sealed",
  disputed: "Disputed",
  unknown: "Unknown",
};

export const PUBLIC_STATUS_CLASS: Record<string, string> = {
  public: "tag-public",
  private: "tag-private",
  leaked: "tag-leaked",
  sealed: "tag-sealed",
  disputed: "tag-disputed",
  unknown: "tag-unknown",
};

export const RELIABILITY_LABEL: Record<string, string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
  unknown: "Unknown",
  contested: "Contested",
};

export const RELIABILITY_CLASS: Record<string, string> = {
  high: "rel-high",
  medium: "rel-medium",
  low: "rel-low",
  unknown: "rel-unknown",
  contested: "rel-contested",
};

export const DECISION_BADGE: Record<string, string> = {
  FOLLOWED: "badge-followed",
  PARTIALLY_FOLLOWED: "badge-partial",
  MODIFIED: "badge-modified",
  DELAYED: "badge-delayed",
  REJECTED: "badge-rejected",
};

export const SOURCE_LABEL: Record<string, string> = {
  advice: "Advice",
  npc_modification: "NPC",
  ambient: "Drift",
  decision: "Decision",
};

export function titleCase(s: string): string {
  return s.replace(/_/g, " ").replace(/\w\S*/g, (w) => w.charAt(0).toUpperCase() + w.slice(1));
}
