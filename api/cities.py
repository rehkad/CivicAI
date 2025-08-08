from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CityPreset:
    socrata_domain: Optional[str] = None
    socrata_dataset: Optional[str] = None
    arcgis_service_url: Optional[str] = None


PRESETS: dict[str, CityPreset] = {
    # NYC 311 Service Requests
    "new_york_city": CityPreset(
        socrata_domain="data.cityofnewyork.us",
        socrata_dataset="erm2-nwe9",
    ),
    # San Francisco 311 Cases
    "san_francisco": CityPreset(
        socrata_domain="data.sfgov.org",
        socrata_dataset="wmuk-udn2",
    ),
}



