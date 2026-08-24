"""MiniMax-Music3 generation worker.

This module runs INSIDE the minimax virtual environment
(`~/.claude/audio-pipeline/venvs/minimax`), so it may import torch, torchaudio
and diffusers. It must never import `_common` or `_manifest`: those belong to
the driver's interpreter, which is a different Python. Everything the worker
needs arrives in a request JSON file and leaves in a result JSON file.

Usage (invoked by scripts/backends/generate_minimax.py, not by hand):
    <venv python> _minimax_worker.py --request <request.json>

Request JSON:
    {
      "repo": "MiniMaxAI/MiniMax-Music3",
      "device": "cuda" | "cuda:1" | null,   # null -> the current CUDA device
      "prompt": "Genre: ... Vocals: ... Arrangement: ...",
      "lyrics": "[verse]\\n...\\n[chorus]\\n...",
      "durationSeconds": 90.0,              # an UPPER BOUND, not a target
      "numInferenceSteps": 30,
      "candidates": [{"seed": 123, "output": "<absolute .wav path>"}, ...],
      "resultPath": "<absolute path>"
    }

Result JSON (always written, success or failure):
    {"ok": true, "model": ..., "runtime": {...}, "candidates": [...]}
    {"ok": false, "error": {"kind": ..., "message": ...}}

Error kinds are a closed vocabulary the driver maps onto manifest failure kinds:
    user_error | oom | model_download_failed | backend_error

The integration is the diffusers modular pipeline shipped in diffusers 0.40.0
(`diffusers.modular_pipelines.minimax_music3`): `ModularPipeline.from_pretrained`
resolves the checkpoint's `modular_model_index.json` and `load_components` pulls
the seven components it names. The model's own repository also ships weights for
an SGLang server, but that path needs a server process, has no Windows build,
and would duplicate a 40 GB download; the diffusers path is the maintainable one.
"""

from __future__ import annotations

import pathlib
import sys
import time
from typing import Any

# Sibling module in this file's own directory, which is sys.path[0] for a
# script launched by absolute path - no package install needed inside the venv.
from _worker_common import (
    WorkerError,
    classify,
    looks_like_download_failure,
    measure_silence,
    run_cli,
    save_wav,
    to_stereo,
)

# The full pipeline in bfloat16 needs roughly 22 GB of VRAM with plain CPU
# offloading (the model card's own figure). Below that the 8B language model has
# to be streamed leaf by leaf, which the same card documents as the path that
# fits an 8 GB device. Cards at or above the threshold skip it: leaf-level
# streaming is several times slower and there is nothing to gain from it.
GROUP_OFFLOAD_VRAM_GIB = 22.0

# How far short of the requested ceiling the language model may stop before the
# shortfall is worth saying out loud. `audio_duration` is an upper bound by
# design, so small undershoots are normal and only a large one is news.
SHORT_SONG_RATIO = 0.9


def resolve_device(request: dict[str, Any]) -> Any:
    """The execution device as a concrete torch.device with an explicit index.

    Returns a device carrying a real index rather than a bare "cuda", and makes
    it the process's current device. Both matter here: the group-offloading
    hooks create their prefetch streams on the CURRENT device, and the memory
    statistics are per device, so a run on cuda:1 would otherwise stream through
    and be measured against cuda:0.

    MiniMax-Music3 has no CPU inference path worth offering: the autoregressive
    stage alone would take hours per candidate, so a non-CUDA request is refused
    rather than silently served at unusable speed.
    """
    import torch

    requested = str(request.get("device") or "").strip()
    if not requested:
        requested = "cuda" if torch.cuda.is_available() else "cpu"

    try:
        device = torch.device(requested)
    except (RuntimeError, ValueError, TypeError) as exc:
        raise WorkerError("user_error", f"--device {requested!r} is not a torch device: {exc}") from exc

    if device.type != "cuda":
        raise WorkerError(
            "user_error",
            f"MiniMax-Music3 requires a CUDA device, but the resolved device is "
            f"{device}. "
            + (
                "torch reports no CUDA device is available; check the driver "
                "installation, or re-run `python setup_env.py --stack minimax` if the "
                "environment resolved a CPU-only torch wheel."
                if not torch.cuda.is_available()
                else "Pass --device cuda (or cuda:N)."
            ),
        )
    if not torch.cuda.is_available():
        raise WorkerError(
            "user_error",
            f"device {device} was requested but torch reports no CUDA device. Check the "
            "driver installation, or re-run `python setup_env.py --stack minimax` if the "
            "environment resolved a CPU-only torch wheel.",
        )

    count = torch.cuda.device_count()
    index = torch.cuda.current_device() if device.index is None else device.index
    if not 0 <= index < count:
        raise WorkerError(
            "user_error",
            f"--device {requested!r} names GPU {index}, but this machine has "
            f"{count} CUDA device(s) (valid indices 0-{count - 1}).",
        )

    device = torch.device("cuda", index)
    torch.cuda.set_device(device)
    return device


