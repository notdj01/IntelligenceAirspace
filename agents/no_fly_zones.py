from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class NoFlyZone:
    id: str
    name: str
    description: str
    lat: float
    lon: float
    radius_km: float


NO_FLY_ZONES: List[NoFlyZone] = [
    NoFlyZone(
        id="rashtrapati-bhavan-delhi",
        name="Rashtrapati Bhavan & Central Delhi",
        description=(
            "Permanent no-fly zone covering Parliament, PM residence, and central "
            "government enclave."
        ),
        lat=28.6143,
        lon=77.1995,
        radius_km=5.0,
    ),
    NoFlyZone(
        id="taj-mahal-agra",
        name="Taj Mahal, Agra",
        description="Protected monument airspace in Agra.",
        lat=27.1751,
        lon=78.0421,
        radius_km=3.0,
    ),
    NoFlyZone(
        id="barc-mumbai",
        name="BARC, Mumbai",
        description="Bhabha Atomic Research Centre nuclear installation security zone.",
        lat=19.0481,
        lon=72.9106,
        radius_km=3.0,
    ),
    NoFlyZone(
        id="tirumala-temple-ap",
        name="Tirumala Venkateswara Temple",
        description="Temple airspace in Tirupati district, Andhra Pradesh.",
        lat=13.6839,
        lon=79.3473,
        radius_km=3.0,
    ),
    NoFlyZone(
        id="padmanabhaswamy-temple-kerala",
        name="Padmanabhaswamy Temple",
        description="Temple airspace in Thiruvananthapuram, Kerala.",
        lat=8.4828,
        lon=76.9432,
        radius_km=3.0,
    ),
    NoFlyZone(
        id="kalpakkam-nuclear-tn",
        name="Kalpakkam Nuclear Installation",
        description="Approximate 10-km security radius in Tamil Nadu.",
        lat=12.5546,
        lon=80.154,
        radius_km=10.0,
    ),
    NoFlyZone(
        id="tower-of-silence-mumbai",
        name="Tower of Silence, Mumbai",
        description="Restricted heritage zone in South Mumbai.",
        lat=18.9553,
        lon=72.7924,
        radius_km=2.0,
    ),
    NoFlyZone(
        id="mathura-refinery-up",
        name="Mathura Refinery",
        description="Critical petroleum infrastructure in Uttar Pradesh.",
        lat=27.459,
        lon=77.73,
        radius_km=5.0,
    ),
]

