"""Test ROE node."""
from agents.graph import run_cycle

result = run_cycle(21.1458, 79.0882, 1, [], [], {})
targets = result.get('active_targets', {})
print(f'Total targets: {len(targets)}')

# Check samples
for i, (uid, t) in enumerate(list(targets.items())[:3]):
    print(f'\n--- Target {i+1}: {uid} ---')
    print(f'  callsign: {t.callsign}')
    print(f'  label: {t.label.value}')
    print(f'  risk: {t.risk.value}')
    print(f'  zone_type: {t.zone_type}')
    print(f'  legal_basis: {t.legal_basis[:60] if t.legal_basis else "None"}...')
    print(f'  authorized_responses: {t.authorized_responses}')
    print(f'  prohibited_responses: {t.prohibited_responses}')
    print(f'  reporting_required: {t.reporting_required}')
    print(f'  roe_confidence: {t.roe_confidence}')
