import { useState, useEffect, useRef } from "react";
import { DashboardHeader } from "./components/dashboard-header";
import { LeftSidebar } from "./components/left-sidebar";
import { RightSidebar } from "./components/right-sidebar";
import { AirspaceMapClient } from "./components/airspace-map-client";
import type { AirTarget, DashboardState, RiskAlert } from "../lib/airspace-data";
import {
  INITIAL_STATE,
  RISK_COLORS,
  LIVE_MESSAGES,
  getNearestNoFlyZone,
} from "../lib/airspace-data";

export default function App() {
  const [dashboardState, setDashboardState] =
    useState<DashboardState>(INITIAL_STATE);
  const [alerts, setAlerts] = useState<RiskAlert[]>([]);
  const [selectedTarget, setSelectedTarget] = useState<AirTarget | null>(null);
  const [isClient, setIsClient] = useState(false);
  const [isRightSidebarVisible, setIsRightSidebarVisible] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [focusTargetId, setFocusTargetId] = useState<string | null>(null);
  const nfzAlertIdsRef = useRef<Set<string>>(new Set());

  // Poll backend for live airspace data
  useEffect(() => {
    const backendUrl =
      (import.meta as any).env?.VITE_BACKEND_URL ?? "http://localhost:8000";

    const fetchState = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/state`);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        setDashboardState({
          active_targets: data.active_targets ?? [],
          agents: data.agents ?? INITIAL_STATE.agents,
          anomalous_target_count: data.anomalous_target_count ?? 0,
        });
        setError(null);
      } catch (e) {
        console.error("Failed to fetch backend state", e);
        setError("Backend unavailable");
      }
    };

    fetchState();
    const id = setInterval(fetchState, 5000);
    return () => clearInterval(id);
  }, []);

  // Initialize client-side only state
  useEffect(() => {
    setIsClient(true);
  }, []);

  // Live alert generation
  useEffect(() => {
    if (!isClient) return;

    let counter = 0;

    const interval = setInterval(() => {
      const targets = dashboardState.active_targets;
      if (targets.length === 0) return;

      const targetIndex = counter % targets.length;
      const target = targets[targetIndex];

      const messageTemplate =
        LIVE_MESSAGES[Math.floor(Math.random() * LIVE_MESSAGES.length)];
      const message = messageTemplate(target);

      const alertType =
        target.risk_level === "Critical"
          ? "ALERT"
          : target.risk_level === "High"
          ? "WARNING"
          : "INFO";

      const newAlert: RiskAlert = {
        id: `alert-${Date.now()}-${Math.random()}`,
        type: alertType,
        message,
        timestamp: new Date(),
      };

      setAlerts((prev) => [newAlert, ...prev].slice(0, 20));
      counter++;
    }, 3500);

    return () => clearInterval(interval);
  }, [isClient, dashboardState]);

  // NFZ intrusion alerts (one per target/zone)
  useEffect(() => {
    const targets = dashboardState.active_targets;
    if (!isClient || targets.length === 0) return;

    const newAlerts: RiskAlert[] = [];
    const seen = nfzAlertIdsRef.current;

    for (const t of targets) {
      if (!t.coords) continue;
      const nearest = getNearestNoFlyZone(t.coords);
      if (!nearest.zone) continue;
      const inside = nearest.distanceKm <= nearest.zone.radius_km;
      if (!inside) continue;

      const key = `nfz-${nearest.zone.id}-${t.id}`;
      if (seen.has(key)) continue;
      seen.add(key);

      newAlerts.push({
        id: key,
        type: "NFZ",
        message: `NFZ INTRUSION: ${t.id} inside ${nearest.zone.name} (${nearest.distanceKm.toFixed(
          1
        )} km, risk ${(t.risk_score ?? 0).toFixed(1)})`,
        timestamp: new Date(),
      });
    }

    if (newAlerts.length > 0) {
      setAlerts((prev) => [...newAlerts, ...prev].slice(0, 20));
    }
  }, [isClient, dashboardState]);

  const handleSelectTarget = (target: AirTarget) => {
    setSelectedTarget(target);
    setIsRightSidebarVisible(true);
  };

  const handleDeselect = () => {
    setSelectedTarget(null);
    setIsRightSidebarVisible(false);
  };

  const handleConfirmRecommendation = (targetId: string) => {
    const confirmAlert: RiskAlert = {
      id: `confirm-${Date.now()}`,
      type: "INFO",
      message: `Commander recommendation confirmed for ${targetId} — executing tactical response protocol.`,
      timestamp: new Date(),
    };
    setAlerts((prev) => [confirmAlert, ...prev].slice(0, 20));
  };

  const criticalCount = dashboardState.active_targets.filter(
    (t) => t.risk_level === "Critical"
  ).length;
  const anomalousCount =
    dashboardState.anomalous_target_count ??
    dashboardState.active_targets.filter(
      (t) => t.anomaly_label === "Anomalous"
    ).length;

  const extremeTarget: AirTarget | null =
    dashboardState.active_targets
      .filter(
        (t) =>
          t.anomaly_label === "Anomalous" && (t.anomaly_score ?? 0) >= 4.5
      )
      .sort(
        (a, b) => (b.anomaly_score ?? 0) - (a.anomaly_score ?? 0)
      )[0] ?? null;

  const handleFocusExtreme = () => {
    if (!extremeTarget) return;
    setSelectedTarget(extremeTarget);
    setIsRightSidebarVisible(true);
    setFocusTargetId(extremeTarget.id);
  };

  return (
    <main className="flex flex-col h-screen overflow-hidden bg-[#0f172a]">
      {/* Header */}
      <DashboardHeader
        targetCount={dashboardState.active_targets.length}
        criticalCount={criticalCount}
        anomalousCount={anomalousCount}
      />

      {/* Main Content Row */}
      <div className="flex flex-1 gap-3 p-3 overflow-hidden min-h-0">
        {/* Left Sidebar */}
        <div
          style={{
            background: "rgba(13,20,32,0.7)",
            backdropFilter: "blur(12px)",
            border: "1px solid rgba(255,255,255,0.07)",
          }}
          className="w-72 flex-shrink-0 rounded-lg p-4"
        >
          <LeftSidebar
            agents={dashboardState.agents}
            alerts={alerts}
          />
        </div>

        {/* Center Column - Target Roster + Map */}
        <div className="flex-1 flex flex-col gap-3 min-w-0">
          {/* Target Roster Strip */}
          <div
            style={{
              background: "rgba(13,20,32,0.7)",
              backdropFilter: "blur(12px)",
              border: "1px solid rgba(255,255,255,0.07)",
            }}
            className="rounded-lg flex items-center gap-2 px-3 py-2"
          >
            <span className="font-mono text-xs uppercase tracking-widest text-[#334155]">
              Tracks:
            </span>
            <div className="flex items-center gap-2 flex-1">
              {dashboardState.active_targets.map((target) => {
                const isSelected = selectedTarget?.id === target.id;
                const riskColor = RISK_COLORS[target.risk_level];
                return (
                  <button
                    key={target.id}
                    onClick={() => handleSelectTarget(target)}
                    style={{
                      background: isSelected
                        ? `${riskColor}21`
                        : "rgba(30,41,59,0.6)",
                      border: isSelected
                        ? `1px solid ${riskColor}61`
                        : "1px solid rgba(255,255,255,0.06)",
                      color: isSelected ? riskColor : "#64748b",
                      transition: "all 0.2s ease",
                    }}
                    className="px-2 py-1 rounded font-mono text-xs flex items-center gap-1.5"
                  >
                    <div
                      style={{ background: riskColor }}
                      className="size-1.5 rounded-full"
                    />
                    {target.id}
                  </button>
                );
              })}
            </div>
            <span className="font-mono text-xs text-[#1e293b]">
              Click marker to select · Drag to pan
            </span>
          </div>

          {/* Map */}
          <div
            style={{
              background: "rgba(13,20,32,0.3)",
              backdropFilter: "blur(8px)",
              border: "1px solid rgba(255,255,255,0.07)",
            }}
            className="flex-1 rounded-lg overflow-hidden min-h-0"
          >
            <AirspaceMapClient
              targets={dashboardState.active_targets}
              selectedId={selectedTarget?.id || null}
              onSelectTarget={handleSelectTarget}
              onDeselect={handleDeselect}
              focusTargetId={focusTargetId}
            />
          </div>
        </div>

        {/* Right Sidebar */}
        <div
          style={{
            background: "rgba(13,20,32,0.7)",
            backdropFilter: "blur(12px)",
            border: "1px solid rgba(255,255,255,0.07)",
            width: isRightSidebarVisible ? "288px" : "0px",
            padding: isRightSidebarVisible ? "16px" : "0px",
            opacity: isRightSidebarVisible ? 1 : 0,
            transition: "width 0.3s ease-in-out, opacity 0.3s ease-in-out, padding 0.3s ease-in-out",
            overflow: "hidden",
          }}
          className="flex-shrink-0 rounded-lg"
        >
          {isRightSidebarVisible && (
            <RightSidebar
              target={selectedTarget}
              onConfirm={handleConfirmRecommendation}
            />
          )}
        </div>
      </div>

      {/* Extreme anomaly popup */}
      {extremeTarget && (
        <button
          onClick={handleFocusExtreme}
          style={{
            position: "fixed",
            left: "50%",
            bottom: "20px",
            transform: "translateX(-50%)",
            background:
              "radial-gradient(circle at top left, rgba(248,113,113,0.15), rgba(15,23,42,0.95))",
            border: "1px solid rgba(248,113,113,0.6)",
            boxShadow: "0 0 18px rgba(248,113,113,0.45)",
          }}
          className="z-50 px-4 py-3 rounded-lg flex flex-col items-start gap-1 font-mono text-xs text-left text-[#fecaca]"
        >
          <span className="text-[10px] tracking-[0.25em] text-[#fecaca]">
            PRIORITY ANOMALY
          </span>
          <span className="text-sm font-bold text-[#fee2e2]">
            {extremeTarget.id} · score{" "}
            {(extremeTarget.anomaly_score ?? 0).toFixed(2)}
          </span>
          <span className="text-[11px] text-[#fecaca]">
            Click to focus map and open response panel.
          </span>
        </button>
      )}
    </main>
  );
}