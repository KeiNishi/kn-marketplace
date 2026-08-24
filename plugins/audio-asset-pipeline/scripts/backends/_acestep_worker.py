"""ACE-Step 1.5 generation worker.

This module runs INSIDE the acestep virtual environment
(`~/.claude/audio-pipeline/venvs/acestep`), so it may import torch, torchaudio
and `acestep`. It must never import `_common` or `_manifest`: those belong to
the driver's interpreter, which is a different Python. Everything the worker
needs arrives in a request JSON file and leaves in a result JSON file.

Usage (invoked by scripts/backends/generate_acestep.py, not by hand):
    <venv python> _acestep_worker.py --request <request.json>

Request JSON:
    {
      "model": "acestep-v15-turbo",         # checkpoint directory name
      "device": "cuda" | null,              # null -> auto
      "dataDir": "<absolute path>",         # holds checkpoints/ and .cache/
      "caption": "...",
      "lyrics": "[Instrumental]" | "...",
      "instrumental": true,
      "durationSeconds": 34.286,
      "bpm": 140 | null,
      "timeSignature": "4/4",
      "inferenceSteps": 8,
      "guidanceScale": 7.0 | null,          # non-turbo checkpoints only
      "lmNegativePrompt": "..." | null,
      "referenceAudio": "<absolute path>" | null,
      "referenceStrength": 0.7 | null,
      "candidates": [{"seed": 123, "output": "<absolute .wav path>"}, ...],
      "resultPath": "<absolute path>"
    }

Result JSON (always written, success or failure):
    {"ok": true, "model": ..., "sampleRate": 48000, "candidates": [...]}
    {"ok": false, "error": {"kind": ..., "message": ...}}

Error kinds are a closed vocabulary the driver maps onto manifest failure kinds:
    user_error | oom | model_download_failed | backend_error

ACE-Step's public Python surface is `acestep.inference.generate_music(dit, llm,
GenerationParams, GenerationConfig)`; the Gradio app in
`acestep.acestep_v15_pipeline` is only a UI on top of it. This worker drives the
same two handlers the app initializes, so it inherits upstream's own defaults
without depending on the UI, the API server, or vLLM (which has no Windows
build).
"""

from __future__ import annotations

import os
import pathlib
import sys
import time
from typing import Any

# Sibling module in this file's own directory, which is sys.path[0] for a
# script launched by absolute path - no package install needed inside the venv.
from _worker_common import (
    WorkerError,
    classify,
    duration_warning,
    looks_like_download_failure,
    measure_silence,
    run_cli,
    save_wav,
    to_stereo,
)

# ACE-Step 1.5 renders 48 kHz stereo. The pipeline contract downstream (loop
# points, LUFS normalization, OGG export) only assumes stereo, and records
# whatever rate came back.
TARGET_SAMPLE_RATE = 48000
# The 5Hz LM planner's PyTorch backend. vLLM is the upstream default but has no
# Windows build, and MLX is Apple Silicon only; 'pt' is the one backend that
# runs everywhere this plugin supports.
LM_BACKEND = "pt"
# torch.compile needs Triton, which has no supported Windows build, and the
# compile step costs minutes on every cold start for a few percent of speed.
COMPILE_MODEL = False


def prepare_environment(data_dir: str) -> pathlib.Path:
    """Point ACE-Step's caches at the plugin's private data directory.

    Upstream resolves both the checkpoints folder and its progress cache from
    the CURRENT WORKING DIRECTORY unless these variables are set. The driver
    runs from the user's game workspace, so without this the first generation
    would drop a multi-gigabyte `checkpoints/` tree straight into their
    repository.
    """
    root = pathlib.Path(data_dir).expanduser()
    checkpoints = root / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    os.environ["ACESTEP_PROJECT_ROOT"] = str(root)
    os.environ["ACESTEP_CHECKPOINTS_DIR"] = str(checkpoints)
    # The worker's stderr is captured, not a terminal; progress bars would only
    # fill the failure tail with carriage returns.
    os.environ.setdefault("ACESTEP_DISABLE_TQDM", "1")
    return checkpoints


