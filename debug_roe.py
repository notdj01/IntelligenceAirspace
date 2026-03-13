"""Debug ROE for critical targets."""
from agents.graph import run_cycle

result = run_cycle(21.1458, 79.0882, 1, [], [], {})
targets = result.get('active_targets', {})

# Find critical targets
critical_targets = [(uid, t) for uid, t in targets.items() if t.risk.value == 'Critical']
print(f'Total Critical targets: {len(critical_targets)}')

if critical_targets:
    uid, t = critical_targets[0]
    print(f'\n=== Sample Critical Target: {uid} ===')
    print(f'  label: {t.label.value}')
    print(f'  risk: {t.risk.value}')
    print(f'  zone_type: {t.zone_type}')
    print(f'  legal_basis: {t.legal_basis}')
    print(f'  authorized_responses: {t.authorized_responses}')
    print(f'  prohibited_responses: {t.prohibited_responses}')
    print(f'  reporting_required: {t.reporting_required}')
    
    # Check if it's in the dict
    d = t.to_dict()
    print(f'\n=== Serialized dict keys ===')
    print(f'  zone_type in dict: {"zone_type" in d}')
    print(f'  authorized_responses in dict: {"authorized_responses" in d}')
    if "authorized_responses" in d:
        print(f'  authorized_responses value: {d["authorized_responses"]}')
else:
    print("No critical targets found")
