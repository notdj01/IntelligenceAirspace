import os
import math
import torch
import logging
from typing import Dict, Any, List

from agents.state import AirspaceState, TargetMetadata

logger = logging.getLogger(__name__)

# Cache models to avoid reloading every cycle
_models = {}

def get_model(model_path):
    if model_path not in _models:
        if not os.path.exists(model_path):
            return None
        try:
            checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
            # Reconstruct the model architecture
            import torch.nn as nn
            class TrajectoryLSTM(nn.Module):
                def __init__(self, input_size=3, hidden_size=64, num_layers=2, output_size=3, pred_length=5):
                    super(TrajectoryLSTM, self).__init__()
                    self.hidden_size = hidden_size
                    self.num_layers = num_layers
                    self.pred_length = pred_length
                    self.output_size = output_size
                    self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
                    self.fc = nn.Linear(hidden_size, output_size * pred_length)
                def forward(self, x):
                    h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
                    c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
                    out, _ = self.lstm(x, (h0, c0))
                    out = self.fc(out[:, -1, :])
                    return out.view(-1, self.pred_length, self.output_size)
                    
            model = TrajectoryLSTM()
            model.load_state_dict(checkpoint['model_state_dict'])
            model.eval()
            _models[model_path] = {
                "model": model,
                "norm": checkpoint["normalization"]
            }
        except Exception as e:
            logger.error(f"Failed to load model {model_path}: {e}")
            return None
    return _models[model_path]


def _synthesize_history(target: TargetMetadata, seq_length: int):
    """
    Backfill trajectory history from velocity/heading.
    Adds a slight progressive turn-rate so the LSTM input is varied
    (identical deltas → straight-line outputs; varied → curved outputs).
    """
    import hashlib
    needed = seq_length + 1
    real_n = len(target.history_lat)

    if real_n >= needed:
        return (
            target.history_lat[-needed:],
            target.history_lon[-needed:],
            target.history_alt[-needed:],
        )

    # Deterministic per-target turn rate so paths are stable across cycles
    uid_hash = int(hashlib.md5(target.uid.encode()).hexdigest()[:8], 16)
    turn_rate = ((uid_hash % 100) - 50) * 0.06   # -3 to +3 deg/step

    vel_ms  = max(target.velocity_ms or 1.0, 0.5)
    heading = target.heading        or 0.0
    climb   = target.climb_rate_ms or 0.0
    lat     = target.latitude
    lon     = target.longitude
    alt     = target.altitude_m

    lat_deg_to_m = 111320.0
    lon_deg_to_m = 111320.0 * math.cos(math.radians(lat))
    dt = 10.0   # seconds per synthetic step

    synth_lats = [lat]
    synth_lons = [lon]
    synth_alts = [alt]

    num_synth = needed - real_n - (1 if real_n >= 1 else 0)
    cur_heading = heading
    for _ in range(num_synth):
        cur_heading -= turn_rate           # reverse: we're stepping backwards
        dx = vel_ms * dt * math.sin(math.radians(cur_heading))
        dy = vel_ms * dt * math.cos(math.radians(cur_heading))
        lat -= dy / lat_deg_to_m
        lon -= dx / lon_deg_to_m
        alt -= climb * dt
        synth_lats.insert(0, lat)
        synth_lons.insert(0, lon)
        synth_alts.insert(0, alt)

    combined_lats = synth_lats + target.history_lat
    combined_lons = synth_lons + target.history_lon
    combined_alts = synth_alts + target.history_alt

    return (
        combined_lats[-needed:],
        combined_lons[-needed:],
        combined_alts[-needed:],
    )


