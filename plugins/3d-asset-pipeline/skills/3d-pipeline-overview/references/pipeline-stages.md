# Pipeline Stages

## Concept

Input: `name`, `description`, and `assetType` from `pipeline.json`.

Output:

- `concept/front.png`
- `concept/three-quarter.png`
- `concept/side.png`
- `concept/back.png`
- `concept/canonical.png`

The canonical image is the source image for mesh generation and later review comparison.

## Mesh

Input: `concept/canonical.png` and the original description.

Output: `mesh/<slug>.glb`, with optional `mesh/<slug>.fbx` when a local converter is available.

## Rig

Input: mesh output.

Output: `rigged/<slug>.fbx`.

Skip when `assetType` is `prop`.

## Animate

Input: rigged output.

Output: `animated/<slug>.fbx` with named animation takes.

Skip when `assetType` is `prop`.

## Engine

Input: animated FBX for rigged assets, or GLB for props.

Output: copied asset files and a Godot wrapper scene under the target project.

## Review

Input: imported Godot asset, canonical concept image, and original description.

Output: review iteration folders, screenshot sets, fix manifests, and a final approval verdict.
