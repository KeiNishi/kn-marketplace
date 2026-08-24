"""Stable Audio 3 generation worker.

This module runs INSIDE the sa3 virtual environment
(`~/.claude/audio-pipeline/venvs/sa3`), so it may import torch, torchaudio and
`stable_audio_3`. It must never import `_common` or `_manifest`: those belong to
the driver's interpreter, which is a different Python. Everything the worker
needs arrives in a request JSON file and leaves in a result JSON file.

Usage (invoked by scripts/backends/generate_sa3.py, not by hand):
    <venv python> _sa3_worker.py --request <request.json>

Request JSON:
    {
      "model": "small-sfx" | "small-music" | "medium",
      "device": "cuda" | null,              # null -> auto
      "prompt": "...",
      "negativePrompt": "..." | null,
      "durationSeconds": 3.0,
      "steps": 8,
      "cfgScale": 1.0,
      "chunkedDecode": true,
      "initAudio": "<absolute path>" | null,
      "initNoiseLevel": 0.3,
      "candidates": [{"seed": 123, "output": "<absolute .wav path>"}, ...],
      "resultPath": "<absolute path>"
    }

Result JSON (always written, success or failure):
    {"ok": true, "model": ..., "sampleRate": 44100, "candidates": [...]}
    {"ok": false, "error": {"kind": ..., "message": ...}}

Error kinds are a closed vocabulary the driver maps onto manifest failure kinds:
    user_error | missing_flash_attn | oom | model_download_failed | backend_error
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import sys
import time
import traceback
from typing import Any

# Stable Audio 3 renders at 44.1 kHz stereo; the pipeline contract downstream
# (loop points, LUFS normalization, OGG export) assumes exactly that.
TARGET_SAMPLE_RATE = 44100
TARGET_CHANNELS = 2
# Written audio may drift from the request by a rounding step; anything past this
# means the model produced a different length than asked for (the classic symptom
# is a missing sample_size, which silently truncates long medium generations).
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
# Only the medium DiT ships fused attention kernels that need Flash Attention 2.
# Without it the model still runs and still writes a file - the audio is just
# quietly wrong, which is the one failure mode a user cannot detect from a log.
FLASH_ATTN_MODELS = frozenset({"medium"})
# Substrings that mark a weight-fetch problem rather than a compute problem.
# Checked case-insensitively against the exception text raised by from_pretrained.
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
    "resolve",
    "no such file or directory",
)


class WorkerError(Exception):
    """A failure that maps onto one of the structured error kinds."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


def flash_attn_status() -> tuple[bool, str]:
    """Whether Flash Attention 2 is present AND actually loadable.

    find_spec alone is not enough: the common Windows failure is an installed
    wheel built against a different torch/CUDA ABI, which imports with a DLL
    error. Importing it is the cheap, real probe.
    """
    if importlib.util.find_spec("flash_attn") is None:
        return False, "not installed"
    try:
        import flash_attn  # noqa: F401
    except Exception as exc:  # ImportError, OSError (DLL), RuntimeError
        return False, f"installed but not importable ({type(exc).__name__}: {exc})"
    return True, "ok"


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


