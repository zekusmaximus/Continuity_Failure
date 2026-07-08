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

// --- Guided turn flow ---------------------------------------------------------
// The frontend walks the player through one focused task at a time. The backend
// still resolves NPC decision + consequences together on advice submission; the
// UI simply reveals that single result across separate phases.

export type Phase =
  | "INTRO"
  | "CALL"
  | "BRIEF"
  | "EVIDENCE"
  | "ADVICE"
  | "CLIENT_DECISION"
  | "CONSEQUENCES"
  | "ARCHIVE"
  | "DOSSIER";

export const PHASE_LABEL: Record<Phase, string> = {
  INTRO: "Intake",
  CALL: "Incoming Call",
  BRIEF: "Situation Brief",
  EVIDENCE: "Evidence Review",
  ADVICE: "Advisory",
  CLIENT_DECISION: "Client Decision",
  CONSEQUENCES: "Consequences",
  ARCHIVE: "Turn Archive",
  DOSSIER: "Campaign Dossier",
};

// The ordered spine of a single turn, used for the header stepper.
export const TURN_STEPS: Phase[] = [
  "CALL",
  "BRIEF",
  "EVIDENCE",
  "ADVICE",
  "CLIENT_DECISION",
  "CONSEQUENCES",
  "ARCHIVE",
];

export const STEP_SHORT: Record<Phase, string> = {
  INTRO: "Intake",
  CALL: "Call",
  BRIEF: "Brief",
  EVIDENCE: "Evidence",
  ADVICE: "Advice",
  CLIENT_DECISION: "Decision",
  CONSEQUENCES: "Fallout",
  ARCHIVE: "Archive",
  DOSSIER: "Dossier",
};

// --- Evidence prioritization --------------------------------------------------
// Group documents into Critical / Relevant / Background without any AI. Priority
// is derived deterministically: attached-to-this-call ⇒ Critical, high-reliability
// or leaked/disputed ⇒ Relevant, everything else ⇒ Background.

export type EvidenceTier = "Critical" | "Relevant" | "Background";

export const EVIDENCE_TIER_ORDER: EvidenceTier[] = ["Critical", "Relevant", "Background"];

export const EVIDENCE_TIER_HINT: Record<EvidenceTier, string> = {
  Critical: "Attached to the current call — read these first.",
  Relevant: "Bears directly on the decision in front of you.",
  Background: "Context on file. Skim if time allows.",
};

// A short, deterministic "why it matters" line for a document.
export function whyItMatters(
  doc: { public_status: string; reliability: string; type: string },
  attached: boolean,
): string {
  if (attached) return "Filed with the current client call.";
  if (doc.public_status === "leaked") return "Already public — shapes the narrative whether you act or not.";
  if (doc.public_status === "disputed") return "Contested record — its reliability is itself a live question.";
  if (doc.reliability === "high") return "High-reliability record you can lean on.";
  if (doc.reliability === "low" || doc.reliability === "contested")
    return "Low-confidence source — corroborate before relying on it.";
  return "Background context on the engagement.";
}

// --- Consequence-phase diff aggregation ---------------------------------------
// Collapse the raw applied-diff list into one net row per variable (old → new),
// so the player sees "what changed" before "why it changed".

export interface AggregatedChange {
  variable: string;
  label: string;
  risk: boolean;
  oldValue: number;
  newValue: number;
  delta: number;
  reasons: string[];
}

export function aggregateChanges(
  diffs: { variable: string; old_value: number; new_value: number; reason: string }[],
): AggregatedChange[] {
  const byVar = new Map<string, AggregatedChange>();
  for (const d of diffs) {
    const meta = VARIABLE_META[d.variable];
    const existing = byVar.get(d.variable);
    if (existing) {
      existing.newValue = d.new_value;
      existing.delta = existing.newValue - existing.oldValue;
      if (d.reason && !existing.reasons.includes(d.reason)) existing.reasons.push(d.reason);
    } else {
      byVar.set(d.variable, {
        variable: d.variable,
        label: meta?.label ?? titleCase(d.variable),
        risk: meta?.risk ?? false,
        oldValue: d.old_value,
        newValue: d.new_value,
        delta: d.new_value - d.old_value,
        reasons: d.reason ? [d.reason] : [],
      });
    }
  }
  return [...byVar.values()]
    .filter((c) => c.delta !== 0)
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
}

// The four indicators surfaced in the header. Full state lives in the Case File.
export const KEY_INDICATORS: string[] = [
  "water_security",
  "public_trust",
  "legal_exposure",
  "hospital_stability",
];
