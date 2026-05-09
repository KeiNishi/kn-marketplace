from __future__ import annotations

import argparse
import base64
import hashlib
import re
import shutil
from pathlib import Path
from typing import Any

try:
    from . import _common, _manifest
except ImportError:
    import _common  # type: ignore
    import _manifest  # type: ignore


LOGGER = _common.setup_logger("import_godot")
ENGINE = "godot"


def _base_dir(value: str | None) -> Path | None:
    return Path(value).resolve() if value else None


def _asset_dir(slug: str, base: Path | None) -> Path:
    return _common.output_dir(slug, base)


def _rel_to_project(project: Path, path: Path) -> str:
    return path.relative_to(project).as_posix()


def _stable_uid(seed: str) -> str:
    digest = hashlib.md5(seed.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")[:22]


def _pascal_name(slug: str) -> str:
    parts = [part for part in re.split(r"[^A-Za-z0-9]+", slug) if part]
    if not parts:
        return "Asset"
    return "".join(part[:1].upper() + part[1:] for part in parts)


def _import_content(uid: str) -> str:
    return (
        "[remap]\n"
        f"uid=uid://{uid}\n"
        'importer="scene"\n'
        'type="PackedScene"\n'
        "[params]\n"
        'nodes/root_type="Node3D"\n'
        "animation/import=true\n"
        "meshes/ensure_tangents=true\n"
        "materials/location=0\n"
        "materials/storage=0\n"
    )


def _scene_content(scene_uid: str, ext_id: str, slug: str, ext: str) -> str:
    node_name = _pascal_name(slug)
    return (
        f'[gd_scene load_steps=2 format=3 uid="uid://{scene_uid}"]\n'
        "\n"
        f'[ext_resource type="PackedScene" path="res://assets/characters/{slug}/{slug}.{ext}" id="{ext_id}"]\n'
        "\n"
        f'[node name="{node_name}" instance=ExtResource("{ext_id}")]\n'
    )


def _validate_project(project_value: str) -> Path:
    project = Path(project_value)
    if not project.is_absolute():
        raise ValueError("--project must be an absolute path to a Godot project root")
    project = project.resolve()
    if not project.exists() or not project.is_dir():
        raise ValueError(f"Godot project root does not exist: {project}")
    if not (project / "project.godot").is_file():
        raise ValueError(f"Godot project root must contain project.godot: {project}")
    return project


def _stage_status(manifest: dict[str, Any], stage: str) -> str:
    return str(manifest.get("stages", {}).get(stage, {}).get("status") or "")


def _default_source_stage(manifest: dict[str, Any]) -> str:
    asset_type = str(manifest.get("assetType") or "").lower()
    if asset_type == "prop":
        return "mesh"

    animate_status = _stage_status(manifest, "animate")
    rig_status = _stage_status(manifest, "rig")
    mesh_status = _stage_status(manifest, "mesh")

    if animate_status == "done":
        return "animated"
    if animate_status == "skipped" and rig_status == "done":
        return "rigged"
    if rig_status == "skipped" and mesh_status == "done":
        return "mesh"

    raise ValueError(
        "Stage 5 requires animation done, animation skipped with rig done, "
        "or rig skipped with mesh done"
    )


def _validate_prerequisites(manifest: dict[str, Any], source_stage: str) -> None:
    asset_type = str(manifest.get("assetType") or "").lower()
    mesh_status = _stage_status(manifest, "mesh")
    rig_status = _stage_status(manifest, "rig")
    animate_status = _stage_status(manifest, "animate")

    if mesh_status != "done":
        raise ValueError("Stage 5 requires stages.mesh.status == done before Godot import")

    if source_stage == "mesh":
        if asset_type == "prop":
            return
        if rig_status not in {"done", "skipped"}:
            raise ValueError("Stage 5 mesh import requires rig done or skipped")
        if animate_status not in {"done", "skipped", "pending"}:
            raise ValueError("Stage 5 mesh import requires a valid animation stage status")
        return

    if source_stage == "rigged":
        if rig_status != "done":
            raise ValueError("Stage 5 rigged import requires stages.rig.status == done")
        return

    if source_stage == "animated":
        if rig_status != "done":
            raise ValueError("Stage 5 animated import requires stages.rig.status == done")
        if animate_status != "done":
            raise ValueError("Stage 5 animated import requires stages.animate.status == done")
        return

    raise ValueError(f"Unknown source stage: {source_stage}")


def _source_path(asset_dir: Path, slug: str, source_stage: str) -> Path:
    if source_stage == "animated":
        return asset_dir / "animated" / f"{slug}.fbx"
    if source_stage == "rigged":
        return asset_dir / "rigged" / f"{slug}.fbx"
    if source_stage == "mesh":
        return asset_dir / "mesh" / f"{slug}.glb"
    raise ValueError(f"Unknown source stage: {source_stage}")


def import_asset(slug: str, args: argparse.Namespace) -> dict[str, Any]:
    base = _base_dir(args.base)
    manifest = _manifest.read(slug, base)
    source_stage = args.source_stage or _default_source_stage(manifest)
    _validate_prerequisites(manifest, source_stage)

    project = _validate_project(args.project)
    asset_dir = _asset_dir(slug, base)
    source = _source_path(asset_dir, slug, source_stage)
    if not source.is_file():
        raise FileNotFoundError(f"Source asset not found: {source}")

    ext = source.suffix.lstrip(".").lower()
    if ext not in {"fbx", "glb"}:
        raise ValueError(f"Godot import only supports FBX or GLB sources, got: {source.suffix}")

    target_dir = project / "assets" / "characters" / slug
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{slug}.{ext}"
    import_file = target_dir / f"{slug}.{ext}.import"
    scene_file = target_dir / f"{slug}.tscn"

    LOGGER.info("Copying %s to %s", source, target)
    shutil.copyfile(source, target)

    project_key = str(project)
    import_uid = _stable_uid(project_key + slug)
    import_file.write_text(_import_content(import_uid), encoding="utf-8", newline="\n")

    scene_path: str | None = None
    if args.scene:
        scene_uid = _stable_uid(project_key + slug + ".tscn")
        ext_id = "1_" + hashlib.md5((project_key + slug + ext).encode("utf-8")).hexdigest()[:4]
        scene_file.write_text(_scene_content(scene_uid, ext_id, slug, ext), encoding="utf-8", newline="\n")
        scene_path = _rel_to_project(project, scene_file)

    return _manifest.update_stage(
        slug,
        "engine",
        {
            "status": "done",
            "engine": ENGINE,
            "projectPath": str(project),
            "targetPath": _rel_to_project(project, target),
            "importFile": _rel_to_project(project, import_file),
            "scenePath": scene_path,
            "completedAt": _common.iso_now(),
        },
        base,
    )


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Stage 5 asset into a Godot 4 project")
    parser.add_argument("slug", help="asset slug with an existing pipeline.json")
    parser.add_argument("--project", required=True, help="absolute path to a Godot project root")
    parser.add_argument("--base", help="output base directory; defaults to git root or cwd")
    parser.add_argument("--source-stage", choices=("animated", "mesh", "rigged"))
    parser.add_argument("--scene", action="store_true", help="also emit a wrapper .tscn scene")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        manifest = import_asset(args.slug, args)
    except (FileNotFoundError, OSError, ValueError) as exc:
        LOGGER.error("%s", exc)
        return _common.EXIT_USER_ERROR
    except Exception as exc:
        LOGGER.error("%s", exc)
        return _common.EXIT_API_ERROR

    engine = manifest["stages"]["engine"]
    print(f"Godot import stage {engine['status']} for {args.slug}")
    print(f"engine: {engine.get('engine')}")
    print(f"target: {engine.get('targetPath')}")
    print(f"import: {engine.get('importFile')}")
    if engine.get("scenePath"):
        print(f"scene: {engine.get('scenePath')}")
    return _common.EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
