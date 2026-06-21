"""Verbose/log helpers for sn-init.

Quiet by default. Verbose prints each step + writes JSON Lines to target/.sn-init.log.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


class StepLogger:
    def __init__(self, target: Path | None = None, verbose: bool = False):
        self.target = target
        self.verbose = verbose
        # Lazy: log_path resolved on first write. Avoids creating the target dir
        # prematurely, which would break the atomic tmp-dir + mv pattern.
        self.log_path: Path | None = None

    def set_target(self, target: Path) -> None:
        """Redirect future log writes to a new target (e.g., after atomic mv)."""
        self.target = target
        self.log_path = None  # force re-resolve on next write

    def step(self, action: str, path: str | Path = "", **extra) -> "StepCtx":
        return StepCtx(self, action, str(path), extra)

    def info(self, msg: str) -> None:
        if self.verbose:
            print(msg, file=sys.stderr)

    def write_record(self, record: dict) -> None:
        if not self.verbose or self.target is None:
            return
        if self.log_path is None:
            self.log_path = self.target / ".sn-init.log"
        if not self.log_path.parent.exists():
            return  # target dir not materialized yet; drop record silently
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


class StepCtx:
    def __init__(self, logger: StepLogger, action: str, path: str, extra: dict):
        self.logger = logger
        self.action = action
        self.path = path
        self.extra = extra
        self.t0 = 0.0

    def __enter__(self) -> "StepCtx":
        self.t0 = time.perf_counter()
        if self.logger.verbose:
            print(f"  → {self.action} {self.path}", file=sys.stderr)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        elapsed_ms = int((time.perf_counter() - self.t0) * 1000)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "action": self.action,
            "path": self.path,
            "duration_ms": elapsed_ms,
            "result": "error" if exc else "ok",
            **self.extra,
        }
        if exc:
            record["error"] = repr(exc)
        self.logger.write_record(record)
        if self.logger.verbose and not exc:
            print(f"    ✓ {elapsed_ms}ms", file=sys.stderr)
        return False
