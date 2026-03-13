"""
Deception Node - Active Deception Engine / Honeypot Airspace

This agent provides autonomous counter-drone capabilities through:
1. GPS Spoofing: Send false GPS coordinates to lure drones to Cyber-Catcher
2. Digital Honeypot: Create fake WiFi/control access points
3. Hybrid Approach: Combine both techniques for maximum effectiveness

The deception engine integrates with ROE to ensure legally authorized responses.
"""

import math
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from agents.state import AirspaceState, TargetMetadata, TargetLabel, RiskLevel

logger = logging.getLogger(__name__)


class DeceptionType(str, Enum):
    """Types of deception operations."""
    GPS_SPOOF = "GPS_SPOOF"
    HONEYPOT = "HONEYPOT"
    HYBRID = "HYBRID"
    NONE = "NONE"


class DeceptionStatus(str, Enum):
    """Status of deception operation."""
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class CyberCatcherZone:
    """
    Cyber-Catcher zones are safe landing zones where deceptive lures direct hostile drones.
    """
    id: str
    name: str
    lat: float
    lon: float
    radius_m: float = 500.0  # Effective radius in meters
    safety_rating: str = "HIGH"  # HIGH, MEDIUM, LOW
    active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "lat": self.lat,
            "lon": self.lon,
            "radius_m": self.radius_m,
            "safety_rating": self.safety_rating,
            "active": self.active,
        }


# Default Cyber-Catcher zones (configurable)
DEFAULT_CYBER_CATCHERS: List[CyberCatcherZone] = [
    CyberCatcherZone(
        id="CC_001",
        name="North Open Field",
        lat=21.1600,
        lon=79.1000,
        radius_m=800.0,
        safety_rating="HIGH",
    ),
    CyberCatcherZone(
        id="CC_002",
        name="South Industrial Zone",
        lat=21.1300,
        lon=79.0800,
        radius_m=600.0,
        safety_rating="HIGH",
    ),
    CyberCatcherZone(
        id="CC_003",
        name="East Empty Lot",
        lat=21.1458,
        lon=79.1200,
        radius_m=500.0,
        safety_rating="MEDIUM",
    ),
]


# Zone type to deception authorization mapping
DECEPTION_AUTHORIZATION: Dict[str, Dict[str, bool]] = {
    "PROHIBITED": {
        "GPS_SPOOF": True,
        "HONEYPOT": True,
        "HYBRID": True,
    },
    "CRITICAL_INFRA": {
        "GPS_SPOOF": True,
        "HONEYPOT": True,
        "HYBRID": True,
    },
    "RESTRICTED": {
        "GPS_SPOOF": True,
        "HONEYPOT": True,
        "HYBRID": True,
    },
    "RESIDENTIAL": {
        "GPS_SPOOF": False,
        "HONEYPOT": True,
        "HYBRID": False,
    },
    "AIRPORT_5KM": {
        "GPS_SPOOF": False,
        "HONEYPOT": False,
        "HYBRID": False,
    },
    "AIRPORT_10KM": {
        "GPS_SPOOF": False,
        "HONEYPOT": True,
        "HYBRID": False,
    },
    "MILITARY_BASE": {
        "GPS_SPOOF": True,
        "HONEYPOT": True,
        "HYBRID": True,
    },
    "PUBLIC_EVENT": {
        "GPS_SPOOF": False,
        "HONEYPOT": True,
        "HYBRID": False,
    },
    "OPEN": {
        "GPS_SPOOF": False,
        "HONEYPOT": False,
        "HYBRID": False,
    },
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two points."""
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def _calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate bearing from point 1 to point 2 in degrees."""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlon_rad = math.radians(lon2 - lon1)
    
    x = math.sin(dlon_rad) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad)
    
    bearing = math.atan2(x, y)
    return (math.degrees(bearing) + 360) % 360


def _generate_spoofed_path(
    start_lat: float,
    start_lon: float,
    target_lat: float,
    target_lon: float,
    num_points: int = 20,
    curve_factor: float = 0.3,
) -> List[Dict[str, float]]:
    """
    Generate a natural-looking GPS spoofing path using bezier-like interpolation.
    
    The path gradually deviates from the original course toward the Cyber-Catcher
    to avoid triggering anomaly detection in the drone's navigation system.
    """
    path = []
    
    for i in range(num_points):
        t = i / (num_points - 1)
        
        # Cubic ease-in-out for smooth transition
        if t < 0.5:
            ease = 2 * t * t
        else:
            ease = 1 - pow(-2 * t + 2, 2) / 2
        
        # Linear interpolation with curve factor
        lat = start_lat + (target_lat - start_lat) * ease * (1 + curve_factor * (1 - t))
        lon = start_lon + (target_lon - start_lon) * ease * (1 + curve_factor * (1 - t))
        
        path.append({
            "lat": lat,
            "lon": lon,
            "progress": ease,  # 0 to 1
        })
    
    return path


