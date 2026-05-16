# 3D Asset Pipeline

## Overview

`3d-asset-pipeline` is a Claude Code plugin for a Godot-first 3D game asset workflow.

The planned pipeline has six stages:

1. Concept art generation from a text description.
2. Mesh generation from the selected concept image and prompt.
3. Auto-rigging for humanoid and quadruped assets.
4. Auto-animation for common game-ready clips.
5. Import into a Godot 4 project.
6. In-engine review loop with screenshots, issue detection, fixes, and re-capture.

The v0.1.0 target is Godot-first.

Unity 6 and Unreal 5 support are planned for later versions.

This plugin is designed around cloud APIs instead of local GPU generation.

The intended vendor stack is:

- OpenAI `gpt-image-2` for concept images.
- Hunyuan 3D 3.1 through Replicate for default mesh generation.
- Meshy v5 for alternate mesh generation, rigging, and animation.
- Tripo3D as an optional fallback for selected asset types.

The review loop is intended to compare the imported asset against the source description and concept art.

It checks visible issues such as scale, orientation, pivot placement, missing materials, animation playback, and concept match.

The current plugin includes setup documentation, security hooks, shared Python helpers, health checks, and the Stage 1 concept-art command, skill, and OpenAI client script.

Mesh, rigging, animation, Godot import, review loop, fixtures, and Godot addon files are planned for later chunks.

## Installation

Add the marketplace:

```text
/plugin marketplace add KeiNishi/kn-marketplace
```

Install the plugin:

```text
/plugin install 3d-asset-pipeline@kn-marketplace
```

After installation, restart Claude Code if the plugin does not appear immediately.

## Setup / API Keys

**Never put API keys inside this repo. This is a public repository.**

API keys must live outside the repository.

Create this file:

```text
~/.claude/3d-pipeline/.env
```

On Windows, the same file is:

```text
%USERPROFILE%\.claude\3d-pipeline\.env
```

Use this format:

```dotenv
OPENAI_API_KEY=sk-...
REPLICATE_API_TOKEN=r8_...
# Optional: MESHY_API_KEY=msy_...   # enables stages 3-4 (auto-rig, auto-animation)
# Optional: TRIPO_API_KEY=tsk_...   # quadruped fallback only
# Optional: GODOT_BIN=C:\path\to\godot.exe   # used by /3d-pipeline:godot-import to auto-build the import cache
```

Do not commit this file.

Do not copy it into the plugin directory.

Do not place `.env`, `.env.local`, or `.env.*` files in this repository.

Do not paste real key values into Markdown, JSON, scripts, command files, or issue reports.

The future pipeline scripts will read credentials only from the user-level Claude directory.

Expected key providers:

- OpenAI: https://platform.openai.com/
- Replicate: https://replicate.com/
- Meshy: https://www.meshy.ai/
- Tripo3D: https://www.tripo3d.ai/

Required keys for stages 1, 2, 5, and 6:

- `OPENAI_API_KEY`
- `REPLICATE_API_TOKEN`

Optional keys:

- `MESHY_API_KEY` — enables stages 3 and 4 (auto-rig, auto-animation). Without it, humanoid and quadruped runs must fall back to prop mode so the rig and animate stages stay skipped.
- `TRIPO_API_KEY` — quadruped fallback only.

## Python Prerequisites

Use Python 3.10 or newer.

Install dependencies from the plugin root:

```bash
pip install -r requirements.txt
```

The dependency list is intentionally small for the first version:

- `requests`
- `python-dotenv`
- `pillow`
- `replicate`
- `openai`

Later chunks will add scripts that use these packages.

## Quick Start

The health check command is:

```text
/3d-pipeline:check-pipeline
```

The planned full pipeline command is:

```text
/3d-pipeline:run-pipeline <name> <description>
```

Example:

```text
/3d-pipeline:run-pipeline knight-hero "Stoic plate armor knight with a longsword"
```

The concept stage can be run after a manifest is initialized:

```text
/3d-pipeline:concept <slug> --defer-canonical
```

The remaining stage commands are planned for later chunks.

They are documented here so users can understand the intended workflow before the command files are added.

## Concept Approval Gate

Stage 2 mesh generation is mechanically blocked until a human approves the canonical concept. This prevents accidental mesh spend on un-vetted concept art.

After Stage 1 completes, run:

```text
/3d-pipeline:approve <slug>
```

This sets `stages.concept.approved: true` in `pipeline.json`. The mesh preflight in `mesh_hunyuan.py`, `mesh_meshy.py`, and `mesh_tripo.py` refuses to run when `approved` is not `true`.

Other approve options:

```text
/3d-pipeline:approve <slug> --reject              # withdraw approval
/3d-pipeline:approve <slug> --canonical <angle>   # change canonical, then approve
```

