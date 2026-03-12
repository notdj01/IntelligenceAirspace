"""Test script for Zero-Trust Flight ID feature."""
import sys
sys.stdout.reconfigure(line_buffering=True)

import logging
logging.basicConfig(level=logging.WARNING)

print("Testing Zero-Trust Flight ID feature...")

# Test 1: Import physics verifier
print("\n[1] Testing physics verifier imports...")
from agents.physics_verifier_node import physics_verifier, verify_physics_identity, SpoofingFlag
from agents.state import TargetMetadata, TargetLabel, RiskLevel
print("    OK: Imports successful")

# Test 2: Create a spoofed target and test detection
print("\n[2] Testing spoofing detection on synthetic target...")

# Create a "bird" with drone-like RCS (spoofed)
spoofed_target = TargetMetadata(
    uid="test_spoof_001",
    callsign="SPOOF-BIRD",
    latitude=21.1458,
    longitude=79.0882,
    altitude_m=200,
    velocity_ms=20,  # Too fast for a bird!
    climb_rate_ms=1,
    heading=45,
    radar_rcs=0,  # Much too high for a bird!
    label=TargetLabel.BIRD,  # Claims to be a bird
    risk=RiskLevel.LOW,
)
result = verify_physics_identity(spoofed_target)
print(f"    Target: bird with RCS=0 dBsm, speed=20 m/s")
print(f"    Physics verified: {result.physics_verified}")
print(f"    Spoofing flags: {[f.value for f in result.spoofing_flags]}")
print(f"    Trust score: {result.digital_identity_trust:.2f}")
print(f"    Violations: {result.physics_violations}")
assert not result.physics_verified, "Should detect spoofing!"
print("    OK: Spoofing detected successfully!")

# Test 3: Create a normal target and verify it passes
print("\n[3] Testing normal target verification...")
normal_target = TargetMetadata(
    uid="test_normal_001",
    callsign="NORMAL-BIRD",
    latitude=21.1458,
    longitude=79.0882,
    altitude_m=200,
    velocity_ms=10,  # Normal bird speed
    climb_rate_ms=1,
    heading=45,
    radar_rcs=-20,  # Normal bird RCS
    label=TargetLabel.BIRD,
    risk=RiskLevel.LOW,
)
result2 = verify_physics_identity(normal_target)
print(f"    Target: bird with RCS=-20 dBsm, speed=10 m/s")
print(f"    Physics verified: {result2.physics_verified}")
print(f"    Trust score: {result2.digital_identity_trust:.2f}")
assert result2.physics_verified, "Normal target should pass verification!"
print("    OK: Normal target verified successfully!")

# Test 4: Test impossible maneuver detection
print("\n[4] Testing impossible maneuver detection...")
impossible_target = TargetMetadata(
    uid="test_impossible_001",
    callsign="IMPOSSIBLE",
    latitude=21.1458,
    longitude=79.0882,
    altitude_m=3000,
    velocity_ms=200,
    climb_rate_ms=50,  # Impossible climb rate!
    heading=45,
    radar_rcs=10,
    label=TargetLabel.COMMERCIAL,
    risk=RiskLevel.LOW,
)
result3 = verify_physics_identity(impossible_target)
print(f"    Target: commercial aircraft with climb=50 m/s")
print(f"    Physics verified: {result3.physics_verified}")
print(f"    Spoofing flags: {[f.value for f in result3.spoofing_flags]}")
assert not result3.physics_verified, "Should detect impossible maneuver!"
print("    OK: Impossible maneuver detected successfully!")

# Test 5: Test graph integration
print("\n[5] Testing LangGraph pipeline integration...")
from agents.graph import build_graph
graph = build_graph()
node_names = [n for n in graph.nodes.keys()]
print(f"    Graph nodes: {node_names}")
assert "physics_verifier" in node_names, "Physics verifier should be in graph!"
print("    OK: Graph integration successful!")

print("\n" + "="*50)
print("ALL TESTS PASSED!")
print("="*50)