def _select_cyber_catcher(
    target: TargetMetadata,
    catchers: List[CyberCatcherZone],
    center_lat: float,
    center_lon: float,
) -> Optional[CyberCatcherZone]:
    """
    Select the optimal Cyber-Catcher zone for a target.
    
    Criteria:
    1. Must be farther from target's current position than minimum range
    2. Should be in a safe direction (away from protected zones)
    3. Prefer higher safety rating
    4. Prefer closer catchers (within operational range)
    """
    min_distance_km = 0.3  # Minimum 300m away from target (relaxed)
    max_distance_km = 200.0  # Maximum 200km operational range (covers large airspace)
    
    candidates = []
    
    for catcher in catchers:
        if not catcher.active:
            continue
            
        dist = _haversine_km(target.latitude, target.longitude, catcher.lat, catcher.lon)
        
        # Debug logging
        logger.debug(f"  Catcher {catcher.id}: dist={dist:.2f}km, active={catcher.active}, rating={catcher.safety_rating}")
        
        # Check distance constraints
        if dist < min_distance_km or dist > max_distance_km:
            logger.debug(f"    -> Skipped: distance {dist:.2f}km not in range [{min_distance_km}, {max_distance_km}]")
            continue
        
        # Calculate score (higher is better)
        # Prefer closer but not too close
        distance_score = 1.0 - (dist / max_distance_km)
        
        # Safety rating score
        safety_scores = {"HIGH": 1.0, "MEDIUM": 0.7, "LOW": 0.4}
        safety_score = safety_scores.get(catcher.safety_rating, 0.5)
        
        # Combined score
        total_score = distance_score * 0.6 + safety_score * 0.4
        
        candidates.append((catcher, total_score, dist))
    
    if not candidates:
        logger.debug(f"  No suitable catchers found for {target.uid}")
        return None
    
    # Sort by score and return best
    candidates.sort(key=lambda x: x[1], reverse=True)
    selected = candidates[0]
    logger.debug(f"  Selected {selected[0].id} at {selected[2]:.2f}km (score={selected[1]:.3f})")
    return selected[0]


def _is_deception_authorized(
    zone_type: str,
    deception_type: DeceptionType,
    authorized_responses: List[str],
    prohibited_responses: List[str],
) -> bool:
    """
    Check if deception is authorized based on zone type and ROE.
    """
    # First check zone-based authorization
    zone_auth = DECEPTION_AUTHORIZATION.get(zone_type, {})
    if not zone_auth.get(deception_type.value, False):
        return False
    
    # Then check ROE responses
    deception_type_str = deception_type.value
    
    # Check if specifically authorized or prohibited in ROE
    response_map = {
        DeceptionType.GPS_SPOOF: "GPS_SPOOF",
        DeceptionType.HONEYPOT: "DIGITAL_HONEYPOT",
        DeceptionType.HYBRID: "HYBRID",
    }
    
    roe_response = response_map.get(deception_type, "")
    
    if roe_response in prohibited_responses:
        return False
    
    # GPS_SPOOF must be in authorized_responses or authorized_responses contains "FULL_DEFENSE"
    if deception_type in (DeceptionType.GPS_SPOOF, DeceptionType.HYBRID):
        if "GPS_SPOOF" not in authorized_responses and "FULL_DEFENSE" not in authorized_responses:
            return False
    
    if deception_type in (DeceptionType.HONEYPOT, DeceptionType.HYBRID):
        if "DIGITAL_HONEYPOT" not in authorized_responses and "FULL_DEFENSE" not in authorized_responses:
            return False
    
    return True


def _should_activate_deception(
    target: TargetMetadata,
    zone_type: str,
) -> bool:
    """
    Determine if deception should be activated for a target.
    
    Criteria:
    1. Target must be a drone, unidentified, or high-risk
    2. Risk level must be HIGH or CRITICAL, OR risk score must be high (>50)
    3. Target must not already be under deception
    4. Target must be in motion (not stationary)
    """
    # Already under deception
    if getattr(target, 'deception_active', False):
        logger.debug(f"{target.uid}: Already under deception")
        return False
    
    # Must be in restricted zone (not OPEN or AIRPORT_5KM)
    if zone_type in ("OPEN", "AIRPORT_5KM"):
        logger.debug(f"{target.uid}: Zone {zone_type} not eligible for deception")
        return False
    
    # Must have velocity (not stationary)
    if target.velocity_ms < 1.0:  # Less than 1 m/s = stationary
        logger.debug(f"{target.uid}: Stationary (velocity={target.velocity_ms})")
        return False
    
    # Must be high risk OR high risk score
    risk = target.risk if isinstance(target.risk, RiskLevel) else RiskLevel.LOW
    risk_score = getattr(target, 'risk_score', 0.0)
    
    if risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        logger.info(f"{target.uid}: Risk {risk.value} - eligible for deception")
        return True
    
    # Also check for high risk score (even if label is wrong)
    if risk_score >= 50.0:
        logger.info(f"{target.uid}: Risk score {risk_score} - eligible for deception")
        return True
    
    logger.debug(f"{target.uid}: Not eligible - risk={risk.value}, score={risk_score}")
    return False


