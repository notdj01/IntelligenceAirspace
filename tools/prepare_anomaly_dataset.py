"""
Prepare anomaly training data from the archive dataset (Kaggle UAV anomaly logs).

Produces (d_lat_m, d_lon_m, d_alt_m) windows compatible with agents.anomaly_node:
- GPS logs: direct Lat, Lng, Alt -> displacement in meters
- Fusion_Data: Roll, Pitch, Yaw deltas scaled to meter-like range as proxy motion

Saves data_prepared/anomaly_windows.npy for the training notebook.
"""
import math
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = BASE_DIR / "archive" / "dataset"
OUT_PATH = BASE_DIR / "data_prepared" / "anomaly_windows.npy"
SEQ_LEN = 20

# Scale Fusion attitude deltas to ~10-1000m range so normalization is comparable
FUSION_SCALE = 50.0


def _deg_to_meters(lat_deg: float) -> tuple:
    """Return (lat_m_per_deg, lon_m_per_deg) at given latitude."""
    lat_m = 111320.0
    lon_m = 111320.0 * math.cos(math.radians(lat_deg))
    return lat_m, lon_m


def load_gps_windows(csv_path: Path) -> np.ndarray:
    """Load GPS CSV, compute (d_lat_m, d_lon_m, d_alt_m) windows."""
    df = pd.read_csv(csv_path)
    if "Lat" not in df.columns or "Lng" not in df.columns or "Alt" not in df.columns:
        return np.zeros((0, SEQ_LEN, 3), dtype=np.float32)

    lat = df["Lat"].values.astype(float)
    lng = df["Lng"].values.astype(float)
    alt = df["Alt"].values.astype(float)

    disp = []
    for i in range(1, len(lat)):
        lat_m, lon_m = _deg_to_meters(lat[i])
        d_lat_m = (lat[i] - lat[i - 1]) * lat_m
        d_lon_m = (lng[i] - lng[i - 1]) * lon_m
        d_alt_m = alt[i] - alt[i - 1]
        disp.append([d_lat_m, d_lon_m, d_alt_m])

    if len(disp) < SEQ_LEN:
        return np.zeros((0, SEQ_LEN, 3), dtype=np.float32)

    windows = []
    for i in range(len(disp) - SEQ_LEN + 1):
        w = np.array(disp[i : i + SEQ_LEN], dtype=np.float32)
        windows.append(w)
    return np.stack(windows)


def load_fusion_windows(csv_path: Path) -> np.ndarray:
    """
    Load Fusion_Data.csv (UAV IMU/attitude). Use Roll, Pitch, Yaw deltas,
    scaled to ~meter range, so the model learns motion patterns that transfer
    to (d_lat_m, d_lon_m, d_alt_m) at runtime.
    """
    df = pd.read_csv(csv_path)
    for col in ["Roll", "Pitch", "Yaw"]:
        if col not in df.columns:
            return np.zeros((0, SEQ_LEN, 3), dtype=np.float32)

    roll = df["Roll"].values.astype(float)
    pitch = df["Pitch"].values.astype(float)
    yaw = df["Yaw"].values.astype(float)

    d_roll = np.diff(roll, prepend=roll[0]) * FUSION_SCALE
    d_pitch = np.diff(pitch, prepend=pitch[0]) * FUSION_SCALE
    d_yaw = np.diff(yaw, prepend=yaw[0]) * FUSION_SCALE

    disp = np.stack([d_roll, d_pitch, d_yaw], axis=1).astype(np.float32)

    if len(disp) < SEQ_LEN:
        return np.zeros((0, SEQ_LEN, 3), dtype=np.float32)

    windows = []
    for i in range(len(disp) - SEQ_LEN + 1):
        w = disp[i : i + SEQ_LEN]
        windows.append(w)
    return np.stack(windows)


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    all_windows = []

    fusion_path = ARCHIVE_DIR / "Fusion_Data.csv"
    if fusion_path.exists():
        w = load_fusion_windows(fusion_path)
        if w.size > 0:
            all_windows.append(w)
            print(f"Loaded {len(w)} windows from Fusion_Data.csv")

    gps_path = ARCHIVE_DIR / "GPS" / "ALL_FAIL_LOG_GPS_0.csv"
    if gps_path.exists():
        w = load_gps_windows(gps_path)
        if w.size > 0:
            all_windows.append(w)
            print(f"Loaded {len(w)} windows from GPS/ALL_FAIL_LOG_GPS_0.csv")

    if not all_windows:
        raise FileNotFoundError(
            f"No data found in {ARCHIVE_DIR}. "
            "Ensure archive/dataset/Fusion_Data.csv or GPS logs exist."
        )

    arr = np.concatenate(all_windows, axis=0)
    np.random.shuffle(arr)
    np.save(OUT_PATH, arr)
    print(f"Saved {arr.shape[0]} windows to {OUT_PATH} (shape {arr.shape})")


if __name__ == "__main__":
    main()
