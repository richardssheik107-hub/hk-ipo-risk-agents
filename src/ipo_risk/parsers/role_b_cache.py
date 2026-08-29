"""Content-addressed local cache for the Role-B Development parser.

The cache is deliberately local and contains deterministic PDF derivatives
only.  Cache identities are SHA-256/fingerprint based; paths, case ids, Gold,
Validation labels, and Blind outcomes are never part of persisted payloads.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import time
from typing import Any
from uuid import uuid4


CACHE_FORMAT_VERSION = "v046_role_b_content_cache_v1"
_SAFE_STAGE = frozenset({"raw_pages", "table_reconstruction", "parser_chunks"})


def canonical_json_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass
class CacheRunMetrics:
    """Per-parser-invocation cache counters and wall-clock timings."""

    hits: dict[str, int] = field(
        default_factory=lambda: {stage: 0 for stage in sorted(_SAFE_STAGE)}
    )
    misses: dict[str, int] = field(
        default_factory=lambda: {stage: 0 for stage in sorted(_SAFE_STAGE)}
    )
    timings_ms: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "parser_cache_hits": self.hits["parser_chunks"],
            "parser_cache_misses": self.misses["parser_chunks"],
            "table_cache_hits": self.hits["table_reconstruction"],
            "table_cache_misses": self.misses["table_reconstruction"],
            "raw_page_cache_hits": self.hits["raw_pages"],
            "raw_page_cache_misses": self.misses["raw_pages"],
            # Reserved stage counters keep every benchmark summary stable while
            # retrieval/fact caches are introduced only after profiling proves value.
            "retrieval_cache_hits": 0,
            "retrieval_cache_misses": 0,
            "fact_cache_hits": 0,
            "fact_cache_misses": 0,
            "stage_wall_clock_ms": {
                key: round(value, 3) for key, value in sorted(self.timings_ms.items())
            },
        }


class RoleBContentCache:
    """Small, atomic, process-safe cache for JSON-primitive stage payloads."""

    def __init__(self, root: Path, *, lock_timeout_seconds: float = 60.0) -> None:
        self.root = Path(root)
        self.lock_timeout_seconds = lock_timeout_seconds

    def _path(self, stage: str, input_hash: str, fingerprint: str) -> Path:
        if stage not in _SAFE_STAGE:
            raise ValueError(f"unsupported cache stage:{stage}")
        for value in (input_hash, fingerprint):
            if not value or any(character not in "0123456789abcdef" for character in value):
                raise ValueError("cache identities must be lowercase hexadecimal")
        # A full combined digest retains collision resistance while avoiding
        # Windows MAX_PATH failures in deeply nested pytest/worktree roots.
        identity = sha256(f"{stage}:{input_hash}:{fingerprint}".encode("ascii")).hexdigest()
        stage_name = {
            "raw_pages": "raw",
            "table_reconstruction": "tables",
            "parser_chunks": "chunks",
        }[stage]
        return self.root / stage_name / identity[:2] / f"{identity}.json.gz"

    @staticmethod
    def _read(path: Path, *, stage: str, input_hash: str, fingerprint: str) -> Any | None:
        try:
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                envelope = json.load(handle)
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None
        if not isinstance(envelope, Mapping):
            return None
        if (
            envelope.get("cache_format_version") != CACHE_FORMAT_VERSION
            or envelope.get("stage") != stage
            or envelope.get("input_hash") != input_hash
            or envelope.get("fingerprint") != fingerprint
        ):
            return None
        payload = envelope.get("payload")
        if envelope.get("payload_hash") != canonical_json_hash(payload):
            return None
        return payload

    @staticmethod
    def _write_atomic(
        path: Path,
        *,
        stage: str,
        input_hash: str,
        fingerprint: str,
        payload: Any,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        envelope = {
            "cache_format_version": CACHE_FORMAT_VERSION,
            "stage": stage,
            "input_hash": input_hash,
            "fingerprint": fingerprint,
            "payload_hash": canonical_json_hash(payload),
            "payload": payload,
        }
        temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid4().hex}.tmp")
        try:
            with gzip.open(temporary, "wt", encoding="utf-8", compresslevel=3) as handle:
                json.dump(envelope, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()

    def load_or_build(
        self,
        *,
        stage: str,
        input_hash: str,
        fingerprint: str,
        builder: Callable[[], Any],
        metrics: CacheRunMetrics,
    ) -> Any:
        path = self._path(stage, input_hash, fingerprint)
        cached = self._read(
            path, stage=stage, input_hash=input_hash, fingerprint=fingerprint
        )
        if cached is not None:
            metrics.hits[stage] += 1
            return cached

        lock_path = path.with_suffix(path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.lock_timeout_seconds
        lock_fd: int | None = None
        while lock_fd is None:
            try:
                lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                cached = self._read(
                    path, stage=stage, input_hash=input_hash, fingerprint=fingerprint
                )
                if cached is not None:
                    metrics.hits[stage] += 1
                    return cached
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"cache writer lock timeout:{stage}") from None
                time.sleep(0.05)

        try:
            # Another writer can finish between the first read and lock acquisition.
            cached = self._read(
                path, stage=stage, input_hash=input_hash, fingerprint=fingerprint
            )
            if cached is not None:
                metrics.hits[stage] += 1
                return cached
            metrics.misses[stage] += 1
            payload = builder()
            self._write_atomic(
                path,
                stage=stage,
                input_hash=input_hash,
                fingerprint=fingerprint,
                payload=payload,
            )
            return payload
        finally:
            if lock_fd is not None:
                os.close(lock_fd)
            lock_path.unlink(missing_ok=True)
