# Tripo3D Quadruped Fallback

## Role In The Pipeline

Tripo3D is the fallback route for difficult quadruped meshes. Use it after the default route produces weak four-legged anatomy, broken limb separation, or topology that is unsuitable for rigging.

## Vendor And Credential

- Vendor tag in `pipeline.json`: `tripo:v2`
- Credential: `TRIPO_API_KEY`
- Credential location: `~/.claude/3d-pipeline/.env`

`TRIPO_API_KEY` is optional for the plugin as a whole. It is required only when invoking the Tripo script. If the key is missing, exit with a user-fixable error and explain that Tripo is an optional fallback.

## When To Use Tripo

Use Tripo when:

- The user passes `--vendor tripo`.
- The asset type is `quadruped` and another vendor produced unusable anatomy.
- A creature has four legs, a tail, or a body plan that needs a more creature-oriented retry.
- The user accepts the optional credential requirement.

Do not use Tripo automatically for humanoids or props unless the user requests it.

## Endpoint

Use the v2 task endpoint:

```text
POST https://api.tripo3d.ai/v2/openapi/task
GET  https://api.tripo3d.ai/v2/openapi/task/<task_id>
```

Authenticate with:

```text
Authorization: Bearer <TRIPO_API_KEY>
```

Send the canonical concept image as a base64 data URI. Include short style guidance only when provided by the user.

## Polling

After the POST response, extract the task id from the top-level payload or a nested `data` object. Poll every five seconds for up to 600 seconds.

Terminal statuses:

- `success`: download output and mark mesh done.
- `failed`: mark mesh failed.

Store errors as `tripo_api_failed` or `tripo_timeout`. Keep messages short and remove tokens from any upstream text.

## Output

The primary output is expected at `output.model` or an equivalent model URL field in the task response. Download it to:

```text
3d-pipeline-output/<slug>/mesh/<slug>.glb
```

Record:

```json
"files": {"glb": "mesh/<slug>.glb"}
```

If an FBX URL is present, download it on a best-effort basis and add `files.fbx`. Do not fail an otherwise successful Tripo GLB run only because the optional FBX is absent.

## Review After Generation

Open the GLB in Godot or Blender before rigging. Check leg separation, foot placement, body orientation, and whether the creature faces the expected front direction. If topology is visibly poor, record the issue in the manifest and rerun with adjusted style guidance or a different vendor.

## Recovery Notes

If Tripo returns a usable GLB but no FBX, continue with the GLB path and let the rigging stage decide whether direct GLB upload is acceptable.

If the task fails quickly, check whether the data URI was built from the canonical concept file and not from a missing or empty path.

If the task remains in progress until timeout, keep the task id in the manifest error context only when it is already present and safe to store.

If the quadruped has merged legs, rerun with style guidance that asks for clear limb separation and a neutral side-readable pose.

## Dry-Run Behavior

When `PIPELINE_DRY_RUN=1`, skip Tripo and copy both dry-run mesh fixtures. Record `taskId` and `predictionId` as null, set `dryRun` to true, and mark the mesh stage done.
