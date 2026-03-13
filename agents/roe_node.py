"""
ROE Node - Rules of Engagement / Legal-Agentic Co-Pilot

This agent provides legally-grounded response recommendations based on:
- Airspace regulations (DGCA/FAA)
- Zone classifications (No-Fly Zones, Restricted Areas)
- Threat assessment (classification, risk level)
- Time of day restrictions

It acts as a RAG (Retrieval-Augmented Generation) system that:
1. Determines the zone type for each target
2. Retrieves applicable regulations
3. Generates legal recommendations for response
"""

import json
import math
import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import asdict

from agents.state import AirspaceState, TargetMetadata, TargetLabel, RiskLevel
from agents.no_fly_zones import NO_FLY_ZONES, NoFlyZone

logger = logging.getLogger(__name__)

# Load regulations and zone rules
REGULATIONS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "regulations.json")
ZONE_RULES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "zone_rules.json")

_regulations_cache = None
_zone_rules_cache = None


def _load_json(path: str, cache: Any) -> Dict:
    """Load and cache JSON file."""
    if cache is not None:
        return cache
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load {path}: {e}")
        return {}


def get_regulations() -> Dict:
    """Get cached regulations."""
    global _regulations_cache
    if _regulations_cache is None:
        _regulations_cache = _load_json(REGULATIONS_PATH, None)
    return _regulations_cache


def get_zone_rules() -> Dict:
    """Get cached zone rules."""
    global _zone_rules_cache
    if _zone_rules_cache is None:
        _zone_rules_cache = _load_json(ZONE_RULES_PATH, None)
    return _zone_rules_cache


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


def _classify_zone(
    target_lat: float,
    target_lon: float,
    center_lat: float,
    center_lon: float,
) -> Tuple[str, Optional[NoFlyZone], float]:
    """
    Classify the zone type for a target based on its location.
    
    Returns:
        Tuple of (zone_type_code, matched_nfz, distance_km)
    """
    zone_rules = get_zone_rules()
    zone_types = zone_rules.get("zone_types", {})
    
    # Check distance to each no-fly zone
    nearest_zone = None
    nearest_distance = float("inf")
    
    for nfz in NO_FLY_ZONES:
        dist = _haversine_km(target_lat, target_lon, nfz.lat, nfz.lon)
        if dist < nearest_distance:
            nearest_distance = dist
            nearest_zone = nfz
    
    if nearest_zone is not None:
        # Determine zone type based on NFZ type
        nfz_name_lower = nearest_zone.name.lower()
        
        if "nuclear" in nfz_name_lower or "atomic" in nfz_name_lower or "refinery" in nfz_name_lower:
            return ("CRITICAL_INFRA", nearest_zone, nearest_distance)
        elif "military" in nfz_name_lower:
            return ("MILITARY_BASE", nearest_zone, nearest_distance)
        elif "airport" in nfz_name_lower:
            if nearest_distance <= 5:
                return ("AIRPORT_5KM", nearest_zone, nearest_distance)
            else:
                return ("AIRPORT_10KM", nearest_zone, nearest_distance)
        else:
            # Default prohibited zone
            return ("PROHIBITED", nearest_zone, nearest_distance)
    
    # Check if in populated area (approximate based on distance from center)
    # This is a simplified check - in production, would use actual population data
    return ("OPEN", None, float("inf"))


def _map_label_to_threat(label: TargetLabel) -> str:
    """Map target label to threat category for response matrix."""
    label_str = label.value if isinstance(label, TargetLabel) else str(label)
    
    if "commercial" in label_str.lower() or "aircraft" in label_str.lower():
        return "COMMERCIAL"
    elif "military" in label_str.lower():
        return "MILITARY"
    elif "drone" in label_str.lower() or "quadcopter" in label_str.lower():
        return "DRONE_GENERIC"
    elif "stealth" in label_str.lower():
        return "STEALTH"
    elif "bird" in label_str.lower() or "balloon" in label_str.lower():
        return "NON_THREAT"
    else:
        return "UNIDENTIFIED"


