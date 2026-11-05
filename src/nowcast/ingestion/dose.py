"""DOSE ground-truth ingestor (Zenodo).

Pinned to DOSE v2.14 (Zenodo record 20035157, DOI 10.5281/zenodo.20035157).
Lands the raw CSV, untouched, in data/raw/dose/v2.14/ via BaseIngestor.

Safeguards
  * the record's published md5 must equal EXPECTED_MD5 (checked BEFORE the
    17 MB download), and the downloaded bytes must hash to EXPECTED_MD5 too
  * if Zenodo reports a newer version of the record, a warning is logged
    (never fatal; a new version is adopted deliberately, by editing the pin)

License: CC BY 4.0. Credit: Wenz, Carr, Kogel, Kotz & Kalkuhl (DOSE).

Usage:  python -m nowcast.ingestion.dose
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import urllib.request
from pathlib import Path

from .base import BaseIngestor, IngestorConfig

log = logging.getLogger(__name__)

RECORD_ID = "20035157"
DOSE_VERSION = "2.14"
EXPECTED_MD5 = "d594cc2cf9198f2fa5cc25c6fe696965"
API_URL = "https://zenodo.org/api/records/{id}"
CSV_NAME = re.compile(r"^DOSE_?V[\d.]+\.csv$", re.IGNORECASE)
REPO_ROOT = Path(__file__).resolve().parents[3]


class PinMismatchError(RuntimeError):
    """The Zenodo record no longer matches the version this code is pinned to."""


class ChecksumError(RuntimeError):
    """Downloaded bytes do not match the pinned md5."""


def _http_get(url, timeout = 120):
    req = urllib.request.Request(url, headers={"User-Agent": "africa-city-nowcast/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _get_json(url):
    return json.loads(_http_get(url, timeout=60))


def _norm_md5(checksum):
    return (checksum or "").removeprefix("md5:").strip().lower()


def _csv_entry(record):
    files = record.get("files", [])
    if isinstance(files, dict):                      # newer API shape
        files = list(files.get("entries", {}).values())
    csvs = [f for f in files if f.get("key", "").lower().endswith(".csv")]
    if len(csvs) > 1:
        csvs = [f for f in csvs if CSV_NAME.match(f["key"])]
    if len(csvs) != 1:
        raise PinMismatchError(
            f"Expected exactly one DOSE CSV in record {RECORD_ID}, found "
            f"{[f.get('key') for f in csvs]}"
        )
    return csvs[0]


class DoseIngestor(BaseIngestor):
    source = "dose"

    def file_extension(self):
        return "csv"

    def fetch(self, partition: str, **params):
        if partition != f"v{DOSE_VERSION}":
            raise ValueError(f"This ingestor is pinned to v{DOSE_VERSION}, got {partition!r}")

        record = _get_json(API_URL.format(id=RECORD_ID))
        entry = _csv_entry(record)

        api_md5 = _norm_md5(entry.get("checksum"))
        if api_md5 and api_md5 != EXPECTED_MD5:
            raise PinMismatchError(
                f"Record md5 {api_md5} != pinned {EXPECTED_MD5}. "
                "The file behind this record changed; review before adopting."
            )
        self._warn_if_newer(record)

        url = entry.get("links", {}).get("self") or (
            f"https://zenodo.org/records/{RECORD_ID}/files/{entry['key']}?download=1"
        )
        payload = _http_get(url)
        got = hashlib.md5(payload).hexdigest()
        if got != EXPECTED_MD5:
            raise ChecksumError(f"Downloaded md5 {got} != pinned {EXPECTED_MD5}")
        return payload

    @staticmethod
    def _warn_if_newer(record):
        try:
            latest_url = record.get("links", {}).get("latest")
            if not latest_url:
                return
            latest = _get_json(latest_url)
            latest_id = str(latest.get("id") or latest.get("recid") or "")
            if latest_id and latest_id != RECORD_ID:
                version = latest.get("metadata", {}).get("version", "?")
                log.warning(
                    "A newer DOSE version is available on Zenodo (record %s, version %s). "
                    "Pinned: %s (v%s). Review the changes before upgrading.",
                    latest_id, version, RECORD_ID, DOSE_VERSION,
                )
        except Exception as exc:  # noqa: BLE001 - advisory check must never break ingestion
            log.debug("Newer-version check skipped: %s", exc)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = IngestorConfig(raw_root=REPO_ROOT / "data" / "raw")
    result = DoseIngestor(config).run(f"v{DOSE_VERSION}")
    print(f"{'Landed' if result.written else 'Already present'}: {result.path}")


if __name__ == "__main__":
    main()
