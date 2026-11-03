import json
from pathlib import Path
from unittest.mock import patch

import pytest

from nowcast.ingestion.base import IngestorConfig
from nowcast.ingestion.open_meteo import OpenMeteoIngestor, load_regions

FAKE = json.dumps({"daily": {"time": ["2023-01-01"], "temperature_2m_max": [24.1]}}).encode()
REGIONS = [{"id": "KEN-nairobi", "lat": -1.286, "lon": 36.817}]


class FakeResp:
    def __init__(self, data): self.data = data
    def read(self): return self.data
    def __enter__(self): return self
    def __exit__(self, *a): return False


def make(tmp_path):
    return OpenMeteoIngestor(IngestorConfig(raw_root=Path(tmp_path)), regions=REGIONS)


def test_lands_once_and_is_idempotent(tmp_path):
    with patch("urllib.request.urlopen", return_value=FakeResp(FAKE)) as m:
        ing = make(tmp_path)
        first = ing.run("KEN-nairobi/2023")
        second = ing.run("KEN-nairobi/2023")
    assert first.written and not second.written
    assert "KEN-nairobi/2023" in str(first.path)
    url = m.call_args[0][0].full_url
    assert "archive-api.open-meteo.com" in url and "latitude=-1.286" in url
    assert "start_date=2023-01-01" in url and "end_date=2023-12-31" in url


def test_api_error_payload_raises(tmp_path):
    bad = json.dumps({"error": True, "reason": "bad variable"}).encode()
    with patch("urllib.request.urlopen", return_value=FakeResp(bad)):
        ing = make(tmp_path)
        ing.config.max_retries = 1
        with pytest.raises(RuntimeError):
            ing.run("KEN-nairobi/2023")


def test_load_regions_requires_coordinates(tmp_path):
    p = tmp_path / "r.yml"
    p.write_text("regions:\n  - {id: A}\n")
    with pytest.raises(ValueError):
        load_regions(p)
