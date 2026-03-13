// Canonical data schema for AIRSPACE-INTEL

export type RiskLevel = "Critical" | "High" | "Medium" | "Low";
export type Classification = "Drone" | "Bird" | "Aircraft" | "Unknown";
export type AgentStatus = "Active" | "Ready" | "Offline";
export type AlertType = "ALERT" | "WARNING" | "INFO" | "NFZ";

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
  anomaly_score?: number;
  anomaly_label?: "Normal" | "Suspect" | "Anomalous";
  anomaly_reasons?: string[];
  risk_score?: number;
  // Zero-Trust Flight ID - Physics Verification
  physics_verified?: boolean;
  spoofing_flags?: string[];
  digital_identity_trust?: number;
  physics_violations?: string[];
  motor_rpm_detected?: number;
  rcs_anomaly_score?: number;
  // ROE - Rules of Engagement (Legal-Agentic Co-Pilot)
  zone_type?: string;
  legal_basis?: string;
  authorized_responses?: string[];
  prohibited_responses?: string[];
  reporting_required?: boolean;
  roe_confidence?: number;
  // Deception Defense - Honeypot Airspace
  deception_active?: boolean;
  deception_type?: string;
  cyber_catcher_id?: string;
  cyber_catcher_target?: { lat: number; lon: number };
  deception_start_time?: string;
  deception_technique?: string;
  spoofed_path?: [number, number][];
}

export interface Agents {
  sentry: AgentStatus;
  profiler: AgentStatus;
  commander: AgentStatus;
}

export interface DashboardState {
  active_targets: AirTarget[];
  agents: Agents;
  anomalous_target_count?: number;
  cyber_catchers?: CyberCatcherZone[];
}

export interface NoFlyZone {
  id: string;
  name: string;
  description: string;
  center: [number, number]; // [lat, lon]
  radius_km: number;
}

export interface CyberCatcherZone {
  id: string;
  name: string;
  lat: number;
  lon: number;
  radius_m: number;
  safety_rating: string;
  active: boolean;
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

// High-level red zones across India derived from DGCA / Digital Sky style guidance.
// Coordinates are approximate and for simulation/visualization only.
export const NO_FLY_ZONES: NoFlyZone[] = [
  {
    id: "rashtrapati-bhavan-delhi",
    name: "Rashtrapati Bhavan & Central Delhi",
    description:
      "Permanent no-fly zone covering Parliament, PM residence, and central government enclave.",
    center: [28.6143, 77.1995],
    radius_km: 5,
  },
  {
    id: "taj-mahal-agra",
    name: "Taj Mahal, Agra",
    description: "Protected monument airspace in Agra.",
    center: [27.1751, 78.0421],
    radius_km: 3,
  },
  {
    id: "barc-mumbai",
    name: "BARC, Mumbai",
    description: "Bhabha Atomic Research Centre nuclear installation security zone.",
    center: [19.0481, 72.9106],
    radius_km: 3,
  },
  {
    id: "tirumala-temple-ap",
    name: "Tirumala Venkateswara Temple",
    description: "Temple airspace in Tirupati district, Andhra Pradesh.",
    center: [13.6839, 79.3473],
    radius_km: 3,
  },
  {
    id: "padmanabhaswamy-temple-kerala",
    name: "Padmanabhaswamy Temple",
    description: "Temple airspace in Thiruvananthapuram, Kerala.",
    center: [8.4828, 76.9432],
    radius_km: 3,
  },
  {
    id: "kalpakkam-nuclear-tn",
    name: "Kalpakkam Nuclear Installation",
    description: "Approximate 10-km security radius in Tamil Nadu.",
    center: [12.5546, 80.154],
    radius_km: 10,
  },
  {
    id: "tower-of-silence-mumbai",
    name: "Tower of Silence, Mumbai",
    description: "Restricted heritage zone in South Mumbai.",
    center: [18.9553, 72.7924],
    radius_km: 2,
  },
  {
    id: "mathura-refinery-up",
    name: "Mathura Refinery",
    description: "Critical petroleum infrastructure in Uttar Pradesh.",
    center: [27.459, 77.73],
    radius_km: 5,
  },
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
  (target: AirTarget) =>
    target.anomaly_label === "Anomalous"
      ? `${target.id}: Anomaly score ${target.anomaly_score?.toFixed(
          3
        )} — pattern breach`
      : `${target.id}: No anomaly signature`,
];

export function formatAlertTime(date: Date): string {
  const h = String(date.getUTCHours()).padStart(2, "0");
  const m = String(date.getUTCMinutes()).padStart(2, "0");
  const s = String(date.getUTCSeconds()).padStart(2, "0");
  return `${h}:${m}:${s}`;
}

export function getNearestNoFlyZone(
  coords: [number, number]
): { zone: NoFlyZone | null; distanceKm: number } {
  const [lat, lon] = coords;
  const R = 6371;

  let bestZone: NoFlyZone | null = null;
  let bestD = Infinity;

  for (const zone of NO_FLY_ZONES) {
    const [zLat, zLon] = zone.center;
    const dLat = ((zLat - lat) * Math.PI) / 180;
    const dLon = ((zLon - lon) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos((lat * Math.PI) / 180) *
        Math.cos((zLat * Math.PI) / 180) *
        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const d = R * c;
    if (d < bestD) {
      bestD = d;
      bestZone = zone;
    }
  }

  if (!bestZone || !isFinite(bestD)) {
    return { zone: null, distanceKm: Infinity };
  }
  return { zone: bestZone, distanceKm: bestD };
}
