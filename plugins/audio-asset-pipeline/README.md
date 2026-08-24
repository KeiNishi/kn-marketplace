# Audio Asset Pipeline

## Overview

A four-stage pipeline that turns a description of a sound into a shipping game
audio asset, using models that run **locally on your own GPU**. No API keys, no
per-asset cost, no upload of your project's material to a vendor.

```
requirement -> generate -> post -> review
```

| Stage | Script | Produces |
| --- | --- | --- |
| `requirement` | `scripts/init_asset.py` | `audio-pipeline-output/<slug>/pipeline.json` |
| `generate` | `scripts/backends/generate_sa3.py`, `generate_acestep.py`, `generate_minimax.py` | Candidate WAVs with seed, params and silence measurements |
| `post` | `scripts/post_process.py` | `post/master.wav` plus 16-bit WAV and OGG exports: trimmed, bar-exact loop, EBU R128 normalized |
| `review` | `scripts/review_asset.py` | A measured pass/fail verdict and a spectrogram per shipped WAV |

Selection and approval sit between `generate` and `post`, recorded by
`scripts/approve_asset.py`.

### Two modes

- **auto** - never asks a question, never waits. Infers the requirement from the
  conversation, generates one candidate, selects it mechanically, posts and
  reviews. `approved` stays `false`, because approval is a human act.
- **manual** - elicits the requirement, generates three candidates, presents them
  and **stops**. `post_process.py` refuses to run until a human has selected and
  approved a take; the approval is bound to the file it was given for.

The mode is fixed at `init_asset.py` time and lives in `manifest.mode`.

### Three backends

| Backend | Use it for | Speed on a 12 GB card |
| --- | --- | --- |
| Stable Audio 3 (`small-sfx`) | Sound effects, foley, UI blips, one-shots. Up to 120 s. | Seconds per candidate |
| Stable Audio 3 (`medium`) | Ambient beds and textures - no musical structure, no BPM. Up to 380 s. | ~3 s of compute for 60 s of audio |
| ACE-Step 1.5 | Instrumental music, themes, loops. The only backend with tempo and bar control, so the only one the post stage can snap a loop to whole bars. | ~17 s for a 31 s instrumental; ~60 s for a 30 s vocal take |
| MiniMax-Music3 | The vocal take that has to carry a scene. Best-in-class singing. | ~36 minutes for 75 s of music |

Model loading adds a minute or two per run on top of those figures, and the
first ever call to a model also downloads it.

## Installation

```
/plugin marketplace add KeiNishi/kn-marketplace
/plugin install audio-asset-pipeline@kn-marketplace
```

## Setup

No API keys. What it does need:

- **Python 3.12 or 3.11** available to create the per-backend virtual
  environments (3.13 is not supported by the model projects yet).
- **ffmpeg with ffprobe on `PATH`** - the post and review stages are built on it.
- **An NVIDIA GPU.** 12 GB is comfortable; `small-sfx` fits in about 2 GB and
  `medium` in about 5-6.5 GB.
- **About 60 GB of disk**: ~24 GB for the three virtual environments and
  ACE-Step's checkpoint tree, ~36 GB for the Hugging Face cache that holds
  Stable Audio 3 (~5 GB) and MiniMax-Music3 (27 GB). Set `HF_HOME` to move the
  cache to a roomier drive - never to a path inside a git repository.

Create the environments (each backend gets its own, because the three projects
pin incompatible torch versions):

```bash
/audio-asset-pipeline:setup-audio --stack all     # or --stack sa3|acestep|minimax
/audio-asset-pipeline:check-audio                 # doctor: python, ffmpeg, venvs, GPU, disk
```

`setup_env.py` installs a CUDA 12.8 torch build over whatever CPU wheel the
model projects resolve, and installs a prebuilt `flash_attn` wheel for the sa3
stack (Windows and Linux x86-64, CPython 3.11/3.12). Flash Attention 2 is what
the Stable Audio 3 `medium` model needs; where no prebuilt wheel exists,
`setup-audio` prints where to look for one and `medium` refuses to run rather
than emitting glitchy audio. `small-sfx` never needs it.

### Gated weights

The `stabilityai/stable-audio-3-*` repositories are gated. Accept the license on
Hugging Face while signed in, then put a read token in
`~/.claude/audio-pipeline/.env` (`%USERPROFILE%/.claude/audio-pipeline/.env` on
Windows):

```
HF_TOKEN=hf_...
```

That file lives **outside any repository** by design. Never put a token in the
manifest, a prompt, a log line, or anything under your project.

## Quick Start

```
/audio-asset-pipeline:se metallic sword whoosh, sharp, dry --duration 2
/audio-asset-pipeline:bgm looping medieval town theme, lute and flute --duration 60 --bpm 110
```

Both run the whole pipeline, honouring the asset's mode. Stage by stage:

```
/audio-asset-pipeline:init-audio door-open --type se --mode manual --prompt "wooden door creaking open, interior, close mic" --duration 3
/audio-asset-pipeline:se door-open
/audio-asset-pipeline:approve door-open --select generate/cand-02.wav --approve
/audio-asset-pipeline:post-audio door-open
/audio-asset-pipeline:review-audio door-open
/audio-asset-pipeline:audio-info door-open
```

Everything lands under `audio-pipeline-output/<slug>/` in the workspace you run
from:

```
audio-pipeline-output/door-open/
  pipeline.json          # the manifest - the source of truth for every stage
  generate/cand-01.wav   # candidates, one per seed
  post/master.wav        # the float master
  post/door-open.wav     # 16-bit shipping WAV
  post/door-open.ogg     # Vorbis q6
  review/*.png           # spectrograms
```

