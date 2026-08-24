"""Stage `generate` on the ACE-Step 1.5 backend (background music).

This is the DRIVER: stdlib only, run with the ordinary system Python from the
workspace that contains `audio-pipeline-output/`. It never imports torch or
`acestep`. All model work happens in `_acestep_worker.py`, which the driver
launches once per run using the acestep virtual environment's interpreter.

Usage:
    python generate_acestep.py boss-battle-theme
    python generate_acestep.py boss-battle-theme --candidates 3 --seed 4242
    python generate_acestep.py town-theme --model sft --no-loop-hints

Set AUDIO_PIPELINE_DRY_RUN=1 to synthesize placeholder wav files with ffmpeg
instead of running a model. (On Windows, use `py -3` if `python3` is not
available.)

Self-check for the bar-snapping arithmetic: `python generate_acestep.py --selftest`.
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


LOGGER = _common.setup_logger("audio-generate-acestep")
BACKEND = "acestep"
WORKER = pathlib.Path(__file__).resolve().parent / "_acestep_worker.py"

# DiT checkpoints this backend offers, mapped to their on-disk checkpoint names.
# 'turbo' ships inside the main model repository, so it is the only one that
# needs no extra multi-GB download. The XL (4B) checkpoints are deliberately
# absent: they do not fit a 12 GB card alongside the LM planner.
MODELS: dict[str, str] = {
    "turbo": "acestep-v15-turbo",
    "sft": "acestep-v15-sft",
    "base": "acestep-v15-base",
}
DEFAULT_MODEL = "turbo"
# Turbo is distilled for 8 steps; base/sft are not distilled and need a real
# diffusion budget. Upstream documents 8 for turbo and 32-100 for the others.
STEPS_BY_MODEL = {"turbo": 8, "sft": 32, "base": 32}
# Classifier-free guidance is only honoured by the non-distilled checkpoints.
CFG_BY_MODEL = {"turbo": None, "sft": 7.0, "base": 7.0}

# ACE-Step 1.5 is trained for 10-600 s. Outside that the model does not merely
# degrade, it is out of distribution, so the driver refuses instead of burning
# the download and the GPU time.
MIN_DURATION_SECONDS = 10.0
MAX_DURATION_SECONDS = 600.0
# Upstream's own field limits (acestep.inference.GenerationParams). Exceeding
# them truncates silently, which is worse than being told.
MAX_CAPTION_CHARS = 512
MAX_LYRICS_CHARS = 4096
# The lyrics token that puts the model in instrumental mode. `GenerationParams`
# also has an `instrumental` flag, but generate_music() never reads it - this
# marker is what actually reaches the DiT.
INSTRUMENTAL_MARKER = "[Instrumental]"
# Accepted by ACE-Step's metadata fields (acestep.inference.GenerationParams and
# acestep.constants.VALID_TIME_SIGNATURES). Values outside these are not clamped
# upstream, they are simply out of distribution, so the driver refuses them.
BPM_RANGE = (30, 300)
VALID_BEATS_PER_BAR = (2, 3, 4, 6)

# Appended to the prompt for looping assets unless --no-loop-hints is passed.
# The planner writes an intro and an outro by default, and neither survives a
# loop point; saying so in the prompt is the only lever at generation time. The
# "sustained energy" clause is there because the planner also likes to resolve
# and stop early, leaving the rest of the requested length as silence.
LOOP_PROMPT_HINTS = (
    "seamless loop, no intro, no outro, no fade-out, sustained energy until the final bar"
)

# Ceiling on candidates generated in one invocation while retrying for loop
# viability. Auto mode is unattended, so the retry has to stop on its own; three
# takes is enough to get past an unlucky plan without quietly burning a GPU.
MAX_LOOP_CANDIDATES = 3

# One run must cover a cold start: the first invocation downloads roughly 12 GB
# (DiT + VAE + text encoder + LM planner) before any audio is produced.
# Generation itself is a minute or two per candidate, so nearly all of this
# budget is download headroom - it covers about 2.5 MB/s. A slower link will
# still time out; the download resumes on the next run, so re-running is the fix
# and the skill says so.
WORKER_TIMEOUT_SECONDS = 5400.0


def fail(message: str, code: int = _common.EXIT_USER_ERROR) -> int:
    LOGGER.error("%s", message)
    return code


def validate_bpm(value: Any) -> int | None:
    """requirement.bpm as an int in ACE-Step's range, or None when unset."""
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"requirement.bpm must be a number, got {value!r}")
    if float(value) != int(value):
        raise ValueError(
            f"requirement.bpm must be a whole number of beats per minute, got {value!r}"
        )
    bpm = int(value)
    low, high = BPM_RANGE
    if not low <= bpm <= high:
        raise ValueError(
            f"requirement.bpm is {bpm}, but ACE-Step accepts {low}-{high}. "
            "Pick a tempo inside that range."
        )
    return bpm


