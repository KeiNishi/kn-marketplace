---
name: bgm-generation
description: This skill should be used when the user asks to "generate BGM", "background music", "game music", "boss theme", "town theme", "looping music", "write a song", "make a soundtrack", or as the generate stage of the audio asset pipeline on the ACE-Step 1.5 backend. Covers prompt structure for genre, instrumentation and mood, BPM and key control, loop-aware bar snapping, instrumental versus vocal tracks with lyrics, reference-audio style conditioning, and backend routing between ACE-Step and Stable Audio 3. Also triggers on "/audio:bgm" and on mentions of audio-pipeline-output, pipeline.json, generate_acestep.py, or ACE-Step.
---

# Background Music Generation (ACE-Step 1.5)

Produce candidate `.wav` files for one music asset and record them in the asset
manifest, so the post and review stages have something to work on.

## Quick Start

Locate the installed plugin directory first; `<plugin-root>` below is that
directory, and every script path is relative to it. Keep the working directory
in the workspace that contains `audio-pipeline-output/`. On Windows, use
`py -3` if `python3` is not available.

1. Confirm the environment once per machine:

```bash
python3 "<plugin-root>/scripts/doctor.py" --stack acestep
```

2. Create the manifest if the asset does not have one yet:

```bash
python3 "<plugin-root>/scripts/init_asset.py" boss-battle-theme --type bgm --mode manual \
  --prompt "driving orchestral boss battle theme, taiko drums, brass ostinato, D minor" \
  --duration 60 --bpm 140 --loop
```

3. Generate candidates:

```bash
python3 "<plugin-root>/scripts/backends/generate_acestep.py" boss-battle-theme
```

4. Listen to every file under `audio-pipeline-output/<slug>/generate/`, then
   record the chosen one in `stages.generate.selected` before moving on.

Useful flags: `--model`, `--candidates N`, `--seed N`, `--negative-prompt`,
`--no-loop-hints`, `--out-name-prefix`, `--base <workspace>`, `--device`.

The first real run downloads the ACE-Step model repository (DiT renderer, VAE,
text encoder and the LM planner - roughly 12 GB) into
`~/.claude/audio-pipeline/acestep/checkpoints`. Nothing is written into the
game workspace. Expect that first run to take a long time; the timeout is 90
minutes. If the download does not finish inside it, the run is recorded as
`timeout` - just run it again, the download resumes where it stopped.

## Backend Routing

| Backend | Use it for |
| --- | --- |
| `generate_acestep.py` (default) | Anything that should sound like a piece of music: themes, battle tracks, loops, songs with vocals. Structure, tempo and key control live here. |
| `generate_sa3.py --model medium` | Ambient beds and textures with no musical structure: wind over a ruin, a droning cave hum, a rain layer. Instrumental only, no BPM or key control. |

Both backends accept `assetType: bgm`. Choose ACE-Step unless the asset is
really a texture rather than a piece of music. See the `se-generation` skill for
Stable Audio 3's model routing, prompt style, and its own failure table.

`generate_acestep.py` refuses `assetType: se` outright and points at
`generate_sa3.py`; ACE-Step's minimum length is 10 s, which is longer than most
sound effects.

## Model Variants

| `--model` | Checkpoint | Steps | When |
| --- | --- | --- | --- |
| `turbo` (default) | `acestep-v15-turbo` | 8 | Everything. Distilled for 8 steps, and it ships inside the main model repository, so it needs no extra download. |
| `sft` | `acestep-v15-sft` | 32 | A quality re-render of an approved idea. Instruction-tuned, not distilled; several times slower and an extra multi-GB download. |
| `base` | `acestep-v15-base` | 32 | Raw base model. Only when `sft` is steering too hard. |

The XL (4B) checkpoints are deliberately not offered: they do not fit a 12 GB
card alongside the LM planner.

Classifier-free guidance is only honoured by `sft` and `base`; `turbo` ignores
it, which is why the driver sets it per model instead of exposing a flag.

ACE-Step pairs the DiT renderer with an LM "planner" that turns the prompt into
structured musical metadata and semantic codes. Which planner is loaded, whether
the DiT is offloaded, and whether INT8 quantization is on are all decided from
the detected VRAM by ACE-Step's own tier table - there is nothing to configure.
If the planner cannot be loaded at all, the backend warns and renders from the
prompt alone, which sounds less structured; the candidate params record which
planner was used (`lmModel`), or `null` when there was none.

## Writing The Prompt

The prompt lives in `requirement.prompt`; entries in `requirement.styleTags`
are appended to it automatically. The whole thing must stay under 512
characters.

Name the genre, the instruments, the mood, and the musical facts:

- `driving orchestral boss battle theme, taiko drums, brass ostinato, D minor`
- `calm medieval town theme, lute, recorder, hand percussion, major key`
- `tense synthwave stealth loop, arpeggiated bass, muted kick, minor key`

Guidance that changes the result:

