"""
fetch_data node — pulls live ADS-B from OpenSky and merges with simulated radar.
"""

import time
import uuid
import random
import logging
from typing import Dict, Any, List, Optional

from agents.state import AirspaceState, TargetMetadata, TargetLabel, RiskLevel, TargetSource

logger = logging.getLogger(__name__)

# Mach 0.8 ≈ 272 m/s at cruise altitude
MACH_0_8_MS = 272.0
# 5000 fpm in m/s
CLIMB_5000FPM_MS = 25.4

# Bounding box half-width in degrees (≈ 1500 km radius for all of India)
BBOX_DEG = 15.0


def _opensky_bbox(lat: float, lon: float, delta: float = BBOX_DEG):
    return (lat - delta, lat + delta, lon - delta, lon + delta)


def fetch_opensky(
    center_lat: float,
    center_lon: float,
    log: List[str],
    errors: List[str],
) -> Dict[str, TargetMetadata]:
    """
    Query OpenSky REST API for states within the bounding box.
    Falls back to an empty dict if network/API fails.
    """
    targets: Dict[str, TargetMetadata] = {}
    bbox = _opensky_bbox(center_lat, center_lon)

    try:
        import json
        import os
        import requests
        from datetime import datetime, timedelta
        
        cred_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "credentials.json")
        client_id, client_secret = None, None
        if os.path.exists(cred_path):
            try:
                with open(cred_path, "r") as f:
                    creds = json.load(f)
                    client_id = creds.get("clientId", creds.get("username"))
                    client_secret = creds.get("clientSecret", creds.get("password"))
            except Exception as e:
                log.append(f"⚠️ Credential load error: {e}")

        states = None

        if client_id and client_secret:
            # OAuth2 logic
            TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
            r = requests.post(TOKEN_URL, data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            })
            if r.status_code == 200:
                token = r.json().get("access_token")
                resp = requests.get(
                    "https://opensky-network.org/api/states/all",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"lamin": bbox[0], "lamax": bbox[1], "lomin": bbox[2], "lomax": bbox[3]}
                )
                if resp.status_code == 200:
                    states = resp.json()
                else:
                    log.append(f"⚠️ OpenSky authenticated fetch failed: {resp.status_code}")
            else:
                log.append(f"⚠️ OpenSky token fetch failed: {r.status_code}")
        
        if states is None:
            # Fallback to anonymous (will usually 429 after 400 requests)
            resp = requests.get(
                "https://opensky-network.org/api/states/all",
                params={"lamin": bbox[0], "lamax": bbox[1], "lomin": bbox[2], "lomax": bbox[3]}
            )
            if resp.status_code == 200:
                states = resp.json()

        if states is None or not states.get("states"):
            log.append("⚡ OpenSky: No ADS-B returns in bounding box.")
            return targets

        now = time.time()
        for s in states.get("states", []):
            if s[1] is None or s[2] is None:
                continue
            uid = f"ads_{s[0]}"
            meta = TargetMetadata(
                uid=uid,
                icao24=str(s[0]),
                callsign=(str(s[1]).strip()) if s[1] else None,
                latitude=float(s[6]) if s[6] is not None else 0.0,
                longitude=float(s[5]) if s[5] is not None else 0.0,
                altitude_m=float(s[7] if s[7] is not None else (s[13] if s[13] is not None else 0.0)),
                baro_altitude_m=float(s[7]) if s[7] is not None else None,
                velocity_ms=float(s[9]) if s[9] is not None else 0.0,
                climb_rate_ms=float(s[11]) if s[11] is not None else 0.0,
                heading=float(s[10]) if s[10] is not None else 0.0,
                source=TargetSource.OPENSKY,
                last_seen=float(s[3] if s[3] else now),
                origin_country=str(s[2]) if s[2] else None,
                label=TargetLabel.UNKNOWN,
                risk=RiskLevel.LOW,
            )
            targets[uid] = meta

    except ImportError:
        errors.append("requests not installed; using simulation only.")
        log.append("⚠️  requests library missing — ADS-B feed disabled.")
    except Exception as e:
        errors.append(f"OpenSky fetch error: {e}")
        log.append(f"⚠️  OpenSky error: {e}")

    return targets


