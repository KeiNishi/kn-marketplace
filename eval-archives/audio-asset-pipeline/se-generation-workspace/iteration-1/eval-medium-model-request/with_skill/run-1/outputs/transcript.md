# Transcript: UI confirmation blip, medium model

## Context

User request: "Use the medium model for this one, I want the best quality." This
follows on from an earlier conversation about a short UI confirmation blip
(~0.5 s). No pipeline asset existed yet for this sound.

Skill followed: `se-generation` at
`D:/Projects/kn-marketplace/plugins/audio-asset-pipeline/skills/se-generation/SKILL.md`.
`<plugin-root>` = `D:/Projects/kn-marketplace/plugins/audio-asset-pipeline`.

All commands were run with `AUDIO_PIPELINE_DRY_RUN=1` in the environment, as
required for this session (no GPU generation). Working directory for every
command was the run directory (contains/creates `audio-pipeline-output/`).

## Steps

1. Recorded start time: `date +%s` → `1787589230`.

2. Read the skill (`SKILL.md`) and its prompt-recipes reference
   (`skills/se-generation/references/prompt-recipes.md`) to get the model
   routing rules, the short-SFX handling rule, and a matching prompt recipe.
   Key facts used:
   - Model routing table: `medium` = "Quality re-render of an approved idea,
     longer musical or ambient beds," needs Flash Attention 2, ~5-6.5 GB VRAM.
     `small-sfx` is the normal default for one-shot SE exploration.
   - "Short Sound Effects" section: for anything under ~2 s, keep
     `requirement.durationSeconds` at the length actually wanted (0.5 s) and
     let the backend generate its 2 s minimum; the post stage trims it later.
   - Prompt-recipes "Stylized and anime SFX" table has a ready-made "Confirm"
     entry: `soft positive interface chime, two tones rising`.

3. Ran the environment check named in the skill's Quick Start step 1:

   ```
   AUDIO_PIPELINE_DRY_RUN=1 python "D:/Projects/kn-marketplace/plugins/audio-asset-pipeline/scripts/doctor.py" --stack sa3
   ```

   Result (relevant lines):
   ```
   [OK] NVIDIA GPU: NVIDIA GeForce RTX 4070 Ti, 12.0 GB VRAM
   [OK] Stack sa3 (Stable Audio 3) extra flash_attn: present, so the 'medium' model can run
   [OK] Generation stacks: usable: sa3
   [WARN] Disk space: 56.7 GB free on C:\, which holds both the data directory and the Hugging Face cache; all three stacks need about 60 GB there
   [INFO] Dry run: AUDIO_PIPELINE_DRY_RUN=1 (no generation will run)
   Doctor: 8 ok, 1 warn, 0 fail
   ```
   Decision: flash_attn is present, so `medium` is actually usable on this
   machine (per the skill, `medium` without Flash Attention 2 refuses to run
   rather than producing glitchy audio). The only warning is disk headroom,
   which is not blocking. Proceeded.

4. No manifest existed yet for this asset, so created one (skill Quick Start
   step 2), slug `ui-confirm-blip`, using the "Confirm" prompt recipe extended
   with `short, dry, no tail` per the recipe's own advice for anything that
   plays on a button press, and `--duration 0.5` per the Short Sound Effects
   rule (keep the requested duration at what's actually wanted, not
   pre-doubled):

   ```
   AUDIO_PIPELINE_DRY_RUN=1 python "D:/Projects/kn-marketplace/plugins/audio-asset-pipeline/scripts/init_asset.py" ui-confirm-blip --type se --mode manual \
     --prompt "soft positive interface chime, two tones rising, short, dry, no tail" --duration 0.5
   ```

   Result:
   ```
   Created .../audio-pipeline-output/ui-confirm-blip/pipeline.json
     se / manual mode, 0.5s, loop=False
     prompt: soft positive interface chime, two tones rising, short, dry, no tail
   Next: run the generate stage for this slug.
   ```

5. Generated candidates on the medium model, as the user explicitly requested
   (skill Quick Start step 3, with `--model medium` override):

   ```
   AUDIO_PIPELINE_DRY_RUN=1 python "D:/Projects/kn-marketplace/plugins/audio-asset-pipeline/scripts/backends/generate_sa3.py" ui-confirm-blip --model medium
   ```

   Result:
   ```
   [audio-generate-sa3] INFO: Generating 2.00s instead of the requested 0.50s: shorter clips are unreliable at this model's latent rate. Trim in the post stage.
   [audio-generate-sa3] INFO: ui-confirm-blip: model=medium duration=2.00s candidates=3 [dry-run]

   Generated 3 candidate(s) for 'ui-confirm-blip' with sa3/medium in 0.1s
     generate/cand-01.wav  seed=3881969242  silence lead=0.00s tail=0.00s
     generate/cand-02.wav  seed=2545416106  silence lead=0.00s tail=0.00s
     generate/cand-03.wav  seed=2157763131  silence lead=0.00s tail=0.00s
   Files: .../audio-pipeline-output/ui-confirm-blip/generate
   Next: listen to the candidates, then record the chosen one as stages.generate.selected.
   ```
   This confirms the backend honored `--model medium` (manual mode's default
   of 3 candidates was used since `--candidates` was not specified).

