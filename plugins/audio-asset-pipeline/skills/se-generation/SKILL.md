---
name: se-generation
description: This skill should be used when the user asks to "generate a sound effect", "SFX", "SE", "footstep sound", "UI sound", "impact sound", "sword whoosh", "magical chime", "ambience", or as the generate stage of the audio asset pipeline on the Stable Audio 3 backend. Covers model routing between the small-sfx and medium checkpoints, prompt recipes for realistic foley and stylized SFX, reference-audio conditioning, seeded variation batches for games, and short-SE trimming. Also triggers on "/audio-asset-pipeline:se" and on mentions of audio-pipeline-output, pipeline.json, generate_sa3.py, or Stable Audio 3.
---

# Sound Effect Generation (Stable Audio 3)

Produce candidate `.wav` files for one sound effect and record them in the asset
manifest, so the post and review stages have something to work on.

## Quick Start

Locate the installed plugin directory first; `<plugin-root>` below is that
directory, and every script path is relative to it. Keep the working directory
in the workspace that contains `audio-pipeline-output/`. On Windows, use
`py -3` if `python3` is not available.

1. Confirm the environment once per machine:

```bash
python3 "<plugin-root>/scripts/doctor.py" --stack sa3
```

   The Stable Audio 3 weights live in **gated** Hugging Face repositories. The
   first real generation fails with `model_download_failed` (a 401
   `GatedRepoError`) until the licence is accepted at
   `huggingface.co/stabilityai/stable-audio-3-small-sfx` while signed in and a
   read token is available locally. Provide the token in any of these ways:
   put `HF_TOKEN=<token>` in the plugin's private env file
   `~/.claude/audio-pipeline/.env` (the driver passes it through to the
   backend), export `HF_TOKEN`, or run `hf auth login` with the `hf` CLI from
   the sa3 environment. The old `huggingface-cli` command was removed in
   huggingface_hub 1.x. Doctor does not catch this, the first run does.

2. Create the manifest if the asset does not have one yet:

```bash
python3 "<plugin-root>/scripts/init_asset.py" door-open --type se --mode manual \
  --prompt "wooden door creaking open, interior, close mic" --duration 3
```

3. Generate candidates:

```bash
python3 "<plugin-root>/scripts/backends/generate_sa3.py" door-open
```

4. Listen to every file under `audio-pipeline-output/<slug>/generate/`, then
   record the chosen one in `stages.generate.selected` before moving on.

Useful flags: `--model`, `--candidates N`, `--seed N`, `--negative-prompt`,
`--out-name-prefix`, `--base <workspace>`, `--device`.

## Model Routing

| Model | Use it for | VRAM | Max length | Flash Attention 2 |
| --- | --- | --- | --- | --- |
| `small-sfx` | Default. Fast exploration, one-shot SFX, foley, short ambience. | ~2 GB | 120 s | not needed |
| `medium` | Quality re-render of an approved idea, longer musical or ambient beds. | ~5-6.5 GB | 380 s | **required** |

- `--model auto` (the default) picks `small-sfx` for `assetType: se` and
  `medium` for `assetType: bgm`. `medium` on a BGM asset is for ambient beds and
  textures with no musical structure; for actual music (tempo, key, loops,
  vocals) use the `bgm-generation` skill and its ACE-Step backend instead.
- Explore on `small-sfx` first. It is quick enough to run several batches while
  the prompt is still being tuned.
- `medium` without Flash Attention 2 does not crash, it produces glitchy audio.
  The backend detects this and refuses to run rather than writing a broken file.
  `setup_env.py --stack sa3` installs a prebuilt `flash_attn` wheel matching
  torch 2.7.1 / CUDA 12.8 on Windows and Linux x86-64 for CPython 3.11 and 3.12;
  on any other interpreter or platform it prints where to find one and `medium`
  stays unavailable until it is installed. `doctor.py --stack sa3` reports
  `extra flash_attn` either way. `small-sfx` never needs it.
- Measured on a 12 GB card: `medium` renders 60 s of ambience in about 3 s of
  compute once loaded, but the first call also downloads and loads the
  checkpoint - budget around 9 minutes wall clock for a cold first run.

## Writing The Prompt

The prompt lives in `requirement.prompt`; entries in `requirement.styleTags`
are appended to it automatically.

Describe the **sound**, not the story. Name the material, the action, the space,
and the mic distance:

- `wooden door creaking open, interior, close mic`
- `heavy metal impact on concrete, short decay, no reverb tail`
- `single footstep on wet gravel, close mic, dry`

Use `--negative-prompt` to push away what keeps leaking in, most often
`music, speech, reverb, noise`.

Read `references/prompt-recipes.md` for realistic foley, ambience, impact, and
stylized/anime recipes with worked examples.

### Give The Sound Room To Decay

Stable Audio 3 fills whatever window it is given. Ask for a window barely longer
than the event and it renders a sustained texture instead of an event with a
tail - no transient, no decay, and `leadingSilenceSeconds` /
`trailingSilenceSeconds` both come back at `0.00`, which is the tell.

Measured, same prompt (`bright magical sparkle chime, anime style, ascending,
cute`) on `small-sfx`:

