# Zero-Trust Flight ID - Physics Verification Agent

## 1. Feature Overview

**Project Name:** Zero-Trust Flight ID (Physics-Verified Identity)

**Core Functionality:** A cyber-physical security layer that verifies ADS-B/transponder data against the laws of physics to detect "deepfake" flight signals - i.e., spoofed drone or aircraft identities.

**Unique Value Proposition:** "Physics-Verified Identity" - We don't just classify objects; we detect "Deepfake" flight signals by verifying that the claimed object type's physical characteristics match its observed behavior.

## 2. Threat Model

The system detects the following attack vectors:

| Attack Type | Description | Detection Method |
|-------------|-------------|------------------|
| **Identity Hijack** | Spoofing a dangerous drone as a peaceful bird | RCS + Motor frequency mismatch |
| **Impossible Maneuver** | Claims of aircraft making physically impossible turns (15G) | Physics-based trajectory analysis |
| **Phantom Aircraft** | Fake aircraft with impossible flight dynamics | Velocity/acceleration consistency |
| **Category Mismatch** | "Bird" with aircraft speed, "Plane" with bird maneuverability | Physical constraints verification |

## 3. Detection Modules

### 3.1 Impossible Maneuver Detector
- **Physics Constraints:**
  - Maximum sustained turn rate: ~3°/sec for commercial aircraft
  - Maximum roll rate: ~20°/sec for fighters, ~5°/sec for commercial
  - Maximum climb/descent rate: ~3000 fpm (typical), ~6000 fpm (fighter)
  - Maximum acceleration: ~1G in level flight, ~9G in turns (fighters), ~0.3G (commercial)
  - Stall speed minimums: ~60 kts (small plane), ~120 kts (commercial)

- **Detection Logic:**
  ```
  IF (turn_rate > threshold_for_type) → PHYSICS_VIOLATION
  IF (climb_rate > max_climb_rate) → PHYSICS_VIOLATION
  IF (speed < stall_speed) AND (altitude > 1000ft) → PHYSICS_VIOLATION
  IF (calculated_G_force > 9G) → PHYSICS_VIOLATION
  ```

### 3.2 Motor Signature Analyzer
- **Brushless Motor Characteristics:**
  - Typical RPM range: 3,000 - 12,000 RPM (varies by drone size)
  - Motor frequency harmonics appear in RCS/Doppler
  - Blade Pass Frequency (BPF) = RPM × (# blades) / 60

- **Detection Logic:**
  ```
  IF (claimed_type == "Bird") AND (detected_RCS_modulation == motor_BPF) → SPOOF_DETECTED
  IF (claimed_type == "Bird") AND (RCS > -10 dBsm) → SPOOF_DETECTED (birds typically < -20 dBsm)
  IF (detected_motor_harmonics > 0) AND (claimed_type ∈ {Bird, Balloon}) → SPOOF_DETECTED
  ```

### 3.3 Category Consistency Checker
| Claimed Type | Min Speed | Max Speed | Typical RCS (dBsm) | Max Turn Rate |
|--------------|-----------|-----------|-------------------|---------------|
| Bird         | 0         | 25 m/s    | -30 to -15        | 180°/sec      |
| Drone        | 0         | 50 m/s    | -20 to +5         | 360°/sec      |
| Helicopter   | 0         | 80 m/s    | +5 to +15         | 90°/sec       |
| RC Plane     | 5         | 60 m/s    | -10 to +5         | 180°/sec      |
| Commercial   | 60        | 250 m/s   | +10 to +25        | 3°/sec        |
| Military     | 50        | 350 m/s   | +5 to +20         | 10°/sec       |

## 4. Data Structures

### 4.1 New Fields in TargetMetadata
```python
# Physics Verification Results
physics_verified: bool = True          # True = passed all checks
spoofing_flags: List[SpoofingFlag]     # List of detected anomalies
digital_identity_trust: float = 1.0    # 0.0 - 1.0 trust score
physics_violations: List[str]          # Detailed violation reasons
motor_rpm_detected: Optional[float]    # Detected motor RPM (if any)
rcs_anomaly_score: float = 0.0          # RCS consistency score
```

### 4.2 Spoofing Flag Types
```python
class SpoofingFlag(str, Enum):
    IMPOSSIBLE_MANEUVER = "Impossible Maneuver"      # 15G turn etc.
    MOTOR_SIGNATURE_DETECTED = "Motor Signature"      # Motor harmonics in "bird"
    CATEGORY_MISMATCH = "Category Mismatch"            # Wrong speed/RCS for type
    RCS_ANOMALY = "RCS Anomaly"                        # Unusual radar signature
    TRAJECTORY_INCONSISTENCY = "Trajectory Inconsistency"  # Jerky/fake path
    IDENTITY_HIJACK_SUSPECTED = "Identity Hijack"     # Multiple identity changes
```

## 5. Implementation Architecture

### 5.1 New Node: `physics_verifier_node.py`
Location: `agents/physics_verifier_node.py`

**Integration Point:** After `classification_gate` and before `risk_assessment`

**Pipeline Flow:**
```
fetch_data → predict_trajectory → anomaly_node → classification_gate → physics_verifier → risk_assessment → END
```

### 5.2 Synthetic Data Generator
For simulation/research purposes, we need synthetic data generators that can:
1. Inject realistic motor frequency signatures into RCS
2. Generate impossible maneuvers for testing
3. Simulate category mismatches
4. Create "spoofed" targets with inconsistent properties

## 6. Acceptance Criteria

1. ✅ Physics verifier node integrates into existing LangGraph pipeline
2. ✅ Detects simulated motor signatures in RCS data
3. ✅ Identifies impossible maneuvers (excessive G-force, turn rates)
4. ✅ Validates category consistency (speed/RCS match claimed type)
5. ✅ Produces trust scores and detailed violation reasons
6. ✅ Visual integration with existing UI (alert badges, color coding)
7. ✅ Graceful fallback when sensor data is unavailable

## 7. Risk Scoring Impact

Physics verification failures significantly elevate risk assessment:

| Verification Status | Risk Multiplier |
|---------------------|-----------------|
| ✅ Fully Verified    | 1.0x            |
| ⚠️ Partially Verified | 1.5x          |
| ❌ Failed (1 flag)  | 2.0x            |
| ❌ Failed (2+ flags)| 3.0x (Critical)|
