import hashlib
import logging
import math
import os
from typing import Any, Dict, List, Tuple

import torch
import torch.nn as nn

from agents.state import AirspaceState, TargetMetadata
from agents.anomaly_config import label_from_score

logger = logging.getLogger(__name__)

_anomaly_model: Dict[str, Any] = {}


class AnomalyAutoencoder(nn.Module):
    """
    Architecture must match the one defined in notebooks/train_anomaly_detector.ipynb.
    """

    def __init__(self, input_size: int = 3, hidden_size: int = 64, latent_size: int = 32):
        super().__init__()
        self.encoder = nn.LSTM(input_size, hidden_size, num_layers=2, batch_first=True)
        self.to_latent = nn.Linear(hidden_size, latent_size)
        self.from_latent = nn.Linear(latent_size, hidden_size)
        self.decoder = nn.LSTM(input_size, hidden_size, num_layers=2, batch_first=True)
        self.out = nn.Linear(hidden_size, input_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        enc_out, _ = self.encoder(x)
        h_last = enc_out[:, -1, :]
        z = self.to_latent(h_last)
        h0 = self.from_latent(z).unsqueeze(0).repeat(2, 1, 1)
        c0 = torch.zeros_like(h0)
        dec_out, _ = self.decoder(x, (h0, c0))
        return self.out(dec_out)


def _load_anomaly_model() -> Dict[str, Any]:
    """
    Load the anomaly autoencoder + normalization from disk, cached in memory.
    """
    global _anomaly_model
    if _anomaly_model:
        return _anomaly_model

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ckpt_path = os.path.join(base_dir, "data_prepared", "anomaly_lstm.pth")
    if not os.path.exists(ckpt_path):
        logger.warning("Anomaly checkpoint not found at %s; falling back to heuristic anomalies", ckpt_path)
        return {}

    try:
        ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        model = AnomalyAutoencoder()
        model.load_state_dict(ckpt["model_state_dict"])
        model.eval()

        norm = ckpt.get("normalization", {})
        seq_len = int(ckpt.get("seq_len", 20))
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Failed to load anomaly model: %s", exc)
        return {}

    _anomaly_model = {"model": model, "norm": norm, "seq_len": seq_len}
    logger.info("Loaded anomaly model from %s (seq_len=%s)", ckpt_path, seq_len)
    return _anomaly_model


def _build_displacement_history(target: TargetMetadata, seq_len: int) -> List[Tuple[float, float, float]]:
    """
    Build a sequence of (d_lat_m, d_lon_m, d_alt_m) similar to agents.predict_node,
    using history plus synthetic backfill when needed.
    """
    needed = seq_len + 1
    lats = list(target.history_lat)
    lons = list(target.history_lon)
    alts = list(target.history_alt)

    # Ensure we have at least the current point
    if not lats:
        lats.append(target.latitude)
        lons.append(target.longitude)
        alts.append(target.altitude_m)

    # Backfill if we do not have enough history
    if len(lats) < needed:
        lat = target.latitude
        lon = target.longitude
        alt = target.altitude_m

        uid_hash = int(hashlib.md5(target.uid.encode()).hexdigest()[:8], 16)
        turn_rate = ((uid_hash % 100) - 50) * 0.06  # -3 to +3 deg/step

        vel_ms = max(target.velocity_ms or 1.0, 0.5)
        heading = target.heading or 0.0
        climb = target.climb_rate_ms or 0.0

        lat_deg_to_m = 111320.0
        lon_deg_to_m = 111320.0 * math.cos(math.radians(lat or 0.0))
        dt = 10.0

        synth_lats = [lat]
        synth_lons = [lon]
        synth_alts = [alt]

        num_synth = needed - len(lats)
        cur_heading = heading
        for _ in range(max(num_synth, 0)):
            cur_heading -= turn_rate
            dx = vel_ms * dt * math.sin(math.radians(cur_heading))
            dy = vel_ms * dt * math.cos(math.radians(cur_heading))
            lat -= dy / lat_deg_to_m
            lon -= dx / lon_deg_to_m
            alt -= climb * dt
            synth_lats.insert(0, lat)
            synth_lons.insert(0, lon)
            synth_alts.insert(0, alt)

        lats = synth_lats + lats
        lons = synth_lons + lons
        alts = synth_alts + alts

    lats = lats[-needed:]
    lons = lons[-needed:]
    alts = alts[-needed:]

    lat_center = sum(lats) / len(lats)
    lat_deg_to_m = 111320.0
    lon_deg_to_m = 111320.0 * math.cos(math.radians(lat_center))

    disp: List[Tuple[float, float, float]] = []
    for i in range(1, len(lats)):
        d_lat = (lats[i] - lats[i - 1]) * lat_deg_to_m
        d_lon = (lons[i] - lons[i - 1]) * lon_deg_to_m
        d_alt = alts[i] - alts[i - 1]
        disp.append((d_lat, d_lon, d_alt))

    return disp[-seq_len:]


def _score_with_model(disp: List[Tuple[float, float, float]], model_blob: Dict[str, Any]) -> float:
    if not model_blob:
        return float("nan")

    model: nn.Module = model_blob["model"]
    norm: Dict[str, float] = model_blob["norm"]

    lat_mean = norm.get("lat_mean", 0.0)
    lat_std = norm.get("lat_std", 1.0) or 1.0
    lon_mean = norm.get("lon_mean", 0.0)
    lon_std = norm.get("lon_std", 1.0) or 1.0
    alt_mean = norm.get("alt_mean", 0.0)
    alt_std = norm.get("alt_std", 1.0) or 1.0

    arr = []
    for d_lat, d_lon, d_alt in disp:
        arr.append(
            [
                (d_lat - lat_mean) / lat_std,
                (d_lon - lon_mean) / lon_std,
                (d_alt - alt_mean) / alt_std,
            ]
        )

    x = torch.tensor([arr], dtype=torch.float32)
    with torch.no_grad():
        recon = model(x)
        mse = torch.mean((recon - x) ** 2).item()
    return float(mse)


def _heuristic_score(target: TargetMetadata) -> Tuple[float, List[str]]:
    """
    Cheap heuristic anomaly score used when the deep model is unavailable.
    """
    reasons: List[str] = []
    score = 0.0

    if len(target.history_alt) >= 2:
        d_alt = target.history_alt[-1] - target.history_alt[-2]
        if abs(d_alt) > 500:  # meters between samples
            score += 0.5
            reasons.append("Abrupt altitude change")

    if len(target.history_lat) >= 2 and len(target.history_lon) >= 2:
        lat_deg_to_m = 111320.0
        lat_center = target.history_lat[-1]
        lon_deg_to_m = 111320.0 * math.cos(math.radians(lat_center))
        dx = (target.history_lon[-1] - target.history_lon[-2]) * lon_deg_to_m
        dy = (target.history_lat[-1] - target.history_lat[-2]) * lat_deg_to_m
        dist = math.hypot(dx, dy)
        if dist > 10_000:  # >10km between samples
            score += 0.5
            reasons.append("Large lateral jump")

    if target.risk in {target.risk.HIGH, target.risk.CRITICAL}:  # type: ignore[attr-defined]
        score += 0.3
        reasons.append("High risk classification")

    return min(score, 1.5), reasons


def detect_anomalies(state: AirspaceState) -> AirspaceState:
    """
    LangGraph node: compute anomaly scores / labels for each active target.
    """
    log = list(state.get("agent_log", []))
    active_targets = state.get("active_targets", {})

    model_blob = _load_anomaly_model()
    seq_len = model_blob.get("seq_len", 20) if model_blob else 20

    raw_scores: Dict[str, float] = {}
    meta: Dict[str, Dict[str, Any]] = {}

    for uid, target in active_targets.items():
        if not isinstance(target, TargetMetadata):
            # When targets come back from serialization they may be dicts.
            target = TargetMetadata(**target)  # type: ignore[arg-type]
            active_targets[uid] = target

        disp = _build_displacement_history(target, seq_len)
        src = getattr(target, "source", None)
        src_str = getattr(src, "value", str(src)) if src is not None else ""
        is_opensky = bool(getattr(target, "icao24", None)) or "OpenSky" in src_str

        # For OpenSky / commercial traffic, rely on downstream risk assessment
        # and NFZ logic. Treat them as non-anomalous by default so the model
        # does not gradually mark all regular airliners as anomalies.
        if is_opensky:
            raw_scores[uid] = 0.0
            meta[uid] = {
                "target": target,
                "is_opensky": is_opensky,
                "reasons": [],
            }
            continue

        raw_score: float
        reasons: List[str]

        if model_blob:
            raw_score = _score_with_model(disp, model_blob)
            reasons = []
        else:
            raw_score, reasons = _heuristic_score(target)

        raw_scores[uid] = raw_score
        meta[uid] = {"target": target, "is_opensky": is_opensky, "reasons": reasons}

    # Robust across-cycle normalization: median + MAD (per-cycle baseline)
    finite_scores = [s for s in raw_scores.values() if math.isfinite(s) and s >= 0]
    if finite_scores:
        finite_scores.sort()
        n = len(finite_scores)
        median = finite_scores[n // 2] if n % 2 == 1 else 0.5 * (
            finite_scores[n // 2 - 1] + finite_scores[n // 2]
        )
        mad_vals = [abs(s - median) for s in finite_scores]
        mad_vals.sort()
        mad = mad_vals[n // 2] if n % 2 == 1 else 0.5 * (
            mad_vals[n // 2 - 1] + mad_vals[n // 2]
        )
        mad = mad or 1e-6
    else:
        median = 0.0
        mad = 1e-6

    anomalous = 0
    for uid, raw in raw_scores.items():
        info = meta[uid]
        target: TargetMetadata = info["target"]
        is_opensky: bool = info["is_opensky"]
        reasons: List[str] = info["reasons"]

        if not math.isfinite(raw) or raw <= 0:
            score = 0.0
        else:
            # Normalized anomaly score: how many MADs above the per-cycle median.
            score = max(0.0, (raw - median) / mad)

        label = label_from_score(score, is_opensky=is_opensky)

        target.anomaly_score = float(score)
        target.anomaly_label = label
        target.anomaly_reasons = reasons

        if label == "Anomalous":
            anomalous += 1

    if anomalous:
        log.append(f"⚠️ Anomaly detector flagged {anomalous} target(s) as anomalous.")

    return {
        **state,
        "active_targets": active_targets,
        "agent_log": log,
    }

