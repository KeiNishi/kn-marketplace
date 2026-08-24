---
name: audio-pipeline-overview
description: This skill should be used when the user asks to "run the audio pipeline", "generate audio assets", "make BGM and SE for my game", "check the audio pipeline status", "resume an audio asset", or mentions audio-pipeline-output, pipeline.json, or stage routing for the audio-asset-pipeline. It coordinates the four stages (requirement, generate, post, review), runs the two modes (auto with no approval stops, manual with an approval gate), routes each request to a backend, reads and updates pipeline.json, and decides which stage to run next. Also triggers on the "/audio-asset-pipeline:se", "/audio-asset-pipeline:bgm", "/audio-asset-pipeline:audio-info" and other "/audio-asset-pipeline:*" commands.
---

# Audio Pipeline Overview

This skill coordinates the local-model audio asset pipeline: one manifest per
asset, four stages, two modes. Use it to decide which stage to run, which
backend to route to, and whether a human has to be asked anything.

For the details of a stage, read the skill that owns it: `se-generation`,
`bgm-generation`, `loop-and-postprocess`.

## Locating the Plugin

Locate the installed plugin directory first; `<plugin-root>` below is that
directory, and every `scripts/...` path is relative to it. Run the scripts with
`python3` from the workspace that contains `audio-pipeline-output/` (on Windows,
use `py -3` if `python3` is not available).

## Stage Order

| Stage | Script | What it produces |
| --- | --- | --- |
| `requirement` | `scripts/init_asset.py` | `audio-pipeline-output/<slug>/pipeline.json` with the requirement block. |
| `generate` | `scripts/backends/generate_sa3.py`, `generate_acestep.py`, `generate_minimax.py` | Candidate WAVs in `generate/`, recorded with seed, params and silence measurements. |
| `post` | `scripts/post_process.py` | `post/master.wav` plus the shipping exports (16-bit WAV, OGG), trimmed, loop-exact, loudness-normalized. |
| `review` | `scripts/review_asset.py` | `stages.review` verdict, per-check detail, and a spectrogram PNG per shipped WAV in `review/`. |

Selection and approval sit between generate and post and are recorded by
`scripts/approve_asset.py`.

## Manifest Rules

- Read and write only `audio-pipeline-output/<slug>/pipeline.json`.
- Use `scripts/_manifest.py` helpers rather than hand-editing JSON; it validates
  every field a later stage reads.
- Keep stage `status` values in `pending`, `in_progress`, `done`, `failed`, or
  `skipped`. Every scripted stage sets its own.
- `updatedAt` is rewritten on every save. Do not set it by hand.
- Never store API keys, tokens, or credential paths in the manifest.

## THE TWO MODES

The mode is fixed at `init_asset.py` time (`--mode auto|manual`) and lives in
`manifest.mode`. Read it before doing anything else: it decides whether the user
is asked questions at all.

### Auto mode: no stops

Auto mode is for "give me a sword swing" and for batch work. It never asks a
question and never waits for approval.

1. **Draft the requirement from the conversation. Do not ask the user.** Infer
   `type` (`se` for a one-shot effect, `bgm` for music), `prompt`, `duration`,
   `loop`, `vocals` and the backend from what the conversation already
   establishes - the game's genre, the scene being built, the asset that was
   just named. Where the conversation says nothing, take the manifest defaults
   (SE: 3 s, no loop, -12 LUFS; BGM: 60 s, loop, -16 LUFS).
