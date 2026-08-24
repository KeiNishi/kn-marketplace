"""Venv-side helpers shared by the generation workers.

This module runs INSIDE a stack's virtual environment, next to the worker that
imports it (the worker's own directory is always on sys.path). It may import
torch, but it must never import `_common` or `_manifest`: those belong to the
driver's interpreter, which is a different Python.

The driver-side half of the protocol lives in `_backend_common.py`.

Result JSON contract (always written, success or failure):
    {"ok": true, ..., "candidates": [{"output": ..., "seed": ..., "params": {...}}]}
    {"ok": false, "error": {"kind": ..., "message": ...}}

Error kinds are a closed vocabulary the drivers map onto manifest failure kinds:
    user_error | missing_flash_attn | oom | model_download_failed | backend_error
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import traceback
from typing import Any, Callable

# The pipeline contract downstream (loop points, LUFS normalization, OGG export)
# assumes stereo; the sample rate is whatever the model renders at.
TARGET_CHANNELS = 2
# Written audio may drift from the request by a rounding step; anything past this
# means the model produced a different length than asked for.
DURATION_TOLERANCE_RATIO = 0.05
DURATION_TOLERANCE_FLOOR = 0.5
# Infix for the in-progress write. The file is renamed into place only once it
# is complete, so a crash or timeout can never leave a half-written candidate
# that later stages would treat as real audio.
#
# The temp name MUST keep the real .wav extension: torchaudio.save picks the
# container format from the extension, so a '.part' tail makes it raise
# "Unsupported format: part". The leading dot keeps the temp file out of the
# way (hidden on POSIX) without changing how it is encoded.
PARTIAL_INFIX = ".tmp"

# Substrings that mark a weight-fetch problem rather than a compute problem.
# Checked case-insensitively against the exception text.
_DOWNLOAD_MARKERS = (
    "connection",
    "connecterror",
    "couldn't connect",
    "could not connect",
    "timed out",
    "429",
    "404",
    "401",
    "403",
    "gated",
    "unauthorized",
    "offline mode",
    "huggingface.co",
    "modelscope",
    "resolve",
    "no such file or directory",
    "download",
)


class WorkerError(Exception):
    """A failure that maps onto one of the structured error kinds."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


def classify(exc: BaseException) -> str:
    """Map an arbitrary exception onto the structured error vocabulary."""
    import torch

    oom_types: tuple[type[BaseException], ...] = (MemoryError,)
    cuda_oom = getattr(torch, "OutOfMemoryError", None) or getattr(
        torch.cuda, "OutOfMemoryError", None
    )
    if isinstance(cuda_oom, type):
        oom_types = (*oom_types, cuda_oom)
    if isinstance(exc, oom_types):
        return "oom"
    text = str(exc).lower()
    # Older torch paths raise a plain RuntimeError for allocator exhaustion.
    if "out of memory" in text or "cuda error: out of memory" in text:
        return "oom"
    return "backend_error"


def looks_like_download_failure(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _DOWNLOAD_MARKERS)


def partial_path(output: pathlib.Path) -> pathlib.Path:
    """Temp name for the in-progress write of `output`.

    Keeps the original extension so torchaudio can still infer the container
    format. _backend_common.partial_name mirrors this rule to remove leftovers.
    """
    return output.with_name(f".{output.stem}{PARTIAL_INFIX}{output.suffix}")


def to_stereo(waveform: Any) -> Any:
    """Force a (channels, samples) tensor to stereo.

    Both current models already return stereo; this only guards the contract so
    a mono variant cannot silently break the post stage's channel assumptions.
    """
    if waveform.dim() == 1:
        waveform = waveform.unsqueeze(0)
    channels = waveform.shape[0]
    if channels == TARGET_CHANNELS:
        return waveform
    if channels == 1:
        return waveform.repeat(TARGET_CHANNELS, 1)
    return waveform[:TARGET_CHANNELS]


# Dead air detection. -45 dBFS is below the noise floor of anything a game mix
# will reproduce, so a window under it reads as silence to a player even though
# it is not digitally zero (models leave a tiny DC/dither tail). 50 ms windows
# are short enough to locate a cut to well inside a beat, and long enough that a
# single zero crossing inside a loud passage cannot register as a gap.
SILENCE_THRESHOLD_DBFS = -45.0
SILENCE_WINDOW_SECONDS = 0.05


def measure_silence(waveform: Any, sample_rate: int) -> tuple[float, float]:
    """(leading, trailing) seconds of near-silence, rounded to 2 decimals.

    Measured per channel and combined with max(), so content in one channel
    counts as content: averaging first would let two out-of-phase channels
    cancel into a false silence.

    A file that is silent throughout reports its whole length in both figures.
    """
    samples = int(waveform.shape[-1])
    window = max(1, int(round(SILENCE_WINDOW_SECONDS * sample_rate)))
    count = samples // window
    total = round(samples / float(sample_rate), 2)
    if count == 0:
        return 0.0, 0.0

    frames = waveform[..., : count * window]
    if frames.dim() == 1:
        frames = frames.unsqueeze(0)
    rms = frames.reshape(frames.shape[0], count, window).pow(2).mean(dim=-1).sqrt()
    level = rms.max(dim=0).values
    threshold = 10.0 ** (SILENCE_THRESHOLD_DBFS / 20.0)
    loud = (level > threshold).nonzero()
    if loud.numel() == 0:
        return total, total

    first = int(loud[0])
    last = int(loud[-1])
    leading = first * window / float(sample_rate)
    trailing = (samples - (last + 1) * window) / float(sample_rate)
    return round(leading, 2), round(max(0.0, trailing), 2)