def _select_deception_type(
    zone_type: str,
    authorized_responses: List[str],
) -> DeceptionType:
    """
    Select the most appropriate deception type based on zone and authorization.
    """
    # Priority: HYBRID > GPS_SPOOF > HONEYPOT
    
    # Normalize responses - ROE returns display names, we need codes
    normalized = []
    for r in authorized_responses:
        r_lower = r.lower().replace(" ", "_")
        if "gps" in r_lower and "spoof" in r_lower:
            normalized.append("GPS_SPOOF")
        elif "honeypot" in r_lower or "digital" in r_lower:
            normalized.append("DIGITAL_HONEYPOT")
        elif "rf" in r_lower and "jam" in r_lower:
            normalized.append("RF_JAM")
        r_upper = r.upper()
        if r_upper in ("GPS_SPOOF", "DIGITAL_HONEYPOT", "RF_JAM", "FULL_DEFENSE"):
            normalized.append(r_upper)
    
    logger.info(f"[DECEPTION] Normalized responses: {authorized_responses} -> {normalized}")
    
    # Check for authorization
    if "GPS_SPOOF" in normalized or "FULL_DEFENSE" in normalized:
        if _is_deception_authorized_zone(zone_type, DeceptionType.HYBRID):
            logger.info(f"[DECEPTION] Selected HYBRID for zone {zone_type}")
            return DeceptionType.HYBRID
        if _is_deception_authorized_zone(zone_type, DeceptionType.GPS_SPOOF):
            logger.info(f"[DECEPTION] Selected GPS_SPOOF for zone {zone_type}")
            return DeceptionType.GPS_SPOOF
    
    if "DIGITAL_HONEYPOT" in normalized or "FULL_DEFENSE" in normalized:
        if _is_deception_authorized_zone(zone_type, DeceptionType.HONEYPOT):
            logger.info(f"[DECEPTION] Selected HONEYPOT for zone {zone_type}")
            return DeceptionType.HONEYPOT
    
    logger.info(f"[DECEPTION] No deception type selected for zone {zone_type}")
    return DeceptionType.NONE


def _is_deception_authorized_zone(zone_type: str, deception_type: DeceptionType) -> bool:
    """Check if deception type is authorized for zone type."""
    zone_auth = DECEPTION_AUTHORIZATION.get(zone_type, {})
    return zone_auth.get(deception_type.value, False)


def _activate_deception(
    target: TargetMetadata,
    catcher: CyberCatcherZone,
    deception_type: DeceptionType,
) -> TargetMetadata:
    """
    Activate deception on a target.
    """
    target.deception_active = True
    target.deception_type = deception_type.value
    target.cyber_catcher_id = catcher.id
    target.cyber_catcher_target = {"lat": catcher.lat, "lon": catcher.lon}
    target.deception_start_time = time.time()
    
    # Generate spoofed path for GPS spoofing
    if deception_type in (DeceptionType.GPS_SPOOF, DeceptionType.HYBRID):
        spoofed_path = _generate_spoofed_path(
            target.latitude,
            target.longitude,
            catcher.lat,
            catcher.lon,
        )
        target.spoofed_path = spoofed_path
        
        technique = f"Bezier GPS lure to {catcher.name} ({catcher.id})"
    else:
        technique = f"Digital Honeypot attraction to {catcher.name} ({catcher.id})"
    
    target.deception_technique = technique
    
    # Update classification path
    path = list(getattr(target, "classification_path", []))
    path.append(f"DECEPTION: {deception_type.value} → {catcher.id}")
    target.classification_path = path
    
    return target


