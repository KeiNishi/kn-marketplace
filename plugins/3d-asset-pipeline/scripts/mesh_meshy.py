from __future__ import annotations

import argparse
import base64
import shutil
from pathlib import Path
from typing import Any

try:
    from . import _common, _credentials, _manifest
except ImportError:
    import _common  # type: ignore
    import _credentials  # type: ignore
    import _manifest  # type: ignore


LOGGER = _common.setup_logger("mesh_meshy")
VENDOR = "meshy:v5"
POST_ENDPOINT = "https://api.meshy.ai/openapi/v1/image-to-3d"
EXIT_INTERNAL_ERROR = 4


def _base_dir(value: str | None) -> Path | None:
    return Path(value).resolve() if value else None


def _rel(asset_dir: Path, path: Path) -> str:
    return path.relative_to(asset_dir).as_posix()


def _plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _concept_image(manifest: dict[str, Any], asset_dir: Path) -> Path:
    concept = manifest.get("stages", {}).get("concept", {})
    files = concept.get("files") or {}
    canonical = files.get("canonical")
    if not canonical:
        raise ValueError("Concept stage is done but files.canonical is missing")
    path = asset_dir / str(canonical)
    if not path.exists():
        raise FileNotFoundError(f"Canonical concept image not found: {path}")
    return path


def _data_uri(path: Path) -> str:
    suffix = path.suffix.lower()
    mime = "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


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


def _extract_model_url(model_urls: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = model_urls.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _download(url: str, target: Path, token: str) -> None:
    import requests

    response = requests.get(url, timeout=120)
    if response.status_code >= 400:
        raise RuntimeError(f"Meshy model download failed with HTTP {response.status_code}")
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
            "mesh",
            {"status": "failed", "error": error, "failedAt": _common.iso_now()},
            base,
        )
    except Exception:
        LOGGER.debug("Could not mark mesh stage as failed", exc_info=True)


def _validate_manifest(slug: str, base: Path | None) -> tuple[dict[str, Any], Path, Path]:
    manifest = _manifest.read(slug, base)
    concept = manifest.get("stages", {}).get("concept", {})
    if concept.get("status") != "done":
        raise ValueError("Stage 2 requires stages.concept.status == done before mesh generation")
    if not _manifest.concept_approved(manifest):
        raise ValueError(
            "Concept stage must be approved before mesh generation. "
            "Run /3d-pipeline:approve <slug> after reviewing concept/canonical.png."
        )
    asset_dir = _common.output_dir(slug, base)
    return manifest, asset_dir, _concept_image(manifest, asset_dir)


def _copy_dry_run(slug: str, base: Path | None, asset_dir: Path) -> dict[str, Any]:
    mesh_dir = asset_dir / "mesh"
    mesh_dir.mkdir(parents=True, exist_ok=True)
    sources = {
        "glb": _plugin_root() / "scripts" / "fixtures" / "mesh" / "dryrun.glb",
        "fbx": _plugin_root() / "scripts" / "fixtures" / "mesh" / "dryrun.fbx",
    }
    files: dict[str, str] = {}
    for label, source in sources.items():
        target = mesh_dir / f"{slug}.{label}"
        shutil.copyfile(source, target)
        files[label] = _rel(asset_dir, target)
    return _manifest.update_stage(
        slug,
        "mesh",
        {
            "status": "done",
            "vendor": VENDOR,
            "mode": "image-to-3d",
            "taskId": None,
            "predictionId": None,
            "dryRun": True,
            "files": files,
            "completedAt": _common.iso_now(),
        },
        base,
    )


