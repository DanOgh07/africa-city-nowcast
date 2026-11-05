import hashlib
import json
import logging
from pathlib import Path

import pytest

from nowcast.ingestion import dose
from nowcast.ingestion.base import IngestorConfig

CSV = b"country,region,GID_1,year\nKenya,Nairobi,KEN.30_1,2013\n"
MD5 = hashlib.md5(CSV).hexdigest()

API = dose.API_URL.format(id=dose.RECORD_ID)
LATEST = "https://zenodo.org/api/records/20035157/versions/latest"
FILE = "https://zenodo.org/files/DOSE_V2.14.csv"


def make_fake(monkeypatch, *, api_md5=MD5, file_bytes=CSV, latest_id=dose.RECORD_ID,
              keys=("DOSE_V2.14.csv",)):
    record = {
        "id": int(dose.RECORD_ID),
        "links": {"latest": LATEST},
        "files": [
            {"key": k, "checksum": f"md5:{api_md5}", "links": {"self": FILE}} for k in keys
        ],
    }

    def fake_get(url, timeout=120):
        if url == API:
            return json.dumps(record).encode()
        if url == LATEST:
            return json.dumps({"id": int(latest_id), "metadata": {"version": "9.9"}}).encode()
        if url == FILE:
            return file_bytes
        raise AssertionError(f"unexpected URL {url}")

    monkeypatch.setattr(dose, "_http_get", fake_get)
    monkeypatch.setattr(dose, "EXPECTED_MD5", MD5)


def ingestor(tmp_path):
    return dose.DoseIngestor(IngestorConfig(raw_root=Path(tmp_path), max_retries=1))


def test_lands_csv_and_is_idempotent(monkeypatch, tmp_path, caplog):
    make_fake(monkeypatch)
    ing = ingestor(tmp_path)
    with caplog.at_level(logging.WARNING):
        first = ing.run("v2.14")
        second = ing.run("v2.14")
    assert first.written and not second.written
    assert first.path.read_bytes() == CSV
    assert "v2.14" in first.path.as_posix()
    assert "newer DOSE version" not in caplog.text


def test_warns_when_newer_version_exists(monkeypatch, tmp_path, caplog):
    make_fake(monkeypatch, latest_id="99999999")
    with caplog.at_level(logging.WARNING):
        ingestor(tmp_path).run("v2.14")
    assert "newer DOSE version" in caplog.text


def test_record_checksum_mismatch_raises_before_download(monkeypatch, tmp_path):
    make_fake(monkeypatch, api_md5="0" * 32)
    with pytest.raises(dose.PinMismatchError):
        ingestor(tmp_path).run("v2.14")


def test_corrupted_download_raises(monkeypatch, tmp_path):
    make_fake(monkeypatch, file_bytes=CSV + b"corrupted")
    with pytest.raises(dose.ChecksumError):
        ingestor(tmp_path).run("v2.14")


def test_wrong_partition_rejected(monkeypatch, tmp_path):
    make_fake(monkeypatch)
    with pytest.raises(ValueError):
        ingestor(tmp_path).run("v3.0")


def test_ambiguous_csvs_resolved_by_name_or_rejected(monkeypatch, tmp_path):
    make_fake(monkeypatch, keys=("DOSE_V2.14.csv", "other.csv"))
    assert ingestor(tmp_path).run("v2.14").written          # name pattern picks one

    make_fake(monkeypatch, keys=("a.csv", "b.csv"))
    with pytest.raises(dose.PinMismatchError):
        ingestor(tmp_path / "second").run("v2.14")
