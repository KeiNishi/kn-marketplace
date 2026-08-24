"""audio-asset-pipeline health checker.

Verifies the driver Python, `uv`, ffmpeg, the CUDA GPU, the per-stack virtual
environments created by setup_env.py, and free disk space for model weights.
Exits non-zero when a hard requirement is missing; warnings never fail the run.

Usage:
    python doctor.py
    python doctor.py --stack sa3
    python doctor.py --json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys
from typing import Any

try:
    from . import _common, setup_env
except ImportError:  # executed as a script, not as a package module
    import _common  # type: ignore
    import setup_env  # type: ignore


Check = tuple[str, str, str]
MIN_PYTHON = (3, 10)  # the pipeline scripts themselves; stack venvs use 3.11/3.12
# Below this the 12 GB-tuned offloading configs no longer fit. A nominally
# "12 GB" card reports ~12282 MiB (11.99 GiB), so the threshold sits at 11.5 GiB.
MIN_VRAM_GB = 11.5
DISK_WARN_GB = setup_env.DISK_WARN_GB
# Run inside a stack venv: exit 1 when torch has no CUDA, else print the device.
_CUDA_PROBE = (
    "import sys, torch\n"
    "if not torch.cuda.is_available():\n"
    "    sys.exit(1)\n"
    "p = torch.cuda.get_device_properties(0)\n"
    "print('%s, %.1f GB VRAM' % (p.name, p.total_memory / (1024 ** 3)))\n"
)


def _add(checks: list[Check], name: str, status: str, detail: str) -> None:
    checks.append((name, status, detail))


def check_python(checks: list[Check]) -> None:
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= MIN_PYTHON:
        _add(checks, "Python version", "ok", version)
    else:
        wanted = ".".join(str(part) for part in MIN_PYTHON)
        _add(checks, "Python version", "fail", f"{version}; Python {wanted}+ is required")


def check_uv(checks: list[Check]) -> None:
    uv = setup_env.find_uv()
    if uv is None:
        _add(
            checks,
            "uv",
            "warn",
            "not on PATH; setup_env.py falls back to the py launcher and pip (slower)",
        )
        return
    result = _common.run([uv, "--version"], timeout=30)
    if result.returncode != 0:
        _add(checks, "uv", "warn", f"{uv} is not runnable: {result.stderr.strip()[-300:]}")
        return
    _add(checks, "uv", "ok", result.stdout.strip() or uv)


def check_ffmpeg(checks: list[Check]) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        _add(
            checks,
            "ffmpeg",
            "fail",
            "not on PATH; loop trimming, LUFS normalization and OGG export need it "
            "(winget install Gyan.FFmpeg, or apt/brew install ffmpeg)",
        )
        return
    result = _common.run([ffmpeg, "-version"], timeout=30)
    if result.returncode != 0:
        _add(
            checks,
            "ffmpeg",
            "fail",
            f"{ffmpeg} is on PATH but not runnable: {result.stderr.strip()[-300:]}",
        )
        return
    first_line = (result.stdout or result.stderr).splitlines()[:1]
    _add(checks, "ffmpeg", "ok", first_line[0] if first_line else ffmpeg)


def check_gpu(checks: list[Check]) -> None:
    smi = shutil.which("nvidia-smi")
    if smi is None:
        _add(
            checks,
            "NVIDIA GPU",
            "warn",
            "nvidia-smi not found; local generation needs a CUDA GPU (CPU inference "
            "is too slow to be usable)",
        )
        return

    result = _common.run(
        [smi, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
        timeout=60,
    )
    if result.returncode != 0:
        _add(checks, "NVIDIA GPU", "warn", f"nvidia-smi failed: {result.stderr.strip()[:200]}")
        return

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        _add(checks, "NVIDIA GPU", "warn", "nvidia-smi reported no GPUs")
        return

    for line in lines:
        name, _, memory = line.partition(",")
        try:
            vram_gb = int(memory.strip()) / 1024
        except ValueError:
            _add(checks, "NVIDIA GPU", "warn", f"unparsable nvidia-smi output: {line}")
            continue
        detail = f"{name.strip()}, {vram_gb:.1f} GB VRAM"
        if vram_gb < MIN_VRAM_GB:
            _add(checks, "NVIDIA GPU", "warn", f"{detail}; under 12 GB, expect OOM")
        else:
            _add(checks, "NVIDIA GPU", "ok", detail)


def check_stack(checks: list[Check], stack: str) -> bool:
    """Check one generation stack. Returns True when it looks usable."""
    spec = setup_env.STACKS[stack]
    label = f"Stack {stack} ({spec['label']})"
    python = _common.venv_python(stack)
    if not python.exists():
        _add(checks, label, "warn", f"venv missing; run setup_env.py --stack {stack}")
        return False

    # Some stacks resolve cache and checkpoint directories from the working
    # directory the moment their package is touched. The registry says where
    # those belong; without it a health check could write gigabytes into
    # whatever project the user happened to run doctor from.
    probe_env = spec.get("probe_env")
    env = {**_common.subprocess_env(), **probe_env} if probe_env else None

    missing = []
    for module in spec["imports"]:
        result = _common.run([python, "-c", f"import {module}"], timeout=180, env=env)
        if result.returncode != 0:
            missing.append(module)
    if missing:
        _add(
            checks,
            label,
            "warn",
            f"venv present but cannot import {', '.join(missing)}; "
            f"re-run setup_env.py --stack {stack}",
        )
        return False

    if "torch" in spec["imports"]:
        # An import check alone passes on a CPU-only torch, which would make the
        # stack look healthy and then generate at unusable speeds.
        cuda = _common.run([python, "-c", _CUDA_PROBE], timeout=300, env=env)
        if cuda.returncode != 0:
            detail = cuda.stderr.strip()[-300:]
            _add(
                checks,
                label,
                "warn",
                "CPU-only torch (torch.cuda.is_available() is False); re-run "
                f"setup_env.py --stack {stack}" + (f": {detail}" if detail else ""),
            )
            return False
        _add(checks, label, "ok", f"{python.as_posix()}; CUDA {cuda.stdout.strip()}")
        return True

    _add(checks, label, "ok", f"{python.as_posix()} ({', '.join(spec['imports'])} import cleanly)")
    return True


def check_disk(checks: list[Check]) -> None:
    data = _common.data_dir()
    probe = data if data.exists() else pathlib.Path.home()
    free_gb = shutil.disk_usage(probe).free / (1024**3)
    detail = f"{free_gb:.1f} GB free on {probe.anchor or probe}"
    if free_gb < DISK_WARN_GB:
        _add(checks, "Disk space", "warn", f"{detail}; model weights need roughly 30 GB")
    else:
        _add(checks, "Disk space", "ok", detail)


def check_data_dir(checks: list[Check]) -> None:
    data = _common.data_dir()
    status = "ok" if data.exists() else "warn"
    detail = data.as_posix() if data.exists() else f"{data.as_posix()} (not created yet)"
    _add(checks, "Data directory", status, detail)
    _add(
        checks,
        "Dry run",
        "info",
        "AUDIO_PIPELINE_DRY_RUN=1 (no generation will run)"
        if _common.is_dry_run()
        else "off",
    )


def run_checks(stacks: list[str]) -> list[Check]:
    checks: list[Check] = []
    check_python(checks)
    check_uv(checks)
    check_ffmpeg(checks)
    check_gpu(checks)
    usable = [stack for stack in stacks if check_stack(checks, stack)]
    if not usable:
        _add(
            checks,
            "Generation stacks",
            "fail",
            f"none of {', '.join(stacks)} is usable; run setup_env.py first",
        )
    else:
        _add(checks, "Generation stacks", "ok", f"usable: {', '.join(usable)}")
    check_disk(checks)
    check_data_dir(checks)
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
    payload: dict[str, Any] = {
        "checks": [{"name": name, "status": status, "detail": detail} for name, status, detail in checks],
        "summary": summarize(checks),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="audio-asset-pipeline health checker")
    parser.add_argument(
        "--stack",
        choices=(*setup_env.STACKS, "all"),
        default="all",
        help="limit the stack checks (default: all)",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    stacks = list(setup_env.STACKS) if args.stack == "all" else [args.stack]
    checks = run_checks(stacks)
    if args.json:
        print_json(checks)
    else:
        print_text(checks)

    failed = any(status == "fail" for _, status, _ in checks)
    return _common.EXIT_USER_ERROR if failed else _common.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
