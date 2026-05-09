# Meshy v5 Mesh Fallback

## Role In The Pipeline

Meshy v5 is the alternate Stage 2 vendor. Use it when the user requests Meshy, when a Meshy plan is already preferred, or when the pipeline needs both GLB and FBX directly from mesh generation.

## Vendor And Credential

- Vendor tag in `pipeline.json`: `meshy:v5`
- Required credential: `MESHY_API_KEY`
- Credential location: `~/.claude/3d-pipeline/.env`
- Stage mode recorded by this chunk: `image-to-3d`

## When To Use Meshy

Use Meshy when:

- The user passes `--vendor meshy`.
- Hunyuan fails or returns unusable output.
- The next stage needs FBX immediately.
- The user wants to stay inside a Meshy account or plan.
- A fallback is needed but Tripo is not appropriate.

Avoid Meshy as the default only because Hunyuan is the selected first route for this plugin.

## Endpoint

Use the image-to-3D endpoint:

```text
POST https://api.meshy.ai/openapi/v1/image-to-3d
GET  https://api.meshy.ai/openapi/v1/image-to-3d/<task_id>
```

Authenticate with:

```text
Authorization: Bearer <MESHY_API_KEY>
```

Never log or write the token.

## Image-To-3D Versus Text-To-3D

This chunk uses image-to-3D because Stage 1 already produced a canonical concept image. Text-to-3D remains a possible future route for assets without concept art, but it should not bypass the manifest precondition in the current pipeline.

Build a base64 data URI from the canonical concept image and send it as the image input. Record user guidance such as target polygon count, PBR preference, seed, or texture prompt when supported by the script.

## Polling

After the POST response, extract the task id from `result`, `task_id`, or `id`. Poll every five seconds for up to 600 seconds.

Terminal statuses:

- `SUCCEEDED`: download model files and mark mesh done.
- `FAILED`: mark mesh failed.

Store errors as categories such as `meshy_api_failed` or `meshy_timeout`.

## Model URLs

On success, read the `model_urls` object. The expected outputs are:

- GLB URL
- FBX URL

Write:

```text
3d-pipeline-output/<slug>/mesh/<slug>.glb
3d-pipeline-output/<slug>/mesh/<slug>.fbx
```

Record:

```json
"files": {
  "glb": "mesh/<slug>.glb",
  "fbx": "mesh/<slug>.fbx"
}
```

## Dry-Run Behavior

When `PIPELINE_DRY_RUN=1`, skip the API, copy both mesh fixtures, set `taskId` and `predictionId` to null, set `dryRun` to true, and mark the mesh stage done.