def load_model(model_id: str, device: str | None) -> Any:
    ok, detail = flash_attn_status()
    if model_id in FLASH_ATTN_MODELS and not ok:
        raise WorkerError(
            "missing_flash_attn",
            f"Model '{model_id}' requires Flash Attention 2, but flash_attn is {detail}. "
            "Without it this model still produces a wav file, but the audio is glitchy, "
            "so generation is refused instead. Use --model small-sfx (no flash-attn "
            f"needed), or install a flash-attn wheel matching torch 2.7.1/cu128 into "
            f"{pathlib.Path(sys.executable).as_posix()}.",
        )

    try:
        from stable_audio_3 import StableAudioModel
    except Exception as exc:
        raise WorkerError(
            "backend_error",
            f"Cannot import stable_audio_3 ({type(exc).__name__}: {exc}). "
            "Re-run setup_env.py --stack sa3.",
        ) from exc

    kwargs: dict[str, Any] = {}
    if device:
        kwargs["device"] = device
    try:
        return StableAudioModel.from_pretrained(model_id, **kwargs)
    except WorkerError:
        raise
    except Exception as exc:
        text = str(exc).lower()
        kind = "model_download_failed" if any(m in text for m in _DOWNLOAD_MARKERS) else classify(exc)
        hint = ""
        if kind == "model_download_failed":
            hint = (
                " The Stable Audio 3 weights are gated: accept the licence for "
                f"'stabilityai/stable-audio-3-{model_id}' on huggingface.co while signed "
                "in, then provide a token - set HF_TOKEN (the pipeline also reads it "
                "from ~/.claude/audio-pipeline/.env), or run `hf auth login` with the "
                "sa3 environment's `hf` CLI. Otherwise check the network connection."
            )
        raise WorkerError(
            kind, f"Loading model '{model_id}' failed ({type(exc).__name__}: {exc}).{hint}"
        ) from exc


def load_init_audio(path_str: str) -> tuple[int, Any]:
    import torchaudio

    path = pathlib.Path(path_str)
    # A bad reference file is the user's input, not a backend fault: it is fixed
    # by pointing at a different file, not by retrying.
    if not path.is_file():
        raise WorkerError("user_error", f"Reference audio not found: {path.as_posix()}")
    try:
        waveform, sample_rate = torchaudio.load(str(path))
    except Exception as exc:
        raise WorkerError(
            "user_error",
            f"Could not read reference audio {path.as_posix()} "
            f"({type(exc).__name__}: {exc}). Convert it to wav or flac first.",
        ) from exc
    return int(sample_rate), waveform


def sample_rate_of(model: Any) -> int:
    """The model's own rate, with the documented 44.1 kHz as the last resort."""
    for holder in (model, getattr(model, "model", None)):
        rate = getattr(holder, "sample_rate", None)
        if isinstance(rate, int) and rate > 0:
            return rate
    return TARGET_SAMPLE_RATE


def partial_path(output: pathlib.Path) -> pathlib.Path:
    """Temp name for the in-progress write of `output`.

    Keeps the original extension so torchaudio can still infer the container
    format. generate_sa3.cleanup_attempt mirrors this rule to remove leftovers.
    """
    return output.with_name(f".{output.stem}{PARTIAL_INFIX}{output.suffix}")


def model_sample_size(model: Any) -> int | None:
    """The model's native latent window, which generate() needs to size output.

    Upstream's own CLI always passes this. None means the config did not expose
    it, in which case generate() falls back to its default and the written
    duration check below is what catches any resulting truncation.
    """
    config = getattr(model, "model_config", None)
    if isinstance(config, dict):
        value = config.get("sample_size")
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            return value
    return None


def duration_warning(actual: float, requested: float) -> str | None:
    tolerance = max(DURATION_TOLERANCE_FLOOR, requested * DURATION_TOLERANCE_RATIO)
    if abs(actual - requested) <= tolerance:
        return None
    return (
        f"wrote {actual:.2f}s of audio for a {requested:.2f}s request "
        f"(tolerance {tolerance:.2f}s)"
    )


def to_stereo(waveform: Any) -> Any:
    """Force a (channels, samples) tensor to stereo.

    SA3 already returns stereo; this only guards the contract so a mono model
    variant cannot silently break the post stage's channel assumptions.
    """
    if waveform.dim() == 1:
        waveform = waveform.unsqueeze(0)
    channels = waveform.shape[0]
    if channels == TARGET_CHANNELS:
        return waveform
    if channels == 1:
        return waveform.repeat(TARGET_CHANNELS, 1)
    return waveform[:TARGET_CHANNELS]


