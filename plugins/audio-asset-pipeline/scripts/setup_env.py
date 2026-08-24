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
import functools
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
# Weights do not all land in one place, and the two places are often on
# different drives, so each volume is checked against what really goes on it.
#
#   data directory : the three venvs (~8 GB) plus ACE-Step's own checkpoint tree
#                    (~12 GB), which the library resolves from ACESTEP_* rather
#                    than from the Hugging Face cache.
#   HF hub cache   : Stable Audio 3 (~5 GB) and MiniMax-Music3 (27 GB measured).
#
# Both figures carry a few GB of headroom for the partial downloads that exist
# while a stack is still being fetched.
DATA_DIR_WARN_GB = 24
HF_CACHE_WARN_GB = 36


def disk_targets() -> tuple[tuple[str, pathlib.Path, float, str], ...]:
    """(label, path, needed GB, what lives there) for every volume that matters."""
    return (
        (
            "data directory",
            _common.data_dir(),
            DATA_DIR_WARN_GB,
            "the stack venvs (~8 GB) and ACE-Step's checkpoints (~12 GB)",
        ),
        (
            "Hugging Face cache",
            _common.hf_cache_dir(),
            HF_CACHE_WARN_GB,
            "Stable Audio 3 (~5 GB) and MiniMax-Music3 (27 GB)",
        ),
    )


def disk_report() -> list[tuple[str, bool, str]]:
    """(label, ok, detail) per volume. Volumes that coincide are summed, not double-counted."""
    rows: list[tuple[str, bool, str]] = []
    targets = disk_targets()
    anchors = [_common.free_gb(path)[1].anchor for _, path, _, _ in targets]
    shared = len(set(anchors)) == 1

    if shared:
        needed = sum(need for _, _, need, _ in targets)
        available, probe = _common.free_gb(targets[0][1])
        detail = (
            f"{available:.1f} GB free on {probe.anchor or probe}, which holds both the "
            f"data directory and the Hugging Face cache; all three stacks need about "
            f"{needed:g} GB there"
        )
        return [("Disk space", available >= needed, detail)]

    for label, path, needed, contents in targets:
        available, probe = _common.free_gb(path)
        rows.append(
            (
                f"Disk space ({label})",
                available >= needed,
                f"{available:.1f} GB free on {probe.anchor or probe} for {path.as_posix()}; "
                f"{contents} need about {needed:g} GB",
            )
        )
    return rows

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

# Stable Audio 3's `medium` DiT needs Flash Attention 2, which has no wheels on
# PyPI at all - every install is either a source build or a third-party wheel.
# These are the community prebuilds from mjun0812/flash-attention-prebuild-wheels,
# pinned by release tag and keyed by "<platform tag>-<CPython tag>". Every entry is
# built against exactly the torch 2.7.1 / CUDA 12.8 pair the torch-cu128 step
# installs, so a mismatched wheel imports and then fails inside the kernel - bump
# these together with _TORCH_CU128, never on their own.
#
# Verified 2026-08-25 on Windows / CPython 3.12 / RTX 12 GB: the cp312 win_amd64
# wheel imports, runs flash_attn_func on CUDA, and lets sa3 `medium` render a
# clean 60 s ambient bed. Combinations absent from this table fall back to the
# step's manual note.
#
# Each URL carries a `#sha256=` fragment, which pip and uv treat as a required
# hash: a wheel whose bytes do not match is refused rather than installed. These
# are third-party binaries carrying CUDA kernels, so the pin is what makes them
# safe to fetch unattended - a re-uploaded or tampered asset fails loudly instead
# of landing in the venv. Every hash below was computed from the downloaded file
# on 2026-08-25 and agreed with the digest GitHub reports for the same asset.
_FLASH_ATTN_VERSION = "2.8.3+cu128torch2.7"
_FLASH_ATTN_RELEASES = "https://github.com/mjun0812/flash-attention-prebuild-wheels/releases"
_FLASH_ATTN_WHEELS: dict[str, str] = {
    "win_amd64-cp312": f"{_FLASH_ATTN_RELEASES}/download/v0.7.11/flash_attn-2.8.3%2Bcu128torch2.7-cp312-cp312-win_amd64.whl#sha256=d0d8eaf2a11aac1d971b74ad5d1a9fbb852b4943895b0f8792e653bddb141638",
    "win_amd64-cp311": f"{_FLASH_ATTN_RELEASES}/download/v0.7.11/flash_attn-2.8.3%2Bcu128torch2.7-cp311-cp311-win_amd64.whl#sha256=ee22b69054b067de658e4a85183fc0d494b495770c8ff557e2d85b34f1f477fb",
    "linux_x86_64-cp312": f"{_FLASH_ATTN_RELEASES}/download/v0.7.16/flash_attn-2.8.3%2Bcu128torch2.7-cp312-cp312-linux_x86_64.whl#sha256=7778847721137d8bd233911ec9710a42cc9c44851ff202e02f90e3ca4cd4e860",
    "linux_x86_64-cp311": f"{_FLASH_ATTN_RELEASES}/download/v0.7.16/flash_attn-2.8.3%2Bcu128torch2.7-cp311-cp311-linux_x86_64.whl#sha256=562ada63800388bfe9733e37feb09992d59a12a386430f40a2b119c0ff68c6ad",
}

