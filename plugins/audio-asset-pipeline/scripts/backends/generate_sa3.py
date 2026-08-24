"""Stage `generate` on the Stable Audio 3 backend.

This is the DRIVER: stdlib only, run with the ordinary system Python from the
workspace that contains `audio-pipeline-output/`. It never imports torch or
`stable_audio_3`. All model work happens in `_sa3_worker.py`, which the driver
launches once per run using the sa3 virtual environment's interpreter.

Usage:
    python generate_sa3.py <slug>
    python generate_sa3.py <slug> --model small-sfx --candidates 3
    python generate_sa3.py <slug> --model medium --seed 4242

Set AUDIO_PIPELINE_DRY_RUN=1 to synthesize placeholder wav files with ffmpeg
instead of running a model. (On Windows, use `py -3` if `python3` is not
available.)
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import shutil
import sys
import tempfile
import time
from typing import Any

_SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import _common  # noqa: E402
import _manifest  # noqa: E402


LOGGER = _common.setup_logger("audio-generate-sa3")
BACKEND = "sa3"
WORKER = pathlib.Path(__file__).resolve().parent / "_sa3_worker.py"

# Maximum duration each checkpoint was trained for. Past these the model starts
# repeating or collapsing, so the driver refuses rather than burning GPU time.
MODEL_MAX_SECONDS: dict[str, float] = {"small-sfx": 120.0, "medium": 380.0}
# Stable Audio 3 works on a ~10.76 Hz latent grid, so a sub-2s request lands on
# a handful of latent frames and comes out unreliable. Generate at least this
# much and let the post stage trim to the requested length.
MIN_GENERATE_SECONDS = 2.0
# Post-trained SA3 checkpoints are distilled for 8 ping-pong steps at CFG 1.0;
# raising either does not improve quality, it just costs time.
STEPS = 8
CFG_SCALE = 1.0
# How many candidates to produce when the user does not say. Manual mode is the
# "pick your favourite" workflow, auto mode takes the first result and moves on.
CANDIDATES_BY_MODE = {"manual": 3, "auto": 1}
# One run must cover a cold start: the first invocation downloads 2-7 GB of
# weights over whatever connection the user has, before any audio is produced.
# Generation itself is seconds per candidate, so almost all of this budget is
# download headroom.
WORKER_TIMEOUT_SECONDS = 1800.0
# torch.manual_seed accepts a 64-bit value, but backends and file names travel
# through JSON and other tooling; 2**32-1 is the widest bound that is safe
# everywhere the seed is recorded.
MAX_SEED = 2**32 - 1
# Mirrors _sa3_worker.partial_path: the worker writes each candidate to
# ".<stem>.tmp.wav" and renames it into place, so a failed attempt can leave one
# behind. The temp name keeps the .wav extension because torchaudio picks the
# container format from it.
PARTIAL_INFIX = ".tmp"


def partial_name(name: str) -> str:
    stem, _, suffix = name.rpartition(".")
    return f".{stem}{PARTIAL_INFIX}.{suffix}"

# Structured failure vocabulary shared with the worker, recorded in
# stages.generate.failureKind. Later backends should reuse these names.
FAILURE_USER_ERROR = "user_error"
FAILURE_TIMEOUT = "timeout"
WORKER_FAILURE_KINDS = (
    FAILURE_USER_ERROR,
    "missing_flash_attn",
    "oom",
    "model_download_failed",
    "backend_error",
)


def fail(message: str, code: int = _common.EXIT_USER_ERROR) -> int:
    LOGGER.error("%s", message)
    return code


def resolve_model(requested: str, asset_type: str) -> str:
    """Route `auto` by asset type; anything explicit is taken as given."""
    if requested != "auto":
        return requested
    # small-sfx is the fast, low-VRAM checkpoint tuned for one-shot sounds;
    # medium is the ambient/instrumental model this backend covers for BGM.
    return "small-sfx" if asset_type == "se" else "medium"


def build_prompt(requirement: dict[str, Any]) -> str:
    parts = [str(requirement.get("prompt") or "").strip()]
    tags = requirement.get("styleTags") or []
    if isinstance(tags, list):
        parts.extend(str(tag).strip() for tag in tags if str(tag).strip())
    return ", ".join(part for part in parts if part)


def resolve_reference(requirement: dict[str, Any], workspace: pathlib.Path) -> pathlib.Path | None:
    """Resolve requirement.referenceAudio against the workspace, not the CWD.

    The manifest was found relative to the workspace root, so a relative path
    inside it means the same thing no matter which directory the user ran from.
    """
    reference = requirement.get("referenceAudio")
    if not reference:
        return None
    path = pathlib.Path(str(reference)).expanduser()
    return path if path.is_absolute() else (workspace / path).resolve()


def make_seeds(count: int, base: int | None) -> list[int]:
    if base is not None:
        return [base + offset for offset in range(count)]
    return [random.randrange(0, MAX_SEED + 1) for _ in range(count)]


def validate_seed_range(base: int | None, count: int) -> None:
    """Reject a base seed whose whole batch would not fit the accepted range."""
    if base is None:
        return
    if base < 0 or base > MAX_SEED:
        raise ValueError(f"--seed must be between 0 and {MAX_SEED}, got {base}")
    if base + count - 1 > MAX_SEED:
        raise ValueError(
            f"--seed {base} with {count} candidates would reach {base + count - 1}, "
            f"past the maximum seed {MAX_SEED}. Lower the seed or the candidate count."
        )


def dry_run_wav(target: pathlib.Path, duration: float, seed: int) -> None:
    """Synthesize a placeholder tone so later stages have real audio to chew on.

    A tone rather than silence: the post and review stages measure loudness and
    loop points, and every one of those checks is degenerate on pure silence.
    The frequency varies with the seed so candidates are distinguishable.
    """
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError(
            "ffmpeg is required even for dry runs (it synthesizes the placeholder "
            "wav files). Install it and re-run; `python doctor.py` checks for it."
        )
    frequency = 220 + (seed % 12) * 40
    result = _common.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={frequency}:sample_rate=44100:duration={duration:.3f}",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            "-y",
            str(target),
        ],
        timeout=120,
    )
    if result.returncode != 0 or not target.is_file():
        raise RuntimeError(f"ffmpeg could not write {target.as_posix()}: {result.stderr.strip()[-500:]}")


def run_worker(request: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Run the venv-side worker once. Returns (result payload, stderr tail)."""
    python = _common.venv_python(BACKEND)
    if not python.exists():
        raise RuntimeError(
            f"The sa3 environment is missing ({python.as_posix()}). Run "
            "`python setup_env.py --stack sa3`, then `python doctor.py --stack sa3`."
        )

    with tempfile.TemporaryDirectory(prefix="sa3-request-") as tmp:
        request_path = pathlib.Path(tmp) / "request.json"
        result_path = pathlib.Path(tmp) / "result.json"
        request = {**request, "resultPath": str(result_path)}
        request_path.write_text(json.dumps(request, indent=2, ensure_ascii=False), encoding="utf-8")

        LOGGER.info("Running the sa3 worker (timeout %.0f min)", WORKER_TIMEOUT_SECONDS / 60)
        # Hands the worker any HF_TOKEN kept in the plugin's private .env so the
        # gated weights can be fetched. Values are secrets: never logged, never
        # written to the manifest.
        completed = _common.run(
            [python, WORKER, "--request", request_path],
            timeout=WORKER_TIMEOUT_SECONDS,
            env=_common.subprocess_env(),
        )
        stderr_tail = (completed.stderr or "").strip()[-2000:]
        try:
            payload = _common.read_json(result_path)
        except ValueError as exc:
            # Corrupt result JSON is still a backend failure, not a driver crash.
            LOGGER.warning("worker result file was unreadable: %s", exc)
            payload = None

    if payload is None:
        if completed.returncode == _common.EXIT_TIMEOUT:
            return {"ok": False, "error": {"kind": FAILURE_TIMEOUT, "message": stderr_tail}}, stderr_tail
        return (
            {
                "ok": False,
                "error": {
                    "kind": "backend_error",
                    "message": f"the worker exited {completed.returncode} without writing a result",
                },
            },
            stderr_tail,
        )
    if not isinstance(payload, dict):
        return (
            {
                "ok": False,
                "error": {"kind": "backend_error", "message": "the worker result was not an object"},
            },
            stderr_tail,
        )
    return payload, stderr_tail