2. State what was inferred in **one line** ("Auto mode: SE, 2 s, no loop,
   Stable Audio 3 small-sfx, from 'metallic sword whoosh'.") and keep going.
3. Generate **1 candidate** (the drivers already default to 1 in auto mode).
4. Let `post_process.py` select. In auto mode it picks the candidate itself
   when none is recorded - loop-viable first, then the least dead air, then the
   lowest seed - records it as `selected`, and logs the choice. `approved`
   stays `false`: approval is a human act.
5. Run `review_asset.py`.
6. Report: the output paths, the review verdict, and the one-line inference.

**Retry policy.** On a failing review, or a loop asset whose candidate came back
`loopViable: false`, adjust and regenerate: a new seed first, a refined prompt if
the same fault repeats (a gap at the end means the model ended early - shorten
the requested duration or state the loop intent in the prompt). **At most 2
further attempts**, then stop and report honestly what failed and what was tried.
Never report a failing review as a success, and never widen a check to make one
pass.

### Manual mode: elicit, present, wait

Manual mode is for an asset that has to be right.

1. **Elicit the requirement.** Ask about purpose and scene, mood and genre,
   duration, whether it must loop, whether it has vocals (and the lyrics), and
   whether there is a reference track. Use the AskUserQuestion tool if
   available; otherwise ask in a plain message and wait for the reply.
2. Initialize with `init_asset.py --mode manual`.
3. Generate **3 candidates** (the drivers default to 3 in manual mode).
4. **Present them and stop.** For each candidate give the file path, its
   `leadingSilenceSeconds` / `trailingSilenceSeconds` (and `loopViable: false`
   when set), and a one-line description of its character. Ask the user to
   listen and choose. Wait for the answer - do not choose for them, and do not
   run the post stage while waiting.
5. Record the choice:
   `python3 "<plugin-root>/scripts/approve_asset.py" <slug> --select generate/cand-02.wav --approve`
6. Run `post_process.py`, then `review_asset.py`.
7. Confirm with the user: play the exports, report the verdict, and ask whether
   to iterate.

## Approval Gates

- **Generate gate (mechanical, manual mode only)**: `post_process.py` refuses to
  run while `_manifest.generation_approved()` is false, and names
  `approve_asset.py` in the error. Approval requires a `selected` candidate that
  is in `candidates` AND on disk; `approve_asset.py` refuses to approve a file
  that is missing.
- **An approval is bound to the file it was given for** (`approvedFile`).
  Selecting a different take closes the gate again, and in manual mode
  `post_process.py --candidate` must name the approved selection - it is not a
  way around the gate.
- **Auto mode has no gate, by design.** It selects without approving, so
  `approved` stays `false` and the manifest still shows that no human signed off.
  Because that selection is a machine decision, it is recomputed over the whole
  candidate set on every run: new candidates can change it, and the post and
  review records of the superseded take are cleared. A human-approved selection
  is never re-chosen.
- `approve_asset.py <slug> --reject` withdraws an approval and keeps the
  selection.

## Backend Routing Table

| Request | Backend | Notes |
| --- | --- | --- |
| Sound effect, foley, UI blip, one-shot | `generate_sa3.py` (`--model small-sfx`, default) | Seconds per candidate. Up to 120 s. |
| Ambient bed or texture (wind, cave hum, rain) | `generate_sa3.py --model medium` | No musical structure, no BPM. Needs Flash Attention 2, which `setup_env.py --stack sa3` installs; `doctor.py` reports it as `extra flash_attn`. |
| Instrumental music, themes, loops | `generate_acestep.py` (default for BGM) | Tempo and bar control; the only backend whose BPM the post stage can snap bars to. |
| A vocal performance that has to carry a scene | `generate_minimax.py` | **License notice**: shipping this audio requires "MiniMax-Music3" displayed in the product UI. **Cost warning**: over half an hour of GPU time per candidate, plus a 27 GB download the first time. Tell the user both before routing here. |

Measured on a 12 GB card (RTX 4070 Ti), model weights already cached: Stable
Audio 3 small-sfx a few seconds per candidate, ACE-Step turbo about 17 s for a
31 s instrumental, MiniMax-Music3 36 minutes for 75 s of music - roughly 29x
real time, and it scales with the requested length. Stable Audio 3 medium
renders 60 s of ambience in about 3 s of compute. Model loading adds a minute
or two per run - more for medium, whose first ever call took 9 minutes
wall clock against 3 s of actual generation. Quote these when telling the user what a request costs in
wall-clock time: in manual mode, 3 MiniMax candidates is an afternoon.

## Manifest-driven Resume

- `pipeline.json` is the source of truth. Read it before running a stage and
  again after every script returns.
- Resume from the first stage whose status is `pending` or `failed`, unless the
  user asks for a fresh asset.
- A failing review leaves `stages.review.status: failed` with `verdict: "fail"`,
  so a resume comes back to it instead of treating the asset as finished. Read
  `stages.review.checks` - each entry says what was measured and what was
  expected - and fix the cause, not the check.
- `stages.generate.attempts` counts how many generation runs the asset has had.
  Use it against the auto-mode retry limit.

## Pre-flight

- Run `python3 "<plugin-root>/scripts/doctor.py" --stack <sa3|acestep|minimax>` once per session
  before the first generation, and stop when it reports a failed check.
- A missing environment is set up with `python3 "<plugin-root>/scripts/setup_env.py" --stack
  <stack>`, not by hand.
- ffmpeg (with ffprobe) must be on `PATH` for the post and review stages.
- When dry-run behavior is expected, confirm `AUDIO_PIPELINE_DRY_RUN=1` is set in
  the same shell. The flag means "use no model", and the two halves of the
  pipeline honour it differently:
  - `generate_*.py` **do** write: ffmpeg synthesizes a placeholder tone per
    candidate at the right rate and duration, and the manifest is filled in as
    usual with `dryRun: true` in the candidate params.
  - `post_process.py` and `review_asset.py` print their plan and write nothing,
    so a dry run stops there - `review_asset.py` then refuses, correctly, because
    the post stage produced no outputs.
- To carry a rehearsal all the way through, generate with the flag and then run
  the post and review stages **without** it. Neither of them touches a model or
  the GPU, they run on the placeholder candidates exactly as on real ones, and
  ffmpeg is required in dry-run mode anyway. Judge wiring and bar arithmetic this
  way, never audio.

## Security Reminder

- `HF_TOKEN` and any other secret belong in `~/.claude/audio-pipeline/.env`
  (`%USERPROFILE%/.claude/audio-pipeline/.env` on Windows), which is outside any
  repository.
- Never write a token into the manifest, a prompt, a log line, or a file in the
  workspace.
- Leave plugin and marketplace version fields alone unless the task explicitly
  asks for a version bump.
