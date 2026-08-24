"""Shared helpers for the audio-asset-pipeline scripts.

Mirrors the conventions of the 3d-asset-pipeline `_common.py`: stdlib only,
explicit exit codes, atomic JSON writes, UTC timestamps, and forward-slash
paths that work identically on Windows and POSIX.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import re
import subprocess
import tempfile
import unicodedata
from datetime import datetime, timezone
from typing import Any, Sequence


EXIT_OK = 0
EXIT_USER_ERROR = 2
EXIT_BACKEND_ERROR = 3
EXIT_TIMEOUT = 4
EXIT_MANIFEST_CORRUPT = 5

OUTPUT_ROOT = "audio-pipeline-output"
# Stages that own a directory. "requirement" is manifest-only (no artifacts).
STAGE_DIRS = ("generate", "post", "review")
# Generation stacks, each with its own venv under <data_dir>/venvs/<name>.
STACKS = ("sa3", "acestep", "minimax")

# A slug becomes a directory name, so it is validated at the trust boundary.
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
# Reserved on Windows; rejected everywhere so a manifest stays portable. Slugs
# cannot contain dots, so comparing the whole slug is sufficient.
_RESERVED_NAMES = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{digit}" for digit in range(1, 10)}
    | {f"lpt{digit}" for digit in range(1, 10)}
)
# Enough of a failing command's output to act on, without flooding the console.
_TAIL_CHARS = 2000


def slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    hyphenated = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower())
    return re.sub(r"-+", "-", hyphenated).strip("-")[:64]


def validate_slug(slug: str) -> str:
    if not isinstance(slug, str) or not _SLUG_RE.match(slug):
        raise ValueError(
            f"Invalid slug: {slug!r}. Use lowercase letters, digits and hyphens "
            "only (max 64 chars), e.g. 'boss-battle-theme'."
        )
    if slug in _RESERVED_NAMES:
        raise ValueError(f"Invalid slug: {slug!r} is a reserved Windows device name.")
    return slug


def relative_artifact_path(value: str, field: str = "path") -> str:
    """Validate an artifact path recorded in a manifest.

    Manifest paths are always relative to the asset's output directory, in
    POSIX form. Absolute paths, drive letters and '..' segments are rejected so
    a manifest can never point a later stage outside that directory.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string, got {value!r}")
    normalized = value.replace("\\", "/").strip()
    parts = pathlib.PurePosixPath(normalized).parts
    if (
        pathlib.PureWindowsPath(normalized).is_absolute()
        or normalized.startswith("/")
        or ".." in parts
    ):
        raise ValueError(
            f"{field} must be a relative path inside the asset directory "
            f"(no drive letter, no leading '/', no '..'): {value!r}"
        )
    return normalized


# A file-name stem supplied on the command line becomes part of a path, so it is
# validated at the trust boundary exactly like a slug is.
_NAME_STEM_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def validate_name_stem(value: str, field: str = "name") -> str:
    """Validate a bare file-name stem (no separators, no extension, no '..').

    Callers build output paths from this, so anything that could climb out of
    the intended directory has to be rejected before it reaches the filesystem.
    """
    if not isinstance(value, str) or not _NAME_STEM_RE.match(value):
        raise ValueError(
            f"{field} must be a bare file name stem: letters, digits, '-' and '_' "
            f"only, starting with a letter or digit (max 64 chars). Got {value!r}."
        )
    if value.lower() in _RESERVED_NAMES:
        raise ValueError(f"{field} must not be a reserved Windows device name: {value!r}")
    return value


def assert_inside(path: pathlib.Path, directory: pathlib.Path, field: str = "path") -> pathlib.Path:
    """Assert `path` resolves to a direct child of `directory`."""
    resolved = pathlib.Path(path).resolve()
    if resolved.parent != pathlib.Path(directory).resolve():
        raise ValueError(
            f"{field} must live directly inside {pathlib.Path(directory).as_posix()}, "
            f"got {resolved.as_posix()}"
        )
    return resolved


def is_dry_run() -> bool:
    return os.environ.get("AUDIO_PIPELINE_DRY_RUN", "").strip().lower() in {"1", "true", "yes"}


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
    return pathlib.Path(root) if root else None


def output_dir(slug: str, base: pathlib.Path | None = None) -> pathlib.Path:
    validate_slug(slug)
    root = pathlib.Path(base) if base is not None else repo_root() or pathlib.Path.cwd()
    path = root / OUTPUT_ROOT / slug
    path.mkdir(parents=True, exist_ok=True)
    return path


def stage_dir(slug: str, stage: str, base: pathlib.Path | None = None) -> pathlib.Path:
    if stage not in STAGE_DIRS:
        raise ValueError(f"Unknown stage directory: {stage}; expected one of {list(STAGE_DIRS)}")
    path = output_dir(slug, base) / stage
    path.mkdir(parents=True, exist_ok=True)
    return path


