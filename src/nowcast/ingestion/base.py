"""Shared base class for all ingestors.

Guarantees for every source:
  * raw payloads land untouched in data/raw/<source>/<partition>/
  * each landing has a metadata sidecar (source, fetched_at, sha256, params)
  * reruns are idempotent: identical content is not written twice
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class LandingResult:
    path: Path
    sha256: str
    written: bool  # False when identical content already existed


@dataclass
class IngestorConfig:
    raw_root: Path = Path("data/raw")
    max_retries: int = 3
    backoff_seconds: float = 2.0
    extra: dict = field(default_factory=dict)


class BaseIngestor(ABC):
    #: short unique name, used as the folder under data/raw/
    source: str = ""

    def __init__(self, config: IngestorConfig | None = None):
        if not self.source:
            raise ValueError("Subclasses must set `source`")
        self.config = config or IngestorConfig()

    # ---- to implement per source -------------------------------------------------
    @abstractmethod
    def fetch(self, partition: str, **params) -> bytes:
        """Return the raw payload for one partition (e.g. '2024-06' or 'KEN')."""

    def file_extension(self) -> str:
        return "bin"

    # ---- shared behaviour ---------------------------------------------------------
    def run(self, partition: str, **params) -> LandingResult:
        payload = self._with_retries(lambda: self.fetch(partition, **params))
        return self._land(partition, payload, params)

    def _with_retries(self, fn):
        for attempt in range(1, self.config.max_retries + 1):
            try:
                return fn()
            except Exception as exc:  # noqa: BLE001 - re-raised after final attempt
                if attempt == self.config.max_retries:
                    raise
                delay = self.config.backoff_seconds * 2 ** (attempt - 1)
                log.warning(
                    "%s attempt %d failed (%s); retrying in %.1fs",
                    self.source, attempt, exc, delay,
                )
                time.sleep(delay)

    def _land(self, partition: str, payload: bytes, params: dict) -> LandingResult:
        digest = hashlib.sha256(payload).hexdigest()
        folder = self.config.raw_root / self.source / partition
        folder.mkdir(parents=True, exist_ok=True)
        data_path = folder / f"{digest[:16]}.{self.file_extension()}"

        if data_path.exists():
            log.info("%s/%s unchanged (%s)", self.source, partition, digest[:8])
            return LandingResult(data_path, digest, written=False)

        data_path.write_bytes(payload)
        meta = {
            "source": self.source,
            "partition": partition,
            "params": params,
            "sha256": digest,
            "bytes": len(payload),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        data_path.with_suffix(data_path.suffix + ".meta.json").write_text(
            json.dumps(meta, indent=2, default=str)
        )
        log.info("%s/%s landed %s", self.source, partition, data_path.name)
        return LandingResult(data_path, digest, written=True)