def load_handlers(request: dict[str, Any], checkpoints: pathlib.Path) -> tuple[Any, Any, dict[str, Any]]:
    """Initialize the DiT renderer and the LM planner. Returns (dit, llm, info).

    Sizing (offload, quantization, LM choice) comes from upstream's own GPU tier
    table rather than from hardcoded numbers here: it is the same table the
    Gradio app uses, and it already knows what fits on the card it finds.
    """
    try:
        from acestep.gpu_config import get_gpu_config, set_global_gpu_config
        from acestep.handler import AceStepHandler
        from acestep.llm_inference import LLMHandler
        from acestep.model_downloader import DEFAULT_LM_MODEL, ensure_lm_model
    except Exception as exc:
        raise WorkerError(
            "backend_error",
            f"Cannot import acestep ({type(exc).__name__}: {exc}). "
            "Re-run setup_env.py --stack acestep.",
        ) from exc

    device = request.get("device") or "auto"
    gpu_config = get_gpu_config()
    set_global_gpu_config(gpu_config)

    dit = AceStepHandler()
    try:
        use_flash_attention = bool(dit.is_flash_attention_available(device))
    except Exception:  # probing must never be the thing that fails a run
        use_flash_attention = False

    quantization = "int8_weight_only" if gpu_config.quantization_default else None
    status, ok = dit.initialize_service(
        project_root=str(checkpoints.parent),
        config_path=request["model"],
        device=device,
        use_flash_attention=use_flash_attention,
        compile_model=COMPILE_MODEL,
        offload_to_cpu=gpu_config.offload_to_cpu_default,
        offload_dit_to_cpu=gpu_config.offload_dit_to_cpu_default,
        quantization=quantization,
        prefer_source=None,
    )
    if not ok:
        kind = "model_download_failed" if looks_like_download_failure(status) else "backend_error"
        raise WorkerError(
            kind,
            f"Initializing the DiT model '{request['model']}' failed: {status}"
            + (
                " The weights come from the ACE-Step Hugging Face repositories; check the "
                "network connection and the free space on the drive holding "
                f"{checkpoints.as_posix()}."
                if kind == "model_download_failed"
                else ""
            ),
        )

    # The LM planner is what turns a caption into structured musical metadata and
    # semantic codes. It is optional: without it the DiT still renders from the
    # caption alone, just with less musical structure. A card too small for the
    # planner must not lose the ability to generate at all.
    llm = LLMHandler()
    lm_model = gpu_config.recommended_lm_model or DEFAULT_LM_MODEL
    lm_status = "not initialized (GPU tier default)"
    if gpu_config.init_lm_default and lm_model:
        downloaded, message = ensure_lm_model(model_name=lm_model, checkpoints_dir=checkpoints)
        if not downloaded:
            raise WorkerError(
                "model_download_failed",
                f"Downloading the 5Hz LM planner '{lm_model}' failed: {message}",
            )
        lm_status, lm_ok = llm.initialize(
            checkpoint_dir=str(checkpoints),
            lm_model_path=lm_model,
            backend=LM_BACKEND,
            device=device,
            offload_to_cpu=gpu_config.offload_to_cpu_default,
            dtype=None,
        )
        if not lm_ok:
            print(
                f"warning: the 5Hz LM planner did not initialize ({lm_status}); "
                "falling back to the DiT-only path",
                file=sys.stderr,
            )

    info = {
        "gpuTier": gpu_config.tier,
        "gpuMemoryGb": round(float(gpu_config.gpu_memory_gb), 2),
        "quantization": quantization,
        "offloadToCpu": bool(gpu_config.offload_to_cpu_default),
        "offloadDitToCpu": bool(gpu_config.offload_dit_to_cpu_default),
        "flashAttention": use_flash_attention,
        "lmModel": lm_model if llm.llm_initialized else None,
        "lmBackend": LM_BACKEND if llm.llm_initialized else None,
        "lmStatus": lm_status,
        "initStatus": status,
    }
    return dit, llm, info


def build_params(request: dict[str, Any], seed: int) -> Any:
    """One GenerationParams for one candidate."""
    from acestep.inference import GenerationParams

    kwargs: dict[str, Any] = {
        "task_type": "text2music",
        "caption": request.get("caption") or "",
        "lyrics": request.get("lyrics") or "",
        "instrumental": bool(request.get("instrumental")),
        "duration": float(request["durationSeconds"]),
        "bpm": request.get("bpm"),
        "timesignature": request.get("timeSignature") or "",
        "inference_steps": int(request["inferenceSteps"]),
        "seed": seed,
        # The LM planner is the point of the hybrid architecture: it writes the
        # musical plan (metadata plus semantic codes) the DiT then renders.
        "thinking": True,
        # ...but the caption stays exactly as the user wrote it. CoT caption
        # rewriting would quietly discard prompt details the requirement is
        # explicit about, the loop hints most of all.
        "use_cot_caption": False,
        "use_cot_metas": True,
        "use_cot_language": True,
    }
    guidance = request.get("guidanceScale")
    if guidance is not None:
        # Distilled turbo checkpoints ignore CFG; only base/sft honour it.
        kwargs["guidance_scale"] = float(guidance)
    if request.get("lmNegativePrompt"):
        # ACE-Step has no negative prompt for the DiT. This one steers the LM
        # planner's classifier-free guidance, which is the only negative lever
        # the API exposes.
        kwargs["lm_negative_prompt"] = str(request["lmNegativePrompt"])
    if request.get("referenceAudio"):
        kwargs["reference_audio"] = request["referenceAudio"]
        strength = request.get("referenceStrength")
        if strength is not None:
            # audio_cover_strength is "how much of the reference conditioning
            # survives": 1.0 keeps it whole, lower blends back toward the
            # prompt-only branch. Same direction as referenceStrength.
            kwargs["audio_cover_strength"] = float(strength)
    return GenerationParams(**kwargs)