def preflight_prompt(request: dict[str, Any]) -> int | None:
    """Reject an over-long prompt before 27 GB of weights load. Returns the count.

    The tokenizer is a few megabytes, so this costs seconds; discovering the same
    refusal after the pipeline has loaded costs minutes. The prompt is assembled
    with the checkpoint's OWN helpers from the pinned diffusers module rather
    than a reimplementation here - the special-token scaffold is part of the
    checkpoint contract and a private copy of it would drift silently.

    Returns None when that private surface has moved under a different diffusers
    build. Nothing breaks: the pipeline raises the same ValueError later, and
    generate() maps it to the same user_error. This is a fast path, not a gate.
    """
    try:
        from transformers import Qwen2Tokenizer

        from diffusers.modular_pipelines.minimax_music3.encoders import (
            _AUDIO_START,
            _CAPTION_END,
            _CAPTION_START,
            _IM_END,
            _IM_START,
            _LYRICS_END,
            _LYRICS_START,
            _MAX_PROMPT_TOKENS,
            _clean_caption,
            _normalize_lyrics,
        )
    except ImportError as exc:
        print(f"note: skipping the prompt-length preflight ({exc})", file=sys.stderr)
        return None

    try:
        tokenizer = Qwen2Tokenizer.from_pretrained(request["repo"], subfolder="tokenizer")
    except Exception as exc:
        text = f"{type(exc).__name__}: {exc}"
        if looks_like_download_failure(text):
            raise WorkerError(
                "model_download_failed", f"Fetching the MiniMax-Music3 tokenizer failed: {text}"
            ) from exc
        print(f"note: skipping the prompt-length preflight ({text})", file=sys.stderr)
        return None

    assembled = (
        f"{_IM_START}{_CAPTION_START}{_clean_caption(request['prompt'])}{_CAPTION_END}"
        f"{_LYRICS_START}{_normalize_lyrics(request['lyrics'])}{_LYRICS_END}"
        f"{_IM_END}{_AUDIO_START}"
    )
    count = int(tokenizer(assembled, return_tensors="pt")["input_ids"].shape[1])
    if count > _MAX_PROMPT_TOKENS:
        raise WorkerError(
            "user_error",
            f"The caption and lyrics tokenize to {count} tokens, past MiniMax-Music3's "
            f"limit of {_MAX_PROMPT_TOKENS}. Shorten requirement.prompt, "
            "requirement.styleTags or requirement.lyrics by roughly "
            f"{count - _MAX_PROMPT_TOKENS} tokens and re-run.",
        )
    return count


