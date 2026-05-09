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
7. Drive the approval gate (see below) before mesh generation can proceed.

## Approval Gate

Stage 2 mesh scripts refuse to run while `stages.concept.approved` is not `true`. The gate is mechanical, enforced inside the mesh preflight.

After the canonical is selected:

1. Display the four angle PNGs and `concept/canonical.png` to the user multimodally.
2. Compare against `pipeline.json.description`.
3. Use `AskUserQuestion` with options: **Approve**, **Change canonical**, **Re-roll with new description**, **Stop**.
4. On approve, run `scripts/approve_concept.py <slug> --approve`.
5. On change canonical, run `scripts/concept_openai.py <slug> --select-canonical <angle>` then approve.
6. On re-roll, run `scripts/concept_openai.py <slug> --description "<new text>"` and loop back to step 1.
7. On stop, end and remind the user that `/3d-pipeline:approve <slug>` can be run later to unblock mesh.

## Moderation Recovery

When `_request_image` raises `ModerationBlocked`, the manifest stage records `failureKind: "moderation_blocked"` alongside `error` and `failedAt`. Surface a friendly retry prompt to the user and ask for softer description text. Do not auto-rewrite the prompt. Re-run with `--description "<new text>"`, which resets the stage to `pending` and regenerates.

## Prompt Rules

- Keep all prompts in English.
- Use identical style, lighting, color, and material language across angles.
- Request a plain background and no text labels.
- Favor production concept art with readable silhouettes over dramatic composition.
- Mention the intended asset type so humanoids, quadrupeds, and props receive suitable posing.

## References

- `references/gpt-image-2-prompts.md`
- `references/multi-angle-spec.md`
