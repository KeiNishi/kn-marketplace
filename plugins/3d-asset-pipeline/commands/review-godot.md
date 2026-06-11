---
name: review-godot
description: Stage 6 capture, review, fix, and iterate for a Godot-imported 3D asset.
argument-hint: "<asset-slug> --project <godot-project-root> [--max-iters 5] [--no-loop] [--godot <path>] [--base <dir>]"
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

# 3D Pipeline Review-Godot Command

Run Stage 6 of the 3D asset pipeline for an asset already imported into Godot by Stage 5.

Use the `engine-review-loop` skill for the review criteria, capture protocol, fix schema, and termination rules.

## Argument Handling

Parse `$ARGUMENTS` as:

```text
<asset-slug> --project <godot-project-root> [--max-iters 5] [--no-loop] [--godot <path>] [--base <dir>]
```

Require the first token as `<asset-slug>`. If it is missing, show usage and stop.

If `--project` is missing, read `3d-pipeline-output/<asset-slug>/pipeline.json` and use `stages.engine.projectPath` when present. If the manifest has no project path, ask the user for the absolute Godot project root with `AskUserQuestion`.

Default `--max-iters` to `5`. Treat `--no-loop` as capture once, review once, then stop.

Pass through:

- `--project <godot-project-root>`
- `--max-iters <N>`
- `--no-loop`
- `--godot <path>`
- `--base <dir>`

## Preflight

Read `3d-pipeline-output/<asset-slug>/pipeline.json`.

Confirm:

- `stages.engine.status` is `done`.
- `stages.engine.engine` is `godot`.
- The Godot project path is absolute and contains `project.godot`.
- `stages.engine.targetPath` or `stages.engine.scenePath` is present.

Run status when useful:

On Windows, use `py -3` if `python3` is not available.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review_loop.py" <asset-slug> --status
```

If the status says the review is already approved, report the approved iteration and stop.

## Iteration 1

Run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review_loop.py" <asset-slug> --project <godot-project-root> --iter 1 --max-iters <N>
```

Add `--godot <path>` and `--base <dir>` when provided.

After the command succeeds, read the PNGs in:

```text
3d-pipeline-output/<asset-slug>/review/iter-1/
```

Read `front.png`, `three-quarter.png`, `side.png`, `back.png`, and `animation-mid.png` multimodally. Also read `concept/canonical.png` when present and compare against `pipeline.json.description`.

## Review

Evaluate:

- Scale against the 1m cube.
- Orientation against `CamFront`.
- Pivot and ground contact.
- Materials and texture assignment.
- Animation visibility.
- Topology integrity.
- Match to description and concept.

Write:

```text
3d-pipeline-output/<asset-slug>/review/iter-<N>/verdict.json
```

If issues remain, write:

```text
3d-pipeline-output/<asset-slug>/review/iter-<N>/fix-instructions.json
```

Use the schema from `skills/engine-review-loop/references/fix-recipes.md`.

## Apply and Continue

If `approved` is false, looping is enabled, and `N < max-iters`, run the next iteration with the prior fix file:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review_loop.py" <asset-slug> --project <godot-project-root> --iter <N+1> --max-iters <max> --apply-fixes 3d-pipeline-output/<asset-slug>/review/iter-<N>/fix-instructions.json
```

Read the new screenshots, compare against the previous verdict, and write the next verdict.

Repeat until approved or the iteration limit is reached.

## No-Loop Mode

When `--no-loop` is present:

1. Capture the requested iteration.
2. Read screenshots multimodally.
3. Write `verdict.json`.
4. Write `fix-instructions.json` if fixes are useful.
5. Stop without running another capture.

Record `loopEnabled: false` in the manifest review stage.

## Completion

On approval, update the manifest review stage with:

- `status: done`
- `approved: true`
- `iterations: <N>`
- `maxIters: <max>`
- `loopEnabled: true|false`
- `completedAt`

On max iterations with unresolved blockers, update the manifest review stage with:

- `status: failed`
- `approved: false`
- `iterations: <max>`
- `maxIters: <max>`
- unresolved issue history

Never modify plugin or marketplace version fields.