If the moderation system rejects a concept prompt, the manifest stage records `failureKind: "moderation_blocked"`. Re-run the concept stage with new wording:

```text
python scripts/concept_openai.py <slug> --description "<softer text>"
```

`--description` overwrites the manifest description and resets the concept stage to `pending` before regenerating.

Inside the full pipeline command (`/3d-pipeline:run-pipeline`), the gate appears as an inline `AskUserQuestion(yes/stop)` prompt that auto-approves on yes.

## Manifest schema 1.2

Plugin v0.2.0 bumps the manifest schema from `1.1` to `1.2`. Manifests with `schemaVersion: "1.1"` are still readable; the first `_manifest.update_stage` call rewrites them as `1.2`.

New fields on the `concept` stage:

- `approved: bool` — set by `scripts/approve_concept.py`. Treated as `false` when absent.
- `approvedAt: ISO-8601 string | null`
- `approvedBy: "user" | null`
- `failureKind: "moderation_blocked" | "api_error" | "user_error" | "timeout"` — set when `status == failed`.

New fields on the `engine` stage:

- `importCacheBuilt: bool` — `true` when `/3d-pipeline:godot-import` ran `godot --headless --import` successfully.
- `godotBin: string | null` — path to the Godot binary used (no secrets).

## Migrating from 0.1.x

Manifests created by 0.1.x have `schemaVersion: "1.1"` and no `concept.approved` field. After upgrading to 0.2.0:

- In-progress assets where `concept.status == done` will be **blocked at the next mesh attempt** with the new approval-gate error. Run `/3d-pipeline:approve <slug>` once to unblock; this also lazy-migrates the manifest to schema 1.2.
- New assets initialized with 0.2.0 use schema 1.2 from the start and require explicit approval before mesh.
- No mass migration is needed; the rewrite happens on the next `update_stage` call for each asset.

## Dry-Run Mode

Set this environment variable to skip all API calls:

```bash
PIPELINE_DRY_RUN=1
```

In dry-run mode, the Stage 1 concept script writes placeholder PNGs instead of calling OpenAI.

Dry-run mode is intended for installation checks, command testing, and demos without API spend.

Fixtures for later stages are planned for later chunks.

## Cost Expectation

Costs depend on provider pricing, selected quality settings, output size, retries, and review loop iterations.

### Measured cost: prop run (no rig, no animate)

Measured on 2026-05-10 with a static prop (`throne-of-swords`, `prop` asset type) running concept → mesh → import → review (1 iteration, approved).

| Stage | Vendor | Cost |
| --- | --- | --- |
| Concept (4 PNGs, 1 retry after moderation) | OpenAI `gpt-image-2` | ~USD 0.38 |
| Mesh (rapid mode) | Replicate `hunyuan-3d-3.1` | ~USD 0.16 |
| Import + review | local (Godot) | USD 0 |
| **Total** | | **~USD 0.54** |

A clean prop run without retries is roughly **USD 0.30-0.40** total. The concept retry above was caused by OpenAI moderation rejecting violent prompt language; a single successful concept pass typically costs ~USD 0.19.

### Estimated cost: humanoid full run

A humanoid full run that exercises every stage (concept + mesh + auto-rig + auto-animate + import + review) is expected to cost about USD 0.80-2.50 across OpenAI, Replicate, and Meshy. This is an estimate based on vendor list pricing and is not yet measured in this repo.

Always check current vendor pricing before running a non-dry pipeline.

The `/3d-pipeline:run-pipeline` command shows a cost preamble before making paid API calls.

## Roadmap

v0.1.0 is scoped to the Godot-first pipeline.

Planned later work includes:

- Claude Code commands for the remaining pipeline stages.
- Skills for stage routing and review criteria.
- Python scripts for the remaining vendor API calls and manifest management.
- Security hooks to block accidental API key writes inside this public repository.
- Godot 4 addon files for capture, setup, and review scenes.
- Dry-run fixtures for offline testing.
- Unity 6 support.
- Unreal 5 support.

Unity 6 and Unreal 5 are not included in v0.1.0.

## Troubleshooting

If installation fails, update the marketplace and retry the install command.

If commands are missing, confirm whether the requested stage has shipped yet.

If dependency installation fails, confirm that Python 3.10 or newer is active.

If API authentication fails in later chunks, confirm that the `.env` file is outside the repository and uses the exact variable names documented above.

If dry-run mode does not work, confirm that `PIPELINE_DRY_RUN=1` is set in the same shell that launches Claude Code.

If Godot import fails in later chunks, confirm that the target project contains `project.godot`.

Additional troubleshooting details will be added with the command and script chunks.

## License / Author

Author: KN

License: see the marketplace repository license.
