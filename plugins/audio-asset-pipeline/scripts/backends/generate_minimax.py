"""Stage `generate` on the MiniMax-Music3 backend (vocal songs).

This is the DRIVER: stdlib only, run with the ordinary system Python from the
workspace that contains `audio-pipeline-output/`. It never imports torch or
diffusers. All model work happens in `_minimax_worker.py`, which the driver
launches once per run using the minimax virtual environment's interpreter.

MiniMax-Music3 is the vocal specialist of this pipeline: it exists to sing
written lyrics well. It refuses instrumental work (use generate_acestep.py) and
it has no reference-audio conditioning at all. It is also the slowest backend by
a wide margin - the 8B global language model emits audio frame by frame, so a
minute of music costs many minutes of GPU time on a 12 GB card.

LICENSE: the MiniMax-Music3 Community License requires any commercial product or
service shipping this model's output to display "MiniMax-Music3" prominently in
its user interface, and organizations over US$20M annual revenue need separate
written authorization from MiniMax. The driver prints this on every successful
run and records it in every candidate's params.

Usage:
    python generate_minimax.py ending-song
    python generate_minimax.py ending-song --candidates 2 --seed 7

Set AUDIO_PIPELINE_DRY_RUN=1 to synthesize placeholder wav files with ffmpeg
instead of running a model. (On Windows, use `py -3` if `python3` is not
available.)

Self-check for the caption and duration arithmetic:
`python generate_minimax.py --selftest`.
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


LOGGER = _common.setup_logger("audio-generate-minimax")
BACKEND = "minimax"
WORKER = pathlib.Path(__file__).resolve().parent / "_minimax_worker.py"

# The only published checkpoint. Its diffusers components (language model,
# flow-matching transformer, RVQ depth decoder, condition encoder, vocoder,
# tokenizer, scheduler) measure 27 GB on disk; the repository also holds the
# original-format weights for the SGLang server, which this backend never fetches.
MODEL_REPO = "MiniMaxAI/MiniMax-Music3"

# Hard limits read out of the installed diffusers integration
# (diffusers/modular_pipelines/minimax_music3/encoders.py): the autoregressive
# stage runs at 25 frames per second and stops at _MAX_AUDIO_FRAMES = 9000, so
# 360 s is the checkpoint's ceiling. Note the README quotes "5 minutes"; the code
# is the authority and it allows six.
FRAME_RATE = 25.0
MAX_AUDIO_FRAMES = 9000
MAX_DURATION_SECONDS = MAX_AUDIO_FRAMES / FRAME_RATE
# No model-side floor exists (one frame is 40 ms), but a sung section needs room
# to exist. Below 10 s the asset is a sound effect or a stinger, not a song, and
# the same floor keeps the two music backends consistent.
MIN_DURATION_SECONDS = 10.0

# The checkpoint refuses an assembled prompt over 5000 tokens. The driver has no
# tokenizer (it lives in the venv), so the real check runs in the worker, which
# tokenizes before loading any weights. This character count only decides when to
# print a heads-up: characters-per-token swings by more than 4x across languages,
# so it is far too blunt to refuse a run on.
MAX_PROMPT_TOKENS = 5000
ADVISORY_PROMPT_CHARS = 6000

# Flow-matching Euler steps per 200-frame window; the diffusers block's own
# default. The autoregressive stage dominates the runtime, so there is nothing
# to gain from lowering it and no flag to tune it.
INFERENCE_STEPS = 30

# License obligation recorded in every candidate's params, so it survives into
# the manifest and cannot be lost between the console and the shipped game.
LICENSE_NOTICE = "MiniMax-Music3 attribution required in product UI"
LICENSE_LINES = (
    "LICENSE NOTICE - MiniMax-Music3 Community License",
    "  Any commercial product or service that ships audio generated here MUST",
    '  display "MiniMax-Music3" prominently in its user interface (section 3.1).',
    "  Organizations whose products earn over US$20M a year need separate written",
    "  authorization from MiniMax first (section 3.2, api@minimax.io).",
    "  Put the credit in the game's credits/legal screen now, not at ship time.",
)

# One run must cover a cold start: the first invocation downloads 27 GB
# of diffusers components before any audio is produced. Generation itself is the
# other half of the problem - the 8B language model emits 25 frames per second of
# audio one frame at a time, and with leaf-level offloading on a 12 GB card that
# is minutes of GPU time per minute of music. The budget is therefore split: a
# fixed download-and-load allowance plus a per-candidate allowance.
WORKER_TIMEOUT_BASE_SECONDS = 5400.0
WORKER_TIMEOUT_PER_CANDIDATE_SECONDS = 3600.0


def fail(message: str, code: int = _common.EXIT_USER_ERROR) -> int:
    LOGGER.error("%s", message)
    return code


def validate_bpm(value: Any) -> int | None:
    """requirement.bpm as a whole number, or None when unset.

    MiniMax-Music3 has no structured tempo field - BPM reaches the model only as
    a line of the caption - so there is no model-side range to enforce here. This
    rejects only values that cannot be written into a caption or used for the bar
    arithmetic. The model is documented not to honour tempo exactly either way.
    """
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"requirement.bpm must be a number, got {value!r}")
    if float(value) != int(value):
        raise ValueError(
            f"requirement.bpm must be a whole number of beats per minute, got {value!r}"
        )
    bpm = int(value)
    if bpm <= 0:
        raise ValueError(f"requirement.bpm must be positive, got {bpm}")
    return bpm


def caption_with_bpm(caption: str, bpm: int | None) -> str:
    """Append 'BPM: n.' when the requirement names a tempo the caption does not.

    The caption is the ONLY channel to this model for tempo, key and arrangement
    - there is no structured metadata input - so a bpm sitting in the requirement
    would otherwise never reach the model at all. An existing mention wins: the
    author's own wording is more specific than a bare number.
    """
    if bpm is None or "bpm" in caption.lower():
        return caption
    if not caption:
        return f"BPM: {bpm}."
    separator = " " if caption.rstrip().endswith((".", "!", "?")) else ". "
    return f"{caption.rstrip()}{separator}BPM: {bpm}."


def _selftest() -> int:
    """Assertions for the caption and duration arithmetic, which nothing else checks."""
    # The duration ceiling is derived, not typed in: it must match the frame cap.
    assert MAX_DURATION_SECONDS == 360.0
    assert MAX_AUDIO_FRAMES / FRAME_RATE == MAX_DURATION_SECONDS

    assert validate_bpm(None) is None and validate_bpm("") is None
    assert validate_bpm(96) == 96 and validate_bpm(96.0) == 96
    for bad in (0, -1, 96.5, True, "fast"):
        try:
            validate_bpm(bad)
        except ValueError:
            continue
        raise AssertionError(f"expected validate_bpm to reject {bad!r}")

    # BPM is appended only when the caption does not already speak for itself.
    assert caption_with_bpm("Genre: acoustic pop", 96) == "Genre: acoustic pop. BPM: 96."
    assert caption_with_bpm("Genre: acoustic pop.", 96) == "Genre: acoustic pop. BPM: 96."
    assert caption_with_bpm("Slow ballad at 72 BPM", 96) == "Slow ballad at 72 BPM"
    assert caption_with_bpm("bpm: 80, dreamy", 96) == "bpm: 80, dreamy"
    assert caption_with_bpm("Genre: pop", None) == "Genre: pop"
    assert caption_with_bpm("", 96) == "BPM: 96."

    # Bar snapping is shared with ACE-Step but clamped to this model's range.
    bars, seconds = backend.snap_to_bars(
        60.0, 96, 4, MIN_DURATION_SECONDS, MAX_DURATION_SECONDS
    )
    assert bars == 24 and abs(seconds - 60.0) < 1e-9, (bars, seconds)
    # Clamping must respect this backend's 360 s ceiling, not ACE-Step's 600 s.
    _, seconds = backend.snap_to_bars(
        MAX_DURATION_SECONDS, 30, 6, MIN_DURATION_SECONDS, MAX_DURATION_SECONDS
    )
    assert seconds <= MAX_DURATION_SECONDS, seconds

    # The license obligation has to be present in the params the manifest keeps.
    params = backend.candidate_params({"params": {}}, {"licenseNotice": LICENSE_NOTICE})
    assert params["licenseNotice"] == LICENSE_NOTICE

    print("generate_minimax selftest: ok")
    return _common.EXIT_OK


def print_license_notice() -> None:
    print("")
    for line in LICENSE_LINES:
        print(line)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv == ["--selftest"]:
        return _selftest()

    parser = argparse.ArgumentParser(
        description="Generate candidate vocal songs for an asset with MiniMax-Music3"
    )
    parser.add_argument("slug", help="asset slug, e.g. 'ending-song'")
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
    # recorded as a failed stage rather than only printed.
    def user_error(message: str) -> int:
        return backend.record_failure(
            args.slug, backend.FAILURE_USER_ERROR, message, base, LOGGER
        )

    if manifest["assetType"] != "bgm":
        return user_error(
            f"MiniMax-Music3 generates songs, but '{args.slug}' has assetType "
            f"'{manifest['assetType']}'. Use scripts/backends/generate_sa3.py for sound "
            "effects, or re-create the asset with --type bgm."
        )

    workspace = base or _common.repo_root() or pathlib.Path.cwd()
    requirement = manifest["requirement"]

    # This backend exists for one job: singing written lyrics. An instrumental
    # request here would spend an hour of GPU time producing something ACE-Step
    # renders in seconds, so it is refused rather than quietly served.
    lyrics = requirement.get("lyrics")
    has_lyrics = isinstance(lyrics, str) and bool(lyrics.strip())
    if not requirement.get("vocals"):
        return user_error(
            f"'{args.slug}' has requirement.vocals false, and MiniMax-Music3 is this "
            "pipeline's vocal specialist - it only earns its cost when there are lyrics "
            "to sing. Use scripts/backends/generate_acestep.py for instrumental music "
            "(it is far faster), or set requirement.vocals true and write "
            "requirement.lyrics."
        )
    if not has_lyrics:
        return user_error(
            f"'{args.slug}' has requirement.vocals set but requirement.lyrics is empty. "
            "Write the lyrics into requirement.lyrics with section tags on their own "
            "lines ('[verse]', '[chorus]'), or use generate_acestep.py for an "
            "instrumental track."
        )
    lyrics_text = str(lyrics).strip()

    # No reference-audio conditioning exists in this model: the pipeline takes a
    # caption and lyrics, nothing else. Saying so is better than ignoring the field.
    if backend.resolve_reference(requirement, workspace) is not None:
        return user_error(
            f"'{args.slug}' sets requirement.referenceAudio, but MiniMax-Music3 has no "
            "reference-audio conditioning - its only inputs are the caption and the "
            "lyrics. Use scripts/backends/generate_acestep.py, which supports style "
            "conditioning on a reference track, or clear requirement.referenceAudio to "
            "generate from the caption alone."
        )

    prompt = backend.build_prompt(requirement)
    if not prompt:
        return user_error(
            f"Nothing to generate from: '{args.slug}' has no requirement.prompt. "
            "MiniMax-Music3 requires a music description alongside the lyrics - "
            "describe the genre, tempo and key, the voice, and the arrangement (for "
            "example 'Genre: wistful indie folk. Key: G major. Vocals: soft female "
            "lead. Arrangement: fingerpicked guitar, brushed drums from the chorus')."
        )

    try:
        bpm = validate_bpm(requirement.get("bpm"))
    except ValueError as exc:
        return user_error(str(exc))
    beats = backend.beats_per_bar(requirement.get("timeSignature"))
    caption = caption_with_bpm(prompt, bpm)

    combined = len(caption) + len(lyrics_text)
    if combined > ADVISORY_PROMPT_CHARS:
        # Advisory only. The worker tokenizes the real assembled prompt before it
        # loads any weights, so the authoritative check has the actual count; a
        # character count cannot tell a 5000-token Japanese lyric from a
        # 1200-token English one and must not be the thing that refuses a run.
        LOGGER.warning(
            "The caption and lyrics are %d characters together. MiniMax-Music3 caps the "
            "assembled prompt at %d tokens; the worker checks the real count before "
            "loading the model and will say so if it does not fit.",
            combined,
            MAX_PROMPT_TOKENS,
        )

    requested_duration = float(requirement["durationSeconds"])
    if not MIN_DURATION_SECONDS <= requested_duration <= MAX_DURATION_SECONDS:
        return user_error(
            f"requirement.durationSeconds is {requested_duration:g}s, but MiniMax-Music3 "
            f"generates {MIN_DURATION_SECONDS:g}-{MAX_DURATION_SECONDS:g}s "
            f"({MAX_AUDIO_FRAMES} frames at {FRAME_RATE:g} fps). Adjust the requirement."
        )

    # Loop-aware duration, recorded the same way ACE-Step records it so the post
    # stage reads one set of fields. Be honest about what it buys here: this model
    # takes no structured tempo, and the duration it is given is a CEILING the
    # language model may stop short of, so the bar count is a target rather than
    # something the backend can enforce.
    loop = bool(requirement.get("loop"))
    duration = requested_duration
    loop_snap: dict[str, Any] = {}
    if loop and bpm and beats:
        try:
            bars, duration = backend.snap_to_bars(
                requested_duration, bpm, beats, MIN_DURATION_SECONDS, MAX_DURATION_SECONDS
            )
        except ValueError as exc:
            return user_error(str(exc))
        loop_snap = {
            "requestedDurationSeconds": requested_duration,
            "barSnappedDurationSeconds": round(duration, 3),
            "bars": bars,
            "bpm": bpm,
            "beatsPerBar": beats,
            "timeSignature": requirement.get("timeSignature"),
        }
        LOGGER.info(
            "Loop asset: snapped %.2fs to %d bars (%.3fs) at %d BPM in %s. The model does "
            "not take a tempo field, so verify the result rather than trusting the maths.",
            requested_duration,
            bars,
            duration,
            bpm,
            requirement.get("timeSignature"),
        )
    elif loop:
        LOGGER.warning(
            "requirement.loop is set but bpm and timeSignature are not both usable, so "
            "the duration cannot be snapped to whole bars. Note that a song with verses "
            "and a chorus rarely loops well in the first place - consider loop false."
        )

    count = args.candidates
    if count is None:
        count = backend.CANDIDATES_BY_MODE[manifest["mode"]]
    if count < 1:
        return user_error(f"--candidates must be at least 1, got {count}")

    # --out-name-prefix reaches the filesystem, so it is validated as a bare stem:
    # '../evil' or an absolute path would otherwise write outside generate/.
    try:
        _common.validate_name_stem(args.out_name_prefix, "--out-name-prefix")
        backend.validate_seed_range(args.seed, count)
    except ValueError as exc:
        return user_error(str(exc))

    dry_run = _common.is_dry_run()
    stage = manifest["stages"]["generate"]
    existing = list(stage.get("candidates") or [])
    stage_path = _common.stage_dir(args.slug, "generate", base)
    attempts = int(stage.get("attempts", 0)) + 1

    names = [
        f"{args.out_name_prefix}-{len(existing) + index + 1:02d}.wav" for index in range(count)
    ]
    try:
        for name in names:
            _common.assert_inside(stage_path / name, stage_path, "candidate output")
    except ValueError as exc:
        return user_error(str(exc))

    timeout = WORKER_TIMEOUT_BASE_SECONDS + WORKER_TIMEOUT_PER_CANDIDATE_SECONDS * count
    LOGGER.info(
        "%s: %s duration<=%.2fs candidates=%d%s",
        args.slug,
        MODEL_REPO,
        duration,
        count,
        " [dry-run]" if dry_run else "",
    )
    if not dry_run:
        LOGGER.info(
            "This backend is autoregressive and slow: expect many minutes of GPU time "
            "per candidate, plus a 27 GB download on the first run. Budget for this "
            "call is %.0f minutes.",
            timeout / 60,
        )

    _manifest.update_stage(
        args.slug,
        "generate",
        {"status": "in_progress", "backend": BACKEND, "attempts": attempts, "failureKind": None},
        base,
    )

    seeds = backend.make_seeds(count, args.seed)
    started = time.monotonic()

    if dry_run:
        entries: list[dict[str, Any]] = []
        try:
            for seed, name in zip(seeds, names):
                # 44.1 kHz, matching what the released vocoder renders, so the post
                # stage sees the same sample rate a real run would produce.
                tail = backend.dry_run_wav(stage_path / name, duration, seed, sample_rate=44100)
                entries.append(
                    {
                        "output": (stage_path / name).as_posix(),
                        "seed": seed,
                        "leadingSilenceSeconds": 0.0,
                        "trailingSilenceSeconds": tail,
                        "params": {
                            "dryRun": True,
                            "model": MODEL_REPO,
                            "durationSeconds": duration,
                            "sampleRate": 44100,
                        },
                    }
                )
        except RuntimeError as exc:
            return backend.record_failure(
                args.slug,
                backend.FAILURE_USER_ERROR,
                str(exc),
                base,
                LOGGER,
                (stage_path, names),
            )
        runtime: dict[str, Any] = {"dryRun": True}
    else:
        request = {
            "repo": MODEL_REPO,
            "device": args.device,
            "prompt": caption,
            "lyrics": lyrics_text,
            # An upper bound, not a target: the language model emits an end token
            # when it decides the song is over, which is frequently earlier.
            "durationSeconds": duration,
            "numInferenceSteps": INFERENCE_STEPS,
            "candidates": [
                {"seed": seed, "output": str(stage_path / name)}
                for seed, name in zip(seeds, names)
            ],
        }
        try:
            payload, stderr_tail = backend.run_worker(BACKEND, WORKER, request, timeout, LOGGER)
        except RuntimeError as exc:
            return backend.record_failure(
                args.slug, backend.FAILURE_USER_ERROR, str(exc), base, LOGGER, (stage_path, names)
            )

        if not payload.get("ok"):
            kind, message = backend.worker_error(payload, stderr_tail)
            return backend.record_failure(
                args.slug,
                kind,
                f"MiniMax-Music3 failed ({kind}): {message}",
                base,
                LOGGER,
                (stage_path, names),
            )
        produced = backend.valid_produced(payload)
        if produced is None:
            return backend.record_failure(
                args.slug,
                backend.FAILURE_BACKEND_ERROR,
                "the worker reported success but its result JSON had no usable candidate "
                f"list. Worker output: {stderr_tail or '(none)'}",
                base,
                LOGGER,
                (stage_path, names),
            )
        entries = produced
        runtime = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}

    extra: dict[str, Any] = {"licenseNotice": LICENSE_NOTICE, **loop_snap}
    candidates = list(existing)
    fresh: list[dict[str, Any]] = []
    for entry in entries:
        name = pathlib.Path(entry["output"]).name
        target = stage_path / name
        if not target.is_file():
            return backend.record_failure(
                args.slug,
                backend.FAILURE_BACKEND_ERROR,
                f"the backend reported {target.as_posix()} but the file is not there",
                base,
                LOGGER,
                (stage_path, names),
            )
        params = backend.candidate_params(entry, extra, loop=loop)
        fresh.append(_manifest.make_candidate(f"generate/{name}", entry["seed"], BACKEND, params))
    candidates.extend(fresh)

    elapsed = time.monotonic() - started
    _manifest.update_stage(
        args.slug,
        "generate",
        {"status": "done", "candidates": candidates, "failureKind": None},
        base,
    )

    print("")
    print(
        f"Generated {len(entries)} candidate(s) for '{args.slug}' with "
        f"{BACKEND}/{MODEL_REPO} in {elapsed:.1f}s"
    )
    for entry, candidate in zip(entries, fresh):
        line = f"  generate/{pathlib.Path(entry['output']).name}  seed={entry['seed']}"
        actual = candidate["params"].get("actualDurationSeconds")
        if actual is not None:
            line += f"  {float(actual):.2f}s"
        line += backend.silence_note(candidate["params"])
        if entry.get("warning"):
            line += f"  WARNING: {entry['warning']}"
        print(line)
    if loop_snap:
        print(
            f"Loop target: {loop_snap['bars']} bars at {loop_snap['bpm']} BPM "
            f"({loop_snap['barSnappedDurationSeconds']:g}s for a "
            f"{loop_snap['requestedDurationSeconds']:g}s request). The model takes no "
            "tempo field - measure the result before relying on it."
        )
    if runtime.get("sampleRate"):
        print(f"Sample rate: {runtime['sampleRate']} Hz stereo")
    if runtime.get("peakVramGb"):
        print(f"Peak VRAM: {runtime['peakVramGb']} GB (offloading: {runtime.get('offloading')})")
    print(f"Files: {stage_path.as_posix()}")
    print_license_notice()
    print("")
    print("Next: listen to the candidates, then record the chosen one as stages.generate.selected.")
    return _common.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
