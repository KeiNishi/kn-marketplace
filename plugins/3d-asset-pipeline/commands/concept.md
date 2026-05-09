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

## Moderation Recovery

If the script exits with `failureKind: "moderation_blocked"` in the concept stage record, OpenAI's safety system rejected the prompt. Surface a friendly retry message to the user. Do not auto-soften the description; ask the user for a new description with less violent or sensitive language, then re-run the concept stage with that description:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/concept_openai.py" <slug> --description "<new description>"
```

`--description` overwrites the manifest description and resets the concept stage to `pending` before regenerating.

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
   - Approve → `python "${CLAUDE_PLUGIN_ROOT}/scripts/approve_concept.py" <slug> --approve`
   - Change canonical → `python "${CLAUDE_PLUGIN_ROOT}/scripts/concept_openai.py" <slug> --select-canonical <angle>` then approve
   - Re-roll → `python "${CLAUDE_PLUGIN_ROOT}/scripts/concept_openai.py" <slug> --description "<new text>"` then loop back to step 1
   - Stop → end the command and print the location of `concept/`

The approval gate is enforced mechanically — `mesh_hunyuan.py`, `mesh_meshy.py`, and `mesh_tripo.py` all refuse to run when `stages.concept.approved` is not `true`.

## Notes

- The script reads `OPENAI_API_KEY` only from `~/.claude/3d-pipeline/.env`.
- Set `PIPELINE_DRY_RUN=1` to create placeholder PNGs without network calls or API spend.
- The planned default model is `gpt-image-2`; pass `--model` or set `PIPELINE_OPENAI_IMAGE_MODEL` if the account should use another GPT Image model.
- Reference image paths may be recorded with `--reference`, but this command uses the Image Generations endpoint for text-to-image output.
