// Canonical data schema for AIRSPACE-INTEL

export type RiskLevel = "Critical" | "High" | "Medium" | "Low";
export type Classification = "Drone" | "Bird" | "Aircraft" | "Unknown";
export type AgentStatus = "Active" | "Ready" | "Offline";
export type AlertType = "ALERT" | "WARNING" | "INFO";

export interface AirTarget {
  id: string;
  coords: [number, number];
  trajectory: [number, number][];
  // Optional future path provided by backend LSTM
  predicted_trajectory?: [number, number][];
  speed: number;
  adsb: boolean;
  classification: Classification;
  confidence: number;
  risk_level: RiskLevel;
}

export interface Agents {
  sentry: AgentStatus;
  profiler: AgentStatus;
  commander: AgentStatus;
}

export interface DashboardState {
  active_targets: AirTarget[];
  agents: Agents;
}

export interface RiskAlert {
  id: string;
  type: AlertType;
  message: string;
  timestamp: Date;
}

export const RISK_COLORS: Record<RiskLevel, string> = {
  Critical: "#f43f5e",
  High: "#fb923c",
  Medium: "#fbbf24",
  Low: "#4ade80",
};

export const NO_FLY_ZONE: [number, number][] = [
  [18.89, 72.82],
  [18.91, 72.79],
  [18.95, 72.8],
  [18.94, 72.84],
  [18.91, 72.85],
];

// Initial seed data - 4 targets around Mumbai
export const INITIAL_STATE: DashboardState = {
  active_targets: [
    {
      id: "UNID-007",
      coords: [18.92, 72.83],
      trajectory: [
        [18.915, 72.825],
        [18.917, 72.827],
        [18.92, 72.83],
      ],
      speed: 150,
      adsb: false,
      classification: "Drone",
      confidence: 92,
      risk_level: "Critical",
    },
    {
      id: "FLIGHT-221",
      coords: [19.08, 72.87],
      trajectory: [
        [19.075, 72.865],
        [19.077, 72.868],
        [19.08, 72.87],
      ],
      speed: 480,
      adsb: true,
      classification: "Aircraft",
      confidence: 99,
      risk_level: "Low",
    },
    {
      id: "BIO-042",
      coords: [18.98, 72.92],
      trajectory: [
        [18.975, 72.915],
        [18.977, 72.918],
        [18.98, 72.92],
      ],
      speed: 12,
      adsb: false,
      classification: "Bird",
      confidence: 78,
      risk_level: "Low",
    },
    {
      id: "UNID-013",
      coords: [19.15, 72.76],
      trajectory: [
        [19.145, 72.755],
        [19.147, 72.758],
        [19.15, 72.76],
      ],
      speed: 95,
      adsb: false,
      classification: "Drone",
      confidence: 85,
      risk_level: "High",
    },
  ],
  agents: {
    sentry: "Active",
    profiler: "Active",
    commander: "Active",
  },
};

export function getXAIRecommendation(target: AirTarget | null): string {
  if (!target) {
    return "No target selected. Awaiting tactical input.";
  }

  const { id, classification, speed, adsb, confidence, risk_level } = target;
  const transponderStatus = adsb ? "ACTIVE" : "INACTIVE";

  if (risk_level === "Critical") {
    return `THREAT ASSESSMENT: Object ${id} classified as ${classification} moving at ${speed} kts. Transponder ${
      adsb ? "ON" : "OFF"
    }. Confidence: ${confidence}%. RECOMMENDATION: Intercept and neutralize immediately. Activate Protocol SIGMA-7.`;
  }

  if (risk_level === "High") {
    return `ELEVATED RISK: Object ${id} is a ${classification} at ${speed} kts with transponder ${transponderStatus}. Confidence: ${confidence}%. RECOMMENDATION: Deploy surveillance drone and alert sector command.`;
  }

  if (!adsb) {
    return `ADVISORY: Object ${id} is moving at ${speed} kts with transponder OFF. Classification: ${classification} (${confidence}% confidence). Monitor trajectory and prepare intercept vector.`;
  }

  return `NOMINAL: Object ${id} — ${classification} at ${speed} kts. Transponder ${transponderStatus}. Confidence: ${confidence}%. No immediate action required.`;
}

// Live alert message templates
export const LIVE_MESSAGES = [
  (target: AirTarget) =>
    `${target.id}: Trajectory deviation detected — ${target.speed} kts`,
  (target: AirTarget) =>
    `Profiler recalibrating for ${target.id} — ${target.classification} signature`,
  (target: AirTarget) =>
    `${target.id} approaching restricted corridor — ${target.confidence}% confidence`,
  (target: AirTarget) =>
    `Transponder ${target.adsb ? "verified" : "lost"} on ${target.id}`,
  (target: AirTarget) =>
    `Commander acknowledged ${target.id} — monitoring ${target.risk_level} risk`,
];

export function formatAlertTime(date: Date): string {
  const h = String(date.getUTCHours()).padStart(2, "0");
  const m = String(date.getUTCMinutes()).padStart(2, "0");
  const s = String(date.getUTCSeconds()).padStart(2, "0");
  return `${h}:${m}:${s}`;
}
