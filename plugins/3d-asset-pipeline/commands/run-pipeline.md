---
name: run-pipeline
description: Run the full 6-stage 3D asset pipeline (concept to mesh to rig to animate to import to review) with approval gates between stages and an automatic in-engine review loop. Default review loop is ON; use --no-review to skip.
argument-hint: "<asset-name> <description> [--type humanoid|quadruped|prop] [--no-review] [--max-iters 5] [--engine-project <godot-project-root>] [--vendor hunyuan|meshy|tripo|local]"
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

# 3D Pipeline Run Command

Use the `3d-pipeline-overview` skill to coordinate the complete asset workflow.

This command runs concept, mesh, rig, animate, Godot import, and review.

Treat every script as the source of deterministic work and `pipeline.json` as the state source.

## 1. Parse Arguments

Parse `$ARGUMENTS` as:

```text
<asset-name> <description> [--type humanoid|quadruped|prop] [--no-review] [--max-iters 5] [--engine-project <godot-project-root>] [--vendor hunyuan|meshy|tripo|local]
```

Require `asset-name` as the first positional argument.

Require `description` as the second positional argument; accept quoted descriptions with spaces.

If required arguments are missing, print usage and stop.

Default `--type` to `humanoid`.

Validate `--type` as `humanoid`, `quadruped`, or `prop`.

Default `--no-review` to `false`, so the review loop is enabled.

Default `--max-iters` to `5` and reject values below `1`.

If `--engine-project` is missing, ask for the absolute Godot project root with `AskUserQuestion`.

Validate that the project path contains `project.godot` before Stage 5.

Default `--vendor` to `hunyuan` for `humanoid` and `prop`.

For `quadruped`, ask the user which vendor to use unless `--vendor` is present.

Offer `hunyuan`, `meshy`, `tripo`, and `local`; recommend `tripo` when quadruped shape recovery is more important than default fidelity, and recommend `local` when the user wants no API cost or has no `REPLICATE_API_TOKEN`.

Derive the initial slug by lowercasing the asset name and replacing spaces with hyphens.

Use `_common.slugify` during manifest creation so punctuation matches the script rules.

Print the resolved asset name, slug, description, type, vendor, review setting, max iterations, and Godot project path.

## 2. Pre-Flight

Run:

On Windows, use `py -3` if `python3` is not available.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py"
```

Capture output.

If any line contains `[FAIL]`, abort.

Print:

```text
Pre-flight checks failed. Run /3d-pipeline:check-pipeline before running the full pipeline.
```

Do not initialize or modify the manifest after a failed doctor run.

### Meshy fallback to prop mode

`MESHY_API_KEY` is optional. The doctor reports `[WARN]` (not `[FAIL]`) when
it is missing, so pre-flight will pass.

If the resolved type is `humanoid` or `quadruped` and the doctor output
contains `[WARN] Credential MESHY_API_KEY: missing optional key`, the
rig and animate stages cannot run. Use `AskUserQuestion` to ask the user
to either:

- Switch the run to `--type prop` (rig and animate become `skipped`,
  pipeline continues through Stage 5 and Stage 6), or
- Abort and add `MESHY_API_KEY` to `~/.claude/3d-pipeline/.env` first.

If the user picks the prop fallback, replace the resolved `--type` with
`prop` for the rest of this run and note the override in the run summary.

## 3. Cost Preamble

Skip this step when `PIPELINE_DRY_RUN=1` is set in the same shell session.

Otherwise show the estimated spend before paid API calls:

- Humanoid: about USD 0.50-2.00.
- Prop: about USD 0.20-0.80.
- Quadruped: about USD 0.80-2.50.

Keep these amounts written as `USD n.nn`. Never write a dollar sign directly before a digit in this file: `$` followed by a digit collides with positional-argument substitution when this command renders.

When the resolved `--vendor` is `local`, the mesh stage costs USD 0 (it runs on the user's own GPU, no API call). Concept stage cost (OpenAI, Stage 1) is unchanged. Lower the estimate shown to the user by the mesh-vendor share of the range above, and note that the mesh stage itself is free.

Use `AskUserQuestion` to confirm paid execution.

Abort unless the user explicitly approves.

## 4. Initialize Manifest

Run Python to call `_manifest.init`:

```bash
python3 -c "import sys; sys.path.insert(0, r'${CLAUDE_PLUGIN_ROOT}'); from scripts import _common, _manifest; name=r'<asset-name>'; description=r'<description>'; asset_type=r'<asset-type>'; slug=_common.slugify(name); manifest=_manifest.init(slug, name, description, asset_type); print(slug); print(_manifest.manifest_path(slug))"
```

If the manifest already exists, stop and report the existing `pipeline.json`.

Print the slug and output folder:

```text
3d-pipeline-output/<slug>/
```

Read `pipeline.json` and confirm all six stages exist.

## 5. Stage 1 Concept

Run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/concept_openai.py" <slug> --defer-canonical
```

