from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable, TypeVar

try:
    from . import _common
except ImportError:
    import _common  # type: ignore


LOGGER = _common.setup_logger("_codex_backend")

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
LOGIN_STATUS_TIMEOUT = 20.0
SUBSCRIPTION_MARKER = "Logged in using ChatGPT"
IMAGEGEN_UNAVAILABLE_MARKER = "IMAGEGEN_UNAVAILABLE"
LOCK_RETRY_TIMEOUT = 120.0
LOCK_RETRY_INTERVAL = 0.5

T = TypeVar("T")


def _retry_on_lock(operation: Callable[[], T]) -> T:
    """Run a filesystem operation, retrying transient Windows file locks.

    Right after codex exec exits, the freshly written staging PNG can stay
    locked by an external process for a while: Windows Defender's
    block-at-first-sight cloud check holds unknown new files with read
    access denied (but delete allowed) for up to about a minute, and a
    lingering handle from the codex process tree can do the same briefly.
    That is an OS-level timing condition, not a code defect, so a bounded
    retry is the correct handling; if the lock persists past
    LOCK_RETRY_TIMEOUT seconds the PermissionError propagates.
    """
    deadline = time.monotonic() + LOCK_RETRY_TIMEOUT
    waited = 0.0
    while True:
        try:
            return operation()
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            if waited and waited % 10 < LOCK_RETRY_INTERVAL:
                LOGGER.info("Staging file still locked by another process; waiting (%.0fs)", waited)
            time.sleep(LOCK_RETRY_INTERVAL)
            waited += LOCK_RETRY_INTERVAL


class CodexBackendError(RuntimeError):
    """Raised when the Codex CLI image backend fails.

    `usage_limit` is set when the failure was identified as the Codex
    subscription's usage limit being exhausted, so callers can surface a
    distinct, actionable failure kind instead of a generic error.
    """

    def __init__(self, message: str, *, usage_limit: bool = False) -> None:
        super().__init__(message)
        self.usage_limit = usage_limit


def find_codex() -> str | None:
    """Locate the codex CLI executable (resolves codex.cmd on Windows)."""
    return shutil.which("codex")


