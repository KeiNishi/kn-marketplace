# Multi-Angle Spec

Generate exactly four concept views.

## Angles

- `front`: front view, full body or full object visible, neutral pose, facing camera.
- `three-quarter`: three-quarter view from camera-left, slight downward camera tilt, neutral pose.
- `side`: left side view, full silhouette visible, neutral pose.
- `back`: back view, full body or full object visible, neutral pose.

## Output Files

Write PNG files under `3d-pipeline-output/<slug>/concept/`:

- `front.png`
- `three-quarter.png`
- `side.png`
- `back.png`
- `canonical.png`

## Canonical Selection

The canonical image should be the clearest view for mesh generation. Prefer:

1. Strong silhouette.
2. Minimal occlusion.
3. Full asset visible.
4. Colors and materials matching the source description.
5. Pose suitable for downstream mesh, rig, and review stages.

When there is no user preference, select `front`.