def valid_produced(payload: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Return the candidate list only if it has the shape the driver relies on.

    A malformed success payload must become a recorded backend_error, never a
    KeyError that leaves the stage stuck in_progress.
    """
    produced = payload.get("candidates")
    if not isinstance(produced, list) or not produced:
        return None
    for entry in produced:
        if not isinstance(entry, dict) or not entry.get("output"):
            return None
        try:
            int(entry["seed"])
        except (KeyError, TypeError, ValueError):
            return None
    return produced


def cleanup_attempt(stage_path: pathlib.Path, names: list[str]) -> None:
    """Remove this attempt's outputs and partials after a failure.

    Only the names this run planned are touched. Candidate numbering continues
    from the existing list, so these never collide with an earlier attempt's
    files.
    """
    for name in names:
        for leftover in (stage_path / name, stage_path / partial_name(name)):
            try:
                leftover.unlink(missing_ok=True)
            except OSError as exc:  # locked file: worth saying, not worth failing over
                LOGGER.warning("could not remove %s: %s", leftover.as_posix(), exc)


def record_failure(
    slug: str,
    kind: str,
    message: str,
    base: pathlib.Path | None,
    cleanup: tuple[pathlib.Path, list[str]] | None = None,
) -> int:
    if cleanup is not None:
        cleanup_attempt(*cleanup)
    _manifest.update_stage(slug, "generate", {"status": "failed", "failureKind": kind}, base)
    LOGGER.error("%s", message)
    code = _common.EXIT_TIMEOUT if kind == FAILURE_TIMEOUT else _common.EXIT_BACKEND_ERROR
    return _common.EXIT_USER_ERROR if kind in {FAILURE_USER_ERROR, "missing_flash_attn"} else code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate candidate audio for an asset with Stable Audio 3"
    )
    parser.add_argument("slug", help="asset slug, e.g. 'door-open'")
    parser.add_argument(
        "--model",
        choices=("auto", "small-sfx", "medium"),
        default="auto",
        help="auto routes SE to small-sfx and BGM to medium (default: auto)",
    )
    parser.add_argument(
        "--candidates",
        type=int,
        default=None,
        help="how many candidates to generate (default: 3 in manual mode, 1 in auto mode)",
    )
    parser.add_argument(
        "--out-name-prefix",
        default="cand",
        help="file name prefix inside the generate/ folder (default: cand)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="base seed; candidate N uses seed+N-1 (default: random per candidate)",
    )
    parser.add_argument("--negative-prompt", default=None, help="qualities to steer away from")
    parser.add_argument("--device", default=None, help="torch device for the worker (default: auto)")
    parser.add_argument("--base", default=None, help="workspace holding audio-pipeline-output/")
    args = parser.parse_args(argv)

    base = pathlib.Path(args.base).expanduser().resolve() if args.base else None

    try:
        manifest = _manifest.read(args.slug, base)
    except FileNotFoundError as exc:
        return fail(str(exc))
    except ValueError as exc:
        return fail(f"Manifest is not usable: {exc}", _common.EXIT_MANIFEST_CORRUPT)

    # Everything below this point has a readable manifest, so a user mistake is
    # recorded as a failed stage rather than only printed. That is what the skill
    # documents, and it stops a stale 'in_progress' or 'done' from lingering.
    def user_error(message: str) -> int:
        return record_failure(args.slug, FAILURE_USER_ERROR, message, base)

    # The manifest was located relative to this root, so relative requirement
    # paths mean the same thing regardless of the caller's working directory.
    workspace = base or _common.repo_root() or pathlib.Path.cwd()
    requirement = manifest["requirement"]
    prompt = build_prompt(requirement)
    reference = resolve_reference(requirement, workspace)
    if not prompt and reference is None:
        return user_error(
            f"Nothing to generate from: {args.slug} has neither requirement.prompt nor "
            "requirement.referenceAudio. Describe the sound (for example 'wooden door "
            "creaking open, interior, close mic') or point referenceAudio at a wav file, "
            "then re-run."
        )
    if reference is not None and not reference.is_file():
        return user_error(f"requirement.referenceAudio does not exist: {reference.as_posix()}")

    model = resolve_model(args.model, manifest["assetType"])
    requested_duration = float(requirement["durationSeconds"])
    limit = MODEL_MAX_SECONDS[model]
    if requested_duration > limit:
        return user_error(
            f"requirement.durationSeconds is {requested_duration:g}s, but model "
            f"'{model}' is trained up to {limit:g}s. Shorten the requirement"
            + (", or use --model medium (up to 380s)." if model == "small-sfx" else ".")
        )
    duration = max(requested_duration, MIN_GENERATE_SECONDS)
    if duration > requested_duration:
        LOGGER.info(
            "Generating %.2fs instead of the requested %.2fs: shorter clips are "
            "unreliable at this model's latent rate. Trim in the post stage.",
            duration,
            requested_duration,
        )

    count = args.candidates
    if count is None:
        count = CANDIDATES_BY_MODE[manifest["mode"]]
    if count < 1:
        return user_error(f"--candidates must be at least 1, got {count}")

    # --out-name-prefix reaches the filesystem, so it is validated as a bare stem:
    # '../evil' or an absolute path would otherwise write outside generate/, and
    # the dry-run ffmpeg call uses -y.
    try:
        _common.validate_name_stem(args.out_name_prefix, "--out-name-prefix")
        validate_seed_range(args.seed, count)
    except ValueError as exc:
        return user_error(str(exc))

    dry_run = _common.is_dry_run()
    stage = manifest["stages"]["generate"]
    existing = list(stage.get("candidates") or [])
    seeds = make_seeds(count, args.seed)
    stage_path = _common.stage_dir(args.slug, "generate", base)
    # Continue the numbering so a re-run appends instead of overwriting earlier takes.
    names = [f"{args.out_name_prefix}-{len(existing) + index + 1:02d}.wav" for index in range(count)]
    try:
        for name in names:
            _common.assert_inside(stage_path / name, stage_path, "candidate output")
    except ValueError as exc:
        return user_error(str(exc))

    _manifest.update_stage(
        args.slug,
        "generate",
        {
            "status": "in_progress",
            "backend": BACKEND,
            "attempts": int(stage.get("attempts", 0)) + 1,
            "failureKind": None,
        },
        base,
    )

    LOGGER.info(
        "%s: model=%s duration=%.2fs candidates=%d%s%s",
        args.slug,
        model,
        duration,
        count,
        f" reference={reference.name}" if reference else "",
        " [dry-run]" if dry_run else "",
    )

    started = time.monotonic()
    if dry_run:
        try:
            for seed, name in zip(seeds, names):
                dry_run_wav(stage_path / name, duration, seed)
        except RuntimeError as exc:
            return record_failure(
                args.slug, FAILURE_USER_ERROR, str(exc), base, (stage_path, names)
            )
        produced = [
            {
                "output": (stage_path / name).as_posix(),
                "seed": seed,
                "params": {"dryRun": True, "model": model, "durationSeconds": duration},
            }
            for seed, name in zip(seeds, names)
        ]
    else:
        request = {
            "model": model,
            "device": args.device,
            "prompt": prompt,
            "negativePrompt": args.negative_prompt,
            "durationSeconds": duration,
            "steps": STEPS,
            "cfgScale": CFG_SCALE,
            "chunkedDecode": True,
            "initAudio": reference.as_posix() if reference else None,
            # referenceStrength is intuitive (1.0 = stay closest to the reference).
            # SA3's init_noise_level is the opposite knob - how much noise replaces
            # the reference - so it is inverted here.
            "initNoiseLevel": 1.0 - float(requirement["referenceStrength"]),
            "candidates": [
                {"seed": seed, "output": str(stage_path / name)} for seed, name in zip(seeds, names)
            ],
        }
        try:
            payload, stderr_tail = run_worker(request)
        except RuntimeError as exc:
            return record_failure(
                args.slug, FAILURE_USER_ERROR, str(exc), base, (stage_path, names)
            )

        if not payload.get("ok"):
            error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
            kind = error.get("kind")
            if kind not in (*WORKER_FAILURE_KINDS, FAILURE_TIMEOUT):
                kind = "backend_error"
            message = error.get("message") or stderr_tail or "the worker reported no detail"
            return record_failure(
                args.slug,
                kind,
                f"Stable Audio 3 failed ({kind}): {message}",
                base,
                (stage_path, names),
            )
        produced = valid_produced(payload)
        if produced is None:
            return record_failure(
                args.slug,
                "backend_error",
                "the worker reported success but its result JSON had no usable "
                f"candidate list. Worker output: {stderr_tail or '(none)'}",
                base,
                (stage_path, names),
            )

    elapsed = time.monotonic() - started

    candidates = list(existing)
    for entry in produced:
        name = pathlib.Path(entry["output"]).name
        target = stage_path / name
        if not target.is_file():
            return record_failure(
                args.slug,
                "backend_error",
                f"the backend reported {target.as_posix()} but the file is not there",
                base,
                (stage_path, names),
            )
        params = dict(entry.get("params") or {})
        for key in ("generationSeconds", "actualDurationSeconds"):
            if entry.get(key) is not None:
                params[key] = entry[key]
        if duration > requested_duration:
            params["requestedDurationSeconds"] = requested_duration
        candidates.append(_manifest.make_candidate(f"generate/{name}", entry["seed"], BACKEND, params))

    _manifest.update_stage(
        args.slug,
        "generate",
        {"status": "done", "candidates": candidates, "failureKind": None},
        base,
    )

    print("")
    print(f"Generated {len(produced)} candidate(s) for '{args.slug}' with {BACKEND}/{model} in {elapsed:.1f}s")
    for entry in produced:
        line = f"  generate/{pathlib.Path(entry['output']).name}  seed={entry['seed']}"
        if entry.get("warning"):
            line += f"  WARNING: {entry['warning']}"
        print(line)
    print(f"Files: {stage_path.as_posix()}")
    print("Next: listen to the candidates, then record the chosen one as stages.generate.selected.")
    return _common.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
