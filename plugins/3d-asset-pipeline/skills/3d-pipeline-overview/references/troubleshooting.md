# 3D Asset Pipeline Troubleshooting Guide

Use this guide when a stage fails, stalls, produces incomplete files, or needs manual recovery.

## Stage 1: concept_openai.py

Missing `OPENAI_API_KEY` means the key is absent from `~/.claude/3d-pipeline/.env`.

Run `/3d-pipeline:doctor` and fix the credentials file outside the repository.

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

Run `/3d-pipeline:doctor` before rerunning Hunyuan.

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

If PreToolUse blocks edits, the secret-protection hook probably detected a credential-like write.

Set `DISABLE_3D_PIPELINE_HOOKS=1` only for the emergency maintenance shell session, then unset it.

Never bypass hooks to commit secrets.

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

Rerun the stage command or `/3d-pipeline:run`.

Keep previous provider task ids in notes when needed for billing or dashboard investigation.
