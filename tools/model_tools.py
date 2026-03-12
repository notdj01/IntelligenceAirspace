"""
Model Tools — Boilerplate classifiers for Phase 2/3 of the cascade.

radar_classifier_tool  : VGG16-based micro-Doppler / DIAT-μSAT classifier
rf_fingerprint_tool    : 1-D CNN placeholder for DroneRF brand identification
"""

import os
import time
import random
import logging
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# DIAT-μSAT class mapping (micro-Doppler SAR imagery classes)
# ──────────────────────────────────────────────────────────────────────────────
DIAT_CLASSES = {
    0: "Quadcopter",
    1: "Bionic Bird",
    2: "Helicopter",
    3: "RC Plane",
}

# DroneRF brand classes
DRONERF_BRANDS = {
    0: "DJI",
    1: "Parrot",
    2: "Syma",
    3: "Hubsan",
    4: "Generic/Unknown",
}

# Lazy-loaded model references
_vgg16_model = None
_rf_model = None


def _load_vgg16():
    """
    Load a pre-trained VGG16 from torchvision, replace the final classifier
    head with a 4-class layer matching DIAT-μSAT.  In production you would
    load fine-tuned weights; here we use random weights for the new head.
    
    NOTE: Disabled to forcefully run simulation mode because full PyTorch 
    model initialization is causing OOM errors on the host CPU.
    """
    global _vgg16_model
    if _vgg16_model is not None:
        return _vgg16_model

    logger.warning("VGG16 load disabled (OOM crash prevention); falling back to simulation mode")
    return None


def radar_classifier_tool(
    image_path: Optional[str] = None,
    uid: str = "unknown",
) -> Tuple[str, float]:
    """
    Classify a radar/micro-Doppler image using VGG16.

    Parameters
    ----------
    image_path : local path to a micro-Doppler spectrogram PNG/JPG.
                 If None, runs in simulation mode.
    uid        : target UID for logging.

    Returns
    -------
    (class_name, confidence)  e.g.  ("Quadcopter", 0.87)
    """
    model = _load_vgg16()

    # ── Simulation mode (no image / no GPU in demo env) ──────────────────────
    if model is None or image_path is None or not Path(image_path).exists():
        # Weighted random: drones are rare, birds are common
        weights = [0.45, 0.25, 0.20, 0.10]   # Quad, Bird, Heli, RC
        idx = random.choices(range(len(DIAT_CLASSES)), weights=weights, k=1)[0]
        confidence = round(random.uniform(0.62, 0.94), 3)
        label = DIAT_CLASSES[idx]
        logger.info(f"[radar_classifier SIMULATED] uid={uid} → {label} ({confidence:.2%})")
        return label, confidence

    # ── Real inference path ───────────────────────────────────────────────────
    try:
        import torch
        from torchvision import transforms
        from PIL import Image

        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

        img = Image.open(image_path).convert("RGB")
        tensor = transform(img).unsqueeze(0)   # (1, 3, 224, 224)

        with torch.no_grad():
            logits = model(tensor)
            probs = torch.softmax(logits, dim=1)[0]
            idx = int(probs.argmax())
            confidence = float(probs[idx])

        label = DIAT_CLASSES[idx]
        logger.info(f"[radar_classifier REAL] uid={uid} → {label} ({confidence:.2%})")
        return label, confidence

    except Exception as e:
        logger.error(f"radar_classifier_tool error for uid={uid}: {e}")
        return "Unknown", 0.0


# ──────────────────────────────────────────────────────────────────────────────
# RF Fingerprinting  (1-D CNN placeholder — DroneRF dataset)
# ──────────────────────────────────────────────────────────────────────────────

def _build_rf_cnn():
    """
    Build a lightweight 1-D CNN skeleton for DroneRF RF fingerprinting.
    Architecture mirrors published DroneRF baselines:
      Conv1d blocks → GlobalAvgPool → FC → Softmax
    Weights are random (no trained checkpoint loaded).
    """
    try:
        import torch.nn as nn

        class RF_CNN(nn.Module):
            def __init__(self, n_classes: int = 5, seq_len: int = 1024):
                super().__init__()
                self.features = nn.Sequential(
                    nn.Conv1d(1, 32, kernel_size=7, padding=3), nn.ReLU(),
                    nn.MaxPool1d(2),
                    nn.Conv1d(32, 64, kernel_size=5, padding=2), nn.ReLU(),
                    nn.MaxPool1d(2),
                    nn.Conv1d(64, 128, kernel_size=3, padding=1), nn.ReLU(),
                    nn.AdaptiveAvgPool1d(1),
                )
                self.classifier = nn.Sequential(
                    nn.Flatten(),
                    nn.Linear(128, 64), nn.ReLU(),
                    nn.Dropout(0.3),
                    nn.Linear(64, n_classes),
                )

            def forward(self, x):
                return self.classifier(self.features(x))

        model = RF_CNN(n_classes=len(DRONERF_BRANDS))
        model.eval()
        return model
    except Exception as e:
        logger.warning(f"RF_CNN build failed: {e}")
        return None


def rf_fingerprint_tool(
    rf_signal: Optional[object] = None,
    uid: str = "unknown",
) -> Tuple[str, float]:
    """
    Identify drone brand/model from RF emission fingerprint using a 1-D CNN.

    Parameters
    ----------
    rf_signal : numpy array of raw IQ samples (shape: [N]) or None for sim.
    uid       : target UID for logging.

    Returns
    -------
    (brand_name, confidence)  e.g.  ("DJI", 0.91)
    """
    global _rf_model

    # ── Simulation mode ───────────────────────────────────────────────────────
    if rf_signal is None:
        weights = [0.40, 0.25, 0.15, 0.10, 0.10]   # DJI, Parrot, Syma, Hubsan, Generic
        idx = random.choices(range(len(DRONERF_BRANDS)), weights=weights, k=1)[0]
        confidence = round(random.uniform(0.55, 0.92), 3)
        brand = DRONERF_BRANDS[idx]
        logger.info(f"[rf_fingerprint SIMULATED] uid={uid} → {brand} ({confidence:.2%})")
        return brand, confidence

    # ── Real inference path ───────────────────────────────────────────────────
    try:
        import torch
        import numpy as np

        if _rf_model is None:
            _rf_model = _build_rf_cnn()
        if _rf_model is None:
            raise RuntimeError("RF CNN unavailable")

        # Normalize & reshape to (1, 1, seq_len)
        arr = np.array(rf_signal, dtype=np.float32)
        arr = (arr - arr.mean()) / (arr.std() + 1e-8)
        arr = arr[:1024] if len(arr) >= 1024 else np.pad(arr, (0, 1024 - len(arr)))
        tensor = torch.tensor(arr).unsqueeze(0).unsqueeze(0)   # (1,1,1024)

        with torch.no_grad():
            logits = _rf_model(tensor)
            probs = torch.softmax(logits, dim=1)[0]
            idx = int(probs.argmax())
            confidence = float(probs[idx])

        brand = DRONERF_BRANDS[idx]
        logger.info(f"[rf_fingerprint REAL] uid={uid} → {brand} ({confidence:.2%})")
        return brand, confidence

    except Exception as e:
        logger.error(f"rf_fingerprint_tool error for uid={uid}: {e}")
        return "Generic/Unknown", 0.0
