"""Driver-side helpers shared by the generate-stage backends.

Everything here runs in the ORDINARY system Python next to `_common` and
`_manifest` - never inside a stack's virtual environment. The venv-side half of
the protocol lives in `_worker_common.py`.

The pieces below were identical in every backend driver: the structured failure
vocabulary, the request/result JSON protocol, the partial-file naming, the
dry-run synthesizer, and the cleanup/record-failure pair. Backend-specific
routing, prompt shaping and parameter mapping stay in the individual drivers.
"""

from __future__ import annotations

import json
import logging
import math
import os
import pathlib
import random
import shutil
import tempfile
from typing import Any

import _common
import _manifest


# Structured failure vocabulary recorded in stages.generate.failureKind. Every
# backend uses these names so the skills can document one table.
FAILURE_USER_ERROR = "user_error"
FAILURE_TIMEOUT = "timeout"
FAILURE_BACKEND_ERROR = "backend_error"
WORKER_FAILURE_KINDS = (
    FAILURE_USER_ERROR,
    "missing_flash_attn",
    "oom",
    "model_download_failed",
    FAILURE_BACKEND_ERROR,
)

# torch.manual_seed accepts a 64-bit value, but seeds travel through JSON, file
# names and manifests; 2**32-1 is the widest bound that is safe everywhere.
MAX_SEED = 2**32 - 1

# Mirrors _worker_common.partial_path: a worker writes each candidate to
# ".<stem>.tmp.wav" and renames it into place, so a failed attempt can leave one
# behind. The temp name keeps the .wav extension because torchaudio picks the
# container format from it.
PARTIAL_INFIX = ".tmp"

# How many candidates to produce when the user does not say. Manual mode is the
# "pick your favourite" workflow; auto mode takes the first result and moves on.
CANDIDATES_BY_MODE = {"manual": 3, "auto": 1}

# Per-candidate measurements the workers report alongside their own params.
SILENCE_KEYS = _common.SILENCE_PARAM_KEYS
CANDIDATE_METRIC_KEYS = ("generationSeconds", "actualDurationSeconds", *SILENCE_KEYS)

# Dead air a looping asset can carry before the seam is audible in engine. Under
# this the post stage's downbeat trim absorbs it; over it, the track has simply
# ended early and looping it would play a gap on every wrap. 0.75 s is under half
# a bar at any tempo this pipeline targets, so it cannot be mistaken for a rest.
LOOP_SILENCE_LIMIT_SECONDS = 0.75


def loop_viable(params: dict[str, Any]) -> bool:
    """False when a candidate carries enough dead air to break a loop.

    Unmeasured candidates count as viable: absence of a measurement is not
    evidence of a gap, and the manual workflow still puts the numbers in front
    of a human.
    """
    for key in SILENCE_KEYS:
        value = params.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if value > LOOP_SILENCE_LIMIT_SECONDS:
                return False
    return True


def beats_per_bar(time_signature: Any) -> int | None:
    """Beats per bar from a "4/4"-style signature, or None when unusable.

    The numerator is the beat count per bar, and the music backends treat BPM as
    the rate of the denominator's note value, so numerator beats really do make
    one bar. A bare number ("4") is accepted too: that is ACE-Step's own
    spelling of the same field.
    """
    numerator = str(time_signature or "").split("/")[0].strip()
    if not numerator.isdigit():
        return None
    beats = int(numerator)
    return beats if beats > 0 else None


