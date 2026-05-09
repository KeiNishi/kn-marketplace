---
name: concept
description: Generate Stage 1 multi-angle concept art for an existing 3D asset pipeline manifest.
argument-hint: "<slug> [--canonical front|three-quarter|side|back] [--defer-canonical] [--model MODEL]"
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

# 3D Pipeline Concept Command

Generate concept images for an asset that already has `3d-pipeline-output/<slug>/pipeline.json`.

## Usage

```text
/3d-pipeline:concept <slug> [--canonical front|three-quarter|side|back] [--defer-canonical] [--model MODEL]
```

## Workflow

1. Read `pipeline.json` for the slug and confirm the asset name, description, and asset type.
2. Run:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/concept_openai.py" <slug> <args>
```

3. If `--defer-canonical` is used, inspect the generated PNG paths in `concept/`, ask the user which view should be canonical, then run:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/concept_openai.py" <slug> --select-canonical <angle>
```

4. Confirm that `stages.concept.status` is `done` and that `concept/canonical.png` exists.

## Notes

- The script reads `OPENAI_API_KEY` only from `~/.claude/3d-pipeline/.env`.
- Set `PIPELINE_DRY_RUN=1` to create placeholder PNGs without network calls or API spend.
- The planned default model is `gpt-image-2`; pass `--model` or set `PIPELINE_OPENAI_IMAGE_MODEL` if the account should use another GPT Image model.
- Reference image paths may be recorded with `--reference`, but this command uses the Image Generations endpoint for text-to-image output.
