# Humanoid Rig Reference

Use the `humanoid` template for biped characters that should receive a standard game-character skeleton.

## Template

- Template name: `humanoid`
- Expected source: Stage 2 GLB from `stages.mesh.files.glb`
- Expected output: Stage 3 FBX at `rigged/<slug>.fbx`
- Vendor: Meshy v5
- Stage field: `stages.rig.template`

## Suitable Assets

- Human characters
- Armored or clothed bipeds
- Stylized humanoids
- Robots with human-like proportions
- Monsters that clearly stand and move on two legs

Avoid this template for static props, vehicles, weapons, buildings, and environmental objects.

## Skeleton Expectations

Meshy may return a skeleton that follows common humanoid naming conventions. When it provides Mixamo-compatible naming, expect names in the general shape of:

- `Hips`
- `Spine`
- `Spine1`
- `Spine2`
- `Neck`
- `Head`
- `LeftArm`
- `LeftForeArm`
- `LeftHand`
- `RightArm`
- `RightForeArm`
- `RightHand`
- `LeftUpLeg`
- `LeftLeg`
- `LeftFoot`
- `RightUpLeg`
- `RightLeg`
- `RightFoot`

Do not require exact bone names in the script. Treat naming as an import-time compatibility concern for Blender, Godot, or retargeting tools.

## Mesh Preparation Notes

- Prefer neutral or A-pose silhouettes from concept and mesh stages.
- Keep limbs visible and separated from the torso.
- Avoid capes, skirts, or large shoulder pieces intersecting the body.
- Keep fingers simple unless high-detail hand animation is required.
- Check that the mesh is centered and upright before uploading.

## API Ambiguity Notes

Meshy rigging API examples may vary between multipart mesh upload and URL-based input. This chunk uses multipart upload because the pipeline owns the Stage 2 GLB locally and can submit it directly.

The script sends:

- Bearer authorization header
- GLB file as multipart `file`
- Rig template as request data

If Meshy changes field names, keep the manifest contract stable and update only the request construction and response extraction.

## Validation

- Confirm `stages.mesh.status == done`.
- Confirm `stages.mesh.files.glb` exists.
- Confirm the selected template is `humanoid`.
- Confirm the final FBX is written under `rigged/`.
- Confirm the rig stage records `vendor: meshy:v5`.
