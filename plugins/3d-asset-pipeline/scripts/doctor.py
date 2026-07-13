"""3d-asset-pipeline health checker.

Verifies the Python version, required packages, credentials file and keys,
git availability, and (with --network) reachability of the OpenAI, Replicate,
and Meshy endpoints. Also checks whether the local TRELLIS.2 mesh backend
(trellis2-stableprojectorz, `--vendor local`) is reachable; that check is
informational only, since local mesh generation is optional. When the local
backend is reachable, a missing `REPLICATE_API_TOKEN` is downgraded from a
required-key failure to a warning, since Stage 2 can still run locally.
Similarly, checks whether the Codex CLI concept-art backend (Stage 1,
`concept_openai.py --backend codex`) is usable, i.e. the codex CLI is on
PATH and logged in with an active ChatGPT subscription; when it is, a
missing `OPENAI_API_KEY` is downgraded from a required-key failure to a
warning, since Stage 1 can still run via the Codex CLI.
"""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from typing import Any

try:
    from . import _codex_backend, _common, _credentials, _local_backend
except ImportError:
    import _codex_backend  # type: ignore
    import _common  # type: ignore
    import _credentials  # type: ignore
    import _local_backend  # type: ignore


Check = tuple[str, str, str]
# Required for stages 1, 2, 5, 6 (concept -> mesh -> import -> review).
# REPLICATE_API_TOKEN is only truly required when the local TRELLIS.2 backend
# is not reachable; see check_credentials().
REQUIRED_KEYS = ("OPENAI_API_KEY", "REPLICATE_API_TOKEN")
# Optional: enables stages 3 and 4 (auto-rig, auto-animation). Without these,
# humanoid/quadruped runs must fall back to prop mode (rig and animate skipped).
OPTIONAL_KEYS = ("MESHY_API_KEY", "TRIPO_API_KEY")
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


def check_local_backend(checks: list[Check]) -> bool:
    """Check the local TRELLIS.2 mesh backend (--vendor local). Never fails.

    Returns True when the backend answered GET /ping, so callers can relax
    the REPLICATE_API_TOKEN requirement accordingly.
    """
    configured = bool(_credentials.optional("TRELLIS2_SPZ_URL")) or bool(
        _credentials.optional("TRELLIS2_SPZ_HOME")
    )
    base_url = _local_backend.resolve_url(None)
    try:
        _local_backend.ping(base_url, timeout=3.0)
    except _local_backend.BackendUnreachable:
        if configured:
            _add(
                checks,
                "Local mesh backend (TRELLIS.2)",
                "warn",
                f"configured but unreachable at {base_url}; start the server "
                "or check TRELLIS2_SPZ_HOME for auto-start",
            )
        else:
            _add(
                checks,
                "Local mesh backend (TRELLIS.2)",
                "warn",
                "local mesh vendor not configured; optional",
            )
        return False

    _add(checks, "Local mesh backend (TRELLIS.2)", "ok", f"reachable at {base_url}")
    return True


def check_codex_backend(checks: list[Check]) -> bool:
    """Check the Codex CLI concept-art backend (Stage 1, `--backend codex`). Never fails.

    Returns True when the codex CLI is present and logged in with an active
    ChatGPT subscription, so callers can relax the OPENAI_API_KEY requirement
    accordingly. Also reports which backend `resolve_backend(None)` (i.e.
    "auto", honoring PIPELINE_CONCEPT_BACKEND) would actually pick, since that
    is the decision concept_openai.py makes by default.
    """
    codex_path = _codex_backend.find_codex()
    if codex_path is None:
        _add(checks, "Codex CLI concept backend", "warn", "codex CLI not found on PATH; optional")
        usable = False
    else:
        active, detail = _codex_backend.subscription_status()
        if active:
            _add(checks, "Codex CLI concept backend", "ok", f"{codex_path}; {detail}")
            usable = True
        else:
            _add(
                checks,
                "Codex CLI concept backend",
                "warn",
                f"found at {codex_path} but no active ChatGPT subscription: {detail}",
            )
            usable = False

    try:
        decision, decision_detail = _codex_backend.resolve_backend(None)
    except ValueError as exc:
        _add(checks, "Concept backend auto-selection", "warn", f"PIPELINE_CONCEPT_BACKEND misconfigured: {exc}")
    else:
        _add(checks, "Concept backend auto-selection", "ok", f"would pick '{decision}' ({decision_detail})")

    return usable


def check_credentials(checks: list[Check], local_backend_reachable: bool, codex_backend_usable: bool) -> None:
    path = _credentials.env_path()
    if path.exists():
        _add(checks, "Credentials file", "ok", str(path))
    else:
        _add(checks, "Credentials file", "fail", f"missing at {path}")

    key_status = _credentials.status()
    for key in REQUIRED_KEYS:
        if key_status.get(key):
            _add(checks, f"Credential {key}", "ok", "present")
        elif key == "REPLICATE_API_TOKEN" and local_backend_reachable:
            _add(checks, f"Credential {key}", "warn", "missing; local mesh vendor available for Stage 2")
        elif key == "OPENAI_API_KEY" and codex_backend_usable:
            _add(checks, f"Credential {key}", "warn", "missing; Codex subscription backend available for Stage 1")
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
    local_backend_reachable = check_local_backend(checks)
    codex_backend_usable = check_codex_backend(checks)
    check_credentials(checks, local_backend_reachable, codex_backend_usable)
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
