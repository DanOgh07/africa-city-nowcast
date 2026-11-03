"""Open-Meteo historical weather (ERA5 reanalysis) ingestor.

Endpoint : https://archive-api.open-meteo.com/v1/archive
Partition: "<region_id>/<year>"  ->  data/raw/open_meteo/<region_id>/<year>/<hash>.json
Terms    : free tier is for NON-COMMERCIAL use only (rate-limited, CC BY 4.0
           attribution required). A commercial use needs a paid key or a
           self-hosted instance. Fine for a portfolio project; revisit if this
           ever feeds a paid product.

Notes
  * ERA5 lags real time by a few days, so the current-year partition is capped
    at (today - LAG_DAYS). Its content changes between runs, so each run lands
    a new hash-named file; older versions are kept (raw layer is immutable).
  * v0 uses ONE point per region (the label city's coordinates). Regions are
    large, so later replace this with area-averaged values over the boundary.
"""
from __future__ import annotations

REPO_ROOT = Path(__file__).resolve().parents[3]  # .../src/nowcast/ingestion/ -> repo root
DEFAULT_REGIONS = REPO_ROOT / "config" / "regions.yml"

import argparse
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import yaml

from .base import BaseIngestor, IngestorConfig

log = logging.getLogger(__name__)

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
LAG_DAYS = 7
DAILY_VARIABLES = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "precipitation_sum",
    "wind_speed_10m_max",
    "shortwave_radiation_sum",
]


class OpenMeteoIngestor(BaseIngestor):
    source = "open_meteo"

    def __init__(self, config: IngestorConfig | None = None, regions: list[dict] | None = None):
        super().__init__(config)
        self._coords = {r["id"]: (r["lat"], r["lon"]) for r in (regions or [])}

    def file_extension(self) -> str:
        return "json"

    # partition looks like "KEN-nairobi/2024"
    def fetch(self, partition: str, **params) -> bytes:
        region_id, year_s = partition.split("/")
        year = int(year_s)
        lat, lon = self._coords[region_id]

        start = date(year, 1, 1)
        end = min(date(year, 12, 31), date.today() - timedelta(days=LAG_DAYS))
        if end < start:
            raise ValueError(f"No complete data yet for {partition}")

        query = urllib.parse.urlencode({
            "latitude": lat,
            "longitude": lon,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": ",".join(DAILY_VARIABLES),
            "timezone": "UTC",  # keep days comparable across regions
        })
        req = urllib.request.Request(
            f"{ARCHIVE_URL}?{query}",
            headers={"User-Agent": "africa-city-nowcast/0.1"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = resp.read()

        # Fail loudly on API-level errors that still return HTTP 200/400 JSON.
        body = json.loads(payload)
        if body.get("error"):
            raise RuntimeError(f"Open-Meteo error for {partition}: {body.get('reason')}")
        return payload


def load_regions(path = DEFAULT_REGIONS):
    cfg = yaml.safe_load(Path(path).read_text())
    regions = cfg["regions"]
    missing = [r["id"] for r in regions if "lat" not in r or "lon" not in r]
    if missing:
        raise ValueError(f"Add lat/lon to these regions in regions.yml: {missing}")
    return regions


def backfill(start_year, end_year, regions_path = DEFAULT_REGIONS, pause_seconds = 1.0):
    regions = load_regions(regions_path)
    ingestor = OpenMeteoIngestor(regions=regions)
    for region in regions:
        for year in range(start_year, end_year + 1):
            try:
                ingestor.run(f"{region['id']}/{year}")
            except urllib.error.HTTPError as exc:
                log.error("%s/%s failed: HTTP %s", region["id"], year, exc.code)
            time.sleep(pause_seconds)  # stay well inside the free-tier rate limits


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="Backfill Open-Meteo daily weather")
    ap.add_argument("--start-year", type=int, default=2013)
    ap.add_argument("--end-year", type=int, default=date.today().year)
    ap.add_argument("--regions", default=DEFAULT_REGIONS)
    args = ap.parse_args()
    backfill(args.start_year, args.end_year, args.regions)
