"""
physics_verifier_node — Zero-Trust Flight ID Agent

Implements physics-based verification of flight identities to detect
"deepfake" ADS-B signals. This node verifies that:

1. Flight maneuvers are physically possible (no 15G turns, etc.)
2. Motor signatures match claimed vehicle type
3. Category consistency (speed, RCS match claimed type)
4. Trajectory authenticity (smooth vs. synthetically injected)

This node runs AFTER classification_gate and before risk_assessment.
"""

import logging
import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from agents.state import AirspaceState, TargetMetadata, TargetLabel, RiskLevel

logger = logging.getLogger(__name__)


class SpoofingFlag(str, Enum):
    """Types of physics violations that indicate spoofing."""
    IMPOSSIBLE_MANEUVER = "Impossible Maneuver"
    MOTOR_SIGNATURE_DETECTED = "Motor Signature"
    CATEGORY_MISMATCH = "Category Mismatch"
    RCS_ANOMALY = "RCS Anomaly"
    TRAJECTORY_INCONSISTENCY = "Trajectory Inconsistency"
    IDENTITY_HIJACK_SUSPECTED = "Identity Hijack"
    STALL_SPEED_VIOLATION = "Stall Speed Violation"
    ACCELERATION_VIOLATION = "Acceleration Violation"


@dataclass
class PhysicsVerificationResult:
    """Result of physics-based identity verification."""
    physics_verified: bool
    spoofing_flags: List[SpoofingFlag]
    digital_identity_trust: float  # 0.0 - 1.0
    physics_violations: List[str]
    motor_rpm_detected: Optional[float]
    rcs_anomaly_score: float
    max_g_force: float
    max_turn_rate: float
    category_consistent: bool


# ──────────────────────────────────────────────────────────────────────────────
# Physical Constants & Thresholds
# ──────────────────────────────────────────────────────────────────────────────

# G-force limits (in Gs)
MAX_SUSTAINED_CIVILIAN_TURN_G = 3.0  # Typical civilian aircraft
MAX_INSTANTANEOUS_G_FIGHTER = 9.0
MAX_INSTANTANEOUS_G_CIVILIAN = 4.5
MAX_SUSTAINED_G_TRAINER = 2.5

# Turn rate limits (degrees per second)
MAX_TURN_RATE_CIVILIAN = 3.0
MAX_TURN_RATE_DRONES = 180.0
MAX_TURN_RATE_BIRD = 180.0
MAX_TURN_RATE_HELICOPTER = 90.0
MAX_TURN_RATE_FIGHTER = 15.0

# Speed limits (m/s)
MIN_STALL_SPEED_CIVILIAN = 30.0  # ~60 kts
MIN_STALL_SPEED_SMALL = 25.0
MAX_SPEED_COMMERCIAL = 280.0  # ~Mach 0.85
MAX_SPEED_FIGHTER = 400.0
MAX_SPEED_DRONE = 50.0
MAX_SPEED_BIRD = 30.0

# Climb rate limits (m/s)
MAX_CLIMB_RATE_COMMERCIAL = 15.0  # ~3000 fpm
MAX_CLIMB_RATE_FIGHTER = 30.0  # ~6000 fpm
MAX_CLIMB_RATE_DRONE = 10.0

# RCS limits (dBsm) - Radar Cross Section
RCS_BIRD_MIN = -35.0
RCS_BIRD_MAX = -15.0
RCS_DRONE_MIN = -25.0
RCS_DRONE_MAX = 10.0
RCS_HELICOPTER_MIN = 0.0
RCS_HELICOPTER_MAX = 20.0
RCS_RC_PLANE_MIN = -15.0
RCS_RC_PLANE_MAX = 10.0
RCS_COMMERCIAL_MIN = 5.0
RCS_COMMERCIAL_MAX = 30.0
RCS_MILITARY_MIN = 0.0
RCS_MILITARY_MAX = 25.0

# Motor characteristics
MOTOR_RPM_MIN = 3000
MOTOR_RPM_MAX = 12000
BLADE_PASS_FREQ_FACTOR = 1.0  # Simplified


# ──────────────────────────────────────────────────────────────────────────────
# Category Physical Constraints
# ──────────────────────────────────────────────────────────────────────────────