def generate(slug: str, args: argparse.Namespace) -> dict[str, Any]:
    base = _base_dir(args.base)
    _manifest_data, asset_dir, image_path = _validate_manifest(slug, base)

    _manifest.update_stage(
        slug,
        "mesh",
        {
            "status": "in_progress",
            "vendor": VENDOR,
            "mode": "image-to-3d",
            "input": args.input,
            "targetPolys": args.target_polys,
            "pbr": args.pbr,
            "dryRun": _common.is_dry_run(),
            "startedAt": _common.iso_now(),
        },
        base,
    )

    if _common.is_dry_run():
        LOGGER.info("PIPELINE_DRY_RUN=1; copying Meshy mesh placeholders")
        return _copy_dry_run(slug, base, asset_dir)

    try:
        credentials = _credentials.require("MESHY_API_KEY")
    except ValueError as exc:
        _mark_failed(slug, base, "missing_credentials", str(exc))
        raise
    token = credentials["MESHY_API_KEY"]

    try:
        import requests

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload: dict[str, Any] = {
            "image_url": _data_uri(image_path),
            "enable_pbr": bool(args.pbr),
        }
        if args.target_polys is not None:
            payload["target_polycount"] = args.target_polys
        if args.seed is not None:
            payload["seed"] = args.seed
        if args.style:
            payload["texture_prompt"] = args.style

        response = requests.post(POST_ENDPOINT, headers=headers, json=payload, timeout=120)
        if response.status_code >= 400:
            detail = response.text[:500].replace(token, "<redacted>")
            raise RuntimeError(f"Meshy image-to-3D request failed with HTTP {response.status_code}: {detail}")
        task_id = _extract_task_id(response.json())
        poll_url = f"{POST_ENDPOINT}/{task_id}"

        def refresh() -> dict[str, Any]:
            result = requests.get(poll_url, headers=headers, timeout=60)
            if result.status_code >= 400:
                detail = result.text[:500].replace(token, "<redacted>")
                raise RuntimeError(f"Meshy poll failed with HTTP {result.status_code}: {detail}")
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
        model_urls = payload_json.get("model_urls") or payload_json.get("result", {}).get("model_urls")
        if not isinstance(model_urls, dict):
            raise RuntimeError("Meshy task did not include model_urls")

        glb_url = _extract_model_url(model_urls, "glb", "glb_url", "model_url")
        fbx_url = _extract_model_url(model_urls, "fbx", "fbx_url")
        if not glb_url or not fbx_url:
            raise RuntimeError("Meshy task did not include both GLB and FBX model URLs")

        mesh_dir = asset_dir / "mesh"
        mesh_dir.mkdir(parents=True, exist_ok=True)
        glb_path = mesh_dir / f"{slug}.glb"
        fbx_path = mesh_dir / f"{slug}.fbx"
        _download(glb_url, glb_path, token)
        _download(fbx_url, fbx_path, token)

        return _manifest.update_stage(
            slug,
            "mesh",
            {
                "status": "done",
                "vendor": VENDOR,
                "mode": "image-to-3d",
                "taskId": task_id,
                "files": {"glb": _rel(asset_dir, glb_path), "fbx": _rel(asset_dir, fbx_path)},
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
    parser = argparse.ArgumentParser(description="Generate Stage 2 mesh with Meshy v5 image-to-3D")
    parser.add_argument("slug", help="asset slug with an existing pipeline.json")
    parser.add_argument("--base", help="output base directory; defaults to git root or cwd")
    parser.add_argument("--mode", choices=("rapid", "pro"), default="rapid")
    parser.add_argument("--input", choices=("text", "image"), default="image")
    parser.add_argument("--target-polys", type=int)
    parser.add_argument("--pbr", dest="pbr", action="store_true", default=True)
    parser.add_argument("--no-pbr", dest="pbr", action="store_false")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--style")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        manifest = generate(args.slug, args)
    except (FileNotFoundError, ValueError) as exc:
        LOGGER.error("%s", exc)
        return _common.EXIT_USER_ERROR
    except TimeoutError as exc:
        LOGGER.error("%s", exc)
        return EXIT_INTERNAL_ERROR
    except Exception as exc:
        LOGGER.error("%s", exc)
        return _common.EXIT_API_ERROR

    mesh = manifest["stages"]["mesh"]
    print(f"Mesh stage {mesh['status']} for {args.slug}")
    print(f"vendor: {mesh.get('vendor')}")
    for label, path in sorted((mesh.get("files") or {}).items()):
        print(f"{label}: {path}")
    return _common.EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
