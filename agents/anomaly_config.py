import math
from dataclasses import dataclass


@dataclass(frozen=True)
class AnomalyThresholds:
    """
    Tunable thresholds for mapping normalized anomaly scores into buckets.

    The incoming score is expressed in units of MADs above the per-cycle
    median reconstruction error (roughly 0–5+).
    """

    normal_max: float = 1.0
    suspect_max: float = 2.5
    # OpenSky/ADS-B aircraft: much more tolerant
    opensky_normal_max: float = 3.5
    opensky_suspect_max: float = 4.5


THRESHOLDS = AnomalyThresholds()


def label_from_score(score: float, is_opensky: bool = False) -> str:
    """
    Map normalized anomaly score to label.
    OpenSky (ADS-B) targets use stricter thresholds – only flag when
    behaviour is truly anomalous.
    """
    if is_opensky:
        if score <= THRESHOLDS.opensky_normal_max:
            return "Normal"
        if score <= THRESHOLDS.opensky_suspect_max:
            return "Suspect"
    else:
        if score <= THRESHOLDS.normal_max:
            return "Normal"
        if score <= THRESHOLDS.suspect_max:
            return "Suspect"
    return "Anomalous"

