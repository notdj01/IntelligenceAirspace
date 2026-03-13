"""Debug why low-risk targets are showing as Critical."""
from agents.graph import run_cycle
from agents.state import RiskLevel, TargetLabel

result = run_cycle(
    center_lat=21.1458,
    center_lon=79.0882,
    cycle_id=1,
    manual_injections=[],
    previous_log=[],
    previous_targets={}
)

targets = result.get('active_targets', {})

# Analyze targets
print("=== Risk Analysis ===")
critical_with_low_score = []
low_score_count = 0
total = 0

for uid, t in targets.items():
    total += 1
    score = getattr(t, 'risk_score', None)
    risk = t.risk
    
    if score is not None and score <= 25 and risk == RiskLevel.CRITICAL:
        critical_with_low_score.append({
            'uid': uid,
            'score': score,
            'risk': risk.value,
            'label': t.label.value,
            'source': t.source.value if hasattr(t.source, 'value') else str(t.source),
            'icao24': t.icao24,
            'callsign': t.callsign,
            'velocity': t.velocity_ms,
            'altitude': t.altitude_m,
        })
    elif score is not None and score <= 25:
        low_score_count += 1

print(f"Total targets: {total}")
print(f"Low score (<=25) but NOT Critical: {low_score_count}")
print(f"Low score (<=25) but IS Critical: {len(critical_with_low_score)}")

if critical_with_low_score:
    print("\n=== Problem Targets ===")
    for t in critical_with_low_score[:5]:
        print(f"  {t['uid']}: score={t['score']}, risk={t['risk']}, label={t['label']}, source={t['source']}")
        print(f"    callsign={t['callsign']}, vel={t['velocity']:.0f}m/s, alt={t['altitude']:.0f}m")