def data_dir() -> pathlib.Path:
    """Plugin-private data: venvs, setup state, and the optional .env.

    Kept in the user's home directory so nothing generated here can ever be
    committed to a repository.
    """
    return pathlib.Path.home() / ".claude" / "audio-pipeline"


def env_file() -> pathlib.Path:
    """The plugin's private .env (e.g. HF_TOKEN). Lives outside any repository."""
    return data_dir() / ".env"


def load_env_file() -> dict[str, str]:
    """Parse simple KEY=VALUE lines from the private .env.

    Blank lines, '#' comments and a leading 'export ' are ignored; surrounding
    quotes are stripped. The values are secrets - never log them, never write
    them into a manifest, never include them in an error message.
    """
    path = env_file()
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def subprocess_env() -> dict[str, str]:
    """The current environment plus any private .env keys it does not already set.

    A real environment variable always wins, so a user can override the file for
    one run without editing it.
    """
    merged = dict(os.environ)
    for key, value in load_env_file().items():
        if value and key not in merged:
            merged[key] = value
    return merged


def stack_data_dir(stack: str) -> pathlib.Path:
    """Per-stack private working directory for model weights and caches.

    Kept out of any repository and out of the venv. ACE-Step in particular
    resolves its checkpoint tree from the CURRENT WORKING DIRECTORY unless it is
    told otherwise, and the working directory is the user's game project - one
    unguarded call would drop ~11 GB of weights into it. Every caller that can
    trigger that (the backend worker, the doctor's import probe) points the
    stack's environment variables here, so they all agree on one location.
    """
    if stack not in STACKS:
        raise ValueError(f"Unknown stack: {stack}; expected one of {list(STACKS)}")
    return data_dir() / stack


def venv_dir(stack: str) -> pathlib.Path:
    if stack not in STACKS:
        raise ValueError(f"Unknown stack: {stack}; expected one of {list(STACKS)}")
    return data_dir() / "venvs" / stack


def venv_python(stack: str) -> pathlib.Path:
    base = venv_dir(stack)
    return base / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


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


def read_json(path: pathlib.Path | str, default: Any = None) -> Any:
    target = pathlib.Path(path)
    if not target.exists():
        return default
    try:
        with target.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Corrupt JSON file: {target} ({exc})") from exc


def atomic_write_json(path: pathlib.Path | str, obj: Any) -> None:
    target = pathlib.Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Unique staging name: a shared "<name>.tmp" lets two processes clobber each
    # other mid-write. ponytail: no file locking - the pipeline is single-user
    # and sequential; add a lock file if concurrent writers ever become real.
    handle_fd, tmp_name = tempfile.mkstemp(dir=str(target.parent), prefix=f"{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle_fd, "w", encoding="utf-8") as handle:
            json.dump(obj, handle, indent=2, sort_keys=False, ensure_ascii=False)
            handle.write("\n")
        os.replace(tmp_name, target)
    except BaseException:
        pathlib.Path(tmp_name).unlink(missing_ok=True)
        raise


def _tail(raw: Any) -> str:
    """Last _TAIL_CHARS of captured output; subprocess may hand back bytes."""
    if raw is None:
        return ""
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
    return text.strip()[-_TAIL_CHARS:]


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run(
    cmd: Sequence[Any],
    *,
    cwd: pathlib.Path | str | None = None,
    timeout: float = 1800.0,
    check: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Run a command, returning a CompletedProcess even when the binary is absent.

    A missing executable yields returncode 127 (POSIX convention) instead of an
    exception, so probe-style callers can treat "not installed" as data. With
    check=True a non-zero exit raises RuntimeError carrying the command and the
    tail of stderr, which is what a user needs in order to act.
    """
    argv = [str(part) for part in cmd]
    try:
        result = subprocess.run(
            argv,
            cwd=str(cwd) if cwd is not None else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except FileNotFoundError:
        result = subprocess.CompletedProcess(argv, 127, "", f"executable not found: {argv[0]}")
    except subprocess.TimeoutExpired as exc:
        # Keep whatever was captured before the timeout; it usually says where it hung.
        stderr = f"timed out after {exc.timeout}s"
        captured = _tail(exc.stderr)
        if captured:
            stderr = f"{stderr}\n{captured}"
        result = subprocess.CompletedProcess(argv, EXIT_TIMEOUT, _tail(exc.stdout), stderr)
    except OSError as exc:
        result = subprocess.CompletedProcess(argv, 126, "", f"could not start: {exc}")

    if check and result.returncode != 0:
        # pip/uv failures put the actionable line at the end of the output.
        tail = _tail(result.stderr) or _tail(result.stdout)
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(argv)}\n{tail}")
    return result
