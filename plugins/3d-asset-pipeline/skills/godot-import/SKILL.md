---
name: godot-import
description: This skill should be used when the user asks to "import to Godot", "drop the asset into Godot", or as stage 5 of the 3D pipeline. Copies the final asset into a Godot 4 project's assets/characters/<slug>/ folder and emits the .import config (and optionally a wrapper .tscn). Also triggers on "/3d-pipeline:import" command. Godot 4 only in v0.1.0; Unity 6 and Unreal 5 are future work.
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

# Godot Import

Run Stage 5 of the 3D asset pipeline after mesh generation, rigging, and animation have produced the final engine-ready file. This stage is intentionally local: it copies an existing FBX or GLB into a Godot 4 project and writes deterministic Godot import metadata.

## Stage 5 Inputs

- Read `3d-pipeline-output/<slug>/pipeline.json` before importing.
- Use `mesh/<slug>.glb` for static props.
- Use `animated/<slug>.fbx` for humanoid and quadruped assets when animation is complete.
- Fall back to `rigged/<slug>.fbx` only when animation is explicitly skipped and rigging is complete.
- Fall back to `mesh/<slug>.glb` only when both rigging and animation are skipped.
- Accept `--source-stage animated|mesh|rigged` for explicit control.
- Confirm the resolved source file exists before writing into the Godot project.
- Treat dry-run files the same as real files; Stage 5 still copies and emits import metadata.

## Project Validation

- Require `--project <godot-project-root>`.
- Require the project path to be absolute.
- Require `<project>/project.godot` to exist.
- Stop with a user-fixable error when the project root is missing or not a Godot project.
- Do not create project files outside an existing Godot project root.
- Run all path checks before copying source assets into the project.

## Target Path Convention

- Copy imported assets under `assets/characters/<slug>/` inside the Godot project.
- Store the engine asset as `<slug>.fbx` when the source is FBX.
- Store the engine asset as `<slug>.glb` when the source is GLB.
- Use manifest paths relative to the Godot project root, not `res://` paths.
- Use `res://assets/characters/<slug>/<slug>.<ext>` only inside Godot scene resources.
- Keep source pipeline outputs unchanged.

## Import Config

Stage 5 emits a sibling `.import` file next to the copied asset:

```ini
[remap]
uid=uid://<stable uid>
importer="scene"
type="PackedScene"
[params]
nodes/root_type="Node3D"
animation/import=true
meshes/ensure_tangents=true
materials/location=0
materials/storage=0
```

- `importer="scene"` tells Godot to use the scene importer for FBX and GLB.
- `type="PackedScene"` makes the imported asset loadable as a scene.
- `nodes/root_type="Node3D"` keeps the imported root compatible with Godot 4 3D scenes.
- `animation/import=true` preserves animation tracks when the source includes them.
- `meshes/ensure_tangents=true` improves normal map and tangent-space material results.
- `materials/location=0` keeps material handling in the default import mode.
- `materials/storage=0` keeps material storage in the default import mode.

## Optional Scene Wrapper

- Pass `--scene` to emit `assets/characters/<slug>/<slug>.tscn`.
- The wrapper uses the imported asset as an external `PackedScene` resource.
- The wrapper root node name is PascalCase derived from the slug.
- Use the wrapper when the next workflow expects a stable editable `.tscn` entry point.
- Skip the wrapper when the project will instance the imported FBX or GLB directly.

## UID Stability

- Generate the `.import` UID deterministically from `md5(project_path + slug)`.
- Base64-encode the digest and truncate it to 22 characters for `uid://...`.
- Generate the optional `.tscn` UID from `md5(project_path + slug + ".tscn")`.
- Stable UIDs reduce churn across repeated imports of the same asset into the same project.
- Changing the project path or slug intentionally changes the generated UID.

## Manifest Update

After a successful import, update `stages.engine`:

- `status: done`
- `engine: godot`
- `projectPath: <absolute project path>`
- `targetPath: assets/characters/<slug>/<slug>.<ext>`
- `importFile: assets/characters/<slug>/<slug>.<ext>.import`
- `scenePath: null` unless `--scene` was used
- `completedAt: <iso timestamp>`

Do not modify plugin or marketplace version fields during this stage.

## Reference Index

- `references/godot-fbx-vs-glb.md` explains why props use GLB, animated assets currently use FBX, and how Godot's material import settings affect this stage.