def load_pipeline(request: dict[str, Any], device: Any) -> tuple[Any, dict[str, Any]]:
    """Load the modular pipeline and size it for the card. Returns (pipe, info)."""
    import torch

    try:
        from diffusers import ComponentsManager, ModularPipeline
        from diffusers.hooks import apply_group_offloading
    except Exception as exc:
        raise WorkerError(
            "backend_error",
            f"Cannot import the diffusers MiniMax-Music3 integration ({type(exc).__name__}: "
            f"{exc}). Re-run setup_env.py --stack minimax.",
        ) from exc

    total_gib = torch.cuda.get_device_properties(device).total_memory / 1024**3

    # The components manager keeps only what a step is using on the card and
    # parks the rest in system RAM. It is what makes a 27 GB pipeline start at
    # all on a consumer GPU.
    manager = ComponentsManager()
    manager.enable_auto_cpu_offload(device=device)

    try:
        pipe = ModularPipeline.from_pretrained(request["repo"], components_manager=manager)
        pipe.load_components(dtype=torch.bfloat16)
    except Exception as exc:
        text = f"{type(exc).__name__}: {exc}"
        if looks_like_download_failure(text):
            raise WorkerError(
                "model_download_failed",
                f"Fetching the MiniMax-Music3 components failed: {text} The diffusers "
                "components measure 27 GB; check the network connection and the free "
                "space on the drive holding the Hugging Face cache.",
            ) from exc
        raise WorkerError(classify(exc), f"Loading MiniMax-Music3 failed: {text}") from exc

    offloading = "auto_cpu_offload"
    if total_gib < GROUP_OFFLOAD_VRAM_GIB:
        # Leaf-level streaming of the 8B global language model. This is the one
        # knob that decides whether the model runs on a 12 GB card at all, and it
        # is the reason a candidate costs minutes rather than seconds.
        apply_group_offloading(
            pipe.language_model,
            onload_device=device,
            offload_type="leaf_level",
            use_stream=True,
        )
        offloading = "auto_cpu_offload+language_model_leaf_level"

    info = {
        "device": str(device),
        "gpuMemoryGb": round(total_gib, 2),
        "offloading": offloading,
        "dtype": "bfloat16",
        "sampleRate": int(pipe.sampling_rate),
        "frameRate": float(pipe.frame_rate),
    }
    return pipe, info


def short_song_warning(actual: float, ceiling: float) -> str | None:
    """Say so when the language model ended the song well short of the ceiling."""
    if actual >= ceiling * SHORT_SONG_RATIO:
        return None
    return (
        f"the language model ended the song at {actual:.1f}s of a {ceiling:.1f}s ceiling; "
        "lengthen the lyrics or add sections if a longer track is needed"
    )


