from __future__ import annotations

import json
import logging
import os
import pathlib
import re
import subprocess
import time
import unicodedata
from datetime import datetime, timezone
from typing import Any, Callable, Iterable


EXIT_OK = 0
EXIT_USER_ERROR = 2
EXIT_API_ERROR = 3
EXIT_TIMEOUT = 4
EXIT_MANIFEST_CORRUPT = 5
EXIT_REVIEW_UNRESOLVED = 6

_STAGE_DIRS = {"concept", "mesh", "rigged", "animated", "engine", "review"}


def slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_name.lower()
    hyphenated = re.sub(r"[^a-z0-9]+", "-", lowered)
    collapsed = re.sub(r"-+", "-", hyphenated)
    return collapsed.strip("-")


def is_dry_run() -> bool:
    return os.environ.get("PIPELINE_DRY_RUN", "").strip().lower() in {"1", "true", "yes"}


def repo_root(start: pathlib.Path | None = None) -> pathlib.Path | None:
    cwd = pathlib.Path.cwd() if start is None else pathlib.Path(start)
    if cwd.is_file():
        cwd = cwd.parent

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(cwd),
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, OSError):
        return None

    root = result.stdout.strip()
    if not root:
        return None
    return pathlib.Path(root)


def output_dir(slug: str, base: pathlib.Path | None = None) -> pathlib.Path:
    root = pathlib.Path(base) if base is not None else repo_root() or pathlib.Path.cwd()
    path = root / "3d-pipeline-output" / slug
    path.mkdir(parents=True, exist_ok=True)
    return path


def stage_dir(slug: str, stage: str) -> pathlib.Path:
    if stage not in _STAGE_DIRS:
        raise ValueError(f"Unknown stage directory: {stage}")
    path = output_dir(slug) / stage
    path.mkdir(parents=True, exist_ok=True)
    return path


def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not any(getattr(handler, "_pipeline_handler", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("[%(name)s] %(levelname)s: %(message)s"))
        setattr(handler, "_pipeline_handler", True)
        logger.addHandler(handler)

    return logger


def atomic_write_json(path: pathlib.Path | str, obj: Any) -> None:
    target = pathlib.Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f"{target.name}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(obj, handle, indent=2, sort_keys=False, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, target)


def atomic_write_bytes(path: pathlib.Path | str, data: bytes) -> None:
    target = pathlib.Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f"{target.name}.tmp")
    with tmp.open("wb") as handle:
        handle.write(data)
    os.replace(tmp, target)


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def poll(
    callable_returning_status: Callable[[], dict[str, Any]],
    *,
    interval: float = 5.0,
    timeout: float = 600.0,
    status_done: Iterable[str] = frozenset({"done", "succeeded"}),
    status_failed: Iterable[str] = frozenset({"failed", "error"}),
) -> dict[str, Any]:
    done = set(status_done)
    failed = set(status_failed)
    deadline = time.monotonic() + timeout
    last_status: dict[str, Any] | None = None

    while True:
        last_status = callable_returning_status()
        status = str(last_status.get("status", "")).lower()

        if status in done:
            return last_status
        if status in failed:
            raise RuntimeError(f"Polling failed with status: {status}")
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Polling timed out after {timeout:.1f}s")

        time.sleep(interval)
