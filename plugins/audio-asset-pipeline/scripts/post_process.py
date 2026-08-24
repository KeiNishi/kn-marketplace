"""Stage `post`: trim, loop, normalize and export one audio asset.

Stdlib only. Every sample of DSP is done by ffmpeg; this script decides *where*
the cuts go and verifies what came back. Run it with the ordinary system Python
from the workspace that contains `audio-pipeline-output/` - it never touches a
generation venv, torch or numpy.

Usage:
    python post_process.py <slug>
    python post_process.py <slug> --candidate generate/cand-03.wav
    python post_process.py <slug> --crossfade-ms 50 --target-rate 44100
    python post_process.py <slug> --skip-loop --skip-normalize
    python post_process.py --selftest

Set AUDIO_PIPELINE_DRY_RUN=1 to print the plan and touch nothing. (On Windows,
use `py -3` if `python3` is not available.)

Why ffmpeg rather than Python for the audio itself: every candidate this
pipeline produces is 32-bit float WAV, and the stdlib `wave` module refuses
those outright ("unknown format: 3"), so there is no stdlib path to the samples
in the first place. ffmpeg's `atrim` takes `start_sample`/`end_sample` and
`acrossfade` takes `ns`, so all of the cutting is already sample-exact without a
line of Python DSP. Python reads raw `f32le` back through a pipe only where it
has to look at individual samples: snapping a cut to a zero crossing, and
measuring the loop seam.
"""

from __future__ import annotations

import argparse
import array
import contextlib
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Iterator, Sequence

_SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent
for _extra in (_SCRIPTS_DIR, _SCRIPTS_DIR / "backends"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import _common  # noqa: E402
import _manifest  # noqa: E402
import _backend_common as backend  # noqa: E402


LOGGER = _common.setup_logger("audio-post")

# Same dead-air definition the generation workers used (`_worker_common.
# measure_silence`): 50 ms RMS windows at -45 dBFS. Deliberately NOT ffmpeg's
# `silencedetect`, which compares raw sample magnitudes instead of RMS and
# therefore disagrees with the numbers already recorded in the manifest - on the
# measured MiniMax take it saw no leading silence at all where the worker
# recorded 0.50 s. The post stage must trim to the same boundary the generate
# stage reported, so it reproduces the same measurement.
SILENCE_THRESHOLD_DBFS = -45.0
SILENCE_WINDOW_SECONDS = 0.05

# Non-loop assets keep this much room tone after the last audible window, so a
# reverb tail decays into the file instead of being cut off dead. It is 4 windows
# of the measurement above: long enough to hold the inaudible end of a decay,
# short enough that a one-shot triggered in engine does not feel late.
NONLOOP_TAIL_KEEP_SECONDS = 0.2
# A one-shot's content bound is measured against the take's OWN level, not the
# absolute floor above. The absolute -45 dBFS figure exists to find dead air in a
# peak-normalized music take; on an unnormalized sound effect it lands inside the
# decay. The measured Stable Audio 3 door creak peaks at -30 dBFS and its creak
# tail sits at -50 dBFS, so an absolute cut removed 0.95 s of audible decay.
# 40 dB below the loudest window is 1% of its amplitude - inaudible under a game
# mix, and low enough to keep a real reverb tail. Whichever of the two floors is
# lower wins, so this never trims MORE than the absolute rule would.
DECAY_RANGE_DB = 40.0
# Leading silence under this is left alone on a non-loop asset: a short pre-roll
# is often the attack transient's own build-up, and trimming it changes the
# sound. Over half a second it is dead air the engine would have to compensate
# for on every trigger.
NONLOOP_LEAD_TRIM_SECONDS = 0.5

# Equal-power crossfade over the loop seam. 30 ms is about one cycle of 33 Hz,
# so it covers the lowest musical fundamental a game mix carries while staying
# far shorter than a sixteenth note at any tempo this pipeline targets.
DEFAULT_CROSSFADE_MS = 30
MIN_CROSSFADE_MS = 10
MAX_CROSSFADE_MS = 80
# `qsin` is a quarter sine, i.e. cos/sin on the two sides: constant total power
# across the fade, which is what keeps the seam from dipping in level.
CROSSFADE_CURVE = "qsin"

# How far a cut may move to land on a zero crossing. 10 ms is inaudible as a
# timing shift and reaches a crossing of anything above 50 Hz.
ZERO_SNAP_SECONDS = 0.010

# Loudness. -1.0 dBTP leaves headroom for the intersample peaks that appear when
# a lossy codec (or a resampler) reconstructs the waveform, which is why it is
# applied even when normalization is skipped: a 16-bit or Vorbis export made
# from a master sitting at 0 dBTP clips on decode.
TRUE_PEAK_CEILING_DBTP = -1.0
# EBU R128 loudness range target. 11 LU is ffmpeg's default and the usual value
# for music; the linear mode used below does not compress toward it, it only
# reports it.
LOUDNESS_RANGE_LU = 11.0
# How far the measured output may sit above the ceiling before a corrective gain
# is applied. 0.05 dB is below the repeatability of the true-peak estimator.
TRUE_PEAK_TOLERANCE_DB = 0.05
# R128 integrated loudness gates in 400 ms blocks; under about 3 s of programme
# the figure is dominated by the gate and is only indicative.
SHORT_PROGRAMME_SECONDS = 3.0

# Vorbis quality 6 is roughly 192 kbps VBR - the point where libvorbis stops
# being distinguishable from the source on game material, and the usual ceiling
# before the file size stops being worth it against shipping WAV.
OGG_QUALITY = 6
SUPPORTED_FORMATS = ("wav", "ogg")
# Only rates the three backends actually render at, so a typo cannot silently
# resample a whole soundtrack to something no engine wants.
SUPPORTED_TARGET_RATES = (44100, 48000)

# Loop seam check: the last and first slice of the finished loop, joined.
SEAM_WINDOW_SECONDS = 0.1
# The join may not be a bigger jump than the biggest jump inside the audio
# either side of it. Equal at 1.0; anything under is a seam that is smoother
# than the music around it.
SEAM_RATIO_LIMIT = 1.0


class PostError(Exception):
    """A failure that maps onto the pipeline's structured failureKind vocabulary."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


def user_error(message: str) -> PostError:
    return PostError(backend.FAILURE_USER_ERROR, message)


def backend_error(message: str) -> PostError:
    return PostError(backend.FAILURE_BACKEND_ERROR, message)


# --------------------------------------------------------------------------- #
# ffmpeg plumbing
# --------------------------------------------------------------------------- #


def _tool(name: str) -> str:
    found = shutil.which(name)
    if found is None:
        raise user_error(
            f"{name} is required by the post stage but is not on PATH. Install ffmpeg "
            "(it ships ffprobe too) and re-run; `python doctor.py` checks for it."
        )
    return found


def run_ffmpeg(args: Sequence[Any], *, verbose: bool = False) -> str:
    """Run ffmpeg and return its stderr. Raises PostError on a non-zero exit.

    `verbose` keeps av_log at INFO, which is the only level at which the
    loudnorm filter prints its measurement JSON.
    """
    command = [_tool("ffmpeg"), "-hide_banner", "-nostdin", "-nostats", "-v", "info" if verbose else "error"]
    result = _common.run([*command, *args])
    if result.returncode != 0:
        raise backend_error(
            f"ffmpeg failed ({result.returncode}): {' '.join(str(part) for part in args)}\n"
            f"{(result.stderr or result.stdout or '').strip()[-1200:]}"
        )
    return result.stderr or ""


def run_ffmpeg_stdout(args: Sequence[Any]) -> str:
    """Run ffmpeg and return its stdout (used by the `ametadata` printer)."""
    command = [_tool("ffmpeg"), "-hide_banner", "-nostdin", "-nostats", "-v", "error"]
    result = _common.run([*command, *args])
    if result.returncode != 0:
        raise backend_error(
            f"ffmpeg failed ({result.returncode}): {' '.join(str(part) for part in args)}\n"
            f"{(result.stderr or '').strip()[-1200:]}"
        )
    return result.stdout or ""


@contextlib.contextmanager
def atomic_output(target: pathlib.Path) -> Iterator[pathlib.Path]:
    """Yield a unique sibling temp path, then move it onto `target` on success.

    Every shipped artifact goes through this. ffmpeg is invoked with `-y`, so
    writing straight to the final name means a failed or interrupted encode
    truncates the file a previous good run produced - and the manifest would
    still be pointing at it. The staging name is unique per call, so two runs
    cannot collide on it either.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(
        dir=str(target.parent), prefix=f".{target.stem}.", suffix=target.suffix
    )
    os.close(handle)
    staged = pathlib.Path(name)
    try:
        yield staged
        if not staged.is_file() or staged.stat().st_size == 0:
            raise backend_error(f"nothing was written for {target.name}; leaving the previous file alone")
        try:
            os.replace(staged, target)
        except OSError as exc:
            # Locked by a player, read-only, no space, or something else sitting
            # at that name. The previous file is still whatever it was.
            raise backend_error(
                f"could not put {target.name} in place: {exc}. The previous file was left alone."
            ) from exc
    except BaseException:
        staged.unlink(missing_ok=True)
        raise


def read_frames(source: pathlib.Path, start: int, end: int, channels: int) -> list[list[float]]:
    """Decode samples [start, end) as f32le and return one list per channel.

    `atrim` with sample indices rather than an input seek: the windows read here
    are tens of milliseconds wide and a seek that lands on the wrong side of the
    boundary would silently move a cut.
    """
    if end <= start:
        return [[] for _ in range(channels)]
    command = [
        _tool("ffmpeg"),
        "-hide_banner",
        "-nostdin",
        "-nostats",
        "-v",
        "error",
        "-i",
        str(source),
        "-af",
        f"atrim=start_sample={start}:end_sample={end}",
        "-f",
        "f32le",
        "-acodec",
        "pcm_f32le",
        "-",
    ]
    # subprocess.run raises rather than returning a status for these, and the
    # stage is already `in_progress` by the time this runs: letting either
    # escape would leave the manifest stuck there instead of recording a
    # failure. `_common.run` is not usable here - it decodes stdout as text.
    try:
        completed = subprocess.run(command, capture_output=True, timeout=600)
    except subprocess.TimeoutExpired as exc:
        raise PostError(
            backend.FAILURE_TIMEOUT,
            f"reading samples {start}-{end} of {source.name} timed out after {exc.timeout:.0f}s",
        ) from exc
    except OSError as exc:
        raise backend_error(f"could not start ffmpeg to read {source.name}: {exc}") from exc

    if completed.returncode != 0:
        raise backend_error(
            f"ffmpeg could not read samples {start}-{end} of {source.name}: "
            f"{completed.stderr.decode('utf-8', 'replace').strip()[-800:]}"
        )
    payload = completed.stdout
    frame_bytes = channels * array.array("f").itemsize
    if not payload or len(payload) % frame_bytes:
        # A short or ragged pipe means the decode was cut off. Silently rounding
        # it down would hand back frames that are one channel out of alignment,
        # which reads as a plausible waveform and a wrong cut.
        raise backend_error(
            f"ffmpeg returned {len(payload)} bytes for samples {start}-{end} of "
            f"{source.name}, which is not a whole number of {channels}-channel frames"
        )
    samples = array.array("f")
    samples.frombytes(payload)
    if sys.byteorder != "little":  # the pipe is f32le regardless of the host
        samples.byteswap()
    return [list(samples[channel::channels]) for channel in range(channels)]


def probe(source: pathlib.Path) -> dict[str, Any]:
    """Sample rate, channel count and exact sample length of an audio file."""
    result = _common.run(
        [
            _tool("ffprobe"),
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=sample_rate,channels,duration_ts,time_base",
            "-of",
            "json",
            str(source),
        ],
        timeout=120,
    )
    if result.returncode != 0:
        raise user_error(f"ffprobe could not read {source.as_posix()}: {result.stderr.strip()[-400:]}")
    try:
        streams = json.loads(result.stdout or "{}").get("streams") or []
    except json.JSONDecodeError as exc:
        raise backend_error(f"ffprobe returned unreadable JSON for {source.name}: {exc}") from exc
    if not streams:
        raise user_error(f"{source.as_posix()} has no audio stream.")

    stream = streams[0]
    rate = int(stream["sample_rate"])
    channels = int(stream["channels"])
    numerator, _, denominator = str(stream.get("time_base") or f"1/{rate}").partition("/")
    ticks = int(stream.get("duration_ts") or 0)
    samples = int(round(ticks * (int(numerator) / int(denominator or 1)) * rate))
    if rate <= 0 or channels <= 0 or samples <= 0:
        raise user_error(
            f"{source.as_posix()} reports an unusable stream "
            f"({rate} Hz, {channels} ch, {samples} samples)."
        )
    return {"rate": rate, "channels": channels, "samples": samples, "seconds": samples / rate}


# --------------------------------------------------------------------------- #
# Measurement
# --------------------------------------------------------------------------- #


_RMS_KEY = re.compile(r"lavfi\.astats\.(\d+)\.RMS_level=(\S+)")


def rms_envelope(source: pathlib.Path, rate: int) -> list[float]:
    """dBFS per 50 ms window, in order. Digital silence reads as -inf.

    Per channel, combined with max() - exactly what `_worker_common.
    measure_silence` does, and the reason the per-channel keys are read instead
    of `Overall.RMS_level`. Overall pools the energy of every channel, so a
    window with content in one channel only measures about 3 dB lower than the
    workers recorded it, which is enough to move a boundary that sits near the
    -45 dBFS threshold.
    """
    window = max(1, int(round(SILENCE_WINDOW_SECONDS * rate)))
    stdout = run_ffmpeg_stdout(
        [
            "-i",
            str(source),
            "-af",
            f"asetnsamples=n={window}:p=0,"
            "astats=metadata=1:reset=1:measure_overall=none:measure_perchannel=RMS_level,"
            "ametadata=mode=print:file=-",
            "-f",
            "null",
            "-",
        ]
    )
    levels: list[float] = []
    window_max = -math.inf
    started = False
    for line in stdout.splitlines():
        if line.startswith("frame:"):
            if started:
                levels.append(window_max)
            started, window_max = True, -math.inf
            continue
        match = _RMS_KEY.search(line)
        if match:
            try:
                window_max = max(window_max, float(match.group(2)))
            except ValueError:  # "-inf" on a digitally silent channel
                pass
    if started:
        levels.append(window_max)
    return levels


def decay_threshold(levels: Sequence[float]) -> float:
    """dBFS floor for a one-shot's TAIL, relative to that take's own body.

    Only the tail gets this. A leading pre-roll is dead air - nothing decays
    into the first sample - so it keeps the absolute floor, which is also the
    figure the generation workers recorded `leadingSilenceSeconds` with.
    """
    loudest = max((level for level in levels if math.isfinite(level)), default=-math.inf)
    if not math.isfinite(loudest):
        return SILENCE_THRESHOLD_DBFS
    return min(SILENCE_THRESHOLD_DBFS, loudest - DECAY_RANGE_DB)


def content_bounds(
    levels: Sequence[float], rate: int, total: int, threshold: float
) -> tuple[int, int] | None:
    """First and last contentful sample as [start, end), or None if nothing is."""
    window = max(1, int(round(SILENCE_WINDOW_SECONDS * rate)))
    loud = [index for index, level in enumerate(levels) if level > threshold]
    if not loud:
        return None
    return min(loud[0] * window, total), min((loud[-1] + 1) * window, total)


def snap_zero(source: pathlib.Path, target: int, channels: int, rate: int, total: int) -> int:
    """Move `target` to the nearest zero crossing within +/-10 ms.

    The crossing is looked for in the channel sum: a stereo pair rarely crosses
    zero on the same sample, and the sum is what a click would be audible in. If
    the window holds no crossing at all (a sustained offset, or the file edge),
    the quietest sample in it is used instead - still the least clicky cut
    available.
    """
    window = max(1, int(round(ZERO_SNAP_SECONDS * rate)))
    start = max(0, target - window)
    end = min(total, target + window)
    if end - start < 2:
        return max(0, min(target, total))

    frames = read_frames(source, start, end, channels)
    if not frames or not frames[0]:
        return max(0, min(target, total))
    mono = [sum(values) for values in zip(*frames)]

    crossings = [
        index
        for index in range(1, len(mono))
        if (mono[index - 1] <= 0.0 < mono[index]) or (mono[index - 1] >= 0.0 > mono[index])
    ]
    if crossings:
        best = min(crossings, key=lambda index: abs(start + index - target))
    else:
        best = min(range(len(mono)), key=lambda index: (abs(mono[index]), abs(start + index - target)))
    return start + best


def measure_loudness(source: pathlib.Path, target_lufs: float) -> dict[str, float]:
    """EBU R128 figures for a file: integrated, true peak, range and threshold.

    This is loudnorm's own analysis pass, so the numbers are exactly what the
    correction pass will act on - and running it again on the *output* is how
    the result is verified rather than assumed.
    """
    stderr = run_ffmpeg(
        [
            "-i",
            str(source),
            "-af",
            f"loudnorm=I={target_lufs}:TP={TRUE_PEAK_CEILING_DBTP}:LRA={LOUDNESS_RANGE_LU}"
            ":print_format=json",
            "-f",
            "null",
            "-",
        ],
        verbose=True,
    )
    payload = _last_json_object(stderr)
    if payload is None:
        raise backend_error(
            f"loudnorm printed no measurement for {source.name}. ffmpeg said:\n{stderr.strip()[-800:]}"
        )
    figures: dict[str, float] = {}
    for key in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset"):
        try:
            figures[key] = float(payload[key])
        except (KeyError, TypeError, ValueError):
            raise backend_error(f"loudnorm measurement for {source.name} is missing {key}: {payload}")
    return figures


def _last_json_object(text: str) -> dict[str, Any] | None:
    """The last {...} block in ffmpeg's log output."""
    end = text.rfind("}")
    while end != -1:
        start = text.rfind("{", 0, end)
        if start == -1:
            return None
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            end = text.rfind("}", 0, end)
            continue
        return parsed if isinstance(parsed, dict) else None
    return None


def seam_metric(source: pathlib.Path, rate: int, channels: int, total: int) -> dict[str, Any]:
    """Discontinuity at the loop wrap, relative to the audio either side of it.

    Renders what the engine will actually hear - the last 100 ms followed
    immediately by the first 100 ms - and compares the one sample-to-sample step
    that spans the join against the largest step inside either half.
    """
    window = min(max(1, int(round(SEAM_WINDOW_SECONDS * rate))), total // 2)
    tail = read_frames(source, total - window, total, channels)
    head = read_frames(source, 0, window, channels)
    if not tail or not tail[0] or not head or not head[0]:
        raise backend_error(f"could not read the loop boundary of {source.name}")

    joined = [list(tail_channel) + list(head_channel) for tail_channel, head_channel in zip(tail, head)]
    boundary = len(tail[0])
    seam = max(abs(channel[boundary] - channel[boundary - 1]) for channel in joined)
    inside = max(
        (
            abs(channel[index] - channel[index - 1])
            for channel in joined
            for index in range(1, len(channel))
            if index != boundary
        ),
        default=0.0,
    )
    ratio = seam / inside if inside > 0 else (0.0 if seam == 0 else math.inf)
    return {
        "seamDeltaPeak": round(seam, 6),
        "segmentDeltaPeak": round(inside, 6),
        "seamRatio": round(ratio, 3) if math.isfinite(ratio) else None,
        "seamOk": ratio <= SEAM_RATIO_LIMIT,
        "windowSeconds": round(window / rate, 3),
    }


# --------------------------------------------------------------------------- #
# Planning
# --------------------------------------------------------------------------- #


def resolve_source(
    manifest: dict[str, Any], requested: str | None
) -> tuple[str, dict[str, Any] | None]:
    """Pick the candidate to process. Returns (relative path, candidate entry)."""
    generate = manifest["stages"]["generate"]
    candidates = [entry for entry in (generate.get("candidates") or []) if isinstance(entry, dict)]
    by_file = {entry.get("file"): entry for entry in candidates}

    if requested is not None:
        wanted = _common.relative_artifact_path(requested, "--candidate")
        if wanted not in by_file:
            raise user_error(
                f"--candidate {requested!r} is not one of this asset's candidates.\n"
                + _candidate_listing(candidates)
            )
        return wanted, by_file[wanted]

    selected = generate.get("selected")
    if selected:
        if selected not in by_file:
            raise user_error(
                f"stages.generate.selected points at {selected!r}, which is not in "
                "stages.generate.candidates. Fix the manifest or pass --candidate."
            )
        return selected, by_file[selected]

    if len(candidates) == 1:
        return candidates[0]["file"], candidates[0]

    if not candidates:
        raise user_error(
            "This asset has no candidates yet. Run the generate stage first "
            "(generate_acestep.py, generate_minimax.py or generate_sa3.py)."
        )
    raise user_error(
        f"{len(candidates)} candidates and no stages.generate.selected. Listen to them, "
        "then re-run with --candidate <file> (or record the choice in the manifest).\n"
        + _candidate_listing(candidates)
    )


def resolve_inside(asset_dir: pathlib.Path, relative: str) -> pathlib.Path:
    """Resolve a manifest-relative path and prove it landed inside the asset dir.

    `relative_artifact_path` already rejected drive letters, leading separators
    and '..' in the string. This checks where the path actually LANDS, which is
    the only thing that catches a symlink or junction sitting inside the asset
    directory and pointing out of it.
    """
    root = asset_dir.resolve()
    resolved = (asset_dir / relative).resolve()
    if root not in resolved.parents:
        raise user_error(
            f"the selected candidate resolves outside the asset directory: "
            f"{resolved.as_posix()} is not under {root.as_posix()}"
        )
    return resolved


def _candidate_listing(candidates: Iterable[dict[str, Any]]) -> str:
    lines = []
    for entry in candidates:
        params = entry.get("params") or {}
        lines.append(
            f"  {entry.get('file')}  seed={entry.get('seed')}  "
            f"backend={entry.get('backend')}{backend.silence_note(params)}"
        )
    return "\n".join(lines) or "  (none)"


def resolve_tempo(
    requirement: dict[str, Any], candidate: dict[str, Any] | None, override_bpm: float | None
) -> tuple[float | None, int | None, str | None]:
    """(bpm, beatsPerBar, source) for bar snapping, or (None, None, None).

    Only ACE-Step actually renders to the tempo it was handed. MiniMax takes BPM
    as caption text and is documented not to honour it, and Stable Audio 3 has no
    tempo control at all, so `requirement.bpm` on those is an annotation - using
    it for bar math would cut on a grid the audio was never on. Those fall back
    to a silence-boundary cut unless the user states a tempo they measured.
    """
    params = (candidate or {}).get("params") or {}
    if not isinstance(params, dict):  # the manifest validator rejects this; belt and braces
        params = {}
    if override_bpm is not None:
        beats = backend.beats_per_bar(params.get("timeSignature") or requirement.get("timeSignature"))
        return float(override_bpm), beats or 4, "flag"

    if (candidate or {}).get("backend") != "acestep":
        return None, None, None
    bpm = params.get("bpm")
    beats = params.get("beatsPerBar") or backend.beats_per_bar(params.get("timeSignature"))
    if not isinstance(bpm, (int, float)) or isinstance(bpm, bool) or bpm <= 0 or not beats:
        return None, None, None
    return float(bpm), int(beats), "acestep-candidate"


def bar_plan(
    content_start: int, content_end: int, bpm: float, beats: int, rate: int
) -> tuple[int, float, int]:
    """(bars kept, seconds per bar, loop end sample) for a contentful bar loop.

    The last bar boundary that still falls inside the audio is the loop point.
    ACE-Step's planner routinely ends a song before the bar count it was asked
    for, so the requested length is a target and the audio is the truth.

    Bar boundaries are rounded from the exact bar length rather than accumulated
    from an integer bar size: at 140 BPM in 4/4 a bar is 82285.714 samples at
    48 kHz, and rounding once per bar would drift by a sample every three bars.
    """
    bar_samples = 60.0 * beats / bpm * rate
    if bar_samples < 1:
        raise user_error(f"{bpm:g} BPM with {beats} beats per bar is not a usable bar length.")
    # Half a sample of tolerance gives the optimistic bar count: `content_end` is
    # a sample index rounded from a continuous boundary, so a bar whose exact end
    # rounds onto it is fully contentful. Then the count is walked back until the
    # endpoint computed with the SAME rounding as the cut actually fits. The two
    # rules disagree when a bar is a whole number of half-samples (128 BPM 4/4 at
    # 44.1 kHz is exactly 82687.5): there `round()` breaks the tie to even and
    # can land one sample past the content the optimistic count promised.
    bars = int((content_end - content_start + 0.5) // bar_samples)
    while bars >= 1 and content_start + int(round(bars * bar_samples)) > content_end:
        bars -= 1
    if bars < 1:
        raise user_error(
            f"the contentful part of this take is {(content_end - content_start) / rate:.2f}s, "
            f"shorter than one bar ({bar_samples / rate:.2f}s at {bpm:g} BPM). Re-generate it "
            "longer, lower requirement.bpm, or clear requirement.loop."
        )
    return bars, bar_samples / rate, content_start + int(round(bars * bar_samples))


def build_plan(args: argparse.Namespace, manifest: dict[str, Any], source: pathlib.Path,
               candidate: dict[str, Any] | None) -> dict[str, Any]:
    """Decide every cut before a single sample is written."""
    info = probe(source)
    rate, channels, total = info["rate"], info["channels"], info["samples"]
    requirement = manifest["requirement"]
    loop = bool(requirement.get("loop")) and not args.skip_loop

    levels = rms_envelope(source, rate)
    bounds = content_bounds(levels, rate, total, SILENCE_THRESHOLD_DBFS)
    if bounds is None:
        raise user_error(
            f"{source.as_posix()} is silent at or below {SILENCE_THRESHOLD_DBFS:g} dBFS all the "
            "way through - there is nothing to post-process. Re-run the generate stage."
        )
    content_start, content_end = bounds
    tail_threshold = SILENCE_THRESHOLD_DBFS
    if not loop:
        tail_threshold = decay_threshold(levels)
        decayed = content_bounds(levels, rate, total, tail_threshold)
        if decayed is not None:
            content_end = max(content_end, decayed[1])

    plan: dict[str, Any] = {
        "sampleRate": rate,
        "channels": channels,
        "sourceSamples": total,
        "sourceSeconds": round(total / rate, 3),
        "silenceThresholdDbfs": SILENCE_THRESHOLD_DBFS,
        "tailThresholdDbfs": round(tail_threshold, 2),
        "contentStartSeconds": round(content_start / rate, 3),
        "contentEndSeconds": round(content_end / rate, 3),
        "crossfadeSamples": 0,
        "crossfadeMs": 0,
        "crossfadeCurve": None,
    }

    if loop:
        start = snap_zero(source, content_start, channels, rate, total) if content_start else 0
        wanted = int(round(args.crossfade_ms / 1000.0 * rate))
        bpm, beats, tempo_source = resolve_tempo(requirement, candidate, args.bpm)
        if bpm is not None and beats is not None:
            bars, bar_seconds, end = bar_plan(start, content_end, bpm, beats, rate)
            # A loop whose last bar reaches the physical end of the file has no
            # audio after the loop point, so the seam would be a bare cut. The
            # only way to gain overhang without leaving the grid is to give back
            # a whole bar - which costs a bar of music but keeps the loop a loop.
            while bars > 1 and total - end < wanted:
                bars -= 1
                end = start + int(round(bars * bar_seconds * rate))
            plan.update(
                mode="bar-loop", bpm=bpm, beatsPerBar=beats, bpmSource=tempo_source,
                bars=bars, barSeconds=round(bar_seconds, 6),
            )
        else:
            # No grid to protect, so the loop point is pulled back by the
            # crossfade length: the seam needs material that FOLLOWS it, and on
            # this path the content usually runs to the last sample of the file,
            # leaving none. Costs one crossfade of music, buys a real seam.
            end = snap_zero(
                source, max(start + 1, content_end - wanted), channels, rate, total
            )
            plan.update(
                mode="silence-loop", bpm=None, beatsPerBar=None, bpmSource=None,
                bars=None, barSeconds=None,
            )
        # The crossfade takes its fade-out material from the audio that follows
        # the loop point - the natural continuation of the last sample - and
        # lays it over the head. That keeps the loop exactly `end - start`
        # samples long, so a bar-snapped loop stays on the grid, and makes the
        # wrap continuous by construction: the first sample after the seam IS
        # the sample that used to follow it.
        available = max(0, total - end)
        crossfade = max(0, min(wanted, available, (end - start) // 2))
        # The tolerance for a shortened crossfade is the low end of the flag's
        # own range: 10 ms is documented as a usable seam, so anything at or
        # above it is recorded as a shortfall and accepted. Below it there is no
        # real fade left, and completing the stage would hand back a loop with a
        # bare cut at the wrap while reporting success.
        floor = int(round(MIN_CROSSFADE_MS / 1000.0 * rate))
        if crossfade < floor:
            raise user_error(
                f"there is only {crossfade / rate * 1000.0:.1f} ms of audio after the loop "
                f"point, too little for a seam crossfade (the minimum is {MIN_CROSSFADE_MS} ms). "
                "This take's content runs to the end of the file with nothing to fade from. "
                "Re-generate it longer, or pass --skip-loop to ship it as a one-shot."
            )
        plan["crossfadeSamples"] = crossfade
        plan["crossfadeMs"] = round(crossfade / rate * 1000.0, 2)
        plan["crossfadeCurve"] = CROSSFADE_CURVE
        if crossfade < wanted:
            plan["crossfadeShortfall"] = (
                f"only {crossfade / rate * 1000.0:.1f} ms of audio follows the loop point; "
                f"asked for {args.crossfade_ms} ms"
            )
    else:
        # `>=`, not `>`: the bound comes off a 50 ms grid, so a measured 0.50 s
        # of dead air is "half a second or more", which is what the rule means.
        if content_start / rate >= NONLOOP_LEAD_TRIM_SECONDS:
            start = snap_zero(source, content_start, channels, rate, total)
        else:
            start = 0
        trailing = (total - content_end) / rate
        end = total
        if trailing > NONLOOP_TAIL_KEEP_SECONDS:
            end = snap_zero(
                source,
                min(total, content_end + int(round(NONLOOP_TAIL_KEEP_SECONDS * rate))),
                channels,
                rate,
                total,
            )
        plan.update(
            mode="trim-only",
            skipped="--skip-loop" if (args.skip_loop and requirement.get("loop")) else None,
            bpm=None, beatsPerBar=None, bpmSource=None, bars=None, barSeconds=None,
        )

    if end <= start:
        raise backend_error(f"the computed cut is empty ({start}-{end} samples); refusing to write it.")
    plan.update(
        loop=loop,
        startSample=start,
        endSample=end,
        leadTrimSeconds=round(start / rate, 3),
        trailTrimSeconds=round((total - end) / rate, 3),
        outputSamples=end - start,
        outputSeconds=round((end - start) / rate, 3),
    )
    return plan


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def render_cut(source: pathlib.Path, target: pathlib.Path, plan: dict[str, Any]) -> None:
    """Write the trimmed (and, for a loop, seam-crossfaded) float master."""
    start, end = plan["startSample"], plan["endSample"]
    crossfade = plan["crossfadeSamples"]
    rate = plan["sampleRate"]

    if crossfade > 0:
        graph = (
            "[0:a]asplit=3[a0][a1][a2];"
            f"[a0]atrim=start_sample={end}:end_sample={end + crossfade},asetpts=PTS-STARTPTS[over];"
            f"[a1]atrim=start_sample={start}:end_sample={start + crossfade},asetpts=PTS-STARTPTS[head];"
            f"[a2]atrim=start_sample={start + crossfade}:end_sample={end},asetpts=PTS-STARTPTS[body];"
            f"[over][head]acrossfade=ns={crossfade}:c1={CROSSFADE_CURVE}:c2={CROSSFADE_CURVE}[seam];"
            "[seam][body]concat=n=2:v=0:a=1[out]"
        )
        args = ["-i", str(source), "-filter_complex", graph, "-map", "[out]"]
    else:
        args = [
            "-i",
            str(source),
            "-af",
            f"atrim=start_sample={start}:end_sample={end},asetpts=PTS-STARTPTS",
        ]
    run_ffmpeg([*args, "-c:a", "pcm_f32le", "-ar", str(rate), "-y", str(target)])

    written = probe(target)["samples"]
    if abs(written - plan["outputSamples"]) > 1:
        raise backend_error(
            f"the cut came back {written} samples long, expected {plan['outputSamples']}. "
            "Check the ffmpeg version; atrim/acrossfade sample indexing is being ignored."
        )


def _finite(value: Any) -> float | None:
    """A JSON-safe float, or None. loudnorm reports -inf on gated-out content.

    `json.dump` writes bare `Infinity`/`NaN`, which is not valid JSON and would
    make the manifest unreadable to anything stricter than Python.
    """
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return float(value)
    return None


def normalization_gain(
    measured: dict[str, float], target_lufs: float
) -> tuple[float, str, float]:
    """(gain in dB, how it was decided, LU still short of the target).

    A static gain computed here rather than loudnorm's own correction pass.
    loudnorm's `linear=true` is a request, not a guarantee: it silently falls
    back to DYNAMIC normalization when the gain it needs would breach the
    true-peak target, which compresses game audio without saying so in anything
    but a log line. Computing the gain makes that impossible - the cap is
    applied here, and the shortfall is recorded instead of hidden.
    """
    peak = _finite(measured.get("input_tp"))
    if peak is None:
        raise user_error(
            "loudness could not be measured: this take has no finite true peak, which "
            "means it is silent. Re-run the generate stage."
        )
    headroom = TRUE_PEAK_CEILING_DBTP - peak

    integrated = _finite(measured.get("input_i"))
    if integrated is None:
        # R128 gating found no programme above its threshold (a very short or
        # very quiet one-shot). There is no integrated figure to correct toward,
        # so the peak becomes the reference instead of guessing one.
        return headroom, "peak-only", 0.0

    wanted = target_lufs - integrated
    gain = min(wanted, headroom)
    return gain, "linear", round(max(0.0, wanted - gain), 2)


def apply_loudness(
    source: pathlib.Path, target: pathlib.Path, target_lufs: float, rate: int
) -> dict[str, Any]:
    """Measure, then move the level by one static gain. Never compresses."""
    measured = measure_loudness(source, target_lufs)
    gain, how, shortfall = normalization_gain(measured, target_lufs)
    if shortfall:
        LOGGER.info(
            "%.2f LU short of %g LUFS: the remaining gain would breach the %g dBTP ceiling",
            shortfall,
            target_lufs,
            TRUE_PEAK_CEILING_DBTP,
        )
    with atomic_output(target) as staged:
        run_ffmpeg(["-i", str(source), "-af", f"volume={gain:.4f}dB", "-c:a", "pcm_f32le",
                    "-ar", str(rate), "-y", str(staged)])
    return {
        "measuredInput": {
            "integratedLufs": _finite(measured["input_i"]),
            "truePeakDbtp": _finite(measured["input_tp"]),
            "lra": _finite(measured["input_lra"]),
            "thresholdLufs": _finite(measured["input_thresh"]),
        },
        "normalizationType": how,
        "gainDb": round(gain, 3),
        "targetShortfallDb": shortfall,
    }


def enforce_true_peak(path: pathlib.Path, target_lufs: float, rate: int) -> tuple[dict[str, Any], float]:
    """Measure the master and pull it down if it still sits over the ceiling.

    Belt and braces for the normalized path (the gain above is already capped),
    and the only thing standing between --skip-normalize and a clipped export.
    Returns (final figures, gain applied in dB).
    """
    figures = measure_loudness(path, target_lufs)
    peak = _finite(figures.get("input_tp"))
    gain = 0.0
    if peak is not None and peak - TRUE_PEAK_CEILING_DBTP > TRUE_PEAK_TOLERANCE_DB:
        gain = TRUE_PEAK_CEILING_DBTP - peak
        LOGGER.info(
            "master measured %.2f dBTP, over the %.1f dBTP ceiling: applying %.2f dB",
            peak,
            TRUE_PEAK_CEILING_DBTP,
            gain,
        )
        with atomic_output(path) as staged:
            run_ffmpeg(["-i", str(path), "-af", f"volume={gain:.4f}dB", "-c:a", "pcm_f32le",
                        "-ar", str(rate), "-y", str(staged)])
        figures = measure_loudness(path, target_lufs)
    return figures, round(gain, 3)


def export(
    master: pathlib.Path, stage_path: pathlib.Path, asset_dir: pathlib.Path, slug: str,
    formats: Sequence[str], source_rate: int, target_rate: int | None, target_lufs: float
) -> tuple[list[pathlib.Path], list[dict[str, Any]]]:
    """Write the shipping files from the float master. One resample, at the end.

    Each file is rendered to a staging name, measured there, and only then moved
    into place - so a failed encode or a clipping export never replaces the file
    a previous good run left behind.
    """
    rate = target_rate or source_rate
    # Dither is what keeps the float-to-16-bit step from adding correlated
    # quantization noise on fades and tails; soxr at precision 28 is transparent
    # for the 44.1<->48 kHz ratio, which is not an integer and is where a cheap
    # resampler leaves audible aliasing.
    resample = ["dither_method=triangular"]
    if target_rate and target_rate != source_rate:
        resample += [f"osr={target_rate}", "resampler=soxr", "precision=28"]
    chain = "aresample=" + ":".join(resample)

    codec: dict[str, list[str]] = {
        "wav": ["-c:a", "pcm_s16le"],
        "ogg": ["-c:a", "libvorbis", "-q:a", str(OGG_QUALITY)],
    }
    written: list[pathlib.Path] = []
    measured: list[dict[str, Any]] = []
    for fmt in formats:
        if fmt not in codec:  # unreachable: formats are validated before rendering starts
            raise user_error(f"unsupported format {fmt!r}")
        path = stage_path / f"{slug}.{fmt}"
        with atomic_output(path) as staged:
            run_ffmpeg(["-i", str(master), "-af", chain, *codec[fmt], "-ar", str(rate),
                        "-y", str(staged)])
            measured.append(_verify_export(staged, path.relative_to(asset_dir).as_posix(), target_lufs))
        written.append(path)
    return written, measured


def _verify_export(staged: pathlib.Path, name: str, target_lufs: float) -> dict[str, Any]:
    """Measure a freshly written export before it is allowed to replace anything.

    A lossy encoder reconstructs its own waveform and can land a fraction of a
    dB above the master's true peak - which is the whole reason the ceiling sits
    a full dB below full scale. Anything at or above 0 dBTP would clip on decode
    and is a hard failure; between the ceiling and 0 it is recorded and warned
    about.
    """
    figures = measure_loudness(staged, target_lufs)
    peak = _finite(figures.get("input_tp"))
    entry: dict[str, Any] = {
        "file": name,
        "integratedLufs": _finite(figures.get("input_i")),
        "truePeakDbtp": peak,
    }
    if peak is None:
        return entry
    if peak >= 0.0:
        raise backend_error(
            f"{name} measures {peak:+.2f} dBTP and will clip when decoded. The master was "
            "under the ceiling, so the encoder is the cause - check the ffmpeg build. The "
            "previous export was left in place."
        )
    if peak > TRUE_PEAK_CEILING_DBTP + TRUE_PEAK_TOLERANCE_DB:
        entry["aboveCeiling"] = True
        LOGGER.info(
            "%s measures %.2f dBTP, just over the %.1f dBTP ceiling - normal encoder "
            "overshoot, still %.2f dB below full scale",
            name,
            peak,
            TRUE_PEAK_CEILING_DBTP,
            -peak,
        )
    return entry


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #


def _db(value: float | None) -> str:
    """A dB figure for the console; gated-out measurements print as n/a."""
    return "n/a" if value is None else f"{value:.2f}"


def print_plan(plan: dict[str, Any], source: pathlib.Path, formats: Sequence[str],
               target_lufs: float, target_rate: int | None, normalize: bool) -> None:
    print("")
    print(f"Post-process plan for {source.as_posix()}")
    print(f"  source        {plan['sourceSeconds']:.3f}s  {plan['sampleRate']} Hz  {plan['channels']} ch")
    print(f"  content       {plan['contentStartSeconds']:.3f}s .. {plan['contentEndSeconds']:.3f}s"
          f"  (floor {plan['silenceThresholdDbfs']:g} dBFS, tail {plan['tailThresholdDbfs']:g} dBFS)")
    print(f"  mode          {plan['mode']}")
    if plan.get("bars"):
        print(f"  bars kept     {plan['bars']} @ {plan['bpm']:g} BPM / {plan['beatsPerBar']} beats "
              f"({plan['bpmSource']})")
    print(f"  cut           samples {plan['startSample']}..{plan['endSample']}  "
          f"-> {plan['outputSeconds']:.3f}s "
          f"(lead -{plan['leadTrimSeconds']:.3f}s, tail -{plan['trailTrimSeconds']:.3f}s)")
    if plan["crossfadeSamples"]:
        print(f"  crossfade     {plan['crossfadeMs']:.1f} ms {plan['crossfadeCurve']} equal-power")
    if plan.get("crossfadeShortfall"):
        print(f"  WARNING       {plan['crossfadeShortfall']}")
    print(f"  loudness      {'%g LUFS' % target_lufs if normalize else 'skipped'}, "
          f"ceiling {TRUE_PEAK_CEILING_DBTP:g} dBTP")
    print(f"  exports       master.wav + {', '.join(formats)}"
          + (f" resampled to {target_rate} Hz" if target_rate else ""))


def process(args: argparse.Namespace, manifest: dict[str, Any], base: pathlib.Path | None) -> int:
    slug = manifest["slug"]
    requirement = manifest["requirement"]

    formats = [str(fmt).strip().lower() for fmt in requirement.get("formats") or []]
    unsupported = [fmt for fmt in formats if fmt not in SUPPORTED_FORMATS]
    if unsupported:
        raise user_error(
            f"requirement.formats contains {unsupported}, which the post stage cannot write. "
            f"Supported: {list(SUPPORTED_FORMATS)}."
        )

    relative, candidate = resolve_source(manifest, args.candidate)
    asset_dir = _common.output_dir(slug, base)
    source = resolve_inside(asset_dir, relative)
    if not source.is_file():
        raise user_error(f"the selected candidate is not on disk: {source.as_posix()}")

    target_lufs = requirement.get("targetLufs", -16.0)
    if (
        isinstance(target_lufs, bool)
        or not isinstance(target_lufs, (int, float))
        or not math.isfinite(target_lufs)
    ):
        raise user_error(
            f"requirement.targetLufs must be a number in LUFS, got {target_lufs!r}"
        )
    target_lufs = float(target_lufs)

    plan = build_plan(args, manifest, source, candidate)
    normalize = not args.skip_normalize

    if _common.is_dry_run():
        print_plan(plan, source, formats, target_lufs, args.target_rate, normalize)
        print("")
        print("AUDIO_PIPELINE_DRY_RUN=1: nothing was written and the manifest is unchanged.")
        return _common.EXIT_OK

    print_plan(plan, source, formats, target_lufs, args.target_rate, normalize)
    # Everything below is about to be recomputed, so the previous run's results
    # are cleared here rather than overwritten at the end. If this run fails, the
    # manifest must not still describe the last successful one - a reader would
    # take stale outputs, bar counts and loudness figures for this take's.
    _manifest.update_stage(
        slug,
        "post",
        {"status": "in_progress", "failureKind": None, "outputs": [],
         "loopProcessing": None, "normalize": None},
        base,
    )

    stage_path = _common.stage_dir(slug, "post", base)
    master = stage_path / "master.wav"
    rate = plan["sampleRate"]

    with tempfile.TemporaryDirectory(prefix=f"post-{slug}-") as tmp:
        cut = pathlib.Path(tmp) / "cut.wav"
        render_cut(source, cut, plan)
        if normalize:
            normalize_record = apply_loudness(cut, master, target_lufs, rate)
        else:
            with atomic_output(master) as staged:
                shutil.copyfile(cut, staged)
            normalize_record = {"skipped": "--skip-normalize", "measuredInput": None,
                                "normalizationType": None, "gainDb": 0.0,
                                "targetShortfallDb": None}

    # Runs in both branches: an export made from a master over 0 dBTP clips when
    # a 16-bit or Vorbis decoder reconstructs it, and --skip-normalize is a
    # request to leave the loudness alone, not to ship something that clips.
    final, safety_gain = enforce_true_peak(master, target_lufs, rate)
    normalize_record.update(
        targetLufs=target_lufs,
        truePeakCeilingDbtp=TRUE_PEAK_CEILING_DBTP,
        peakSafetyGainDb=safety_gain,
        measuredOutput={
            "integratedLufs": _finite(final.get("input_i")),
            "truePeakDbtp": _finite(final.get("input_tp")),
            "lra": _finite(final.get("input_lra")),
        },
        shortProgramme=plan["outputSeconds"] < SHORT_PROGRAMME_SECONDS,
    )

    loop_record = dict(plan)
    if plan["loop"]:
        loop_record.update(seam_metric(master, rate, plan["channels"], plan["outputSamples"]))

    exported, normalize_record["exports"] = export(
        master, stage_path, asset_dir, slug, formats, rate, args.target_rate, target_lufs
    )
    outputs = [path.relative_to(asset_dir).as_posix() for path in (master, *exported)]

    _manifest.update_stage(
        slug,
        "post",
        {"status": "done", "loopProcessing": loop_record, "normalize": normalize_record,
         "outputs": outputs, "failureKind": None},
        base,
    )

    print("")
    print(f"Post stage done for '{slug}'")
    print(f"  {plan['outputSeconds']:.3f}s at {plan['sampleRate']} Hz"
          + (f" (exports resampled to {args.target_rate} Hz)" if args.target_rate else ""))
    if plan.get("bars"):
        print(f"  {plan['bars']} bars kept of the take's content")
    if plan["loop"]:
        status = "ok" if loop_record.get("seamOk") else "CHECK BY EAR"
        print(f"  seam ratio {loop_record.get('seamRatio')} ({status}), "
              f"crossfade {plan['crossfadeMs']:.1f} ms")
    measured_out = normalize_record["measuredOutput"]
    print(f"  {_db(measured_out['integratedLufs'])} LUFS, {_db(measured_out['truePeakDbtp'])} dBTP"
          + (f", peak-safety gain {safety_gain:g} dB" if safety_gain else "")
          + (f", {normalize_record['targetShortfallDb']:g} LU short of target"
             if normalize_record.get("targetShortfallDb") else ""))
    print(f"  {outputs[0]}")
    for entry in normalize_record["exports"]:
        print(f"  {entry['file']}  {_db(entry['integratedLufs'])} LUFS  "
              f"{_db(entry['truePeakDbtp'])} dBTP")
    print(
        "Next: play the loop twice in a row (or in engine) and listen to the wrap."
        if plan["loop"]
        else "Next: audition the export, then run the review stage."
    )
    return _common.EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Trim, loop, normalize and export the selected candidate of an audio asset"
    )
    parser.add_argument("slug", nargs="?", help="asset slug, e.g. 'chiptune-loop'")
    parser.add_argument("--candidate", default=None,
                        help="candidate to process, e.g. generate/cand-03.wav "
                             "(default: stages.generate.selected, or the only candidate)")
    parser.add_argument("--base", default=None, help="workspace holding audio-pipeline-output/")
    parser.add_argument("--skip-loop", action="store_true",
                        help="treat a looping asset as a one-shot: no bar cut, no seam crossfade")
    parser.add_argument("--skip-normalize", action="store_true",
                        help="leave loudness alone (the true-peak ceiling is still enforced)")
    parser.add_argument("--crossfade-ms", type=int, default=DEFAULT_CROSSFADE_MS,
                        help=f"loop seam crossfade length, {MIN_CROSSFADE_MS}-{MAX_CROSSFADE_MS} "
                             f"(default: {DEFAULT_CROSSFADE_MS})")
    parser.add_argument("--bpm", type=float, default=None,
                        help="tempo to snap bars to, for a take whose backend does not render to "
                             "the requirement's BPM (MiniMax, Stable Audio 3)")
    parser.add_argument("--target-rate", type=int, default=None, choices=SUPPORTED_TARGET_RATES,
                        help="resample the exports once, at the end (default: keep the source rate)")
    parser.add_argument("--selftest", action="store_true", help="run the built-in assertions")
    args = parser.parse_args(argv)

    if args.selftest:
        return _selftest()
    if not args.slug:
        parser.error("a slug is required (or pass --selftest)")
    if not MIN_CROSSFADE_MS <= args.crossfade_ms <= MAX_CROSSFADE_MS:
        parser.error(
            f"--crossfade-ms must be between {MIN_CROSSFADE_MS} and {MAX_CROSSFADE_MS}, "
            f"got {args.crossfade_ms}"
        )
    if args.bpm is not None and not (math.isfinite(args.bpm) and args.bpm > 0):
        parser.error(f"--bpm must be a positive number, got {args.bpm}")

    base = pathlib.Path(args.base).expanduser().resolve() if args.base else None
    try:
        manifest = _manifest.read(args.slug, base)
    except FileNotFoundError as exc:
        LOGGER.error("%s", exc)
        return _common.EXIT_USER_ERROR
    except ValueError as exc:
        LOGGER.error("Manifest is not usable: %s", exc)
        return _common.EXIT_MANIFEST_CORRUPT

    try:
        try:
            return process(args, manifest, base)
        except ValueError as exc:
            # The shared validators (`relative_artifact_path`, the manifest
            # checks) signal a rejected input with ValueError. Every one of them
            # is a user mistake, so they become a recorded user_error here
            # rather than a traceback in each call site.
            raise user_error(str(exc)) from exc
    except PostError as exc:
        LOGGER.error("%s", exc.message)
        if not _common.is_dry_run():
            _manifest.update_stage(args.slug, "post", {"status": "failed", "failureKind": exc.kind}, base)
        return (
            _common.EXIT_USER_ERROR
            if exc.kind == backend.FAILURE_USER_ERROR
            else _common.EXIT_TIMEOUT
            if exc.kind == backend.FAILURE_TIMEOUT
            else _common.EXIT_BACKEND_ERROR
        )


# --------------------------------------------------------------------------- #
# Self-check
# --------------------------------------------------------------------------- #


def _tone(path: pathlib.Path, frequency: float, seconds: float, rate: int, pad: float = 0.0) -> None:
    """A test tone of an exactly known frequency, optionally padded with silence.

    `aevalsrc` with the expression written out rather than the `sine` source:
    ffmpeg 8.0's `sine` does not render the frequency it is handed at every
    sample rate, and these assertions depend on the period being what it says.
    """
    args = ["-f", "lavfi", "-i", f"aevalsrc=0.5*sin(2*PI*{frequency}*t):s={rate}:d={seconds}"]
    if pad:
        args += ["-af", f"apad=whole_dur={seconds + pad}"]
    run_ffmpeg([*args, "-ac", "2", "-c:a", "pcm_f32le", "-y", str(path)])


def _selftest() -> int:
    rate = 48000

    # Bar math: a 140 BPM 4/4 bar is 1.714285...s, which is never a whole number
    # of samples. Boundaries must come from the exact length, not an accumulated
    # integer, and only whole contentful bars may be kept.
    bar = 60.0 * 4 / 140 * rate  # 82285.714... samples
    bars, seconds, end = bar_plan(0, int(26.77 * rate), 140.0, 4, rate)
    assert bars == 15, bars
    assert abs(seconds - 60.0 * 4 / 140) < 1e-9, seconds
    assert end == int(round(15 * bar)) == 1234286, end
    assert abs(end / rate - 25.714286) < 1e-5, end / rate
    # One sample short of bar 16 still keeps 15 bars; one sample past keeps 16.
    assert bar_plan(0, int(round(16 * bar)) - 1, 140.0, 4, rate)[0] == 15
    assert bar_plan(0, int(round(16 * bar)) + 1, 140.0, 4, rate)[0] == 16
    # A leading trim shifts the whole grid with it.
    assert bar_plan(1000, 1000 + int(round(3 * bar)), 140.0, 4, rate)[2] == 1000 + int(round(3 * bar))
    for impossible in ((0, 100), (0, int(bar) - 1)):
        try:
            bar_plan(impossible[0], impossible[1], 140.0, 4, rate)
        except PostError as exc:
            assert exc.kind == backend.FAILURE_USER_ERROR
        else:
            raise AssertionError("expected a user_error for a sub-bar take")

    # Half-sample bars, where the optimistic count and round()'s tie-to-even
    # disagree. 128 BPM in 4/4 at 44.1 kHz is exactly 82687.5 samples per bar;
    # the 48 kHz case needs a fractional tempo to land on the same .5.
    for check_rate, check_bpm in ((44100, 128.0), (48000, 240.0 * 48000 / 82687.5)):
        half = 60.0 * 4 / check_bpm * check_rate
        assert abs(half - 82687.5) < 1e-6, half
        for count in range(2, 7):
            endpoint = int(round(count * half))
            # Content one sample short of the endpoint must never keep that bar,
            # whichever way the tie broke - the cut has to land inside the audio.
            kept, _, kept_end = bar_plan(0, endpoint - 1, check_bpm, 4, check_rate)
            assert kept == count - 1, (check_rate, count, kept)
            assert kept_end <= endpoint - 1, (check_rate, count, kept_end)
            # Content exactly on the endpoint keeps it.
            exact, _, exact_end = bar_plan(0, endpoint, check_bpm, 4, check_rate)
            assert exact == count and exact_end == endpoint, (check_rate, count, exact, exact_end)
        # bar 1 ends at 82688 (rounded up from .5), so 82687 samples of content
        # is not a whole bar - the old +0.5 rule alone claimed it was.
        try:
            bar_plan(0, int(round(half)) - 1, check_bpm, 4, check_rate)
        except PostError as exc:
            assert exc.kind == backend.FAILURE_USER_ERROR
        else:
            raise AssertionError("expected a user_error one sample short of bar 1")

    with tempfile.TemporaryDirectory(prefix="post-selftest-") as tmp:
        work = pathlib.Path(tmp)

        # Containment: a path that RESOLVES outside the asset directory is
        # rejected even though its string form is a clean relative path. On a
        # machine that allows symlinks that is how an escape would arrive; here
        # it is proven with a directory that really is elsewhere.
        asset = work / "asset"
        (asset / "generate").mkdir(parents=True)
        (asset / "generate/cand-01.wav").write_bytes(b"x")
        assert resolve_inside(asset, "generate/cand-01.wav") == (asset / "generate/cand-01.wav").resolve()
        elsewhere = work / "elsewhere"
        elsewhere.mkdir()
        relative_escape = os.path.relpath(elsewhere / "loot.wav", asset).replace("\\", "/")
        try:
            resolve_inside(asset, relative_escape)
        except PostError as exc:
            assert exc.kind == backend.FAILURE_USER_ERROR, exc.kind
        else:
            raise AssertionError("expected a user_error for a path resolving outside the asset dir")

        # Content bounds from the RMS envelope, against a file with a known
        # 0.5 s silent tail.
        tone = work / "tone.wav"
        _tone(tone, 220.0, 2.0, rate, pad=0.5)
        info = probe(tone)
        assert (info["rate"], info["channels"]) == (rate, 2), info
        levels = rms_envelope(tone, rate)
        # A one-shot tail's floor follows its own body and is never above the absolute one.
        relative = decay_threshold(levels)
        assert relative <= SILENCE_THRESHOLD_DBFS, relative
        assert abs(relative - (max(levels) - DECAY_RANGE_DB)) < 1e-9, relative
        start, end = content_bounds(levels, rate, info["samples"], SILENCE_THRESHOLD_DBFS)
        assert start == 0, start
        assert abs(end / rate - 2.0) <= SILENCE_WINDOW_SECONDS, end / rate
        # Digital silence has no content at any threshold.
        silent = work / "silent.wav"
        run_ffmpeg(["-f", "lavfi", "-i", f"anullsrc=r={rate}:cl=stereo:d=1",
                    "-c:a", "pcm_f32le", "-y", str(silent)])
        assert content_bounds(rms_envelope(silent, rate), rate, rate, SILENCE_THRESHOLD_DBFS) is None

        # The envelope must take the MAX across channels, like the workers do,
        # not the pooled energy. A tone in one channel only sits just under the
        # threshold when the two are averaged and just over it when they are
        # not, so the two rules disagree about whether this file has content.
        # About -43.9 dBFS in one channel: over the threshold on its own, and
        # 3 dB lower once pooled with a silent partner, which puts it under.
        lopsided = work / "lopsided.wav"
        run_ffmpeg([
            "-f", "lavfi", "-i", f"aevalsrc=0.009*sin(2*PI*440*t):s={rate}:d=1",
            "-f", "lavfi", "-i", f"anullsrc=r={rate}:cl=mono:d=1",
            "-filter_complex", "[0:a][1:a]join=inputs=2:channel_layout=stereo[out]",
            "-map", "[out]", "-c:a", "pcm_f32le", "-y", str(lopsided),
        ])
        per_channel = rms_envelope(lopsided, rate)
        loudest = max(per_channel)
        assert loudest > SILENCE_THRESHOLD_DBFS, loudest
        # The pooled (Overall) figure would have called the same file silent.
        assert loudest - 3.01 < SILENCE_THRESHOLD_DBFS, loudest
        assert content_bounds(per_channel, rate, rate, SILENCE_THRESHOLD_DBFS) is not None

        # read_frames refuses a payload that is not whole frames rather than
        # rounding it down into misaligned channels.
        try:
            read_frames(silent, 0, 100, 3)  # the file is stereo; 3 never divides it
        except PostError as exc:
            assert exc.kind == backend.FAILURE_BACKEND_ERROR, exc.kind
        else:
            raise AssertionError("expected a backend_error for a ragged frame payload")

        # Zero-crossing snap: 220 Hz crosses zero every ~109 samples, so the
        # snapped cut must land within half a period and read near zero.
        target = rate // 2
        snapped = snap_zero(tone, target, 2, rate, info["samples"])
        assert abs(snapped - target) <= rate // 220, (snapped, target)
        at_cut = read_frames(tone, snapped, snapped + 1, 2)
        assert abs(sum(channel[0] for channel in at_cut)) < 0.05, at_cut

        # Equal-power crossfade: two identical DC streams crossfaded with qsin
        # sum to cos+sin, which reaches sqrt(2) times the input in the middle.
        # A linear (`tri`) fade stays at 1.0 there, so this really does check
        # that the constant-power curve is the one being applied.
        flat = work / "flat.wav"
        run_ffmpeg(["-f", "lavfi", "-i", f"aevalsrc=0.5:s={rate}:d=1", "-ac", "2",
                    "-c:a", "pcm_f32le", "-y", str(flat)])
        base = read_frames(flat, 0, 1, 2)[0][0]
        assert base > 0.01, base
        middle = rate // 20
        for curve, expected in ((CROSSFADE_CURVE, math.sqrt(2)), ("tri", 1.0)):
            faded = work / f"faded-{curve}.wav"
            run_ffmpeg([
                "-i", str(flat), "-filter_complex",
                f"[0:a]asplit=2[p][q];"
                f"[p]atrim=start_sample=0:end_sample={rate // 10},asetpts=PTS-STARTPTS[a];"
                f"[q]atrim=start_sample=0:end_sample={rate // 10},asetpts=PTS-STARTPTS[b];"
                f"[a][b]acrossfade=ns={rate // 10}:c1={curve}:c2={curve}[out]",
                "-map", "[out]", "-c:a", "pcm_f32le", "-y", str(faded),
            ])
            assert probe(faded)["samples"] == rate // 10, probe(faded)
            value = read_frames(faded, middle, middle + 1, 2)[0][0]
            assert abs(value / base - expected) < 0.01, (curve, value / base, expected)

        # Seam metric: 1 kHz at 48 kHz is 48 samples per cycle, so a cut on a
        # multiple of 48 wraps continuously and a cut 12 samples past one wraps
        # a quarter cycle out of phase - a discontinuity the check must catch.
        clean = work / "clean.wav"
        _tone(clean, 1000.0, 1.2, rate)
        cycles = rate  # exactly 1000 whole cycles
        for name, length, expect_ok in (("loopable", cycles, True), ("broken", cycles + 12, False)):
            cut = work / f"{name}.wav"
            run_ffmpeg(["-i", str(clean), "-af", f"atrim=start_sample=0:end_sample={length}",
                        "-c:a", "pcm_f32le", "-y", str(cut)])
            metric = seam_metric(cut, rate, 2, length)
            assert metric["seamOk"] is expect_ok, (name, metric)
        assert seam_metric(work / "broken.wav", rate, 2, cycles + 12)["seamRatio"] > 5, "quarter-cycle jump"

        # End to end on a synthetic ACE-Step-shaped take: 140 BPM, content that
        # stops between bar 15 and 16, and a silent tail. The processed loop must
        # be exactly 15 bars and its seam must pass.
        with tempfile.TemporaryDirectory(prefix="post-selftest-ws-") as workspace_dir:
            workspace = pathlib.Path(workspace_dir)
            _manifest.init("selftest-loop", "bgm", "auto",
                           {"prompt": "selftest", "durationSeconds": 30.0, "bpm": 140,
                            "formats": ["wav", "ogg"]}, workspace)
            stage = _common.stage_dir("selftest-loop", "generate", workspace)
            _tone(stage / "cand-01.wav", 440.0, 26.77, rate, pad=4.03)
            _manifest.update_stage(
                "selftest-loop", "generate",
                {"status": "done", "backend": "acestep",
                 "candidates": [_manifest.make_candidate(
                     "generate/cand-01.wav", 1, "acestep",
                     {"bpm": 140, "beatsPerBar": 4, "bars": 18})]},
                workspace,
            )
            code = main(["selftest-loop", "--base", str(workspace)])
            assert code == _common.EXIT_OK, code
            done = _manifest.read("selftest-loop", workspace)["stages"]["post"]
            assert done["status"] == "done", done
            assert done["loopProcessing"]["bars"] == 15, done["loopProcessing"]
            assert done["loopProcessing"]["seamOk"], done["loopProcessing"]
            assert done["normalize"]["measuredOutput"]["truePeakDbtp"] <= TRUE_PEAK_CEILING_DBTP + 0.05
            assert done["outputs"] == ["post/master.wav", "post/selftest-loop.wav",
                                       "post/selftest-loop.ogg"], done["outputs"]
            asset = _common.output_dir("selftest-loop", workspace)
            processed = probe(asset / "post/master.wav")
            assert abs(processed["seconds"] - 15 * 60.0 * 4 / 140) < 0.001, processed

            # A failed re-run must not leave the previous run's numbers behind.
            # Wedging a directory where master.wav goes fails the rename after
            # the stage has already been marked in_progress, which is exactly
            # the window the metadata has to be cleared in.
            exports = {name: (asset / "post" / name).read_bytes()
                       for name in ("selftest-loop.wav", "selftest-loop.ogg")}
            (asset / "post/master.wav").unlink()
            (asset / "post/master.wav").mkdir()
            assert main(["selftest-loop", "--base", str(workspace)]) == _common.EXIT_BACKEND_ERROR
            failed = _manifest.read("selftest-loop", workspace)["stages"]["post"]
            assert failed["status"] == "failed", failed
            assert failed["failureKind"] == backend.FAILURE_BACKEND_ERROR, failed
            assert failed["outputs"] == [], failed["outputs"]
            assert failed["loopProcessing"] is None and failed["normalize"] is None, failed
            # ...and the exports the good run wrote are untouched.
            for name, blob in exports.items():
                assert (asset / "post" / name).read_bytes() == blob, name
            # No staging files were left lying around either.
            leftovers = [p.name for p in (asset / "post").iterdir() if p.name.startswith(".")]
            assert not leftovers, leftovers

        # A loop whose content reaches the physical end of the file has no
        # material to fade from, so a whole bar is given back to make room.
        with tempfile.TemporaryDirectory(prefix="post-selftest-edge-") as workspace_dir:
            workspace = pathlib.Path(workspace_dir)
            bar_seconds = 60.0 * 4 / 140
            _manifest.init("selftest-edge", "bgm", "auto",
                           {"prompt": "selftest", "durationSeconds": 15 * bar_seconds,
                            "bpm": 140, "formats": ["wav"]}, workspace)
            stage = _common.stage_dir("selftest-edge", "generate", workspace)
            _tone(stage / "cand-01.wav", 440.0, 15 * bar_seconds, rate)
            candidate = _manifest.make_candidate("generate/cand-01.wav", 1, "acestep",
                                                 {"bpm": 140, "beatsPerBar": 4})
            _manifest.update_stage("selftest-edge", "generate",
                                   {"status": "done", "backend": "acestep",
                                    "candidates": [candidate]}, workspace)
            assert main(["selftest-edge", "--base", str(workspace)]) == _common.EXIT_OK
            edge = _manifest.read("selftest-edge", workspace)["stages"]["post"]["loopProcessing"]
            assert edge["bars"] == 14, edge["bars"]
            assert edge["crossfadeMs"] == DEFAULT_CROSSFADE_MS, edge["crossfadeMs"]
            assert edge["seamOk"], edge

        # One bar of content running to the end cannot give a bar back, so the
        # stage refuses rather than shipping a loop with a bare cut.
        with tempfile.TemporaryDirectory(prefix="post-selftest-tiny-") as workspace_dir:
            workspace = pathlib.Path(workspace_dir)
            _manifest.init("selftest-tiny", "bgm", "auto",
                           {"prompt": "selftest", "durationSeconds": 60.0 * 4 / 140,
                            "bpm": 140, "formats": ["wav"]}, workspace)
            stage = _common.stage_dir("selftest-tiny", "generate", workspace)
            _tone(stage / "cand-01.wav", 440.0, 60.0 * 4 / 140, rate)
            _manifest.update_stage(
                "selftest-tiny", "generate",
                {"status": "done", "backend": "acestep",
                 "candidates": [_manifest.make_candidate("generate/cand-01.wav", 1, "acestep",
                                                         {"bpm": 140, "beatsPerBar": 4})]},
                workspace,
            )
            assert main(["selftest-tiny", "--base", str(workspace)]) == _common.EXIT_USER_ERROR
            tiny = _manifest.read("selftest-tiny", workspace)["stages"]["post"]
            assert tiny["status"] == "failed" and tiny["failureKind"] == backend.FAILURE_USER_ERROR

    print("post_process selftest: ok")
    return _common.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
