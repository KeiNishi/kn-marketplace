---
name: concept
description: Generate Stage 1 multi-angle concept art for an existing 3D asset pipeline manifest.
argument-hint: "<slug> [--canonical front|three-quarter|side|back] [--defer-canonical] [--backend auto|codex|openai] [--model MODEL]"
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

# 3D Pipeline Concept Command

Generate concept images for an asset that already has `3d-pipeline-output/<slug>/pipeline.json`.

## Usage

```text
/3d-pipeline:concept <slug> [--canonical front|three-quarter|side|back] [--defer-canonical] [--backend auto|codex|openai] [--model MODEL]
```

## Workflow

1. Read `pipeline.json` for the slug and confirm the asset name, description, and asset type.
2. Run:

On Windows, use `py -3` if `python3` is not available.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/concept_openai.py" <slug> <args>
```

3. If `--defer-canonical` is used, inspect the generated PNG paths in `concept/`, ask the user which view should be canonical, then run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/concept_openai.py" <slug> --select-canonical <angle>
```

4. Confirm that `stages.concept.status` is `done` and that `concept/canonical.png` exists.

## Moderation Recovery

If the script exits with `failureKind: "moderation_blocked"` in the concept stage record, OpenAI's safety system rejected the prompt. Surface a friendly retry message to the user. Do not auto-soften the description; ask the user for a new description with less violent or sensitive language, then re-run the concept stage with that description:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/concept_openai.py" <slug> --description "<new description>"
```

`--description` overwrites the manifest description and resets the concept stage to `pending` before regenerating.

## Codex Backend Failures

If the script exits with `failureKind: "codex_usage_limit"` or `failureKind: "codex_error"` in the concept stage record, the codex image-generation backend was selected and failed at generation time; by design there is no automatic fallback to the pay-per-use openai backend. Map the failure kind to guidance:

- `codex_usage_limit` — the ChatGPT subscription's usage limit is exhausted. Tell the user to wait for the reset time shown in `error`, buy more usage credits, or re-run with `--backend openai`.
- `codex_error` — a different codex failure (tool error, no or invalid PNG produced). Show the user the `error` text from `pipeline.json`, then retry the same command or re-run with `--backend openai`.

## Approval Gate

After the concept stage reaches `status: done`, the mesh stage will refuse to run until concept is approved. Drive the approval interactively:

1. Display all four PNGs and the canonical multimodally:
   - `concept/front.png`
   - `concept/three-quarter.png`
   - `concept/side.png`
   - `concept/back.png`
   - `concept/canonical.png`
2. Compare against `pipeline.json.description`.
3. Use `AskUserQuestion` with options:
   - **Approve** — accept the canonical and unblock mesh generation.
   - **Change canonical** — select a different angle as canonical, then approve.
   - **Re-roll with new description** — supply softer or different prompt language and regenerate.
   - **Stop** — leave the concept un-approved; mesh remains blocked until `/3d-pipeline:approve <slug>` is run later.
4. Map answers to:
   - Approve → `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/approve_concept.py" <slug> --approve`
   - Change canonical → `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/concept_openai.py" <slug> --select-canonical <angle>` then approve
   - Re-roll → `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/concept_openai.py" <slug> --description "<new text>"` then loop back to step 1
   - Stop → end the command and print the location of `concept/`

The approval gate is enforced mechanically — `mesh_hunyuan.py`, `mesh_meshy.py`, and `mesh_tripo.py` all refuse to run when `stages.concept.approved` is not `true`.

## Notes

- Two backends are available: `codex` (Codex CLI's built-in `gpt-image-2` tool, uses an active ChatGPT subscription, no API key) and `openai` (the Images API, pay-per-use). Precedence: `--backend` > `PIPELINE_CONCEPT_BACKEND` env var (`codex`, `openai`, or `auto`) > auto detection (codex CLI on `PATH` and an active subscription -> codex, else openai).
- `OPENAI_API_KEY` (read only from `~/.claude/3d-pipeline/.env`) is required only when the `openai` backend is used. It is not needed when the `codex` backend is selected.
- Set `PIPELINE_DRY_RUN=1` to create placeholder PNGs without network calls or API spend; this is unchanged by the backend feature and always records `vendor: openai:<model>`.
- The planned default model is `gpt-image-2`; pass `--model` or set `PIPELINE_OPENAI_IMAGE_MODEL` if the account should use another GPT Image model. These only apply to the `openai` backend.
- Reference image paths may be recorded with `--reference`, but this command uses the Image Generations endpoint for text-to-image output.
