from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from typing import Any

try:
    from . import _common, _credentials
except ImportError:
    import _common  # type: ignore
    import _credentials  # type: ignore


Check = tuple[str, str, str]
REQUIRED_KEYS = ("OPENAI_API_KEY", "REPLICATE_API_TOKEN", "MESHY_API_KEY")
OPTIONAL_KEYS = ("TRIPO_API_KEY",)
NETWORK_TARGETS = (
    ("OpenAI", "https://api.openai.com/v1/models"),
    ("Replicate", "https://api.replicate.com/v1/models"),
    ("Meshy", "https://api.meshy.ai"),
)


def _add(checks: list[Check], name: str, status: str, detail: str) -> None:
    checks.append((name, status, detail))


def check_python(checks: list[Check]) -> None:
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 10):
        _add(checks, "Python version", "ok", version)
    else:
        _add(checks, "Python version", "fail", f"{version}; Python 3.10+ is required")


def check_packages(checks: list[Check]) -> None:
    packages = (
        ("requests", "requests"),
        ("dotenv", "dotenv"),
        ("PIL", "PIL"),
        ("replicate", "replicate"),
        ("openai", "openai"),
    )
    for display, module in packages:
        try:
            importlib.import_module(module)
        except ImportError:
            _add(checks, f"Package {display}", "fail", "missing")
        else:
            _add(checks, f"Package {display}", "ok", "installed")


def check_credentials(checks: list[Check]) -> None:
    path = _credentials.env_path()
    if path.exists():
        _add(checks, "Credentials file", "ok", str(path))
    else:
        _add(checks, "Credentials file", "fail", f"missing at {path}")

    key_status = _credentials.status()
    for key in REQUIRED_KEYS:
        if key_status.get(key):
            _add(checks, f"Credential {key}", "ok", "present")
        else:
            _add(checks, f"Credential {key}", "fail", "missing")
    for key in OPTIONAL_KEYS:
        if key_status.get(key):
            _add(checks, f"Credential {key}", "ok", "present")
        else:
            _add(checks, f"Credential {key}", "warn", "missing optional key")


def check_git(checks: list[Check]) -> None:
    try:
        result = subprocess.run(
            ["git", "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, OSError) as exc:
        _add(checks, "Git availability", "fail", str(exc))
    else:
        _add(checks, "Git availability", "ok", result.stdout.strip())

    root = _common.repo_root()
    if root is None:
        _add(checks, "Repo detection", "warn", "not currently inside a Git repository")
    else:
        _add(checks, "Repo detection", "ok", str(root))


def check_public_repo_reminder(checks: list[Check]) -> None:
    _add(checks, "Public repo reminder", "info", "Keep API keys outside the repository.")


def _has_failures(checks: list[Check]) -> bool:
    return any(status == "fail" for _, status, _ in checks)


def check_network(checks: list[Check]) -> None:
    try:
        requests = importlib.import_module("requests")
    except ImportError:
        _add(checks, "Network checks", "fail", "requests package is missing")
        return

    for name, url in NETWORK_TARGETS:
        try:
            response = requests.head(url, timeout=5.0, allow_redirects=True)
        except requests.RequestException as exc:  # type: ignore[attr-defined]
            _add(checks, f"Network {name}", "fail", f"connection error: {exc.__class__.__name__}")
            continue

        code = response.status_code
        if 200 <= code < 400 or code == 401:
            _add(checks, f"Network {name}", "ok", f"reachable: HTTP {code}")
        elif 400 <= code < 500:
            _add(checks, f"Network {name}", "warn", f"reachable with HTTP {code}")
        else:
            _add(checks, f"Network {name}", "fail", f"HTTP {code}")


def run_checks(include_network: bool) -> list[Check]:
    checks: list[Check] = []
    check_python(checks)
    check_packages(checks)
    check_credentials(checks)
    check_git(checks)
    check_public_repo_reminder(checks)
    if include_network:
        if _has_failures(checks):
            _add(checks, "Network checks", "info", "skipped because earlier checks failed")
        else:
            check_network(checks)
    return checks


def summarize(checks: list[Check]) -> dict[str, int]:
    return {
        "ok": sum(1 for _, status, _ in checks if status == "ok"),
        "warn": sum(1 for _, status, _ in checks if status == "warn"),
        "fail": sum(1 for _, status, _ in checks if status == "fail"),
    }


def print_text(checks: list[Check]) -> None:
    for name, status, detail in checks:
        print(f"[{status.upper()}] {name}: {detail}")
    summary = summarize(checks)
    print(f"Doctor: {summary['ok']} ok, {summary['warn']} warn, {summary['fail']} fail")


def print_json(checks: list[Check]) -> None:
    summary = summarize(checks)
    payload: dict[str, Any] = {
        "checks": [{"name": name, "status": status, "detail": detail} for name, status, detail in checks],
        "summary": summary,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="3d-pipeline health checker")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--network", action="store_true", help="include network reachability checks")
    args = parser.parse_args(argv)

    checks = run_checks(args.network)
    if args.json:
        print_json(checks)
    else:
        print_text(checks)

    return _common.EXIT_USER_ERROR if _has_failures(checks) else _common.EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