def fetch_simulated_radar(
    center_lat: float,
    center_lon: float,
    log: List[str],
    count: int = 6,
) -> Dict[str, TargetMetadata]:
    """
    Generate synthetic primary-radar returns that have NO transponder.
    These are the targets that will trigger the cascade classifier.
    """
    radar_targets: Dict[str, TargetMetadata] = {}
    now = time.time()

    # Mix of drone-like and bird-like profiles
    profiles = [
        # (velocity_ms, climb_ms, rcs_dbsm, signal_strength)
        (8,   1.5,  -15, "Moderate"),   # small drone
        (4,   0.5,  -22, "Weak"),       # small bird / nano-drone
        (12,  2.0,  -10, "Moderate"),   # larger drone
        (280, 30.0,  10, "Strong"),     # high-performance / military sim
        (3,   0.3,  -28, "Weak"),       # stealth / very small
        (15,  3.0,   -8, "Strong"),     # RC plane
    ]

    random.seed(int(now) // 10)   # stable within 10-second window
    chosen = random.sample(profiles, min(count, len(profiles)))

    for i, (vel, climb, rcs, sig) in enumerate(chosen):
        uid = f"rad_{i:03d}"
        lat = center_lat + random.uniform(-1.5, 1.5)
        lon = center_lon + random.uniform(-1.5, 1.5)
        meta = TargetMetadata(
            uid=uid,
            icao24=None,
            latitude=lat,
            longitude=lon,
            altitude_m=random.uniform(50, 3000),
            velocity_ms=float(vel),
            climb_rate_ms=float(climb),
            heading=random.uniform(0, 360),
            source=TargetSource.RADAR,
            radar_rcs=float(rcs),
            radar_signal_strength=sig,
            last_seen=now,
            label=TargetLabel.UNKNOWN,
            risk=RiskLevel.LOW,
        )
        radar_targets[uid] = meta

    log.append(f"🔭 Simulated Radar: {len(radar_targets)} primary returns generated.")
    return radar_targets


def fetch_manual_injections(
    injections: List[Dict[str, Any]],
    log: List[str],
) -> Dict[str, TargetMetadata]:
    """Convert manually injected targets into TargetMetadata objects."""
    manual: Dict[str, TargetMetadata] = {}
    for inj in injections:
        uid = inj.get("uid") or f"man_{uuid.uuid4().hex[:6]}"
        meta = TargetMetadata(
            uid=uid,
            icao24=inj.get("icao24"),
            latitude=float(inj.get("latitude", 0)),
            longitude=float(inj.get("longitude", 0)),
            altitude_m=float(inj.get("altitude_m", 500)),
            velocity_ms=float(inj.get("velocity_ms", 10)),
            climb_rate_ms=float(inj.get("climb_rate_ms", 0)),
            heading=float(inj.get("heading", 0)),
            source=TargetSource.MANUAL,
            radar_signal_strength=inj.get("radar_signal_strength", "Moderate"),
            radar_rcs=inj.get("radar_rcs", -15.0),
            last_seen=time.time(),
            label=TargetLabel.UNKNOWN,
            risk=RiskLevel.LOW,
        )
        manual[uid] = meta
        log.append(
            f"🎯 Manual Injection: uid={uid} at ({meta.latitude:.3f}, {meta.longitude:.3f}) "
            f"alt={meta.altitude_m:.0f}m vel={meta.velocity_ms:.1f}m/s "
            f"signal={meta.radar_signal_strength}"
        )
    return manual


def fetch_spoofed_targets(
    center_lat: float,
    center_lon: float,
    log: List[str],
    include_spoofed: bool = True,
) -> Dict[str, TargetMetadata]:
    """
    Generate synthetic spoofed targets for Zero-Trust testing.
    
    These targets have intentionally mismatched physics properties:
    - "Bird" with drone-like RCS and velocity (motor signature)
    - "Aircraft" with impossible turn rates
    - "Drone" with phantom speed
    
    This function is called periodically to demonstrate the physics verification.
    NOTE: Uses fixed UIDs so targets are updated, not accumulated.
    """
    if not include_spoofed:
        return {}
    
    spoofed: Dict[str, TargetMetadata] = {}
    now = time.time()
    
    # Use FIXED UIDs so we update existing spoofed targets instead of creating new ones
    # Attack Type 1: Motor in Bird (identity hijack)
    uid1 = "spoof_motor_bird"
    spoofed[uid1] = TargetMetadata(
        uid=uid1,
        callsign="SPOOF-001",
        latitude=center_lat + random.uniform(-0.5, 0.5),
        longitude=center_lon + random.uniform(-0.5, 0.5),
        altitude_m=random.uniform(100, 500),
        velocity_ms=random.uniform(18, 25),  # Too fast for bird!
        climb_rate_ms=random.uniform(-2, 2),
        heading=random.uniform(0, 360),
        source=TargetSource.RADAR,
        radar_rcs=random.uniform(-5, 5),  # Much too high for bird!
        radar_signal_strength="Moderate",
        last_seen=now,
        label=TargetLabel.BIRD,  # Claim to be a bird
        risk=RiskLevel.LOW,
    )
    
    # Attack Type 2: Phantom aircraft (impossible maneuver)
    uid2 = "spoof_phantom_aircraft"
    spoofed[uid2] = TargetMetadata(
        uid=uid2,
        callsign="PHANTOM-01",
        latitude=center_lat + random.uniform(-1.0, 1.0),
        longitude=center_lon + random.uniform(-1.0, 1.0),
        altitude_m=random.uniform(1000, 5000),
        velocity_ms=200,  # Normal aircraft speed
        climb_rate_ms=random.uniform(45, 60),  # Impossible climb rate!
        heading=random.uniform(0, 360),
        source=TargetSource.RADAR,
        radar_rcs=random.uniform(5, 15),  # Aircraft-like RCS
        radar_signal_strength="Strong",
        last_seen=now,
        label=TargetLabel.COMMERCIAL,  # Claim to be commercial
        risk=RiskLevel.LOW,
    )
    
    # Attack Type 3: Category mismatch (wrong speed for type)
    uid3 = "spoof_category_mismatch"
    spoofed[uid3] = TargetMetadata(
        uid=uid3,
        callsign="CATEGORY-ERR",
        latitude=center_lat + random.uniform(-0.3, 0.3),
        longitude=center_lon + random.uniform(-0.3, 0.3),
        altitude_m=random.uniform(50, 200),
        velocity_ms=random.uniform(70, 90),  # Way too fast for drone!
        climb_rate_ms=random.uniform(-1, 1),
        heading=random.uniform(0, 360),
        source=TargetSource.RADAR,
        radar_rcs=random.uniform(-15, -5),
        radar_signal_strength="Moderate",
        last_seen=now,
        label=TargetLabel.QUADCOPTER,  # Claim to be quadcopter but fly like jet
        risk=RiskLevel.LOW,
    )
    
    log.append("🛡️ [Zero-Trust] Injected 3 synthetic spoofed targets for physics verification testing")
    return spoofed


# ──────────────────────────────────────────────────────────────────────────────
# LangGraph Node
# ──────────────────────────────────────────────────────────────────────────────

def fetch_data(state: AirspaceState) -> AirspaceState:
    """
    LangGraph node: populate active_targets from all data sources.
    Merges OpenSky ADS-B + simulated radar + manual injections.
    """
    log: List[str] = list(state.get("agent_log", []))
    errors: List[str] = list(state.get("errors", []))
    cycle = state.get("cycle_id", 0)

    log.append(f"━━━ Cycle #{cycle} — Data Acquisition Phase ━━━")

    center_lat = state.get("center_lat", 28.6139)
    center_lon = state.get("center_lon", 77.2090)

    # 1. Live ADS-B
    opensky_targets = fetch_opensky(center_lat, center_lon, log, errors)

    # 2. Simulated primary radar
    radar_targets = fetch_simulated_radar(center_lat, center_lon, log)

    # 3. Synthetic spoofed targets for Zero-Trust testing (DISABLED by default)
    # Enable via environment variable: ZERO_TRUST_DEMO=1
    import os
    enable_spoofed = os.environ.get("ZERO_TRUST_DEMO", "0") == "1"
    spoofed_targets = fetch_spoofed_targets(center_lat, center_lon, log, include_spoofed=enable_spoofed)

    # 4. Manual injections (one-shot — consumed after this cycle)
    manual_targets = fetch_manual_injections(
        state.get("manual_injections", []), log
    )

    # Merge: OpenSky wins on overlapping UIDs
    merged: Dict[str, TargetMetadata] = {}
    merged.update(radar_targets)
    merged.update(manual_targets)
    merged.update(spoofed_targets)
    merged.update(opensky_targets)

    # Preserve history from previous cycles
    prev_targets = state.get("active_targets", {})
    for uid, target in merged.items():
        if uid in prev_targets:
            # Check if it was serialised
            if isinstance(prev_targets[uid], dict):
                prev_hist_lat = prev_targets[uid].get("history_lat", [])
                prev_hist_lon = prev_targets[uid].get("history_lon", [])
                prev_hist_alt = prev_targets[uid].get("history_alt", [])
            else:
                prev_hist_lat = prev_targets[uid].history_lat
                prev_hist_lon = prev_targets[uid].history_lon
                prev_hist_alt = prev_targets[uid].history_alt
                
            target.history_lat = prev_hist_lat + [target.latitude]
            target.history_lon = prev_hist_lon + [target.longitude]
            target.history_alt = prev_hist_alt + [target.altitude_m]
        else:
            target.history_lat = [target.latitude]
            target.history_lon = [target.longitude]
            target.history_alt = [target.altitude_m]

    log.append(f"✅ Total targets after merge: {len(merged)}")

    return {
        **state,
        "active_targets": merged,
        "agent_log": log,
        "errors": errors,
        "manual_injections": [],   # consumed
    }
