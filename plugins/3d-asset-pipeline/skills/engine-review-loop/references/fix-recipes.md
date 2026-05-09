# Fix Recipes

Stage 6 fixes are stored in `fix-instructions.json` next to the screenshots for the current iteration.

## fix-instructions.json Schema

```json
{
  "scale": 1.5,
  "rotation_y_degrees": 180.0,
  "material_overrides": {
    "slot_0": "res://assets/characters/hero/textures/albedo.png"
  },
  "default_animation": "idle",
  "import_options": {
    "materials/location": 1
  },
  "notes": "Short explanation of why these fixes were selected."
}
```

All fields are optional. Include only fields that address observed issues.

Field meanings:

- `scale`: global asset scale applied under `AssetSlot`.
- `rotation_y_degrees`: global Y-axis rotation in degrees.
- `material_overrides`: dictionary keyed by material slot, such as `slot_0`.
- `default_animation`: animation clip name to sample for `animation-mid.png`.
- `import_options`: Godot `.import` `[params]` key-value edits.
- `notes`: concise human-readable rationale.

## Recipe: Too Small

Symptoms:

- Asset is hard to inspect.
- Character is much shorter than the 1m reference cube when it should be human scale.
- Prop is too tiny for its described use.

Fix:

```json
{"scale": 1.5}
```

Use `scale * 1.5` for mild undersizing. Use `scale * 2.0` for severe undersizing. Avoid guessing exact meters unless the manifest gives dimensions.

Severity:

- Blocker when gameplay placement would be impossible.
- Minor when only presentation scale is off.

## Recipe: Too Large

Symptoms:

- Asset clips out of frame.
- Reference cube is hidden or dwarfed without description support.
- Camera cannot show the full silhouette.

Fix:

```json
{"scale": 0.5}
```

Use `0.75` for mild oversizing and `0.5` for severe oversizing. Reinspect all views after scaling.

## Recipe: Wrong Facing Direction

Symptoms:

- Front view shows the asset's back.
- Side view shows the front.
- Quadruped head points away from `CamFront`.

Fix:

```json
{"rotation_y_degrees": 180.0}
```

Use `90.0` or `-90.0` when the asset is sideways. Use `180.0` when it is backwards. Keep existing rotation in mind if `setup.json` already contains a value.

Severity:

- Blocker for characters, creatures, vehicles, and directional props.
- Minor only for rotationally symmetric props.

## Recipe: Floating or Sinking

Symptoms:

- Feet or base are not on the ground plane.
- The asset is visually offset from origin.

Fix:

Use a note when the current schema cannot express a vertical offset. Prefer rerunning Stage 5 import or wrapper creation if placement is consistently wrong. Do not misuse scale to hide a pivot problem.

Example:

```json
{
  "notes": "Pivot appears above the feet; requires wrapper scene vertical offset in a future fix schema."
}
```

Severity:

- Blocker when placement is unusable.
- Minor when the offset is slight.

## Recipe: Magenta or Missing Materials

Symptoms:

- Surfaces are magenta or checkerboard.
- Asset is flat grey despite textured concept art.
- One material slot is clearly missing.

Fix:

```json
{
  "material_overrides": {
    "slot_0": "res://assets/characters/hero/textures/albedo.png"
  },
  "import_options": {
    "materials/location": 1,
    "materials/storage": 0
  }
}
```

Use a texture path when known. Use a neutral HTML color only as a temporary visual review aid:

```json
{"material_overrides": {"slot_0": "#b8b8b8"}}
```

Severity:

- Blocker when fallback material dominates.
- Minor when a secondary material needs polish.

## Recipe: No Visible Animation

Symptoms:

- `animation-mid.png` matches the static three-quarter view for an animated asset.
- The selected clip is empty or wrong.

Fix:

```json
{"default_animation": "idle"}
```

Try `idle` first for review stability. Use `walk`, `run`, or another clip only when the manifest requested a specific motion and the clip exists.

Severity:

- Blocker for humanoid and quadruped assets with Stage 4 complete.
- Not an issue for static props.

## Recipe: Deformed Animation

Symptoms:

- Limbs collapse or stretch in `animation-mid.png`.
- Mesh explodes during animation.
- Root motion moves out of frame.

Fix:

Select a safer default animation if available:

```json
{"default_animation": "idle"}
```

If deformation remains visible, write a failing verdict and route back to rigging or animation rather than stacking transform fixes.

## Recipe: Import Options

Use `import_options` only for Godot importer settings that map directly to `.import` `[params]` keys.

Common keys:

- `animation/import`
- `meshes/ensure_tangents`
- `materials/location`
- `materials/storage`

Example:

```json
{
  "import_options": {
    "animation/import": true,
    "meshes/ensure_tangents": true
  }
}
```

After changing import options, recapture. If Godot does not pick up the change, run a project import refresh.

## verdict.json Schema

Write `verdict.json` for every iteration:

```json
{
  "approved": false,
  "iter": 2,
  "issues": [
    {
      "category": "materials",
      "severity": "blocker",
      "detail": "Body material is magenta in all views."
    }
  ],
  "remaining": 1
}
```

Rules:

- `approved` is `true` only when no blocker remains.
- `iter` equals the current iteration number.
- `issues` is an array, empty when approved.
- `remaining` equals the unresolved issue count.

When approved:

```json
{"approved": true, "iter": 3, "issues": [], "remaining": 0}
```