6. Verified the Verification Checklist from the skill:
   - Listed the output directory: `cand-01.wav`, `cand-02.wav`, `cand-03.wav`,
     each 352,878 bytes (non-empty).
   - `ffprobe` on `cand-01.wav`: `codec_name=pcm_s16le`, `sample_rate=44100`,
     `channels=2`, `duration=2.000000` — 44.1 kHz stereo, duration matches the
     backend's stated 2.00 s target (which itself is the documented minimum
     override of the 0.5 s request).
   - Read `pipeline.json`: `stages.generate.status = "done"`,
     `stages.generate.backend = "sa3"`, `stages.generate.failureKind = null`,
     each candidate has a `file`, a `seed`, and `params.model = "medium"`,
     `params.requestedDurationSeconds = 0.5`, `params.durationSeconds = 2.0`,
     `params.dryRun = true`.
   - All checklist items pass. `stages.generate.selected` is still `null` —
     that field records a human listening choice, which is out of scope for
     this dry run (see note below).

7. Recorded end time: `date +%s` → `1787589343`. Elapsed: `1787589343 -
   1787589230 = 113` seconds.

## Questions I would have asked the user (could not, per session rules) and the assumptions I proceeded with instead

- "The `medium` model in this pipeline is documented as best for re-rendering
  an already-approved idea or for longer ambient/musical beds, and the normal
  workflow explores cheap iterations on `small-sfx` first. Have you already
  settled on the exact character of this blip, or would you like a quick
  `small-sfx` pass first to nail the prompt before spending the heavier
  `medium` render on it?" — Assumption: the user said "I want the best
  quality" for *this one*, i.e. they've decided what they want and want the
  higher-fidelity model directly, so I generated straight on `medium` per
  their explicit instruction and skipped the small-sfx exploration pass.
- "Is 'soft positive interface chime, two tones rising' the right character
  (a two-tone rising chime), or did you have something else in mind — a
  single blip/click instead of a chime, a different tone count, retro/8-bit
  vs. clean synth, etc.?" — Assumption: used the skill's own ready-made
  "Confirm" prompt recipe verbatim (plus `short, dry, no tail`, which the
  recipes doc recommends for anything triggered by a button press), since
  nothing more specific was given.
- "Any sounds you want explicitly kept out (e.g. music bed, reverb tail,
  speech) via a negative prompt?" — Assumption: none specified, so no
  `--negative-prompt` was passed.
- "How many takes do you want to compare?" — Assumption: left at manual
  mode's default of 3 candidates.

## Final answer given to the user

I created the pipeline asset for this SFX (`ui-confirm-blip`) and generated
3 candidate takes on the `medium` Stable Audio 3 model, as you asked, using
the pipeline's own "confirmation chime" prompt recipe: *"soft positive
interface chime, two tones rising, short, dry, no tail"*.

A few notes on how this went:

- `doctor.py` confirms your machine has the `flash_attn` wheel `medium`
  needs, so it isn't silently falling back to glitchy output — `medium` is
  actually running as requested, not just requested.
- Because a 0.5 s window is too short for Stable Audio 3's latent grid, the
  backend generated 2.00 s per candidate instead (this is documented,
  expected behavior) with your usable transient sitting in the first
  fraction of a second. That's fine — the post stage trims it down to the
  final ~0.5 s and normalizes loudness; nothing further to do about it now.
- Note this session ran in dry-run mode (`AUDIO_PIPELINE_DRY_RUN=1`), so the
  three files are placeholder synthesized tones for verifying the pipeline
  wiring, not real Stable Audio 3 output — good for confirming everything is
  connected correctly, not for judging how the actual sound will feel. When
  you run this for real (dry run off), expect the first `medium` call to
  take roughly 9 minutes to download and load the checkpoint before it
  starts rendering; after that it's fast.
- One thing worth flagging: `medium`'s documented sweet spot is re-rendering
  an idea you've already validated cheaply on `small-sfx`, or ambient/musical
  beds — a one-shot UI blip is normally explored on `small-sfx` first because
  it's much cheaper to iterate on. You said you want best quality on this
  one specifically, so I went straight to `medium` per your instruction, but
  if the prompt itself still needs tuning, a `small-sfx` pass would be the
  cheap way to do that before spending more `medium` renders.

Files: `audio-pipeline-output/ui-confirm-blip/generate/cand-01.wav`,
`cand-02.wav`, `cand-03.wav` (44.1 kHz stereo, 2.00 s each, seeds
3881969242 / 2545416106 / 2157763131).

Next step: listen to the three candidates and tell me which one to record as
`stages.generate.selected` (or ask for another batch of `medium` takes if
none of them land), then I'll run the post stage to trim it to ~0.5 s and
normalize it to -12 LUFS / -1.0 dBTP for engine use.
