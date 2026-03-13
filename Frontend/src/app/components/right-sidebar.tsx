import { useRef, useEffect, useState } from "react";
import {
  Crosshair,
  Zap,
  Bot,
  CheckCircle,
  ChevronRight,
  Shield,
  AlertTriangle,
  Radio,
  Gavel,
  FileText,
  CheckSquare,
  XCircle,
  Target,
  Wifi,
  MapPin,
} from "lucide-react";
import type { AirTarget, Classification } from "../../lib/airspace-data";
import {
  RISK_COLORS,
  NO_FLY_ZONES,
  getNearestNoFlyZone,
  getXAIRecommendation,
} from "../../lib/airspace-data";

interface RightSidebarProps {
  target: AirTarget | null;
  onConfirm: (targetId: string) => void;
}

export function RightSidebar({ target, onConfirm }: RightSidebarProps) {
  return (
    <aside
      style={{
        scrollbarWidth: "thin",
        scrollbarColor: "#1e293b transparent",
      }}
      className="flex flex-col gap-3 h-full overflow-y-auto"
    >
      <TargetDetailCard target={target} />
      <MicroDopplerPanel target={target} />
      <ZeroTrustPanel target={target} />
      <ROEPanel target={target} />
      <DeceptionPanel target={target} />
      <CommanderXAIBox target={target} onConfirm={onConfirm} />
    </aside>
  );
}

