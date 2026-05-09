from __future__ import annotations

import pathlib


KNOWN_KEYS = ("OPENAI_API_KEY", "REPLICATE_API_TOKEN", "MESHY_API_KEY", "TRIPO_API_KEY")
MISSING_FILE_MESSAGE = (
    "3d-pipeline credentials file not found. Create "
    "%USERPROFILE%\\.claude\\3d-pipeline\\.env "
    "(or ~/.claude/3d-pipeline/.env on POSIX) with OPENAI_API_KEY, "
    "REPLICATE_API_TOKEN, and MESHY_API_KEY."
)


def env_path() -> pathlib.Path:
    return pathlib.Path.home() / ".claude" / "3d-pipeline" / ".env"


def _clean(value: object) -> str:
    if value is None:
        return ""
    cleaned = str(value).strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        cleaned = cleaned[1:-1].strip()
    return cleaned


def load() -> dict[str, str]:
    path = env_path()
    if not path.exists():
        raise FileNotFoundError(MISSING_FILE_MESSAGE)

    import dotenv

    values = dotenv.dotenv_values(env_path())
    present: dict[str, str] = {}
    for key in KNOWN_KEYS:
        value = _clean(values.get(key))
        if value:
            present[key] = value
    return present


def require(*names: str) -> dict[str, str]:
    values = load()
    missing = [name for name in names if not values.get(name)]
    if missing:
        raise ValueError(f"Missing required credentials: {', '.join(missing)}")
    return {name: values[name] for name in names}


def status() -> dict[str, bool]:
    try:
        values = load()
    except (FileNotFoundError, ImportError):
        values = {}
    return {key: bool(values.get(key)) for key in KNOWN_KEYS}
