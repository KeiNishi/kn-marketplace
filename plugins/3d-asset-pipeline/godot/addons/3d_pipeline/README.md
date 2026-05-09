# 3D Pipeline Godot Addon

This addon supports Stage 6 of the 3D Asset Pipeline: in-engine screenshot capture and fix application for Godot 4.4+ projects.

## Files

- `capture.gd` loads `review_scene.tscn`, instances the imported asset into `AssetSlot`, renders the canonical camera set, and writes `screenshots.json`.
- `apply_fixes.gd` reads `fix-instructions.json`, persists `setup.json`, and updates import options in the asset `.import` file when requested.
- `review_scene.tscn` provides a neutral review scene with a 1m reference cube, ground plane, studio lighting, and four cameras.

## Capture

Run capture from a Godot project after the addon has been copied under `res://addons/3d_pipeline/`:

```bash
godot --path <project> --script res://addons/3d_pipeline/capture.gd -- --asset <slug> --source res://assets/characters/<slug>/<slug>.glb --output <absolute-output-dir>
```

Do not use `--headless`; Godot disables rendering in headless mode. The scripts minimize the normal window through `DisplayServer.WINDOW_MODE_MINIMIZED`.

## Fixes

Apply a fix file before the next capture:

```bash
godot --path <project> --script res://addons/3d_pipeline/apply_fixes.gd -- --asset <slug> --fixes <absolute-fix-instructions-json>
```

`apply_fixes.gd` writes `<review-dir>/setup.json`. The next `capture.gd` run reads that setup file and applies scale, rotation, material overrides, and default animation selection.