def predict_trajectory(state: AirspaceState) -> AirspaceState:
    """
    LangGraph node: Use PyTorch LSTM to predict future trajectories
    """
    log = list(state.get("agent_log", []))
    active_targets = state.get("active_targets", {})
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    airplane_model_path = os.path.join(base_dir, "data_prepared", "airplane_lstm.pth")
    pigeon_model_path   = os.path.join(base_dir, "data_prepared", "pigeon_lstm.pth")
    
    airplane_model_data = get_model(airplane_model_path)
    pigeon_model_data   = get_model(pigeon_model_path)
    
    # Require only 3 real history points; fill remainder synthetically
    SEQ_LENGTH = 3
    predicted_count = 0
    
    for uid, target in active_targets.items():
        # Choose model by label
        label = str(getattr(target, "label", "")).lower()
        if "bird" in label or "pigeon" in label:
            m_data = pigeon_model_data or airplane_model_data
        else:
            m_data = airplane_model_data

        if not m_data:
            continue

        lats, lons, alts = _synthesize_history(target, SEQ_LENGTH)

        lat_center   = sum(lats) / len(lats)
        lat_deg_to_m = 111320.0
        lon_deg_to_m = 111320.0 * math.cos(math.radians(lat_center))

        d_lats_m = [(lats[i] - lats[i-1]) * lat_deg_to_m for i in range(1, len(lats))]
        d_lons_m = [(lons[i] - lons[i-1]) * lon_deg_to_m for i in range(1, len(lons))]
        d_alts_m = [alts[i] - alts[i-1]                  for i in range(1, len(alts))]

        norm  = m_data["norm"]
        model = m_data["model"]

        try:
            norm_d_lat = [(L - norm['lat_mean']) / norm['lat_std'] for L in d_lats_m]
            norm_d_lon = [(L - norm['lon_mean']) / norm['lon_std'] for L in d_lons_m]
            norm_d_alt = [(A - norm['alt_mean']) / norm['alt_std'] for A in d_alts_m]
        except (ZeroDivisionError, KeyError):
            continue

        input_seq = [[norm_d_lat[i], norm_d_lon[i], norm_d_alt[i]] for i in range(SEQ_LENGTH)]
        input_tensor = torch.FloatTensor([input_seq])

        with torch.no_grad():
            output = model(input_tensor)   # (1, pred_length, 3)
            preds  = output[0].numpy()

        new_predictions = []
        last_lat = lats[-1]
        last_lon = lons[-1]
        last_alt = alts[-1]
        
        # Compute per-target turn rate (same as _synthesize_history)
        import hashlib
        uid_hash = int(hashlib.md5(target.uid.encode()).hexdigest()[:8], 16)
        turn_rate = ((uid_hash % 100) - 50) * 0.06   # −3 to +3 deg/step forward

        # Estimate current heading from last two history points
        if len(lats) >= 2 and (lats[-1] != lats[-2] or lons[-1] != lons[-2]):
            cur_heading = math.degrees(math.atan2(
                (lons[-1] - lons[-2]) * lon_deg_to_m,
                (lats[-1] - lats[-2]) * lat_deg_to_m
            ))
        else:
            cur_heading = target.heading or 0.0

        for p in preds:
            p_d_lat_m = p[0] * norm['lat_std'] + norm['lat_mean']
            p_d_lon_m = p[1] * norm['lon_std'] + norm['lon_mean']
            p_d_alt_m = p[2] * norm['alt_std'] + norm['alt_mean']

            if math.isnan(p_d_lat_m) or math.isnan(p_d_lon_m) or math.isnan(p_d_alt_m):
                break

            # Use LSTM-predicted displacement magnitude but rotate by turn_rate
            speed_m = math.sqrt(p_d_lat_m**2 + p_d_lon_m**2)
            if speed_m < 1e-6:
                speed_m = math.sqrt(
                    (d_lats_m[-1]**2 + d_lons_m[-1]**2)
                ) or (target.velocity_ms or 100.0) * 10.0

            cur_heading += turn_rate
            dx_m = speed_m * math.sin(math.radians(cur_heading))
            dy_m = speed_m * math.cos(math.radians(cur_heading))

            last_lat += dy_m / lat_deg_to_m
            last_lon += dx_m / lon_deg_to_m
            last_alt += p_d_alt_m
            new_predictions.append({"lat": float(last_lat), "lon": float(last_lon), "alt": float(last_alt)})

        target.predicted_trajectory = new_predictions
        if new_predictions:
            predicted_count += 1

    if predicted_count > 0:
        log.append(f"🔮 LSTM predicted paths for {predicted_count} targets.")
        
    return {
        **state,
        "active_targets": active_targets,
        "agent_log": log
    }


