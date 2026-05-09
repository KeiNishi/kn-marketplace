---
name: concept-art-generation
description: Use this skill when generating Stage 1 concept art for the 3d-asset-pipeline, writing multi-angle prompts, selecting a canonical concept image, or updating the concept stage in pipeline.json.
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

# Concept Art Generation

Generate a consistent four-view concept set for a 3D game asset, then choose one canonical image for downstream mesh generation and review.

## Preconditions

- `3d-pipeline-output/<slug>/pipeline.json` exists.
- `pipeline.json` includes `name`, `description`, and `assetType`.
- `OPENAI_API_KEY` is present in `~/.claude/3d-pipeline/.env`, unless `PIPELINE_DRY_RUN=1`.

## Workflow

1. Read the manifest and summarize the asset description.
2. Build one shared style anchor, then append the angle clause for each view.
3. Run `scripts/concept_openai.py <slug> --defer-canonical` when the user should choose the canonical view.
4. Present the four generated paths and ask which view should be canonical.
5. Run `scripts/concept_openai.py <slug> --select-canonical <angle>`.
6. Verify `stages.concept.status` is `done`.

## Prompt Rules

- Keep all prompts in English.
- Use identical style, lighting, color, and material language across angles.
- Request a plain background and no text labels.
- Favor production concept art with readable silhouettes over dramatic composition.
- Mention the intended asset type so humanoids, quadrupeds, and props receive suitable posing.

## References

- `references/gpt-image-2-prompts.md`
- `references/multi-angle-spec.md`
