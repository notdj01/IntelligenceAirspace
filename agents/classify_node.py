"""
classification_gate node — implements the 5-level cascading classification:

  Level 0 — Flight Dynamics Gate:
              Speed > Mach 0.8 OR climb_rate > 5000 fpm → Military/High-Performance

  Level 1 — Transponder Gate:
              ICAO24 present → Commercial (ADS-B confirmed)

  Level 2 — Radar Classifier:
              No transponder → call radar_classifier_tool (VGG16 / DIAT-μSAT)

  Level 3 — RF Fingerprinting:
              Radar says "Quadcopter"|"RC Plane" → call rf_fingerprint_tool (1-D CNN)

  Level 4 — Stealth Gate:
              Not in OpenSky AND radar_signal_strength == "Weak" → Stealth/Low-Observable

Risk assignment follows classification.
"""

import logging
from typing import Dict, List

from agents.state import (
    AirspaceState, TargetMetadata,
    TargetLabel, RiskLevel, TargetSource,
)
from tools.model_tools import radar_classifier_tool, rf_fingerprint_tool

logger = logging.getLogger(__name__)

# ── Thresholds ─────────────────────────────────────────────────────────────
MACH_0_8_MS       = 272.0   # m/s
CLIMB_5000FPM_MS  =  25.4   # m/s  (5000 ft/min → m/s)

# Map DIAT label strings to TargetLabel enum
_RADAR_LABEL_MAP = {
    "Quadcopter":   TargetLabel.QUADCOPTER,
    "Bionic Bird":  TargetLabel.BIONIC_BIRD,
    "Helicopter":   TargetLabel.HELICOPTER,
    "RC Plane":     TargetLabel.RC_PLANE,
}

# Map RF brand strings to TargetLabel enum
_RF_BRAND_MAP = {
    "DJI":             TargetLabel.DRONE_DJI,
    "Parrot":          TargetLabel.DRONE_PARROT,
    "Syma":            TargetLabel.DRONE_GENERIC,
    "Hubsan":          TargetLabel.DRONE_GENERIC,
    "Generic/Unknown": TargetLabel.DRONE_GENERIC,
}

# Labels that are "drone-class" and warrant RF fingerprinting
_DRONE_CLASS_LABELS = {TargetLabel.QUADCOPTER, TargetLabel.RC_PLANE}


