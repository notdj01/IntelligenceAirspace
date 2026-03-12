"""
Agentic Airspace Monitoring System — Streamlit UI
"""

import time
import uuid
import logging
import sys
import os

# Make project root importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from streamlit_autorefresh import st_autorefresh   # type: ignore

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Page config (must be FIRST Streamlit call)
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AirWatch — Agentic Airspace Monitor",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# Inline CSS  (dark radar / military aesthetic)
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap');

  html, body, [class*="css"] {
      background-color: #060d18 !important;
      color: #c8daf0 !important;
      font-family: 'Rajdhani', sans-serif;
  }

  h1, h2, h3 { font-family: 'Share Tech Mono', monospace; color: #00ffe7 !important; }

  /* Sidebar */
  section[data-testid="stSidebar"] {
      background: #08111f !important;
      border-right: 1px solid #1a3350;
  }

  /* Metric cards */
  div[data-testid="metric-container"] {
      background: #0d1f35;
      border: 1px solid #1a3a5c;
      border-radius: 6px;
      padding: 12px;
  }

  /* Log box */
  .log-box {
      background: #040c18;
      border: 1px solid #0a2540;
      border-radius: 6px;
      padding: 12px;
      font-family: 'Share Tech Mono', monospace;
      font-size: 0.72rem;
      color: #7fbfff;
      max-height: 420px;
      overflow-y: auto;
      line-height: 1.6;
      white-space: pre-wrap;
  }

  /* Inject target form */
  .stTextInput > div > div > input, .stNumberInput input, .stSelectbox > div > div {
      background: #0d1f35 !important;
      color: #c8daf0 !important;
      border: 1px solid #1a3a5c !important;
  }

  /* Buttons */
  .stButton > button {
      background: #0a2540;
      color: #00ffe7;
      border: 1px solid #00ffe7;
      border-radius: 4px;
      font-family: 'Share Tech Mono', monospace;
      letter-spacing: 0.08em;
  }
  .stButton > button:hover {
      background: #00ffe7;
      color: #060d18;
  }

  /* Risk badge colours */
  .badge-low      { color: #00ff88; font-weight:700; }
  .badge-medium   { color: #ffd700; font-weight:700; }
  .badge-high     { color: #ff7700; font-weight:700; }
  .badge-critical { color: #ff2244; font-weight:700; animation: blink 1s step-start infinite; }

  @keyframes blink { 50% { opacity: 0; } }

  div[data-testid="stMetricValue"] { font-family: 'Share Tech Mono', monospace; font-size: 1.6rem; }

  /* Scrollbar */
  ::-webkit-scrollbar       { width: 6px; }
  ::-webkit-scrollbar-track { background: #060d18; }
  ::-webkit-scrollbar-thumb { background: #1a3a5c; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# State helpers
# ──────────────────────────────────────────────────────────────────────────────

def _init_session():
    defaults = {
        "cycle_id":          0,
        "agent_log":         [],
        "active_targets":    {},
        "manual_queue":      [],   # pending injections
        "center_lat":        21.1458,  # Nagpur (Central India)
        "center_lon":        79.0882,
        "selected_uid":      None,     # target selected for trajectory display
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _run_cycle():
    from agents.graph import run_cycle

    st.session_state.cycle_id += 1
    result = run_cycle(
        center_lat         = st.session_state.center_lat,
        center_lon         = st.session_state.center_lon,
        cycle_id           = st.session_state.cycle_id,
        manual_injections  = st.session_state.manual_queue,
        previous_log       = st.session_state.agent_log,
        previous_targets   = st.session_state.active_targets,
    )
    st.session_state.active_targets = result.get("active_targets", {})
    st.session_state.agent_log      = result.get("agent_log", [])
    st.session_state.manual_queue   = []   # consumed


# ──────────────────────────────────────────────────────────────────────────────
# Map helpers
# ──────────────────────────────────────────────────────────────────────────────

LABEL_COLOUR = {
    "Commercial":                [0,   200, 80],
    "Military/High-Performance": [255, 50,  50],
    "Stealth/Low-Observable":    [200, 0,   255],
    "Drone":                     [255, 80,  0],
    "Drone (DJI)":               [255, 80,  0],
    "Drone (Parrot)":            [255, 120, 0],
    "Drone (Generic)":           [255, 100, 20],
    "Quadcopter":                [255, 80,  0],
    "RC Plane":                  [255, 160, 0],
    "Helicopter":                [255, 200, 0],
    "Bird":                      [0,   140, 255],
    "Bionic Bird":               [0,   140, 255],
    "Weather Balloon":           [0,   200, 255],
    "Unidentified":              [255, 0,   200],
    "Unknown":                   [120, 120, 120],
}

RISK_ICON = {
    "Low":      "🟢",
    "Medium":   "🟡",
    "High":     "🟠",
    "Critical": "🔴",
}


def _build_map(targets: dict, selected_uid: str = None):
    """Return dataframes for the ScatterplotLayer and optional PathLayer."""
    import pandas as pd
    rows = []
    paths = []
    for uid, t in targets.items():
        # t can be TargetMetadata dataclass or dict (after serialisation)
        if hasattr(t, "to_dict"):
            d = t.to_dict()
        elif isinstance(t, dict):
            d = t
        else:
            continue
        colour = LABEL_COLOUR.get(d.get("label", "Unknown"), [120, 120, 120])
        is_selected = uid == selected_uid
        rows.append({
            "lat":      d.get("latitude",   0),
            "lon":      d.get("longitude",  0),
            "label":    d.get("label",      "Unknown"),
            "uid":      uid,
            "callsign": d.get("callsign")   or d.get("icao24") or uid,
            "alt":      d.get("altitude_m", 0),
            "speed":    d.get("velocity_ms",0),
            "risk":     d.get("risk",       "Low"),
            # Selected target is highlighted with bright gold ring
            "r": 255 if is_selected else colour[0],
            "g": 200 if is_selected else colour[1],
            "b": 0   if is_selected else colour[2],
            "radius": 12000 if is_selected else 6000,
        })
        
        # Only build path for the selected target
        if is_selected:
            preds = d.get("predicted_trajectory", [])
            if preds:
                path_points = [[d.get("longitude", 0), d.get("latitude", 0)]]
                for p in preds:
                    path_points.append([p["lon"], p["lat"]])
                paths.append({
                    "path":  path_points,
                    "color": [0, 255, 200, 230]
                })

    return pd.DataFrame(rows) if rows else None, pd.DataFrame(paths) if paths else None


def _render_map(df, df_paths=None):
    import pydeck as pdk

    layers = []
    
    if df_paths is not None and not df_paths.empty:
        path_layer = pdk.Layer(
            "PathLayer",
            data=df_paths,
            pickable=False,
            get_color="color",
            width_scale=20,
            width_min_pixels=3,
            get_path="path",
            get_width=6,
            dash_array=[5, 2],
        )
        layers.append(path_layer)

    if df is not None and not df.empty:
        layer = pdk.Layer(
            "ScatterplotLayer",
            id="scatter",
            data=df,
            get_position=["lon", "lat"],
            get_fill_color=["r", "g", "b", 200],
            get_radius="radius",
            pickable=True,
            auto_highlight=True,
            radius_scale=0.5,
            radius_min_pixels=6,
            radius_max_pixels=22,
        )
        text_layer = pdk.Layer(
            "TextLayer",
            data=df,
            get_position=["lon", "lat"],
            get_text="callsign",
            get_size=12,
            get_color=[200, 220, 255, 220],
            get_pixel_offset=[0, -18],
        )
        layers.extend([layer, text_layer])

    view = pdk.ViewState(
        latitude=st.session_state.center_lat,
        longitude=st.session_state.center_lon,
        zoom=7,
        pitch=30,
    )

    return pdk.Deck(
        layers=layers,
        initial_view_state=view,
        tooltip={"text": "{callsign}\nLabel: {label}\nRisk: {risk}\nAlt: {alt}m  Speed: {speed}m/s"},
        map_style="light",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Sidebar — agent log + inject form
# ──────────────────────────────────────────────────────────────────────────────

def _render_sidebar():
    with st.sidebar:
        st.markdown("## ✈️ AirWatch")
        st.caption(f"Cycle #{st.session_state.cycle_id}  |  "
                   f"{len(st.session_state.active_targets)} active targets")
        st.divider()

        # ── Agent log ────────────────────────────────────────────────────────
        st.markdown("### 🧠 Agent Reasoning Log")
        log_lines = st.session_state.agent_log[-80:]
        log_text  = "\n".join(log_lines)
        st.markdown(f'<div class="log-box">{log_text}</div>', unsafe_allow_html=True)

        st.divider()

        # ── Manual target injection ───────────────────────────────────────────
        st.markdown("### 🎯 Manual Target Injection")
        with st.expander("Inject a Radar-Only Target", expanded=False):
            inj_lat  = st.number_input("Latitude",  value=st.session_state.center_lat,
                                       format="%.4f", key="inj_lat")
            inj_lon  = st.number_input("Longitude", value=st.session_state.center_lon,
                                       format="%.4f", key="inj_lon")
            inj_alt  = st.number_input("Altitude (m)", value=500.0, key="inj_alt")
            inj_vel  = st.number_input("Speed (m/s)",  value=10.0,  key="inj_vel")
            inj_clmb = st.number_input("Climb Rate (m/s)", value=0.0, key="inj_clmb")
            inj_sig  = st.selectbox("Radar Signal Strength",
                                    ["Strong", "Moderate", "Weak"], index=1, key="inj_sig")
            inj_icao = st.text_input("ICAO24 (leave blank for no transponder)", value="",
                                     key="inj_icao")

            if st.button("🚀 Inject Target"):
                payload = {
                    "uid":                  f"man_{uuid.uuid4().hex[:6]}",
                    "latitude":             inj_lat,
                    "longitude":            inj_lon,
                    "altitude_m":           inj_alt,
                    "velocity_ms":          inj_vel,
                    "climb_rate_ms":        inj_clmb,
                    "radar_signal_strength": inj_sig,
                    "icao24":               inj_icao.strip() or None,
                }
                st.session_state.manual_queue.append(payload)
                st.success(f"Target {payload['uid']} queued for next cycle.")

        st.divider()

        # ── Operator position ─────────────────────────────────────────────────
        st.markdown("### 📍 Operator Centre")
        c1, c2 = st.columns(2)
        with c1:
            new_lat = st.number_input("Latitude",  value=st.session_state.center_lat,
                                      format="%.4f", key="op_lat")
        with c2:
            new_lon = st.number_input("Longitude", value=st.session_state.center_lon,
                                      format="%.4f", key="op_lon")
        if (new_lat != st.session_state.center_lat or
                new_lon != st.session_state.center_lon):
            st.session_state.center_lat = new_lat
            st.session_state.center_lon = new_lon

        st.caption(f"Bounding box: ±2° ({st.session_state.center_lat:.3f}, "
                   f"{st.session_state.center_lon:.3f})")


# ──────────────────────────────────────────────────────────────────────────────
# Main dashboard
# ──────────────────────────────────────────────────────────────────────────────

def _render_metrics(targets: dict):
    from agents.state import RiskLevel, TargetLabel

    counts = {
        "commercial":  0, "drone": 0, "military": 0,
        "stealth": 0, "unknown": 0, "critical": 0,
    }
    for uid, t in targets.items():
        d = t.to_dict() if hasattr(t, "to_dict") else t
        label = d.get("label", "Unknown")
        risk  = d.get("risk",  "Low")

        if "Commercial" in label:
            counts["commercial"] += 1
        elif "Military" in label:
            counts["military"] += 1
        elif "Stealth" in label:
            counts["stealth"] += 1
        elif any(x in label for x in ["Drone", "Quadcopter", "RC Plane"]):
            counts["drone"] += 1
        else:
            counts["unknown"] += 1

        if risk == "Critical":
            counts["critical"] += 1

    cols = st.columns(6)
    defs = [
        ("✈️ Commercial",    counts["commercial"], "#00ff88"),
        ("🚁 Drone / UAS",   counts["drone"],      "#ff7700"),
        ("🚀 Military",      counts["military"],   "#ff2244"),
        ("👻 Stealth",        counts["stealth"],    "#aa00ff"),
        ("❓ Unknown",        counts["unknown"],    "#888888"),
        ("🚨 CRITICAL",      counts["critical"],   "#ff2244"),
    ]
    for col, (label, val, colour) in zip(cols, defs):
        with col:
            st.metric(label, val)


def _render_target_table(targets: dict):
    """Render target registry as a clickable dataframe. Returns selected UID or None."""
    import pandas as pd

    rows = []
    uid_index = []  # preserve order for row→uid lookup
    for uid, t in targets.items():
        d = t.to_dict() if hasattr(t, "to_dict") else t
        risk = d.get("risk", "Low")
        risk_icon = RISK_ICON.get(risk, "⚪")
        rows.append({
            "Callsign":  d.get("callsign") or d.get("icao24") or uid,
            "Label":     d.get("label", "Unknown"),
            "Risk":      f"{risk_icon} {risk}",
            "Alt (m)":   f"{d.get('altitude_m', 0):.0f}",
            "Spd (m/s)": f"{d.get('velocity_ms', 0):.1f}",
            "Conf":      f"{d.get('confidence', 0):.0%}",
        })
        uid_index.append(uid)

    if not rows:
        st.info("No active targets this cycle.")
        return None

    df = pd.DataFrame(rows)
    st.caption("👆 Click a row to see its LSTM trajectory on the map")
    sel = st.dataframe(
        df,
        use_container_width=True,
        height=300,
        on_select="rerun",
        selection_mode="single-row",
        key="target_table_sel",
    )
    selected_rows = (sel.selection or {}).get("rows", []) if sel else []
    if selected_rows:
        return uid_index[selected_rows[0]]
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main():
    _init_session()

    # Auto-refresh every 20 seconds (returns current count)
    refresh_count = st_autorefresh(interval=20_000, key="autorefresh")

    # Run agent cycle on every refresh (or first load)
    if refresh_count > 0 or st.session_state.cycle_id == 0:
        with st.spinner("Running LangGraph classification cycle..."):
            _run_cycle()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    _render_sidebar()

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        '<h1 style="margin-bottom:0">⬡ AirWatch — Agentic Airspace Monitor</h1>',
        unsafe_allow_html=True
    )
    st.caption(
        f"Cycle #{st.session_state.cycle_id} · "
        f"Auto-refresh: 20s · "
        f"Centre: ({st.session_state.center_lat:.3f}, {st.session_state.center_lon:.3f}) · "
        f"Bounding Box ±2°"
    )

    st.divider()

    # ── Metric row ────────────────────────────────────────────────────────────
    _render_metrics(st.session_state.active_targets)

    st.divider()

    # ── Map + Table ───────────────────────────────────────────────────────────
    map_col, tbl_col = st.columns([3, 2])

    with map_col:
        selected_uid = st.session_state.get("selected_uid")
        if selected_uid:
            st.markdown(f"### 🎯 LSTM trajectory for **{selected_uid}**")
        else:
            st.markdown("### 🗺 Live Airspace Picture")

        df, df_paths = _build_map(st.session_state.active_targets, selected_uid)
        if (df is not None and not df.empty) or (df_paths is not None and not df_paths.empty):
            deck = _render_map(df, df_paths)
            st.pydeck_chart(deck, use_container_width=True)
            if selected_uid:
                if st.button("❌ Clear trajectory", key="clear_traj"):
                    st.session_state.selected_uid = None
                    st.rerun()
        else:
            st.info("Awaiting first data cycle…")

    with tbl_col:
        st.markdown("### 📋 Target Registry")
        clicked_uid = _render_target_table(st.session_state.active_targets)
        if clicked_uid and clicked_uid != st.session_state.get("selected_uid"):
            st.session_state.selected_uid = clicked_uid
            st.rerun()

        # ── Legend ────────────────────────────────────────────────────────────
        st.markdown("""
| Colour | Classification |
|--------|----------------|
| 🟢 Green  | Commercial (ADS-B) |
| 🔵 Blue   | Bird / Bionic Bird |
| 🟠 Orange | Drone / UAS |
| 🔴 Red    | Military / High-Perf |
| 🟣 Purple | Stealth / Low-Observable |
| ⚫ Grey   | Unknown / Unclassified |
""")

    st.divider()

    # ── Classification Path detail expander ───────────────────────────────────
    with st.expander("🔬 Classification Paths (last cycle)"):
        for uid, t in st.session_state.active_targets.items():
            d = t.to_dict() if hasattr(t, "to_dict") else t
            path = d.get("classification_path", [])
            if path:
                st.markdown(
                    f"**{uid}** → `{d.get('label')}` "
                    f"(conf {d.get('confidence',0):.0%})\n"
                    + " → ".join(path)
                )


if __name__ == "__main__":
    main()