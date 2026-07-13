---
name: concept-art-generation
description: This skill should be used when the user asks to "generate concept art", "create concept images", "pick the canonical concept", or runs Stage 1 of the 3d-asset-pipeline. It covers writing multi-angle prompts, selecting a canonical concept image, driving the concept approval gate, recovering from moderation blocks, and updating the concept stage in pipeline.json. Also triggers on "/3d-pipeline:concept" and "/3d-pipeline:approve" commands.
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

# Concept Art Generation

Generate a consistent four-view concept set for a 3D game asset, then choose one canonical image for downstream mesh generation and review.

## Preconditions

- `3d-pipeline-output/<slug>/pipeline.json` exists.
- `pipeline.json` includes `name`, `description`, and `assetType`.
- A working image-generation backend is available, unless `PIPELINE_DRY_RUN=1`: either an active Codex CLI ChatGPT subscription (`codex` backend) or `OPENAI_API_KEY` present in `~/.claude/3d-pipeline/.env` (`openai` backend). See Backend Selection below.

## Workflow

Script paths below are relative to the plugin root (`${CLAUDE_PLUGIN_ROOT}` in Claude Code; in other agents, locate the installed plugin directory first and prefix script paths with it). Run them with `python3` from the workspace that contains `3d-pipeline-output/` (on Windows, use `py -3` if `python3` is not available).

1. Read the manifest and summarize the asset description.
2. Build one shared style anchor, then append the angle clause for each view.
3. Run `python3 scripts/concept_openai.py <slug> --defer-canonical` when the user should choose the canonical view.
4. Present the four generated paths and ask which view should be canonical.
5. Run `python3 scripts/concept_openai.py <slug> --select-canonical <angle>`.
6. Verify `stages.concept.status` is `done`.
7. Drive the approval gate (see below) before mesh generation can proceed.

## Approval Gate

Stage 2 mesh scripts refuse to run while `stages.concept.approved` is not `true`. The gate is mechanical, enforced inside the mesh preflight.

After the canonical is selected:

1. Display the four angle PNGs and `concept/canonical.png` to the user multimodally.
2. Compare against `pipeline.json.description`.
3. Ask the user to choose one of: **Approve**, **Change canonical**, **Re-roll with new description**, **Stop** (use the AskUserQuestion tool if available; otherwise ask in a plain message and wait for the reply).
4. On approve, run `python3 scripts/approve_concept.py <slug> --approve`.
5. On change canonical, run `python3 scripts/concept_openai.py <slug> --select-canonical <angle>` then approve.
6. On re-roll, run `python3 scripts/concept_openai.py <slug> --description "<new text>"` and loop back to step 1.
7. On stop, end and remind the user that `/3d-pipeline:approve <slug>` can be run later to unblock mesh.

## Backend Selection

`scripts/concept_openai.py` supports two image-generation backends: `codex` (Codex CLI's built-in `gpt-image-2` tool, covered by a ChatGPT subscription, no API key) and `openai` (the existing Images API, pay-per-use, unchanged behavior). Precedence: `--backend {auto,codex,openai}` > `PIPELINE_CONCEPT_BACKEND` env var > auto detection (codex CLI on `PATH` and an active ChatGPT subscription -> codex, else openai, silently -- identical to prior behavior). Forcing `--backend codex` when the CLI is missing or the subscription is inactive is a user error and fails the stage. `--model` / `PIPELINE_OPENAI_IMAGE_MODEL` only apply to the openai backend. `PIPELINE_DRY_RUN=1` is unaffected -- no backend detection runs, and vendor is always recorded as `openai:<model>`. See `references/codex-backend.md` for full detail.

## Moderation Recovery

When `_request_image` raises `ModerationBlocked`, the manifest stage records `failureKind: "moderation_blocked"` alongside `error` and `failedAt`. Surface a friendly retry prompt to the user and ask for softer description text. Do not auto-rewrite the prompt. Re-run with `--description "<new text>"`, which resets the stage to `pending` and regenerates.

## Codex Backend Recovery

When the codex backend fails at generation time, there is no automatic fallback to the openai backend -- this is deliberate, to avoid surprise charges. Two failure kinds:

- `failureKind: "codex_usage_limit"` -- the ChatGPT subscription's usage limit is exhausted. Tell the user to wait for the reset time shown in `error`, buy more usage, or re-run with `--backend openai`.
- `failureKind: "codex_error"` -- any other codex failure (tool error, missing/invalid PNG). Inspect `error` in `pipeline.json`, retry, or re-run with `--backend openai`.

See `references/codex-backend.md` for detection rules, precedence, and manifest fields.

## Prompt Rules

- Keep all prompts in English.
- Use identical style, lighting, color, and material language across angles.
- Request a plain background and no text labels.
- Favor production concept art with readable silhouettes over dramatic composition.
- Mention the intended asset type so humanoids, quadrupeds, and props receive suitable posing.

## References

- `references/gpt-image-2-prompts.md`
- `references/multi-angle-spec.md`
- `references/codex-backend.md`
