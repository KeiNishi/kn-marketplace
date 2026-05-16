---
name: generate-mesh
description: Stage 2 of the 3D asset pipeline - generate a textured 3D mesh from the canonical concept image. Defaults to Hunyuan 3D 3.1 via Replicate; supports Meshy v5 alt and Tripo3D fallback.
argument-hint: "<asset-slug> [--vendor hunyuan|meshy|tripo] [--mode rapid|pro] [--target-polys N] [--no-pbr]"
allowed-tools: Read, Write, Bash, AskUserQuestion
---

# 3D Pipeline Generate-Mesh Command

Generate the Stage 2 mesh for an existing 3D pipeline manifest.

## Argument Handling

Parse `$ARGUMENTS` as:

```text
<asset-slug> [--vendor hunyuan|meshy|tripo] [--mode rapid|pro] [--target-polys N] [--no-pbr]
```

Require the first token as `<asset-slug>`. If it is missing, show usage and stop.

Default `--vendor` to `hunyuan`. Default `--mode` to `rapid`. Pass any remaining supported flags through to the selected script.

## Preflight

Read `3d-pipeline-output/<asset-slug>/pipeline.json`.

Confirm:

- `stages.concept.status` is `done`.
- `stages.concept.files.canonical` exists.
- `description` and `assetType` are present.

If the asset type is ambiguous and no vendor override was supplied, ask whether the asset is a quadruped. If the user confirms a quadruped and wants the fallback route, use `tripo`; otherwise keep `hunyuan`.

## Script Routing

For Hunyuan:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/mesh_hunyuan.py" <asset-slug> <flags>
```

For Meshy:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/mesh_meshy.py" <asset-slug> <flags>
```

For Tripo:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/mesh_tripo.py" <asset-slug> <flags>
```

## Reporting

After the script exits, read `pipeline.json` again and print:

- Mesh status.
- Vendor.
- Prediction or task id when present.
- `files.glb` and `files.fbx` when present.
- Any concise error field when failed.

If the mesh stage is done, ask whether to continue to the rig stage. For props, suggest continuing directly to import. For humanoids and quadrupeds, suggest `/3d-pipeline:rig <asset-slug>`.

## Notes

- Use the mesh-generation skill for vendor routing and recovery details.
- Set `PIPELINE_DRY_RUN=1` to copy placeholder mesh files without API calls.
- Never print credential values.
- Do not modify plugin or marketplace version fields.
