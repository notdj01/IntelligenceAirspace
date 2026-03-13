import logging
import math
from typing import Dict, List, Tuple

from agents.state import AirspaceState, TargetMetadata, RiskLevel, TargetLabel, TargetSource
from agents.no_fly_zones import NO_FLY_ZONES, NoFlyZone

logger = logging.getLogger(__name__)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def _base_risk_from_label(label: TargetLabel) -> float:
    if label in (TargetLabel.MILITARY, TargetLabel.STEALTH):
        return 70.0
    if label in (
        TargetLabel.DRONE_DJI,
        TargetLabel.DRONE_PARROT,
        TargetLabel.DRONE_GENERIC,
        TargetLabel.QUADCOPTER,
        TargetLabel.RC_PLANE,
    ):
        return 40.0
    if label == TargetLabel.UNIDENTIFIED:
        return 60.0
    if label == TargetLabel.HELICOPTER:
        return 35.0
    if label in (TargetLabel.BIRD, TargetLabel.WEATHER_BALLOON):
        return 5.0
    return 20.0


def _level_from_score(score: float) -> RiskLevel:
    if score >= 75:
        return RiskLevel.CRITICAL
    if score >= 50:
        return RiskLevel.HIGH
    if score >= 25:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _compare_levels(a: RiskLevel, b: RiskLevel) -> RiskLevel:
    order = {
        RiskLevel.LOW: 0,
        RiskLevel.MEDIUM: 1,
        RiskLevel.HIGH: 2,
        RiskLevel.CRITICAL: 3,
    }
    return a if order[a] >= order[b] else b


def _distance_to_nearest_nfz(t: TargetMetadata) -> Tuple[float, NoFlyZone | None]:
    best_d = float("inf")
    best_zone: NoFlyZone | None = None
    for zone in NO_FLY_ZONES:
        d = _haversine_km(t.latitude, t.longitude, zone.lat, zone.lon)
        if d < best_d:
            best_d = d
            best_zone = zone
    return best_d, best_zone


def _compute_risk(t: TargetMetadata) -> Tuple[float, RiskLevel, List[str]]:
    reasons: List[str] = []

    score = _base_risk_from_label(t.label)
    reasons.append(f"Label={t.label.value} → base {score:.1f}")

    # ──────────────────────────────────────────────────────────────────────────
    # ZERO-TRUST FLIGHT ID: Physics Verification Risk Impact
    # ──────────────────────────────────────────────────────────────────────────
    # Note: We no longer apply heavy multipliers for physics verification failures
    # because this causes over-escalation. Instead, we just flag them for awareness.
    # The spoofing flags are still recorded and displayed in the UI.
    spoofing_flags = getattr(t, 'spoofing_flags', []) or []
    physics_verified = getattr(t, 'physics_verified', True)
    digital_identity_trust = getattr(t, 'digital_identity_trust', 1.0)
    
    if not physics_verified and spoofing_flags:
        # Instead of multiplying risk, just add a small penalty
        # and log the flags for display in UI
        score += 10.0
        reasons.append(f"⚠️ Physics verification issues detected ({len(spoofing_flags)} flags)")
    elif digital_identity_trust < 1.0 and digital_identity_trust > 0.5:
        # Minor penalty for reduced trust
        score += 5.0
        reasons.append(f"⚠️ Reduced trust score ({digital_identity_trust:.2f})")

    # Proximity to no-fly zones
    d_km, zone = _distance_to_nearest_nfz(t)
    nfz_points = 0.0
    inside_nfz = False

    # Commercial / OpenSky aircraft
    is_commercial = (
        t.source == TargetSource.OPENSKY
        or bool(t.icao24)
        or t.label == TargetLabel.COMMERCIAL
    )

    if zone is not None:
        inside_nfz = d_km <= zone.radius_km
        near = zone.radius_km < d_km <= zone.radius_km * 2.0
        buffer = zone.radius_km * 2.0 < d_km <= zone.radius_km * 4.0

        if inside_nfz:
            nfz_points = 40.0
        elif near:
            nfz_points = 25.0
        elif buffer:
            nfz_points = 10.0

        if nfz_points > 0:
            if is_commercial:
                nfz_points *= 0.5
            score += nfz_points
            reasons.append(
                f"Proximity to NFZ '{zone.name}' (d={d_km:.1f}km, R={zone.radius_km:.1f}km)"
                f" → +{nfz_points:.1f}"
            )

    # If this is a commercial/OpenSky aircraft that is NOT inside a NFZ and
    # not already labelled anomalous, keep it in a low-risk band regardless
    # of speed/altitude. Normal, lawful commercial flights should stay green.
    # NOTE: This does NOT apply if physics verification failed (potential spoofing)
    spoofing_flags = getattr(t, 'spoofing_flags', []) or []
    physics_verified = getattr(t, 'physics_verified', True)
    
    if (is_commercial and not inside_nfz 
        and getattr(t, "anomaly_label", "Normal") == "Normal"
        and physics_verified):  # Don't clamp risk if physics verification failed
        score = min(score, 20.0)
        reasons.append("Commercial/OpenSky normal corridor → clamped to low risk")
        score = max(0.0, min(score, 100.0))
        level = _level_from_score(score)
        return score, level, reasons

    # Speed contribution (cap at 40 points)
    spd = max(t.velocity_ms, 0.0)
    if spd > 0:
        spd_norm = min(spd / 300.0, 1.0)
        spd_points = 40.0 * spd_norm
        score += spd_points
        reasons.append(f"Speed={spd:.1f}m/s → +{spd_points:.1f}")

    # Altitude contribution (cap at 20 points beyond 500m)
    alt = max(t.altitude_m, 0.0)
    if alt > 500.0:
        alt_norm = min((alt - 500.0) / 2000.0, 1.0)
        alt_points = 20.0 * alt_norm
        score += alt_points
        reasons.append(f"Altitude={alt:.0f}m → +{alt_points:.1f}")

    score = max(0.0, min(score, 100.0))
    level = _level_from_score(score)
    return score, level, reasons


def risk_assessment(state: AirspaceState) -> AirspaceState:
    """
    LangGraph node: compute risk_score for each target and adjust RiskLevel
    based on dynamics + proximity to Indian no-fly zones.
    """
    log: List[str] = list(state.get("agent_log", []))
    targets: Dict[str, TargetMetadata] = dict(state.get("active_targets", {}))

    updated: Dict[str, TargetMetadata] = {}
    escalated: List[str] = []

    for uid, t in targets.items():
        score, level_from_score, reasons = _compute_risk(t)
        old_level = t.risk
        new_level = _compare_levels(old_level, level_from_score)

        t.risk_score = score
        if reasons:
            # Extend classification path with risk reasons for XAI
            path = list(getattr(t, "classification_path", []))
            path.append(f"RiskAssessment: score={score:.1f}, level={new_level.value}")
            t.classification_path = path

        if new_level != old_level:
            escalated.append(f"{uid} ({old_level.value}→{new_level.value})")
            t.risk = new_level

        updated[uid] = t

    if escalated:
        log.append(
            "🛡️ Risk assessment escalated levels for: " + ", ".join(escalated)
        )

    return {
        **state,
        "active_targets": updated,
        "agent_log": log,
    }