def _assign_risk(t: TargetMetadata) -> RiskLevel:
    """Derive risk from final label + dynamics."""
    if t.label in (TargetLabel.MILITARY, TargetLabel.STEALTH):
        return RiskLevel.CRITICAL
    if t.label in (TargetLabel.DRONE_DJI, TargetLabel.DRONE_PARROT,
                   TargetLabel.DRONE_GENERIC, TargetLabel.QUADCOPTER,
                   TargetLabel.RC_PLANE):
        if t.altitude_m > 500 or t.velocity_ms > 30:
            return RiskLevel.HIGH
        return RiskLevel.MEDIUM
    if t.label == TargetLabel.UNIDENTIFIED:
        return RiskLevel.HIGH
    if t.label == TargetLabel.HELICOPTER:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _classify_target(t: TargetMetadata, log: List[str]) -> TargetMetadata:
    """Run the full cascade on a single target and return the annotated copy."""
    path = []

    # ── Level 0: Flight Dynamics Gate ────────────────────────────────────────
    # Only flag as Military if NO transponder (ICAO24) - otherwise it's a real aircraft
    # that might just be flying fast. Real commercial flights can exceed Mach 0.8.
    spd_hi   = t.velocity_ms   >= MACH_0_8_MS
    climb_hi = abs(t.climb_rate_ms) >= CLIMB_5000FPM_MS

    if (spd_hi or climb_hi) and not t.icao24:
        # No transponder + high speed/climb = potential military/hostile
        reason = []
        if spd_hi:
            reason.append(f"speed={t.velocity_ms:.0f}m/s > Mach 0.8")
        if climb_hi:
            reason.append(f"climb={t.climb_rate_ms:.1f}m/s > 5000fpm")
        path.append("L0: FlightDynamicsGate → MILITARY")
        log.append(
            f"  🚀 Target {t.uid}: {', '.join(reason)}. No transponder detected. "
            f"Labelling Military/High-Performance."
        )
        t.label      = TargetLabel.MILITARY
        t.confidence = 0.95
        t.risk       = RiskLevel.CRITICAL
        t.classification_path = path
        return t
    elif spd_hi or climb_hi:
        # Has transponder - likely just a fast commercial flight
        path.append("L0: FlightDynamicsGate → COMMERCIAL (transponder confirmed)")
        log.append(
            f"  ✈️  Target {t.uid}: High speed/climb but has transponder (ICAO24={t.icao24}). "
            f"Keeping as Commercial aircraft."
        )
        t.label      = TargetLabel.COMMERCIAL
        t.confidence = 0.99
        t.risk       = RiskLevel.LOW
        t.classification_path = path
        return t

    # ── Level 1: Transponder / ICAO24 Gate ───────────────────────────────────
    if t.icao24:
        path.append("L1: TransponderGate → COMMERCIAL")
        callsign_str = f" ({t.callsign})" if t.callsign else ""
        log.append(
            f"  ✈️  Target {t.uid}{callsign_str}: ICAO24={t.icao24} detected. "
            f"Labelling Commercial."
        )
        t.label      = TargetLabel.COMMERCIAL
        t.confidence = 0.99
        t.risk       = _assign_risk(t)
        t.classification_path = path
        return t

    # ── Level 4 (early): Stealth Gate (no transponder + weak radar signal) ───
    # Check this BEFORE radar classification to short-circuit processing.
    if t.radar_signal_strength == "Weak":
        path.append("L4: StealthGate (no transponder + weak signal) → STEALTH")
        log.append(
            f"  👻 Target {t.uid}: NOT in OpenSky AND radar signal is Weak. "
            f"Labelling Stealth/Low-Observable. Escalating to enhanced tracking."
        )
        t.label      = TargetLabel.STEALTH
        t.confidence = 0.78
        t.risk       = RiskLevel.CRITICAL
        t.classification_path = path
        return t

    # ── Level 2: Radar Classifier (VGG16 / DIAT-μSAT) ────────────────────────
    path.append("L2: RadarClassifier (VGG16)")
    log.append(
        f"  📡 Target {t.uid}: No transponder detected. "
        f"Escalating to Micro-Doppler analysis (VGG16 / DIAT-μSAT)..."
    )

    radar_label_str, radar_conf = radar_classifier_tool(uid=t.uid)
    radar_label = _RADAR_LABEL_MAP.get(radar_label_str, TargetLabel.UNIDENTIFIED)

    path.append(f"  → Radar says: {radar_label_str} ({radar_conf:.0%})")
    log.append(
        f"  🔍 Target {t.uid}: Micro-Doppler → '{radar_label_str}' "
        f"(confidence {radar_conf:.0%})."
    )

    t.label      = radar_label
    t.confidence = radar_conf

    # ── Level 3: RF Fingerprinting (drone-class only) ─────────────────────────
    if radar_label in _DRONE_CLASS_LABELS:
        path.append("L3: RF_Fingerprint (1D-CNN DroneRF)")
        log.append(
            f"  📻 Target {t.uid}: Identified as {radar_label_str}. "
            f"Escalating to RF Fingerprinting to identify drone brand..."
        )

        brand_str, brand_conf = rf_fingerprint_tool(uid=t.uid)
        brand_label = _RF_BRAND_MAP.get(brand_str, TargetLabel.DRONE_GENERIC)

        path.append(f"  → RF Fingerprint: {brand_str} ({brand_conf:.0%})")
        log.append(
            f"  🏷️  Target {t.uid}: RF Fingerprint → Brand='{brand_str}' "
            f"(confidence {brand_conf:.0%}). Final label: {brand_label.value}."
        )

        t.label      = brand_label
        t.confidence = round((radar_conf + brand_conf) / 2, 3)

    # Bionic Bird → relabel as Bird for display
    if radar_label == TargetLabel.BIONIC_BIRD:
        t.label = TargetLabel.BIRD

    t.risk = _assign_risk(t)
    t.classification_path = path
    return t


# ──────────────────────────────────────────────────────────────────────────────
# LangGraph Node
# ──────────────────────────────────────────────────────────────────────────────

def classification_gate(state: AirspaceState) -> AirspaceState:
    """
    LangGraph node: iterate over all active_targets and run the cascade.
    """
    log: List[str] = list(state.get("agent_log", []))
    targets: Dict[str, TargetMetadata] = dict(state.get("active_targets", {}))

    log.append(f"━━━ Classification Phase — {len(targets)} targets ━━━")

    # Prioritize OpenSky targets (they skip VGG16/RF fingerprinting expensive calls)
    # Separate and process all targets - no hard limit needed since OpenSky is cheap
    opensky_targets = {k: v for k, v in targets.items() if v.source == TargetSource.OPENSKY}
    other_targets = {k: v for k, v in targets.items() if v.source != TargetSource.OPENSKY}
    
    # Limit non-OpenSky (radar/manual) targets to prevent Torch OOM
    other_items = list(other_targets.items())[:100]
    if len(other_targets) > 100:
        log.append(f"⚠️ Truncating radar classification to {len(other_items)} targets to conserve memory.")
    
    # Merge all OpenSky + limited others
    target_items = list(opensky_targets.items()) + other_items
    
    log.append(f"📡 Processing {len(opensky_targets)} OpenSky (fast) + {len(other_items)} radar/manual targets")

    classified: Dict[str, TargetMetadata] = {}
    for uid, target in target_items:
        try:
            annotated = _classify_target(target, log)
            classified[uid] = annotated
        except Exception as e:
            log.append(f"  ❌ Target {uid}: classification error — {e}")
            target.label = TargetLabel.UNIDENTIFIED
            target.risk  = RiskLevel.HIGH
            classified[uid] = target

    # Summary
    from collections import Counter
    label_counts = Counter(t.label.value for t in classified.values())
    summary_parts = [f"{v}× {k}" for k, v in label_counts.items()]
    log.append(f"📊 Classification summary: {', '.join(summary_parts)}")

    critical = [uid for uid, t in classified.items() if t.risk == RiskLevel.CRITICAL]
    if critical:
        log.append(f"🚨 CRITICAL targets requiring attention: {critical}")

    return {
        **state,
        "active_targets": classified,
        "agent_log": log,
    }