def generate(request: dict[str, Any]) -> dict[str, Any]:
    import torch

    device = resolve_device(request)
    prompt_tokens = preflight_prompt(request)
    load_started = time.monotonic()
    pipe, info = load_pipeline(request, device)
    load_seconds = time.monotonic() - load_started
    info["promptTokens"] = prompt_tokens

    sample_rate = int(pipe.sampling_rate)
    ceiling = float(request["durationSeconds"])
    steps = int(request.get("numInferenceSteps") or 30)
    peak_bytes = 0
    results: list[dict[str, Any]] = []

    for entry in request["candidates"]:
        seed = int(entry["seed"])
        output = pathlib.Path(entry["output"])
        torch.cuda.reset_peak_memory_stats(device)

        started = time.monotonic()
        try:
            audios = pipe(
                prompt=request["prompt"],
                lyrics=request["lyrics"],
                audio_duration=ceiling,
                num_inference_steps=steps,
                generator=torch.Generator(device).manual_seed(seed),
                output_type="pt",
                output="audios",
            )
        except ValueError as exc:
            # Every ValueError the pipeline raises is an input-contract violation:
            # an empty caption or lyrics, an assembled prompt over 5000 tokens, an
            # audio_duration under one frame, or a prompt that ended generation
            # before a single frame was emitted. All of those are the user's to fix.
            raise WorkerError(
                "user_error", f"MiniMax-Music3 rejected the request: {exc}"
            ) from exc
        except WorkerError:
            raise
        except Exception as exc:
            kind = classify(exc)
            hint = (
                " Shorten the duration, close other GPU work, or generate one candidate "
                "per run."
                if kind == "oom"
                else ""
            )
            raise WorkerError(
                kind,
                f"Generation failed for seed {seed} ({type(exc).__name__}: {exc}).{hint}",
            ) from exc
        elapsed = time.monotonic() - started

        # `output="audios"` yields (batch, channels, samples); one prompt in, one
        # song out. Anything else means the integration changed under us.
        if audios is None or len(audios) == 0:
            raise WorkerError(
                "backend_error", f"MiniMax-Music3 returned no audio for seed {seed}"
            )
        waveform = to_stereo(audios[0].detach().cpu().float())
        actual_seconds = waveform.shape[-1] / float(sample_rate)
        # Measured on the tensor before anything else can touch the file: the
        # language model decides when the song ends, so the driver needs the dead
        # air at both ends to judge whether the take can loop.
        leading_silence, trailing_silence = measure_silence(waveform, sample_rate)
        save_wav(waveform, output, sample_rate)

        peak_bytes = max(peak_bytes, int(torch.cuda.max_memory_allocated(device)))
        del waveform, audios
        # empty_cache has no device argument - it acts on the current device, which
        # resolve_device() already set to this one.
        torch.cuda.empty_cache()

        warning = short_song_warning(actual_seconds, ceiling)
        if warning:
            print(f"warning: {output.name}: {warning}", file=sys.stderr)
        results.append(
            {
                "output": output.as_posix(),
                "seed": seed,
                "generationSeconds": round(elapsed, 2),
                "actualDurationSeconds": round(actual_seconds, 3),
                "leadingSilenceSeconds": leading_silence,
                "trailingSilenceSeconds": trailing_silence,
                "warning": warning,
                "params": {
                    "model": request["repo"],
                    "steps": steps,
                    # The ceiling that was asked for, not what came back; the
                    # measured length is actualDurationSeconds above.
                    "durationCeilingSeconds": ceiling,
                    "sampleRate": sample_rate,
                    "offloading": info["offloading"],
                    "dtype": info["dtype"],
                },
            }
        )

    info["peakVramGb"] = round(peak_bytes / 1024**3, 2)
    return {
        "ok": True,
        "model": request["repo"],
        "sampleRate": sample_rate,
        "modelLoadSeconds": round(load_seconds, 2),
        "runtime": info,
        "candidates": results,
    }


def _selftest() -> int:
    """Assertions for the shortfall warning and device parsing. Needs the minimax venv."""
    import torch

    assert short_song_warning(60.0, 60.0) is None
    assert short_song_warning(55.0, 60.0) is None  # inside the normal undershoot
    message = short_song_warning(30.0, 60.0)
    assert message is not None and "30.0s of a 60.0s ceiling" in message, message

    def rejects(device: Any) -> str:
        try:
            resolve_device({"device": device})
        except WorkerError as exc:
            assert exc.kind == "user_error", exc.kind
            return exc.message
        raise AssertionError(f"expected resolve_device to reject {device!r}")

    # CPU is refused whether or not this machine has a GPU: there is no CPU path.
    assert "requires a CUDA device" in rejects("cpu")
    assert "not a torch device" in rejects("gpu0")

    if torch.cuda.is_available():
        count = torch.cuda.device_count()
        # An out-of-range index must be named, not silently coerced to cuda:0.
        assert f"{count} CUDA device(s)" in rejects(f"cuda:{count}")
        # Both an empty request and a bare "cuda" resolve to a concrete index,
        # and that index becomes the current device.
        for request_device in (None, "cuda"):
            device = resolve_device({"device": request_device})
            assert device.type == "cuda" and device.index is not None, device
            assert torch.cuda.current_device() == device.index, device
    else:
        print("note: no CUDA device, skipping the index assertions", file=sys.stderr)

    print("_minimax_worker selftest: ok")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(_selftest())
    sys.exit(run_cli(generate, "MiniMax-Music3 generation worker (venv-side)"))
