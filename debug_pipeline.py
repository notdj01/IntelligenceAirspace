"""Debug target loss in pipeline."""
import requests
import json
import os

from agents.fetch_node import fetch_opensky
from agents.predict_node import predict_trajectory
from agents.anomaly_node import detect_anomalies
from agents.classify_node import classification_gate
from agents.physics_verifier_node import physics_verifier
from agents.risk_node import risk_assessment
from agents.state import AirspaceState

# Run fetch
log = []
errors = []
center_lat = 21.1458
center_lon = 79.0882

targets = fetch_opensky(center_lat, center_lon, log, errors)
print(f"After fetch_opensky: {len(targets)} targets")
print(f"  Logs: {log}")

# Run predict_trajectory
state: AirspaceState = {
    "active_targets": targets,
    "agent_log": log,
    "errors": errors,
    "center_lat": center_lat,
    "center_lon": center_lon,
    "cycle_id": 1,
}
state = predict_trajectory(state)
print(f"\nAfter predict_trajectory: {len(state.get('active_targets', {}))} targets")

# Run anomaly_node
state = detect_anomalies(state)
print(f"After anomaly_node: {len(state.get('active_targets', {}))} targets")

# Run classification_gate
state = classification_gate(state)
print(f"After classification_gate: {len(state.get('active_targets', {}))} targets")

# Run physics_verifier
state = physics_verifier(state)
print(f"After physics_verifier: {len(state.get('active_targets', {}))} targets")

# Run risk_assessment
state = risk_assessment(state)
print(f"After risk_assessment: {len(state.get('active_targets', {}))} targets")

# Show errors
print(f"\nErrors: {state.get('errors', [])}")
print(f"\nLogs: {state.get('agent_log', [])[-10:]}")