def _is_known_aircraft(target: TargetMetadata) -> bool:
    """Check if target is a known/authorized aircraft (has transponder)."""
    return bool(target.icao24) or target.source.value == "OpenSky ADS-B"


def _get_roe_for_target(
    target: TargetMetadata,
    center_lat: float,
    center_lon: float,
) -> Dict[str, Any]:
    """
    Get Rules of Engagement recommendation for a target.
    
    This implements a simple RAG-like retrieval:
    1. Classify zone
    2. Get zone-specific rules
    3. Apply threat-response matrix
    4. Generate recommendation
    """
    zone_rules = get_zone_rules()
    zone_types = zone_rules.get("zone_types", {})
    threat_matrix = zone_rules.get("threat_response_matrix", {})
    
    # Step 1: Classify zone
    zone_type_code, matched_nfz, distance_km = _classify_zone(
        target.latitude, target.longitude, center_lat, center_lon
    )
    
    # Step 2: Get zone rules
    zone_info = zone_types.get(zone_type_code, {})
    
    # Step 3: Map threat category
    threat_category = _map_label_to_threat(target.label)
    risk_level = target.risk.value if isinstance(target.risk, RiskLevel) else str(target.risk)
    
    # Step 4: Get authorized/prohibited responses from zone rules
    authorized = list(zone_info.get("authorized_responses", []))
    prohibited = list(zone_info.get("prohibited_responses", []))
    legal_basis = zone_info.get("legal_basis", "No specific regulation found")
    reporting_required = zone_info.get("reporting_required", False)
    
    # Step 5: Check if this is a known aircraft (pre-authorized via transponder)
    is_known = _is_known_aircraft(target)
    
    # For known commercial aircraft with transponder, limit responses to monitoring
    # unless there's specific evidence of wrongdoing (high risk + spoofing indicators)
    if is_known and threat_category == "COMMERCIAL" and not getattr(target, 'physics_verified', True):
        # Suspected spoofed commercial - use threat matrix
        pass
    elif is_known and threat_category == "COMMERCIAL":
        # Known commercial flight - only monitor
        authorized = ["MONITOR"]
        prohibited = ["RF_JAM", "GPS_SPOOF", "KINETIC"]
        legal_basis = "Transponder confirmed - authorized civil aircraft"
    else:
        # Step 6: Apply threat matrix based on risk level for unknown/threat targets
        if threat_category in threat_matrix:
            threat_responses = threat_matrix[threat_category]
            if risk_level in threat_responses:
                # Use risk-appropriate responses from threat matrix
                authorized = threat_matrix[threat_category][risk_level].copy()
    
    # Finally, filter out prohibited responses from zone rules
    authorized = [r for r in authorized if r not in prohibited]
    
    # Step 6: Format response names for display
    response_names = {
        "RF_JAM": "RF Jamming",
        "GPS_SPOOF": "GPS Spoofing",
        "DIGITAL_HONEYPOT": "Digital Honeypot",
        "VISUAL_TRACKING": "Visual Tracking",
        "FORCED_LANDING": "Forced Landing",
        "KINETIC": "Kinetic Interdiction",
        "MONITOR": "Monitor Only",
        "REPORT_ATC": "Report to ATC",
        "REPORT_MILITARY": "Report to Military",
        "REPORT_AUTHORITIES": "Report to Authorities",
        "FULL_DEFENSE": "Full Defensive Measures Authorized",
    }
    
    authorized_display = [response_names.get(r, r) for r in authorized]
    prohibited_display = [response_names.get(r, r) for r in prohibited]
    
    # Step 7: Determine confidence (higher for precise zone match)
    confidence = 0.95 if matched_nfz is not None else 0.7
    
    # Generate recommendation text
    recommendation_text = _generate_recommendation_text(
        zone_info, authorized, prohibited, target, matched_nfz, distance_km
    )
    
    return {
        "zone_type": zone_info.get("name", zone_type_code),
        "zone_code": zone_type_code,
        "legal_basis": legal_basis,
        "authorized_responses": authorized_display,
        "prohibited_responses": prohibited_display,
        "reporting_required": reporting_required,
        "roe_confidence": confidence,
        "matched_nfz": matched_nfz.name if matched_nfz else None,
        "distance_to_nfz_km": round(distance_km, 2) if distance_km != float("inf") else None,
        "recommendation_text": recommendation_text,
    }


