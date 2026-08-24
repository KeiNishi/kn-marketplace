# Transcript: Wooden Door Creak SFX Generation

Request: "Generate a wooden door creaking open sound effect for my game, about
3 seconds."

Skill followed: `se-generation` (Sound Effect Generation, Stable Audio 3
backend) at `D:/Projects/kn-marketplace/plugins/audio-asset-pipeline/skills/se-generation/SKILL.md`,
plugin root `D:/Projects/kn-marketplace/plugins/audio-asset-pipeline`.

Constraints followed: all work stayed inside the RUN DIRECTORY
(`.../bench/se-generation/eval-door-creak/with_skill`); nothing under
`D:/Projects/kn-marketplace` was written; no git commands were run;
`AUDIO_PIPELINE_DRY_RUN=1` was set on every pipeline command (GPU generation
forbidden in this benchmark).

## Steps

1. Recorded the start time:

   ```
   date +%s
   ```

   Returned `1787589224`.

2. Read the skill file (`se-generation/SKILL.md`) and its reference doc
   (`references/prompt-recipes.md`) in full before doing anything else, per
   the task instructions.

   Key facts taken from the skill:
   - Quick Start's own worked example is this exact asset: slug `door-open`,
     prompt `wooden door creaking open, interior, close mic`, 3 s duration.
     `references/prompt-recipes.md` lists the identical prompt under
     "Realistic foley" for "Door".
   - `assetType: se` with no override routes to the `small-sfx` model
     (fast, ~2 GB VRAM, up to 120 s) via `--model auto`.
   - Manual mode defaults to 3 candidates so there is something to choose
     between.
   - The backend enforces a 2 s floor per candidate (Stable Audio 3's ~10.76 Hz
     latent grid makes anything shorter unreliable); 3 s is above that floor,
     so no floor-adjustment note was expected in the generate output.
   - "Give The Sound Room To Decay" advises doubling the request for sounds
     with a transient + decay tail (chimes, impacts, whooshes) so the model
     doesn't render a flat sustained texture. Decision: I did **not** apply
     that doubling here. This task is scoped to the `se-generation` skill
     only (generation stage, not `loop-and-postprocess`/trimming), so
     whatever duration is requested at generation time is what ships as the
     candidate — there is no later trim step in this run to cut a longer
     take back down. The user asked for "about 3 seconds" and the skill's
     own canonical example for this exact sound already uses `--duration 3`,
     so requesting 3 s directly satisfies the request without depending on a
     stage that wasn't run. This is a real judgment call and the doubling
     guidance is a documented alternative — flagged here rather than silently
     picked.
   - Negative prompt guidance: add only terms that are actually leaking in;
     `music, speech, reverb, noise` is the stock list for foley.

