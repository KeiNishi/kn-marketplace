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
import pathlib
import sys
import time
from typing import Any

_SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import _common  # noqa: E402
import _manifest  # noqa: E402
import _backend_common as backend  # noqa: E402


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
# One run must cover a cold start: the first invocation downloads 2-7 GB of
# weights over whatever connection the user has, before any audio is produced.
# Generation itself is seconds per candidate, so almost all of this budget is
# download headroom.
WORKER_TIMEOUT_SECONDS = 1800.0


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


def record_failure(
    slug: str,
    kind: str,
    message: str,
    base: pathlib.Path | None,
    cleanup: tuple[pathlib.Path, list[str]] | None = None,
) -> int:
    return backend.record_failure(slug, kind, message, base, LOGGER, cleanup)


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
        return record_failure(args.slug, backend.FAILURE_USER_ERROR, message, base)

    # The manifest was located relative to this root, so relative requirement
    # paths mean the same thing regardless of the caller's working directory.
    workspace = base or _common.repo_root() or pathlib.Path.cwd()
    requirement = manifest["requirement"]
    prompt = backend.build_prompt(requirement)
    reference = backend.resolve_reference(requirement, workspace)
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
        count = backend.CANDIDATES_BY_MODE[manifest["mode"]]
    if count < 1:
        return user_error(f"--candidates must be at least 1, got {count}")

    # --out-name-prefix reaches the filesystem, so it is validated as a bare stem:
    # '../evil' or an absolute path would otherwise write outside generate/, and
    # the dry-run ffmpeg call uses -y.
    try:
        _common.validate_name_stem(args.out_name_prefix, "--out-name-prefix")
        backend.validate_seed_range(args.seed, count)
    except ValueError as exc:
        return user_error(str(exc))

    dry_run = _common.is_dry_run()
    stage = manifest["stages"]["generate"]
    existing = list(stage.get("candidates") or [])
    seeds = backend.make_seeds(count, args.seed)
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
        tails = []
        try:
            for seed, name in zip(seeds, names):
                tails.append(backend.dry_run_wav(stage_path / name, duration, seed))
        except RuntimeError as exc:
            return record_failure(
                args.slug, backend.FAILURE_USER_ERROR, str(exc), base, (stage_path, names)
            )
        produced = [
            {
                "output": (stage_path / name).as_posix(),
                "seed": seed,
                "leadingSilenceSeconds": 0.0,
                "trailingSilenceSeconds": tail,
                "params": {"dryRun": True, "model": model, "durationSeconds": duration},
            }
            for (seed, name), tail in zip(zip(seeds, names), tails)
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
            payload, stderr_tail = backend.run_worker(
                BACKEND, WORKER, request, WORKER_TIMEOUT_SECONDS, LOGGER
            )
        except RuntimeError as exc:
            return record_failure(
                args.slug, backend.FAILURE_USER_ERROR, str(exc), base, (stage_path, names)
            )

        if not payload.get("ok"):
            kind, message = backend.worker_error(payload, stderr_tail)
            return record_failure(
                args.slug,
                kind,
                f"Stable Audio 3 failed ({kind}): {message}",
                base,
                (stage_path, names),
            )
        produced = backend.valid_produced(payload)
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
        extra = {"requestedDurationSeconds": requested_duration} if duration > requested_duration else None
        params = backend.candidate_params(entry, extra, loop=bool(requirement.get("loop")))
        candidates.append(_manifest.make_candidate(f"generate/{name}", entry["seed"], BACKEND, params))

    _manifest.update_stage(
        args.slug,
        "generate",
        {"status": "done", "candidates": candidates, "failureKind": None},
        base,
    )

    print("")
    print(f"Generated {len(produced)} candidate(s) for '{args.slug}' with {BACKEND}/{model} in {elapsed:.1f}s")
    for entry, candidate in zip(produced, candidates[len(existing):]):
        line = f"  generate/{pathlib.Path(entry['output']).name}  seed={entry['seed']}"
        line += backend.silence_note(candidate["params"])
        if entry.get("warning"):
            line += f"  WARNING: {entry['warning']}"
        print(line)
    print(f"Files: {stage_path.as_posix()}")
    print("Next: listen to the candidates, then record the chosen one as stages.generate.selected.")
    return _common.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
