---
name: animate
description: Stage 4 of the 3D asset pipeline -- auto-animate the rigged mesh via Meshy v5. Skipped for static props.
argument-hint: "<asset-slug> [--clips idle,walk,run,attack]"
---

# 3D Pipeline Animate Command

Auto-animate the Stage 3 rig for an existing 3D pipeline manifest.

## Argument Handling

Parse `$ARGUMENTS` as:

```text
<asset-slug> [--clips idle,walk,run,attack]
```

Require the first token as `<asset-slug>`. If it is missing, show usage and stop.

Pass `--clips` through when provided. Otherwise let the script choose default clips from `manifest.assetType`.

## Preflight

Read `3d-pipeline-output/<asset-slug>/pipeline.json`.

Confirm:

- `stages.rig.status` is `done` for humanoid and quadruped assets.
- `stages.rig.files.fbx` exists.
- `stages.rig.taskId` exists for real Meshy animation requests.
- `assetType` is present.

If `assetType` is `prop` or `stages.animate.status` is `skipped`, report that animation is skipped and stop successfully.

## Script Invocation

Run:

On Windows, use `py -3` if `python3` is not available.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/animate_meshy.py" <asset-slug> [--clips idle,walk,run,attack]
```

## Reporting

After the script exits, read `pipeline.json` again and print:

- Animation status.
- Vendor.
- Clips.
- Task ids when present.
- `takeMap` entries.
- Any concise error field when failed.

If the animation stage is done, suggest continuing to the engine import stage when that stage is available.

## Notes

- Use the rigging-and-animation skill for clip defaults and recovery details.
- Set `PIPELINE_DRY_RUN=1` to copy the animation placeholder without API calls.
- Never print credential values.
- Do not modify plugin or marketplace version fields.