def subscription_status() -> tuple[bool, str]:
    """Check whether the codex CLI is logged in with an active ChatGPT subscription.

    Returns (active, detail). Any failure to run the CLI (missing binary,
    timeout, OS error) is treated as inactive rather than raised, since this
    is a best-effort detection used for backend auto-selection and doctor
    reporting.
    """
    codex_path = find_codex()
    if codex_path is None:
        return False, "codex CLI not found on PATH"

    try:
        result = subprocess.run(
            [codex_path, "login", "status"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=LOGIN_STATUS_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return False, "codex login status timed out"
    except (FileNotFoundError, OSError) as exc:
        return False, f"could not run codex login status: {exc}"

    combined = f"{result.stdout}\n{result.stderr}"
    if result.returncode == 0 and SUBSCRIPTION_MARKER in combined:
        return True, SUBSCRIPTION_MARKER

    detail = combined.strip().splitlines()[-1] if combined.strip() else f"exit code {result.returncode}"
    return False, detail


def resolve_backend(explicit: str | None) -> tuple[str, str]:
    """Resolve which concept-art backend to use: codex or openai.

    Precedence: explicit argument > PIPELINE_CONCEPT_BACKEND env var > auto
    detection (codex CLI present and subscription active -> codex, else
    openai). Raises ValueError for invalid explicit/env values, and when an
    explicit "codex" request cannot actually be satisfied.
    """
    if explicit is not None:
        choice = explicit.strip().lower()
        if choice not in {"codex", "openai"}:
            raise ValueError(f"Invalid --backend value: {explicit}. Expected one of: codex, openai")
        if choice == "codex":
            codex_path = find_codex()
            if codex_path is None:
                raise ValueError("--backend codex was requested but the codex CLI was not found on PATH")
            active, detail = subscription_status()
            if not active:
                raise ValueError(f"--backend codex was requested but no active Codex subscription was found: {detail}")
            return "codex", detail
        return "openai", "explicit --backend openai"

    env_value = os.environ.get("PIPELINE_CONCEPT_BACKEND")
    if env_value:
        choice = env_value.strip().lower()
        if choice not in {"codex", "openai", "auto"}:
            raise ValueError(
                f"Invalid PIPELINE_CONCEPT_BACKEND value: {env_value}. Expected one of: codex, openai, auto"
            )
        if choice == "codex":
            codex_path = find_codex()
            if codex_path is None:
                raise ValueError("PIPELINE_CONCEPT_BACKEND=codex was set but the codex CLI was not found on PATH")
            active, detail = subscription_status()
            if not active:
                raise ValueError(
                    f"PIPELINE_CONCEPT_BACKEND=codex was set but no active Codex subscription was found: {detail}"
                )
            return "codex", detail
        if choice == "openai":
            return "openai", "PIPELINE_CONCEPT_BACKEND=openai"
        # "auto" falls through to auto-detection below.

    codex_path = find_codex()
    if codex_path is None:
        return "openai", "codex CLI not found; falling back to openai"

    active, detail = subscription_status()
    if active:
        return "codex", detail
    return "openai", f"codex subscription not active ({detail}); falling back to openai"


def _generated_images_root() -> Path:
    """Return the Codex CLI's generated-images root directory.

    Honors the CODEX_HOME environment variable (same as the Codex CLI
    itself); defaults to ~/.codex. Codex writes each `image_gen` tool call's
    output PNG under `<root>/<session-uuid>/call_*.png`, so a new
    subdirectory appearing here during a run is evidence the built-in tool
    actually ran.
    """
    codex_home = os.environ.get("CODEX_HOME")
    base = Path(codex_home) if codex_home else Path.home() / ".codex"
    return base / "generated_images"


def _existing_subdirs(root: Path) -> set[str]:
    if not root.is_dir():
        return set()
    return {entry.name for entry in root.iterdir() if entry.is_dir()}


def generate_image(prompt: str, out_path: Path, *, timeout: float = 600.0) -> None:
    """Generate one PNG image via the Codex CLI's built-in gpt-image-2 tool.

    Runs `codex exec` in a freshly created, empty temporary staging
    directory (never inside the pipeline workspace), so the agent cannot
    see pipeline.json or the pipeline's own scripts and cannot be tempted
    into "helping" by running them. The prompt follows the Codex system
    imagegen skill's schema (use case + labeled request + execution
    requirements) and demands the built-in image_gen tool; the agent's only
    job is to generate one image and print a sentinel.

    The output image is collected directly from the Codex CLI's own
    generated-images artifact (`$CODEX_HOME/generated_images/<session>/
    call_*.png`, written by the codex main process), NOT from a file the
    sandboxed agent copies into place: files created by the sandboxed shell
    can stay read-locked by the Codex process tree long after codex exec
    exits, and the artifact doubles as provenance that the built-in tool --
    not hand-written code -- produced the image. A run that yields no new
    artifact fails. The newest new artifact is validated (PNG magic) and
    written atomically to out_path. The staging directory is always removed
    afterward, which also discards any .git/.agents/.codex pollution Codex
    leaves behind.

    Raises CodexBackendError (with usage_limit set when applicable) or
    TimeoutError on failure.
    """
    codex_path = find_codex()
    if codex_path is None:
        raise CodexBackendError("codex CLI not found on PATH")

    full_prompt = (
        "Use case: stylized-concept\n"
        "Asset type: multi-angle concept art for a 3D game asset pipeline\n\n"
        f"Primary request:\n{prompt}\n\n"
        "Execution requirements:\n"
        "- This request is issued programmatically by the 3d-asset-pipeline's own scripts. Do NOT invoke "
        "any 3d-asset-pipeline skill, command, or script, and do not read or modify any project files.\n"
        "- Use your built-in image generation tool (image_gen, gpt-image-2) to generate exactly one image, "
        "then print IMAGEGEN_OK. The tool's saved output is collected automatically afterward; do not "
        "move, copy, or save any files yourself, and do not create any files in the working directory.\n"
        "- If the built-in image_gen tool is NOT available in your tool list, print exactly "
        f"{IMAGEGEN_UNAVAILABLE_MARKER} and stop. Never draw or synthesize the image with code (no Pillow, "
        "no SVG, no matplotlib, no scripts) -- a code-drawn image is a failure."
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)

    images_root = _generated_images_root()
    before_dirs = _existing_subdirs(images_root)

    staging_dir = Path(tempfile.mkdtemp(prefix="codex-concept-"))
    try:
        LOGGER.info("Generating %s via Codex CLI (gpt-image-2)", out_path.name)
        last_message_path = staging_dir / "last-message.txt"
        try:
            # The prompt is passed via stdin ("-"), never as an argv token: on
            # Windows the codex CLI is an npm .cmd shim, and cmd.exe argument
            # expansion truncates a multi-line argv at the first newline.
            result = subprocess.run(
                [
                    codex_path,
                    "exec",
                    "--sandbox",
                    "workspace-write",
                    "--skip-git-repo-check",
                    "--output-last-message",
                    str(last_message_path),
                    "-",
                ],
                cwd=str(staging_dir),
                input=full_prompt,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"codex exec timed out after {timeout:.0f}s generating {out_path.name}") from exc

        if result.returncode != 0:
            tail = (result.stderr or result.stdout or "").strip()[-500:]
            combined_lower = f"{result.stdout}\n{result.stderr}".lower()
            if "usage limit" in combined_lower:
                message = (
                    "Codex subscription usage limit is exhausted. Retry after the reset time shown below, "
                    f"or re-run with --backend openai to use the pay-per-use API instead.\n{tail}"
                )
                raise CodexBackendError(message, usage_limit=True)
            raise CodexBackendError(f"codex exec failed with exit code {result.returncode}: {tail}")

        # The sentinel must be checked against the agent's final message only
        # (--output-last-message): codex exec echoes the full prompt — which
        # itself names the sentinel — to stdout, so scanning stdout would
        # always self-trigger.
        try:
            last_message = last_message_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            last_message = ""
        if IMAGEGEN_UNAVAILABLE_MARKER in last_message:
            raise CodexBackendError(
                "The built-in image generation tool was unavailable in the codex exec session "
                f"(codex printed {IMAGEGEN_UNAVAILABLE_MARKER}). Re-run with --backend openai to use the "
                "pay-per-use API instead."
            )

        after_dirs = _existing_subdirs(images_root)
        new_dirs = after_dirs - before_dirs
        artifacts = [
            artifact for name in new_dirs for artifact in images_root.joinpath(name).glob("*.png")
        ]
        if not artifacts:
            diagnostics = (last_message or (result.stdout or "")).strip()[-500:]
            raise CodexBackendError(
                "codex exec finished without using the built-in image generation tool (no new "
                f"session artifact appeared under {images_root}), so there is no trusted image to "
                f"collect. Last output:\n{diagnostics}"
            )

        newest = max(artifacts, key=lambda artifact: artifact.stat().st_mtime)
        data = _retry_on_lock(newest.read_bytes)
        if not data.startswith(PNG_MAGIC):
            raise CodexBackendError(
                f"The generated-images artifact {newest.name} is not a valid PNG file."
            )

        _common.atomic_write_bytes(out_path, data)
    except PermissionError as exc:
        raise CodexBackendError(
            f"The generated image for {out_path.name} stayed locked for more than "
            f"{LOCK_RETRY_TIMEOUT:.0f}s after codex exec finished: {exc}"
        ) from exc
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)