def generate(request: dict[str, Any]) -> dict[str, Any]:
    import torch
    import torchaudio

    model_id = request["model"]
    duration = float(request["durationSeconds"])
    steps = int(request.get("steps", 8))
    cfg_scale = float(request.get("cfgScale", 1.0))
    chunked_decode = bool(request.get("chunkedDecode", True))
    prompt = request.get("prompt") or ""
    negative_prompt = request.get("negativePrompt") or None

    init_audio = None
    init_noise_level = None
    if request.get("initAudio"):
        init_audio = load_init_audio(request["initAudio"])
        init_noise_level = float(request.get("initNoiseLevel", 0.3))

    load_started = time.monotonic()
    model = load_model(model_id, request.get("device"))
    load_seconds = time.monotonic() - load_started
    sample_rate = sample_rate_of(model)
    sample_size = model_sample_size(model)

    results: list[dict[str, Any]] = []
    for entry in request["candidates"]:
        seed = int(entry["seed"])
        output = pathlib.Path(entry["output"])
        output.parent.mkdir(parents=True, exist_ok=True)

        kwargs: dict[str, Any] = {
            "prompt": prompt,
            "duration": duration,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "seed": seed,
            "batch_size": 1,
            "chunked_decode": chunked_decode,
        }
        # Without sample_size the model falls back to its default window and
        # silently truncates anything longer, which is how a 250s medium request
        # comes back as 120s of audio with no error anywhere.
        if sample_size is not None:
            kwargs["sample_size"] = sample_size
        if negative_prompt:
            kwargs["negative_prompt"] = negative_prompt
        if init_audio is not None:
            kwargs["init_audio"] = init_audio
            kwargs["init_noise_level"] = init_noise_level

        started = time.monotonic()
        try:
            audio = model.generate(**kwargs)
        except WorkerError:
            raise
        except Exception as exc:
            kind = classify(exc)
            hint = ""
            if kind == "oom":
                hint = (
                    " Free VRAM, shorten the duration, or switch to --model small-sfx "
                    "(~2 GB) instead of medium (~5-6.5 GB)."
                )
            raise WorkerError(
                kind,
                f"Generation failed for seed {seed} ({type(exc).__name__}: {exc}).{hint}",
            ) from exc
        elapsed = time.monotonic() - started

        waveform = to_stereo(audio[0].detach().cpu().float())
        actual_seconds = waveform.shape[-1] / float(sample_rate)
        # Write beside the target, then rename: a crash mid-encode must not leave
        # a truncated wav sitting at the candidate's final name.
        partial = partial_path(output)
        torchaudio.save(str(partial), waveform, sample_rate)
        os.replace(partial, output)

        # The tensors are the largest live allocation; dropping them before the
        # next generate() is what keeps peak VRAM at one candidate's worth.
        del audio, waveform
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        warning = duration_warning(actual_seconds, duration)
        if warning:
            print(f"warning: {output.name}: {warning}", file=sys.stderr)
        results.append(
            {
                "output": output.as_posix(),
                "seed": seed,
                "generationSeconds": round(elapsed, 2),
                "actualDurationSeconds": round(actual_seconds, 3),
                "warning": warning,
                "params": {
                    "model": model_id,
                    "steps": steps,
                    "cfgScale": cfg_scale,
                    "durationSeconds": duration,
                    "negativePrompt": negative_prompt,
                    "initAudio": request.get("initAudio"),
                    "initNoiseLevel": init_noise_level,
                },
            }
        )

    return {
        "ok": True,
        "model": model_id,
        "sampleRate": sample_rate,
        "sampleSize": sample_size,
        "modelLoadSeconds": round(load_seconds, 2),
        "candidates": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stable Audio 3 generation worker (venv-side)")
    parser.add_argument("--request", required=True, help="path to the request JSON file")
    args = parser.parse_args(argv)

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
            "error": {
                "kind": "backend_error",
                "message": f"{type(exc).__name__}: {exc}",
            },
        }
        traceback.print_exc()
        exit_code = 1

    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