- **Put BPM and time signature in the requirement**, not only the prompt.
  `requirement.bpm` and `requirement.timeSignature` are passed as structured
  metadata and are what makes bar snapping possible. The model honours them.
  BPM must be a whole number in 30-300 and the signature must be 2/4, 3/4, 4/4
  or 6/8; anything else is a `user_error` rather than a silent mis-render.
- **Put the key in the prompt** (`D minor`, `C major`). The manifest has no key
  field, and the prompt is where ACE-Step reads it.
- **Structure tags help**: `intro, main loop, build, no outro` shapes the
  arrangement over the requested duration.
- **The prompt is passed through verbatim.** The LM planner writes the musical
  plan, but it is not allowed to rewrite the caption, so whatever is written
  here is exactly what conditions the model.
- `--negative-prompt` steers the LM planner's guidance only. ACE-Step has no
  negative prompt for the renderer itself, so it is a nudge, not a filter.

## Loops

When `requirement.loop` is true and both `requirement.bpm` and
`requirement.timeSignature` are set, the backend snaps the requested duration to
the nearest whole number of bars and generates that instead. A 60 s request at
140 BPM in 4/4 becomes 35 bars (60.0 s); a 30 s request becomes 18 bars
(30.857 s). The candidate params record `requestedDurationSeconds`,
`barSnappedDurationSeconds`, `bars`, `bpm`, `beatsPerBar` and `timeSignature`.

Why it matters: a track that ends mid-bar cannot be cut on a downbeat, so its
loop seam either drops musical content or lands off the grid. Fixing the bar
count before generation is the only place this can be solved.

The backend also appends `seamless loop, no intro, no outro, no fade-out,
sustained energy until the final bar` to the prompt of a looping asset, because
the planner writes an intro and a fade-out by default, likes to resolve early,
and none of that survives a loop point. Pass `--no-loop-hints` to turn it off
(for example when the asset genuinely wants a one-shot intro).

**Be honest about what is not done yet**: bar snapping is generation-side only.
Trimming exactly on the downbeat and crossfading the seam belong to the post
stage, which is not implemented yet. Until it lands, verify the loop by ear and
expect to trim manually. Do not tell the user the loop is seamless because the
bar count is right.

The snapped length is also a target, not a guarantee. ACE-Step renders on a
25 Hz latent grid, so the decoder rounds the request down to a whole 40 ms
frame: a 30.857 s target comes back as 30.80 s, 57 ms short. Allow **+/-80 ms
(two latent frames)** when comparing - one frame for the rounding itself, one
for the decoder's own edge handling. Measure the real file with `ffprobe` and
treat `barSnappedDurationSeconds` as what the post stage should trim or pad
toward, not as what is already on disk.

### Trailing Silence

The LM planner decides when the song is finished, and it regularly finishes
early: it writes an ending a few bars before the requested length and the
renderer fills the rest with silence. The first real chiptune test asked for 18
bars and got content up to bar 15 followed by 5.05 s of nothing. In a game that
is not a short track, it is a track with an audible hole every time the loop
wraps.

Every candidate is therefore measured (50 ms RMS windows, -45 dBFS threshold)
and the numbers are recorded as `leadingSilenceSeconds` and
`trailingSilenceSeconds` in the candidate params, plus printed in the run
summary.

For looping assets the driver also records `params.loopViable`, which is false
when either end carries more than 0.75 s of dead air:

- **Auto mode** retries with a fresh seed until a take is loop-viable, up to 3
  candidates per invocation. Rejected takes stay on disk and in the manifest -
  one of them may still be the best available. If none qualify, the run still
  finishes `done` and prints a warning naming the closest candidate and its
  figures. Passing `--candidates N` explicitly turns the retry off: an explicit
  count is an instruction, not a starting point.
- **Manual mode** never retries. It annotates and prints the figures so the
  person choosing sees them first.
- **Non-loop assets** get the measurements, no flag and no policy.

When nothing is loop-viable, the fix is the requirement, not another roll of the
dice: shorten `requirement.durationSeconds` toward where the music actually
stops. **A loop does not have to be the requested bar count to be valid** - the
post stage (a later chunk) will trim to the last contentful bar boundary as the
final fallback, so a 15-bar loop out of an 18-bar request is a good outcome, not
a failure.

Set expectations accordingly: on the chiptune case the loop prompt hints cut the
trailing silence from 5.05 s to 3.05-4.10 s across three seeds, but never below
the 0.75 s limit. Prompting reduces the problem; it does not remove it, and no
number of retries will make a planner fill bars it has decided to end before.

If `loop` is set but BPM or time signature is missing, the backend logs a
warning and generates the raw duration. Set both.

## Vocals

Instrumental is the default. `requirement.vocals` is false out of the box and
the backend sends ACE-Step's `[Instrumental]` marker.

For a song with words:

