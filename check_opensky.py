"""Check OpenSky count."""
import requests
import json

# Get token
with open('credentials.json') as f:
    creds = json.load(f)

r = requests.post('https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token', data={
    'grant_type': 'client_credentials',
    'client_id': creds['clientId'],
    'client_secret': creds['clientSecret'],
})
token = r.json()['access_token']

# Get states for India
resp = requests.get('https://opensky-network.org/api/states/all',
    headers={'Authorization': f'Bearer {token}'},
    params={'lamin': 6, 'lamax': 36, 'lomin': 68, 'lomax': 97})

states = resp.json()['states']
print(f'OpenSky API returns: {len(states)} aircraft')

# Check how many have valid coordinates
valid = sum(1 for s in states if s[5] is not None and s[6] is not None)
print(f'With valid lat/lon: {valid}')

# Check what's in the backend
from agents.graph import run_cycle
result = run_cycle(
    center_lat=21.1458,
    center_lon=79.0882,
    cycle_id=1,
    manual_injections=[],
    previous_log=[],
    previous_targets={}
)
targets = result.get('active_targets', {})
opensky_targets = [t for t in targets.values() if hasattr(t, 'source') and t.source.value == 'OpenSky ADS-B']
print(f'Backend returns: {len(opensky_targets)} OpenSky targets')
print(f'Total targets: {len(targets)}')
