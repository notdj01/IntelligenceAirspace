import { useState, useEffect } from "react";
import { Satellite, Map, Activity, Clock } from "lucide-react";

interface DashboardHeaderProps {
  targetCount: number;
  criticalCount: number;
}

export function DashboardHeader({
  targetCount,
  criticalCount,
}: DashboardHeaderProps) {
  const [currentTime, setCurrentTime] = useState<string>("");
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    if (!isClient) return;

    const updateTime = () => {
      const now = new Date();
      const h = String(now.getUTCHours()).padStart(2, "0");
      const m = String(now.getUTCMinutes()).padStart(2, "0");
      const s = String(now.getUTCSeconds()).padStart(2, "0");
      setCurrentTime(`${h}:${m}:${s}`);
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, [isClient]);

  return (
    <header
      style={{
        background: "rgba(13,20,32,0.95)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid rgba(34,211,238,0.12)",
      }}
      className="h-12 flex items-center justify-between px-4 gap-4"
    >
      {/* Left Zone - Branding */}
      <div className="flex items-center gap-3">
        <div
          style={{
            background: "rgba(34,211,238,0.1)",
            border: "1px solid rgba(34,211,238,0.25)",
          }}
          className="size-8 rounded flex items-center justify-center"
        >
          <Satellite size={16} className="text-[#22d3ee]" />
        </div>
        <div className="flex flex-col">
          <h1 className="font-mono text-sm font-bold tracking-widest uppercase text-[#e2e8f0]">
            AIRSPACE-INTEL
          </h1>
          <p className="font-mono text-xs text-[#334155]">
            Tactical Situational Awareness v2.4.1
          </p>
        </div>
      </div>

      {/* Center Zone - Status Chips */}
      <div className="flex items-center gap-2">
        <StatusChip
          icon={<Map size={12} />}
          label="SECTOR: MUMBAI"
          color="cyan"
        />
        <StatusChip
          icon={<Activity size={12} />}
          label={`${targetCount} TRACKS ACTIVE`}
          color="green"
        />
        {criticalCount > 0 && (
          <StatusChip
            label={`${criticalCount} CRITICAL`}
            color="rose"
            pulse
          />
        )}
      </div>

      {/* Right Zone - Clock */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Clock size={14} className="text-[#64748b]" />
          <span className="font-mono text-xs text-[#64748b]">UTC</span>
          <span className="font-mono text-sm font-bold tracking-widest text-[#e2e8f0]">
            {isClient ? currentTime : "00:00:00"}
          </span>
        </div>
        <div className="flex flex-col items-center gap-0.5">
          <div
            style={{
              boxShadow: "0 0 8px #4ade80",
            }}
            className="size-1.5 rounded-full bg-[#4ade80]"
          />
          <span className="font-mono text-[8px] text-[#4ade80]">LIVE</span>
        </div>
      </div>
    </header>
  );
}

function StatusChip({
  icon,
  label,
  color,
  pulse = false,
}: {
  icon?: React.ReactNode;
  label: string;
  color: "cyan" | "green" | "rose";
  pulse?: boolean;
}) {
  const colors = {
    cyan: {
      bg: "rgba(34,211,238,0.1)",
      border: "rgba(34,211,238,0.3)",
      text: "#22d3ee",
      dot: "#22d3ee",
    },
    green: {
      bg: "rgba(74,222,128,0.1)",
      border: "rgba(74,222,128,0.3)",
      text: "#4ade80",
      dot: "#4ade80",
    },
    rose: {
      bg: "rgba(244,63,94,0.1)",
      border: "rgba(244,63,94,0.3)",
      text: "#f43f5e",
      dot: "#f43f5e",
    },
  };

  const colorScheme = colors[color];

  return (
    <div
      style={{
        background: colorScheme.bg,
        border: `1px solid ${colorScheme.border}`,
        animation: pulse ? "blink-border 1.5s ease-in-out infinite" : undefined,
      }}
      className="px-2 py-1 rounded flex items-center gap-1.5"
    >
      {pulse && (
        <div
          style={{
            background: colorScheme.dot,
          }}
          className="size-1.5 rounded-full"
        />
      )}
      {icon && <span style={{ color: colorScheme.text }}>{icon}</span>}
      <span
        style={{ color: colorScheme.text }}
        className="font-mono text-xs tracking-wider font-medium"
      >
        {label}
      </span>
    </div>
  );
}
