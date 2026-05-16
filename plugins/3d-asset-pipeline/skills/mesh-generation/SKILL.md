---
name: mesh-generation
description: This skill should be used when the user asks to "generate a 3D mesh", "convert concept to 3D", "text-to-3D", or as stage 2 of the 3D pipeline. Selects between Hunyuan 3D 3.1 (default), Meshy v5 (alt), or Tripo3D (quadruped fallback) based on asset type and user override. Polls vendor APIs and writes outputs to the mesh stage folder. Also triggers on "/3d-pipeline:generate-mesh" command.
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

# Mesh Generation

Run Stage 2 of the 3D asset pipeline: convert the canonical concept image and asset description into a textured mesh file for later rigging, animation, import, and review.

## Stage 2 Inputs

- Read `3d-pipeline-output/<slug>/pipeline.json` before running a mesh script.
- Confirm `stages.concept.status` is `done`.
- Resolve the canonical concept image from `stages.concept.files.canonical`.
- Treat the concept image as the visual source of truth for silhouette, colors, and material cues.
- Use `description`, `name`, and `assetType` from the manifest as prompt context.
- Accept `--mode rapid|pro` for vendors with quality or speed tiers.
- Accept `--target-polys N` as a requested budget, even when a vendor only treats it as guidance.
- Prefer PBR output unless the user passes `--no-pbr`.
- Keep prompts and manifest notes in English.
- Set `PIPELINE_DRY_RUN=1` for no-network plumbing checks.

## Vendor Routing

- Use Hunyuan 3D 3.1 through Replicate by default.
- Use Meshy v5 when the user requests `--vendor meshy`, already has a Meshy plan, or needs both GLB and FBX directly from the mesh stage.
- Use Tripo3D only when the user requests `--vendor tripo` or when a quadruped result from the default route is not satisfactory.
- Ask whether the asset is a quadruped if the manifest is ambiguous and the user did not provide a vendor override.
- Keep Hunyuan as the first pass for humanoids and props.
- Prefer Meshy over Tripo when an FBX is immediately required by the next stage.
- Prefer Tripo as a fallback for difficult four-legged creatures.
- Do not switch vendors after a partial API run without recording the failed vendor in the manifest.

## Pre-Flight Checks

- Verify the manifest exists and validates before spending API credits.
- Verify the canonical concept file exists on disk.
- Check credentials only after dry-run handling is ruled out.
- Require `REPLICATE_API_TOKEN` for Hunyuan.
- Require `MESHY_API_KEY` for Meshy.
- Treat `TRIPO_API_KEY` as optional globally, but required when invoking Tripo.
- Never read credentials from the repository.
- Never print or write credential values to logs, errors, or manifest fields.
- Confirm that `scripts/fixtures/mesh/dryrun.glb` and `dryrun.fbx` exist for dry-run mode.
- Create `mesh/` under the asset output folder before writing files.

## Script Commands

Run the vendor-specific script from the plugin root:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/mesh_hunyuan.py" <slug> --mode rapid
```

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/mesh_meshy.py" <slug> --target-polys 20000
```

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/mesh_tripo.py" <slug>
```

Pass through supported shared flags:

- `--base <dir>` for a custom output base.
- `--mode rapid|pro` for speed or quality.
- `--input text|image` to record the intended generation mode.
- `--target-polys N` for the requested budget.
- `--pbr` or `--no-pbr` for material output preference.
- `--seed N` when the vendor supports deterministic attempts.
- `--style "..."` for extra style or texture guidance.

## Pollers And Timeouts

- Use five-second polling intervals.
- Use a 600-second timeout for mesh generation.
- Treat `succeeded` as success for Replicate.
- Treat `failed` and `canceled` as failure for Replicate.
- Treat `SUCCEEDED` as success for Meshy.
- Treat `FAILED` as failure for Meshy.
- Treat `success` as success for Tripo.
- Treat `failed` as failure for Tripo.
- On timeout, mark the mesh stage as `failed` and preserve a concise error category.
- Avoid tracebacks for user-fixable problems such as missing concept output or missing credentials.

## Output Expectations

- Write outputs under `3d-pipeline-output/<slug>/mesh/`.
- Hunyuan writes `<slug>.glb` only.
- Meshy writes `<slug>.glb` and `<slug>.fbx`.
- Tripo writes `<slug>.glb` and may write `<slug>.fbx` on a best-effort basis.
- Store file paths relative to the asset output folder in the manifest.
- Use `files.glb` as the canonical mesh for Godot import when no rigging is needed.
- Use `files.fbx` when present and the rigging or animation stage prefers FBX.
- Do not synthesize an FBX for Hunyuan in this stage.

## Manifest Updates

- Set `stages.mesh.status` to `in_progress` before calling a real vendor.
- Record `vendor`, `input`, `targetPolys`, `pbr`, `dryRun`, and `startedAt` when starting.
- On dry-run, copy fixture files and record `dryRun: true`.
- On success, set `status: done`, vendor identifiers, task or prediction ids, files, and `completedAt`.
- On API failure, set `status: failed`, `error`, and `failedAt`.
- Keep error values short and categorical.
- Never include API keys, bearer tokens, request headers, or full signed URLs in `error`.
- Do not modify plugin or marketplace version fields as part of mesh generation.

## Recovery

- If concept status is not done, run `/3d-pipeline:concept <slug>` first.
- If the canonical image is missing, inspect `concept/` files and reselect the canonical concept.
- If Hunyuan fails because of image upload or model output shape, try Meshy with the same canonical image.
- If a quadruped result has broken limbs or poor topology, try Tripo and compare the GLB in Godot or Blender.
- If a vendor times out, rerun the same script only after checking whether a task id exists in the manifest.
- If dry-run output is needed, set `PIPELINE_DRY_RUN=1` and rerun the same command.

## Reference Index

- `references/hunyuan-3-1-replicate.md` covers the default Hunyuan 3D 3.1 route through Replicate.
- `references/meshy-fallback.md` covers Meshy v5 image-to-3D fallback behavior and model URL handling.
- `references/tripo-quadruped.md` covers Tripo3D fallback behavior for quadrupeds and optional credentials.
