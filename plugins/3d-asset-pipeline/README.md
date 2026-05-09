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
MESHY_API_KEY=msy_...
# Optional: TRIPO_API_KEY=tsk_...
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

Required keys for the planned full pipeline:

- `OPENAI_API_KEY`
- `REPLICATE_API_TOKEN`
- `MESHY_API_KEY`

Optional key:

- `TRIPO_API_KEY`

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
/3d-pipeline:doctor
```

The planned full pipeline command is:

```text
/3d-pipeline:run <name> <description>
```

Example:

```text
/3d-pipeline:run knight-hero "Stoic plate armor knight with a longsword"
```

The concept stage can be run after a manifest is initialized:

```text
/3d-pipeline:concept <slug> --defer-canonical
```

The remaining stage commands are planned for later chunks.

They are documented here so users can understand the intended workflow before the command files are added.

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

A typical humanoid full run is expected to cost about USD 0.50-2.00 across OpenAI, Replicate, and Meshy.

This is only an estimate.

Always check current vendor pricing before running a non-dry pipeline.

The planned run command will show a cost preamble before making paid API calls.

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
