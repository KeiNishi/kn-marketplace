# Animation Library Reference

Use Meshy v5 auto-animation after Stage 3 rigging completes. This chunk records each generated clip as a separate FBX file.

## Humanoid Defaults

Default humanoid clips:

- `idle`
- `walk`
- `run`
- `attack`

Use these for most player characters, NPCs, enemies, and biped robots. The set gives enough coverage for engine import tests, state-machine setup, and basic combat prototyping.

## Quadruped Defaults

Default quadruped clips:

- `idle`
- `walk`
- `gallop`

Use these for animals and four-legged creatures. The set focuses on locomotion because attack clips vary widely by anatomy.

## Custom Clips

Pass explicit clips with:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/animate_meshy.py" <slug> --clips idle,walk,run,attack
```

Keep clip names simple and lowercase when possible. Avoid spaces in clip names because the script uses clip names in output filenames.

Useful humanoid candidates:

- `jump`
- `death`
- `hit`
- `cast`
- `block`

Useful quadruped candidates:

- `trot`
- `attack`
- `turn`
- `sit`
- `sleep`

Availability depends on Meshy support. Treat unsupported clips as vendor errors and record the failure in `stages.animate.error`.

## Per-Clip FBX Decision

This chunk writes one FBX per clip:

- `animated/<slug>_idle.fbx`
- `animated/<slug>_walk.fbx`
- `animated/<slug>_run.fbx`

The manifest records the same mapping in both `takeMap` and `files`. This keeps downstream engine import simple because each file can be inspected, imported, and replaced independently.

Bundling all takes into a single FBX is intentionally deferred. A later chunk can add take merging if the target engine workflow needs it.

## Dry Run

Dry-run animation copies one fixture to:

- `animated/<slug>.fbx`

The manifest maps every canned clip to that same placeholder path. This keeps plumbing tests small while preserving the clip-map shape expected by downstream stages.

## Manifest Fields

Record:

- `status: done`
- `vendor: meshy:v5`
- `clips`
- `taskIds` in real mode
- `takeMap`
- `files`
- `completedAt`

Never record API keys, signed URLs, or bearer headers.
