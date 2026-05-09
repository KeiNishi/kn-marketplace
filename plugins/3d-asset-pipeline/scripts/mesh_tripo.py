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


LOGGER = _common.setup_logger("mesh_tripo")
VENDOR = "tripo:v2"
POST_ENDPOINT = "https://api.tripo3d.ai/v2/openapi/task"
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


def _optional_key() -> str:
    try:
        values = _credentials.load()
    except FileNotFoundError as exc:
        raise ValueError("TRIPO_API_KEY is optional, but it is required to use the Tripo3D fallback") from exc
    except ImportError as exc:
        raise ValueError("python-dotenv is required to read optional TRIPO_API_KEY") from exc
    token = values.get("TRIPO_API_KEY")
    if not token:
        raise ValueError("TRIPO_API_KEY is optional, but it is required to use the Tripo3D fallback")
    return token


def _extract_task_id(payload: dict[str, Any]) -> str:
    data = payload.get("data")
    if isinstance(data, dict):
        for key in ("task_id", "id"):
            value = data.get(key)
            if isinstance(value, str) and value:
                return value
    for key in ("task_id", "id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    raise RuntimeError("Tripo3D response did not include a task id")


def _payload_body(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if isinstance(data, dict):
        return data
    return payload


def _extract_url(value: Any) -> str | None:
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return value
    if isinstance(value, list):
        for item in value:
            result = _extract_url(item)
            if result:
                return result
    if isinstance(value, dict):
        for key in ("model", "model_url", "glb", "url", "fbx"):
            result = _extract_url(value.get(key))
            if result:
                return result
    return None


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
            "input": args.input,
            "targetPolys": args.target_polys,
            "pbr": args.pbr,
            "dryRun": _common.is_dry_run(),
            "startedAt": _common.iso_now(),
        },
        base,
    )

    if _common.is_dry_run():
        LOGGER.info("PIPELINE_DRY_RUN=1; copying Tripo mesh placeholders")
        return _copy_dry_run(slug, base, asset_dir)

    try:
        token = _optional_key()
    except ValueError as exc:
        _mark_failed(slug, base, "missing_credentials", str(exc))
        raise

    try:
        import requests

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload: dict[str, Any] = {
            "type": "image_to_model",
            "file": {"type": "image", "data": _data_uri(image_path)},
        }
        if args.seed is not None:
            payload["seed"] = args.seed
        if args.style:
            payload["prompt"] = args.style

        response = requests.post(POST_ENDPOINT, headers=headers, json=payload, timeout=120)
        if response.status_code >= 400:
            detail = response.text[:500].replace(token, "<redacted>")
            raise RuntimeError(f"Tripo3D task request failed with HTTP {response.status_code}: {detail}")
        task_id = _extract_task_id(response.json())
        poll_url = f"{POST_ENDPOINT}/{task_id}"

        def refresh() -> dict[str, Any]:
            result = requests.get(poll_url, headers=headers, timeout=60)
            if result.status_code >= 400:
                detail = result.text[:500].replace(token, "<redacted>")
                raise RuntimeError(f"Tripo3D poll failed with HTTP {result.status_code}: {detail}")
            payload_json = result.json()
            body = _payload_body(payload_json)
            status = body.get("status") or body.get("task_status") or ""
            return {"status": str(status), "payload": payload_json}

        result = _common.poll(
            refresh,
            interval=5,
            timeout=600,
            status_done={"success"},
            status_failed={"failed"},
        )
        body = _payload_body(result["payload"])
        output = body.get("output") or body.get("result") or {}
        glb_url = _extract_url(output.get("model") if isinstance(output, dict) else output)
        if not glb_url:
            raise RuntimeError("Tripo3D task did not include output.model")

        fbx_url = None
        if isinstance(output, dict):
            fbx_url = _extract_url(output.get("fbx") or output.get("fbx_model"))

        mesh_dir = asset_dir / "mesh"
        mesh_dir.mkdir(parents=True, exist_ok=True)
        glb_path = mesh_dir / f"{slug}.glb"
        glb_response = requests.get(glb_url, timeout=120)
        if glb_response.status_code >= 400:
            raise RuntimeError(f"Tripo3D GLB download failed with HTTP {glb_response.status_code}")
        _common.atomic_write_bytes(glb_path, glb_response.content)

        files = {"glb": _rel(asset_dir, glb_path)}
        if fbx_url:
            try:
                fbx_response = requests.get(fbx_url, timeout=120)
                if fbx_response.status_code < 400:
                    fbx_path = mesh_dir / f"{slug}.fbx"
                    _common.atomic_write_bytes(fbx_path, fbx_response.content)
                    files["fbx"] = _rel(asset_dir, fbx_path)
            except Exception as exc:
                LOGGER.warning("Best-effort FBX download skipped: %s", _sanitize(str(exc), token))

        return _manifest.update_stage(
            slug,
            "mesh",
            {
                "status": "done",
                "vendor": VENDOR,
                "taskId": task_id,
                "files": files,
                "completedAt": _common.iso_now(),
            },
            base,
        )
    except TimeoutError as exc:
        detail = _sanitize(str(exc), token)
        _mark_failed(slug, base, "tripo_timeout", detail)
        raise
    except Exception as exc:
        detail = _sanitize(str(exc), token)
        _mark_failed(slug, base, "tripo_api_failed", detail)
        raise


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Stage 2 mesh with Tripo3D fallback")
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