def snap_to_bars(
    duration: float, bpm: float, beats: int, minimum: float, maximum: float
) -> tuple[int, float]:
    """Round a duration to a whole number of bars. Returns (bars, seconds).

    A loop that ends mid-bar cannot be trimmed to a downbeat by the post stage
    without either dropping musical content or leaving a rhythmic hiccup at the
    seam, so the bar count is fixed here, before generation.

    `minimum`/`maximum` are the calling backend's own accepted duration range.
    The feasible bar counts are the integers whose length lands inside it, and
    the answer is the nearest one to `duration`; when the interval is too narrow
    to hold a single whole bar this raises ValueError, which every caller turns
    into a user_error naming the tempo and the duration.

    Closed form rather than stepping one bar at a time: at 300 BPM a six-minute
    ceiling is already thousands of bars, and a backend that accepts an
    unbounded tempo (MiniMax takes the requirement's bpm as caption text) would
    otherwise spin for millions of iterations before returning.
    """
    if not (math.isfinite(bpm) and bpm > 0):
        raise ValueError(f"bpm must be a finite positive number, got {bpm!r}")
    if not (isinstance(beats, int) and not isinstance(beats, bool) and beats > 0):
        raise ValueError(f"beats per bar must be a positive whole number, got {beats!r}")
    if not (math.isfinite(duration) and duration > 0):
        raise ValueError(f"duration must be a finite positive number, got {duration!r}")
    if not (math.isfinite(minimum) and math.isfinite(maximum) and 0 < minimum <= maximum):
        raise ValueError(
            f"the backend's duration range is unusable: minimum={minimum!r} maximum={maximum!r}"
        )

    seconds_per_bar = 60.0 * beats / bpm
    lowest = max(1, math.ceil(minimum / seconds_per_bar))
    highest = math.floor(maximum / seconds_per_bar)
    if lowest > highest:
        raise ValueError(
            f"no whole number of bars fits between {minimum:g}s and {maximum:g}s at "
            f"{bpm:g} BPM with {beats} beats per bar (one bar is "
            f"{seconds_per_bar:g}s). Change requirement.bpm or "
            "requirement.timeSignature, or clear requirement.loop so the duration "
            "is used as written."
        )

    bars = min(highest, max(lowest, round(duration / seconds_per_bar)))
    return bars, bars * seconds_per_bar


def candidate_params(
    entry: dict[str, Any],
    extra: dict[str, Any] | None = None,
    loop: bool = False,
) -> dict[str, Any]:
    """Merge a worker's params with its measurements and the driver's own fields."""
    params = dict(entry.get("params") or {})
    for key in CANDIDATE_METRIC_KEYS:
        if entry.get(key) is not None:
            params[key] = entry[key]
    params.update(extra or {})
    if loop:
        params["loopViable"] = loop_viable(params)
    return params


def silence_note(params: dict[str, Any]) -> str:
    """Trailing text for a candidate's summary line, empty when unmeasured."""
    values = [params.get(key) for key in SILENCE_KEYS]
    if all(value is None for value in values):
        return ""
    lead, tail = (0.0 if value is None else float(value) for value in values)
    note = f"  silence lead={lead:.2f}s tail={tail:.2f}s"
    if params.get("loopViable") is False:
        note += "  NOT LOOP-VIABLE"
    return note


def partial_name(name: str) -> str:
    stem, _, suffix = name.rpartition(".")
    return f".{stem}{PARTIAL_INFIX}.{suffix}"


def build_prompt(requirement: dict[str, Any]) -> str:
    """requirement.prompt with requirement.styleTags appended, comma separated."""
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


def test_silent_tail() -> float:
    """Seconds of trailing silence the dry run should fake, from the test hook.

    AUDIO_PIPELINE_TEST_SILENT_TAIL exists so the loop-viability policy can be
    exercised without a GPU: it is read by the tests and by nothing else, and it
    is deliberately undocumented in the skills.
    """
    raw = os.environ.get("AUDIO_PIPELINE_TEST_SILENT_TAIL", "").strip()
    if not raw:
        return 0.0
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 0.0


