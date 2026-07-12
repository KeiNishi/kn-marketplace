from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    from . import _common, _credentials
except ImportError:
    import _common  # type: ignore
    import _credentials  # type: ignore


LOGGER = _common.setup_logger("_local_backend")

DEFAULT_URL = "http://127.0.0.1:7960"
VALID_RESOLUTIONS = (512, 1024, 1536)
MESH_SIMPLIFY_MIN = 10
MESH_SIMPLIFY_MAX = 1000
DEFAULT_SEED = 1234


class LocalBackendError(RuntimeError):
    """Base exception for the local TRELLIS.2-stableprojectorz backend client."""


class BackendUnreachable(LocalBackendError):
    """The backend could not be reached (and could not be auto-started)."""


class BackendBusy(LocalBackendError):
    """The backend is already running a generation (single-job server)."""


class GenerationFailed(LocalBackendError):
    """The backend reported a non-successful generation result."""


def _sanitize(message: str, *, limit: int = 300) -> str:
    return message.strip()[:limit]


def resolve_url(cli_value: str | None) -> str:
    """Resolve the backend base URL: --url > TRELLIS2_SPZ_URL > default."""
    if cli_value:
        return cli_value.rstrip("/")
    env_value = _credentials.optional("TRELLIS2_SPZ_URL")
    if env_value:
        return env_value.rstrip("/")
    return DEFAULT_URL


def resolve_home(cli_value: str | None) -> Path | None:
    """Resolve the install home for auto-start: --spz-home > TRELLIS2_SPZ_HOME > None."""
    if cli_value:
        return Path(cli_value).expanduser().resolve()
    env_value = _credentials.optional("TRELLIS2_SPZ_HOME")
    if env_value:
        return Path(env_value).expanduser().resolve()
    return None


def ping(base_url: str, timeout: float = 5.0) -> dict[str, Any]:
    """GET /ping. Raises BackendUnreachable on connection error/timeout."""
    url = f"{base_url}/ping"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read()
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise BackendUnreachable(
            f"Could not reach local TRELLIS.2 backend at {base_url}: {_sanitize(str(exc))}"
        ) from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise BackendUnreachable(
            f"Local TRELLIS.2 backend at {base_url} returned an invalid /ping response"
        ) from exc


def _poll_status_once(base_url: str, timeout: float = 5.0) -> dict[str, Any] | None:
    try:
        with urllib.request.urlopen(f"{base_url}/status", timeout=timeout) as response:
            return json.loads(response.read())
    except Exception:
        return None


def _spawn_server(home: Path) -> None:
    tools_dir = home / "tools"
    launcher = tools_dir / "projectorz-internal.bat"
    if not launcher.is_file():
        raise BackendUnreachable(
            f"Auto-start launcher not found: {launcher}. Verify TRELLIS2_SPZ_HOME points at a "
            "valid TRELLIS.2-stableprojectorz install directory (expects tools/projectorz-internal.bat)."
        )

    log_path = home / "api-server-autostart.log"
    env = dict(os.environ)
    env["HF_HOME"] = str(home / "code" / "models")
    # Some hosts (including Claude Code shells) set NoDefaultCurrentDirectoryInExePath,
    # which stops cmd.exe from resolving .bat files via the current directory. The
    # fork's launcher chain relies on relative `call` lookups, so drop it for the child.
    env.pop("NoDefaultCurrentDirectoryInExePath", None)

    creationflags = 0
    if hasattr(subprocess, "DETACHED_PROCESS") and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    LOGGER.info("Auto-starting local TRELLIS.2 backend from %s", home)
    with log_path.open("ab") as log_handle:
        # The child process gets its own inherited duplicate of this handle at
        # creation time, so closing our copy when this `with` block exits does
        # not affect the detached process's ability to keep writing to it.
        subprocess.Popen(
            ["cmd", "/c", str(launcher)],
            cwd=str(tools_dir),
            env=env,
            stdout=log_handle,
            stderr=log_handle,
            creationflags=creationflags,
        )


