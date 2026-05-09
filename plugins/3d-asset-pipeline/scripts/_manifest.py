from __future__ import annotations

import json
import pathlib
from typing import Any

try:
    from . import _common
except ImportError:
    import _common  # type: ignore


SCHEMA_VERSION = "1.2"
SUPPORTED_SCHEMA_VERSIONS = {"1.1", "1.2"}
ASSET_TYPES = {"humanoid", "quadruped", "prop"}
STAGES = ("concept", "mesh", "rig", "animate", "engine", "review")
STATUSES = {"pending", "in_progress", "done", "failed", "skipped"}


def manifest_path(slug: str, base: pathlib.Path | None = None) -> pathlib.Path:
    return _common.output_dir(slug, base) / "pipeline.json"


def _stage_skeleton(asset_type: str) -> dict[str, dict[str, str]]:
    stages: dict[str, dict[str, str]] = {}
    for stage in STAGES:
        status = "skipped" if asset_type == "prop" and stage in {"rig", "animate"} else "pending"
        stages[stage] = {"status": status}
    return stages


def init(
    slug: str,
    name: str,
    description: str,
    asset_type: str,
    base: pathlib.Path | None = None,
) -> dict[str, Any]:
    if asset_type not in ASSET_TYPES:
        raise ValueError(f"Invalid asset_type: {asset_type}")

    path = manifest_path(slug, base)
    if path.exists():
        raise FileExistsError(f"Manifest already exists: {path}")

    now = _common.iso_now()
    manifest: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "slug": slug,
        "name": name,
        "description": description,
        "assetType": asset_type,
        "createdAt": now,
        "updatedAt": now,
        "dryRun": _common.is_dry_run(),
        "stages": _stage_skeleton(asset_type),
    }
    validate(manifest)
    _common.atomic_write_json(path, manifest)
    return manifest


def read(slug: str, base: pathlib.Path | None = None) -> dict[str, Any]:
    path = manifest_path(slug, base)
    with path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    validate(manifest)
    return manifest


def update_stage(
    slug: str,
    stage: str,
    fields: dict[str, Any],
    base: pathlib.Path | None = None,
) -> dict[str, Any]:
    if stage not in STAGES:
        raise ValueError(f"Unknown stage: {stage}")

    if "status" in fields and fields["status"] not in STATUSES:
        raise ValueError(f"Invalid status: {fields['status']}")

    manifest = read(slug, base)
    manifest["stages"][stage].update(fields)
    manifest["updatedAt"] = _common.iso_now()
    if manifest.get("schemaVersion") != SCHEMA_VERSION:
        manifest["schemaVersion"] = SCHEMA_VERSION
    validate(manifest)
    _common.atomic_write_json(manifest_path(slug, base), manifest)
    return manifest


def validate(manifest: dict[str, Any]) -> None:
    if manifest.get("schemaVersion") not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(
            f"Unsupported schemaVersion: {manifest.get('schemaVersion')}; "
            f"supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )
    if not manifest.get("slug"):
        raise ValueError("Manifest slug is required")
    if manifest.get("assetType") not in ASSET_TYPES:
        raise ValueError(f"Invalid assetType: {manifest.get('assetType')}")

    stages = manifest.get("stages")
    if not isinstance(stages, dict):
        raise ValueError("Manifest stages must be an object")

    for stage in STAGES:
        if stage not in stages:
            raise ValueError(f"Missing stage: {stage}")
        stage_data = stages[stage]
        if not isinstance(stage_data, dict):
            raise ValueError(f"Stage must be an object: {stage}")
        status = stage_data.get("status")
        if status not in STATUSES:
            raise ValueError(f"Invalid status for stage {stage}: {status}")


def concept_approved(manifest: dict[str, Any]) -> bool:
    return bool(manifest.get("stages", {}).get("concept", {}).get("approved"))
