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


LOGGER = _common.setup_logger("animate_meshy")
VENDOR = "meshy:v5"
POST_ENDPOINT = "https://api.meshy.ai/openapi/v1/animation"
EXIT_INTERNAL_ERROR = 4
DEFAULT_CLIPS = {
    "humanoid": ["idle", "walk", "run", "attack"],
    "quadruped": ["idle", "walk", "gallop"],
}


def _base_dir(value: str | None) -> Path | None:
    return Path(value).resolve() if value else None


def _rel(asset_dir: Path, path: Path) -> str:
    return path.relative_to(asset_dir).as_posix()


def _plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _clips(manifest: dict[str, Any], requested: str | None) -> list[str]:
    if requested:
        clips = [item.strip() for item in requested.split(",") if item.strip()]
        if not clips:
            raise ValueError("--clips must include at least one clip name")
        return clips
    asset_type = str(manifest.get("assetType") or "").lower()
    return list(DEFAULT_CLIPS.get(asset_type, []))


def _rig_file(manifest: dict[str, Any], asset_dir: Path) -> Path:
    rig = manifest.get("stages", {}).get("rig", {})
    files = rig.get("files") or {}
    fbx = files.get("fbx")
    if not fbx:
        raise ValueError("Rig stage is done but files.fbx is missing")
    path = asset_dir / str(fbx)
    if not path.exists():
        raise FileNotFoundError(f"Rigged FBX not found: {path}")
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
        for key in ("fbx_url", "fbx", "animation_fbx_url", "url", "model_url"):
            result = _extract_url(value.get(key))
            if result:
                return result
    return None


def _download(url: str, target: Path, token: str) -> None:
    import requests

    response = requests.get(url, timeout=120)
    if response.status_code >= 400:
        raise RuntimeError(f"Meshy animated FBX download failed with HTTP {response.status_code}")
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
            "animate",
            {"status": "failed", "error": error, "failedAt": _common.iso_now()},
            base,
        )
    except Exception:
        LOGGER.debug("Could not mark animate stage as failed", exc_info=True)


def _validate_manifest(slug: str, base: Path | None) -> tuple[dict[str, Any], Path, Path]:
    manifest = _manifest.read(slug, base)
    animate = manifest.get("stages", {}).get("animate", {})
    if manifest.get("assetType") == "prop" or animate.get("status") == "skipped":
        LOGGER.info("Skipping animation stage for prop asset type")
        raise SystemExit(_common.EXIT_OK)

    rig = manifest.get("stages", {}).get("rig", {})
    if rig.get("status") != "done":
        raise ValueError("Stage 4 requires stages.rig.status == done before animation")
    if not rig.get("taskId") and not _common.is_dry_run():
        raise ValueError("Stage 4 requires stages.rig.taskId from Meshy rigging before animation")
    asset_dir = _common.output_dir(slug, base)
    return manifest, asset_dir, _rig_file(manifest, asset_dir)


def _copy_dry_run(slug: str, base: Path | None, asset_dir: Path, clips: list[str]) -> dict[str, Any]:
    animated_dir = asset_dir / "animated"
    animated_dir.mkdir(parents=True, exist_ok=True)
    source = _plugin_root() / "scripts" / "fixtures" / "animated" / "dryrun.fbx"
    target = animated_dir / f"{slug}.fbx"
    shutil.copyfile(source, target)
    path = _rel(asset_dir, target)
    files = {clip: path for clip in clips}
    return _manifest.update_stage(
        slug,
        "animate",
        {
            "status": "done",
            "vendor": VENDOR,
            "clips": clips,
            "takeMap": files,
            "dryRun": True,
            "files": files,
            "completedAt": _common.iso_now(),
        },
        base,
    )


def generate(slug: str, args: argparse.Namespace) -> dict[str, Any]:
    base = _base_dir(args.base)
    manifest, asset_dir, _rig_path = _validate_manifest(slug, base)
    clips = _clips(manifest, None if _common.is_dry_run() else args.clips)
    if not clips:
        LOGGER.info("Skipping animation stage for prop asset type")
        return manifest
    rig = manifest.get("stages", {}).get("rig", {})

    _manifest.update_stage(
        slug,
        "animate",
        {
            "status": "in_progress",
            "vendor": VENDOR,
            "clips": clips,
            "rigTaskId": rig.get("taskId"),
            "dryRun": _common.is_dry_run(),
            "startedAt": _common.iso_now(),
        },
        base,
    )

    if _common.is_dry_run():
        LOGGER.info("PIPELINE_DRY_RUN=1; copying Meshy animation placeholder")
        return _copy_dry_run(slug, base, asset_dir, clips)

    try:
        credentials = _credentials.require("MESHY_API_KEY")
    except ValueError as exc:
        _mark_failed(slug, base, "missing_credentials", str(exc))
        raise
    token = credentials["MESHY_API_KEY"]

    try:
        import requests

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        animated_dir = asset_dir / "animated"
        animated_dir.mkdir(parents=True, exist_ok=True)
        task_ids: dict[str, str] = {}
        files: dict[str, str] = {}

        for clip in clips:
            payload: dict[str, Any] = {
                "rigging_task_id": rig.get("taskId"),
                "clip": clip,
            }
            response = requests.post(POST_ENDPOINT, headers=headers, json=payload, timeout=120)
            if response.status_code >= 400:
                detail = response.text[:500].replace(token, "<redacted>")
                raise RuntimeError(f"Meshy animation request failed with HTTP {response.status_code}: {detail}")
            task_id = _extract_task_id(response.json())
            task_ids[clip] = task_id
            poll_url = f"{POST_ENDPOINT}/{task_id}"

            def refresh() -> dict[str, Any]:
                result = requests.get(poll_url, headers=headers, timeout=60)
                if result.status_code >= 400:
                    detail = result.text[:500].replace(token, "<redacted>")
                    raise RuntimeError(f"Meshy animation poll failed with HTTP {result.status_code}: {detail}")
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
                raise RuntimeError(f"Meshy animation task did not include an FBX URL for clip {clip}")

            fbx_path = animated_dir / f"{slug}_{clip}.fbx"
            _download(fbx_url, fbx_path, token)
            files[clip] = _rel(asset_dir, fbx_path)

        return _manifest.update_stage(
            slug,
            "animate",
            {
                "status": "done",
                "vendor": VENDOR,
                "clips": clips,
                "taskIds": task_ids,
                "takeMap": files,
                "files": files,
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
    parser = argparse.ArgumentParser(description="Generate Stage 4 animations with Meshy v5")
    parser.add_argument("slug", help="asset slug with an existing pipeline.json")
    parser.add_argument("--base", help="output base directory; defaults to git root or cwd")
    parser.add_argument("--clips", help="comma-separated clip list; defaults by manifest.assetType")
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

    animate = manifest["stages"]["animate"]
    print(f"Animation stage {animate['status']} for {args.slug}")
    print(f"vendor: {animate.get('vendor')}")
    for label, path in sorted((animate.get("files") or {}).items()):
        print(f"{label}: {path}")
    return _common.EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
