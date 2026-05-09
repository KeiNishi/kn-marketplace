---
name: 3d-pipeline-overview
description: Use this skill for routing the 3d-asset-pipeline stages, reading or updating pipeline.json, checking stage prerequisites, or deciding which stage command to run next.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion
---

# 3D Pipeline Overview

This skill coordinates the Godot-first 3D asset pipeline. Use it to inspect `pipeline.json`, choose the next stage, and keep stage data synchronized.

## Stage Order

1. `concept`: Generate four multi-angle PNGs and select `concept/canonical.png`.
2. `mesh`: Generate a textured GLB from the canonical concept image.
3. `rig`: Add a humanoid or quadruped skeleton. Skip for props.
4. `animate`: Add gameplay animation clips. Skip for props.
5. `engine`: Import the asset into a Godot 4 project.
6. `review`: Capture in-engine screenshots, synthesize fixes, and repeat until approved or max iterations are reached.

## Manifest Rules

- Read and write only `3d-pipeline-output/<slug>/pipeline.json`.
- Use `scripts/_manifest.py` helpers when a script is available.
- Keep stage `status` values in `pending`, `in_progress`, `done`, `failed`, or `skipped`.
- Update `updatedAt` whenever a stage changes.
- Never store API keys or credential paths in the manifest.

## References

- `references/pipeline-stages.md`
- `references/manifest-schema.md`
- `references/credentials.md`

## Pre-flight Checks

- Run `scripts/doctor.py` before starting paid or long-running stages.
- Stop when the doctor reports failed checks and ask the user to run `/3d-pipeline:doctor`.
- Confirm `PIPELINE_DRY_RUN=1` is set in the same shell session when dry-run behavior is expected.

## Asset Type Detection

- Use `humanoid` when the asset has a two-legged character skeleton.
- Use `quadruped` when the asset moves on four legs and needs animal-style rigging.
- Use `prop` when the asset is static or does not need rigging and animation.

## Vendor Routing Table

| Asset type | Default mesh vendor | Notes |
| --- | --- | --- |
| `humanoid` | `hunyuan` | Use Meshy for rig and animation after mesh generation. |
| `quadruped` | ask user | Consider Tripo fallback when Hunyuan struggles with animal forms. |
| `prop` | `hunyuan` | Skip rig and animate stages. |

## Manifest-driven Resume

- Treat `pipeline.json` as the source of truth for completed, failed, pending, and skipped stages.
- Read the manifest before running a stage and after every script completes.
- Resume from the first stage whose status is `pending` or `failed`, unless the user explicitly requests a fresh asset.

## Approval Gates

- Ask for user approval after canonical concept selection before mesh generation.
- Ask for user approval after mesh generation before rig, animation, or import.
- Stop cleanly when the user declines and report the current output folder.

## Output Layout

- Store all asset outputs under `3d-pipeline-output/<slug>/`.
- Use `concept/`, `mesh/`, `rigged/`, `animated/`, `engine/`, and `review/` for stage artifacts.
- Keep review captures under `review/iter-<N>/` with `verdict.json` and optional `fix-instructions.json`.

## Security Reminder

- Read API keys only from `~/.claude/3d-pipeline/.env`.
- Never store API keys, credential paths, or secret values in the repository or manifest.
- Leave plugin and marketplace version fields unchanged unless a task explicitly asks for version updates.