def _generate_recommendation_text(
    zone_info: Dict,
    authorized: List[str],
    prohibited: List[str],
    target: TargetMetadata,
    matched_nfz: Optional[NoFlyZone],
    distance_km: float,
) -> str:
    """Generate natural language recommendation."""
    
    threat_name = target.callsign or target.uid
    risk = target.risk.value if isinstance(target.risk, RiskLevel) else str(target.risk)
    zone_name = zone_info.get("name", "Unknown Zone")
    
    lines = []
    lines.append(f"THREAT ASSESSMENT: {threat_name} (Risk: {risk})")
    lines.append(f"LOCATION: {zone_name}")
    
    if matched_nfz and distance_km < zone_info.get("radius_km", 0):
        lines.append(f"⚠️ INSIDE NO-FLY ZONE: {matched_nfz.name}")
    elif matched_nfz and distance_km < 10:
        lines.append(f"⚠️ WITHIN {distance_km:.1f}km of {matched_nfz.name}")
    
    lines.append(f"\nLEGAL BASIS: {zone_info.get('legal_basis', 'N/A')}")
    
    if authorized:
        lines.append(f"\n✅ AUTHORIZED RESPONSES:")
        for resp in authorized[:3]:  # Top 3
            lines.append(f"  • {resp}")
    
    if prohibited:
        lines.append(f"\n🚫 PROHIBITED:")
        for resp in prohibited:
            lines.append(f"  • {resp}")
    
    if zone_info.get("reporting_required"):
        lines.append(f"\n📋 REPORTING REQUIRED")
    
    return "\n".join(lines)


def _process_target(
    target: TargetMetadata,
    center_lat: float,
    center_lon: float,
) -> TargetMetadata:
    """Process a single target and add ROE data."""
    
    roe = _get_roe_for_target(target, center_lat, center_lon)
    
    target.zone_type = roe.get("zone_code", "OPEN")
    target.legal_basis = roe.get("legal_basis", "")
    target.authorized_responses = roe.get("authorized_responses", [])
    target.prohibited_responses = roe.get("prohibited_responses", [])
    target.reporting_required = roe.get("reporting_required", False)
    target.roe_confidence = roe.get("roe_confidence", 1.0)
    
    return target


def roe_assessment(state: AirspaceState) -> AirspaceState:
    """
    LangGraph node: Generate Rules of Engagement recommendations.
    
    This node runs AFTER risk_assessment to provide legal context
    for response to each threat.
    """
    log: List[str] = list(state.get("agent_log", []))
    targets: Dict[str, TargetMetadata] = dict(state.get("active_targets", {}))
    
    center_lat = state.get("center_lat", 28.6139)
    center_lon = state.get("center_lon", 77.2090)
    
    log.append("━━━ ROE (Rules of Engagement) Assessment ━━━")
    
    updated: Dict[str, TargetMetadata] = {}
    critical_with_roe = 0
    
    for uid, target in targets.items():
        try:
            processed = _process_target(target, center_lat, center_lon)
            
            # Track high-risk targets with ROE
            risk = processed.risk if isinstance(processed.risk, RiskLevel) else RiskLevel.LOW
            if risk == RiskLevel.CRITICAL:
                critical_with_roe += 1
            
            # Add to classification path
            path = list(getattr(processed, "classification_path", []))
            path.append(f"ROE: zone={processed.zone_type}, authorized={len(processed.authorized_responses)}")
            processed.classification_path = path
            
            updated[uid] = processed
            
        except Exception as e:
            logger.warning(f"ROE processing error for {uid}: {e}")
            updated[uid] = target
    
    log.append(f"✅ ROE assessment complete: {len(updated)} targets processed")
    
    if critical_with_roe > 0:
        log.append(f"🎯 {critical_with_roe} CRITICAL targets have ROE recommendations")
    
    return {
        **state,
        "active_targets": updated,
        "agent_log": log,
    }