function TargetDetailCard({ target }: { target: AirTarget | null }) {
  const nearest =
    target != null ? getNearestNoFlyZone(target.coords) : { zone: null, distanceKm: Infinity };
  const insideNfz =
    nearest.zone && nearest.distanceKm <= nearest.zone.radius_km;

  return (
    <div
      style={{
        background: "rgba(13,20,32,0.7)",
        backdropFilter: "blur(12px)",
        border: "1px solid rgba(255,255,255,0.07)",
      }}
      className="rounded-lg p-4 flex flex-col gap-3"
    >
      {/* Header */}
      <div className="flex items-center gap-2">
        <Crosshair size={14} className="text-[#22d3ee]" />
        <h2 className="font-mono text-xs uppercase tracking-widest text-[#22d3ee]">
          TARGET DETAIL
        </h2>
      </div>

      {/* Content */}
      {!target ? (
        <div className="flex flex-col items-center justify-center py-8 gap-2">
          <Crosshair size={24} className="text-[#1e293b]" />
          <p className="font-mono text-xs text-[#475569]">
            No target selected
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {/* ID and Risk Badge */}
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-xl font-mono font-bold tracking-widest text-[#f1f5f9]">
              {target.id}
            </h3>
            <div
              style={{
                background: `${RISK_COLORS[target.risk_level]}1A`,
                border: `1px solid ${RISK_COLORS[target.risk_level]}40`,
              }}
              className="px-2 py-1 rounded-sm"
            >
              <span
                style={{ color: RISK_COLORS[target.risk_level] }}
                className="font-mono text-xs font-bold"
              >
                {target.risk_level.toUpperCase()}
              </span>
            </div>
          </div>

          {/* Stats */}
          <div className="flex flex-col">
            <StatRow label="CLASS" value={target.classification} color="#e2e8f0" />
            <StatRow
              label="SPEED"
              value={`${target.speed} kts`}
              color="#22d3ee"
            />
            <StatRow
              label="TRANSPONDER"
              value={target.adsb ? "ON" : "OFF"}
              color={target.adsb ? "#4ade80" : "#f43f5e"}
            />
            <StatRow
              label="CONFIDENCE"
              value={`${target.confidence}%`}
              color="#fb923c"
            />
            <StatRow
              label="COORDS"
              value={`${target.coords[0].toFixed(2)}°N, ${target.coords[1].toFixed(
                2
              )}°E`}
              color="#94a3b8"
              noBorder
            />
            <StatRow
              label="RISK SCORE"
              value={`${(target.risk_score ?? 0).toFixed(1)} / 100`}
              color={
                target.risk_level === "Critical"
                  ? "#f97316"
                  : target.risk_level === "High"
                  ? "#fb923c"
                  : target.risk_level === "Low"
                  ? "#4ade80"
                  : "#e5e7eb"
              }
            />
            {nearest.zone && (
              <StatRow
                label="NEAREST NFZ"
                value={`${nearest.zone.name} · ${nearest.distanceKm.toFixed(1)} km${
                  insideNfz ? " (INSIDE)" : ""
                }`}
                color={insideNfz ? "#f97316" : "#94a3b8"}
                noBorder
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function StatRow({
  label,
  value,
  color,
  noBorder = false,
}: {
  label: string;
  value: string;
  color: string;
  noBorder?: boolean;
}) {
  return (
    <div
      style={{
        borderBottom: noBorder ? undefined : "1px solid rgba(255,255,255,0.06)",
      }}
      className="flex items-center justify-between py-2"
    >
      <span className="font-mono text-xs uppercase tracking-widest text-[#475569]">
        {label}
      </span>
      <span style={{ color }} className="font-mono text-sm font-semibold">
        {value}
      </span>
    </div>
  );
}

function MicroDopplerPanel({ target }: { target: AirTarget | null }) {
  const signatureType = target
    ? target.classification === "Drone"
      ? "HIGH-FREQ PERIODIC"
      : target.classification === "Bird"
      ? "LOW-FREQ ERRATIC"
      : "SMOOTH SINUSOID"
    : "";

  const maxFreq = target?.classification === "Drone" ? "5 kHz" : "500 Hz";

  return (
    <div
      style={{
        background: "rgba(13,20,32,0.7)",
        backdropFilter: "blur(12px)",
        border: "1px solid rgba(255,255,255,0.07)",
      }}
      className="rounded-lg p-4 flex flex-col gap-3"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap size={14} className="text-[#22d3ee]" />
          <h2 className="font-mono text-xs uppercase tracking-widest text-[#22d3ee]">
            MICRO-DOPPLER
          </h2>
        </div>
        {target && (
          <span className="font-mono text-xs text-[#475569]">
            {signatureType}
          </span>
        )}
      </div>

      {/* Canvas */}
      {!target ? (
        <div
          style={{ background: "rgba(15,23,42,0.8)" }}
          className="h-[72px] rounded flex items-center justify-center"
        >
          <span className="font-mono text-xs text-[#334155]">
            — NO SIGNAL —
          </span>
        </div>
      ) : (
        <>
          <DopplerCanvas key={target.id} target={target} />
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs text-[#334155]">0 Hz</span>
            <span className="font-mono text-xs text-[#334155]">{maxFreq}</span>
          </div>
        </>
      )}
    </div>
  );
}

function DopplerCanvas({ target }: { target: AirTarget }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const timeRef = useRef(0);
  const animationRef = useRef<number>();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const W = 280;
    const H = 72;
    const isDrone = target.classification === "Drone";

    const animate = () => {
      ctx.clearRect(0, 0, W, H);

      // Grid lines
      ctx.strokeStyle = "rgba(34,211,238,0.05)";
      ctx.lineWidth = 1;
      for (let i = 0; i <= 3; i++) {
        const y = (H / 3) * i;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(W, y);
        ctx.stroke();
      }

      // Waveform
      const gradient = ctx.createLinearGradient(0, 0, W, 0);
      gradient.addColorStop(0, "rgba(34,211,238,0)");
      gradient.addColorStop(0.5, "rgba(34,211,238,0.9)");
      gradient.addColorStop(1, "rgba(34,211,238,0)");

      ctx.strokeStyle = gradient;
      ctx.lineWidth = 2;
      ctx.shadowColor = "#22d3ee";
      ctx.shadowBlur = 6;

      ctx.beginPath();
      const t = timeRef.current;

      for (let x = 0; x < W; x++) {
        const p = x / W;
        let y = H / 2;

        if (target.classification === "Drone") {
          // High-frequency periodic
          y =
            H / 2 +
            Math.sin(p * 2 * Math.PI * 6 + t) * H * 0.28 +
            Math.sin(p * 2 * Math.PI * 3 + t * 1.3) * H * 0.1 +
            (Math.random() - 0.5) * H * 0.04;
        } else if (target.classification === "Bird") {
          // Erratic low-frequency
          y =
            H / 2 +
            Math.sin(p * 2 * Math.PI * 1.5 + t) *
              H *
              0.2 *
              (1 + 0.5 * Math.sin(p * 4 * Math.PI + t * 0.7)) +
            (Math.random() - 0.5) * H * 0.35;
        } else {
          // Smooth aircraft
          y =
            H / 2 +
            Math.sin(p * 2 * Math.PI * 2 + t) * H * 0.15 +
            Math.sin(p * 2 * Math.PI * 0.5 + t * 0.5) * H * 0.05;
        }

        if (x === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }

      ctx.stroke();
      ctx.shadowBlur = 0;

      timeRef.current += isDrone ? 0.12 : 0.04;
      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [target]);

  return (
    <div
      style={{ background: "rgba(15,23,42,0.8)" }}
      className="rounded overflow-hidden"
    >
      <canvas ref={canvasRef} width={280} height={72} />
    </div>
  );
}

// ROE - Rules of Engagement Panel
function ROEPanel({ target }: { target: AirTarget | null }) {
  const zoneType = target?.zone_type ?? "OPEN";
  const legalBasis = target?.legal_basis ?? "";
  const authorizedResponses = target?.authorized_responses ?? [];
  const prohibitedResponses = target?.prohibited_responses ?? [];
  const reportingRequired = target?.reporting_required ?? false;
  const roeConfidence = target?.roe_confidence ?? 1.0;

  // Determine status based on response availability
  const hasAuthorized = authorizedResponses.length > 0;
  const isMonitorOnly = authorizedResponses.length === 1 && authorizedResponses[0] === "Monitor Only";
  
  const statusColor = isMonitorOnly ? "#4ade80" : hasAuthorized ? "#fb923c" : "#f43f5e";
  const statusIcon = isMonitorOnly ? <CheckCircle size={14} /> : hasAuthorized ? <AlertTriangle size={14} /> : <XCircle size={14} />;
  const statusText = isMonitorOnly ? "CLEARED" : hasAuthorized ? "RESTRICTED" : "NO RESPONSE";

  return (
    <div
      style={{
        background: "rgba(13,20,32,0.7)",
        backdropFilter: "blur(12px)",
        border: `1px solid ${statusColor}40`,
      }}
      className="rounded-lg p-4 flex flex-col gap-3"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Gavel size={14} style={{ color: statusColor }} />
          <h2 className="font-mono text-xs uppercase tracking-widest" style={{ color: statusColor }}>
            RULES OF ENGAGEMENT
          </h2>
        </div>
        <div
          style={{
            background: `${statusColor}1A`,
            border: `1px solid ${statusColor}40`,
          }}
          className="px-2 py-1 rounded-sm flex items-center gap-1"
        >
          {statusIcon}
          <span className="font-mono text-[10px] font-bold" style={{ color: statusColor }}>
            {statusText}
          </span>
        </div>
      </div>

      {/* Content */}
      {!target ? (
        <div
          style={{ background: "rgba(15,23,42,0.8)" }}
          className="h-[100px] rounded flex items-center justify-center"
        >
          <span className="font-mono text-xs text-[#334155]">
            — WAITING FOR TARGET —
          </span>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {/* Zone Info */}
          <div className="flex flex-col gap-1">
            <span className="font-mono text-[10px] text-[#64748b] uppercase">Zone Classification</span>
            <div className="flex items-center gap-2">
              <FileText size={12} className="text-[#94a3b8]" />
              <span className="font-mono text-xs text-[#e2e8f0]">{zoneType}</span>
            </div>
          </div>

          {/* Legal Basis */}
          {legalBasis && (
            <div className="flex flex-col gap-1">
              <span className="font-mono text-[10px] text-[#64748b] uppercase">Legal Basis</span>
              <span className="font-mono text-[10px] text-[#94a3b8] leading-tight">
                {legalBasis}
              </span>
            </div>
          )}

          {/* Authorized Responses */}
          {authorizedResponses.length > 0 && (
            <div className="flex flex-col gap-1">
              <span className="font-mono text-[10px] text-[#64748b] uppercase">
                Authorized Responses
              </span>
              <div className="flex flex-wrap gap-1">
                {authorizedResponses.map((response, idx) => (
                  <span
                    key={idx}
                    className="font-mono text-[9px] px-1.5 py-0.5 rounded"
                    style={{
                      background: "rgba(74,222,128,0.15)",
                      color: "#4ade80",
                      border: "1px solid rgba(74,222,128,0.3)",
                    }}
                  >
                    {response}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Prohibited Responses */}
          {prohibitedResponses.length > 0 && (
            <div className="flex flex-col gap-1">
              <span className="font-mono text-[10px] text-[#64748b] uppercase">
                Prohibited
              </span>
              <div className="flex flex-wrap gap-1">
                {prohibitedResponses.map((response, idx) => (
                  <span
                    key={idx}
                    className="font-mono text-[9px] px-1.5 py-0.5 rounded"
                    style={{
                      background: "rgba(244,63,94,0.15)",
                      color: "#f43f5e",
                      border: "1px solid rgba(244,63,94,0.3)",
                    }}
                  >
                    {response}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Reporting Required */}
          {reportingRequired && (
            <div
              className="flex items-center gap-2 px-2 py-1.5 rounded"
              style={{ background: "rgba(251,191,36,0.1)", border: "1px solid rgba(251,191,36,0.3)" }}
            >
              <FileText size={12} style={{ color: "#fbbf24" }} />
              <span className="font-mono text-[10px]" style={{ color: "#fbbf24" }}>
                Reporting Required
              </span>
            </div>
          )}

          {/* Confidence */}
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] text-[#64748b]">ROE Confidence</span>
            <span className="font-mono text-[10px]" style={{ color: roeConfidence >= 0.9 ? "#4ade80" : roeConfidence >= 0.7 ? "#fbbf24" : "#f43f5e" }}>
              {(roeConfidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

// Deception Defense - Honeypot Airspace Panel
function DeceptionPanel({ target }: { target: AirTarget | null }) {
  const deceptionActive = target?.deception_active ?? false;
  const deceptionType = target?.deception_type ?? "";
  const cyberCatcherId = target?.cyber_catcher_id ?? "";
  const cyberCatcherTarget = target?.cyber_catcher_target;
  const deceptionStartTime = target?.deception_start_time ?? "";
  const deceptionTechnique = target?.deception_technique ?? "";

  const statusColor = deceptionActive ? "#f43f5e" : "#4ade80";
  const statusText = deceptionActive ? "ACTIVE" : "INACTIVE";
  const statusIcon = deceptionActive ? <AlertTriangle size={14} /> : <CheckCircle size={14} />;

  return (
    <div
      style={{
        background: "rgba(13,20,32,0.7)",
        backdropFilter: "blur(12px)",
        border: `1px solid ${statusColor}40`,
      }}
      className="rounded-lg p-4 flex flex-col gap-3"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Target size={14} style={{ color: statusColor }} />
          <h2 className="font-mono text-xs uppercase tracking-widest" style={{ color: statusColor }}>
            DECEPTION DEFENSE
          </h2>
        </div>
        <div
          style={{
            background: `${statusColor}1A`,
            border: `1px solid ${statusColor}40`,
          }}
          className="px-2 py-1 rounded-sm flex items-center gap-1"
        >
          {statusIcon}
          <span className="font-mono text-[10px] font-bold" style={{ color: statusColor }}>
            {statusText}
          </span>
        </div>
      </div>

      {/* Content */}
      {!target ? (
        <div
          style={{ background: "rgba(15,23,42,0.8)" }}
          className="h-[80px] rounded flex items-center justify-center"
        >
          <span className="font-mono text-xs text-[#334155]">
            — WAITING FOR TARGET —
          </span>
        </div>
      ) : !deceptionActive ? (
        <div className="flex flex-col gap-2">
          <div
            style={{ background: "rgba(74,222,128,0.1)" }}
            className="p-3 rounded border border-green-500/20"
          >
            <div className="flex items-center gap-2">
              <CheckCircle size={14} className="text-green-400" />
              <span className="font-mono text-xs text-green-400">
                No active deception operation
              </span>
            </div>
            <p className="font-mono text-[10px] text-[#64748b] mt-1">
              Target is not being targeted by deception systems
            </p>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {/* Deception Type */}
          <div className="flex flex-col gap-1">
            <span className="font-mono text-[10px] text-[#64748b] uppercase">Deception Type</span>
            <div className="flex items-center gap-2">
              <Zap size={12} className="text-red-400" />
              <span className="font-mono text-xs text-[#e2e8f0]">{deceptionType || "HYBRID"}</span>
            </div>
          </div>

          {/* Cyber-Catcher */}
          {cyberCatcherId && (
            <div className="flex flex-col gap-1">
              <span className="font-mono text-[10px] text-[#64748b] uppercase">Lure Target</span>
              <div className="flex items-center gap-2">
                <MapPin size={12} className="text-orange-400" />
                <span className="font-mono text-xs text-[#e2e8f0]">{cyberCatcherId}</span>
              </div>
              {cyberCatcherTarget && (
                <span className="font-mono text-[10px] text-[#64748b] ml-4">
                  [{cyberCatcherTarget.lat.toFixed(4)}, {cyberCatcherTarget.lon.toFixed(4)}]
                </span>
              )}
            </div>
          )}

          {/* Technique */}
          {deceptionTechnique && (
            <div className="flex flex-col gap-1">
              <span className="font-mono text-[10px] text-[#64748b] uppercase">Technique</span>
              <div className="flex items-center gap-2">
                <Wifi size={12} className="text-purple-400" />
                <span className="font-mono text-xs text-[#e2e8f0]">{deceptionTechnique}</span>
              </div>
            </div>
          )}

          {/* Start Time */}
          {deceptionStartTime && (
            <div className="flex flex-col gap-1">
              <span className="font-mono text-[10px] text-[#64748b] uppercase">Activated</span>
              <span className="font-mono text-xs text-[#94a3b8]">
                {deceptionStartTime}
              </span>
            </div>
          )}

          {/* Status Alert */}
          <div
            style={{ background: "rgba(244,63,94,0.1)" }}
            className="p-3 rounded border border-red-500/20"
          >
            <div className="flex items-center gap-2">
              <AlertTriangle size={14} className="text-red-400" />
              <span className="font-mono text-xs text-red-400 font-bold">
                DECEPTION IN PROGRESS
              </span>
            </div>
            <p className="font-mono text-[10px] text-[#64748b] mt-1">
              Target navigation is being manipulated to land at Cyber-Catcher
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function CommanderXAIBox({
  target,
  onConfirm,
}: {
  target: AirTarget | null;
  onConfirm: (targetId: string) => void;
}) {
  const xaiText = getXAIRecommendation(target);
  const [isHovering, setIsHovering] = useState(false);

  return (
    <div
      style={{
        background: "rgba(251,146,60,0.06)",
        border: "1px solid rgba(251,146,60,0.25)",
        minHeight: "260px",
      }}
      className="rounded-lg p-4 flex flex-col gap-3"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot size={14} className="text-[#fb923c]" />
          <h2 className="font-mono text-xs uppercase tracking-widest text-[#fb923c]">
            COMMANDER XAI
          </h2>
        </div>
        <div
          style={{
            background: "rgba(251,146,60,0.15)",
            border: "1px solid rgba(251,146,60,0.35)",
          }}
          className="px-1.5 py-0.5 rounded-sm"
        >
          <span className="font-mono text-[10px] text-[#fb923c]">AUTO</span>
        </div>
      </div>

      {/* XAI Message Display */}
      <div
        style={{
          background: "rgba(15,23,42,0.5)",
          border: "1px solid rgba(251,146,60,0.15)",
          scrollbarWidth: "thin",
          scrollbarColor: "#1e293b transparent",
        }}
        className="flex-1 rounded p-3 overflow-y-auto"
      >
        <p className="font-mono text-xs leading-relaxed text-[#d1d5db]">
          {xaiText}
        </p>
      </div>

      {/* Confirm Button */}
      <button
        disabled={!target}
        onMouseEnter={() => setIsHovering(true)}
        onMouseLeave={() => setIsHovering(false)}
        onClick={() => target && onConfirm(target.id)}
        style={{
          background: target
            ? isHovering
              ? "rgba(251,146,60,0.35)"
              : "rgba(251,146,60,0.2)"
            : "rgba(30,41,59,0.5)",
          border: target
            ? "1px solid rgba(251,146,60,0.5)"
            : "1px solid rgba(255,255,255,0.06)",
          color: target ? "#fb923c" : "#334155",
          cursor: target ? "pointer" : "not-allowed",
          transition: "all 0.2s ease",
        }}
        className="w-full px-3 py-2 rounded flex items-center justify-center gap-2 font-mono text-xs font-bold tracking-wider"
      >
        <CheckCircle size={14} />
        <span>CONFIRM RECOMMENDATION</span>
        <ChevronRight size={14} />
      </button>
    </div>
  );
}

// Zero-Trust Flight ID - Physics Verification Panel
function ZeroTrustPanel({ target }: { target: AirTarget | null }) {
  const isVerified = target?.physics_verified ?? true;
  const spoofingFlags = target?.spoofing_flags ?? [];
  const trustScore = target?.digital_identity_trust ?? 1.0;
  const violations = target?.physics_violations ?? [];
  const motorRpm = target?.motor_rpm_detected;

  // Determine status color based on verification
  const statusColor = !isVerified ? "#f43f5e" : spoofingFlags.length > 0 ? "#fb923c" : "#4ade80";
  const statusIcon = !isVerified ? <AlertTriangle size={14} /> : <Shield size={14} />;
  const statusText = !isVerified ? "SPOOFING DETECTED" : spoofingFlags.length > 0 ? "FLAGGED" : "PHYSICS VERIFIED";

  return (
    <div
      style={{
        background: "rgba(13,20,32,0.7)",
        backdropFilter: "blur(12px)",
        border: `1px solid ${!isVerified ? "rgba(244,63,94,0.4)" : "rgba(255,255,255,0.07)"}`,
      }}
      className="rounded-lg p-4 flex flex-col gap-3"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield size={14} style={{ color: statusColor }} />
          <h2 className="font-mono text-xs uppercase tracking-widest" style={{ color: statusColor }}>
            ZERO-TRUST FLIGHT ID
          </h2>
        </div>
        <div
          style={{
            background: `${statusColor}1A`,
            border: `1px solid ${statusColor}40`,
          }}
          className="px-2 py-1 rounded-sm flex items-center gap-1"
        >
          {statusIcon}
          <span className="font-mono text-[10px] font-bold" style={{ color: statusColor }}>
            {statusText}
          </span>
        </div>
      </div>

      {/* Content */}
      {!target ? (
        <div
          style={{ background: "rgba(15,23,42,0.8)" }}
          className="h-[100px] rounded flex items-center justify-center"
        >
          <span className="font-mono text-xs text-[#334155]">
            — WAITING FOR TARGET —
          </span>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {/* Trust Score Bar */}
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs text-[#64748b]">Identity Trust</span>
              <span className="font-mono text-xs font-bold" style={{ color: statusColor }}>
                {(trustScore * 100).toFixed(0)}%
              </span>
            </div>
            <div
              style={{ background: "rgba(30,41,59,0.8)" }}
              className="h-2 rounded-full overflow-hidden"
            >
              <div
                style={{
                  width: `${trustScore * 100}%`,
                  background: statusColor,
                  transition: "width 0.3s ease",
                }}
                className="h-full rounded-full"
              />
            </div>
          </div>

          {/* Spoofing Flags */}
          {spoofingFlags.length > 0 && (
            <div className="flex flex-col gap-1">
              <span className="font-mono text-xs text-[#f43f5e]">Violations Detected:</span>
              {spoofingFlags.map((flag, idx) => (
                <div
                  key={idx}
                  style={{ background: "rgba(244,63,94,0.1)", border: "1px solid rgba(244,63,94,0.2)" }}
                  className="px-2 py-1 rounded flex items-center gap-2"
                >
                  <AlertTriangle size={10} className="text-[#f43f5e]" />
                  <span className="font-mono text-[10px] text-[#f1f5f9]">{flag}</span>
                </div>
              ))}
            </div>
          )}

          {/* Motor RPM Detection */}
          {motorRpm && (
            <div className="flex items-center gap-2">
              <Radio size={12} className="text-[#f43f5e]" />
              <span className="font-mono text-xs text-[#64748b]">Motor Signature:</span>
              <span className="font-mono text-xs font-bold text-[#f43f5e]">
                {motorRpm.toFixed(0)} RPM
              </span>
            </div>
          )}

          {/* Physics Violations */}
          {violations.length > 0 && (
            <div
              style={{ background: "rgba(15,23,42,0.5)" }}
              className="rounded p-2 max-h-[80px] overflow-y-auto"
            >
              {violations.map((v, idx) => (
                <div key={idx} className="font-mono text-[10px] text-[#94a3b8] leading-relaxed">
                  • {v}
                </div>
              ))}
            </div>
          )}

          {/* Verified Status */}
          {isVerified && spoofingFlags.length === 0 && (
            <div
              style={{ background: "rgba(74,222,128,0.1)", border: "1px solid rgba(74,222,128,0.2)" }}
              className="rounded p-2 flex items-center gap-2"
            >
              <Shield size={14} className="text-[#4ade80]" />
              <span className="font-mono text-xs text-[#4ade80]">
                All physics constraints verified. Digital identity trusted.
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
