"""
AirspaceState TypedDict and supporting data structures.
"""

from typing import TypedDict, Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class TargetLabel(str, Enum):
    UNKNOWN = "Unknown"
    COMMERCIAL = "Commercial"
    MILITARY = "Military/High-Performance"
    STEALTH = "Stealth/Low-Observable"
    DRONE = "Drone"
    DRONE_DJI = "Drone (DJI)"
    DRONE_PARROT = "Drone (Parrot)"
    DRONE_GENERIC = "Drone (Generic)"
    QUADCOPTER = "Quadcopter"
    BIONIC_BIRD = "Bionic Bird"
    HELICOPTER = "Helicopter"
    RC_PLANE = "RC Plane"
    BIRD = "Bird"
    WEATHER_BALLOON = "Weather Balloon"
    UNIDENTIFIED = "Unidentified"


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class TargetSource(str, Enum):
    OPENSKY = "OpenSky ADS-B"
    RADAR = "Primary Radar"
    MANUAL = "Manual Injection"
    FUSED = "Sensor Fusion"


@dataclass
class TargetMetadata:
    # Identity
    uid: str
    icao24: Optional[str] = None
    callsign: Optional[str] = None

    # Position
    latitude: float = 0.0
    longitude: float = 0.0
    altitude_m: float = 0.0          # meters
    baro_altitude_m: Optional[float] = None

    # Dynamics
    velocity_ms: float = 0.0         # m/s
    climb_rate_ms: float = 0.0       # m/s (vertical rate)
    heading: float = 0.0             # degrees

    # Classification
    label: TargetLabel = TargetLabel.UNKNOWN
    risk: RiskLevel = RiskLevel.LOW
    source: TargetSource = TargetSource.RADAR

    # Radar-specific
    radar_rcs: Optional[float] = None     # Radar Cross Section (dBsm)
    radar_signal_strength: Optional[str] = None  # "Strong", "Moderate", "Weak"

    # Provenance
    classification_path: List[str] = field(default_factory=list)
    confidence: float = 0.0
    last_seen: float = 0.0           # Unix timestamp
    origin_country: Optional[str] = None
    
    # Trajectory Data
    history_lat: List[float] = field(default_factory=list)
    history_lon: List[float] = field(default_factory=list)
    history_alt: List[float] = field(default_factory=list)
    predicted_trajectory: List[Dict[str, float]] = field(default_factory=list)

    # Anomaly Detection
    anomaly_score: float = 0.0
    anomaly_label: Optional[str] = None
    anomaly_reasons: List[str] = field(default_factory=list)
    
    # Zero-Trust Flight ID - Physics Verification
    physics_verified: bool = True                    # True if passed all physics checks
    spoofing_flags: List[str] = field(default_factory=list)  # List of detected spoofing indicators
    digital_identity_trust: float = 1.0              # 0.0 - 1.0 trust score
    physics_violations: List[str] = field(default_factory=list)  # Detailed violation reasons
    motor_rpm_detected: Optional[float] = None        # Detected motor RPM (if any)
    rcs_anomaly_score: float = 0.0                    # RCS consistency score
    
    # Risk Assessment
    risk_score: float = 0.0
    
    # Extended trajectory for physics verification
    history_heading: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uid": self.uid,
            "icao24": self.icao24,
            "callsign": self.callsign,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude_m": self.altitude_m,
            "baro_altitude_m": self.baro_altitude_m,
            "velocity_ms": self.velocity_ms,
            "climb_rate_ms": self.climb_rate_ms,
            "heading": self.heading,
            "label": self.label.value,
            "risk": self.risk.value,
            "source": self.source.value,
            "radar_rcs": self.radar_rcs,
            "radar_signal_strength": self.radar_signal_strength,
            "classification_path": self.classification_path,
            "confidence": self.confidence,
            "last_seen": self.last_seen,
            "origin_country": self.origin_country,
            "history_lat": self.history_lat,
            "history_lon": self.history_lon,
            "history_alt": self.history_alt,
            "history_heading": self.history_heading,
            "predicted_trajectory": self.predicted_trajectory,
            "anomaly_score": self.anomaly_score,
            "anomaly_label": self.anomaly_label,
            "anomaly_reasons": self.anomaly_reasons,
            "physics_verified": self.physics_verified,
            "spoofing_flags": self.spoofing_flags,
            "digital_identity_trust": self.digital_identity_trust,
            "physics_violations": self.physics_violations,
            "motor_rpm_detected": self.motor_rpm_detected,
            "rcs_anomaly_score": self.rcs_anomaly_score,
            "risk_score": self.risk_score,
        }


class AirspaceState(TypedDict):
    """
    Central state object passed through the LangGraph pipeline.
    active_targets: dict[uid -> TargetMetadata]
    agent_log: running list of reasoning steps
    center_lat/lon: operator's location for bounding box
    manual_injections: list of manually added targets pending classification
    cycle_id: monotonic counter for each 10-second refresh cycle
    errors: any non-fatal errors encountered this cycle
    """
    active_targets: Dict[str, TargetMetadata]
    agent_log: List[str]
    center_lat: float
    center_lon: float
    manual_injections: List[Dict[str, Any]]
    cycle_id: int
    errors: List[str]
