"""
LangGraph pipeline for the Agentic Airspace Monitoring System.

Graph topology (linear for Phase 1-3):

  START → fetch_data → classification_gate → END

Both nodes mutate and return the AirspaceState TypedDict.
"""

import logging
from typing import Dict, Any, List

from langgraph.graph import StateGraph, END

from agents.state import AirspaceState, TargetMetadata
from agents.fetch_node import fetch_data
from agents.predict_node import predict_trajectory
from agents.anomaly_node import detect_anomalies
from agents.classify_node import classification_gate
from agents.risk_node import risk_assessment
from agents.physics_verifier_node import physics_verifier
from agents.roe_node import roe_assessment

logger = logging.getLogger(__name__)


def build_graph() -> StateGraph:
    """Compile and return the LangGraph StateGraph."""
    builder = StateGraph(AirspaceState)

    builder.add_node("fetch_data",         fetch_data)
    builder.add_node("predict_trajectory", predict_trajectory)
    builder.add_node("anomaly_node",       detect_anomalies)
    builder.add_node("classification_gate", classification_gate)
    builder.add_node("physics_verifier",   physics_verifier)  # Zero-Trust Flight ID
    builder.add_node("risk_assessment",    risk_assessment)
    builder.add_node("roe_assessment",     roe_assessment)    # Legal-Agentic Co-Pilot

    builder.set_entry_point("fetch_data")
    builder.add_edge("fetch_data", "predict_trajectory")
    builder.add_edge("predict_trajectory", "anomaly_node")
    builder.add_edge("anomaly_node", "classification_gate")
    builder.add_edge("classification_gate", "physics_verifier")  # NEW: Physics verification
    builder.add_edge("physics_verifier", "risk_assessment")
    builder.add_edge("risk_assessment", "roe_assessment")      # NEW: ROE
    builder.add_edge("roe_assessment", END)

    graph = builder.compile()
    logger.info(
        "LangGraph compiled: fetch_data → predict_trajectory → anomaly_node → "
        "classification_gate → physics_verifier → risk_assessment → roe_assessment → END"
    )
    return graph


def run_cycle(
    center_lat: float,
    center_lon: float,
    cycle_id: int,
    manual_injections: List[Dict[str, Any]] = None,
    previous_log: List[str] = None,
    previous_targets: Dict[str, TargetMetadata] = None,
) -> AirspaceState:
    """
    Execute one full monitoring cycle.

    Parameters
    ----------
    center_lat/lon     : operator's coordinates for bounding box.
    cycle_id           : monotonic cycle counter.
    manual_injections  : list of dicts describing user-injected targets.
    previous_log       : log lines to carry over (capped to last 200 lines).
    previous_targets   : target dict from last cycle to preserve history.

    Returns
    -------
    Final AirspaceState after all nodes have run.
    """
    graph = build_graph()

    # Keep log bounded
    log_carry = (previous_log or [])[-200:]

    initial_state: AirspaceState = {
        "active_targets":    previous_targets or {},
        "agent_log":         log_carry,
        "center_lat":        center_lat,
        "center_lon":        center_lon,
        "manual_injections": manual_injections or [],
        "cycle_id":          cycle_id,
        "errors":            [],
    }

    try:
        final_state = graph.invoke(initial_state)
        return final_state
    except Exception as e:
        logger.exception("Graph execution failed")
        initial_state["agent_log"].append(f"💥 Graph error: {e}")
        initial_state["errors"].append(str(e))
        return initial_state
