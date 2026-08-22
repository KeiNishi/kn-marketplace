# 3D Asset Pipeline Troubleshooting Guide

## Contents

- [Stage 1: concept_openai.py](#stage-1-concept_openaipy)
- [Stage 2: Hunyuan Replicate mesh_hunyuan.py](#stage-2-hunyuan-replicate-mesh_hunyuanpy)
- [Stage 2: Meshy mesh_meshy.py](#stage-2-meshy-mesh_meshypy)
- [Stages 3-4: Rig and Animate](#stages-3-4-rig-and-animate)
- [Stage 5: Godot Import](#stage-5-godot-import)
- [Stage 6: Review Loop](#stage-6-review-loop)
- [Hooks](#hooks)
- [General](#general)
- [Recovering From a Failed Stage](#recovering-from-a-failed-stage)

Use this guide when a stage fails, stalls, produces incomplete files, or needs manual recovery.

## Stage 1: concept_openai.py

Missing `OPENAI_API_KEY` means the key is absent from `~/.claude/3d-pipeline/.env`. This only blocks Stage 1 when the `openai` backend is selected; if the Codex CLI is on `PATH` with an active ChatGPT subscription, use `--backend codex` instead and no key is needed.

Run `/3d-pipeline:check-pipeline` and fix the credentials file outside the repository, or confirm the Codex CLI subscription backend instead.

`failureKind: "codex_usage_limit"` means the codex backend was selected and the ChatGPT subscription's usage limit is exhausted. Wait for the reset time shown in `stages.concept.error`, buy more usage credits, or rerun with `--backend openai`.

`failureKind: "codex_error"` means the codex backend failed for another reason (tool error, or `codex exec` exited 0 but produced no valid PNG). Inspect `stages.concept.error`, retry, or rerun with `--backend openai`. There is no automatic fallback from codex to openai on failure -- this is deliberate, to avoid surprise API spend.

HTTP `429` means the OpenAI image API rate limit or quota was reached.

Wait for reset, reduce parallel generation, or retry later.

Content-policy refusals from `gpt-image-2` usually come from violent, NSFW, exploitative, or otherwise disallowed prompts.

Rewrite the description as game-safe production art focused on silhouette, materials, shape language, and rigging needs.

Treat `4xx` responses as request, key, billing, prompt, access, or malformed-argument problems; treat `5xx` responses as transient provider failures and retry after a delay.

If PNG files are not generated, check command output, `pipeline.json`, and the concept folder.

Confirm `front.png`, `three-quarter.png`, `side.png`, and `back.png` exist before selecting `canonical.png`.

## Stage 2: Hunyuan Replicate mesh_hunyuan.py

Prediction failures are auto-retried three times by the script.

If all retries fail, inspect `stages.mesh.error` and any provider prediction id in `pipeline.json`.

Rapid mode usually takes 2-3 minutes; Turbo or higher-quality mode can take 5-10 minutes.

If a timeout occurs, check the provider dashboard before starting a duplicate paid job.

GLB download failures can happen because Replicate output URLs expire after about 1 hour.

When the prediction succeeded but the GLB was not downloaded, reset the mesh stage status to `pending` and rerun the stage.

If image input is rejected, confirm `concept/canonical.png` is a valid PNG under 8 MB, then regenerate or compress the canonical image when needed.

Missing `REPLICATE_API_TOKEN` means the token is absent from `~/.claude/3d-pipeline/.env`.

Run `/3d-pipeline:check-pipeline` before rerunning Hunyuan.

## Stage 2: Meshy mesh_meshy.py

Rate limits should be handled with backoff; if retries still fail, wait for the provider window to reset.

Plan credit limits appear as quota, account, payment, or credit errors, so check the Meshy dashboard before rerunning paid tasks.

Prefer image-to-3D when `concept/canonical.png` exists.

Use text-to-3D only when the concept stage is intentionally bypassed or the vendor rejects image input.

## Stages 3-4: Rig and Animate

If the humanoid template cannot detect joints, regenerate a clear front-facing concept.

Visible head, shoulders, hips, hands, knees, and feet improve detection.

Avoid crossed limbs, extreme perspective, capes hiding joints, or props covering the body.

Animated FBX files may contain multiple takes.

`import_godot.py` relies on Godot import behavior to split clips.

If clips are missing, inspect the imported animations in the Godot editor.

The rig task id is stored in `pipeline.json` at `stages.rig.task_id`.

If the dashboard has a task but the manifest lacks it, record the id before retrying.

For `assetType=prop`, skipping rig and animate is expected.

Do not force static props through humanoid or quadruped rigging.

## Stage 5: Godot Import

`project.godot` not found means the project path is wrong or relative.

Use an absolute path to the Godot project root.

On Windows, quote paths with spaces or use forward slashes.

If `.import` files do not regenerate, run `godot --headless --import` from the Godot project root.

If the Godot CLI is not on `PATH`, set `GODOT_BIN` in `~/.claude/3d-pipeline/.env`.

Do not store `GODOT_BIN` in the repository.

If the scene file is not created, rerun import with `--scene`.

Then check `stages.engine.scenePath` and the target asset directory.

## Stage 6: Review Loop

If the addon is not installed, check `addons/capture/capture.gd` and the plugin-provided capture files.

A black screen can indicate renderer problems, missing resources, or an invisible transform.

Try `GODOT_RENDERING_DRIVER=opengl3` and rerun capture.

Godot crashes usually require Godot 4.2+ or fixing missing resources, broken paths, unsupported materials, or invalid animation tracks.

If screenshots show the same angle, camera rotation may not be applied.

Inspect the capture scene, camera node names, and Godot headless output.

Confirm each screenshot is newly written for the current iteration.

## Hooks

If Claude Code PreToolUse blocks edits, the secret-protection hook probably detected a credential-like write.

Set `DISABLE_3D_PIPELINE_HOOKS=1` only for the emergency maintenance shell session, then unset it.

Never bypass hooks to commit secrets.

On Windows, `cursor-agent` currently composes Claude command hooks as PowerShell and then evaluates them with bash when `MSYSTEM` is set. That bash eval exits 2, which cursor-agent treats as a deny, so every Write/Edit is blocked even when the file has no secrets. This plugin therefore keeps the Write/Edit PreToolUse command hook in `hooks/hooks.json` (Claude Code loads that file automatically) and points `plugin.json` `hooks` at `hooks/session-start.json` (SessionStart only). cursor-agent imports the manifest hook path instead of `hooks/hooks.json`. Do not add a PreToolUse command hook to `plugin.json` or to `hooks/session-start.json`; that would restore the cursor-agent full-deny.

A SessionStart warning for `.env.example` is a false positive.

Real credentials belong at `~/.claude/3d-pipeline/.env`, not in the repo.

## General

`PIPELINE_DRY_RUN=1` must be set in the same shell session that runs the command.

It does not apply retroactively to jobs already started.

The credentials file must be at `~/.claude/3d-pipeline/.env`.

Do not store credentials in the plugin, marketplace, or project repository.

For mixed slashes on Windows, use quotes or forward slashes, such as `"D:/Projects/My Godot Game"`.

## Recovering From a Failed Stage

Open `3d-pipeline-output/<slug>/pipeline.json`.

Find the failed stage under `stages`.

Change that stage `status` to `pending`.

Save the file.

Rerun the stage command or `/3d-pipeline:run-pipeline`.

Keep previous provider task ids in notes when needed for billing or dashboard investigation.
