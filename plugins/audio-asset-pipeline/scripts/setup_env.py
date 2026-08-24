"""Create the local generation environments for the audio asset pipeline.

Each generation stack gets its own virtual environment under
`~/.claude/audio-pipeline/venvs/<stack>` because the three projects pin
incompatible torch / transformers versions. Model weights are NOT downloaded
here; every backend pulls them into the Hugging Face cache on first use.

Usage:
    python setup_env.py --stack all
    python setup_env.py --stack sa3
    python setup_env.py --check-only

Set AUDIO_PIPELINE_DRY_RUN=1 to print the planned actions without touching
anything. (On Windows, use `py -3` if `python3` is not available.)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import sys
from typing import Any

try:
    from . import _common
except ImportError:  # executed as a script, not as a package module
    import _common  # type: ignore


LOGGER = _common.setup_logger("audio-setup")
STATE_VERSION = 1
# Weights for all three stacks land in the Hugging Face cache, not in the venvs.
DISK_WARN_GB = 40  # ~30 GB of weights plus ~8 GB of venvs, with headroom

# The three project installers resolve a CPU-only torch wheel on Windows, which
# silently produces unusable (CPU) generation. Force the CUDA 12.8 build after
# the project install so it wins.
_TORCH_CU128: dict[str, Any] = {
    "id": "torch-cu128",
    "kind": "pip",
    "args": [
        "--force-reinstall",
        "torch==2.7.1+cu128",
        "torchaudio==2.7.1+cu128",
        "--index-url",
        "https://download.pytorch.org/whl/cu128",
    ],
    "label": "CUDA 12.8 torch/torchaudio (overrides the CPU wheel the projects resolve)",
}

# stable-audio-3 main @ 2026-08-24, verified to expose
# `stable_audio_3.StableAudioModel.from_pretrained(...)` / `.generate(...)`.
_SA3_COMMIT = "a0b57f5483c4588f827f3552b7d5c6ca2a9687be"

STACKS: dict[str, dict[str, Any]] = {
    "sa3": {
        "label": "Stable Audio 3",
        # 3.12 preferred, 3.11 accepted; the projects do not support 3.13 yet.
        "pythons": ("3.12", "3.11"),
        # `stable_audio_3` is the package the `stable-audio-3` distribution
        # installs; importing it is what proves the install actually works.
        "imports": ("stable_audio_3", "torch", "soundfile"),
        "steps": (
            {
                "id": "project",
                "kind": "pip",
                # Pinned: stable-audio-3 has no releases and no tags, so an
                # unpinned git install silently changes the model API under a
                # user who re-runs setup months later. Bump this deliberately.
                "args": [f"git+https://github.com/Stability-AI/stable-audio-3@{_SA3_COMMIT}"],
                "label": f"stable-audio-3 from GitHub @ {_SA3_COMMIT[:7]}",
            },
            _TORCH_CU128,
            {
                "id": "soundfile",
                "kind": "pip",
                "args": ["soundfile"],
                "label": "soundfile (torchaudio ships no audio backend on Windows)",
            },
            {
                "id": "hf-auth",
                "kind": "manual",
                "label": "Hugging Face access to the gated Stable Audio 3 weights",
                "note": (
                    "The stabilityai/stable-audio-3-* repositories are gated, so the "
                    "first generation fails with a 401 GatedRepoError until access is "
                    "granted. Accept the license at "
                    "https://huggingface.co/stabilityai/stable-audio-3-small-sfx while "
                    "signed in, then authenticate locally with a read token: put "
                    "HF_TOKEN=<token> in ~/.claude/audio-pipeline/.env (the driver "
                    "passes it to the backend), export HF_TOKEN, or run 'hf auth login' "
                    "using the 'hf' CLI next to {venv_python}. Note 'huggingface-cli' "
                    "was removed in huggingface_hub 1.x; the command is 'hf' now."
                ),
            },
            {
                "id": "flash-attn",
                "kind": "manual",
                "label": "flash-attn (cu128) - required only by the 'medium' model",
                "note": (
                    "No prebuilt flash-attn cu128 wheel is published for Windows; "
                    "building from source needs the MSVC toolchain. The 'small' model "
                    "runs without it. Install a matching wheel into "
                    "{venv_python} before using the 'medium' model."
                ),
            },
        ),
    },
    "acestep": {
        "label": "ACE-Step 1.5",
        "pythons": ("3.12", "3.11"),
        "imports": ("torch",),
        "steps": (
            {
                "id": "project",
                "kind": "pip",
                "args": ["git+https://github.com/ace-step/ACE-Step-1.5"],
                "label": "ACE-Step-1.5 from GitHub (PyTorch backend; vLLM is not available on Windows)",
            },
            _TORCH_CU128,
        ),
    },
    "minimax": {
        "label": "MiniMax-Music3",
        "pythons": ("3.12", "3.11"),
        "imports": ("torch", "diffusers"),
        "steps": (
            _TORCH_CU128,
            {
                "id": "diffusers",
                "kind": "pip",
                # Group offloading in diffusers is what keeps this model inside
                # 12 GB of VRAM. Exact pins are settled when the backend lands.
                "args": ["diffusers", "transformers", "accelerate"],
                "label": "diffusers stack (group offloading for 12 GB cards)",
            },
        ),
    },
}

# _common owns the stack names; this registry only adds the install recipes.
assert tuple(STACKS) == _common.STACKS, (
    f"Stack registries drifted: setup_env.STACKS={tuple(STACKS)} vs "
    f"_common.STACKS={_common.STACKS}. Keep _common.STACKS as the source of truth."
)


# --------------------------------------------------------------------------
# state
# --------------------------------------------------------------------------


def state_path() -> pathlib.Path:
    return _common.data_dir() / "setup-state.json"


def load_state() -> dict[str, Any]:
    state = _common.read_json(state_path(), default={"version": STATE_VERSION, "stacks": {}})
    if not isinstance(state, dict) or not isinstance(state.get("stacks"), dict):
        raise ValueError(
            f"Unusable setup state at {state_path()}. Delete the file and re-run setup_env.py."
        )
    if state.get("version") != STATE_VERSION:
        raise ValueError(
            f"setup state at {state_path()} was written by version {state.get('version')!r}, "
            f"this script writes version {STATE_VERSION}. Delete the file and re-run "
            "setup_env.py (the venvs themselves are re-checked, not rebuilt from scratch)."
        )
    return state


def step_hash(step: dict[str, Any]) -> str:
    """Fingerprint of a step spec, so an edited recipe re-runs instead of being skipped."""
    payload = json.dumps(step, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def step_is_current(done: dict[str, Any], step: dict[str, Any]) -> bool:
    entry = done.get(step["id"])
    return isinstance(entry, dict) and entry.get("hash") == step_hash(step)


def record_step(
    stack: str,
    step_id: str,
    fingerprint: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    state = load_state()
    entry = state["stacks"].setdefault(stack, {"steps": {}})
    entry.setdefault("steps", {})[step_id] = {"at": _common.iso_now(), "hash": fingerprint}
    entry.update(extra or {})
    _common.atomic_write_json(state_path(), state)


def completed_steps(stack: str) -> dict[str, Any]:
    return load_state()["stacks"].get(stack, {}).get("steps", {})


# --------------------------------------------------------------------------
# environment creation
# --------------------------------------------------------------------------


def find_uv() -> str | None:
    return shutil.which("uv")


def _base_python(version: str) -> str | None:
    """Locate an interpreter for `version` without uv (py launcher on Windows)."""
    probe = ["py", f"-{version}"] if os.name == "nt" else [f"python{version}"]
    result = _common.run([*probe, "-c", "import sys; print(sys.executable)"], timeout=60)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def create_venv(stack: str, dry_run: bool) -> None:
    spec = STACKS[stack]
    target = _common.venv_dir(stack)
    if _common.venv_python(stack).exists():
        LOGGER.info("%s: venv already present at %s", stack, target)
        return

    uv = find_uv()
    for version in spec["pythons"]:
        if uv:
            # uv downloads a matching interpreter when the system lacks one.
            cmd = [uv, "venv", "--python", version, str(target)]
        else:
            base = _base_python(version)
            if base is None:
                continue
            cmd = [base, "-m", "venv", str(target)]

        if dry_run:
            LOGGER.info("[dry-run] %s: would create venv: %s", stack, " ".join(cmd))
            return
        result = _common.run(cmd, timeout=900)
        if result.returncode == 0:
            record_step(stack, "venv", extra={"python": version, "createdAt": _common.iso_now()})
            LOGGER.info("%s: created venv (Python %s) at %s", stack, version, target)
            return
        LOGGER.warning("%s: Python %s venv creation failed: %s", stack, version, result.stderr.strip()[-500:])

    raise RuntimeError(
        f"{stack}: could not create a virtual environment. Install Python "
        f"{' or '.join(spec['pythons'])} (or install 'uv', which can fetch it "
        "automatically) and re-run setup_env.py."
    )


def pip_install(stack: str, args: list[str], dry_run: bool) -> None:
    python = _common.venv_python(stack)
    uv = find_uv()
    if uv:
        cmd = [uv, "pip", "install", "--python", str(python), *args]
    else:
        cmd = [str(python), "-m", "pip", "install", *args]

    if dry_run:
        LOGGER.info("[dry-run] %s: would run: %s", stack, " ".join(cmd))
        return
    _common.run(cmd, timeout=3600, check=True)


def setup_stack(stack: str, dry_run: bool) -> None:
    spec = STACKS[stack]
    LOGGER.info("=== %s (%s) ===", stack, spec["label"])
    create_venv(stack, dry_run)

    done = {} if dry_run else completed_steps(stack)
    for step in spec["steps"]:
        step_id = step["id"]
        if step_is_current(done, step):
            LOGGER.info(
                "%s: step '%s' already done (%s); skipping",
                stack,
                step_id,
                done[step_id].get("at", "unknown time"),
            )
            continue
        if step_id in done:
            LOGGER.info("%s: step '%s' changed since it was installed; re-running", stack, step_id)

        if step["kind"] == "manual":
            note = step["note"].format(venv_python=_common.venv_python(stack).as_posix())
            LOGGER.warning("%s: manual step '%s' - %s", stack, step_id, step["label"])
            LOGGER.warning("%s: %s", stack, note)
            continue

        LOGGER.info("%s: installing %s", stack, step["label"])
        pip_install(stack, list(step["args"]), dry_run)
        if not dry_run:
            record_step(stack, step_id, step_hash(step))


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------


def print_notes() -> None:
    data = _common.data_dir()
    print(f"Data directory : {data.as_posix()}")
    print(f"Setup state    : {state_path().as_posix()}")
    hf_home = os.environ.get("HF_HOME")
    if hf_home:
        print(f"HF_HOME        : {hf_home}")
    else:
        print(
            "HF_HOME        : not set; weights go to the default Hugging Face cache "
            "(~/.cache/huggingface). Set HF_HOME to a drive with room to spare - "
            "never to a path inside a git repository."
        )
    probe = data if data.exists() else pathlib.Path.home()
    free_gb = shutil.disk_usage(probe).free / (1024**3)
    line = f"Free disk space: {free_gb:.1f} GB on {probe.anchor or probe}"
    if free_gb < DISK_WARN_GB:
        line += f" - WARNING: model weights need roughly 30 GB, {DISK_WARN_GB} GB recommended"
    print(line)
    if _common.is_dry_run():
        print("Dry run        : AUDIO_PIPELINE_DRY_RUN=1, no changes will be made")
    print("")
    sys.stdout.flush()  # keep this header above the stderr log lines that follow


def print_status(stacks: list[str]) -> None:
    state_stacks = load_state()["stacks"]
    for stack in stacks:
        spec = STACKS[stack]
        python = _common.venv_python(stack)
        done = state_stacks.get(stack, {}).get("steps", {})
        pending = [
            step["id"]
            for step in spec["steps"]
            if step["kind"] == "pip" and not step_is_current(done, step)
        ]
        manual = [step["id"] for step in spec["steps"] if step["kind"] == "manual"]
        status = "ready" if python.exists() and not pending else "incomplete"
        print(f"[{status}] {stack} ({spec['label']})")
        print(f"    venv    : {python.as_posix()} {'(present)' if python.exists() else '(missing)'}")
        print(f"    done    : {', '.join(sorted(done)) or 'none'}")
        print(f"    pending : {', '.join(pending) or 'none'}")
        if manual:
            print(f"    manual  : {', '.join(manual)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create the local generation environments for the audio asset pipeline"
    )
    parser.add_argument(
        "--stack",
        choices=(*STACKS, "all"),
        default="all",
        help="which generation stack to set up (default: all)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="report what is installed without changing anything",
    )
    args = parser.parse_args(argv)

    stacks = list(STACKS) if args.stack == "all" else [args.stack]
    print_notes()

    if args.check_only:
        print_status(stacks)
        return _common.EXIT_OK

    dry_run = _common.is_dry_run()
    failures: list[str] = []
    for stack in stacks:
        try:
            setup_stack(stack, dry_run)
        except (RuntimeError, ValueError, OSError) as exc:
            LOGGER.error("%s: setup failed: %s", stack, exc)
            failures.append(stack)

    if failures:
        LOGGER.error(
            "Setup incomplete for: %s. Fix the errors above and re-run; completed "
            "steps are skipped.",
            ", ".join(failures),
        )
        return _common.EXIT_USER_ERROR

    print("")
    print_status(stacks)
    if not dry_run:
        print("")
        print("Next: python doctor.py")
    return _common.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
