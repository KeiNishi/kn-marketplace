---
name: status
description: Print the pipeline.json status table for an asset slug -- stage names, statuses, vendors, and key file paths.
argument-hint: "<asset-slug>"
allowed-tools: Read, Bash
---

# 3D Pipeline Status Command

Print the current manifest status for one asset.

Require `<asset-slug>` as the first argument.

If it is missing, print:

```text
Usage: /3d-pipeline:status <asset-slug>
```

Read:

```text
3d-pipeline-output/<asset-slug>/pipeline.json
```

If `pipeline.json` is missing, print:

```text
No pipeline.json found for <asset-slug>. Run /3d-pipeline:init or /3d-pipeline:run first.
```

Then stop.

Print header fields: `slug`, `assetType`, `dryRun`, and `updatedAt`.

Print a table:

```text
Stage      Status       Vendor            Key file
concept    done         openai:gpt-image  concept/canonical.png
mesh       done         hunyuan           mesh/<slug>.glb
rig        skipped      -                 -
animate    skipped      -                 -
engine     done         godot             assets/characters/<slug>/<slug>.tscn
review     done         local             review/iter-1/verdict.json
```

For each row, read `stages.<stage>.status` and `stages.<stage>.vendor`.

For key file, prefer `files.canonical`, `files.glb`, `files.fbx`, `files.output`, `scenePath`, `targetPath`, then `verdictPath`.

If no key file is recorded, print `-`.

If a stage has `error`, print a concise indented error line under that stage.
