"""Test cycle counts."""
import logging
logging.basicConfig(level=logging.WARNING)

from agents.graph import run_cycle
from collections import Counter

# Run 3 cycles
prev_targets = {}
for i in range(1, 4):
    print(f"\n=== Cycle {i} ===")
    result = run_cycle(
        center_lat=21.1458,
        center_lon=79.0882,
        cycle_id=i,
        manual_injections=[],
        previous_log=[],
        previous_targets=prev_targets
    )
    targets = result.get('active_targets', {})
    prev_targets = targets
    
    # Count by risk
    risk_counts = Counter()
    for t in targets.values():
        if hasattr(t, 'risk'):
            risk_counts[t.risk.value] += 1
        elif isinstance(t, dict):
            risk_counts[t.get('risk', 'Low')] += 1
    
    # Count by source
    source_counts = Counter()
    for t in targets.values():
        if hasattr(t, 'source'):
            source_counts[t.source.value] += 1
        elif isinstance(t, dict):
            source_counts[t.get('source', 'Unknown')] += 1
    
    print(f"Total: {len(targets)}")
    print(f"Sources: {dict(source_counts)}")
    print(f"Risk: {dict(risk_counts)}")

print("\nDone!")
