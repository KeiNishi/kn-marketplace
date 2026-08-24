"""Stage `review`: mechanical QC of what the post stage shipped.

Runs after `post_process.py`. Every check re-measures the FILES rather than
trusting the numbers the post stage recorded - the point of a review stage is to
catch the case where the manifest and the audio disagree (a truncated export, a
file replaced by hand, an encoder that clipped). The recorded figures are used
only as the expectation to measure against.

It also renders a spectrogram PNG per shipped WAV into `review/`, so an agent
that can look at images - or a person - can inspect structure, dropouts and
band-limiting that no scalar check describes.

Usage:
    python review_asset.py <slug>
    python review_asset.py <slug> --base <workspace>

Exit 0 when the verdict is `pass`, 2 when it is `fail` (or the stage cannot run).
Set AUDIO_PIPELINE_DRY_RUN=1 to print the plan and touch nothing. (On Windows,
use `py -3` if `python3` is not available.)

`clapScore` stays `null` in v0.1: a CLAP prompt-audio similarity score would
need a model download and a venv, which the review stage deliberately does not
have. The manifest field exists so adding it later needs no schema change.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import re
import sys
from typing import Any

_SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent
for _extra in (_SCRIPTS_DIR, _SCRIPTS_DIR / "backends"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import _common  # noqa: E402
import _manifest  # noqa: E402
import post_process as post  # noqa: E402


LOGGER = _common.setup_logger("audio-review")

# Loudness. The post stage normalizes with a single measured static gain, so a
# correct export lands on the target within the repeatability of the R128
# estimator; 1 LU is the smallest tolerance that never fires on a good file and
# is still half the size of the smallest level difference a listener notices.
LOUDNESS_TOLERANCE_LU = 1.0
# True peak. The ceiling is the post stage's own, plus the overshoot a lossy
# encoder adds when it reconstructs its waveform - Vorbis at q6 lands a few
# hundredths of a dB over on peaky material. Well below 0 dBTP either way, which
# is the figure that actually matters: above it, the file clips on decode.
TRUE_PEAK_TOLERANCE_DB = 0.15
# Duration. Vorbis carries its length in granule positions, so a re-decode can
# land a few samples either side of the master; 50 ms is far wider than that and
# far narrower than any cut this pipeline makes.
DURATION_TOLERANCE_SECONDS = 0.05
# Silence floor. -60 dBFS overall RMS is roughly a 16-bit file's noise floor: a
# take that measures under it has no programme in it at all, whatever the
# loudness normalizer did to it afterwards.
SILENCE_FLOOR_DBFS = -60.0
# A one-shot is trimmed to its content, so it is normally SHORTER than the
# duration that was requested. It must never be longer (the post stage only
# cuts), and a take that came back under a quarter of the request is a failed
# generation rather than a tight edit.
NONLOOP_OVERRUN_SECONDS = 0.5
NONLOOP_MIN_FRACTION = 0.25

# `legend=1` keeps the axes: without them a spectrogram cannot be read
# quantitatively, and the whole point of the image is inspecting where the
# energy sits. 1024x512 is wide enough to resolve a 30 s loop's bar structure.
SPECTROGRAM_SIZE = "1024x512"

_RMS_LINE = re.compile(r"RMS level dB:\s*(\S+)")


def overall_rms_dbfs(path: pathlib.Path) -> float | None:
    """Overall RMS of a file in dBFS; None when it is digitally silent.

    astats' summary rather than the R128 integrated figure: R128 gates, so a
    file that is silent apart from one click reports no integrated loudness at
    all, and "unmeasurable" would be indistinguishable from "silent".
    """
    stderr = post.run_ffmpeg(
        ["-i", str(path), "-af", "astats=measure_perchannel=none", "-f", "null", "-"],
        verbose=True,
    )
    match = _RMS_LINE.search(stderr)
    if match is None:
        raise post.backend_error(
            f"astats printed no RMS level for {path.name}. ffmpeg said:\n{stderr.strip()[-600:]}"
        )
    try:
        value = float(match.group(1))
    except ValueError:  # "-inf" on digital silence
        return None
    return value if math.isfinite(value) else None


def measure_output(path: pathlib.Path, target_lufs: float) -> dict[str, Any]:
    """Decode one shipped file and return everything the checks need from it."""
    # A full decode first: ffprobe reads headers, so a file whose container says
    # 30 s but whose stream stops at 12 s passes a probe and fails here.
    post.run_ffmpeg(["-xerror", "-i", str(path), "-f", "null", "-"])
    info = post.probe(path)
    figures = post.measure_loudness(path, target_lufs)
    return {
        "seconds": round(info["seconds"], 3),
        # The exact count, not a figure rebuilt from the rounded seconds above:
        # the seam check reads the LAST samples of the file, and a length that
        # is a few samples off measures the wrap at the wrong place.
        "samples": info["samples"],
        "sampleRate": info["rate"],
        "channels": info["channels"],
        "integratedLufs": post._finite(figures.get("input_i")),
        "truePeakDbtp": post._finite(figures.get("input_tp")),
        "rmsDbfs": overall_rms_dbfs(path),
    }


def render_spectrogram(source: pathlib.Path, target: pathlib.Path) -> None:
    with post.atomic_output(target) as staged:
        post.run_ffmpeg(
            [
                "-i",
                str(source),
                "-lavfi",
                f"showspectrumpic=s={SPECTROGRAM_SIZE}:legend=1",
                "-frames:v",
                "1",
                "-y",
                str(staged),
            ]
        )


def _check(passed: bool, detail: str) -> dict[str, Any]:
    return {"pass": bool(passed), "detail": detail}


def _rms_text(value: float | None) -> str:
    return "digital silence" if value is None else f"{value:.1f} dBFS RMS"


# Formats whose decoder rebuilds the waveform and can land slightly above the
# master's true peak. PCM cannot, so it gets no such allowance.
LOSSY_SUFFIXES = (".ogg", ".mp3", ".m4a", ".opus")


def _peak_limit(relative: str) -> float:
    """The ceiling this file is held to, in dBTP.

    PCM is a sample-for-sample copy of the master, so it is held to what the
    post stage itself enforces - the ceiling plus that stage's own correction
    threshold, below the repeatability of the true-peak estimator. Reviewing
    stricter than the producing stage guarantees would only manufacture
    failures. A lossy export additionally gets the encoder's reconstruction
    overshoot.
    """
    if relative.lower().endswith(LOSSY_SUFFIXES):
        return post.TRUE_PEAK_CEILING_DBTP + TRUE_PEAK_TOLERANCE_DB
    return post.TRUE_PEAK_CEILING_DBTP + post.TRUE_PEAK_TOLERANCE_DB


def expected_duration(manifest: dict[str, Any]) -> tuple[float | None, float, float, str]:
    """(expected seconds, low bound, high bound, how it was decided).

    A loop is the strict case: the post stage cut it to an exact length and a
    game will wrap it at exactly that point, so anything else means the file on
    disk is not the file the manifest describes. A one-shot has no such contract
    - it was trimmed to its own content - so only the two ways it can be WRONG
    are bounded.
    """
    post_stage = manifest["stages"]["post"]
    loop_record = post_stage.get("loopProcessing") or {}
    kept = loop_record.get("outputSeconds")
    if loop_record.get("loop") and isinstance(kept, (int, float)):
        return (
            float(kept),
            float(kept) - DURATION_TOLERANCE_SECONDS,
            float(kept) + DURATION_TOLERANCE_SECONDS,
            "the loop length the post stage kept",
        )
    if isinstance(kept, (int, float)):
        return (
            float(kept),
            float(kept) - DURATION_TOLERANCE_SECONDS,
            float(kept) + DURATION_TOLERANCE_SECONDS,
            "the length the post stage kept",
        )
    requested = float(manifest["requirement"]["durationSeconds"])
    return (
        None,
        requested * NONLOOP_MIN_FRACTION,
        requested + NONLOOP_OVERRUN_SECONDS,
        f"the requested {requested:g}s (one-shots are trimmed, so shorter is expected)",
    )


def run_checks(
    manifest: dict[str, Any],
    asset_dir: pathlib.Path,
    review_dir: pathlib.Path,
) -> tuple[dict[str, dict[str, Any]], list[str], dict[str, Any]]:
    """Every mechanical check, plus the spectrograms. Returns (checks, pngs, measurements)."""
    slug = manifest["slug"]
    post_stage = manifest["stages"]["post"]
    outputs = [entry for entry in (post_stage.get("outputs") or []) if isinstance(entry, str)]
    normalize = post_stage.get("normalize") or {}
    target_lufs = normalize.get("targetLufs")
    if not isinstance(target_lufs, (int, float)) or isinstance(target_lufs, bool):
        target_lufs = float(manifest["requirement"]["targetLufs"])
    target_lufs = float(target_lufs)

    checks: dict[str, dict[str, Any]] = {}
    measurements: dict[str, Any] = {}

    # 1. Every recorded output is on disk.
    paths: dict[str, pathlib.Path] = {}
    missing: list[str] = []
    for relative in outputs:
        try:
            path = _common.resolve_inside(asset_dir, relative, f"stages.post.outputs[{relative}]")
        except ValueError as exc:
            missing.append(f"{relative} ({exc})")
            continue
        try:
            present = path.is_file() and path.stat().st_size > 0
        except OSError as exc:
            # The file went away (or became unreadable) between the two calls.
            # That is a missing output, not a crash - a traceback here would
            # leave the stage stuck at in_progress with the previous verdict.
            missing.append(f"{relative} ({exc.strerror or exc})")
            continue
        if present:
            paths[relative] = path
        else:
            missing.append(relative)
    checks["outputs_exist"] = _check(
        not missing and bool(paths),
        f"{len(paths)}/{len(outputs)} recorded outputs present"
        + (f"; missing: {', '.join(missing)}" if missing else ""),
    )

    # 2. Every one of them decodes end to end and measures.
    failures: list[str] = []
    for relative, path in paths.items():
        try:
            measurements[relative] = measure_output(path, target_lufs)
        except post.PostError as exc:
            failures.append(f"{relative}: {exc.message.splitlines()[0]}")
    checks["decodes"] = _check(
        bool(measurements) and not failures,
        "every output decodes and measures" if not failures else "; ".join(failures),
    )

    # 3. Length, against what the post stage says it produced.
    expected, low, high, how = expected_duration(manifest)
    wrong = [
        f"{relative} is {data['seconds']:.3f}s"
        for relative, data in measurements.items()
        if not low <= data["seconds"] <= high
    ]
    checks["duration"] = _check(
        bool(measurements) and not wrong,
        (
            f"all outputs are {expected:.3f}s (+/-{DURATION_TOLERANCE_SECONDS:g}s), {how}"
            if expected is not None and not wrong
            else f"all outputs are within {low:.2f}-{high:.2f}s, {how}"
            if not wrong
            else f"expected {low:.3f}-{high:.3f}s ({how}); " + ", ".join(wrong)
        ),
    )

    # 4. Loudness of the file an engine actually loads, re-measured.
    reference = f"post/{slug}.wav" if f"post/{slug}.wav" in measurements else None
    reference = reference or next(
        (name for name in measurements if name.endswith(".wav")),
        next(iter(measurements), None),
    )
    checks["loudness"] = _loudness_check(reference, measurements, normalize, target_lufs, post_stage)

    # 5. True peak. The tolerance is an allowance for what a lossy encoder adds
    #    when it reconstructs its own waveform. A PCM file is a sample-for-sample
    #    copy of the master, so it has no such excuse and is held to the ceiling.
    hot = [
        f"{relative} at {data['truePeakDbtp']:+.2f} dBTP (limit {_peak_limit(relative):+.2f})"
        for relative, data in measurements.items()
        if data["truePeakDbtp"] is not None and data["truePeakDbtp"] > _peak_limit(relative)
    ]
    peaks = [data["truePeakDbtp"] for data in measurements.values() if data["truePeakDbtp"] is not None]
    checks["true_peak"] = _check(
        bool(measurements) and not hot,
        f"loudest output {max(peaks):+.2f} dBTP, ceiling "
        f"{post.TRUE_PEAK_CEILING_DBTP:g} dBTP (+{TRUE_PEAK_TOLERANCE_DB:g} for lossy exports only)"
        if peaks and not hot
        else "; ".join(hot) or "no true-peak measurement",
    )

    # 6. Not silent.
    silent = [
        f"{relative} at {_rms_text(data['rmsDbfs'])}"
        for relative, data in measurements.items()
        if data["rmsDbfs"] is None or data["rmsDbfs"] < SILENCE_FLOOR_DBFS
    ]
    levels = [data["rmsDbfs"] for data in measurements.values() if data["rmsDbfs"] is not None]
    checks["not_silent"] = _check(
        bool(measurements) and not silent,
        f"quietest output {min(levels):.1f} dBFS RMS, floor {SILENCE_FLOOR_DBFS:g} dBFS"
        if levels and not silent
        else "; ".join(silent) or "nothing to measure",
    )

    # 7. The loop seam, re-measured on the shipped file.
    loop_record = post_stage.get("loopProcessing") or {}
    if loop_record.get("loop") and reference in paths:
        checks["loop_seam"] = _seam_check(paths[reference], reference, measurements[reference],
                                          loop_record)

    # 8. Spectrograms - not a verdict input on their own, but a render that
    # fails means the file cannot be inspected, which is worth failing on.
    pngs: list[str] = []
    render_failures: list[str] = []
    for relative, path in paths.items():
        if not relative.lower().endswith(".wav"):
            continue
        target = review_dir / f"{pathlib.PurePosixPath(relative).stem}-spectrogram.png"
        try:
            render_spectrogram(path, target)
            pngs.append(target.relative_to(asset_dir).as_posix())
        except post.PostError as exc:
            render_failures.append(f"{relative}: {exc.message.splitlines()[0]}")
    checks["spectrogram"] = _check(
        bool(pngs) and not render_failures,
        f"rendered {', '.join(pngs)}" if not render_failures else "; ".join(render_failures),
    )
    return checks, pngs, measurements


def _loudness_check(
    reference: str | None,
    measurements: dict[str, Any],
    normalize: dict[str, Any],
    target_lufs: float,
    post_stage: dict[str, Any],
) -> dict[str, Any]:
    if reference is None:
        return _check(False, "no decodable output to measure")
    measured = measurements[reference]["integratedLufs"]
    if normalize.get("skipped"):
        return _check(
            True,
            f"{reference} measures "
            + ("n/a" if measured is None else f"{measured:.2f} LUFS")
            + f"; normalization was skipped ({normalize['skipped']}), so the target is advisory",
        )
    if measured is None:
        # R128 gated everything out. On a very short one-shot that is expected;
        # on anything longer it means there is no programme material.
        short = bool(normalize.get("shortProgramme"))
        return _check(
            short,
            f"{reference} has no integrated loudness"
            + (
                f" (under {post.SHORT_PROGRAMME_SECONDS:g}s, so R128 gating is expected to)"
                if short
                else "; R128 found no programme above its gate"
            ),
        )
    delta = measured - target_lufs
    # `delta < 0` only: the shortfall the post stage declared is gain it could
    # NOT apply, so it can explain a file that is too quiet and never one that
    # is too loud. Allowing it in both directions would let a 6 LU overshoot
    # pass on the strength of a 5 LU shortfall in the opposite direction.
    if delta < 0 and abs(delta) > LOUDNESS_TOLERANCE_LU and normalize.get("targetShortfallDb"):
        # The post stage recorded that it could not reach the target without
        # breaching the true-peak ceiling. That is a deliberate, documented
        # trade-off, not a broken export - it fails only if it is short by MORE
        # than the shortfall it declared.
        allowed = LOUDNESS_TOLERANCE_LU + float(normalize["targetShortfallDb"])
        return _check(
            abs(delta) <= allowed,
            f"{reference} measures {measured:.2f} LUFS, {delta:+.2f} LU from "
            f"{target_lufs:g}; the post stage declared a "
            f"{float(normalize['targetShortfallDb']):.2f} LU shortfall against the "
            f"{post.TRUE_PEAK_CEILING_DBTP:g} dBTP ceiling",
        )
    return _check(
        abs(delta) <= LOUDNESS_TOLERANCE_LU,
        f"{reference} measures {measured:.2f} LUFS, {delta:+.2f} LU from the "
        f"{target_lufs:g} LUFS target (tolerance +/-{LOUDNESS_TOLERANCE_LU:g} LU)",
    )


def _seam_check(
    path: pathlib.Path, name: str, measured: dict[str, Any], loop_record: dict[str, Any]
) -> dict[str, Any]:
    try:
        metric = post.seam_metric(
            path, measured["sampleRate"], measured["channels"], measured["samples"]
        )
    except post.PostError as exc:
        return _check(False, f"{name}: {exc.message.splitlines()[0]}")
    recorded = loop_record.get("seamRatio")
    return _check(
        bool(metric["seamOk"]),
        f"{name} wraps with a seam ratio of {metric['seamRatio']} "
        f"(limit {post.SEAM_RATIO_LIMIT:g}; the post stage recorded {recorded})",
    )


def print_report(slug: str, checks: dict[str, dict[str, Any]], pngs: list[str], verdict: str) -> None:
    print("")
    print(f"Review of '{slug}': {verdict.upper()}")
    for name, result in checks.items():
        print(f"  [{'PASS' if result['pass'] else 'FAIL'}] {name}: {result['detail']}")
    if pngs:
        print("  spectrograms: " + ", ".join(pngs))
    if verdict == "fail":
        print("")
        print("Failing checks and what they mean:")
        for name, result in checks.items():
            if not result["pass"]:
                print(f"  {name}: {result['detail']}")
                print(f"    -> {_REMEDY.get(name, 'inspect the file and re-run the post stage.')}")


_REMEDY = {
    "outputs_exist": "re-run post_process.py; the manifest describes files that are not there.",
    "decodes": "the file is truncated or corrupt - re-run post_process.py to rewrite it.",
    "duration": "the file on disk is not the cut the post stage recorded; re-run post_process.py.",
    "loudness": "re-run post_process.py (without --skip-normalize) to normalize to the target.",
    "true_peak": "re-run post_process.py; the export is hot enough to clip on decode.",
    "not_silent": "the take has no audible content - re-run the generate stage with a new seed.",
    "loop_seam": "re-run post_process.py with a longer --crossfade-ms, or regenerate the take: "
                 "the wrap is a bigger jump than the music around it.",
    "spectrogram": "check the ffmpeg build - showspectrumpic is part of a standard build.",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Review the post stage's outputs of one audio asset and record a verdict"
    )
    parser.add_argument("slug", nargs="?", help="asset slug, e.g. 'chiptune-loop'")
    parser.add_argument("--base", default=None, help="workspace holding audio-pipeline-output/")
    parser.add_argument("--selftest", action="store_true", help="run the built-in assertions")
    args = parser.parse_args(argv)

    if args.selftest:
        return _selftest()
    if not args.slug:
        parser.error("a slug is required (or pass --selftest)")

    base = pathlib.Path(args.base).expanduser().resolve() if args.base else None
    try:
        manifest = _manifest.read(args.slug, base)
    except FileNotFoundError as exc:
        LOGGER.error("%s", exc)
        return _common.EXIT_USER_ERROR
    except (ValueError, json.JSONDecodeError) as exc:
        LOGGER.error("Manifest is not usable: %s", exc)
        return _common.EXIT_MANIFEST_CORRUPT

    post_stage = manifest["stages"]["post"]
    outputs = [entry for entry in (post_stage.get("outputs") or []) if isinstance(entry, str)]
    if post_stage.get("status") != "done" or not outputs:
        LOGGER.error(
            "stages.post.status is %r with %d outputs. Run the post stage first: "
            "python post_process.py %s",
            post_stage.get("status"),
            len(outputs),
            args.slug,
        )
        return _common.EXIT_USER_ERROR

    asset_dir = _common.output_dir(args.slug, base)
    if _common.is_dry_run():
        print("")
        print(f"Review plan for '{args.slug}'")
        for relative in outputs:
            print(f"  check   {relative}")
        for relative in outputs:
            if relative.lower().endswith(".wav"):
                print(f"  render  review/{pathlib.PurePosixPath(relative).stem}-spectrogram.png")
        print("  checks  outputs_exist, decodes, duration, loudness, true_peak, not_silent"
              + (", loop_seam" if (post_stage.get("loopProcessing") or {}).get("loop") else "")
              + ", spectrogram")
        print("")
        print("AUDIO_PIPELINE_DRY_RUN=1: nothing was measured and the manifest is unchanged.")
        return _common.EXIT_OK

    review_dir = _common.stage_dir(args.slug, "review", base)
    # Clear the previous verdict before measuring anything. If this run dies
    # halfway, the manifest must not still be showing the last run's `pass`
    # against files that have since been rewritten.
    _manifest.update_stage(
        args.slug,
        "review",
        {"status": "in_progress", "checks": None, "verdict": None, "clapScore": None,
         "spectrograms": [], "measurements": None},
        base,
    )
    try:
        checks, pngs, measurements = run_checks(manifest, asset_dir, review_dir)
    except (post.PostError, OSError) as exc:
        message = exc.message if isinstance(exc, post.PostError) else str(exc)
        LOGGER.error("%s", message)
        _manifest.update_stage(args.slug, "review", {"status": "failed", "verdict": "fail"}, base)
        return _common.EXIT_USER_ERROR

    verdict = "pass" if all(result["pass"] for result in checks.values()) else "fail"
    _manifest.update_stage(
        args.slug,
        "review",
        {
            # A failed verdict leaves the stage `failed`, so manifest-driven
            # resume comes back to it instead of treating the asset as finished.
            "status": "done" if verdict == "pass" else "failed",
            "checks": checks,
            "clapScore": None,
            "verdict": verdict,
            "spectrograms": pngs,
            "measurements": measurements,
        },
        base,
    )
    print_report(args.slug, checks, pngs, verdict)
    return _common.EXIT_OK if verdict == "pass" else _common.EXIT_USER_ERROR


def _selftest() -> int:
    """A real loop asset through post and review, then the same asset broken.

    Everything here is measured from files, so the check is only worth anything
    against files that really were written: the tone is generated, processed by
    the post stage, and reviewed exactly as an asset would be.
    """
    import tempfile

    rate = 48000
    with tempfile.TemporaryDirectory(prefix="review-selftest-") as tmp:
        workspace = pathlib.Path(tmp)
        _manifest.init(
            "selftest-review", "bgm", "auto",
            {"prompt": "selftest", "durationSeconds": 8.0, "bpm": 120, "formats": ["wav", "ogg"]},
            workspace,
        )
        stage = _common.stage_dir("selftest-review", "generate", workspace)
        post._tone(stage / "cand-01.wav", 440.0, 8.0, rate)
        _manifest.update_stage(
            "selftest-review", "generate",
            {"status": "done", "backend": "acestep",
             "candidates": [_manifest.make_candidate("generate/cand-01.wav", 1, "acestep",
                                                     {"bpm": 120, "beatsPerBar": 4})]},
            workspace,
        )
        assert post.main(["selftest-review", "--base", str(workspace)]) == _common.EXIT_OK

        assert main(["selftest-review", "--base", str(workspace)]) == _common.EXIT_OK
        review = _manifest.read("selftest-review", workspace)["stages"]["review"]
        assert review["verdict"] == "pass" and review["status"] == "done", review
        assert review["clapScore"] is None, review
        assert all(entry["pass"] for entry in review["checks"].values()), review["checks"]
        # Every check named in the contract really ran, and the loop asset got
        # its seam measured.
        assert {"outputs_exist", "decodes", "duration", "loudness", "true_peak",
                "not_silent", "loop_seam", "spectrogram"} == set(review["checks"]), review["checks"]
        asset = _common.output_dir("selftest-review", workspace)
        for relative in review["spectrograms"]:
            assert (asset / relative).stat().st_size > 0, relative

        # A truncated export is the failure this stage exists to catch: the
        # manifest still describes the full-length file.
        export = asset / "post/selftest-review.ogg"
        blob = export.read_bytes()
        export.write_bytes(blob[: len(blob) // 3])
        assert main(["selftest-review", "--base", str(workspace)]) == _common.EXIT_USER_ERROR
        broken = _manifest.read("selftest-review", workspace)["stages"]["review"]
        assert broken["verdict"] == "fail", broken
        # A failing verdict must leave the stage resumable, not "done".
        assert broken["status"] == "failed", broken
        assert broken["checks"]["duration"]["pass"] is False, broken["checks"]["duration"]

        # A declared shortfall excuses a file that is too QUIET, never one that
        # is too loud: the gain the post stage could not apply cannot explain an
        # overshoot in the other direction.
        quiet = {"targetLufs": -16.0, "targetShortfallDb": 5.0}
        assert _loudness_check("x", {"x": {"integratedLufs": -20.0}}, quiet, -16.0, {})["pass"]
        loud = _loudness_check("x", {"x": {"integratedLufs": -10.0}}, quiet, -16.0, {})
        assert loud["pass"] is False, loud
        # ...and the ordinary tolerance still applies in both directions.
        assert _loudness_check("x", {"x": {"integratedLufs": -16.4}}, {}, -16.0, {})["pass"]
        assert _loudness_check("x", {"x": {"integratedLufs": -14.5}}, {}, -16.0, {})["pass"] is False

        # The lossy allowance is for lossy files only.
        assert _peak_limit("post/a.ogg") > _peak_limit("post/a.wav")
        assert _peak_limit("post/a.wav") == post.TRUE_PEAK_CEILING_DBTP + post.TRUE_PEAK_TOLERANCE_DB

        # The seam is measured from the exact sample count ffprobe reports, not
        # from a rounded duration. A file 7 samples past a whole millisecond
        # proves the difference: the rounded seconds reconstruct to 96000, and
        # reading the last window there would miss the real end of the file.
        odd = asset / "review/odd.wav"
        post.run_ffmpeg(["-i", str(asset / "post/master.wav"), "-af",
                         "atrim=start_sample=0:end_sample=96007", "-c:a", "pcm_s16le",
                         "-y", str(odd)])
        measured = measure_output(odd, -16.0)
        assert measured["samples"] == 96007, measured
        assert int(round(measured["seconds"] * measured["sampleRate"])) == 96000, measured
        odd.unlink()

        # A silent export fails the floor even though it decodes fine.
        post.run_ffmpeg(["-f", "lavfi", "-i", f"anullsrc=r={rate}:cl=stereo:d=4",
                         "-c:a", "pcm_s16le", "-y", str(asset / "post/selftest-review.wav")])
        assert main(["selftest-review", "--base", str(workspace)]) == _common.EXIT_USER_ERROR
        silent = _manifest.read("selftest-review", workspace)["stages"]["review"]["checks"]
        assert silent["not_silent"]["pass"] is False, silent["not_silent"]

    print("review_asset selftest: ok")
    return _common.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
