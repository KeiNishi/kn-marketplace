# Godot Capture Protocol

Stage 6 uses a standard Godot 4.4+ scene and two tool scripts:

- `capture.gd` renders screenshots.
- `apply_fixes.gd` persists setup changes and import option edits.

## Capture Invocation

Run:

```bash
godot --path <project> --script res://addons/3d_pipeline/capture.gd -- --asset <slug> --source <res-path> --output <absolute-output-dir>
```

Supported arguments:

- `--asset <slug>`: asset slug used for logs and screenshot metadata.
- `--source <res-path>`: `res://` path to the imported Godot asset or wrapper scene.
- `--output <abs-path>`: destination directory for PNG files and `screenshots.json`.
- `--anim-frame 0.5`: normalized animation sample position for `animation-mid.png`.
- `--scale 1.0`: fallback scale when no `setup.json` exists.
- `--rotation-y 0.0`: fallback Y rotation in degrees when no `setup.json` exists.

`capture.gd` also reads `<review-dir>/setup.json`, where `<review-dir>` is the parent of `iter-<N>`.

## Outputs

Each capture writes:

```text
front.png
three-quarter.png
side.png
back.png
animation-mid.png
screenshots.json
```

The four static views are always expected. `animation-mid.png` is captured from the three-quarter camera after seeking the first or configured animation. Dry-run mode uses fixture PNG files with the same names.

## Camera Positions

The review scene uses a 3m radius and 1.5m camera height.

| Camera | Position | Purpose |
|---|---|---|
| `CamFront` | `(0, 1.5, 3)` | Intended front-facing view |
| `CamTQ` | `(2.121, 1.5, 2.121)` | 45 degree three-quarter view |
| `CamSide` | `(3, 1.5, 0)` | Right-side profile |
| `CamBack` | `(0, 1.5, -3)` | Rear view |

All cameras look at the origin. Field of view is 45 degrees. The asset is added under `AssetSlot` at the review scene origin.

## Reference Cube

`RefCube` is a 1m cube placed beside the asset. Use it for scale evaluation, not as an object to match exactly. Characters, creatures, props, and environment pieces can all be larger or smaller than the cube when the description requires it.

## Lighting and Background

The scene uses:

- Neutral grey world background.
- 4m x 4m grey ground plane.
- Three directional lights: key, fill, and rim.

This lighting is intentionally plain. It should reveal material assignment, silhouette, and geometry without stylized effects.

## No Headless Mode

Do not pass `--headless` for capture. Godot headless mode disables rendering, which can produce blank or invalid viewport images. The capture script opens a normal Godot process and immediately minimizes the window with `DisplayServer.WINDOW_MODE_MINIMIZED`.

## Timeout

The Python driver uses a 120 second timeout for each Godot subprocess. Treat timeout as an execution failure, not as a review verdict. Common causes include:

- Godot executable not found or blocked.
- Project opens slowly because import cache is rebuilding.
- Asset import hangs.
- Addon files are missing from `res://addons/3d_pipeline/`.

## Apply Fixes Invocation

Run:

```bash
godot --path <project> --script res://addons/3d_pipeline/apply_fixes.gd -- --fixes <fix-instructions.json> --asset <slug>
```

`apply_fixes.gd` writes `<review-dir>/setup.json`. It can also edit the asset `.import` file for import options and prints a reimport instruction when those options change.
