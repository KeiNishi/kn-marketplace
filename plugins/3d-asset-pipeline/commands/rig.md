---
name: rig
description: Stage 3 of the 3D asset pipeline -- auto-rig the generated mesh via Meshy v5. Skipped for static props.
argument-hint: "<asset-slug> [--template humanoid|quadruped]"
allowed-tools: Read, Write, Bash, AskUserQuestion
---

# 3D Pipeline Rig Command

Auto-rig the Stage 2 mesh for an existing 3D pipeline manifest.

## Argument Handling

Parse `$ARGUMENTS` as:

```text
<asset-slug> [--template humanoid|quadruped]
```

Require the first token as `<asset-slug>`. If it is missing, show usage and stop.

Pass `--template` through when provided. Otherwise let the script derive the template from `manifest.assetType`.

## Preflight

Read `3d-pipeline-output/<asset-slug>/pipeline.json`.

Confirm:

- `stages.mesh.status` is `done` for humanoid and quadruped assets.
- `stages.mesh.files.glb` exists.
- `assetType` is present.

If `assetType` is `prop` or `stages.rig.status` is `skipped`, report that rigging is skipped and stop successfully.

## Script Invocation

Run:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/rig_meshy.py" <asset-slug> [--template humanoid|quadruped]
```

## Reporting

After the script exits, read `pipeline.json` again and print:

- Rig status.
- Vendor.
- Template.
- Task id when present.
- `files.fbx` when present.
- Any concise error field when failed.

If the rig stage is done, suggest continuing with `/3d-pipeline:animate <asset-slug>`.

## Notes

- Use the rigging-and-animation skill for template and recovery details.
- Set `PIPELINE_DRY_RUN=1` to copy the rig placeholder without API calls.
- Never print credential values.
- Do not modify plugin or marketplace version fields.
