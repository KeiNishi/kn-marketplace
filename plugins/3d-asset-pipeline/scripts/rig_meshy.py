from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Any

try:
    from . import _common, _credentials, _manifest
except ImportError:
    import _common  # type: ignore
    import _credentials  # type: ignore
    import _manifest  # type: ignore


LOGGER = _common.setup_logger("rig_meshy")
VENDOR = "meshy:v5"
POST_ENDPOINT = "https://api.meshy.ai/openapi/v1/rigging"
EXIT_INTERNAL_ERROR = 4


def _base_dir(value: str | None) -> Path | None:
    return Path(value).resolve() if value else None


def _rel(asset_dir: Path, path: Path) -> str:
    return path.relative_to(asset_dir).as_posix()


def _plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _short_vendor(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value.split(":", 1)[0]


def _derive_template(manifest: dict[str, Any], requested: str | None) -> str | None:
    if requested:
        return requested
    asset_type = str(manifest.get("assetType") or "").lower()
    if asset_type in {"humanoid", "quadruped"}:
        return asset_type
    return None


def _mesh_file(manifest: dict[str, Any], asset_dir: Path) -> Path:
    mesh = manifest.get("stages", {}).get("mesh", {})
    files = mesh.get("files") or {}
    glb = files.get("glb")
    if not glb:
        raise ValueError("Mesh stage is done but files.glb is missing")
    path = asset_dir / str(glb)
    if not path.exists():
        raise FileNotFoundError(f"Mesh GLB not found: {path}")
    return path


def _extract_task_id(payload: dict[str, Any]) -> str:
    for key in ("result", "task_id", "id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
        if isinstance(value, dict):
            nested = _extract_task_id(value)
            if nested:
                return nested
    raise RuntimeError("Meshy response did not include a task id")


def _extract_url(value: Any) -> str | None:
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return value
    if isinstance(value, list):
        for item in value:
            result = _extract_url(item)
            if result:
                return result
    if isinstance(value, dict):
        for key in ("fbx_url", "fbx", "rigged_fbx_url", "url", "model_url"):
            result = _extract_url(value.get(key))
            if result:
                return result
    return None


def _download(url: str, target: Path, token: str) -> None:
    import requests

    response = requests.get(url, timeout=120)
    if response.status_code >= 400:
        raise RuntimeError(f"Meshy rigged FBX download failed with HTTP {response.status_code}")
    _common.atomic_write_bytes(target, response.content)


def _sanitize(message: str, token: str | None = None) -> str:
    cleaned = message
    if token:
        cleaned = cleaned.replace(token, "<redacted>")
    return cleaned[:500]


def _mark_failed(slug: str, base: Path | None, category: str, detail: str | None = None) -> None:
    error = category if not detail else f"{category}: {detail}"
    try:
        _manifest.update_stage(
            slug,
            "rig",
            {"status": "failed", "error": error, "failedAt": _common.iso_now()},
            base,
        )
    except Exception:
        LOGGER.debug("Could not mark rig stage as failed", exc_info=True)


def _validate_manifest(slug: str, base: Path | None, template: str | None) -> tuple[dict[str, Any], Path, Path, str]:
    manifest = _manifest.read(slug, base)
    rig = manifest.get("stages", {}).get("rig", {})
    if manifest.get("assetType") == "prop" or rig.get("status") == "skipped":
        LOGGER.info("Skipping rig stage for prop asset type")
        raise SystemExit(_common.EXIT_OK)

    resolved_template = _derive_template(manifest, template)
    if resolved_template not in {"humanoid", "quadruped"}:
        raise ValueError("Stage 3 requires --template humanoid|quadruped or manifest.assetType humanoid|quadruped")

    mesh = manifest.get("stages", {}).get("mesh", {})
    if mesh.get("status") != "done":
        raise ValueError("Stage 3 requires stages.mesh.status == done before rigging")
    asset_dir = _common.output_dir(slug, base)
    return manifest, asset_dir, _mesh_file(manifest, asset_dir), resolved_template


def _copy_dry_run(
    slug: str,
    base: Path | None,
    asset_dir: Path,
    manifest: dict[str, Any],
    template: str,
) -> dict[str, Any]:
    rigged_dir = asset_dir / "rigged"
    rigged_dir.mkdir(parents=True, exist_ok=True)
    source = _plugin_root() / "scripts" / "fixtures" / "rigged" / "dryrun.fbx"
    target = rigged_dir / f"{slug}.fbx"
    shutil.copyfile(source, target)
    mesh = manifest.get("stages", {}).get("mesh", {})
    return _manifest.update_stage(
        slug,
        "rig",
        {
            "status": "done",
            "vendor": VENDOR,
            "template": template,
            "taskId": None,
            "uploadedFrom": _short_vendor(mesh.get("vendor")),
            "dryRun": True,
            "files": {"fbx": _rel(asset_dir, target)},
            "completedAt": _common.iso_now(),
        },
        base,
    )


def generate(slug: str, args: argparse.Namespace) -> dict[str, Any]:
    base = _base_dir(args.base)
    manifest, asset_dir, mesh_path, template = _validate_manifest(slug, base, args.template)
    mesh = manifest.get("stages", {}).get("mesh", {})

    _manifest.update_stage(
        slug,
        "rig",
        {
            "status": "in_progress",
            "vendor": VENDOR,
            "template": template,
            "uploadedFrom": _short_vendor(mesh.get("vendor")),
            "dryRun": _common.is_dry_run(),
            "startedAt": _common.iso_now(),
        },
        base,
    )

    if _common.is_dry_run():
        LOGGER.info("PIPELINE_DRY_RUN=1; copying Meshy rig placeholder")
        return _copy_dry_run(slug, base, asset_dir, manifest, template)

    try:
        credentials = _credentials.require("MESHY_API_KEY")
    except ValueError as exc:
        _mark_failed(slug, base, "missing_credentials", str(exc))
        raise
    token = credentials["MESHY_API_KEY"]

    try:
        import requests

        headers = {"Authorization": f"Bearer {token}"}
        with mesh_path.open("rb") as handle:
            response = requests.post(
                POST_ENDPOINT,
                headers=headers,
                data={"template": template},
                files={"file": (mesh_path.name, handle, "model/gltf-binary")},
                timeout=120,
            )
        if response.status_code >= 400:
            detail = response.text[:500].replace(token, "<redacted>")
            raise RuntimeError(f"Meshy rigging request failed with HTTP {response.status_code}: {detail}")
        task_id = _extract_task_id(response.json())
        poll_url = f"{POST_ENDPOINT}/{task_id}"

        def refresh() -> dict[str, Any]:
            result = requests.get(poll_url, headers=headers, timeout=60)
            if result.status_code >= 400:
                detail = result.text[:500].replace(token, "<redacted>")
                raise RuntimeError(f"Meshy rigging poll failed with HTTP {result.status_code}: {detail}")
            payload_json = result.json()
            status = payload_json.get("status") or payload_json.get("task_status") or ""
            return {"status": str(status), "payload": payload_json}

        result = _common.poll(
            refresh,
            interval=5,
            timeout=600,
            status_done={"succeeded"},
            status_failed={"failed"},
        )
        payload_json = result["payload"]
        fbx_url = _extract_url(payload_json.get("model_urls") or payload_json.get("result") or payload_json)
        if not fbx_url:
            raise RuntimeError("Meshy rigging task did not include an FBX URL")

        rigged_dir = asset_dir / "rigged"
        rigged_dir.mkdir(parents=True, exist_ok=True)
        fbx_path = rigged_dir / f"{slug}.fbx"
        _download(fbx_url, fbx_path, token)

        return _manifest.update_stage(
            slug,
            "rig",
            {
                "status": "done",
                "vendor": VENDOR,
                "template": template,
                "taskId": task_id,
                "uploadedFrom": _short_vendor(mesh.get("vendor")),
                "files": {"fbx": _rel(asset_dir, fbx_path)},
                "completedAt": _common.iso_now(),
            },
            base,
        )
    except TimeoutError as exc:
        detail = _sanitize(str(exc), token)
        _mark_failed(slug, base, "meshy_timeout", detail)
        raise
    except Exception as exc:
        detail = _sanitize(str(exc), token)
        _mark_failed(slug, base, "meshy_api_failed", detail)
        raise


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Stage 3 rig with Meshy v5 auto-rigging")
    parser.add_argument("slug", help="asset slug with an existing pipeline.json")
    parser.add_argument("--base", help="output base directory; defaults to git root or cwd")
    parser.add_argument("--template", choices=("humanoid", "quadruped"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        manifest = generate(args.slug, args)
    except SystemExit as exc:
        return int(exc.code)
    except (FileNotFoundError, ValueError) as exc:
        LOGGER.error("%s", exc)
        return _common.EXIT_USER_ERROR
    except TimeoutError as exc:
        LOGGER.error("%s", exc)
        return EXIT_INTERNAL_ERROR
    except Exception as exc:
        LOGGER.error("%s", exc)
        return _common.EXIT_API_ERROR

    rig = manifest["stages"]["rig"]
    print(f"Rig stage {rig['status']} for {args.slug}")
    print(f"vendor: {rig.get('vendor')}")
    for label, path in sorted((rig.get("files") or {}).items()):
        print(f"{label}: {path}")
    return _common.EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