def validate_beats(time_signature: Any) -> int | None:
    """Beats per bar for a supported signature, or None when unset."""
    if time_signature is None or not str(time_signature).strip():
        return None
    beats = backend.beats_per_bar(time_signature)
    if beats not in VALID_BEATS_PER_BAR:
        raise ValueError(
            f"requirement.timeSignature is {time_signature!r}, but ACE-Step only supports "
            f"{', '.join(f'{n}/{4 if n != 6 else 8}' for n in VALID_BEATS_PER_BAR)}. "
            "Use one of those, or clear the field to let the model choose."
        )
    return beats


def snap_to_bars(duration: float, bpm: int, beats: int) -> tuple[int, float]:
    """backend.snap_to_bars clamped to ACE-Step 1.5's own trained duration range."""
    return backend.snap_to_bars(
        duration, bpm, beats, MIN_DURATION_SECONDS, MAX_DURATION_SECONDS
    )


def _selftest() -> int:
    """Assertions for the bar-snapping arithmetic, which nothing else checks."""
    assert backend.beats_per_bar("4/4") == 4
    assert backend.beats_per_bar("3/4") == 3
    assert backend.beats_per_bar("6/8") == 6
    # ACE-Step's own field is the bare numerator, so accept that spelling too.
    assert backend.beats_per_bar(4) == 4
    for bad in (None, "", "x/4", "0/4", "-3/4", "/4"):
        assert backend.beats_per_bar(bad) is None, bad

    # 140 BPM in 4/4 is 12/7 s per bar: 30 s is 17.5 bars, which rounds to 18.
    bars, seconds = snap_to_bars(30.0, 140, 4)
    assert bars == 18 and abs(seconds - 30.857) < 0.001, (bars, seconds)
    # An exact fit must not drift.
    bars, seconds = snap_to_bars(60.0, 120, 4)
    assert bars == 30 and abs(seconds - 60.0) < 1e-9, (bars, seconds)
    # 6/8 counts six beats to the bar.
    bars, seconds = snap_to_bars(60.0, 120, 6)
    assert bars == 20 and abs(seconds - 60.0) < 1e-9, (bars, seconds)
    # Rounding down must never leave the result under the model's 10 s floor.
    bars, seconds = snap_to_bars(10.0, 30, 2)
    assert seconds >= MIN_DURATION_SECONDS, (bars, seconds)
    # ...nor over its 600 s ceiling.
    bars, seconds = snap_to_bars(600.0, 30, 6)
    assert seconds <= MAX_DURATION_SECONDS, (bars, seconds)

    # A tempo whose bar is longer than the whole accepted range has no answer,
    # and the caller must hear about it instead of receiving a silent clamp.
    # 30 BPM in 6/8 is a 12 s bar, which cannot land inside a 10-11 s window;
    # 1 BPM in 7/4 is a 420 s bar, longer than MiniMax's whole 360 s ceiling.
    for impossible in ((60.0, 30, 6, 10.0, 11.0), (360.0, 1, 7, 10.0, 360.0)):
        try:
            backend.snap_to_bars(*impossible)
        except ValueError:
            continue
        raise AssertionError(f"expected snap_to_bars to reject {impossible}")

    # A tempo that makes bars tiny must return immediately, not step bar by bar.
    started = time.monotonic()
    bars, seconds = backend.snap_to_bars(75.0, 1_000_000_000, 4, 10.0, 360.0)
    assert 10.0 <= seconds <= 360.0 and bars > 1, (bars, seconds)
    assert time.monotonic() - started < 1.0, "snap_to_bars must be constant time"

    # Non-finite and non-positive inputs are rejected rather than producing NaN bars.
    for bad_args in (
        (60.0, float("nan"), 4, 10.0, 600.0),
        (60.0, float("inf"), 4, 10.0, 600.0),
        (60.0, 0, 4, 10.0, 600.0),
        (60.0, -120, 4, 10.0, 600.0),
        (60.0, 120, 0, 10.0, 600.0),
        (60.0, 120, True, 10.0, 600.0),
        (60.0, 120, 4.5, 10.0, 600.0),
        (float("nan"), 120, 4, 10.0, 600.0),
        (0.0, 120, 4, 10.0, 600.0),
        (60.0, 120, 4, 600.0, 10.0),
    ):
        try:
            backend.snap_to_bars(*bad_args)
        except ValueError:
            continue
        raise AssertionError(f"expected snap_to_bars to reject {bad_args}")
    # Every model variant needs a step count and a CFG entry.
    assert set(STEPS_BY_MODEL) == set(MODELS) == set(CFG_BY_MODEL)

    # ACE-Step metadata validation: unset is fine, out-of-range is refused.
    assert validate_bpm(None) is None and validate_bpm("") is None
    assert validate_bpm(140) == 140 and validate_bpm(140.0) == 140
    for bad_bpm in (0, 29, 301, -1, 140.5, True, "fast"):
        try:
            validate_bpm(bad_bpm)
        except ValueError:
            continue
        raise AssertionError(f"expected validate_bpm to reject {bad_bpm!r}")

    assert validate_beats(None) is None and validate_beats("  ") is None
    for good, beats in (("4/4", 4), ("3/4", 3), ("6/8", 6), ("2/4", 2), ("4", 4)):
        assert validate_beats(good) == beats, good
    for bad_signature in ("5/4", "7/8", "0/4", "x/4", "12/8"):
        try:
            validate_beats(bad_signature)
        except ValueError:
            continue
        raise AssertionError(f"expected validate_beats to reject {bad_signature!r}")

    # Loop viability: only measurements past the limit disqualify a candidate.
    limit = backend.LOOP_SILENCE_LIMIT_SECONDS
    assert backend.loop_viable({}) is True
    assert backend.loop_viable({"trailingSilenceSeconds": limit}) is True
    assert backend.loop_viable({"trailingSilenceSeconds": limit + 0.01}) is False
    assert backend.loop_viable({"leadingSilenceSeconds": limit + 0.01}) is False
    annotated = backend.candidate_params(
        {"params": {}, "trailingSilenceSeconds": 5.05, "leadingSilenceSeconds": 0.0}, loop=True
    )
    assert annotated["loopViable"] is False and annotated["trailingSilenceSeconds"] == 5.05
    assert "NOT LOOP-VIABLE" in backend.silence_note(annotated)
    assert backend.silence_note({}) == ""
    # Without loop=True the flag is not added at all: non-loop assets have no policy.
    assert "loopViable" not in backend.candidate_params({"trailingSilenceSeconds": 5.05})

    print("generate_acestep selftest: ok")
    return _common.EXIT_OK


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv == ["--selftest"]:
        return _selftest()

    parser = argparse.ArgumentParser(
        description="Generate candidate background music for an asset with ACE-Step 1.5"
    )
    parser.add_argument("slug", help="asset slug, e.g. 'boss-battle-theme'")
    parser.add_argument(
        "--model",
        choices=("auto", *MODELS),
        default="auto",
        help=f"DiT checkpoint; auto uses '{DEFAULT_MODEL}' (default: auto)",
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
    parser.add_argument(
        "--negative-prompt",
        default=None,
        help="qualities to steer the LM planner away from (LM guidance only; the DiT has no negative prompt)",
    )
    parser.add_argument(
        "--no-loop-hints",
        action="store_true",
        help="do not append 'seamless loop, no intro, no outro' to the prompt of a looping asset",
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
    # recorded as a failed stage rather than only printed. That is what the skill
    # documents, and it stops a stale 'in_progress' or 'done' from lingering.
    def user_error(message: str) -> int:
        return backend.record_failure(
            args.slug, backend.FAILURE_USER_ERROR, message, base, LOGGER
        )

    if manifest["assetType"] != "bgm":
        return user_error(
            f"ACE-Step generates music, but '{args.slug}' has assetType "
            f"'{manifest['assetType']}'. Use scripts/backends/generate_sa3.py for sound "
            "effects, or re-create the asset with --type bgm."
        )

    # The manifest was located relative to this root, so relative requirement
    # paths mean the same thing regardless of the caller's working directory.
    workspace = base or _common.repo_root() or pathlib.Path.cwd()
    requirement = manifest["requirement"]
    prompt = backend.build_prompt(requirement)
    reference = backend.resolve_reference(requirement, workspace)
    if not prompt and reference is None:
        return user_error(
            f"Nothing to generate from: {args.slug} has neither requirement.prompt nor "
            "requirement.referenceAudio. Describe the music (for example 'driving "
            "orchestral boss battle theme, taiko drums, brass ostinato') or point "
            "referenceAudio at an audio file, then re-run."
        )
    if reference is not None and not reference.is_file():
        return user_error(f"requirement.referenceAudio does not exist: {reference.as_posix()}")

    loop = bool(requirement.get("loop"))
    if loop and prompt and not args.no_loop_hints:
        prompt = f"{prompt}, {LOOP_PROMPT_HINTS}"
    if len(prompt) > MAX_CAPTION_CHARS:
        return user_error(
            f"The prompt is {len(prompt)} characters, past ACE-Step's {MAX_CAPTION_CHARS}-character "
            "limit (requirement.prompt plus requirement.styleTags"
            + (", plus the loop hints; --no-loop-hints removes those" if loop and not args.no_loop_hints else "")
            + "). Shorten it and re-run."
        )

    # Vocals need words. Generating a 'vocal' track with no lyrics gives
    # wordless mumbling, which reads as a broken backend rather than a missing
    # input, so it is refused here.
    lyrics = requirement.get("lyrics")
    has_lyrics = isinstance(lyrics, str) and lyrics.strip()
    if requirement.get("vocals"):
        if not has_lyrics:
            return user_error(
                f"'{args.slug}' has requirement.vocals set but requirement.lyrics is empty. "
                "Write the lyrics into requirement.lyrics, or set requirement.vocals to false "
                "for an instrumental track."
            )
        lyrics_text = lyrics.strip()
        if len(lyrics_text) > MAX_LYRICS_CHARS:
            return user_error(
                f"requirement.lyrics is {len(lyrics_text)} characters, past ACE-Step's "
                f"{MAX_LYRICS_CHARS}-character limit. Shorten them and re-run."
            )
    else:
        if has_lyrics:
            LOGGER.warning(
                "requirement.lyrics is set but requirement.vocals is false; generating "
                "an instrumental track and ignoring the lyrics."
            )
        lyrics_text = INSTRUMENTAL_MARKER

    requested_duration = float(requirement["durationSeconds"])
    if not MIN_DURATION_SECONDS <= requested_duration <= MAX_DURATION_SECONDS:
        return user_error(
            f"requirement.durationSeconds is {requested_duration:g}s, but ACE-Step 1.5 is "
            f"trained for {MIN_DURATION_SECONDS:g}-{MAX_DURATION_SECONDS:g}s. Adjust the "
            "requirement; for anything shorter than 10s use a sound effect asset with "
            "generate_sa3.py instead."
        )

    try:
        bpm = validate_bpm(requirement.get("bpm"))
        beats = validate_beats(requirement.get("timeSignature"))
    except ValueError as exc:
        return user_error(str(exc))

    # Loop-aware duration: the post stage trims a loop on a downbeat, which is
    # only possible if the generated length is a whole number of bars.
    duration = requested_duration
    loop_snap: dict[str, Any] = {}
    if loop and bpm and beats:
        try:
            bars, duration = snap_to_bars(requested_duration, bpm, beats)
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
            "Loop asset: snapped %.2fs to %d bars (%.3fs) at %d BPM in %s",
            requested_duration,
            bars,
            duration,
            bpm,
            requirement.get("timeSignature"),
        )
    elif loop:
        LOGGER.warning(
            "requirement.loop is set but bpm and timeSignature are not both usable, so the "
            "duration cannot be snapped to whole bars. Set both to get a loop the post "
            "stage can trim on a downbeat."
        )

    model = DEFAULT_MODEL if args.model == "auto" else args.model
    checkpoint = MODELS[model]

    count = args.candidates
    if count is None:
        count = backend.CANDIDATES_BY_MODE[manifest["mode"]]
    if count < 1:
        return user_error(f"--candidates must be at least 1, got {count}")

    # Auto mode is unattended, so a take that cannot loop has to be caught and
    # replaced here. Manual mode annotates instead: a human is about to listen,
    # and burning extra GPU time on their behalf is not the driver's call.
    retry_for_loop = loop and manifest["mode"] == "auto" and args.candidates is None
    budget = MAX_LOOP_CANDIDATES if retry_for_loop else count

    # --out-name-prefix reaches the filesystem, so it is validated as a bare stem:
    # '../evil' or an absolute path would otherwise write outside generate/, and
    # the dry-run ffmpeg call uses -y.
    try:
        _common.validate_name_stem(args.out_name_prefix, "--out-name-prefix")
        backend.validate_seed_range(args.seed, budget)
    except ValueError as exc:
        return user_error(str(exc))

    dry_run = _common.is_dry_run()
    stage = manifest["stages"]["generate"]
    existing = list(stage.get("candidates") or [])
    stage_path = _common.stage_dir(args.slug, "generate", base)
    attempts = int(stage.get("attempts", 0))

    LOGGER.info(
        "%s: model=%s duration=%.2fs candidates=%d %s%s%s",
        args.slug,
        checkpoint,
        duration,
        count,
        "vocals" if lyrics_text != INSTRUMENTAL_MARKER else "instrumental",
        f" reference={reference.name}" if reference else "",
        " [dry-run]" if dry_run else "",
    )

    def generate_round(
        seeds: list[int], names: list[str]
    ) -> tuple[list[dict[str, Any]] | None, int]:
        """One batch of candidates. Returns (produced, exit code on failure)."""
        if dry_run:
            try:
                entries = []
                for seed, name in zip(seeds, names):
                    # 48 kHz, matching what ACE-Step renders, so the post stage
                    # sees the same sample rate it would see after a real run.
                    tail = backend.dry_run_wav(
                        stage_path / name, duration, seed, sample_rate=48000
                    )
                    entries.append(
                        {
                            "output": (stage_path / name).as_posix(),
                            "seed": seed,
                            "leadingSilenceSeconds": 0.0,
                            "trailingSilenceSeconds": tail,
                            "params": {
                                "dryRun": True,
                                "model": checkpoint,
                                "durationSeconds": duration,
                            },
                        }
                    )
            except RuntimeError as exc:
                return None, backend.record_failure(
                    args.slug,
                    backend.FAILURE_USER_ERROR,
                    str(exc),
                    base,
                    LOGGER,
                    (stage_path, names),
                )
            return entries, _common.EXIT_OK

        request = {
            "model": checkpoint,
            "device": args.device,
            # ACE-Step resolves its checkpoint tree from the working directory
            # unless it is told otherwise, and the working directory here is the
            # user's game workspace. Keep the weights in the plugin's private
            # data directory instead, where nothing can commit them.
            "dataDir": _common.stack_data_dir(BACKEND).as_posix(),
            "caption": prompt,
            "lyrics": lyrics_text,
            "instrumental": lyrics_text == INSTRUMENTAL_MARKER,
            "durationSeconds": duration,
            "bpm": bpm,
            # ACE-Step's timesignature field is the bare numerator ("4" for 4/4);
            # the manifest keeps the "N/D" spelling, which is what the bar maths
            # and the recorded params use.
            "timeSignature": str(beats) if beats else "",
            "inferenceSteps": STEPS_BY_MODEL[model],
            "guidanceScale": CFG_BY_MODEL[model],
            "lmNegativePrompt": args.negative_prompt,
            "referenceAudio": reference.as_posix() if reference else None,
            # referenceStrength means "how much of the reference survives", and
            # so does ACE-Step's audio_cover_strength (1.0 = full reference
            # conditioning, lower blends back toward the prompt-only branch), so
            # this one maps straight across with no inversion.
            "referenceStrength": float(requirement["referenceStrength"]) if reference else None,
            "candidates": [
                {"seed": seed, "output": str(stage_path / name)} for seed, name in zip(seeds, names)
            ],
        }
        try:
            payload, stderr_tail = backend.run_worker(
                BACKEND, WORKER, request, WORKER_TIMEOUT_SECONDS, LOGGER
            )
        except RuntimeError as exc:
            return None, backend.record_failure(
                args.slug, backend.FAILURE_USER_ERROR, str(exc), base, LOGGER, (stage_path, names)
            )

        if not payload.get("ok"):
            kind, message = backend.worker_error(payload, stderr_tail)
            return None, backend.record_failure(
                args.slug,
                kind,
                f"ACE-Step failed ({kind}): {message}",
                base,
                LOGGER,
                (stage_path, names),
            )
        runtime = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}
        if not runtime.get("lmModel"):
            # Losing the planner is a real quality drop, and the worker's own
            # warning only reaches captured stderr, so say it here where the
            # user is actually looking.
            LOGGER.warning(
                "The 5Hz LM planner was not used (%s). The DiT rendered from the prompt "
                "alone, which gives less musical structure.",
                runtime.get("lmStatus") or "no detail",
            )
        entries = backend.valid_produced(payload)
        if entries is None:
            return None, backend.record_failure(
                args.slug,
                backend.FAILURE_BACKEND_ERROR,
                "the worker reported success but its result JSON had no usable "
                f"candidate list. Worker output: {stderr_tail or '(none)'}",
                base,
                LOGGER,
                (stage_path, names),
            )
        return entries, _common.EXIT_OK

    started = time.monotonic()
    candidates = list(existing)
    produced: list[dict[str, Any]] = []
    while True:
        # Continue the numbering so a re-run - or a retry - appends instead of
        # overwriting earlier takes. Failed-for-loop candidates stay on disk and
        # in the manifest: they may still be the best thing available.
        names = [
            f"{args.out_name_prefix}-{len(existing) + len(produced) + index + 1:02d}.wav"
            for index in range(count)
        ]
        try:
            for name in names:
                _common.assert_inside(stage_path / name, stage_path, "candidate output")
        except ValueError as exc:
            return user_error(str(exc))

        attempts += 1
        _manifest.update_stage(
            args.slug,
            "generate",
            {
                "status": "in_progress",
                "backend": BACKEND,
                "attempts": attempts,
                "failureKind": None,
            },
            base,
        )

        seeds = backend.make_seeds(
            count, None if args.seed is None else args.seed + len(produced)
        )
        entries, code = generate_round(seeds, names)
        if entries is None:
            return code

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
            params = backend.candidate_params(entry, loop_snap, loop=loop)
            if loop_snap:
                params["timeSignature"] = requirement.get("timeSignature")
            fresh.append(
                _manifest.make_candidate(f"generate/{name}", entry["seed"], BACKEND, params)
            )

        produced.extend(entries)
        candidates.extend(fresh)
        # Persist after every round so a later failure cannot lose earlier takes.
        _manifest.update_stage(args.slug, "generate", {"candidates": candidates}, base)

        if not retry_for_loop:
            break
        if any(candidate["params"].get("loopViable") is not False for candidate in fresh):
            break
        if len(produced) >= budget:
            break
        # ponytail: each retry is a fresh worker process, so it pays the model
        # load again (a minute or two) on top of the generation. Keeping the
        # worker alive across rounds would mean moving the loop policy into it;
        # revisit only if retries stop being the exception.
        LOGGER.warning(
            "Candidate %s carries %.2fs of silence at the start and %.2fs at the end, "
            "which would be audible at the loop point. Retrying with a fresh seed "
            "(%d of %d).",
            pathlib.Path(entries[-1]["output"]).name,
            float(fresh[-1]["params"].get("leadingSilenceSeconds") or 0.0),
            float(fresh[-1]["params"].get("trailingSilenceSeconds") or 0.0),
            len(produced) + 1,
            budget,
        )
        count = 1

    elapsed = time.monotonic() - started

    _manifest.update_stage(
        args.slug,
        "generate",
        {"status": "done", "candidates": candidates, "failureKind": None},
        base,
    )

    print("")
    print(
        f"Generated {len(produced)} candidate(s) for '{args.slug}' with "
        f"{BACKEND}/{checkpoint} in {elapsed:.1f}s"
    )
    new_candidates = candidates[len(existing):]
    for entry, candidate in zip(produced, new_candidates):
        line = f"  generate/{pathlib.Path(entry['output']).name}  seed={entry['seed']}"
        line += backend.silence_note(candidate["params"])
        if entry.get("warning"):
            line += f"  WARNING: {entry['warning']}"
        print(line)
    if loop and not any(c["params"].get("loopViable") is not False for c in new_candidates):
        best = min(
            new_candidates,
            key=lambda c: float(c["params"].get("trailingSilenceSeconds") or 0.0),
        )
        print("")
        print(
            f"WARNING: no candidate is loop-viable - every take carries more than "
            f"{backend.LOOP_SILENCE_LIMIT_SECONDS:g}s of dead air at one end. Closest is "
            f"{best['file']} (lead "
            f"{float(best['params'].get('leadingSilenceSeconds') or 0.0):.2f}s, tail "
            f"{float(best['params'].get('trailingSilenceSeconds') or 0.0):.2f}s)."
        )
        print(
            "The music likely ended before the requested bar count. Shorten "
            "requirement.durationSeconds toward where the content actually stops, or "
            "accept a shorter loop - the post stage trims to the last contentful bar."
        )
    if loop_snap:
        print(
            f"Loop: {loop_snap['bars']} bars at {loop_snap['bpm']} BPM "
            f"({loop_snap['barSnappedDurationSeconds']:g}s for a "
            f"{loop_snap['requestedDurationSeconds']:g}s request)"
        )
    print(f"Files: {stage_path.as_posix()}")
    print("Next: listen to the candidates, then record the chosen one as stages.generate.selected.")
    return _common.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
