# Manifest Schema

`pipeline.json` uses schema version `1.1`.

## Root Fields

- `schemaVersion`: Must be `1.1`.
- `slug`: Stable kebab-case asset id.
- `name`: Human-readable asset name.
- `description`: Source prompt for the asset.
- `assetType`: `humanoid`, `quadruped`, or `prop`.
- `createdAt`: UTC ISO timestamp.
- `updatedAt`: UTC ISO timestamp.
- `dryRun`: Boolean copied from `PIPELINE_DRY_RUN`.
- `stages`: Object containing `concept`, `mesh`, `rig`, `animate`, `engine`, and `review`.

## Concept Stage

```json
{
  "status": "done",
  "vendor": "openai:gpt-image-2",
  "endpoint": "https://api.openai.com/v1/images/generations",
  "requestIds": ["req_..."],
  "prompts": {
    "front": "...",
    "three-quarter": "...",
    "side": "...",
    "back": "..."
  },
  "references": ["optional-reference-note-or-path"],
  "files": {
    "front": "concept/front.png",
    "three-quarter": "concept/three-quarter.png",
    "side": "concept/side.png",
    "back": "concept/back.png",
    "canonical": "concept/canonical.png",
    "canonicalSource": "concept/front.png"
  },
  "canonicalAngle": "front",
  "dryRun": false,
  "startedAt": "2026-05-09T00:00:00Z",
  "completedAt": "2026-05-09T00:05:00Z"
}
```

The stage may remain `in_progress` after angle generation when canonical selection is deferred. It becomes `done` only after `concept/canonical.png` is written.

When Stage 1 uses the `codex` backend instead of `openai`, `vendor` is `"codex:gpt-image-2"`, `endpoint` is `"codex-cli"`, and `requestIds` is always `[]` (codex has no per-request API ids). See `skills/concept-art-generation/references/codex-backend.md`.

## Status Values

All stages use one of:

- `pending`
- `in_progress`
- `done`
- `failed`
- `skipped`
