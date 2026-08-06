---
name: approve
description: Approve or reject the canonical concept art for a 3D asset pipeline run. Mesh generation refuses to run until the concept is approved.
argument-hint: "<slug> [--reject] [--canonical front|three-quarter|side|back]"
---

# 3D Pipeline Approve Command

Record the human approval (or rejection) of Stage 1 concept art so Stage 2 mesh generation can proceed.

## Usage

```text
/3d-pipeline:approve <slug>                       # approve (default)
/3d-pipeline:approve <slug> --reject              # withdraw approval
/3d-pipeline:approve <slug> --canonical <angle>   # change canonical, then approve
```

## Workflow

1. Read `3d-pipeline-output/<slug>/pipeline.json` and confirm `stages.concept.status` is `done`.
2. Display `concept/canonical.png` (and the four angle PNGs if helpful) so the user can verify the asset before approving.
3. Run (on Windows, use `py -3` if `python3` is not available):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/approve_concept.py" <slug> [--reject] [--canonical <angle>]
```

4. Print the concept stage block from the manifest (`status`, `canonicalAngle`, `approved`, `approvedAt`, `approvedBy`).

## Notes

- Approval sets `stages.concept.approved = true`, `approvedAt = <iso>`, `approvedBy = "user"`.
- Rejection clears the approval flag. Re-run `/3d-pipeline:concept <slug>` (optionally with `--description` for a new prompt) before approving again.
- `--canonical` re-selects which angle is the canonical view. The script delegates to `concept_openai.select_canonical` and then approves in the same call.
- The mesh scripts (`mesh_hunyuan.py`, `mesh_meshy.py`, `mesh_tripo.py`) refuse to run when `concept.approved` is not `true`. The gate is mechanical, not advisory.
- This command does not call any paid APIs.