| `--duration` | What came out |
| --- | --- |
| `2.5` | Flat broadband shimmer for the whole 2.5 s, no onset, no decay. Held across 4 seeds and a re-worded prompt. |
| `6` | Real one-shot: transient at 0.05 s, ascending shimmer, then a decay visible on the spectrogram out to about 5.3 s. Silence figures 0.05 s / 3.05 s - the tail drops under the -45 dBFS content floor at 2.95 s and keeps ringing below it. |

So for anything with a tail - chimes, impacts, whooshes, magic - request roughly
twice the length of the audible event and let the post stage trim to the content
it finds. This is the same reasoning as **Short Sound Effects** below, one step
further up the scale.

## Reference Audio

Set `requirement.referenceAudio` to an absolute or workspace-relative path to
condition generation on an existing sound. Text prompt and reference can be
combined; either one alone is enough to run.

`requirement.referenceStrength` is how strongly the reference should survive, so
**higher means closer to the reference**. The backend inverts it into Stable
Audio 3's `init_noise_level`; nothing outside the backend needs to know that.

| Value | Result |
| --- | --- |
| `0.9` | Close variation. Same sound, different take. |
| `0.7` | Default. Recognisably related, clearly re-generated. |
| `0.5` | Halfway blend between the reference and the prompt. |
| `0.1` | The reference barely survives; effectively prompt-only. |

Values outside `0.0`-`1.0` are rejected when the manifest is validated.

## Variation Batches

Games need several takes of the same sound or repeated playback turns into a
machine-gun rattle. Generate a batch and keep the ones that differ:

```bash
python3 "<plugin-root>/scripts/backends/generate_sa3.py" footstep-gravel --candidates 5
```

- Manual mode defaults to 3 candidates, auto mode to 1.
- Each candidate gets its own seed. Pass `--seed N` to make a batch
  reproducible: candidate N uses `seed + N - 1`.
- Re-running appends (`cand-04.wav`, `cand-05.wav`, ...) instead of overwriting
  earlier takes, so nothing is lost by trying again.
- For a variation set, prefer several seeds on one prompt over several prompts.
  Same character, different take, which is what a footstep set needs.

## Short Sound Effects

Stable Audio 3 works on a roughly 10.76 Hz latent grid, so a request under two
seconds lands on a handful of latent frames and comes out unreliable. The
backend therefore generates at least 2 s regardless of the requirement and
records `requestedDurationSeconds` in the candidate params.

For a 0.3 s UI blip: keep `requirement.durationSeconds` at the length actually
wanted, let the backend generate its 2 s, and let the post stage trim it. Prompt for
the transient itself (`short UI click, dry, no tail`) so the useful part sits at
the very start of the file.

## Dry Run

Set `AUDIO_PIPELINE_DRY_RUN=1` to exercise the whole flow without a GPU or the
sa3 environment. ffmpeg synthesizes a 44.1 kHz stereo tone per candidate at the
right duration and the manifest is filled in as usual, with `dryRun: true` in
the candidate params. Use it to check wiring, never to judge audio.

## When It Fails

The backend records a `stages.generate.failureKind` and prints an actionable
message. Do not retry blindly; fix the named cause first.

| failureKind | What to do |
| --- | --- |
| `user_error` | Missing prompt, missing reference file, duration over the model limit, missing ffmpeg, or missing sa3 environment. The message names which. |
| `missing_flash_attn` | Use `--model small-sfx`, or install a matching `flash_attn` wheel. |
| `oom` | Shorten the duration, close other GPU work, or drop from `medium` to `small-sfx`. |
| `model_download_failed` | Usually the gated repository: accept the model licence on Hugging Face and set `HF_TOKEN` (see Quick Start step 1). Otherwise check the network. |
| `backend_error` | Read the message; it carries the worker's own error. |
| `timeout` | The run exceeded 30 minutes. Usually a stalled first-run weight download. |

## Verification Checklist

Before declaring the generate stage done, confirm all of the following:

- `stages.generate.status` is `done` and `stages.generate.backend` is `sa3`.
- Every entry in `stages.generate.candidates` has a `file` like
  `generate/cand-01.wav` that exists on disk and is non-empty.
- Each candidate records the seed that produced it.
- The files are 44.1 kHz stereo and their duration matches the request within a
  tolerance (a later stage checks this properly; `ffprobe` is enough here).
- Nothing is clipped or silent on a quick listen.
- `stages.generate.failureKind` is `null`.

If any item fails, fix it and re-verify before moving to the post stage.

## Next Stage

After selecting a candidate, run the post stage - see the `loop-and-postprocess`
skill. It trims the dead air and the decay tail, normalizes to
`requirement.targetLufs` (-12 LUFS for sound effects) under a -1.0 dBTP ceiling,
and writes the 16-bit WAV and OGG an engine loads:

```bash
python3 "<plugin-root>/scripts/post_process.py" <slug> --candidate generate/cand-01.wav
```

## Reference Index

- `references/prompt-recipes.md` covers prompt patterns for realistic foley,
  ambience, impacts, and stylized SFX, plus the limits of prompt-only styling.