def _process_target_for_deception(
    target: TargetMetadata,
    catchers: List[CyberCatcherZone],
    center_lat: float,
    center_lon: float,
) -> TargetMetadata:
    """
    Process a single target for potential deception activation.
    """
    zone_type = getattr(target, 'zone_type', 'OPEN')
    authorized = getattr(target, 'authorized_responses', [])
    prohibited = getattr(target, 'prohibited_responses', [])
    
    # Check if deception should be activated
    if not _should_activate_deception(target, zone_type):
        return target
    
    # Select best deception type
    deception_type = _select_deception_type(zone_type, authorized)
    if deception_type == DeceptionType.NONE:
        logger.info(f"[DECEPTION] No deception type selected for {target.uid}")
        return target
    
    # Verify authorization - normalize responses first
    normalized_auth = []
    for r in authorized:
        r_lower = r.lower().replace(" ", "_")
        if "gps" in r_lower and "spoof" in r_lower:
            normalized_auth.append("GPS_SPOOF")
        elif "honeypot" in r_lower or "digital" in r_lower:
            normalized_auth.append("DIGITAL_HONEYPOT")
        elif "rf" in r_lower and "jam" in r_lower:
            normalized_auth.append("RF_JAM")
    
    if not _is_deception_authorized(zone_type, deception_type, normalized_auth, []):
        logger.info(f"[DECEPTION] Deception not authorized for {target.uid}")
        return target
    
    # Select optimal Cyber-Catcher
    catcher = _select_cyber_catcher(target, catchers, center_lat, center_lon)
    if catcher is None:
        logger.info(f"[DECEPTION] No Cyber-Catcher available for {target.uid}")
        return target
    
    logger.info(f"[DECEPTION] Selected Cyber-Catcher {catcher.id} for {target.uid}")
    
    # Activate deception
    return _activate_deception(target, catcher, deception_type)


def deception_assessment(state: AirspaceState) -> AirspaceState:
    """
    LangGraph node: Active Deception Engine
    
    This node evaluates high-risk targets for deception operations and
    activates GPS spoofing or digital honeypot when authorized.
    
    Runs AFTER roe_assessment to ensure legal authorization.
    """
    log: List[str] = list(state.get("agent_log", []))
    targets: Dict[str, TargetMetadata] = dict(state.get("active_targets", {}))
    
    center_lat = state.get("center_lat", 28.6139)
    center_lon = state.get("center_lon", 77.2090)
    
    log.append("━━━ Deception Engine - Active Defense ━━━")
    
    # Use default catchers or could be loaded from config
    catchers = DEFAULT_CYBER_CATCHERS
    
    updated: Dict[str, TargetMetadata] = {}
    deception_activated = 0
    deception_authorized = 0
    
    for uid, target in targets.items():
        try:
            # Check ROE authorization first
            zone_type = getattr(target, 'zone_type', 'OPEN')
            authorized = getattr(target, 'authorized_responses', [])
            prohibited = getattr(target, 'prohibited_responses', [])
            
            # Skip if no authorized responses
            if not authorized:
                updated[uid] = target
                continue
            
            # Check if zone allows any deception
            zone_auth = DECEPTION_AUTHORIZATION.get(zone_type, {})
            if not any(zone_auth.values()):
                updated[uid] = target
                continue
            
            deception_authorized += 1
            
            # Log each target being evaluated
            risk = target.risk if isinstance(target.risk, RiskLevel) else RiskLevel.LOW
            risk_score = getattr(target, 'risk_score', 0.0)
            logger.info(f"[DECEPTION] Evaluating {uid}: zone={zone_type}, risk={risk.value}, score={risk_score:.1f}, vel={target.velocity_ms:.1f}")
            
            # Process for deception
            processed = _process_target_for_deception(target, catchers, center_lat, center_lon)
            
            if processed.deception_active:
                deception_activated += 1
                log.append(
                    f"🎯 DECEPTION ACTIVATED: {uid} → {processed.deception_type} "
                    f"(Catcher: {processed.cyber_catcher_id})"
                )
            
            updated[uid] = processed
            
        except Exception as e:
            logger.warning(f"Deception processing error for {uid}: {e}")
            updated[uid] = target
    
    log.append(f"✅ Deception assessment complete:")
    log.append(f"   - {deception_authorized} targets evaluated for deception")
    log.append(f"   - {deception_activated} deception operations activated")
    
    # Log available Cyber-Catchers
    active_catchers = [c.id for c in catchers if c.active]
    log.append(f"   - Active Cyber-Catchers: {', '.join(active_catchers)}")
    
    return {
        **state,
        "active_targets": updated,
        "agent_log": log,
        "available_catchers": [c.to_dict() for c in DEFAULT_CYBER_CATCHERS if c.active],
    }


def get_deception_status(state: AirspaceState) -> Dict[str, Any]:
    """
    Get current deception status for frontend display.
    """
    targets = state.get("active_targets", {})
    
    active_deceptions = []
    for uid, target in targets.items():
        if getattr(target, 'deception_active', False):
            active_deceptions.append({
                "target_id": uid,
                "deception_type": target.deception_type,
                "catcher_id": target.cyber_catcher_id,
                "catcher_target": target.cyber_catcher_target,
                "technique": target.deception_technique,
                "start_time": target.deception_start_time,
            })
    
    return {
        "active_operations": len(active_deceptions),
        "operations": active_deceptions,
        "available_catchers": [c.to_dict() for c in DEFAULT_CYBER_CATCHERS if c.active],
    }