def dry_run_wav(target: pathlib.Path, duration: float, seed: int, sample_rate: int = 44100) -> float:
    """Synthesize a placeholder tone. Returns the seconds of silence at its end.

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
    # Leave at least a tenth of a second of tone: an all-silent placeholder is
    # indistinguishable from a broken generation.
    tail = min(test_silent_tail(), max(0.0, duration - 0.1))
    content = duration - tail
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency={frequency}:sample_rate={sample_rate}:duration={content:.3f}",
        "-ac",
        "2",
        "-c:a",
        "pcm_s16le",
    ]
    if tail > 0:
        command += ["-af", f"apad=whole_dur={duration:.3f}"]
    result = _common.run([*command, "-y", str(target)], timeout=120)
    if result.returncode != 0 or not target.is_file():
        raise RuntimeError(f"ffmpeg could not write {target.as_posix()}: {result.stderr.strip()[-500:]}")
    return round(tail, 2)


def run_worker(
    stack: str,
    worker: pathlib.Path,
    request: dict[str, Any],
    timeout: float,
    logger: logging.Logger,
) -> tuple[dict[str, Any], str]:
    """Run a venv-side worker once. Returns (result payload, stderr tail).

    Never raises for a backend failure: everything the caller needs to record a
    structured failureKind comes back in the payload.
    """
    python = _common.venv_python(stack)
    if not python.exists():
        raise RuntimeError(
            f"The {stack} environment is missing ({python.as_posix()}). Run "
            f"`python setup_env.py --stack {stack}`, then `python doctor.py --stack {stack}`."
        )

    with tempfile.TemporaryDirectory(prefix=f"{stack}-request-") as tmp:
        request_path = pathlib.Path(tmp) / "request.json"
        result_path = pathlib.Path(tmp) / "result.json"
        request = {**request, "resultPath": str(result_path)}
        request_path.write_text(json.dumps(request, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")

        logger.info("Running the %s worker (timeout %.0f min)", stack, timeout / 60)
        # Hands the worker any HF_TOKEN kept in the plugin's private .env so
        # gated weights can be fetched. Values are secrets: never logged, never
        # written to the manifest.
        completed = _common.run(
            [python, worker, "--request", request_path],
            timeout=timeout,
            env=_common.subprocess_env(),
        )
        stderr_tail = (completed.stderr or "").strip()[-2000:]
        try:
            payload = _common.read_json(result_path)
        except ValueError as exc:
            # Corrupt result JSON is still a backend failure, not a driver crash.
            logger.warning("worker result file was unreadable: %s", exc)
            payload = None

    if payload is None:
        if completed.returncode == _common.EXIT_TIMEOUT:
            return {"ok": False, "error": {"kind": FAILURE_TIMEOUT, "message": stderr_tail}}, stderr_tail
        return (
            {
                "ok": False,
                "error": {
                    "kind": FAILURE_BACKEND_ERROR,
                    "message": f"the worker exited {completed.returncode} without writing a result",
                },
            },
            stderr_tail,
        )
    if not isinstance(payload, dict):
        return (
            {
                "ok": False,
                "error": {"kind": FAILURE_BACKEND_ERROR, "message": "the worker result was not an object"},
            },
            stderr_tail,
        )
    return payload, stderr_tail


def worker_error(payload: dict[str, Any], stderr_tail: str) -> tuple[str, str]:
    """Normalize a failed worker payload into (failureKind, message)."""
    error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    kind = error.get("kind")
    if kind not in (*WORKER_FAILURE_KINDS, FAILURE_TIMEOUT):
        kind = FAILURE_BACKEND_ERROR
    message = error.get("message") or stderr_tail or "the worker reported no detail"
    return kind, message


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


def cleanup_attempt(stage_path: pathlib.Path, names: list[str], logger: logging.Logger) -> None:
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
                logger.warning("could not remove %s: %s", leftover.as_posix(), exc)


def record_failure(
    slug: str,
    kind: str,
    message: str,
    base: pathlib.Path | None,
    logger: logging.Logger,
    cleanup: tuple[pathlib.Path, list[str]] | None = None,
) -> int:
    """Mark the generate stage failed, clean up this attempt, return an exit code."""
    if cleanup is not None:
        cleanup_attempt(*cleanup, logger)
    _manifest.update_stage(slug, "generate", {"status": "failed", "failureKind": kind}, base)
    logger.error("%s", message)
    code = _common.EXIT_TIMEOUT if kind == FAILURE_TIMEOUT else _common.EXIT_BACKEND_ERROR
    return _common.EXIT_USER_ERROR if kind in {FAILURE_USER_ERROR, "missing_flash_attn"} else code