```bash
python3 "<plugin-root>/scripts/init_asset.py" ending-song --type bgm \
  --prompt "wistful indie folk ending theme, acoustic guitar, female vocal" \
  --duration 120 --vocals --lyrics "[verse] ..."
```

- `requirement.vocals` true with `requirement.lyrics` empty is a `user_error`.
  Wordless singing reads as a broken backend, so it is refused rather than
  generated. Write the lyrics, or set `vocals` to false.
- Lyrics support 50+ languages and cap at 4096 characters. The language is
  detected from the lyrics themselves.
- `requirement.lyrics` set while `vocals` is false is ignored, with a warning.

## Reference Audio

Set `requirement.referenceAudio` to an absolute or workspace-relative path to
condition generation on the style of an existing track. Text prompt and
reference can be combined; either one alone is enough to run.

`requirement.referenceStrength` is how strongly the reference should survive, so
**higher means closer to the reference**. It maps straight onto ACE-Step's
`audio_cover_strength` with no inversion.

| Value | Result |
| --- | --- |
| `1.0` | Full style conditioning on the reference. |
| `0.7` | Default. Clearly related, still led by the prompt. |
| `0.2` | Light style transfer; the prompt dominates. |

The backend samples 30 seconds from the reference as three 10 second segments
taken from its front, middle and end; nothing else in the file is used. This is
style conditioning, not cover mode: it borrows character, not melody. Cover,
repaint and audio-to-audio are not wired up yet.

## Duration

ACE-Step 1.5 is trained for 10-600 s and hits the requested length closely.
Anything outside that range is a `user_error`; under 10 s the asset is a sound
effect, so use `generate_sa3.py` instead.

Practical limits on a 12 GB card with the LM planner loaded: around 8 minutes
per track. A long track also costs proportionally more time per candidate, so
explore the idea at 30-60 s before committing to a 5 minute render. For scale, a
31 s instrumental on a 12 GB card takes about 17 s of generation once the models
are loaded; loading them costs another minute or two on every run.

## Candidates And Seeds

- Manual mode defaults to 3 candidates, auto mode to 1.
- Candidates are generated one at a time to keep peak VRAM at a single track's
  worth. Each gets its own seed; pass `--seed N` to make a batch reproducible
  (candidate N uses `seed + N - 1`).
- Re-running appends (`cand-04.wav`, `cand-05.wav`, ...) instead of overwriting
  earlier takes, so nothing is lost by trying again.

## Dry Run

Set `AUDIO_PIPELINE_DRY_RUN=1` to exercise the whole flow without a GPU or the
acestep environment. ffmpeg synthesizes a 48 kHz stereo tone per candidate at
the bar-snapped duration and the manifest is filled in as usual, with
`dryRun: true` in the candidate params. Use it to check wiring and bar snapping,
never to judge audio.

## When It Fails

The backend records a `stages.generate.failureKind` and prints an actionable
message. Do not retry blindly; fix the named cause first.

| failureKind | What to do |
| --- | --- |
| `user_error` | Wrong asset type, missing prompt, missing reference file, duration outside 10-600 s, vocals without lyrics, a prompt over 512 characters, missing ffmpeg, or a missing acestep environment. The message names which. |
| `oom` | Shorten the duration, close other GPU work, or generate fewer candidates per run. |
| `model_download_failed` | The model repository could not be fetched. Check the network and the free space on the drive holding `~/.claude/audio-pipeline/acestep/checkpoints`. |
| `backend_error` | Read the message; it carries the worker's own error. |
| `timeout` | The run exceeded 90 minutes. Almost always a first-run weight download that is slower than the budget. Check that `~/.claude/audio-pipeline/acestep/checkpoints` grew, then re-run: the download resumes. |

## Verification Checklist

Before declaring the generate stage done, confirm all of the following:

- `stages.generate.status` is `done` and `stages.generate.backend` is `acestep`.
- Every entry in `stages.generate.candidates` has a `file` like
  `generate/cand-01.wav` that exists on disk and is non-empty.
- Each candidate records the seed that produced it.
- The files are 48 kHz stereo and their duration matches the request within
  +/-80 ms, two 40 ms latent frames (`ffprobe` is enough here). For a looping
  asset, compare against `barSnappedDurationSeconds`, not the original request.
- For a looping asset, every kept candidate has `params.loopViable` true, or the
  shortfall has been discussed with the user rather than passed off as fine.
- For a looping asset, the track does not fade out and does not open with a
  one-shot intro flourish.
- Vocal tracks sing the supplied lyrics; instrumental tracks have no voice.
- `stages.generate.failureKind` is `null`.

Candidates come out peak-normalized to -1 dBFS (ACE-Step's own default), so a
peak reading of exactly -1.0 dB is expected and is not the same thing as the
`requirement.targetLufs` the post stage will apply.

If any item fails, fix it and re-verify before moving to the post stage.

## Reference Index

- `references/prompt-patterns.md` covers genre and mood vocabulary, worked
  prompts for common game cues, structure tags, and what the model does not
  take direction on.