3. Ran the health check for the Stable Audio 3 stack, dry-run flag set:

   ```
   AUDIO_PIPELINE_DRY_RUN=1 python "D:/Projects/kn-marketplace/plugins/audio-asset-pipeline/scripts/doctor.py" --stack sa3
   ```

   Result: `Doctor: 8 ok, 1 warn, 0 fail`, exit code 0. All hard requirements
   (Python, uv, ffmpeg, GPU, the sa3 venv + flash_attn extra) were OK; the one
   warning was free disk space on `C:\` (56.7 GB free, ~60 GB wanted) — a
   warning only, not a blocker, and irrelevant to dry-run generation anyway
   since dry-run never touches the model or downloads weights.

4. Created the asset manifest:

   ```
   AUDIO_PIPELINE_DRY_RUN=1 python "D:/Projects/kn-marketplace/plugins/audio-asset-pipeline/scripts/init_asset.py" door-open --type se --mode manual \
     --prompt "wooden door creaking open, interior, close mic" --duration 3 \
     --base "<RUN_DIR>"
   ```

   Output:
   ```
   Created <RUN_DIR>/audio-pipeline-output/door-open/pipeline.json
     se / manual mode, 3s, loop=False
     prompt: wooden door creaking open, interior, close mic
   Next: run the generate stage for this slug.
   ```
   Exit code 0.

5. Generated candidates:

   ```
   AUDIO_PIPELINE_DRY_RUN=1 python "D:/Projects/kn-marketplace/plugins/audio-asset-pipeline/scripts/backends/generate_sa3.py" door-open \
     --base "<RUN_DIR>" --negative-prompt "music, speech, reverb, noise"
   ```

   Output:
   ```
   [audio-generate-sa3] INFO: door-open: model=small-sfx duration=3.00s candidates=3 [dry-run]

   Generated 3 candidate(s) for 'door-open' with sa3/small-sfx in 0.1s
     generate/cand-01.wav  seed=1647208824  silence lead=0.00s tail=0.00s
     generate/cand-02.wav  seed=1339493294  silence lead=0.00s tail=0.00s
     generate/cand-03.wav  seed=2985872003  silence lead=0.00s tail=0.00s
   Files: <RUN_DIR>/audio-pipeline-output/door-open/generate
   Next: listen to the candidates, then record the chosen one as stages.generate.selected.
   ```
   Exit code 0. Model auto-routed to `small-sfx` as expected for an `se`
   asset. Since `AUDIO_PIPELINE_DRY_RUN=1` was set, this synthesized
   placeholder tones with ffmpeg rather than loading Stable Audio 3 — no GPU
   model ran, per the benchmark's hard rule.

6. Verified the three candidate files against the skill's Verification
   Checklist:

   ```
   ls -la <RUN_DIR>/audio-pipeline-output/door-open/generate/
   ffprobe -v error -show_entries stream=sample_rate,channels,codec_name -show_entries format=duration ...
   ```

   All three files: 529278 bytes (non-empty), `pcm_s16le`, `sample_rate=44100`,
   `channels=2`, `duration=3.000000`. Matches the 44.1 kHz stereo requirement
   and the requested 3 s duration exactly. `stages.generate.candidates` in the
   manifest records a seed for each. `stages.generate.status` is `done`,
   `backend` is `sa3`, `failureKind` is `null`. The "not clipped or silent"
   checklist item is a real-audio judgment call this dry run cannot make —
   these are synthesized placeholder tones, not model output, so I did not
   claim to have listened for audio quality (the skill is explicit: dry run
   is for checking wiring, never for judging audio).

7. Recorded a selection so the manifest reflects a completed generate stage:

   ```
   AUDIO_PIPELINE_DRY_RUN=1 python "D:/Projects/kn-marketplace/plugins/audio-asset-pipeline/scripts/approve_asset.py" door-open --select generate/cand-01.wav --base "<RUN_DIR>"
   ```

   Output:
   ```
   Asset 'door-open' (manual mode)
     selected   generate/cand-01.wav
     approved   False
   Next: re-run with --approve once you have listened to the selected take (the post stage refuses until then).
   ```

   `cand-01.wav` was picked as `selected` (first take, arbitrary among three
   otherwise-equivalent placeholder tones) but deliberately left `approved:
   false` — manual mode requires a human to actually listen before approving,
   and a dry-run placeholder tone cannot stand in for that judgment. This is
   the point where I would have asked the user: "I generated 3 candidate
   takes of the door creak — please listen to
   `audio-pipeline-output/door-open/generate/cand-0{1,2,3}.wav` and tell me
   which one to keep (or approve `cand-01.wav` if it's fine), so I can run it
   through the post stage (trim, loudness-normalize to -12 LUFS, export
   WAV+OGG)." Since this run cannot ask follow-up questions, I proceeded with
   `cand-01.wav` selected and unapproved, and surface that assumption below.

8. Copied the deliverable files into `<RUN_DIR>/outputs/`:

   ```
   mkdir -p <RUN_DIR>/outputs/generate
   cp <RUN_DIR>/audio-pipeline-output/door-open/generate/*.wav <RUN_DIR>/outputs/generate/
   cp <RUN_DIR>/audio-pipeline-output/door-open/pipeline.json <RUN_DIR>/outputs/pipeline.json
   ```

9. Recorded the end time:

   ```
   date +%s
   ```

   Returned `1787589371`. Total wall clock: `1787589371 - 1787589224 = 147`
   seconds.

## Scope note

This run covers only the `se-generation` skill's generate stage, as
instructed. The pipeline's next stage (`post_process.py` / the
`loop-and-postprocess` skill) trims dead air and the decay tail, normalizes
loudness to -12 LUFS under a -1.0 dBTP ceiling, and exports the final 16-bit
WAV + OGG an engine loads. That was not run here — it needs a listened-to,
approved candidate first, which this dry run cannot genuinely provide.

## Final answer to the user

I generated 3 candidate takes of a wooden door creak, about 3 seconds each,
using the audio-asset-pipeline's `se-generation` skill (Stable Audio 3,
`small-sfx` model, which is what `se` assets route to automatically).

Note: this session ran in a sandboxed dry-run mode (no GPU access here), so
the actual `.wav` files are placeholder tones, not real creak audio — treat
them as a pipeline/wiring check, not something to judge for sound quality.
On a real run the exact same commands (without `AUDIO_PIPELINE_DRY_RUN=1`)
will produce genuine Stable Audio 3 output using this setup:

- Prompt: `wooden door creaking open, interior, close mic`
- Negative prompt: `music, speech, reverb, noise`
- Model: `small-sfx` (auto-routed), duration 3 s, 3 candidates (manual mode)
- Files land in `audio-pipeline-output/door-open/generate/cand-01.wav`
  through `cand-03.wav`; the asset manifest is
  `audio-pipeline-output/door-open/pipeline.json`

I picked `cand-01.wav` as the working `selected` candidate in the manifest,
but left it unapproved — I can't actually listen to these placeholder tones,
and manual-mode assets require a human to listen before the pipeline's post
stage (trim/normalize/export) will run.

Questions I'd ask if I could: Which of the 3 takes sounds best to you (or do
you want more variations with different seeds)? Do you want it left dry (no
reverb baked in, so your game engine's reverb zone handles the room), which
is what the current prompt assumes? Once you pick a take and approve it
(`approve_asset.py door-open --select generate/cand-0N.wav --approve`), the
next step is the post stage to trim, loudness-normalize to -12 LUFS, and
export the final WAV/OGG your engine can load.
