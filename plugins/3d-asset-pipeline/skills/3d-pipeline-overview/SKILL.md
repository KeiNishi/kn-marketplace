---
name: 3d-pipeline-overview
description: This skill should be used when the user asks to "run the 3D pipeline", "check pipeline status", "resume an asset", or mentions pipeline.json, 3d-pipeline-output, or stage routing for the 3d-asset-pipeline. It coordinates the six stages (concept, mesh, rig, animate, engine import, review), reads and updates pipeline.json, checks stage prerequisites, and decides which stage to run next. Also triggers on "/3d-pipeline:run-pipeline" and "/3d-pipeline:pipeline-info" commands.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion
---

# 3D Pipeline Overview

This skill coordinates the Godot-first 3D asset pipeline. Use it to inspect `pipeline.json`, choose the next stage, and keep stage data synchronized.

## Locating the Plugin

All `scripts/...` paths in this skill are relative to the plugin root. In Claude Code the plugin root is `${CLAUDE_PLUGIN_ROOT}`; in other agents, locate the installed plugin directory first and prefix script paths with it. Run scripts with `python3` from the workspace that contains `3d-pipeline-output/` (on Windows, use `py -3` if `python3` is not available).

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

## Schema 1.2

Schema bumped from `1.1` to `1.2` in plugin v0.2.0. Manifests with `schemaVersion: "1.1"` are still readable; the first `_manifest.update_stage` call rewrites them as `1.2`.

New fields on the `concept` stage:

- `approved: bool` — set by `scripts/approve_concept.py`. Defaults to absent (treated as `false`).
- `approvedAt: ISO-8601 string | null` — timestamp of the approval.
- `approvedBy: "user" | null` — who approved. Currently always `"user"`.
- `failureKind: "moderation_blocked" | "api_error" | "user_error" | "timeout" | "codex_usage_limit" | "codex_error"` — set when `status == failed` so the concept skill can surface tailored recovery text. The `codex_*` kinds apply only when Stage 1 used the `codex` image-generation backend; see `skills/concept-art-generation/references/codex-backend.md`.

Use `_manifest.concept_approved(manifest)` to check approval; mesh preflight scripts already do this.

## References

- `references/pipeline-stages.md`
- `references/manifest-schema.md`
- `references/credentials.md`

## Pre-flight Checks

- Run `python3 scripts/doctor.py` (path relative to the plugin root) before starting paid or long-running stages.
- Stop when the doctor reports failed checks and ask the user to run `/3d-pipeline:check-pipeline`.
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

- **Concept gate (mechanical)**: ask for user approval after canonical concept selection. Mesh scripts (`mesh_hunyuan.py`, `mesh_meshy.py`, `mesh_tripo.py`) refuse to run while `stages.concept.approved` is not `true`. Record approval via `scripts/approve_concept.py <slug> --approve`. Use `/3d-pipeline:approve` as the user-facing command.
- **Mesh / rig / animate gates (advisory)**: ask for user approval before each subsequent stage. Stop cleanly when the user declines and report the current output folder.

## Output Layout

- Store all asset outputs under `3d-pipeline-output/<slug>/`.
- Use `concept/`, `mesh/`, `rigged/`, `animated/`, `engine/`, and `review/` for stage artifacts.
- Keep review captures under `review/iter-<N>/` with `verdict.json` and optional `fix-instructions.json`.

## Security Reminder

- Read API keys only from `~/.claude/3d-pipeline/.env` (`%USERPROFILE%\.claude\3d-pipeline\.env` on Windows).
- Never store API keys, credential paths, or secret values in the repository or manifest.
- Leave plugin and marketplace version fields unchanged unless a task explicitly asks for version updates.
