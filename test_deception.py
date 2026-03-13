"""Test script for deception feature - direct test."""
import sys
import logging

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

# Inject a high-risk drone manually
manual_injection = [
    {
        'uid': 'DRONE_ATTACK_001',
        'latitude': 21.1458,
        'longitude': 79.0882,
        'altitude_m': 80.0,
        'velocity_ms': 15.0,
        'label': 'Drone (DJI)',
        'callsign': 'ATTACK_DRONE',
    }
]

from agents.graph import run_cycle

print("=== Running Full Pipeline ===\n", file=sys.stderr)

result = run_cycle(
    center_lat=21.1458,
    center_lon=79.0882,
    cycle_id=1,
    manual_injections=manual_injection,
)

targets = result.get('active_targets', {})

# Find targets with HIGH/CRITICAL risk in PROHIBITED zone
print('\n=== Targets with HIGH/CRITICAL risk in PROHIBITED zone ===', file=sys.stderr)
for uid, t in targets.items():
    zone = getattr(t, 'zone_type', '')
    risk = getattr(t, 'risk', None)
    if zone == 'PROHIBITED' and risk and str(risk) in ['RiskLevel.HIGH', 'RiskLevel.CRITICAL', 'HIGH', 'CRITICAL']:
        vel = t.velocity_ms
        authorized = getattr(t, 'authorized_responses', [])
        deception_active = getattr(t, 'deception_active', False)
        print(f'{uid}: risk={risk}, vel={vel}, authorized={authorized}, deception={deception_active}', file=sys.stderr)

# Print agent logs for deception
print('\n=== Agent Logs (deception-related) ===', file=sys.stderr)
logs = result.get('agent_log', [])
for log in logs:
    if 'DECEPTION' in log or 'deception' in log.lower():
        print(f'  {log}', file=sys.stderr)

print('\nDone!', file=sys.stderr)

# Check available_catchers in result
print('\n=== Available Cyber-Catchers ===', file=sys.stderr)
catchers = result.get('available_catchers', [])
print(f'Found {len(catchers)} catchers:', file=sys.stderr)
for c in catchers:
    print(f'  {c}', file=sys.stderr)
