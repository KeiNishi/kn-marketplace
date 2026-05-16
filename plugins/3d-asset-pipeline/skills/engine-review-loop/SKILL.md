---
name: engine-review-loop
description: This skill should be used when the user asks to run "stage 6", "engine review", "Godot screenshot capture", "review loop", "/3d-pipeline:review-godot", or any Stage 6 task in the 3D asset pipeline. It covers Godot screenshot capture, multimodal review, fix-instructions.json synthesis, and bounded apply-and-recapture iterations.
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

# Engine Review Loop

Run Stage 6 after Stage 5 has imported the asset into a Godot 4 project. This stage validates the asset inside the engine, captures canonical screenshots, reviews those screenshots against the manifest description and concept art, writes structured fixes, and repeats until approved or the configured iteration limit is reached.

Use this skill for Godot only. Treat Unity and Unreal review support as future work.

## Preconditions

Start by reading `3d-pipeline-output/<slug>/pipeline.json`.

Confirm:

- `stages.engine.status` is `done`.
- `stages.engine.engine` is `godot`.
- `stages.engine.projectPath` points to a project containing `project.godot`.
- `stages.engine.targetPath` or `stages.engine.scenePath` exists in the Godot project.
- `plugins/3d-asset-pipeline/godot/addons/3d_pipeline/` is available from `${CLAUDE_PLUGIN_ROOT}`.
- The user supplied `--project` or the manifest already provides the project path.

Stop with a user-fixable error when the imported asset is missing, the Godot project is invalid, or Stage 5 has not completed.

## Iteration Protocol

For iteration `N`, run:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/review_loop.py" <slug> --project <godot-project-root> --iter <N> --max-iters 5
```

Pass through user options:

- `--godot <path>` when the executable is not on `PATH`.
- `--base <dir>` for tests or non-standard output roots.
- `--apply-fixes <path>` when applying the previous iteration fix file.
- `--no-loop` when the user requests a single capture and verdict only.

The script copies the Godot addon into the project when missing, runs `apply_fixes.gd` when a fix file is supplied, runs `capture.gd`, verifies screenshots, and updates the `review` stage.

After capture, read every PNG in:

```text
3d-pipeline-output/<slug>/review/iter-<N>/
```

Read these files multimodally:

- `front.png`
- `three-quarter.png`
- `side.png`
- `back.png`
- `animation-mid.png`

Also read the manifest description and the canonical concept image when available:

```text
3d-pipeline-output/<slug>/concept/canonical.png
```

Compare the screenshots to the description, asset type, and concept art. Inspect the 1m reference cube in the front and three-quarter views before deciding on scale.

## Issue Triage

Classify every visible issue using `references/review-criteria.md`.

Check:

- Scale relative to the 1m cube.
- Orientation relative to the front camera.
- Pivot and ground contact.
- Materials and texture binding.
- Animation visibility in `animation-mid.png`.
- Topology integrity across all views.
- Match to the manifest description and canonical concept.

Mark an issue as `blocker` when it prevents practical use in game, such as missing geometry, clearly wrong orientation, severe scale mismatch, broken materials, or no visible animation on an animated asset. Mark an issue as `minor` when the asset is usable but needs polish, such as slightly dull material response or a small pivot offset.

Do not invent hidden problems. Base findings on screenshots, manifest data, and concept art only.

## Fix Synthesis

When issues are present, write:

```text
3d-pipeline-output/<slug>/review/iter-<N>/fix-instructions.json
```

Use the schema in `references/fix-recipes.md`.

Prefer deterministic, small fixes:

- Use `scale` for global size correction.
- Use `rotation_y_degrees` for facing direction.
- Use `material_overrides` for obvious missing or fallback materials.
- Use `default_animation` to select the best visible idle or motion clip.
- Use `import_options` only when Godot import settings are the likely cause.

Include `notes` with concise reasoning. Do not include API keys, local secrets, or unrelated project paths.

## Verdict Writing

Always write:

```text
3d-pipeline-output/<slug>/review/iter-<N>/verdict.json
```

Use:

```json
{
  "approved": false,
  "iter": 1,
  "issues": [
    {"category": "orientation", "severity": "blocker", "detail": "Asset faces away from CamFront."}
  ],
  "remaining": 1
}
```

Set `approved` to `true` only when no blocker remains and any minor issue is acceptable for the asset type. Set `remaining` to the count of unresolved issues. Keep issue details short and actionable.

Update the manifest review stage after writing a verdict:

- `status: done` when approved.
- `status: failed` when max iterations are exhausted with unresolved blockers.
- `approved: true|false`.
- `iterations: N`.
- `maxIters: <configured value>`.
- `loopEnabled: true|false`.
- `history` entries for each iteration.

Use existing manifest helper scripts when possible.

## Apply and Recapture

If `approved` is false and looping is enabled:

1. Write `fix-instructions.json`.
2. Run the next iteration with `--apply-fixes` pointing at that file.
3. Read the new PNGs multimodally.
4. Compare against the prior issues and identify regressions.
5. Write the next verdict.

Example:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/review_loop.py" <slug> --project <project> --iter 2 --apply-fixes 3d-pipeline-output/<slug>/review/iter-1/fix-instructions.json
```

`apply_fixes.gd` stores persistent setup data in `review/setup.json`; `capture.gd` reads it on the next pass.

## Termination Conditions

Stop when any condition is true:

- `verdict.json` has `approved: true`.
- Iteration count reaches `--max-iters`.
- The user selected `--no-loop`.
- Capture fails with a user-fixable error.
- A proposed fix would require regenerating the asset in Stage 1 through Stage 4.

When max iterations are reached without approval, record unresolved issues in the final verdict and manifest. Do not silently continue beyond the limit.

## No-Loop Handling

When `--no-loop` is present, capture once, review once, write `verdict.json`, and stop. If fixes are identified, write `fix-instructions.json` for later manual use, but do not run another capture. Record `loopEnabled: false` in the review stage.

## Reference Files

- `references/review-criteria.md` - Visual inspection criteria, severity, and prompts.
- `references/godot-capture-protocol.md` - Capture script arguments, camera positions, output files, and timeout rules.
- `references/fix-recipes.md` - Fix JSON schema, recipes, and verdict schema.
