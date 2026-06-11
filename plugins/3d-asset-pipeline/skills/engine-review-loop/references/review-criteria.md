# Review Criteria

## Contents

1. [Scale](#1-scale)
2. [Orientation](#2-orientation)
3. [Pivot and Ground Contact](#3-pivot-and-ground-contact)
4. [Materials](#4-materials)
5. [Animation](#5-animation)
6. [Topology Integrity](#6-topology-integrity)
7. [Match to Description and Concept](#7-match-to-description-and-concept)

Use these criteria for every Stage 6 screenshot review. Inspect the asset in all views before writing a verdict. Prefer visible evidence over assumptions.

## 1. Scale

What to look for:

- Compare the asset against the 1m reference cube near the origin.
- Estimate whether the asset size matches its type: character, creature, prop, pickup, or environment piece.
- Check whether the asset is so large that it clips out of frame or so small that details are unreadable.

Failure modes:

- Character is below knee height relative to the cube.
- Small prop is taller than a humanoid unless the description says so.
- Asset fills the frame and hides the reference cube.
- Scale differs wildly between views because root transforms are incorrect.

Severity:

- Blocker: scale makes the asset unusable in a game scene.
- Minor: scale is plausible but needs tuning for a specific game.

Inspection prompt:

```text
Is the asset's visible height and footprint plausible when compared to the 1m cube?
```

## 2. Orientation

What to look for:

- The front view should show the intended front of the asset.
- The side view should show a clear profile.
- The back view should show rear detail.
- The asset should not be upside down, sideways, or mirrored in an obvious way.

Failure modes:

- The front camera sees the back of the asset.
- The asset lies on its side.
- A character faces 90 degrees away from the front camera.
- Quadruped head and tail orientation is reversed.

Severity:

- Blocker: front-facing direction is wrong or asset is not upright.
- Minor: small yaw offset that still reads correctly.

Inspection prompt:

```text
Does CamFront show the intended front silhouette without needing a camera workaround?
```

## 3. Pivot and Ground Contact

What to look for:

- Feet, wheels, base, or bottom surface should rest on the ground plane.
- The pivot should be near the origin for predictable placement.
- The asset should not float, sink, or rotate around a distant point.

Failure modes:

- Feet are below the ground plane.
- Prop floats above the plane.
- Root origin appears far outside the mesh.
- Animation moves the root away from the review position.

Severity:

- Blocker: placement is unusable or animation drifts away.
- Minor: slight vertical offset that can be corrected in setup.

Inspection prompt:

```text
Can the asset be placed at origin in a level without manual offset cleanup?
```

## 4. Materials

What to look for:

- Materials should use believable colors or textures from the generated asset.
- No magenta fallback, checker fallback, missing texture slots, or all-black unlit appearance.
- PBR response should be visible under the three-point lighting.

Failure modes:

- Entire asset is magenta.
- Important surfaces are flat grey when concept shows clear colors.
- Texture orientation is broken.
- Transparent surfaces render opaque when they should not.

Severity:

- Blocker: missing materials or fallback material dominates the asset.
- Minor: roughness, metallic, or color needs polish but identity is readable.

Inspection prompt:

```text
Do the screenshots show real material assignment instead of fallback colors?
```

## 5. Animation

What to look for:

- `animation-mid.png` should differ from the static three-quarter pose for rigged or animated assets.
- Motion should preserve proportions and avoid extreme mesh collapse.
- Props with no animation may show the same pose and should not fail this criterion.

Failure modes:

- Animated character has no visible motion.
- Mesh deforms into spikes or folded limbs.
- Root motion moves the asset out of the camera frame.
- Wrong clip plays, such as an attack when idle was requested.

Severity:

- Blocker: animated asset has no usable visible animation or severe deformation.
- Minor: motion exists but selected clip is not ideal.

Inspection prompt:

```text
Does the mid-animation capture prove that the imported asset can animate in Godot?
```

## 6. Topology Integrity

What to look for:

- Inspect all angles for missing limbs, holes, inverted normals, broken seams, and disconnected shells.
- Check silhouette continuity from front, side, and back.
- Look for camera-dependent disappearance that suggests normals or culling problems.

Failure modes:

- Large body sections are missing.
- Limbs are detached or fused incorrectly.
- Normals are inverted and surfaces disappear.
- Mesh has obvious holes that contradict the concept.

Severity:

- Blocker: geometry defects break the asset identity or usability.
- Minor: small artifact away from gameplay focus.

Inspection prompt:

```text
Does the asset remain structurally coherent from every canonical camera?
```

## 7. Match to Description and Concept

What to look for:

- Compare silhouette, color palette, key accessories, and broad proportions to `pipeline.json.description`.
- Compare against `concept/canonical.png` when available.
- Prioritize major identity markers over tiny details.

Failure modes:

- Humanoid requested but output is a generic prop.
- Main weapon, creature features, or iconic accessory is missing.
- Color palette is unrelated to the concept.
- The generated mesh is a different asset category.

Severity:

- Blocker: asset identity does not match the requested subject.
- Minor: secondary details differ but the main asset is recognizable.

Inspection prompt:

```text
Would a game developer recognize this as the asset described in the manifest and concept?
```