def ensure_server(base_url: str, home: Path | None, wait_seconds: float = 180.0) -> None:
    """Ping the backend; auto-start it from `home` if unreachable, then wait."""
    try:
        ping(base_url, timeout=5)
        return
    except BackendUnreachable:
        pass

    if home is None:
        raise BackendUnreachable(
            f"Local TRELLIS.2 backend is not reachable at {base_url}. Start it manually "
            "(run run-stableprojectorz.bat in the install directory) or set TRELLIS2_SPZ_HOME "
            "in ~/.claude/3d-pipeline/.env to enable auto-start."
        )

    _spawn_server(home)

    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        try:
            ping(base_url, timeout=5)
            return
        except BackendUnreachable:
            time.sleep(3)

    raise BackendUnreachable(
        f"Local TRELLIS.2 backend did not become reachable at {base_url} within "
        f"{wait_seconds:.0f}s after auto-start. Check {home / 'api-server-autostart.log'} for details."
    )


def _clamp_mesh_simplify(value: int) -> int:
    return max(MESH_SIMPLIFY_MIN, min(MESH_SIMPLIFY_MAX, value))


def generate(
    base_url: str,
    image_path: Path,
    *,
    resolution: int,
    mesh_simplify_thousands: int,
    texture_size: int,
    apply_texture: bool,
    seed: int | None,
    timeout: float = 1800.0,
) -> bytes:
    """Run a full synchronous generation and return GLB bytes.

    POST /generate_no_preview is SYNCHRONOUS on this server: it blocks for the
    entire generation (measured 107s at resolution 1024, 294s at 1536) and
    returns the final status in the response body. That response is the sole
    source of truth for success/failure. GET /status is polled from the main
    thread purely to log progress; a "FAILED" seen there before completion is
    the server's idle default, never a real failure signal.
    """
    import requests

    if resolution not in VALID_RESOLUTIONS:
        raise ValueError(f"resolution must be one of {VALID_RESOLUTIONS}, got {resolution}")
    mesh_simplify = _clamp_mesh_simplify(mesh_simplify_thousands)

    status = ping(base_url, timeout=5)
    if status.get("busy"):
        raise BackendBusy(f"Local TRELLIS.2 backend at {base_url} is already busy with another generation")

    fields = {
        "seed": str(seed if seed is not None else DEFAULT_SEED),
        "resolution": str(resolution),
        "mesh_simplify": str(mesh_simplify),
        "texture_size": str(texture_size),
        "apply_texture": "true" if apply_texture else "false",
        "output_format": "glb",
    }

    result: dict[str, Any] = {}
    error: BaseException | None = None

    def _submit() -> None:
        nonlocal result, error
        try:
            with image_path.open("rb") as image_handle:
                files = {"file": (image_path.name, image_handle, "application/octet-stream")}
                response = requests.post(
                    f"{base_url}/generate_no_preview",
                    data=fields,
                    files=files,
                    timeout=timeout,
                )
        except Exception as exc:  # propagated as-is so callers can distinguish timeouts
            error = exc
            return

        if response.status_code >= 400:
            error = GenerationFailed(
                f"generation request failed with HTTP {response.status_code}: {_sanitize(response.text)}"
            )
            return
        try:
            result = response.json()
        except ValueError as exc:
            error = GenerationFailed(f"generation response was not valid JSON: {_sanitize(str(exc))}")

    worker = threading.Thread(target=_submit, name="trellis2-generate", daemon=True)
    worker.start()

    while worker.is_alive():
        worker.join(timeout=5)
        if worker.is_alive():
            progress = _poll_status_once(base_url)
            if progress:
                LOGGER.info(
                    "Generation progress: %s%% %s",
                    progress.get("progress"),
                    progress.get("message") or "",
                )

    if error is not None:
        raise error

    if result.get("status") != "COMPLETE":
        detail = result.get("message") or json.dumps(result)[:300]
        raise GenerationFailed(_sanitize(f"generation ended with status {result.get('status')}: {detail}"))

    download = requests.get(f"{base_url}/download/model", timeout=300)
    if download.status_code >= 400:
        raise GenerationFailed(f"model download failed HTTP {download.status_code}")
    return download.content