# stable-audio-3 main @ 2026-08-24, verified to expose
# `stable_audio_3.StableAudioModel.from_pretrained(...)` / `.generate(...)`.
_SA3_COMMIT = "a0b57f5483c4588f827f3552b7d5c6ca2a9687be"

# ACE-Step-1.5 main @ 2026-08-24, verified to expose
# `acestep.inference.generate_music(dit_handler, llm_handler, GenerationParams,
# GenerationConfig)` plus `acestep.handler.AceStepHandler` and
# `acestep.llm_inference.LLMHandler`.
_ACESTEP_COMMIT = "14c0211d5a0653b0f63e27686f4c3f151b4d8629"

STACKS: dict[str, dict[str, Any]] = {
    "sa3": {
        "label": "Stable Audio 3",
        # 3.12 preferred, 3.11 accepted; the projects do not support 3.13 yet.
        "pythons": ("3.12", "3.11"),
        # `stable_audio_3` is the package the `stable-audio-3` distribution
        # installs; importing it is what proves the install actually works.
        "imports": ("stable_audio_3", "torch", "soundfile"),
        # Gates one model, not the stack: `small-sfx` runs without flash_attn.
        # Importing flash_attn only proves the wheel is present. A wheel built
        # against a different torch or CUDA imports perfectly well and then dies
        # inside the kernel, which is exactly the failure a mismatched pin has,
        # so the health check calls a kernel rather than trusting the import.
        "optional_imports": {
            "flash_attn": {
                "unlocks": "the 'medium' model",
                "probe": (
                    "import torch; from flash_attn import flash_attn_func; "
                    "q = torch.randn(1, 8, 4, 64, device='cuda', dtype=torch.float16); "
                    "assert flash_attn_func(q, q, q).shape == q.shape"
                ),
            }
        },
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
                "kind": "wheel",
                "wheels": _FLASH_ATTN_WHEELS,
                "label": f"flash-attn {_FLASH_ATTN_VERSION} (cu128/torch2.7) - required by the 'medium' model",
                "note": (
                    "No pinned flash-attn "
                    + _FLASH_ATTN_VERSION
                    + " wheel is configured for this platform and Python, and "
                    "building from source needs the CUDA toolkit plus a C++ compiler. "
                    "The 'small-sfx' model runs without flash-attn; the 'medium' model "
                    "refuses to run rather than emit glitchy audio. Look for a wheel "
                    "built against torch 2.7.1 / CUDA 12.8 at "
                    + _FLASH_ATTN_RELEASES
                    + " and install it into {venv_python} before using 'medium'."
                ),
            },
        ),
    },
    "acestep": {
        "label": "ACE-Step 1.5",
        "pythons": ("3.12", "3.11"),
        # `acestep` is the package the `ace-step` distribution installs;
        # importing it is what proves the install actually works.
        "imports": ("acestep", "torch", "torchaudio"),
        # Anything that runs acestep code - including a bare import probe - must
        # carry these, or the library resolves its checkpoint tree from the
        # current working directory and can fill the user's project with weights.
        # The backend worker sets the same two variables from the same helper.
        "probe_env": {
            "ACESTEP_PROJECT_ROOT": str(_common.stack_data_dir("acestep")),
            "ACESTEP_CHECKPOINTS_DIR": str(_common.stack_data_dir("acestep") / "checkpoints"),
        },
        "steps": (
            {
                "id": "project",
                "kind": "pip",
                # Pinned: ACE-Step-1.5's default branch moves fast and its
                # generate_music() signature is not a stable public API, so an
                # unpinned git install silently changes the backend under a user
                # who re-runs setup months later. Bump this deliberately.
                "args": [f"git+https://github.com/ace-step/ACE-Step-1.5@{_ACESTEP_COMMIT}"],
                "label": f"ACE-Step-1.5 from GitHub @ {_ACESTEP_COMMIT[:7]} (PyTorch LM backend; vLLM has no Windows build)",
            },
            _TORCH_CU128,
        ),
    },
    "minimax": {
        "label": "MiniMax-Music3",
        "pythons": ("3.12", "3.11"),
        # `diffusers.modular_pipelines.minimax_music3` is where the integration
        # lives; importing the pipeline class is what proves the pin is right,
        # because a diffusers without it imports perfectly well and then fails at
        # generation time.
        "imports": (
            "torch",
            "torchaudio",
            "soundfile",
            "diffusers.modular_pipelines.minimax_music3",
        ),
        "steps": (
            {
                "id": "diffusers",
                "kind": "pip",
                # Pinned: 0.40.0 is the first release carrying the MiniMax-Music3
                # modular pipeline (MiniMaxMusic3ModularPipeline plus the
                # transformer, condition encoder, RVQ depth decoder and vocoder
                # classes), which is the whole integration. The model card still
                # points at the pre-release PR commit; the release supersedes it.
                # transformers supplies Qwen2Tokenizer/Qwen3ForCausalLM, and
                # accelerate backs the components manager's CPU offloading.
                "args": [
                    "diffusers==0.40.0",
                    "transformers>=5.0,<6",
                    "accelerate>=1.10",
                ],
                "label": "diffusers 0.40.0 + transformers 5.x (MiniMax-Music3 modular pipeline)",
            },
            _TORCH_CU128,
            {
                "id": "soundfile",
                "kind": "pip",
                "args": ["soundfile"],
                "label": "soundfile (torchaudio ships no audio backend on Windows)",
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


@functools.lru_cache(maxsize=None)
def venv_wheel_tags(stack: str) -> tuple[str, str] | None:
    """(platform tag, CPython tag) of the stack's venv interpreter, e.g.
    ("win_amd64", "cp312"). None when the venv cannot be interrogated."""
    python = _common.venv_python(stack)
    if not python.exists():
        return None
    result = _common.run(
        [
            str(python),
            "-c",
            "import sys, sysconfig; print(sysconfig.get_platform()); "
            "print('cp%d%d' % sys.version_info[:2])",
        ],
        timeout=60,
    )
    if result.returncode != 0:
        return None
    lines = result.stdout.split()
    if len(lines) != 2:
        return None
    # sysconfig spells these 'win-amd64' / 'linux-x86_64'; wheel tags use '_'.
    return lines[0].replace("-", "_").replace(".", "_"), lines[1]


def wheel_step_url(stack: str, step: dict[str, Any]) -> str | None:
    """Prebuilt wheel URL for this venv, or None when no build exists for it."""
    tags = venv_wheel_tags(stack)
    return step["wheels"].get(f"{tags[0]}-{tags[1]}") if tags else None


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

        args = list(step.get("args", ()))
        if step["kind"] == "wheel":
            # A prebuilt wheel only exists for some interpreter/platform pairs;
            # where it does not, the step degrades to its manual note.
            url = wheel_step_url(stack, step)
            if url is None:
                tags = venv_wheel_tags(stack)
                LOGGER.warning(
                    "%s: no pinned wheel configured for '%s' on %s",
                    stack,
                    step_id,
                    "/".join(tags) if tags else "this interpreter",
                )
                LOGGER.warning(
                    "%s: %s",
                    stack,
                    step["note"].format(venv_python=_common.venv_python(stack).as_posix()),
                )
                continue
            # --no-deps: flash-attn declares a bare `torch` requirement, so a
            # plain install is free to pull a fresh PyPI torch over the pinned
            # cu128 build the previous step just installed - which silently
            # turns the stack CPU-only. The wheel is built against that exact
            # torch and needs nothing else.
            args = ["--no-deps", url]

        if step["kind"] == "manual":
            note = step["note"].format(venv_python=_common.venv_python(stack).as_posix())
            LOGGER.warning("%s: manual step '%s' - %s", stack, step_id, step["label"])
            LOGGER.warning("%s: %s", stack, note)
            continue

        LOGGER.info("%s: installing %s", stack, step["label"])
        pip_install(stack, args, dry_run)
        if not dry_run:
            record_step(stack, step_id, step_hash(step))


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------


def print_notes() -> None:
    data = _common.data_dir()
    print(f"Data directory : {data.as_posix()}")
    print(f"Setup state    : {state_path().as_posix()}")
    cache = _common.hf_cache_dir()
    if os.environ.get("HF_HUB_CACHE") or os.environ.get("HF_HOME"):
        print(f"HF cache       : {cache.as_posix()}")
    else:
        print(
            f"HF cache       : {cache.as_posix()} (default; set HF_HOME to move it to a "
            "drive with room to spare - never to a path inside a git repository)"
        )
    for label, ok, detail in disk_report():
        print(f"{label:<15}: {detail}" + ("" if ok else " - WARNING: not enough room"))
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
        # A wheel step is installable here only when a prebuilt wheel exists for
        # this venv's interpreter and platform; otherwise it is a manual step.
        # Before the venv exists there is no interpreter to match a wheel
        # against, so a wheel step counts as pending until setup can look.
        unknown = venv_wheel_tags(stack) is None
        installable = [
            step
            for step in spec["steps"]
            if step["kind"] == "pip"
            or (step["kind"] == "wheel"
                and (unknown or wheel_step_url(stack, step) is not None))
        ]
        pending = [
            step["id"] for step in installable if not step_is_current(done, step)
        ]
        installable_ids = {step["id"] for step in installable}
        manual = [
            step["id"]
            for step in spec["steps"]
            if step["kind"] == "manual"
            or (step["kind"] == "wheel" and step["id"] not in installable_ids)
        ]
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