def duration_warning(actual: float, requested: float) -> str | None:
    tolerance = max(DURATION_TOLERANCE_FLOOR, requested * DURATION_TOLERANCE_RATIO)
    if abs(actual - requested) <= tolerance:
        return None
    return (
        f"wrote {actual:.2f}s of audio for a {requested:.2f}s request "
        f"(tolerance {tolerance:.2f}s)"
    )


# Every backend writes 32-bit float PCM. Stated explicitly rather than left to
# the default because torchaudio dispatches to whichever backend it finds first
# (soundfile here, FFmpeg elsewhere) and those disagree: FFmpeg's wav muxer
# defaults to 16-bit integer, which would silently quantize a candidate and clip
# the samples MiniMax leaves sitting at +/-1.0. The post stage decides the
# shipped bit depth; generation must not decide it by accident.
WAV_ENCODING = "PCM_F"
WAV_BITS_PER_SAMPLE = 32


def save_wav(waveform: Any, output: pathlib.Path, sample_rate: int) -> None:
    """Write a stereo 32-bit float wav atomically: encode beside the target, then rename.

    A crash mid-encode must not leave a truncated wav sitting at the candidate's
    final name, where later stages would treat it as finished audio.
    """
    import torchaudio

    output.parent.mkdir(parents=True, exist_ok=True)
    partial = partial_path(output)
    torchaudio.save(
        str(partial),
        waveform,
        sample_rate,
        encoding=WAV_ENCODING,
        bits_per_sample=WAV_BITS_PER_SAMPLE,
    )
    # Read the header back rather than trusting the request: a backend that
    # quietly ignored the encoding would hand the post stage int16 audio under a
    # float contract, and nothing downstream re-checks.
    info = torchaudio.info(str(partial))
    if info.encoding != WAV_ENCODING or info.bits_per_sample != WAV_BITS_PER_SAMPLE:
        partial.unlink(missing_ok=True)
        raise WorkerError(
            "backend_error",
            f"torchaudio wrote {output.name} as {info.encoding}/{info.bits_per_sample}-bit "
            f"instead of {WAV_ENCODING}/{WAV_BITS_PER_SAMPLE}-bit. The pipeline's later "
            "stages assume float wav; check the torchaudio backend in this environment.",
        )
    os.replace(partial, output)


def run_cli(generate: Callable[[dict[str, Any]], dict[str, Any]], description: str) -> int:
    """Standard worker entry point: read the request, run, always write a result."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--request", required=True, help="path to the request JSON file")
    args = parser.parse_args()

    request_path = pathlib.Path(args.request)
    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"unreadable request file {request_path}: {exc}", file=sys.stderr)
        return 1

    result_path = pathlib.Path(request["resultPath"])
    try:
        payload = generate(request)
        exit_code = 0
    except WorkerError as exc:
        payload = {"ok": False, "error": {"kind": exc.kind, "message": exc.message}}
        print(f"{exc.kind}: {exc.message}", file=sys.stderr)
        exit_code = 1
    except BaseException as exc:  # keep the driver informed even on KeyboardInterrupt
        payload = {
            "ok": False,
            "error": {"kind": "backend_error", "message": f"{type(exc).__name__}: {exc}"},
        }
        traceback.print_exc()
        exit_code = 1

    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    return exit_code


def _selftest() -> int:
    """Assertions for the silence measurement. Run with a stack's venv python."""
    import torch

    rate = 48000
    silence = torch.zeros(2, rate)
    tone = torch.sin(torch.arange(2 * rate, dtype=torch.float32) * 0.1).repeat(2, 1) * 0.5

    leading, trailing = measure_silence(torch.cat([silence, tone, silence, silence], dim=1), rate)
    assert (leading, trailing) == (1.0, 2.0), (leading, trailing)

    assert measure_silence(tone, rate) == (0.0, 0.0)

    # An entirely silent file reports its whole length both ways.
    assert measure_silence(silence, rate) == (1.0, 1.0)

    # Content in one channel only must not be averaged away.
    half = torch.cat([tone[:1], torch.zeros(1, 2 * rate)], dim=0)
    assert measure_silence(torch.cat([silence, half], dim=1), rate) == (1.0, 0.0)

    # A mono tensor is accepted as a single channel.
    assert measure_silence(torch.cat([silence[0], tone[0]]), rate) == (1.0, 0.0)

    # save_wav must produce 32-bit float wav in every venv, and must leave no
    # partial behind. Samples at exactly +/-1.0 are what int16 would clip.
    import tempfile

    import torchaudio

    with tempfile.TemporaryDirectory() as tmp:
        target = pathlib.Path(tmp) / "check.wav"
        loud = torch.cat([tone, torch.full((2, 100), 1.0), torch.full((2, 100), -1.0)], dim=1)
        save_wav(loud, target, rate)
        info = torchaudio.info(str(target))
        assert info.encoding == WAV_ENCODING, info.encoding
        assert info.bits_per_sample == WAV_BITS_PER_SAMPLE, info.bits_per_sample
        assert info.sample_rate == rate and info.num_channels == TARGET_CHANNELS
        assert not partial_path(target).exists(), "the partial must be renamed away"
        back, back_rate = torchaudio.load(str(target))
        assert back_rate == rate and back.shape == loud.shape, (back_rate, back.shape)
        # Float round-trip is exact; int16 would have clipped these to 0.99997.
        assert float(back.max()) == 1.0 and float(back.min()) == -1.0, (
            float(back.max()),
            float(back.min()),
        )

    print("_worker_common selftest: ok")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] != ["--selftest"]:
        print("this module is a library; pass --selftest to run its assertions", file=sys.stderr)
        sys.exit(2)
    sys.exit(_selftest())
