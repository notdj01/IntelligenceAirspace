import math

from agents.anomaly_node import detect_anomalies
from agents.state import AirspaceState, TargetMetadata, RiskLevel, TargetLabel


def _make_state_for_target(target: TargetMetadata) -> AirspaceState:
  return {
      "active_targets": {target.uid: target},
      "agent_log": [],
      "center_lat": target.latitude,
      "center_lon": target.longitude,
      "manual_injections": [],
      "cycle_id": 1,
      "errors": [],
  }


def test_heuristic_anomaly_high_altitude_jump():
  t = TargetMetadata(
      uid="T1",
      latitude=10.0,
      longitude=20.0,
      altitude_m=1000.0,
      history_lat=[10.0, 10.001],
      history_lon=[20.0, 20.001],
      history_alt=[1000.0, 1700.0],
      label=TargetLabel.DRONE,
      risk=RiskLevel.MEDIUM,
  )

  state = _make_state_for_target(t)
  out = detect_anomalies(state)
  t_out = out["active_targets"]["T1"]

  assert t_out.anomaly_score >= 0.5
  assert t_out.anomaly_label in {"Suspect", "Anomalous"}


def test_anomaly_fields_present_for_normal_target():
  t = TargetMetadata(
      uid="T2",
      latitude=10.0,
      longitude=20.0,
      altitude_m=1000.0,
      history_lat=[10.0, 10.0001],
      history_lon=[20.0, 20.0001],
      history_alt=[1000.0, 1005.0],
      label=TargetLabel.COMMERCIAL,
      risk=RiskLevel.LOW,
  )

  state = _make_state_for_target(t)
  out = detect_anomalies(state)
  t_out = out["active_targets"]["T2"]

  assert isinstance(t_out.anomaly_score, float)
  assert t_out.anomaly_label is not None
  assert isinstance(t_out.anomaly_reasons, list)