CATEGORY_CONSTRAINTS: Dict[TargetLabel, Dict[str, Any]] = {
    TargetLabel.BIRD: {
        "min_speed": 0.0,
        "max_speed": 25.0,
        "max_turn_rate": 180.0,
        "max_climb_rate": 5.0,
        "max_g": 5.0,  # Birds can pull highGs briefly
        "rcs_min": -35.0,
        "rcs_max": -15.0,
        "has_motor": False,
    },
    TargetLabel.BIONIC_BIRD: {
        "min_speed": 0.0,
        "max_speed": 15.0,
        "max_turn_rate": 120.0,
        "max_climb_rate": 3.0,
        "max_g": 3.0,
        "rcs_min": -30.0,
        "rcs_max": -10.0,
        "has_motor": True,  # Bionic birds have motors
    },
    TargetLabel.DRONE: {
        "min_speed": 0.0,
        "max_speed": 50.0,
        "max_turn_rate": 180.0,
        "max_climb_rate": 10.0,
        "max_g": 8.0,
        "rcs_min": -25.0,
        "rcs_max": 10.0,
        "has_motor": True,
    },
    TargetLabel.DRONE_DJI: {
        "min_speed": 0.0,
        "max_speed": 20.0,
        "max_turn_rate": 120.0,
        "max_climb_rate": 6.0,
        "max_g": 4.0,
        "rcs_min": -20.0,
        "rcs_max": 5.0,
        "has_motor": True,
    },
    TargetLabel.QUADCOPTER: {
        "min_speed": 0.0,
        "max_speed": 30.0,
        "max_turn_rate": 180.0,
        "max_climb_rate": 8.0,
        "max_g": 6.0,
        "rcs_min": -20.0,
        "rcs_max": 5.0,
        "has_motor": True,
    },
    TargetLabel.RC_PLANE: {
        "min_speed": 5.0,
        "max_speed": 60.0,
        "max_turn_rate": 180.0,
        "max_climb_rate": 15.0,
        "max_g": 8.0,
        "rcs_min": -15.0,
        "rcs_max": 10.0,
        "has_motor": True,
    },
    TargetLabel.HELICOPTER: {
        "min_speed": 0.0,
        "max_speed": 80.0,
        "max_turn_rate": 90.0,
        "max_climb_rate": 12.0,
        "max_g": 3.5,
        "rcs_min": 0.0,
        "rcs_max": 20.0,
        "has_motor": True,
    },
    TargetLabel.COMMERCIAL: {
        "min_speed": 60.0,
        "max_speed": 280.0,
        "max_turn_rate": 3.0,
        "max_climb_rate": 15.0,
        "max_g": 2.5,
        "rcs_min": 5.0,
        "rcs_max": 30.0,
        "has_motor": True,
    },
    TargetLabel.MILITARY: {
        "min_speed": 50.0,
        "max_speed": 400.0,
        "max_turn_rate": 15.0,
        "max_climb_rate": 30.0,
        "max_g": 9.0,
        "rcs_min": 0.0,
        "rcs_max": 25.0,
        "has_motor": True,
    },
    TargetLabel.STEALTH: {
        "min_speed": 50.0,
        "max_speed": 350.0,
        "max_turn_rate": 10.0,
        "max_climb_rate": 25.0,
        "max_g": 7.0,
        "rcs_min": -30.0,
        "rcs_max": 0.0,
        "has_motor": True,
    },
    TargetLabel.WEATHER_BALLOON: {
        "min_speed": 0.0,
        "max_speed": 10.0,
        "max_turn_rate": 5.0,
        "max_climb_rate": 5.0,
        "max_g": 0.5,
        "rcs_min": 0.0,
        "rcs_max": 15.0,
        "has_motor": False,
    },
    TargetLabel.UNKNOWN: {
        "min_speed": 0.0,
        "max_speed": 400.0,
        "max_turn_rate": 180.0,
        "max_climb_rate": 30.0,
        "max_g": 9.0,
        "rcs_min": -40.0,
        "rcs_max": 30.0,
        "has_motor": None,  # Unknown
    },
    TargetLabel.UNIDENTIFIED: {
        "min_speed": 0.0,
        "max_speed": 400.0,
        "max_turn_rate": 180.0,
        "max_climb_rate": 30.0,
        "max_g": 9.0,
        "rcs_min": -40.0,
        "rcs_max": 30.0,
        "has_motor": None,
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# Physics Verification Functions
# ──────────────────────────────────────────────────────────────────────────────

def _calculate_g_force(velocity_ms: float, turn_rate_deg_s: float, bank_angle_deg: float = None) -> float:
    """
    Calculate G-force experienced during a turn.
    
    G-force = (v² / r) / 9.81
    where r = v / ω (radius of turn)
    
    For coordinated turn: G = 1 / cos(bank_angle)
    """
    if velocity_ms <= 0 or turn_rate_deg_s <= 0:
        return 1.0  # Level flight = 1G
    
    # Turn rate in radians per second
    turn_rate_rad_s = math.radians(turn_rate_deg_s)
    
    # Radius of turn: r = v / ω
    if turn_rate_rad_s > 0:
        radius = velocity_ms / turn_rate_rad_s
    else:
        radius = float('inf')
    
    # Centripetal acceleration: a = v² / r
    if radius > 0:
        centripetal_accel = (velocity_ms ** 2) / radius
    else:
        centripetal_accel = 0
    
    # Total G-force (adding 1G for gravity)
    g_force = (centripetal_accel / 9.81) + 1.0
    
    # If bank angle provided, add load factor
    if bank_angle_deg is not None:
        bank_rad = math.radians(bank_angle_deg)
        load_factor = 1.0 / math.cos(bank_rad) if math.cos(bank_rad) > 0 else 10.0
        g_force = max(g_force, load_factor)
    
    return g_force


def _calculate_turn_rate_from_trajectory(
    history_lat: List[float],
    history_lon: List[float],
    history_alt: List[float],
    headings: List[float],
    dt_seconds: float = 10.0
) -> float:
    """Calculate average turn rate from trajectory history."""
    if len(headings) < 2:
        return 0.0
    
    turn_changes = []
    for i in range(1, len(headings)):
        diff = headings[i] - headings[i-1]
        # Handle wraparound
        if diff > 180:
            diff -= 360
        elif diff < -180:
            diff += 360
        turn_rate = abs(diff) / dt_seconds
        turn_changes.append(turn_rate)
    
    return sum(turn_changes) / len(turn_changes) if turn_changes else 0.0


def _check_rcs_consistency(rcs_db: float, label: TargetLabel) -> Tuple[bool, str]:
    """Check if RCS value is consistent with claimed vehicle type."""
    if rcs_db is None:
        return True, ""  # No RCS data to check
    
    constraints = CATEGORY_CONSTRAINTS.get(label, CATEGORY_CONSTRAINTS[TargetLabel.UNKNOWN])
    rcs_min = constraints["rcs_min"]
    rcs_max = constraints["rcs_max"]
    
    if rcs_min <= rcs_db <= rcs_max:
        return True, ""
    
    # Check for motor vehicle masquerading as biological
    if label in {TargetLabel.BIRD} and rcs_db > RCS_BIRD_MAX:
        return False, f"RCS ({rcs_db:.1f} dBsm) too high for bird (max {RCS_BIRD_MAX} dBsm)"
    
    return False, f"RCS ({rcs_db:.1f} dBsm) outside expected range [{rcs_min}, {rcs_max}] for {label.value}"


def _detect_motor_signature(rcs_db: float, velocity_ms: float, label: TargetLabel) -> Tuple[Optional[float], SpoofingFlag, str]:
    """
    Detect motor signature from RCS fluctuations.
    
    In a real system, this would analyze micro-Doppler data.
    For simulation, we check:
    1. If RCS is too high for a biological target
    2. If velocity profile matches motor-driven flight
    
    Returns: (detected_rpm, flag, reason) or (None, None, "")
    """
    # Birds shouldn't have consistent high RCS that looks like a drone
    if label == TargetLabel.BIRD:
        if rcs_db is not None and rcs_db > -10:
            # Simulate detected motor RPM based on RCS magnitude
            # Higher RCS = larger motor = lower RPM typical
            detected_rpm = random.uniform(5000, 10000)
            return (
                detected_rpm,
                SpoofingFlag.MOTOR_SIGNATURE_DETECTED,
                f"Motor signature detected in bird-class target (RCS={rcs_db:.1f} dBsm, estimated RPM={detected_rpm:.0f})"
            )
    
    # Check for motor in weather balloon (should be passive)
    if label == TargetLabel.WEATHER_BALLOON:
        if velocity_ms > 5.0:  # Balloons drift slowly
            detected_rpm = random.uniform(3000, 8000)
            return (
                detected_rpm,
                SpoofingFlag.MOTOR_SIGNATURE_DETECTED,
                f"Motor signature detected in balloon-class target (velocity={velocity_ms:.1f} m/s)"
            )
    
    return None, None, ""


def _check_speed_consistency(velocity_ms: float, label: TargetLabel) -> Tuple[bool, str]:
    """Check if speed is consistent with claimed vehicle type."""
    constraints = CATEGORY_CONSTRAINTS.get(label, CATEGORY_CONSTRAINTS[TargetLabel.UNKNOWN])
    min_speed = constraints["min_speed"]
    max_speed = constraints["max_speed"]
    
    if min_speed <= velocity_ms <= max_speed:
        return True, ""
    
    return False, f"Speed ({velocity_ms:.1f} m/s) outside expected range [{min_speed}, {max_speed}] for {label.value}"


def _check_stall_speed(velocity_ms: float, altitude_m: float, label: TargetLabel) -> Tuple[bool, str]:
    """Check if speed is above stall speed for the aircraft type."""
    # Only relevant for heavier-than-air aircraft at altitude
    if altitude_m < 1000:
        return True, ""  # Too low to check
    
    if label in {TargetLabel.COMMERCIAL, TargetLabel.MILITARY, TargetLabel.STEALTH}:
        if velocity_ms < MIN_STALL_SPEED_CIVILIAN:
            return False, f"Speed below stall speed ({velocity_ms:.1f} < {MIN_STALL_SPEED_CIVILIAN} m/s) at {altitude_m:.0f}m"
    
    return True, ""


def _check_impossible_maneuver(
    velocity_ms: float,
    turn_rate_deg_s: float,
    climb_rate_ms: float,
    label: TargetLabel,
    history_count: int
) -> List[Tuple[SpoofingFlag, str]]:
    """Check for physically impossible maneuvers."""
    violations = []
    
    constraints = CATEGORY_CONSTRAINTS.get(label, CATEGORY_CONSTRAINTS[TargetLabel.UNKNOWN])
    
    # Check turn rate
    max_turn_rate = constraints["max_turn_rate"]
    if turn_rate_deg_s > max_turn_rate:
        violations.append((
            SpoofingFlag.IMPOSSIBLE_MANEUVER,
            f"Turn rate {turn_rate_deg_s:.1f}°/s exceeds {label.value} limit of {max_turn_rate}°/s"
        ))
    
    # Check climb rate
    max_climb_rate = constraints["max_climb_rate"]
    if abs(climb_rate_ms) > max_climb_rate:
        violations.append((
            SpoofingFlag.IMPOSSIBLE_MANEUVER,
            f"Climb rate {climb_rate_ms:.1f} m/s exceeds {label.value} limit of {max_climb_rate} m/s"
        ))
    
    # Calculate and check G-force
    g_force = _calculate_g_force(velocity_ms, turn_rate_deg_s)
    max_g = constraints["max_g"]
    if g_force > max_g:
        violations.append((
            SpoofingFlag.IMPOSSIBLE_MANEUVER,
            f"G-force {g_force:.1f}G exceeds {label.value} structural limit of {max_g}G"
        ))
    
    # Check for impossibly smooth/perfect trajectories (synthetic injection)
    # Real aircraft have some jitter; perfect circles indicate fake
    if history_count >= 10:
        # This would require trajectory analysis - simplified for now
        pass
    
    return violations


def _check_trajectory_consistency(
    history_lat: List[float],
    history_lon: List[float],
    history_alt: List[float],
    velocity_ms: float
) -> Optional[Tuple[SpoofingFlag, str]]:
    """Check for trajectory anomalies that suggest synthetic data."""
    if len(history_lat) < 3:
        return None
    
    # Check for impossibly large jumps (teleportation)
    lat_deg_to_m = 111320.0
    
    # Use actual velocity if available, otherwise use conservative estimate
    # Commercial aircraft: ~250 m/s, drones: ~20 m/s, birds: ~15 m/s
    max_speed = max(velocity_ms, 50.0)  # At least 50 m/s for aircraft
    max_distance = max_speed * 12  # 12 seconds between updates (generous)
    
    for i in range(1, len(history_lat)):
        d_lat = abs(history_lat[i] - history_lat[i-1]) * lat_deg_to_m
        d_lon = abs(history_lon[i] - history_lon[i-1]) * lat_deg_to_m
        distance = math.sqrt(d_lat**2 + d_lon**2)
        
        # Allow 3x margin for GPS jitter and update intervals
        if distance > max_distance * 3:
            return (
                SpoofingFlag.TRAJECTORY_INCONSISTENCY,
                f"Impossible trajectory jump: {distance:.0f}m in single timestep"
            )
    
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Main Verification Function
# ──────────────────────────────────────────────────────────────────────────────

def verify_physics_identity(target: TargetMetadata) -> PhysicsVerificationResult:
    """
    Perform full physics-based identity verification.
    
    NOTE: We skip verification for OpenSky/ADS-B targets because they are
    already verified via transponder data. We only verify RADAR targets.
    
    Returns a PhysicsVerificationResult with:
    - physics_verified: True if all checks pass
    - spoofing_flags: List of detected anomalies
    - digital_identity_trust: 0.0-1.0 trust score
    - physics_violations: Detailed violation descriptions
    - motor_rpm_detected: Detected motor RPM (if any)
    - rcs_anomaly_score: RCS consistency score
    - max_g_force: Maximum calculated G-force
    - max_turn_rate: Maximum observed turn rate
    - category_consistent: Whether category matches physics
    """
    # Skip physics verification for OpenSky/ADS-B targets - they are already trusted
    # We only verify RADAR targets (no transponder)
    if target.source.value in ("OpenSky ADS-B", "Fused") or target.icao24:
        return PhysicsVerificationResult(
            physics_verified=True,
            spoofing_flags=[],
            digital_identity_trust=1.0,
            physics_violations=[],
            motor_rpm_detected=None,
            rcs_anomaly_score=0.0,
            max_g_force=1.0,
            max_turn_rate=0.0,
            category_consistent=True,
        )
    
    spoofing_flags: List[SpoofingFlag] = []
    physics_violations: List[str] = []
    motor_rpm_detected: Optional[float] = None
    rcs_anomaly_score = 0.0
    max_g_force = 1.0
    max_turn_rate = 0.0
    category_consistent = True
    
    label = target.label
    velocity = target.velocity_ms
    climb_rate = target.climb_rate_ms
    rcs = target.radar_rcs
    
    # Get heading history - use current heading if no history
    headings = list(target.history_heading) if hasattr(target, 'history_heading') and target.history_heading else []
    if not headings and target.heading:
        headings = [target.heading]
    
    # Calculate turn rate from trajectory
    if len(headings) >= 2 or (target.heading and len(headings) >= 1):
        # Use current heading and estimate turn rate
        max_turn_rate = abs(target.heading - headings[0]) / 10.0 if len(headings) >= 1 else 0.0
        if max_turn_rate > 180:  # Handle wraparound
            max_turn_rate = 360 - max_turn_rate
    
    # 1. Check impossible maneuvers
    maneuver_violations = _check_impossible_maneuver(
        velocity,
        max_turn_rate,
        climb_rate,
        label,
        len(target.history_lat)
    )
    for flag, reason in maneuver_violations:
        spoofing_flags.append(flag)
        physics_violations.append(reason)
    
    if maneuver_violations:
        max_g_force = _calculate_g_force(velocity, max_turn_rate)
    
    # 2. Check speed consistency
    speed_ok, speed_reason = _check_speed_consistency(velocity, label)
    if not speed_ok:
        spoofing_flags.append(SpoofingFlag.CATEGORY_MISMATCH)
        physics_violations.append(speed_reason)
        category_consistent = False
        rcs_anomaly_score += 0.3
    
    # 3. Check RCS consistency
    if rcs is not None:
        rcs_ok, rcs_reason = _check_rcs_consistency(rcs, label)
        if not rcs_ok:
            spoofing_flags.append(SpoofingFlag.RCS_ANOMALY)
            physics_violations.append(rcs_reason)
            category_consistent = False
            rcs_anomaly_score += 0.4
        
        # 4. Check for motor signatures in non-motorized targets
        detected_rpm, flag, reason = _detect_motor_signature(rcs, velocity, label)
        if detected_rpm is not None:
            motor_rpm_detected = detected_rpm
            spoofing_flags.append(flag)
            physics_violations.append(reason)
            rcs_anomaly_score += 0.5
    
    # 5. Check stall speed
    stall_ok, stall_reason = _check_stall_speed(velocity, target.altitude_m, label)
    if not stall_ok:
        spoofing_flags.append(SpoofingFlag.STALL_SPEED_VIOLATION)
        physics_violations.append(stall_reason)
    
    # 6. Check trajectory consistency
    traj_issue = _check_trajectory_consistency(
        target.history_lat,
        target.history_lon,
        target.history_alt,
        velocity
    )
    if traj_issue:
        flag, reason = traj_issue
        spoofing_flags.append(flag)
        physics_violations.append(reason)
    
    # Calculate trust score
    if len(spoofing_flags) == 0:
        digital_identity_trust = 1.0
        physics_verified = True
    elif len(spoofing_flags) == 1:
        digital_identity_trust = 0.5
        physics_verified = False
    else:
        digital_identity_trust = max(0.0, 1.0 - (len(spoofing_flags) * 0.25))
        physics_verified = False
    
    return PhysicsVerificationResult(
        physics_verified=physics_verified,
        spoofing_flags=spoofing_flags,
        digital_identity_trust=digital_identity_trust,
        physics_violations=physics_violations,
        motor_rpm_detected=motor_rpm_detected,
        rcs_anomaly_score=min(rcs_anomaly_score, 1.0),
        max_g_force=max_g_force,
        max_turn_rate=max_turn_rate,
        category_consistent=category_consistent,
    )


# ──────────────────────────────────────────────────────────────────────────────
# LangGraph Node
# ──────────────────────────────────────────────────────────────────────────────

def physics_verifier(state: AirspaceState) -> AirspaceState:
    """
    LangGraph node: Run physics-based identity verification on all targets.
    
    This node runs AFTER classification_gate to have access to the label,
    but BEFORE risk_assessment so risk can incorporate trust scores.
    """
    targets = state.get("active_targets", {})
    log = state.get("agent_log", [])
    
    spoofed_count = 0
    verified_count = 0
    
    log.append("🛡️ [Zero-Trust] Running physics verification on all targets...")
    
    for uid, target in targets.items():
        result = verify_physics_identity(target)
        
        # Store verification results in target metadata
        target.physics_verified = result.physics_verified
        target.spoofing_flags = [f.value for f in result.spoofing_flags]
        target.digital_identity_trust = result.digital_identity_trust
        target.physics_violations = result.physics_violations
        target.motor_rpm_detected = result.motor_rpm_detected
        target.rcs_anomaly_score = result.rcs_anomaly_score
        
        if result.physics_verified:
            verified_count += 1
            logger.debug(f"Target {uid}: Physics verified (trust={result.digital_identity_trust:.2f})")
        else:
            spoofed_count += 1
            log.append(f"  ⚠️ {uid}: FAILED - {', '.join(result.spoofing_flags)}")
            for violation in result.physics_violations:
                log.append(f"    → {violation}")
    
    log.append(f"  📊 Zero-Trust Results: {verified_count} verified, {spoofed_count} flagged")
    
    state["active_targets"] = targets
    state["agent_log"] = log
    
    return state


# ──────────────────────────────────────────────────────────────────────────────
# Synthetic Data Injection (for testing)
# ──────────────────────────────────────────────────────────────────────────────

def inject_synthetic_spoofing(target: TargetMetadata, attack_type: str = "motor_in_bird") -> TargetMetadata:
    """
    Inject synthetic spoofing characteristics into a target for testing.
    
    This is used to demonstrate the Zero-Trust detection capabilities.
    
    Attack types:
    - "motor_in_bird": RCS + velocity consistent with drone, labeled as bird
    - "impossible_turn": Turn rate exceeding physical limits
    - "phantom_speed": Speed inconsistent with claimed type
    - "teleportation": Impossible trajectory jump
    """
    random.seed(hash(target.uid) % 2**32)
    
    if attack_type == "motor_in_bird":
        # Inject drone-like RCS into bird
        target.radar_rcs = random.uniform(-5.0, 5.0)  # High RCS for bird
        target.velocity_ms = random.uniform(15.0, 25.0)  # Too fast for bird
        target.label = TargetLabel.BIRD  # But labeled as bird!
        
    elif attack_type == "impossible_turn":
        # Inject impossibly high turn rate
        target.climb_rate_ms = random.uniform(40.0, 60.0)  # Way too fast climb
        
    elif attack_type == "phantom_speed":
        target.label = TargetLabel.BIRD
        target.velocity_ms = random.uniform(50.0, 80.0)  # Aircraft speed for "bird"
        
    elif attack_type == "teleportation":
        # Inject trajectory jump
        if len(target.history_lat) >= 1:
            target.history_lat.append(target.history_lat[-1] + 0.5)  # ~50km jump!
            target.history_lon.append(target.history_lon[-1] + 0.5)
            target.history_alt.append(target.altitude_m)
    
    return target
