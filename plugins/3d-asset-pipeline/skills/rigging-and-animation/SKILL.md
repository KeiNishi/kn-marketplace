---
name: rigging-and-animation
description: This skill should be used when the user asks to "auto-rig", "skin the mesh", "auto-animate", or as stages 3-4 of the 3D pipeline. Uses Meshy v5 auto-rig and auto-animation APIs for humanoids and creatures. Skipped automatically for static props. Also triggers on "/3d-pipeline:rig" and "/3d-pipeline:animate" commands.
---

# Rigging And Animation

Run Stage 3 and Stage 4 of the 3D asset pipeline after mesh generation is complete. Use Meshy v5 for this chunk. Treat the rig stage as the conversion from a static GLB mesh to a skinned FBX, and treat the animation stage as per-clip motion generation against that Meshy rigging task.

## Stage 3 Rig Inputs

- Read `3d-pipeline-output/<slug>/pipeline.json` before running the rig script.
- Confirm `stages.mesh.status` is `done` for humanoid and quadruped assets.
- Resolve the mesh source from `stages.mesh.files.glb`.
- Confirm the GLB exists on disk before spending API credits.
- Use `assetType` to choose the default rig template.
- Use `humanoid` for human, biped, and character assets that should receive a standard game-character skeleton.
- Use `quadruped` for four-legged creatures that should receive a creature skeleton.
- Accept `--template humanoid|quadruped` to override the manifest-derived template.
- Record the source mesh vendor in `stages.rig.uploadedFrom` using a short vendor name.
- Write rig output under `3d-pipeline-output/<slug>/rigged/`.
- Store `files.fbx` as a path relative to the asset output directory.

## Stage 4 Animate Inputs

- Read `pipeline.json` again after rigging.
- Confirm `stages.rig.status` is `done` for humanoid and quadruped assets.
- Resolve the rigged source from `stages.rig.files.fbx`.
- Confirm the FBX exists before requesting animation clips.
- Use `stages.rig.taskId` as the Meshy rigging task id for real animation requests.
- Default humanoid clips to `idle,walk,run,attack`.
- Default quadruped clips to `idle,walk,gallop`.
- Accept `--clips idle,walk,run,attack` to override defaults.
- Write animation outputs under `3d-pipeline-output/<slug>/animated/`.
- Store each real clip as its own FBX file named `<slug>_<clip>.fbx`.

## Asset-Type Gate

- Skip rigging and animation for static props.
- Treat either `assetType: prop` or a stage status of `skipped` as authoritative.
- Log `Skipping rig stage for prop asset type` when the rig script exits early.
- Log `Skipping animation stage for prop asset type` when the animation script exits early.
- Return success for prop skips so pipeline orchestration can continue to import or review.
- Do not create rigged or animated placeholder files for props unless a test deliberately changes the manifest asset type.
- Do not ask for a rig template when the asset type is `prop`.

## Vendor

- Use Meshy v5 only for this chunk.
- Require `MESHY_API_KEY` for real rig and animation calls.
- Read credentials through the shared `_credentials` helper.
- Never read API keys from the repository.
- Never print bearer tokens, request headers, or full credential values.
- Treat future vendors as possible extensions, but do not route to them in this skill.
- Preserve `vendor: meshy:v5` in rig and animation manifest updates.

## Script Commands

The scripts live under the plugin root's `scripts/` directory; `<plugin-root>` below is the installed plugin directory (`${CLAUDE_PLUGIN_ROOT}` in Claude Code; in other agents, locate the installed plugin directory first). Keep the working directory in the workspace that contains `3d-pipeline-output/`. On Windows, use `py -3` if `python3` is not available.

Run Stage 3:

```bash
python3 "<plugin-root>/scripts/rig_meshy.py" <slug>
```

Pass a template override when needed:

```bash
python3 "<plugin-root>/scripts/rig_meshy.py" <slug> --template quadruped
```

Run Stage 4:

```bash
python3 "<plugin-root>/scripts/animate_meshy.py" <slug>
```

Pass explicit clip names when the default library is not enough:

```bash
python3 "<plugin-root>/scripts/animate_meshy.py" <slug> --clips idle,walk,run,attack
```

Use `--base <dir>` for a custom output base in automated tests or non-standard workspaces.

## Dry Run

- Set `PIPELINE_DRY_RUN=1` for local no-network checks.
- Rig dry-run copies `scripts/fixtures/rigged/dryrun.fbx` to `rigged/<slug>.fbx`.
- Animation dry-run copies `scripts/fixtures/animated/dryrun.fbx` to `animated/<slug>.fbx`.
- Dry-run animation records the canned clip set for the manifest asset type.
- Mark dry-run stages with `dryRun: true`.
- Keep dry-run manifest paths identical in shape to real-mode paths.

## Polling And Error Handling

- Set the stage to `in_progress` before calling Meshy in real mode.
- Poll every five seconds through the shared `_common.poll` helper.
- Use a 600-second timeout per rigging task and per animation clip.
- Treat `SUCCEEDED` or equivalent lowercase status as success.
- Treat `FAILED` or equivalent lowercase status as failure.
- On timeout, mark the active stage as `failed`.
- On API failure, mark the active stage as `failed`.
- Sanitize error messages before writing them to the manifest.
- Redact API tokens from HTTP response bodies and exception messages.
- Keep errors concise enough for the manifest to remain readable.
- Return user-error exits for missing inputs and credential setup problems.
- Return API-error exits for vendor failures.

## Manifest Updates

- For rig success, record `status`, `vendor`, `template`, `taskId`, `uploadedFrom`, `files.fbx`, and `completedAt`.
- For animation success, record `status`, `vendor`, `clips`, `takeMap`, `files`, and `completedAt`.
- Preserve existing manifest fields that belong to other stages.
- Store all output file paths relative to the asset output folder.
- Do not modify plugin or marketplace version fields.
- Do not commit generated outputs from `3d-pipeline-output/`.

## Verification Checklist

Before declaring Stage 3 or Stage 4 done, confirm all of the following:

- Rig: `stages.rig.status` is `done` (or `skipped` for props), `stages.rig.files.fbx` exists under `rigged/`, and `template`, `taskId`, and `uploadedFrom` are recorded.
- Animate: `stages.animate.status` is `done` (or `skipped` for props), every requested clip has an FBX under `animated/`, and `clips` plus `takeMap` are recorded.
- All recorded file paths are relative to the asset output folder and resolve on disk.
- `completedAt` is set on the finished stage, and `dryRun: true` is recorded for dry-run output.
- No credential values appear anywhere in the manifest.

If any item fails, fix it and re-verify before moving to engine import.

## Reference Index

- `references/humanoid-rig.md` documents the humanoid template, skeleton assumptions, and Mixamo-compatible naming expectations.
- `references/quadruped-rig.md` documents creature rig selection and common four-legged failure modes.
- `references/animation-library.md` documents default clip sets and the per-clip FBX output decision.
