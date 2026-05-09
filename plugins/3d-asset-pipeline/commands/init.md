---
name: init
description: Initialize a 3D asset pipeline manifest before running concept, mesh, rig, animation, import, or review stages.
argument-hint: "<asset-name> <description> [--type humanoid|quadruped|prop]"
allowed-tools: Read, Write, Bash
---

# 3D Pipeline Init Command

Create `3d-pipeline-output/<slug>/pipeline.json` for a new asset.

## Usage

```text
/3d-pipeline:init <asset-name> <description> [--type humanoid|quadruped|prop]
```

## Workflow

1. Parse the asset name, description, and type. Default type is `humanoid` when omitted.
2. Create a slug with the same rules as `scripts/_common.py`.
3. Initialize the manifest through `scripts/_manifest.py` from Python:

```bash
python -c "import sys; sys.path.insert(0, r'${CLAUDE_PLUGIN_ROOT}'); from scripts import _common, _manifest; name='<asset-name>'; slug=_common.slugify(name); _manifest.init(slug, name, '<description>', '<asset-type>'); print(slug)"
```

4. Tell the user the slug and the manifest path.

## Manifest Result

The manifest starts at schema version `1.1`, marks every stage as `pending`, and marks `rig` and `animate` as `skipped` when `assetType` is `prop`.