## Commands

| Command | What it does |
| --- | --- |
| `/init-audio` | Create the manifest for one asset. |
| `/se` | Sound effect, end to end, on Stable Audio 3. |
| `/bgm` | Background music, end to end, on ACE-Step or MiniMax-Music3. |
| `/approve` | Record which candidate ships, and the human approval for it. |
| `/post-audio` | Trim, loop, normalize, export. |
| `/review-audio` | Measure the exports and render spectrograms. |
| `/audio-info` | Print one asset's manifest status. |
| `/check-audio` | Health check the whole environment. |
| `/setup-audio` | Create or repair a backend environment. |

## Skills

| Skill | Covers |
| --- | --- |
| `audio-pipeline-overview` | Stage routing, the two modes, approval gates, backend selection, manifest-driven resume. |
| `se-generation` | Stable Audio 3: model routing, prompt recipes, reference-audio conditioning, variation batches, short one-shots. |
| `bgm-generation` | ACE-Step and MiniMax-Music3: genre and instrumentation prompts, BPM and bar snapping, lyrics and section tags, the MiniMax license notice. |
| `loop-and-postprocess` | Bar-exact loop trimming, seam crossfade with a measured seam check, EBU R128 normalization with a true-peak ceiling, WAV/OGG export. |

## Post-processing

The post stage is where a generated take becomes a shippable file.

- **Loop trimming.** A model asked for 60 s of a 110 BPM loop usually stops
  singing before the file ends. The post stage finds the last contentful bar and
  cuts there, so the loop is a whole number of bars rather than a whole number of
  seconds. Needs `requirement.bpm` and `requirement.timeSignature`; without them
  no snapping happens at all.
- **Seam crossfade.** Equal-power `qsin` crossfade at the wrap, with a measured
  `seamRatio` reported afterwards. A green seam ratio is not the same as the loop
  sounding right - play it round three times before you believe it.
- **Loudness.** Two-pass EBU R128 loudnorm: **-16 LUFS** for BGM, **-12 LUFS**
  for SE (effects have to cut through the music at the same fader position).
- **True peak.** A **-1.0 dBTP** ceiling on everything, enforced even with
  `--skip-normalize`. A lossy encoder reconstructs its own waveform, so an OGG
  made from a master sitting on the ceiling decodes above it; the post stage
  measures each export and re-encodes it once with exactly that much attenuation,
  recorded as `encoderTrimDb`.

## Dry-Run Mode

```bash
AUDIO_PIPELINE_DRY_RUN=1 python scripts/backends/generate_sa3.py door-open
```

`AUDIO_PIPELINE_DRY_RUN=1` means **use no model**, and the stages honour it
differently:

| Stage | Under the flag |
| --- | --- |
| `init_asset.py`, `approve_asset.py` | No dry-run concept - they only read and write the manifest, and behave the same either way. |
| `generate_*.py` | **Write.** ffmpeg synthesizes a placeholder tone per candidate at the rate and duration the real model would produce (48 kHz for ACE-Step, 44.1 kHz for Stable Audio 3 and MiniMax), and the manifest is filled in as usual with `dryRun: true` in the candidate params. |
| `post_process.py`, `review_asset.py` | **Print the plan and write nothing** - not the files, not the manifest. A dry run stops here, and `review_asset.py` then refuses, correctly, because the post stage produced no outputs. |

To carry a rehearsal all the way through, generate with the flag and then run the
post and review stages **without** it. Neither touches a model or the GPU, and
both process placeholder candidates exactly as they do real ones. Judge wiring,
manifests and bar arithmetic this way - never audio. ffmpeg is required in
dry-run mode too.

## Licensing

**MiniMax-Music3 carries a UI-attribution obligation.** Any commercial product
shipping audio from that backend must display "MiniMax-Music3" prominently in its
user interface (Community License section 3.1), and organizations earning over
US$20M a year need separate written authorization from MiniMax first (section
3.2). The driver prints the notice after every run and records
`params.licenseNotice` on every candidate, so the manifest carries the obligation
forward. Put the credit in the game's credits screen as soon as a MiniMax
candidate is selected, not at ship time.

ACE-Step 1.5 and Stable Audio 3 carry no equivalent clause.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `missing_flash_attn` | The `medium` model needs Flash Attention 2. Re-run `/setup-audio --stack sa3`, or use `--model small-sfx`. |
| 401 `GatedRepoError` on the first Stable Audio 3 run | The weights are gated. Accept the license on Hugging Face and put `HF_TOKEN` in `~/.claude/audio-pipeline/.env`. |
| `oom` | Shorten the duration, close other GPU work, or drop from `medium` to `small-sfx`. |
| Generation is unusably slow | A CPU-only torch got resolved. `/check-audio` reports it; re-run `/setup-audio --stack <stack>`. |
| `post_process.py` refuses with "not approved" | Manual-mode approval gate. Listen to the candidates and run `/approve <slug> --select generate/cand-NN.wav --approve`. This is not a flag you can bypass. |
| Audible seam in a loop | Check `requirement.bpm` and `requirement.timeSignature` are both set - without them nothing was snapped. Then re-generate with a different seed. |
| ffmpeg / ffprobe not found | Install ffmpeg and put it on `PATH`. Required even in dry-run mode. |

## Manifest schema

`schemaVersion` `1.0`. `pipeline.json` is the source of truth: read it before
running a stage and again after every script returns, and resume from the first
stage whose status is `pending` or `failed`. Use the `scripts/_manifest.py`
helpers rather than hand-editing the JSON.

## Author

KN. Part of the [kn-marketplace](https://github.com/KeiNishi/kn-marketplace)
plugin marketplace.
