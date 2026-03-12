import logging
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agents.graph import run_cycle
from agents.state import TargetMetadata

logger = logging.getLogger(__name__)

app = FastAPI(title="Airspace Monitor Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class _BackendState:
    """
    Simple in-memory state holder that mirrors the old Streamlit session_state
    usage so we can re-use the existing LangGraph pipeline.
    """

    def __init__(self) -> None:
        self.cycle_id: int = 0
        self.center_lat: float = 21.1458
        self.center_lon: float = 79.0882
        self.agent_log: List[str] = []
        self.active_targets: Dict[str, TargetMetadata] = {}
        self.errors: List[str] = []
        self.manual_injections: List[Dict[str, Any]] = []

    def to_airspace_state(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "center_lat": self.center_lat,
            "center_lon": self.center_lon,
            "agent_log": self.agent_log,
            "active_targets": self.active_targets,
            "errors": self.errors,
            "manual_injections": self.manual_injections,
        }


backend_state = _BackendState()


def _run_backend_cycle() -> Dict[str, Any]:
    """
    Execute a LangGraph monitoring cycle and update the in-memory backend_state.
    """
    backend_state.cycle_id += 1

    result = run_cycle(
        center_lat=backend_state.center_lat,
        center_lon=backend_state.center_lon,
        cycle_id=backend_state.cycle_id,
        manual_injections=backend_state.manual_injections,
        previous_log=backend_state.agent_log,
        previous_targets=backend_state.active_targets,
    )

    backend_state.active_targets = result.get("active_targets", {})
    backend_state.agent_log = result.get("agent_log", [])
    backend_state.errors = result.get("errors", [])
    backend_state.manual_injections = []

    return result


def _target_to_frontend(t_uid: str, t: Any) -> Dict[str, Any]:
    """
    Convert internal TargetMetadata / dict into the Frontend `AirTarget` shape.
    """
    d: Dict[str, Any]
    if hasattr(t, "to_dict"):
        d = t.to_dict()  # type: ignore[assignment]
    elif isinstance(t, dict):
        d = t
    else:
        logger.warning("Unexpected target type for %s: %r", t_uid, type(t))
        return {
            "id": t_uid,
            "coords": [0.0, 0.0],
            "trajectory": [],
            "speed": 0.0,
            "adsb": False,
            "classification": "Unknown",
            "confidence": 0,
            "risk_level": "Low",
        }

    # Coords
    lat = float(d.get("latitude", 0.0))
    lon = float(d.get("longitude", 0.0))
    coords = [lat, lon]

    # Trajectory – use history if available, otherwise the current point
    traj: List[List[float]] = []
    hist_lat = d.get("history_lat") or []
    hist_lon = d.get("history_lon") or []
    for la, lo in zip(hist_lat, hist_lon):
        try:
            traj.append([float(la), float(lo)])
        except (TypeError, ValueError):
            continue
    if not traj:
        traj.append(coords)

    # Predicted trajectory – list of {lat, lon, alt}
    pred_coords: List[List[float]] = []
    for p in d.get("predicted_trajectory") or []:
        try:
            pred_coords.append([float(p["lat"]), float(p["lon"])])
        except (KeyError, TypeError, ValueError):
            continue

    # Classification mapping from rich backend labels to simplified frontend buckets
    label = str(d.get("label", "Unknown"))
    classification = "Unknown"
    if "Drone" in label or "Quadcopter" in label or "RC Plane" in label:
        classification = "Drone"
    elif "Bird" in label:
        classification = "Bird"
    elif label not in {"Unknown", "Unidentified"}:
        classification = "Aircraft"

    # Confidence – backend tends to use 0–1, frontend expects percentage
    raw_conf = d.get("confidence", 0.0)
    try:
        conf = float(raw_conf)
    except (TypeError, ValueError):
        conf = 0.0
    if conf <= 1.0:
        conf = conf * 100.0

    # Velocity – keep units consistent with existing frontend text ("kts" label)
    speed = float(d.get("velocity_ms", 0.0))

    # Risk level – already matches frontend union type ("Low" | "Medium" | "High" | "Critical")
    risk_level = str(d.get("risk", "Low"))

    # Anomaly information (optional)
    anomaly_score = float(d.get("anomaly_score", 0.0) or 0.0)
    anomaly_label = d.get("anomaly_label") or "Normal"
    anomaly_reasons = d.get("anomaly_reasons") or []
    risk_score = float(d.get("risk_score", 0.0) or 0.0)

    return {
        "id": d.get("callsign") or d.get("icao24") or t_uid,
        "coords": coords,
        "trajectory": traj,
        "predicted_trajectory": pred_coords,
        "speed": speed,
        "adsb": bool(d.get("icao24")),
        "classification": classification,
        "confidence": round(conf),
        "risk_level": risk_level,
        "anomaly_score": anomaly_score,
        "anomaly_label": anomaly_label,
        "anomaly_reasons": anomaly_reasons,
        "risk_score": risk_score,
    }


@app.get("/api/state")
def get_state() -> Dict[str, Any]:
    """
    Run one monitoring cycle and return the dashboard state in the
    structure expected by the new React frontend.
    """
    airspace = _run_backend_cycle()
    active_targets = airspace.get("active_targets", {})

    targets = [
        _target_to_frontend(uid, t) for uid, t in active_targets.items()
    ]

    anomalous_count = sum(
        1
        for t in targets
        if t.get("anomaly_label") == "Anomalous"
    )

    # For now, expose a simple synthetic agent status that always shows the
    # three core agents as active. This matches the existing React model.
    agents = {
        "sentry": "Active",
        "profiler": "Active",
        "commander": "Active",
    }

    return {
        "cycle_id": airspace.get("cycle_id", backend_state.cycle_id),
        "center_lat": airspace.get("center_lat", backend_state.center_lat),
        "center_lon": airspace.get("center_lon", backend_state.center_lon),
        "active_targets": targets,
        "agents": agents,
        "agent_log": airspace.get("agent_log", []),
        "errors": airspace.get("errors", []),
        "anomalous_target_count": anomalous_count,
    }


@app.post("/api/inject")
def inject_target(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Optional manual injection endpoint that mirrors the old Streamlit
    sidebar injection form. The next /api/state call will consume these
    injections.
    """
    backend_state.manual_injections.append(payload)
    return {"status": "queued", "uid": payload.get("uid")}


