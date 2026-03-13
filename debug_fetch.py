"""Debug why OpenSky targets are being filtered."""
import requests
import json
import os

cred_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json")
with open(cred_path) as f:
    creds = json.load(f)

# Get token
r = requests.post('https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token', data={
    'grant_type': 'client_credentials',
    'client_id': creds['clientId'],
    'client_secret': creds['clientSecret'],
})
token = r.json()['access_token']

# Get states for India bounding box (same as fetch_node)
bbox = (21.1458 - 15.0, 21.1458 + 15.0, 79.0882 - 15.0, 79.0882 + 15.0)
resp = requests.get('https://opensky-network.org/api/states/all',
    headers={'Authorization': f'Bearer {token}'},
    params={'lamin': bbox[0], 'lamax': bbox[1], 'lomin': bbox[2], 'lomax': bbox[3]})

states = resp.json()['states']
print(f'Raw OpenSky API: {len(states)} aircraft')

# Now simulate the filtering logic from fetch_node
# Index mapping for OpenSky states:
# 0: icao24, 1: callsign, 2: origin_country, 3: time_position, 4: last_contact,
# 5: lon, 6: lat, 7: baro_altitude, 8: on_ground, 9: velocity, 10: heading,
# 11: vertical_rate, 12: sensors, 13: geo_altitude, 14: squawk, 15: spi, 16: position_source

filtered_no_callsign = 0
filtered_no_country = 0
filtered_no_latlon = 0
valid = 0

for s in states:
    if s[1] is None:
        filtered_no_callsign += 1
    if s[2] is None:
        filtered_no_country += 1
    if s[5] is None or s[6] is None:
        filtered_no_latlon += 1
    if s[1] is not None and s[2] is not None and s[5] is not None and s[6] is not None:
        valid += 1

print(f'Filtered (no callsign): {filtered_no_callsign}')
print(f'Filtered (no country): {filtered_no_country}')
print(f'Filtered (no lat/lon): {filtered_no_latlon}')
print(f'Valid: {valid}')

# Now check what happens in fetch_node at line 96-117
# The issue is s[1] and s[2] - but wait, those are callsign and origin_country
# Actually wait - line 97-98 says: if s[1] is None or s[2] is None: continue
# This filters out ANY aircraft that doesn't have BOTH callsign AND origin_country!

print(f'\n=== Analysis ===')
print(f'If we filter only callsign OR country missing: {filtered_no_callsign + filtered_no_country - (filtered_no_callsign and filtered_no_country)}')