Read the four PNGs multimodally:

- `concept/front.png`
- `concept/three-quarter.png`
- `concept/side.png`
- `concept/back.png`

Ask with `AskUserQuestion` which angle is canonical.

Default recommendation: `three-quarter`.

Valid answers: `front`, `three-quarter`, `side`, `back`.

Run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/concept_openai.py" <slug> --select-canonical <angle>
```

Read `concept/canonical.png` multimodally and compare it with the description.

## 6. Approval Gate After Concept

Display or read `concept/canonical.png`.

Ask whether to proceed to Stage 2 mesh generation.

Use `AskUserQuestion` with `yes` and `stop`.

If the user chooses `stop`, report the slug and concept folder, then end. The user can run `/3d-pipeline:approve <slug>` later to unblock mesh generation, or `/3d-pipeline:concept <slug> --description "<new text>"` to re-roll first.

If the user chooses `yes`, record the approval so the mesh preflight passes:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/approve_concept.py" <slug> --approve
```

The mesh scripts refuse to run while `stages.concept.approved` is not `true`. The gate is enforced inside the mesh preflight, so a stopped run can always resume by approving from a separate session.

## 7. Stage 2 Mesh

Run exactly one vendor script:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/mesh_hunyuan.py" <slug>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/mesh_meshy.py" <slug>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/mesh_tripo.py" <slug>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/mesh_trellis_local.py" <slug>
```

Select the command that matches the resolved vendor.

Tell the user that script logger output shows progress and the stage normally takes 2-5 minutes. For `local`, the stage runs on the user's GPU and normally takes 2-5 minutes as well (measured ~107s rapid, ~294s pro on an RTX 4070 Ti); it blocks the shell until the generation finishes.

After the script exits, read `pipeline.json`.

Report mesh status, vendor, prediction id or task id, GLB path, FBX path when present, and error when failed.

If mesh failed, stop and suggest `/3d-pipeline:pipeline-info <slug>`.

## 8. Approval Gate After Mesh

Show the GLB path from the manifest.

Ask whether to proceed.

Use `AskUserQuestion` with `yes` and `stop`.

If the user chooses `stop`, report the mesh folder and leave later stages pending or skipped.

## 9. Stages 3-4 Rig and Animate

If `assetType` is `prop`, do not run rigging or animation.

Log that prop rig and animate stages are expected to stay `skipped`.

For `humanoid` and `quadruped`, run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/rig_meshy.py" <slug>
```

Read `pipeline.json`.

If rigging failed, stop and report `stages.rig.error` and `stages.rig.task_id` when present.

Then run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/animate_meshy.py" <slug>
```

Read `pipeline.json`.

If animation failed, stop and report `stages.animate.error`.

## 10. Stage 5 Engine Import

Run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/import_godot.py" <slug> --project "<engine-project>" --scene
```

Read `pipeline.json`.

Report `stages.engine.status`, `projectPath`, `targetPath`, and `scenePath`.

If import failed, stop and report the engine error.

## 11. Stage 6 Review Loop

If `--no-review` is present, update the review stage to `status=skipped`, `approved=false`, and `loopEnabled=false`, then skip to the final summary.

Otherwise iterate from `1` to `max-iters`.

For iteration `1`, run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review_loop.py" <slug> --project "<engine-project>" --iter 1 --max-iters <max-iters>
```

For iteration `N > 1`, run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review_loop.py" <slug> --project "<engine-project>" --iter <N> --max-iters <max-iters> --apply-fixes "3d-pipeline-output/<slug>/review/iter-<N-1>/fix-instructions.json"
```

After each capture, read all PNGs in `review/iter-<N>/` multimodally.

Read `concept/canonical.png` for comparison.

Read `pipeline.json`.

Check scale, orientation, ground contact, pivot, materials, textures, animation visibility, topology, and description match.

If no issues remain, write `review/iter-<N>/verdict.json` with `approved=true`, then update review status to `done`, `approved=true`, `iterations=N`, `maxIters=<max-iters>`, and break.

If issues remain, write `verdict.json` with `approved=false` and write `fix-instructions.json`, then continue.

After the final allowed iteration, if unresolved issues remain, set review status to `failed` and `error=review-loop unresolved`.

## 12. Final Summary

Print slug, output folder, Godot target path, Godot scene path, review verdict path, review approval status, and iteration count.

Print:

```text
Security reminder: API keys remain in ~/.claude/3d-pipeline/.env; this plugin never reads keys from the repo.
```

Do not modify plugin or marketplace version fields.
