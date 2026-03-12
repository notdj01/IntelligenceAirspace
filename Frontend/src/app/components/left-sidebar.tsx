import { useState, useEffect } from "react";
import {
  Radio,
  Shield,
  ScanEye,
  Terminal,
  AlertTriangle,
  Info,
  ShieldAlert,
} from "lucide-react";
import type { Agents, RiskAlert, AgentStatus, AlertType } from "../../lib/airspace-data";
import { formatAlertTime } from "../../lib/airspace-data";

interface LeftSidebarProps {
  agents: Agents;
  alerts: RiskAlert[];
}

export function LeftSidebar({ agents, alerts }: LeftSidebarProps) {
  return (
    <aside className="flex flex-col gap-4 h-full overflow-hidden">
      {/* Agentic Mesh Section */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <Radio size={14} className="text-[#22d3ee]" />
          <h2 className="font-mono text-xs uppercase tracking-widest text-[#22d3ee]">
            AGENTIC MESH
          </h2>
        </div>

        <div className="flex flex-col gap-2">
          <AgentCard
            icon={<Shield size={18} />}
            name="SENTRY"
            description="Perimeter radar · 360° sweep"
            status={agents.sentry}
          />
          <AgentCard
            icon={<ScanEye size={18} />}
            name="PROFILER"
            description="Micro-Doppler analysis engine"
            status={agents.profiler}
          />
          <AgentCard
            icon={<Terminal size={18} />}
            name="COMMANDER"
            description="Agentic decision & response"
            status={agents.commander}
          />
        </div>
      </div>

      {/* Divider */}
      <div
        style={{ borderColor: "rgba(255,255,255,0.08)" }}
        className="border-t"
      />

      {/* Risk Feed Section */}
      <div className="flex flex-col gap-3 flex-1 min-h-0 overflow-hidden">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle size={14} className="text-[#f43f5e]" />
            <h2 className="font-mono text-xs uppercase tracking-widest text-[#f43f5e]">
              RISK FEED
            </h2>
          </div>
          <div
            style={{
              background: "rgba(244,63,94,0.1)",
              border: "1px solid rgba(244,63,94,0.3)",
            }}
            className="px-1.5 py-0.5 rounded-sm"
          >
            <span className="font-mono text-[10px] text-[#f43f5e]">LIVE</span>
          </div>
        </div>

        <AlertList alerts={alerts} />
      </div>
    </aside>
  );
}

function AgentCard({
  icon,
  name,
  description,
  status,
}: {
  icon: React.ReactNode;
  name: string;
  description: string;
  status: AgentStatus;
}) {
  return (
    <div
      style={{
        background: "rgba(13,20,32,0.7)",
        backdropFilter: "blur(12px)",
        border: "1px solid rgba(255,255,255,0.07)",
      }}
      className="rounded-lg p-3 flex items-center gap-3"
    >
      {/* Icon Container */}
      <div
        style={{
          background: "rgba(34,211,238,0.1)",
          border: "1px solid rgba(34,211,238,0.2)",
        }}
        className="size-9 rounded-md flex items-center justify-center flex-shrink-0"
      >
        <span className="text-[#22d3ee]">{icon}</span>
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="font-sans text-xs tracking-widest text-[#94a3b8] uppercase">
          {name}
        </div>
        <div className="font-mono text-xs text-[#475569]">{description}</div>
      </div>

      {/* Status LED */}
      <StatusLED status={status} />
    </div>
  );
}

function StatusLED({ status }: { status: AgentStatus }) {
  const config = {
    Active: {
      color: "#4ade80",
      shadow: "0 0 6px #4ade80, 0 0 12px rgba(74,222,128,0.4)",
      animate: true,
    },
    Ready: {
      color: "#fb923c",
      shadow: "0 0 6px #fb923c",
      animate: false,
    },
    Offline: {
      color: "#64748b",
      shadow: "none",
      animate: false,
    },
  };

  const cfg = config[status];

  return (
    <div className="flex flex-col items-center gap-1">
      <div
        style={{
          background: cfg.color,
          boxShadow: cfg.shadow,
          animation: cfg.animate ? "pulse-led 2s ease-in-out infinite" : undefined,
        }}
        className="size-2 rounded-full"
      />
      <span
        style={{ color: cfg.color }}
        className="font-mono text-[9px] uppercase"
      >
        {status}
      </span>
    </div>
  );
}

function AlertList({ alerts }: { alerts: RiskAlert[] }) {
  const [visibleIds, setVisibleIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (alerts.length === 0) return;
    const newestAlert = alerts[0];
    if (!visibleIds.has(newestAlert.id)) {
      const timer = setTimeout(() => {
        setVisibleIds((prev) => new Set([...prev, newestAlert.id]));
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [alerts, visibleIds]);

  return (
    <div
      style={{
        scrollbarWidth: "thin",
        scrollbarColor: "#1e293b transparent",
      }}
      className="flex flex-col gap-2 flex-1 overflow-y-auto min-h-0"
    >
      {alerts.map((alert) => (
        <AlertItem
          key={alert.id}
          alert={alert}
          visible={visibleIds.has(alert.id)}
        />
      ))}
    </div>
  );
}

function AlertItem({
  alert,
  visible,
}: {
  alert: RiskAlert;
  visible: boolean;
}) {
  const typeConfig: Record<
    AlertType,
    { bg: string; border: string; icon: React.ReactNode; color: string }
  > = {
    ALERT: {
      bg: "rgba(244,63,94,0.08)",
      border: "rgba(244,63,94,0.25)",
      icon: <AlertTriangle size={14} />,
      color: "#f43f5e",
    },
    WARNING: {
      bg: "rgba(251,146,60,0.08)",
      border: "rgba(251,146,60,0.25)",
      icon: <AlertTriangle size={14} />,
      color: "#fb923c",
    },
    INFO: {
      bg: "rgba(15,23,42,0.6)",
      border: "rgba(255,255,255,0.07)",
      icon: <Info size={14} />,
      color: "#22d3ee",
    },
    NFZ: {
      bg: "rgba(248,113,113,0.12)",
      border: "rgba(248,113,113,0.4)",
      icon: <ShieldAlert size={14} />,
      color: "#fecaca",
    },
  };

  const config = typeConfig[alert.type];

  return (
    <div
      style={{
        background: config.bg,
        border: `1px solid ${config.border}`,
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : "translateY(-8px)",
        transition: "opacity 0.3s ease-out, transform 0.3s ease-out",
      }}
      className="rounded-md p-2.5 flex flex-col gap-2"
    >
      {/* Header Row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span style={{ color: config.color }}>{config.icon}</span>
          <span
            style={{ color: config.color }}
            className="font-mono font-bold text-xs tracking-wider"
          >
            {alert.type}
          </span>
        </div>
        <span className="font-mono text-xs text-[#475569]">
          {formatAlertTime(alert.timestamp)}
        </span>
      </div>

      {/* Message */}
      <p className="font-mono text-xs leading-relaxed text-[#94a3b8]">
        {alert.message}
      </p>
    </div>
  );
}
