# Hunyuan 3D 3.1 Through Replicate

## Role In The Pipeline

Hunyuan 3D 3.1 is the default Stage 2 mesh generator for the plugin. It receives the canonical concept image plus the manifest description and returns a textured GLB suitable for Godot import or later rigging.

## Model Identifier

- Replicate model: `tencent/hunyuan-3d-3.1`
- Vendor tag in `pipeline.json`: `replicate:hunyuan-3d-3.1`
- Required credential: `REPLICATE_API_TOKEN`
- Credential location: `~/.claude/3d-pipeline/.env`

## Input Shape

The script uses the Replicate Python SDK:

```python
client = replicate.Client(api_token=token)
prediction = client.predictions.create(
    model="tencent/hunyuan-3d-3.1",
    input={
        "image": open(path, "rb"),
        "prompt": description,
        "edition": "Pro" if mode == "pro" else "Rapid",
    },
)
```

Use the canonical concept image from `stages.concept.files.canonical`. Use the manifest description as the prompt and append short style guidance only when the user provides it.

## Editions

- `Rapid` is the default.
- `Pro` is selected with `--mode pro`.
- Rapid is intended for faster and cheaper iteration.
- Pro is intended for a higher quality pass after the design is stable.

Keep the edition value in the manifest so later review can explain quality differences between runs.

## Polling

Poll the prediction every five seconds for up to 600 seconds. Treat these statuses as terminal:

- `succeeded`: download output and mark mesh done.
- `failed`: mark mesh failed.
- `canceled`: mark mesh failed.

Do not expose the API token in polling errors. Store a concise category such as `replicate_api_failed` or `replicate_timeout`.

## Output

The expected production output is a GLB URL in `prediction.output`. The output shape can vary by SDK and model version, so read a string URL, a list containing a URL, or a dictionary containing a GLB/model URL.

Download the GLB with a bounded HTTP request and write:

```text
3d-pipeline-output/<slug>/mesh/<slug>.glb
```

Record the path as:

```json
"files": {"glb": "mesh/<slug>.glb"}
```

Do not write `files.fbx` for Hunyuan in this chunk. Later rigging stages can upload the GLB directly when supported.

## PBR Notes

Hunyuan 3D 3.1 is selected because its textured GLB output is expected to include PBR-friendly material data. The mesh stage records the user's PBR preference, but this script does not post-process materials.

## Typical Timing

Expect Rapid runs to take a few minutes and Pro runs to take longer. Keep the timeout at 600 seconds so a single command remains bounded inside Claude Code.

## Dry-Run Behavior

When `PIPELINE_DRY_RUN=1`, skip Replicate entirely. Copy only `scripts/fixtures/mesh/dryrun.glb` to the mesh folder, set `predictionId` to null, set `dryRun` to true, and mark the mesh stage done.
