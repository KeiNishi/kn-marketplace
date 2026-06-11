---
name: godot-import
description: Stage 5 of the 3D asset pipeline -- copy the final asset into a Godot 4 project and emit the import config. Godot 4 only in v0.1.0.
argument-hint: "<asset-slug> --project <godot-project-root> [--source-stage animated|mesh|rigged] [--scene]"
allowed-tools: Read, Write, Bash, AskUserQuestion
---

# 3D Pipeline Godot-Import Command

Copy the final Stage 5 asset into a Godot 4 project and emit Godot import metadata.

## Argument Handling

Parse `$ARGUMENTS` as:

```text
<asset-slug> --project <godot-project-root> [--source-stage animated|mesh|rigged] [--scene]
```

Require the first token as `<asset-slug>`. If it is missing, show usage and stop.

If `--project` is missing, ask the user with `AskUserQuestion` for the absolute Godot project root path. The path must contain `project.godot`.

Pass through:

- `--project <godot-project-root>`
- `--source-stage animated|mesh|rigged`
- `--scene`

## Preflight

Read `3d-pipeline-output/<asset-slug>/pipeline.json`.

Confirm:

- `stages.mesh.status` is `done`.
- Props import from `mesh/<asset-slug>.glb`.
- Humanoid and quadruped assets import from `animated/<asset-slug>.fbx` by default.
- If animation is skipped, the script can fall back to `rigged/<asset-slug>.fbx`.
- If rigging is also skipped, the script can fall back to `mesh/<asset-slug>.glb`.
- The Godot project path is absolute and contains `project.godot`.

## Script Invocation

Run (on Windows, use `py -3` if `python3` is not available):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/import_godot.py" <asset-slug> --project <godot-project-root> [--source-stage animated|mesh|rigged] [--scene]
```

Use `--base <dir>` only for automated tests or non-standard output locations.

## Reporting

After the script exits successfully, read `pipeline.json` again and print:

- Engine status.
- Godot project path.
- Target asset path.
- Import file path.
- Scene wrapper path when present.

Then remind the user that Godot will auto-import the asset the next time the project opens. For immediate import cache generation, suggest running this from the Godot project root:

```bash
godot --headless --import
```

## Notes

- Use the godot-import skill for import option details and format choice.
- Set `PIPELINE_DRY_RUN=1` only when earlier stages created placeholder source files.
- Never modify plugin or marketplace version fields.