def check_reference_audio(path_str: str) -> None:
    """A missing or unreadable reference is the user's input, not a backend fault."""
    path = pathlib.Path(path_str)
    if not path.is_file():
        raise WorkerError("user_error", f"Reference audio not found: {path.as_posix()}")


def generate(request: dict[str, Any]) -> dict[str, Any]:
    import torch

    if request.get("referenceAudio"):
        check_reference_audio(request["referenceAudio"])

    checkpoints = prepare_environment(request["dataDir"])
    load_started = time.monotonic()
    dit, llm, info = load_handlers(request, checkpoints)
    load_seconds = time.monotonic() - load_started

    from acestep.inference import GenerationConfig, generate_music

    duration = float(request["durationSeconds"])
    results: list[dict[str, Any]] = []
    for entry in request["candidates"]:
        seed = int(entry["seed"])
        output = pathlib.Path(entry["output"])

        params = build_params(request, seed)
        # One candidate per call: batching would share the LM plan across seeds
        # and multiply peak VRAM, and a 12 GB card is the design target.
        config = GenerationConfig(
            batch_size=1,
            use_random_seed=False,
            seeds=[seed],
            audio_format="wav",
        )

        started = time.monotonic()
        try:
            # save_dir=None: generate_music hands back the tensor and this worker
            # writes it under the candidate's own name. Upstream would otherwise
            # save it under a content-hash file name of its own choosing.
            result = generate_music(dit, llm, params, config, save_dir=None)
        except WorkerError:
            raise
        except Exception as exc:
            raise WorkerError(
                classify(exc), f"Generation failed for seed {seed} ({type(exc).__name__}: {exc})."
            ) from exc
        elapsed = time.monotonic() - started

        if not result.success or not result.audios:
            message = result.error or result.status_message or "no detail reported"
            kind = "model_download_failed" if looks_like_download_failure(message) else "backend_error"
            if "out of memory" in message.lower():
                kind = "oom"
            hint = ""
            if kind == "oom":
                hint = (
                    " Shorten the duration, close other GPU work, or generate fewer "
                    "candidates per run."
                )
            raise WorkerError(kind, f"Generation failed for seed {seed}: {message}{hint}")

        audio = result.audios[0]
        tensor = audio.get("tensor")
        if tensor is None:
            raise WorkerError(
                "backend_error",
                f"ACE-Step returned no audio tensor for seed {seed}; it reported: "
                f"{result.status_message or '(no status)'}",
            )
        sample_rate = int(audio.get("sample_rate") or TARGET_SAMPLE_RATE)
        waveform = to_stereo(tensor.detach().cpu().float())
        actual_seconds = waveform.shape[-1] / float(sample_rate)
        # Measured here, on the tensor, before anything else can touch the file:
        # the LM planner regularly ends a song before the requested bar count and
        # pads the rest with silence, which the driver has to see to judge
        # whether the take can loop.
        leading_silence, trailing_silence = measure_silence(waveform, sample_rate)
        save_wav(waveform, output, sample_rate)

        # The tensors are the largest live allocation; dropping them before the
        # next generation is what keeps peak VRAM at one candidate's worth.
        del waveform, tensor, audio, result
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
                "leadingSilenceSeconds": leading_silence,
                "trailingSilenceSeconds": trailing_silence,
                "warning": warning,
                "params": {
                    "model": request["model"],
                    "steps": int(request["inferenceSteps"]),
                    "guidanceScale": request.get("guidanceScale"),
                    "durationSeconds": duration,
                    "bpm": request.get("bpm"),
                    "timeSignature": request.get("timeSignature") or None,
                    "instrumental": bool(request.get("instrumental")),
                    "lmNegativePrompt": request.get("lmNegativePrompt"),
                    "referenceAudio": request.get("referenceAudio"),
                    "referenceStrength": request.get("referenceStrength"),
                    "lmModel": info["lmModel"],
                    "quantization": info["quantization"],
                },
            }
        )

    return {
        "ok": True,
        "model": request["model"],
        "sampleRate": TARGET_SAMPLE_RATE,
        "modelLoadSeconds": round(load_seconds, 2),
        "runtime": info,
        "candidates": results,
    }


if __name__ == "__main__":
    sys.exit(run_cli(generate, "ACE-Step 1.5 generation worker (venv-side)"))
